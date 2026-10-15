import csv
import io
from typing import Any, Union

DANGEROUS_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

CSV_FIELDNAMES = [
    "Position",
    "Track Title",
    "Artist",
    "Album",
    "URL",
    "Tags",
    "Genres",
    "Moods",
    "Contexts",
    "Match Score",
    "Hybrid Score",
    "Diversity Adjustment",
    "Final Recommendation Score",
    "Explanation",
]


def sanitize_csv_value(value: Any) -> str:
    """
    Sanitize text fields against spreadsheet formula injection (CWE-1236).
    If a string starts with =, +, -, @, tab, or CR, it is prefixed with a single quote.
    """
    if value is None:
        return ""

    text = str(value)
    # Check if leading characters (ignoring leading whitespace) trigger formula execution
    stripped = text.lstrip()
    if stripped.startswith(DANGEROUS_FORMULA_PREFIXES):
        return f"'{text}"
    return text


def format_list_field(items: Any) -> str:
    """Format a list or sequence of strings into a clean comma-delimited string."""
    if not items:
        return ""
    if isinstance(items, (list, tuple, set)):
        cleaned = [str(x).strip() for x in items if str(x).strip()]
        return ", ".join(cleaned)
    return str(items).strip()


def format_numeric_score(value: Any) -> str:
    """Format numeric float scores to 4 decimal places, or return empty string."""
    if value is None or value == "":
        return ""
    try:
        val = float(value)
        return f"{val:.4f}"
    except (ValueError, TypeError):
        return sanitize_csv_value(str(value))


def export_playlist_to_csv(tracks: list[Union[dict, Any]]) -> str:
    """
    Serialize a list of playlist tracks to a RFC 4180 compliant CSV string
    with formula injection protection on all untrusted text fields.
    """
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")

    # Write Header Row
    writer.writerow(CSV_FIELDNAMES)

    for index, raw_track in enumerate(tracks, start=1):
        if hasattr(raw_track, "model_dump"):
            track = raw_track.model_dump()
        elif hasattr(raw_track, "dict"):
            track = raw_track.dict()
        elif isinstance(raw_track, dict):
            track = raw_track
        else:
            track = dict(raw_track)

        # 1. Position
        pos = track.get("ranking_position") or track.get("position") or index

        # 2. Track Title
        title = sanitize_csv_value(track.get("title") or "")

        # 3. Artist
        artist = sanitize_csv_value(track.get("artist") or "")

        # 4. Album
        album = sanitize_csv_value(track.get("album") or "")

        # 5. URL
        url = sanitize_csv_value(track.get("url") or "")

        # 6. Tags
        tags = sanitize_csv_value(format_list_field(track.get("tags")))

        # 7. Genres
        genres = sanitize_csv_value(format_list_field(track.get("genres")))

        # 8. Moods
        moods = sanitize_csv_value(format_list_field(track.get("moods")))

        # 9. Contexts
        contexts = sanitize_csv_value(format_list_field(track.get("contexts")))

        # 10. Match Score
        match_score = format_numeric_score(track.get("match_score"))

        # 11. Hybrid Score
        hybrid_score = format_numeric_score(track.get("hybrid_score"))

        # 12. Diversity Adjustment
        diversity_adj = format_numeric_score(track.get("diversity_adjustment"))

        # 13. Final Recommendation Score
        final_score = format_numeric_score(
            track.get("sounddeck_score")
            if track.get("sounddeck_score") is not None
            else track.get("relevance_score")
        )

        # 14. Explanation
        explanation = sanitize_csv_value(track.get("explanation") or "")

        row = [
            pos,
            title,
            artist,
            album,
            url,
            tags,
            genres,
            moods,
            contexts,
            match_score,
            hybrid_score,
            diversity_adj,
            final_score,
            explanation,
        ]
        writer.writerow(row)

    return output.getvalue()
