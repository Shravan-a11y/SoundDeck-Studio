import asyncio
from app.services.lastfm import get_similar_tracks
from app.services.music_intelligence import (
    get_track_tags,
    get_artist_tags,
    enrich_candidate_with_intelligence,
)

SEEDS = [
    ("The Night We Met", "Lord Huron"),
    ("505", "Arctic Monkeys"),
    ("Sweater Weather", "The Neighbourhood"),
]


async def main():
    for seed_title, seed_artist in SEEDS:
        print("\n" + "=" * 90)
        print(f"SEED: {seed_title} — {seed_artist}")
        print("=" * 90)

        seed_tags = await get_track_tags(seed_artist, seed_title)
        if not seed_tags:
            seed_tags = await get_artist_tags(seed_artist)

        candidates = await get_similar_tracks(
            artist=seed_artist,
            track=seed_title,
            limit=30,
        )

        results = []

        for candidate in candidates:
            title = candidate["title"]
            artist = candidate["artist"]

            try:
                track_tags = await get_track_tags(artist, title)
                artist_tags = []

                if not track_tags:
                    artist_tags = await get_artist_tags(artist)

                result = enrich_candidate_with_intelligence(
                    candidate,
                    seed_tags,
                    track_tags,
                    candidate_artist_tags=artist_tags,
                )
                results.append(result)

            except Exception as exc:
                print(f"Could not process {title} — {artist}: {exc}")

        results.sort(
            key=lambda item: item.get("hybrid_score", 0),
            reverse=True,
        )

        print(
            f"{'Track':35} {'Last.fm':>8} {'Hybrid':>8} "
            f"{'Genre':>8} {'Mood':>8} {'Context':>8} {'Coverage':>9}"
        )
        print("-" * 100)

        for item in results[:20]:
            print(
                f"{item['title'][:34]:35} "
                f"{item.get('match_score', 0):8.3f} "
                f"{item.get('hybrid_score', 0):8.3f} "
                f"{str(item.get('genre_similarity')):>8} "
                f"{str(item.get('mood_similarity')):>8} "
                f"{str(item.get('context_similarity')):>8} "
                f"{item.get('metadata_coverage', 0):9.2f}"
            )


if __name__ == "__main__":
    asyncio.run(main())
