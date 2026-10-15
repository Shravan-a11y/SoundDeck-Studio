import logging
from typing import Optional, Any

from app.services.tag_classifier import classify_tags

logger = logging.getLogger("sounddeck.analytics")


def calculate_playlist_analytics(
    tracks: list[dict[str, Any]],
    unmet_constraints: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Calculate deterministic, comprehensive analytics for a curated SoundDeck playlist.

    Metrics calculated:
    - total_tracks: Total track count.
    - unique_artists: Count of distinct artists (case-insensitive).
    - artist_distribution: Frequency count per artist (descending).
    - repetition_ratio: Fraction of tracks belonging to artists already encountered
      earlier in playlist sequence order (repetition_ratio = repeat_tracks / total_tracks).
    - genre_distribution: Count of tracks featuring each genre tag.
    - mood_distribution: Count of tracks featuring each mood tag.
    - duplicate_track_count: Number of duplicate track entries by title and artist.
    - metadata_coverage: Fraction of tracks with tags/metadata available.
    - average_hybrid_score: Mean hybrid score across tracks with numeric scores.
    - average_recommendation_score: Mean final sounddeck/relevance score.
    - unmet_constraints: Forwarded list of constraints that could not be satisfied.
    - notes: Contextual explanations regarding community tag completeness.
    """
    total_tracks = len(tracks)

    if total_tracks == 0:
        return {
            "total_tracks": 0,
            "unique_artists": 0,
            "artist_distribution": {},
            "repetition_ratio": 0.0,
            "genre_distribution": {},
            "mood_distribution": {},
            "duplicate_track_count": 0,
            "metadata_coverage": 0.0,
            "average_hybrid_score": None,
            "average_recommendation_score": None,
            "unmet_constraints": list(unmet_constraints or []),
            "notes": [
                "Playlist is empty. All count distributions and ratios are zero.",
                "Community tags from Last.fm may be incomplete or subjective for niche tracks.",
                "No BPM, acoustic energy, or musical key data is claimed without direct audio analysis.",
            ],
        }

    # 1. Artist Metrics & Repetition Ratio
    seen_artists: set[str] = set()
    repeat_tracks_count = 0
    artist_counts: dict[str, int] = {}
    valid_artist_keys: set[str] = set()

    for track in tracks:
        raw_artist = str(track.get("artist") or "").strip()
        if raw_artist:
            art_key = raw_artist.casefold()
            valid_artist_keys.add(art_key)
            # Display canonical name (first appearance or title)
            display_name = raw_artist
            # Store in artist_counts using display name
            found_key = None
            for k in artist_counts:
                if k.casefold() == art_key:
                    found_key = k
                    break
            if found_key:
                artist_counts[found_key] += 1
            else:
                artist_counts[display_name] = 1

            if art_key in seen_artists:
                repeat_tracks_count += 1
            else:
                seen_artists.add(art_key)
        else:
            # Missing or empty artist name
            artist_counts["[Unknown Artist]"] = artist_counts.get("[Unknown Artist]", 0) + 1

    unique_artists = len(valid_artist_keys)
    repetition_ratio = round(repeat_tracks_count / total_tracks, 4)

    # Sort artist distribution descending by count
    sorted_artists = dict(
        sorted(artist_counts.items(), key=lambda item: item[1], reverse=True)
    )

    # 2. Genre and Mood Distributions
    genre_counts: dict[str, int] = {}
    mood_counts: dict[str, int] = {}
    tracks_with_metadata = 0

    for track in tracks:
        track_genres = track.get("genres")
        track_moods = track.get("moods")
        raw_tags = track.get("tags") or []

        # If genres or moods not pre-classified, classify from tags
        if (track_genres is None or track_moods is None) and raw_tags:
            classified = classify_tags(raw_tags)
            if track_genres is None:
                track_genres = classified.get("genres", [])
            if track_moods is None:
                track_moods = classified.get("moods", [])

        if track_genres:
            for g in track_genres:
                g_clean = str(g).strip().lower()
                if g_clean:
                    genre_counts[g_clean] = genre_counts.get(g_clean, 0) + 1

        if track_moods:
            for m in track_moods:
                m_clean = str(m).strip().lower()
                if m_clean:
                    mood_counts[m_clean] = mood_counts.get(m_clean, 0) + 1

        # Check metadata availability
        has_metadata = bool(
            track.get("metadata_enriched") is True
            or raw_tags
            or track_genres
            or track_moods
        )
        if has_metadata:
            tracks_with_metadata += 1

    metadata_coverage = round(tracks_with_metadata / total_tracks, 4)

    sorted_genres = dict(
        sorted(genre_counts.items(), key=lambda item: item[1], reverse=True)
    )
    sorted_moods = dict(
        sorted(mood_counts.items(), key=lambda item: item[1], reverse=True)
    )

    # 3. Duplicate Tracks Detection
    seen_track_keys: set[tuple[str, str]] = set()
    duplicate_track_count = 0

    for track in tracks:
        t_title = str(track.get("title") or "").strip().casefold()
        t_artist = str(track.get("artist") or "").strip().casefold()
        if t_title or t_artist:
            key = (t_title, t_artist)
            if key in seen_track_keys:
                duplicate_track_count += 1
            else:
                seen_track_keys.add(key)

    # 4. Score Averages
    hybrid_scores = [
        float(t["hybrid_score"])
        for t in tracks
        if t.get("hybrid_score") is not None
        and isinstance(t.get("hybrid_score"), (int, float))
    ]
    avg_hybrid_score = (
        round(sum(hybrid_scores) / len(hybrid_scores), 4)
        if hybrid_scores
        else None
    )

    recommendation_scores = []
    for t in tracks:
        score = t.get("sounddeck_score")
        if score is None:
            score = t.get("relevance_score")
        if score is not None and isinstance(score, (int, float)):
            recommendation_scores.append(float(score))

    avg_rec_score = (
        round(sum(recommendation_scores) / len(recommendation_scores), 4)
        if recommendation_scores
        else None
    )

    notes = [
        "Artist repetition ratio is calculated as tracks belonging to artists already encountered earlier in playlist order divided by total tracks.",
        "Genre and mood distributions reflect Last.fm community tags; coverage may vary for niche or unindexed recordings.",
        "Acoustic features such as BPM, key, and raw audio energy are omitted as they are not provided by metadata APIs.",
    ]

    return {
        "total_tracks": total_tracks,
        "unique_artists": unique_artists,
        "artist_distribution": sorted_artists,
        "repetition_ratio": repetition_ratio,
        "genre_distribution": sorted_genres,
        "mood_distribution": sorted_moods,
        "duplicate_track_count": duplicate_track_count,
        "metadata_coverage": metadata_coverage,
        "average_hybrid_score": avg_hybrid_score,
        "average_recommendation_score": avg_rec_score,
        "unmet_constraints": list(unmet_constraints or []),
        "notes": notes,
    }
