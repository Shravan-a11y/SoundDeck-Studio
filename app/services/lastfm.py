import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

BASE_URL = "https://ws.audioscrobbler.com/2.0/"

_request_lock = asyncio.Lock()
_last_request_time = 0.0


async def get_similar_tracks(
    artist: str,
    track: str,
    limit: int = 30
) -> list[dict]:
    global _last_request_time

    api_key = os.getenv("LASTFM_API_KEY")

    if not api_key:
        raise RuntimeError(
            "LASTFM_API_KEY is missing from the .env file"
        )

    params = {
        "method": "track.getSimilar",
        "artist": artist,
        "track": track,
        "api_key": api_key.strip(),
        "format": "json",
        "limit": limit,
        "autocorrect": 1
    }

    async with _request_lock:
        loop = asyncio.get_running_loop()
        elapsed = loop.time() - _last_request_time

        if elapsed < 1.1:
            await asyncio.sleep(1.1 - elapsed)

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(BASE_URL, params=params)
            _last_request_time = loop.time()
            response.raise_for_status()
            data = response.json()

    if "error" in data:
        raise ValueError(
            data.get("message", "Last.fm returned an error")
        )

    results = data.get("similartracks", {}).get("track", [])

    if isinstance(results, dict):
        results = [results]

    candidates = []

    for item in results:
        artist_data = item.get("artist", {})

        if isinstance(artist_data, dict):
            artist_name = artist_data.get("name", "")
        else:
            artist_name = str(artist_data)

        title = item.get("name", "")

        if not title or not artist_name:
            continue

        try:
            match_score = float(item.get("match", 0))
        except (ValueError, TypeError):
            match_score = 0.0

        candidates.append({
            "title": title,
            "artist": artist_name,
            "match_score": max(0.0, min(1.0, match_score)),
            "url": item.get("url")
        })

    return candidates


def rank_tracks(
    candidates: list[dict],
    limit: int = 20,
    max_per_artist: int = 2,
    diversity_weight: float = 0.15,
    score_field: str = "match_score"
) -> list[dict]:
    if limit < 1:
        raise ValueError("limit must be at least 1")

    if max_per_artist < 1:
        raise ValueError("max_per_artist must be at least 1")

    if not 0 <= diversity_weight <= 1:
        raise ValueError("diversity_weight must be between 0 and 1")

    unique_tracks = {}

    for item in candidates:
        title = str(item.get("title", "")).strip()
        artist = str(item.get("artist", "")).strip()

        if not title or not artist:
            continue

        key = (artist.casefold(), title.casefold())

        if key not in unique_tracks:
            unique_tracks[key] = {
                **item,
                "title": title,
                "artist": artist
            }

    remaining = list(unique_tracks.values())
    selected = []
    artist_counts = {}

    while remaining and len(selected) < limit:
        best_track = None
        best_score = float("-inf")
        best_relevance = 0.0
        best_penalty = 0.0

        for candidate in remaining:
            artist_key = candidate["artist"].casefold()

            if artist_counts.get(artist_key, 0) >= max_per_artist:
                continue

            try:
                relevance = float(candidate.get(score_field, 0.0))
            except (ValueError, TypeError):
                relevance = 0.0

            relevance = max(0.0, min(1.0, relevance))

            artist_penalty = min(
                artist_counts.get(artist_key, 0) / max_per_artist,
                1.0
            )

            diversity_adjustment = (
                diversity_weight * artist_penalty
            )

            score = (
                (1.0 - diversity_weight) * relevance
                - diversity_adjustment
            )

            if score > best_score:
                best_score = score
                best_track = candidate
                best_relevance = relevance
                best_penalty = diversity_adjustment

        if best_track is None:
            break

        artist_key = best_track["artist"].casefold()
        artist_counts[artist_key] = artist_counts.get(artist_key, 0) + 1

        best_track["relevance_score"] = round(best_relevance, 4)
        best_track["diversity_adjustment"] = round(best_penalty, 4)
        best_track["sounddeck_score"] = round(best_score, 4)
        best_track["ranking_position"] = len(selected) + 1

        selected.append(best_track)
        remaining.remove(best_track)

    return selected
