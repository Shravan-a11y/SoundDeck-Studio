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
    first = set(first_tags or [])
    second = set(second_tags or [])

    if not first or not second:
        return None

    return len(first & second) / len(first | second)


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
