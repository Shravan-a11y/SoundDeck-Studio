GENRE_TAGS = {
    "indie", "indie rock", "indie folk", "indie pop",
    "folk", "folk rock", "folk pop", "alternative",
    "alternative rock", "pop", "rock", "indie alternative",
    "ambient", "ambient pop", "electronic", "acoustic",
    "singer-songwriter", "psychedelic", "psychedelic rock",
    "country", "country folk", "r&b", "soul", "jazz",
    "classical", "hip hop", "rap", "metal", "punk",
    "dream pop", "shoegaze", "post-rock", "indie electronic",
    "chillout",
}

MOOD_TAGS = {
    "sad", "happy", "melancholic", "melancholy", "uplifting",
    "energetic", "relaxing", "chill", "calm", "emotional",
    "heartbreaking", "dark", "hopeful", "romantic", "nostalgic",
    "dreamy", "peaceful", "aggressive", "angry", "moody",
    "bittersweet", "introspective", "euphoric", "feel good",
    "laid back",
}

CONTEXT_TAGS = {
    "study", "workout", "running", "sleep", "sleep music",
    "background music", "late night", "road trip", "party",
    "driving", "focus", "meditation", "relax",
}


MOOD_SYNONYM_CLUSTERS = [
    {"melancholic", "melancholy", "sad", "heartbreaking", "bittersweet", "depressing"},
    {"calm", "relaxing", "chill", "peaceful", "laid back", "mellow"},
    {"happy", "uplifting", "feel good", "euphoric", "cheerful"},
    {"energetic", "aggressive", "angry", "hype", "workout"},
    {"dreamy", "nostalgic", "introspective", "hopeful"},
    {"dark", "moody", "somber"},
    {"romantic", "love"},
]

CONTEXT_SYNONYM_CLUSTERS = [
    {"study", "focus", "meditation", "background music"},
    {"party", "workout", "running", "driving", "road trip"},
    {"sleep", "sleep music", "late night", "relax"},
]


def single_tag_similarity(tag1: str, tag2: str) -> float:
    """Compute semantic similarity between two individual musical tags."""
    t1 = tag1.strip().casefold()
    t2 = tag2.strip().casefold()

    if not t1 or not t2:
        return 0.0

    if t1 == t2:
        return 1.0

    # Stem / suffix match (e.g. melancholy vs melancholic)
    if (t1.startswith("melanchol") and t2.startswith("melanchol")) or \
       (t1.startswith("chill") and t2.startswith("chill")) or \
       (t1.startswith("relax") and t2.startswith("relax")):
        return 0.95

    # Check mood synonym clusters
    for cluster in MOOD_SYNONYM_CLUSTERS:
        if t1 in cluster and t2 in cluster:
            return 0.85

    # Check context synonym clusters
    for cluster in CONTEXT_SYNONYM_CLUSTERS:
        if t1 in cluster and t2 in cluster:
            return 0.85

    # Subphrase / subgenre containment (e.g. "indie" in "indie folk" or "indie rock")
    if t1 in t2 or t2 in t1:
        return 0.80

    # Word-level token intersection (e.g. "indie rock" vs "alternative rock")
    w1 = set(t1.split())
    w2 = set(t2.split())
    if w1 & w2:
        return 0.50

    return 0.0


def classify_tags(tags: list[str]) -> dict:
    genres = []
    moods = []
    contexts = []
    other = []

    for original_tag in tags or []:
        if not isinstance(original_tag, str):
            continue

        tag = " ".join(original_tag.casefold().split())

        if not tag:
            continue

        if tag in GENRE_TAGS:
            genres.append(tag)
        elif tag in MOOD_TAGS:
            moods.append(tag)
        elif tag in CONTEXT_TAGS:
            contexts.append(tag)
        else:
            other.append(tag)

    return {
        "genres": list(dict.fromkeys(genres)),
        "moods": list(dict.fromkeys(moods)),
        "contexts": list(dict.fromkeys(contexts)),
        "other": list(dict.fromkeys(other)),
    }


def similarity(
    first_tags: list[str],
    second_tags: list[str],
) -> float | None:
    first = [t for t in (first_tags or []) if t and isinstance(t, str)]
    second = [t for t in (second_tags or []) if t and isinstance(t, str)]

    if not first or not second:
        return None

    # Calculate query coverage (how well second satisfies first)
    coverage_scores = []
    for q in first:
        best_match = max((single_tag_similarity(q, c) for c in second), default=0.0)
        coverage_scores.append(best_match)

    coverage = sum(coverage_scores) / len(coverage_scores) if coverage_scores else 0.0

    # Calculate candidate precision (how focused second is on first)
    precision_scores = []
    for c in second:
        best_match = max((single_tag_similarity(c, q) for q in first), default=0.0)
        precision_scores.append(best_match)

    precision = sum(precision_scores) / len(precision_scores) if precision_scores else 0.0

    # Weighted combination: 75% coverage, 25% precision
    score = (0.75 * coverage) + (0.25 * precision)
    return round(min(1.0, max(0.0, score)), 4)


def compare_classifications(
    seed: dict,
    candidate: dict,
) -> dict:
    result = {}

    for category in ("genres", "moods", "contexts"):
        first = seed.get(category, [])
        second = candidate.get(category, [])

        score = similarity(first, second)

        result[f"{category[:-1] if category != 'contexts' else 'context'}_similarity"] = (
            round(score, 4) if score is not None else None
        )

        result[f"{category}_available"] = bool(first and second)

    available = [
        result[key]
        for key in (
            "genre_similarity",
            "mood_similarity",
            "context_similarity",
        )
        if result[key] is not None
    ]

    result["metadata_similarity"] = (
        round(sum(available) / len(available), 4)
        if available
        else None
    )

    result["metadata_coverage"] = round(len(available) / 3, 4)

    return result
