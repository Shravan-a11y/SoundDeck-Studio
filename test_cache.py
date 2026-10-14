import asyncio
from app.services.music_intelligence import (
    get_track_tags,
    read_cache,
    DATABASE_PATH
)

async def main():
    artist = "Lord Huron"
    track = "The Night We Met"
    key = f"track:{artist.casefold()}:{track.casefold()}"

    print("\nSoundDeck Cache Verification")
    print("=" * 40)
    print(f"Database: {DATABASE_PATH}")
    print(f"Database exists: {DATABASE_PATH.exists()}")

    cached_before = read_cache(key)
    print(f"Cache present before request: {cached_before is not None}")

    tags = await get_track_tags(artist, track)

    cached_after = read_cache(key)
    print(f"Tags returned: {tags}")
    print(f"Cache present after request: {cached_after is not None}")
    print(f"Cached data matches result: {cached_after == tags}")

    print("\nRun this script again to verify the existing cache is reused.")

asyncio.run(main())
