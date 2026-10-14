import asyncio
import csv
import inspect
from collections import Counter
from pathlib import Path

from app.services.lastfm import get_similar_tracks, rank_tracks
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

CANDIDATE_LIMIT = 30
METADATA_LIMIT = CANDIDATE_LIMIT
TOP_K = 20


async def resolve(value):
    if inspect.isawaitable(value):
        return await value
    return value


def key(track):
    return (
        track.get("artist", "").strip().casefold(),
        track.get("title", "").strip().casefold(),
    )


def average(values):
    return round(sum(values) / len(values), 4) if values else 0.0


def evaluate_strategy(name, tracks):
    tracks = tracks[:TOP_K]

    artist_counts = Counter(
        track.get("artist", "").strip().casefold()
        for track in tracks
        if track.get("artist")
    )

    genres = {
        genre
        for track in tracks
        for genre in track.get("genres", [])
    }

    return {
        "strategy": name,
        "track_count": len(tracks),
        "unique_artists": len(artist_counts),
        "unique_genres": len(genres),
        "average_lastfm_score": average([
            float(track.get("match_score", 0))
            for track in tracks
        ]),
        "average_hybrid_score": average([
            float(track.get("hybrid_score", track.get("match_score", 0)))
            for track in tracks
        ]),
        "average_metadata_coverage": average([
            float(track.get("metadata_coverage", 0))
            for track in tracks
        ]),
        "track_metadata_count": sum(
            track.get("metadata_source") == "track" for track in tracks
        ),
        "artist_fallback_count": sum(
            track.get("metadata_source") == "artist_fallback"
            for track in tracks
        ),
        "lastfm_only_count": sum(
            track.get("metadata_source") == "lastfm_only"
            for track in tracks
        ),
        "max_tracks_from_one_artist": max(
            artist_counts.values(), default=0
        ),
    }


async def evaluate_seed(title, artist):
    print(f"\n{'=' * 72}")
    print(f"Seed: {title} — {artist}")
    print("=" * 72)

    seed_tags = await resolve(get_track_tags(artist, title))
    seed_artist_tags = await resolve(get_artist_tags(artist))

    # Track tags take precedence. Artist tags are only a seed fallback
    # when the seed track has no usable tags.
    effective_seed_tags = seed_tags or seed_artist_tags

    print(f"Seed track tags: {len(seed_tags)}")
    print(f"Seed artist tags: {len(seed_artist_tags)}")
    print(f"Effective seed tags: {len(effective_seed_tags)}")

    candidates = await resolve(
        get_similar_tracks(
            artist=artist,
            track=title,
            limit=CANDIDATE_LIMIT,
        )
    )

    candidates = list({
        key(track): dict(track)
        for track in reversed(candidates or [])
        if track.get("artist") and track.get("title")
    }.values())

    if not candidates:
        print("No candidates returned.")
        return []

    # Baseline: original Last.fm similarity, with no diversity penalty.
    baseline = rank_tracks(
        candidates=[dict(track) for track in candidates],
        limit=TOP_K,
        score_field="match_score",
        diversity_weight=0,
        max_per_artist=max(1, len(candidates)),
    )

    enriched_map = {}

    for candidate in candidates[:METADATA_LIMIT]:
        candidate_title = candidate["title"]
        candidate_artist = candidate["artist"]

        try:
            track_tags = await resolve(
                get_track_tags(candidate_artist, candidate_title)
            )

            artist_tags = []

            if not track_tags:
                artist_tags = await resolve(
                    get_artist_tags(candidate_artist)
                )

            enriched = enrich_candidate_with_intelligence(
                dict(candidate),
                effective_seed_tags,
                track_tags,
                candidate_artist_tags=artist_tags,
            )

            enriched_map[key(candidate)] = enriched

        except Exception as exc:
            print(
                f"Metadata error for {candidate_title} "
                f"— {candidate_artist}: {exc}"
            )

    # Do not claim that candidates outside the enrichment budget were
    # metadata-enriched. They retain a Last.fm-only score.
    hybrid_candidates = []

    for candidate in candidates:
        candidate_key = key(candidate)

        if candidate_key in enriched_map:
            hybrid_candidates.append(dict(enriched_map[candidate_key]))
        else:
            hybrid_candidates.append({
                **candidate,
                "hybrid_score": float(candidate.get("match_score", 0)),
                "metadata_source": "lastfm_only",
                "metadata_enriched": False,
                "metadata_coverage": 0.0,
                "genres": [],
                "moods": [],
                "contexts": [],
            })

    hybrid = rank_tracks(
        candidates=[dict(track) for track in hybrid_candidates],
        limit=TOP_K,
        score_field="hybrid_score",
        diversity_weight=0,
        max_per_artist=max(1, len(candidates)),
    )

    diverse = rank_tracks(
        candidates=[dict(track) for track in hybrid_candidates],
        limit=TOP_K,
        score_field="hybrid_score",
        diversity_weight=0.15,
        max_per_artist=2,
    )

    baseline_keys = {key(track) for track in baseline}
    hybrid_keys = {key(track) for track in hybrid}

    overlap = len(baseline_keys & hybrid_keys)

    print(f"Candidates retrieved: {len(candidates)}")
    print(f"Candidates with metadata: {len(enriched_map)}")
    print(f"Baseline/hybrid top-{TOP_K} overlap: {overlap}/{TOP_K}")

    strategies = [
        evaluate_strategy("Baseline Last.fm", baseline),
        evaluate_strategy("Hybrid without diversity", hybrid),
        evaluate_strategy("Hybrid with diversity", diverse),
    ]

    for result in strategies:
        print(f"\n{result['strategy']}")

        for metric, value in result.items():
            if metric != "strategy":
                print(f"  {metric}: {value}")

    print("\nTop 10 hybrid recommendations:")

    for position, track in enumerate(hybrid[:10], start=1):
        print(
            f"{position:2}. {track.get('title', 'Unknown')} — "
            f"{track.get('artist', 'Unknown')} | "
            f"Last.fm={float(track.get('match_score', 0)):.3f} | "
            f"Hybrid={float(track.get('hybrid_score', 0)):.3f} | "
            f"Source={track.get('metadata_source', 'unknown')} | "
            f"Coverage={float(track.get('metadata_coverage', 0)):.2f}"
        )

    return [
        {"seed": f"{title} — {artist}", **result}
        for result in strategies
    ]


async def main():
    all_results = []

    for title, artist in SEEDS:
        try:
            all_results.extend(await evaluate_seed(title, artist))
        except Exception as exc:
            print(f"Evaluation failed for {title}: {exc}")

    if not all_results:
        print("\nNo evaluation results generated.")
        return

    output_path = Path("data") / "recommendation_evaluation.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(all_results[0].keys()),
        )
        writer.writeheader()
        writer.writerows(all_results)

    print(f"\nSaved evaluation to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
