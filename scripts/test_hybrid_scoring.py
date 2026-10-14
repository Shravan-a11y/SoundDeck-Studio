from app.services.music_intelligence import (
    calculate_hybrid_score,
    enrich_candidate_with_intelligence,
)

print("Test 1: All metadata available")
print(calculate_hybrid_score(0.8, 0.7, 0.6, 0.5))

print("\nTest 2: Genre metadata unavailable")
print(calculate_hybrid_score(0.8, None, 0.6, 0.5))

print("\nTest 3: Only Last.fm available")
print(calculate_hybrid_score(0.8, None, None, None))

print("\nTest 4: Candidate with artist-tag fallback")
result = enrich_candidate_with_intelligence(
    candidate={
        "title": "Example Track",
        "artist": "Example Artist",
        "match_score": 0.75,
    },
    seed_tags=["indie folk", "folk", "sad", "late night"],
    candidate_tags=[],
    candidate_artist_tags=["indie folk", "folk", "sad"],
)

print("Score:", result["hybrid_score"])
print("Metadata source:", result["metadata_source"])
print("Genres:", result["genres"])
print("Moods:", result["moods"])
print("Coverage:", result["metadata_coverage"])
