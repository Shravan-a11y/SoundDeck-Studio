import asyncio
import inspect
from pprint import pprint

from app.services.lastfm import get_similar_tracks
from app.services.music_intelligence import get_track_tags


async def resolve(value):
    if inspect.isawaitable(value):
        return await value
    return value


async def main():
    print("\n=== get_similar_tracks signature ===")
    print(inspect.signature(get_similar_tracks))

    print("\n=== get_track_tags signature ===")
    print(inspect.signature(get_track_tags))

    print("\n=== Raw Last.fm candidate ===")
    candidates = await resolve(
        get_similar_tracks(
            track="The Night We Met",
            artist="Lord Huron",
            limit=3,
        )
    )

    pprint(candidates[:2] if candidates else candidates)

    print("\n=== Seed track tags ===")
    tags = await resolve(get_track_tags("The Night We Met", "Lord Huron"))
    pprint(tags)


asyncio.run(main())
