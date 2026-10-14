import os
import re
import json
import time
import sqlite3
import asyncio
import logging
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger("sounddeck.music_intelligence")

BASE_URL = "https://ws.audioscrobbler.com/2.0/"
CACHE_TTL_SECONDS = 30 * 24 * 60 * 60

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "music_metadata.sqlite3"

_request_lock = asyncio.Lock()
_last_request_time = 0.0

# Tags that are usually contextual rather than musical.
NOISY_TAGS = {
    "13 reasons why",
    "soundtrack",
    "seen live",
    "all",
    "favorites",
    "favourites",
    "favorite",
    "favourite",
    "my music",
    "awesome",
    "love",
}

YEAR_PATTERN = re.compile(r"^(19|20)\d{2}$")


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        str(DATABASE_PATH),
        timeout=10
    )

    connection.execute("""
        CREATE TABLE IF NOT EXISTS metadata_cache (
            cache_key TEXT PRIMARY KEY,
            tags_json TEXT NOT NULL,
            fetched_at REAL NOT NULL
        )
    """)

    return connection


def read_cache(cache_key: str):
    now = time.time()

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT tags_json, fetched_at
            FROM metadata_cache
            WHERE cache_key = ?
            """,
            (cache_key,)
        ).fetchone()

    if row is None:
        return None

    tags_json, fetched_at = row

    if now - fetched_at > CACHE_TTL_SECONDS:
        with get_connection() as connection:
            connection.execute(
                "DELETE FROM metadata_cache WHERE cache_key = ?",
                (cache_key,)
            )

        return None

    try:
        return json.loads(tags_json)
    except json.JSONDecodeError:
        return None


def write_cache(cache_key: str, tags: list[str]):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO metadata_cache (
                cache_key,
                tags_json,
                fetched_at
            )
            VALUES (?, ?, ?)
            ON CONFLICT(cache_key)
            DO UPDATE SET
                tags_json = excluded.tags_json,
                fetched_at = excluded.fetched_at
            """,
            (
                cache_key,
                json.dumps(tags),
                time.time()
            )
        )


async def lastfm_request(params: dict) -> dict:
    global _last_request_time

    api_key = os.getenv("LASTFM_API_KEY")

    if not api_key:
        raise RuntimeError(
            "LASTFM_API_KEY is missing from the .env file"
        )

    request_params = {
        **params,
        "api_key": api_key.strip(),
        "format": "json"
    }

    async with _request_lock:
        loop = asyncio.get_running_loop()
        elapsed = loop.time() - _last_request_time

        if elapsed < 1.1:
            await asyncio.sleep(1.1 - elapsed)

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                BASE_URL,
                params=request_params
            )

            _last_request_time = loop.time()
            response.raise_for_status()
            data = response.json()

    if "error" in data:
        raise ValueError(
            data.get("message", "Last.fm API error")
        )

    return data


def normalise_tags(
    tag_data,
    exclude_terms: list[str] | None = None
) -> list[str]:
    if isinstance(tag_data, dict):
        tag_data = [tag_data]

    excluded = {
        term.strip().casefold()
        for term in (exclude_terms or [])
        if term and term.strip()
    }

    tags = []

    for item in tag_data or []:
        if not isinstance(item, dict):
            continue

        name = item.get("name")

        if not isinstance(name, str):
            continue

        tag = " ".join(name.casefold().split())

        if not tag:
            continue

        # Filter year-only tags.
        if YEAR_PATTERN.fullmatch(tag):
            continue

        # Filter known contextual tags.
        if tag in NOISY_TAGS:
            continue

        # Remove the current artist's name when it appears as a tag.
        if tag in excluded:
            continue

        # Radio station tags are generally not musical descriptors.
        if " fm " in f" {tag} " or "radio station" in tag:
            continue

        tags.append(tag)

    return list(dict.fromkeys(tags))


async def get_track_tags(
    artist: str,
    track: str
) -> list[str]:
    cache_key = (
        f"track:{artist.strip().casefold()}:"
        f"{track.strip().casefold()}"
    )

    cached_tags = read_cache(cache_key)

    if cached_tags is not None:
        logger.debug("Track tag cache hit: %s - %s", artist, track)
        return cached_tags

    data = await lastfm_request({
        "method": "track.getTopTags",
        "artist": artist,
        "track": track,
        "autocorrect": 1
    })

    raw_tags = data.get("toptags", {}).get("tag", [])

    tags = normalise_tags(
        raw_tags,
        exclude_terms=[artist]
    )

    write_cache(cache_key, tags)

    logger.debug("Cached tags for %s - %s", artist, track)

    return tags


async def get_artist_tags(artist: str) -> list[str]:
    cache_key = f"artist:{artist.strip().casefold()}"

    cached_tags = read_cache(cache_key)

    if cached_tags is not None:
        logger.debug("Artist tag cache hit: %s", artist)
        return cached_tags

    data = await lastfm_request({
        "method": "artist.getTopTags",
        "artist": artist,
        "autocorrect": 1
    })

    raw_tags = data.get("toptags", {}).get("tag", [])

    tags = normalise_tags(
        raw_tags,
        exclude_terms=[artist]
    )

    write_cache(cache_key, tags)

    return tags


def calculate_tag_similarity(
    seed_tags: list[str],
    candidate_tags: list[str]
) -> float:
    seed = set(seed_tags)
    candidate = set(candidate_tags)

    if not seed or not candidate:
        return 0.0

    return len(seed & candidate) / len(seed | candidate)


def enrich_candidate(
    candidate: dict,
    seed_tags: list[str],
    candidate_tags: list[str]
) -> dict:
    tag_similarity = calculate_tag_similarity(
        seed_tags,
        candidate_tags
    )

    try:
        lastfm_score = float(
            candidate.get("match_score", 0.0)
        )
    except (ValueError, TypeError):
        lastfm_score = 0.0

    lastfm_score = max(0.0, min(1.0, lastfm_score))

    combined_score = (
        0.75 * lastfm_score
        + 0.25 * tag_similarity
    )

    return {
        **candidate,
        "tags": candidate_tags,
        "tag_similarity": round(tag_similarity, 4),
        "combined_score": round(combined_score, 4)
    }
from app.services.tag_classifier import (
    classify_tags,
    compare_classifications,
)


def calculate_hybrid_score(
    lastfm_score: float,
    genre_similarity: float,
    mood_similarity: float,
    context_similarity: float,
) -> float:
    weights = {
        "lastfm": 0.60,
        "genre": 0.20,
        "mood": 0.15,
        "context": 0.05,
    }

    values = {
        "lastfm": lastfm_score,
        "genre": genre_similarity,
        "mood": mood_similarity,
        "context": context_similarity,
    }

    for name, value in values.items():
        if not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be numeric")

        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be between 0 and 1")

    return round(
        sum(weights[name] * values[name] for name in weights),
        4,
    )


def enrich_candidate_with_intelligence(
    candidate: dict,
    seed_tags: list[str],
    candidate_tags: list[str],
) -> dict:
    seed_classification = classify_tags(seed_tags)
    candidate_classification = classify_tags(candidate_tags)

    similarities = compare_classifications(
        seed_classification,
        candidate_classification,
    )

    try:
        lastfm_score = float(candidate.get("match_score", 0.0))
    except (ValueError, TypeError):
        lastfm_score = 0.0

    lastfm_score = max(0.0, min(1.0, lastfm_score))

    hybrid_score = calculate_hybrid_score(
        lastfm_score=lastfm_score,
        genre_similarity=similarities["genre_similarity"],
        mood_similarity=similarities["mood_similarity"],
        context_similarity=similarities["context_similarity"],
    )

    return {
        **candidate,
        "tags": candidate_tags,
        "genres": candidate_classification["genres"],
        "moods": candidate_classification["moods"],
        "contexts": candidate_classification["contexts"],
        **similarities,
        "hybrid_score": hybrid_score,
        "combined_score": hybrid_score,
    }

# Updated missing-metadata-aware hybrid scoring.

def calculate_hybrid_score(
    lastfm_score: float,
    genre_similarity: float | None,
    mood_similarity: float | None,
    context_similarity: float | None,
) -> float:
    weights = {
        "lastfm": 0.60,
        "genre": 0.20,
        "mood": 0.15,
        "context": 0.05,
    }

    values = {
        "lastfm": lastfm_score,
        "genre": genre_similarity,
        "mood": mood_similarity,
        "context": context_similarity,
    }

    for name, value in values.items():
        if value is not None:
            if not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be numeric or None")
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")

    # Missing metadata signals fall back to Last.fm similarity.
    # This keeps every candidate on the same fixed-weight scale.
    effective_values = {
        name: lastfm_score if value is None else value
        for name, value in values.items()
    }

    return round(
        sum(weights[name] * effective_values[name] for name in weights),
        4,
    )


def enrich_candidate_with_intelligence(
    candidate: dict,
    seed_tags: list[str],
    candidate_tags: list[str],
    candidate_artist_tags: list[str] | None = None,
) -> dict:
    seed_classification = classify_tags(seed_tags or [])

    track_tags = list(candidate_tags or [])
    artist_tags = list(candidate_artist_tags or [])

    if track_tags:
        effective_tags = track_tags
        metadata_source = "track"
    elif artist_tags:
        effective_tags = artist_tags
        metadata_source = "artist_fallback"
    else:
        effective_tags = []
        metadata_source = "lastfm_only"

    candidate_classification = classify_tags(effective_tags)

    similarities = compare_classifications(
        seed_classification,
        candidate_classification,
    )

    try:
        lastfm_score = float(candidate.get("match_score", 0.0))
    except (ValueError, TypeError):
        lastfm_score = 0.0

    lastfm_score = max(0.0, min(1.0, lastfm_score))

    hybrid_score = calculate_hybrid_score(
        lastfm_score=lastfm_score,
        genre_similarity=similarities["genre_similarity"],
        mood_similarity=similarities["mood_similarity"],
        context_similarity=similarities["context_similarity"],
    )

    available_categories = sum(
        similarities[key] is not None
        for key in (
            "genre_similarity",
            "mood_similarity",
            "context_similarity",
        )
    )

    return {
        **candidate,
        "tags": effective_tags,
        "track_tags": track_tags,
        "artist_tags": artist_tags,
        "metadata_source": metadata_source,
        "metadata_enriched": metadata_source != "lastfm_only",
        "metadata_coverage": round(available_categories / 3, 4),
        "genres": candidate_classification["genres"],
        "moods": candidate_classification["moods"],
        "contexts": candidate_classification["contexts"],
        **similarities,
        "hybrid_score": hybrid_score,
        "combined_score": hybrid_score,
    }
