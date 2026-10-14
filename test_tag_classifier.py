from app.services.tag_classifier import (
    classify_tags,
    compare_classifications
)

seed_tags = [
    "indie",
    "folk",
    "indie folk",
    "psychedelic",
    "sad",
    "heartbreaking",
    "late night",
    "2015",
]

candidate_tags = [
    "indie folk",
    "folk",
    "acoustic",
    "sad",
    "melancholic",
    "late night",
    "2018",
]

seed = classify_tags(seed_tags)
candidate = classify_tags(candidate_tags)

print("Seed classification:")
print(seed)

print("\nCandidate classification:")
print(candidate)

print("\nSimilarity:")
print(compare_classifications(seed, candidate))
