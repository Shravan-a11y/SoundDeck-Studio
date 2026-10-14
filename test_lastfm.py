import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

async def main():
    api_key = os.getenv("LASTFM_API_KEY")

    if not api_key:
        print("ERROR: API key missing from .env")
        return

    print("API key loaded:", bool(api_key))
    print("API key length:", len(api_key))

    params = {
        "method": "track.getSimilar",
        "artist": "Lord Huron",
        "track": "The Night We Met",
        "api_key": api_key.strip(),
        "format": "json",
        "limit": 10,
        "autocorrect": 1
    }

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            response = await client.get(
                "https://ws.audioscrobbler.com/2.0/",
                params=params
            )

            print("HTTP status:", response.status_code)

            try:
                data = response.json()
            except ValueError:
                print("Response is not JSON")
                print(response.text[:500])
                return

            if "error" in data:
                print("Last.fm error:", data.get("error"))
                print("Message:", data.get("message"))
                return

            tracks = data.get("similartracks", {}).get("track", [])

            if isinstance(tracks, dict):
                tracks = [tracks]

            print("SUCCESS: Last.fm API is working")
            print("Tracks returned:", len(tracks))

            for item in tracks[:5]:
                artist_data = item.get("artist", {})
                artist = artist_data.get("name", "") if isinstance(artist_data, dict) else ""
                print("-", item.get("name"), "|", artist)

        except httpx.HTTPError as exc:
            print("Network error:", type(exc).__name__, str(exc))

asyncio.run(main())
