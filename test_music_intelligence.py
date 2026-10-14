import asyncio

from app.services.music_intelligence import (
    get_track_tags,
    get_artist_tags
)


async def main():
    artist = "Lord Huron"
    track = "The Night We Met"

    print("\nSoundDeck Music Intelligence Test")
    print("=" * 40)

    track_tags = await get_track_tags(artist, track)
    print("\nTrack tags:")
    print(track_tags)

    artist_tags = await get_artist_tags(artist)
    print("\nArtist tags:")
    print(artist_tags)


asyncio.run(main())
