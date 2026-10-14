import asyncio
import httpx

BASE_URL = "https://musicbrainz.org/ws/2"

HEADERS = {
    "User-Agent": "SoundDeck/0.1.0 (music-discovery-project)"
}

_request_lock = asyncio.Lock()
_last_request_time = 0.0


async def search_tracks(query: str, limit: int = 10):
    global _last_request_time

    params = {
        "query": query,
        "fmt": "json",
        "limit": limit
    }

    async with _request_lock:
        loop = asyncio.get_running_loop()
        elapsed = loop.time() - _last_request_time

        if elapsed < 1.1:
            await asyncio.sleep(1.1 - elapsed)

        async with httpx.AsyncClient(
            timeout=15.0,
            headers=HEADERS
        ) as client:
            response = await client.get(
                f"{BASE_URL}/recording",
                params=params
            )

            _last_request_time = loop.time()
            response.raise_for_status()
            data = response.json()

    tracks = []

    for recording in data.get("recordings", []):
        artist_credit = recording.get("artist-credit", [])

        artists = [
            item["artist"]["name"]
            for item in artist_credit
            if isinstance(item, dict) and "artist" in item
        ]

        tracks.append({
            "id": recording.get("id"),
            "title": recording.get("title"),
            "artists": artists,
            "duration_ms": recording.get("length"),
            "first_release_date": recording.get(
                "first-release-date"
            )
        })

    return tracks
