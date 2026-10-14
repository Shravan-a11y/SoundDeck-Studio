import json
import unittest
from unittest.mock import patch, AsyncMock
import httpx
from starlette.testclient import TestClient

from app.main import app
from app.schemas import PlaylistConstraints, PlaylistParseRequest
from app.services.ollama_service import (
    parse_playlist_request,
    check_ollama_health,
    clean_model_output,
    OllamaConnectionError,
    OllamaTimeoutError,
    OllamaModelNotFoundError,
    OllamaResponseValidationError,
    OllamaServiceError,
)


class TestOllamaOutputCleaning(unittest.TestCase):
    """Test output sanitizer handles thinking tokens and markdown fences."""

    def test_strip_markdown_code_fences(self):
        raw = "```json\n{\"limit\": 25, \"target_genres\": [\"indie\"]}\n```"
        cleaned = clean_model_output(raw)
        self.assertEqual(json.loads(cleaned), {"limit": 25, "target_genres": ["indie"]})

    def test_strip_thinking_tags(self):
        raw = "<think>Let me see what genres fit.\nIndie and rock.</think>\n{\"seed_artist\": \"Lord Huron\", \"target_genres\": [\"indie\"]}"
        cleaned = clean_model_output(raw)
        self.assertEqual(json.loads(cleaned), {"seed_artist": "Lord Huron", "target_genres": ["indie"]})

    def test_handles_empty_or_whitespace(self):
        self.assertEqual(clean_model_output(""), "")
        self.assertEqual(clean_model_output("   \n\t  "), "")


class TestPlaylistConstraintsSchema(unittest.TestCase):
    """Test Pydantic schema validation and normalization."""

    def test_valid_constraints_normalization(self):
        data = {
            "seed_artist": "  Lord Huron  ",
            "seed_track": " The Night We Met ",
            "target_genres": [" Indie ", "indie", "FOLK ", ""],
            "target_moods": ["calm", " CALM "],
            "target_contexts": ["STUDYING"],
            "limit": 25,
            "max_per_artist": 3,
            "diversity_weight": 0.5,
        }
        constraints = PlaylistConstraints.model_validate(data)
        self.assertEqual(constraints.seed_artist, "Lord Huron")
        self.assertEqual(constraints.seed_track, "The Night We Met")
        self.assertEqual(constraints.target_genres, ["indie", "folk"])
        self.assertEqual(constraints.target_moods, ["calm"])
        self.assertEqual(constraints.target_contexts, ["studying"])
        self.assertEqual(constraints.limit, 25)
        self.assertEqual(constraints.max_per_artist, 3)
        self.assertEqual(constraints.diversity_weight, 0.5)

    def test_default_values_applied(self):
        constraints = PlaylistConstraints.model_validate({})
        self.assertIsNone(constraints.seed_artist)
        self.assertIsNone(constraints.seed_track)
        self.assertEqual(constraints.target_genres, [])
        self.assertEqual(constraints.limit, 20)
        self.assertEqual(constraints.max_per_artist, 2)
        self.assertEqual(constraints.diversity_weight, 0.2)

    def test_limit_bounds_enforced(self):
        with self.assertRaises(Exception):
            PlaylistConstraints.model_validate({"limit": 2})  # below 5
        with self.assertRaises(Exception):
            PlaylistConstraints.model_validate({"limit": 100})  # above 50

    def test_diversity_weight_bounds_enforced(self):
        with self.assertRaises(Exception):
            PlaylistConstraints.model_validate({"diversity_weight": 1.5})
        with self.assertRaises(Exception):
            PlaylistConstraints.model_validate({"diversity_weight": -0.1})


class TestOllamaServiceUnit(unittest.IsolatedAsyncioTestCase):
    """Test Ollama client service with deterministic mock transports."""

    async def test_successful_request_and_parse(self):
        mock_payload = {
            "message": {
                "role": "assistant",
                "content": json.dumps({
                    "seed_artist": "Lord Huron",
                    "seed_track": None,
                    "target_genres": ["indie", "acoustic"],
                    "target_moods": ["calm"],
                    "target_contexts": ["studying"],
                    "limit": 20,
                    "max_per_artist": 2,
                    "diversity_weight": 0.8
                })
            }
        }

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/api/chat")
            return httpx.Response(200, json=mock_payload)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            constraints = await parse_playlist_request(
                prompt="Create a calm indie playlist for studying with Lord Huron",
                client=client,
            )

        self.assertEqual(constraints.seed_artist, "Lord Huron")
        self.assertIsNone(constraints.seed_track)
        self.assertEqual(constraints.target_genres, ["indie", "acoustic"])
        self.assertEqual(constraints.target_moods, ["calm"])
        self.assertEqual(constraints.limit, 20)
        self.assertEqual(constraints.diversity_weight, 0.8)

    async def test_reasoning_model_with_thinking_tags(self):
        raw_content = "<think>Analyzing user preferences: calm, studying, Lord Huron.</think>\n" + json.dumps({
            "seed_artist": "Lord Huron",
            "seed_track": "The Night We Met",
            "target_genres": ["indie folk"],
            "target_moods": ["melancholic", "calm"],
            "target_contexts": ["late night"],
            "limit": 15,
            "max_per_artist": 1,
            "diversity_weight": 0.5
        })

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"message": {"role": "assistant", "content": raw_content}})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            constraints = await parse_playlist_request(
                prompt="Late night set starting with The Night We Met",
                client=client,
            )

        self.assertEqual(constraints.seed_artist, "Lord Huron")
        self.assertEqual(constraints.seed_track, "The Night We Met")
        self.assertEqual(constraints.limit, 15)
        self.assertEqual(constraints.max_per_artist, 1)

    async def test_malformed_json_response_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"message": {"role": "assistant", "content": "Here is your playlist: [not json]"}})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            with self.assertRaises(OllamaResponseValidationError):
                await parse_playlist_request("prompt", client=client)

    async def test_invalid_schema_values_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={
                "message": {
                    "role": "assistant",
                    "content": json.dumps({"limit": 9999})
                }
            })

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            with self.assertRaises(OllamaResponseValidationError):
                await parse_playlist_request("prompt", client=client)

    async def test_model_not_found_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, text="model 'qwen3:1.7b' not found")

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            with self.assertRaises(OllamaModelNotFoundError):
                await parse_playlist_request("prompt", client=client)

    async def test_connection_error_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            with self.assertRaises(OllamaConnectionError):
                await parse_playlist_request("prompt", client=client)

    async def test_timeout_error_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("Timed out")

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            with self.assertRaises(OllamaTimeoutError):
                await parse_playlist_request("prompt", client=client)

    async def test_health_check_success(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"models": [{"name": "qwen3:1.7b"}]})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            data = await check_ollama_health(client=client)
            self.assertEqual(len(data.get("models", [])), 1)


class TestFastAPIEndpoint(unittest.TestCase):
    """Test the POST /api/ai/parse-playlist-request endpoint using TestClient."""

    def setUp(self):
        self.client = TestClient(app)

    @patch("app.main.parse_playlist_request")
    def test_parse_endpoint_success(self, mock_parse):
        mock_parse.return_value = PlaylistConstraints(
            seed_artist="Lord Huron",
            seed_track=None,
            target_genres=["indie", "acoustic"],
            target_moods=["calm"],
            target_contexts=["studying"],
            limit=20,
            max_per_artist=2,
            diversity_weight=0.8,
        )

        response = self.client.post(
            "/api/ai/parse-playlist-request",
            json={"prompt": "Create a calm indie playlist for studying with Lord Huron"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("constraints", body)
        self.assertIn("model", body)
        self.assertEqual(body["constraints"]["seed_artist"], "Lord Huron")
        self.assertEqual(body["constraints"]["target_genres"], ["indie", "acoustic"])
        self.assertEqual(body["constraints"]["limit"], 20)
        self.assertEqual(body["constraints"]["diversity_weight"], 0.8)

    def test_parse_endpoint_invalid_request(self):
        # Empty prompt
        response = self.client.post(
            "/api/ai/parse-playlist-request",
            json={"prompt": ""},
        )
        self.assertEqual(response.status_code, 422)

        # Missing prompt
        response = self.client.post(
            "/api/ai/parse-playlist-request",
            json={},
        )
        self.assertEqual(response.status_code, 422)

    @patch("app.main.parse_playlist_request")
    def test_parse_endpoint_ollama_connection_error(self, mock_parse):
        mock_parse.side_effect = OllamaConnectionError("Could not connect to Ollama")

        response = self.client.post(
            "/api/ai/parse-playlist-request",
            json={"prompt": "Any playlist prompt"},
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn("Local AI service unavailable", response.json()["detail"])

    @patch("app.main.parse_playlist_request")
    def test_parse_endpoint_ollama_model_not_found(self, mock_parse):
        mock_parse.side_effect = OllamaModelNotFoundError("Model not found")

        response = self.client.post(
            "/api/ai/parse-playlist-request",
            json={"prompt": "Any playlist prompt"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("Configured model not found", response.json()["detail"])

    @patch("app.main.parse_playlist_request")
    def test_parse_endpoint_ollama_timeout(self, mock_parse):
        mock_parse.side_effect = OllamaTimeoutError("Timed out")

        response = self.client.post(
            "/api/ai/parse-playlist-request",
            json={"prompt": "Any playlist prompt"},
        )
        self.assertEqual(response.status_code, 504)
        self.assertIn("Local AI request timed out", response.json()["detail"])

    @patch("app.main.parse_playlist_request")
    def test_parse_endpoint_validation_error(self, mock_parse):
        mock_parse.side_effect = OllamaResponseValidationError("Invalid JSON returned")

        response = self.client.post(
            "/api/ai/parse-playlist-request",
            json={"prompt": "Any playlist prompt"},
        )
        self.assertEqual(response.status_code, 502)
        self.assertIn("AI model returned invalid constraints", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
