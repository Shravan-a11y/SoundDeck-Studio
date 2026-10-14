import asyncio

from app.services.lastfm import get_similar_tracks
from app.services.music_intelligence import get_track_tags, get_artist_tags


SEEDS = [
    ("The Night We Met", "Lord Huron"),
    ("505", "Arctic Monkeys"),
    ("Sweater Weather", "The Neighbourhood"),
]


async def main():
    for title, artist in SEEDS:
        print(f"\n{'=' * 65}")
        print(f"{title} — {artist}")
        print("=" * 65)

        candidates = await get_similar_tracks(
            artist=artist,
            track=title,
            limit=30,
        )

        track_tag_count = 0
        artist_fallback_count = 0
        missing_count = 0

        for candidate in candidates:
            candidate_title = candidate["title"]
            candidate_artist = candidate["artist"]

            tags = await get_track_tags(
                candidate_artist,
                candidate_title,
            )

            if tags:
                track_tag_count += 1
                source = "track tags"
            else:
                artist_tags = await get_artist_tags(candidate_artist)

                if artist_tags:
                    artist_fallback_count += 1
                    source = "artist fallback"
                else:
                    missing_count += 1
                    source = "no metadata"

            print(
                f"{candidate_title} — {candidate_artist}: {source}"
            )

        print("\nSummary")
        print(f"Track metadata: {track_tag_count}")
        print(f"Artist fallback: {artist_fallback_count}")
        print(f"No metadata: {missing_count}")


asyncio.run(main())
