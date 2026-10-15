import os
import re
import json
import logging
from typing import Optional

import httpx
from dotenv import load_dotenv

from app.schemas import PlaylistConstraints

load_dotenv(override=True)

logger = logging.getLogger("sounddeck.ollama")

DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "qwen3:1.7b"
DEFAULT_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT", "120.0"))


class OllamaServiceError(Exception):
    """Base exception for Ollama service errors."""
    pass


class OllamaConnectionError(OllamaServiceError):
    """Raised when the Ollama service cannot be reached."""
    pass


class OllamaTimeoutError(OllamaServiceError):
    """Raised when an Ollama request times out."""
    pass


class OllamaModelNotFoundError(OllamaServiceError):
    """Raised when the requested model is not found in Ollama."""
    pass


class OllamaResponseValidationError(OllamaServiceError):
    """Raised when the model response is malformed or violates the schema."""
    pass


def get_ollama_config() -> tuple[str, str]:
    """Retrieve base URL and model name from environment variables."""
    base_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).strip().rstrip("/")
    model = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL).strip()
    return base_url, model


SYSTEM_PROMPT = """You are SoundDeck Studio's AI music curation assistant.
Your task is to analyze natural-language playlist requests from DJs and event organizers and convert them into structured JSON constraints.

You MUST respond ONLY with a valid JSON object matching this exact structure:
{
  "seed_artist": "Artist name or null if none specified",
  "seed_track": "Track title or null if none specified",
  "target_genres": ["genre1", "genre2"],
  "target_moods": ["mood1", "mood2"],
  "target_contexts": ["context1", "context2"],
  "exclude_genres": ["genre_to_avoid"],
  "exclude_artists": ["artist_to_avoid"],
  "limit": 20,
  "max_per_artist": 2,
  "diversity_weight": 0.2
}

Guidelines:
1. Extract any mentioned seed track or artist. For example:
   - "start with a track by Lord Huron" -> seed_artist: "Lord Huron", seed_track: null
   - "505 by Arctic Monkeys" -> seed_artist: "Arctic Monkeys", seed_track: "505"
2. If track count is mentioned, set limit between 5 and 50 (default 20).
3. If diversity or avoiding repeat artists is requested, set max_per_artist to 1 or 2, and diversity_weight to a number between 0.0 and 1.0 (e.g. 0.8 for high diversity).
4. Put clean descriptive strings into target_genres, target_moods, and target_contexts.
5. If the request asks to avoid, exclude, or skip certain genres (e.g. "no rap", "avoid hip hop") or artists (e.g. "exclude Drake"), put them in exclude_genres and exclude_artists.
6. Do NOT output commentary, markdown blocks, or extra text. Output raw JSON only.
"""


def clean_model_output(content: str) -> str:
    """Remove thinking tags, code fences, and extraneous whitespace."""
    if not content:
        return ""

    # Strip thinking blocks from reasoning models (e.g. Qwen3 / DeepSeek <think>...</think>)
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", content, flags=re.DOTALL)

    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())

    # Find the outer JSON object boundaries
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end >= start:
        cleaned = cleaned[start:end + 1]

    return cleaned.strip()


async def check_ollama_health(
    base_url: Optional[str] = None,
    timeout: float = 5.0,
    client: Optional[httpx.AsyncClient] = None,
) -> dict:
    """Check whether the Ollama server is reachable and return installed models."""
    url, _ = get_ollama_config()
    target_base = (base_url or url).rstrip("/")

    async def _do_req(c: httpx.AsyncClient):
        response = await c.get(f"{target_base}/api/tags")
        response.raise_for_status()
        return response.json()

    try:
        if client:
            return await _do_req(client)
        else:
            async with httpx.AsyncClient(timeout=timeout) as c:
                return await _do_req(c)
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        raise OllamaConnectionError(
            f"Could not connect to Ollama at {target_base}. Ensure Ollama is running."
        ) from exc
    except httpx.TimeoutException as exc:
        raise OllamaTimeoutError(
            f"Connection to Ollama at {target_base} timed out after {timeout}s."
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise OllamaServiceError(
            f"Ollama returned HTTP error {exc.response.status_code}: {exc.response.text}"
        ) from exc
    except httpx.HTTPError as exc:
        raise OllamaServiceError(f"HTTP error communicating with Ollama: {exc}") from exc


async def parse_playlist_request(
    prompt: str,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    timeout: Optional[float] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> PlaylistConstraints:
    """
    Send natural-language playlist request to local Ollama model
    and validate returned structured constraints.
    """
    configured_base, configured_model = get_ollama_config()
    target_base = (base_url or configured_base).rstrip("/")
    target_model = model or configured_model
    effective_timeout = timeout if timeout is not None else DEFAULT_TIMEOUT_SECONDS

    payload = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.2,
        },
    }

    endpoint = f"{target_base}/api/chat"

    async def _post_chat(c: httpx.AsyncClient):
        return await c.post(endpoint, json=payload)

    try:
        if client:
            resp = await _post_chat(client)
        else:
            async with httpx.AsyncClient(timeout=effective_timeout) as c:
                resp = await _post_chat(c)

        if resp.status_code == 404:
            raise OllamaModelNotFoundError(
                f"Model '{target_model}' was not found in Ollama at {target_base}. "
                f"Run `ollama pull {target_model}` to download it."
            )

        resp.raise_for_status()
        resp_data = resp.json()

    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        logger.warning("Ollama connection failed at %s", target_base)
        raise OllamaConnectionError(
            f"Could not connect to Ollama at {target_base}. "
            "Ensure Ollama is running (`ollama serve`)."
        ) from exc

    except httpx.TimeoutException as exc:
        logger.warning("Ollama request timed out after %s s", effective_timeout)
        raise OllamaTimeoutError(
            f"Request to Ollama timed out after {effective_timeout} seconds."
        ) from exc

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise OllamaModelNotFoundError(
                f"Model '{target_model}' was not found in Ollama at {target_base}. "
                f"Run `ollama pull {target_model}` to download it."
            ) from exc
        raise OllamaServiceError(
            f"Ollama returned HTTP error {exc.response.status_code}: {exc.response.text}"
        ) from exc

    except httpx.HTTPError as exc:
        raise OllamaServiceError(f"Ollama communication error: {exc}") from exc

    # Extract assistant message content
    raw_content = ""
    if isinstance(resp_data, dict):
        if "message" in resp_data and isinstance(resp_data["message"], dict):
            msg = resp_data["message"]
            raw_content = msg.get("content", "")
            # If content is empty but thinking has JSON, fallback to thinking block
            if not raw_content.strip() and "thinking" in msg:
                raw_content = msg.get("thinking", "")
        elif "response" in resp_data:
            raw_content = resp_data.get("response", "")

    cleaned_json_str = clean_model_output(raw_content)

    if not cleaned_json_str:
        raise OllamaResponseValidationError(
            f"Ollama returned an empty response or no valid JSON. Raw output: {raw_content!r}"
        )

    try:
        parsed_dict = json.loads(cleaned_json_str)
    except json.JSONDecodeError as exc:
        logger.error("JSON decode error from Ollama response: %s", cleaned_json_str)
        raise OllamaResponseValidationError(
            f"Model output is not valid JSON: {exc}. Cleaned string: {cleaned_json_str}"
        ) from exc

    if not isinstance(parsed_dict, dict):
        raise OllamaResponseValidationError(
            f"Expected a JSON object from model, received: {type(parsed_dict).__name__}"
        )

    # Normalize defaults if omitted or provided as null
    if not parsed_dict.get("limit"):
        parsed_dict["limit"] = 20
    if not parsed_dict.get("max_per_artist"):
        parsed_dict["max_per_artist"] = 2
    if parsed_dict.get("diversity_weight") is None:
        parsed_dict["diversity_weight"] = 0.2

    try:
        constraints = PlaylistConstraints.model_validate(parsed_dict)
    except Exception as exc:
        logger.error("Pydantic validation failed for Ollama constraints: %s", exc)
        raise OllamaResponseValidationError(
            f"Model constraints failed validation: {exc}"
        ) from exc

    return constraints
