from app.services.tag_classifier import (
    classify_tags,
    compare_classifications
)


def calculate_hybrid_score(
    lastfm_score,
    genre_similarity,
    mood_similarity,
    context_similarity
):
    weights = {
        "lastfm": 0.60,
        "genre": 0.20,
        "mood": 0.15,
        "context": 0.05,
    }

    values = {
        "lastfm": lastfm_score,
        "genre": genre_similarity,
        "mood": mood_similarity,
        "context": context_similarity,
    }

    for name, value in values.items():
        if not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be numeric")

        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be between 0 and 1")

    score = sum(
        weights[name] * values[name]
        for name in weights
    )

    return round(score, 4)


seed_tags = [
    "indie",
    "folk",
    "indie folk",
    "psychedelic",
    "sad",
    "heartbreaking",
    "late night",
]

candidate_tags = [
    "indie folk",
    "folk",
    "acoustic",
    "sad",
    "melancholic",
    "late night",
]

seed = classify_tags(seed_tags)
candidate = classify_tags(candidate_tags)

similarities = compare_classifications(seed, candidate)

lastfm_score = 0.85

hybrid_score = calculate_hybrid_score(
    lastfm_score=lastfm_score,
    genre_similarity=similarities["genre_similarity"],
    mood_similarity=similarities["mood_similarity"],
    context_similarity=similarities["context_similarity"],
)

print("SoundDeck Hybrid Scoring Test")
print("=" * 40)
print(f"Last.fm score:       {lastfm_score:.4f}")
print(f"Genre similarity:    {similarities['genre_similarity']:.4f}")
print(f"Mood similarity:     {similarities['mood_similarity']:.4f}")
print(f"Context similarity:  {similarities['context_similarity']:.4f}")
print(f"Hybrid score:        {hybrid_score:.4f}")

assert 0.0 <= hybrid_score <= 1.0
print("\nPASS: Hybrid score is within the valid range.")
