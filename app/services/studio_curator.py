import uuid
import logging
from typing import Optional

import httpx

from app.schemas import PlaylistConstraints
from app.services.ollama_service import (
    parse_playlist_request,
    get_ollama_config,
    OllamaConnectionError,
    OllamaTimeoutError,
    OllamaModelNotFoundError,
    OllamaResponseValidationError,
    OllamaServiceError,
)
from app.services.lastfm import get_similar_tracks, rank_tracks
from app.services.musicbrainz import search_tracks
from app.services.music_intelligence import (
    get_track_tags,
    get_artist_tags,
    enrich_candidate_with_intelligence,
    read_cache,
    lastfm_request,
)
from app.services.tag_classifier import (
    classify_tags,
    single_tag_similarity,
    GENRE_TAGS,
    MOOD_TAGS,
    CONTEXT_TAGS,
)
from app.services.analytics import calculate_playlist_analytics

logger = logging.getLogger("sounddeck.studio_curator")


def extract_classifier_tags(raw_tags: list[str], allowed_set: set[str]) -> list[str]:
    """
    Map and expand raw user or model tags into recognized classifier tags.
    Handles hyphenation, sub-phrase matching, and basic suffix stemming.
    """
    result: list[str] = []
    for raw in raw_tags or []:
        if not raw or not isinstance(raw, str):
            continue
        cleaned = " ".join(raw.lower().replace("-", " ").split())
        matched = False

        if cleaned in allowed_set:
            result.append(cleaned)
            matched = True

        # Multi-word tag match inside string (e.g. "late night" in "late night studying")
        for allowed in allowed_set:
            if " " in allowed and allowed in cleaned and allowed not in result:
                result.append(allowed)
                matched = True

        # Single word check and stemming
        for w in cleaned.split():
            if w in allowed_set and w not in result:
                result.append(w)
                matched = True
            elif w.endswith("ing"):
                stem = w[:-3]
                if stem in allowed_set and stem not in result:
                    result.append(stem)
                    matched = True

        # Preserve the cleaned tag even if not in standard vocabulary
        if not matched and cleaned not in result:
            result.append(cleaned)

    return list(dict.fromkeys(result))


def generate_track_explanation(track: dict, constraints: PlaylistConstraints) -> str:
    """Generate an explanation grounded in real metadata match and scoring."""
    matched_genres = [
        g for g in track.get("genres", [])
        if any(single_tag_similarity(tg, g) >= 0.5 or tg in g or g in tg for tg in constraints.target_genres)
    ]
    matched_moods = [
        m for m in track.get("moods", [])
        if any(single_tag_similarity(tm, m) >= 0.5 or tm in m or m in tm for tm in constraints.target_moods)
    ]
    matched_contexts = [
        c for c in track.get("contexts", [])
        if any(single_tag_similarity(tc, c) >= 0.5 or tc in c or c in tc for tc in constraints.target_contexts)
    ]

    parts = []
    if matched_genres:
        parts.append(f"genre '{'/'.join(matched_genres[:3])}'")
    if matched_moods:
        parts.append(f"mood '{'/'.join(matched_moods[:2])}'")
    if matched_contexts:
        parts.append(f"context '{'/'.join(matched_contexts[:2])}'")

    sounddeck_score = track.get("sounddeck_score", 0.0)
    relevance = track.get("relevance_score", 0.0)

    if parts:
        explanation = f"Matches requested {', '.join(parts)} (relevance: {relevance:.2f}, score: {sounddeck_score:.2f})"
    elif constraints.seed_artist and track.get("artist", "").casefold() == constraints.seed_artist.casefold():
        explanation = f"Seed artist track establishing core playlist aesthetic (relevance: {relevance:.2f}, score: {sounddeck_score:.2f})"
    elif track.get("match_score", 0.0) >= 0.75:
        explanation = f"Strong acoustic similarity match to seed reference (match: {track['match_score']:.2f}, score: {sounddeck_score:.2f})"
    else:
        explanation = f"Acoustic/musical similarity match from recommendation engine (score: {sounddeck_score:.2f})"

    if track.get("diversity_adjustment", 0.0) > 0:
        penalty = track["diversity_adjustment"]
        explanation += f"; repeat-artist diversity penalty applied (-{penalty:.2f})"

    return explanation


async def get_top_tracks_by_tag(tag: str, limit: int = 50) -> list[dict]:
    """Retrieve top tracks for a genre or mood tag from Last.fm."""
    try:
        data = await lastfm_request({
            "method": "tag.getTopTracks",
            "tag": tag.strip().casefold(),
            "limit": limit,
            "autocorrect": 1,
        })
        tracks_data = data.get("tracks", {}).get("track", [])
        if isinstance(tracks_data, dict):
            tracks_data = [tracks_data]

        candidates = []
        for rank_idx, item in enumerate(tracks_data):
            artist_data = item.get("artist", {})
            artist_name = artist_data.get("name", "") if isinstance(artist_data, dict) else str(artist_data)
            title = item.get("name", "")
            if not title or not artist_name:
                continue

            decay = max(0.60, 0.95 - (rank_idx * 0.007))
            candidates.append({
                "title": title,
                "artist": artist_name,
                "match_score": round(decay, 4),
                "url": item.get("url"),
            })
        return candidates
    except Exception as exc:
        logger.warning("Last.fm tag.getTopTracks failed for '%s': %s", tag, exc)
        return []


async def resolve_seed_track_for_artist(artist_name: str) -> Optional[str]:
    """Find a representative track for a seed artist via MusicBrainz or Last.fm."""
    # 1. Try MusicBrainz search
    try:
        mb_results = await search_tracks(artist_name, limit=10)
        target_art = artist_name.strip().casefold()
        for rec in mb_results:
            artists = [a.casefold() for a in rec.get("artists", [])]
            if target_art in artists or any(target_art in a for a in artists):
                if rec.get("title"):
                    return rec["title"]
        if mb_results and mb_results[0].get("title"):
            return mb_results[0]["title"]
    except Exception as exc:
        logger.warning("MusicBrainz search failed for artist '%s': %s", artist_name, exc)

    # 2. Fallback to Last.fm artist.getTopTracks
    try:
        data = await lastfm_request({
            "method": "artist.getTopTracks",
            "artist": artist_name,
            "limit": 5,
            "autocorrect": 1
        })
        top_tracks = data.get("toptracks", {}).get("track", [])
        if isinstance(top_tracks, dict):
            top_tracks = [top_tracks]
        if top_tracks and isinstance(top_tracks[0], dict):
            return top_tracks[0].get("name")
    except Exception as exc:
        logger.warning("Last.fm artist.getTopTracks failed for '%s': %s", artist_name, exc)

    return None


async def retrieve_candidates(
    constraints: PlaylistConstraints,
) -> tuple[list[dict], Optional[dict], list[str]]:
    """
    Retrieve candidate tracks from Last.fm and MusicBrainz based on interpreted constraints.
    Returns: (candidates_list, seed_info_dict, unmet_constraints_list)
    """
    candidates: list[dict] = []
    unmet: list[str] = []
    seed_info: Optional[dict] = None

    seed_artist = constraints.seed_artist
    seed_track = constraints.seed_track

    # Case 1: Both seed artist and seed track are provided
    if seed_artist and seed_track:
        seed_info = {"artist": seed_artist, "track": seed_track}
        similars = await get_similar_tracks(seed_artist, seed_track, limit=50)
        candidates.append({
            "title": seed_track,
            "artist": seed_artist,
            "match_score": 1.0,
            "url": None,
        })
        candidates.extend(similars)

    # Case 2: Seed artist only (no seed track)
    elif seed_artist and not seed_track:
        resolved_track = await resolve_seed_track_for_artist(seed_artist)
        if resolved_track:
            seed_info = {"artist": seed_artist, "track": resolved_track}
            similars = await get_similar_tracks(seed_artist, resolved_track, limit=50)
            candidates.append({
                "title": resolved_track,
                "artist": seed_artist,
                "match_score": 1.0,
                "url": None,
            })
            candidates.extend(similars)
        else:
            unmet.append(f"Could not find catalog tracks for seed artist '{seed_artist}'.")

    # Case 3: Seed track only (no seed artist)
    elif seed_track and not seed_artist:
        resolved_artist = None
        try:
            mb_results = await search_tracks(seed_track, limit=5)
            if mb_results and mb_results[0].get("artists"):
                resolved_artist = mb_results[0]["artists"][0]
        except Exception as exc:
            logger.warning("MusicBrainz search failed for track '%s': %s", seed_track, exc)

        if resolved_artist:
            seed_info = {"artist": resolved_artist, "track": seed_track}
            similars = await get_similar_tracks(resolved_artist, seed_track, limit=50)
            candidates.append({
                "title": seed_track,
                "artist": resolved_artist,
                "match_score": 1.0,
                "url": None,
            })
            candidates.extend(similars)
        else:
            unmet.append(f"Could not resolve artist for seed track '{seed_track}'.")

    # Case 4: No seed artist or track (or seed resolution yielded no candidates)
    if not candidates:
        primary_tags = constraints.target_genres or constraints.target_moods or constraints.target_contexts
        if primary_tags:
            for ptag in primary_tags[:2]:
                tag_tracks = await get_top_tracks_by_tag(ptag, limit=35)
                if tag_tracks:
                    candidates.extend(tag_tracks)
                    if not seed_info:
                        seed_info = {"artist": tag_tracks[0]["artist"], "track": tag_tracks[0]["title"]}

        # If tag.getTopTracks yielded no candidates or API error, fallback to MusicBrainz
        if not candidates:
            query_terms = constraints.target_genres + constraints.target_moods + constraints.target_contexts
            query = " ".join(query_terms).strip() or "indie"
            try:
                mb_results = await search_tracks(query, limit=20)
                for rec in mb_results:
                    art = rec.get("artists", ["Unknown"])[0] if rec.get("artists") else "Unknown"
                    candidates.append({
                        "title": rec.get("title", ""),
                        "artist": art,
                        "match_score": 0.8,
                        "url": None,
                    })

                if mb_results and mb_results[0].get("artists") and mb_results[0].get("title"):
                    top_art = mb_results[0]["artists"][0]
                    top_title = mb_results[0]["title"]
                    seed_info = {"artist": top_art, "track": top_title}
                    try:
                        similars = await get_similar_tracks(top_art, top_title, limit=30)
                        candidates.extend(similars)
                    except Exception as exc:
                        logger.warning("Last.fm get_similar_tracks failed during genre expansion: %s", exc)
            except Exception as exc:
                logger.warning("MusicBrainz search failed for query '%s': %s", query, exc)

    # Deduplicate candidates
    seen = set()
    deduped: list[dict] = []
    for item in candidates:
        title = str(item.get("title", "")).strip()
        artist = str(item.get("artist", "")).strip()
        if not title or not artist:
            continue
        key = (artist.casefold(), title.casefold())
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped, seed_info, unmet


async def curate_playlist(
    prompt: str,
    limit: Optional[int] = None,
    max_per_artist: Optional[int] = None,
    diversity_weight: Optional[float] = None,
    metadata_limit: int = 15,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> dict:
    """
    Curate a playlist from a natural-language request by connecting
    the local Ollama model to the SoundDeck recommendation engine.
    """
    # 1. AI Constraint Extraction
    base_url_cfg, model_cfg = get_ollama_config()
    target_base = base_url or base_url_cfg
    target_model = model or model_cfg

    constraints = await parse_playlist_request(
        prompt=prompt,
        base_url=target_base,
        model=target_model,
        client=client,
    )

    # Apply explicit overrides from request
    if limit is not None:
        constraints.limit = limit
    if max_per_artist is not None:
        constraints.max_per_artist = max_per_artist
    if diversity_weight is not None:
        constraints.diversity_weight = diversity_weight

    # 2. Extract and expand target tags against recognized classifier vocabulary
    target_genres = extract_classifier_tags(constraints.target_genres, GENRE_TAGS)
    target_moods = extract_classifier_tags(constraints.target_moods, MOOD_TAGS)
    target_contexts = extract_classifier_tags(constraints.target_contexts, CONTEXT_TAGS)

    # 3. Retrieve Candidate Tracks
    candidates, seed_info, unmet_constraints = await retrieve_candidates(constraints)

    if not candidates:
        unmet_constraints.append("No candidate tracks found matching the requested criteria.")
        playlist_id = f"sd-{uuid.uuid4().hex[:12]}"
        analytics = calculate_playlist_analytics([], unmet_constraints=unmet_constraints)
        return {
            "playlist_id": playlist_id,
            "interpreted_request": constraints.model_dump(),
            "tracks": [],
            "summary": {
                "track_count": 0,
                "unique_artist_count": 0,
                "unmet_constraints": unmet_constraints,
            },
            "analytics": analytics,
        }

    # 4. Formulate effective seed profile tags for hybrid scoring
    seed_track_tags: list[str] = []
    if seed_info and seed_info.get("artist") and seed_info.get("track"):
        try:
            seed_track_tags = await get_track_tags(seed_info["artist"], seed_info["track"])
        except Exception as exc:
            logger.debug("Could not retrieve tags for seed track: %s", exc)

    seed_track_classification = classify_tags(seed_track_tags) if seed_track_tags else {}

    # Blend explicit target tags with seed track tags so seed aesthetics are preserved
    seed_genres = seed_track_classification.get("genres", [])
    effective_genres = list(dict.fromkeys(target_genres + [g for g in seed_genres if g not in target_genres]))
    seed_moods = seed_track_classification.get("moods", [])
    effective_moods = list(dict.fromkeys(target_moods + [m for m in seed_moods if m not in target_moods]))
    seed_contexts = seed_track_classification.get("contexts", [])
    effective_contexts = list(dict.fromkeys(target_contexts + [c for c in seed_contexts if c not in target_contexts]))

    effective_seed_tags = effective_genres + effective_moods + effective_contexts

    # 5. Candidate Metadata Enrichment & Cache Reuse
    enriched_candidates = []
    uncached_fetches = 0

    for candidate in candidates:
        cand_artist = candidate.get("artist", "").strip()
        cand_title = candidate.get("title", "").strip()

        track_cache_key = f"track:{cand_artist.casefold()}:{cand_title.casefold()}"
        cached_tags = read_cache(track_cache_key)

        cand_tags: list[str] = []
        cand_artist_tags: list[str] = []

        if cached_tags is not None:
            cand_tags = cached_tags
        elif uncached_fetches < metadata_limit:
            try:
                cand_tags = await get_track_tags(cand_artist, cand_title)
                uncached_fetches += 1
            except Exception:
                cand_tags = []

        # If track tags are missing, check artist tags
        if not cand_tags:
            artist_cache_key = f"artist:{cand_artist.casefold()}"
            cached_artist = read_cache(artist_cache_key)
            if cached_artist is not None:
                cand_artist_tags = cached_artist
            elif uncached_fetches < metadata_limit:
                try:
                    cand_artist_tags = await get_artist_tags(cand_artist)
                    uncached_fetches += 1
                except Exception:
                    cand_artist_tags = []

        # Enrich candidate using existing SoundDeck intelligence
        enriched = enrich_candidate_with_intelligence(
            candidate=candidate,
            seed_tags=effective_seed_tags,
            candidate_tags=cand_tags,
            candidate_artist_tags=cand_artist_tags,
        )

        if "hybrid_score" not in enriched:
            enriched["hybrid_score"] = float(enriched.get("match_score", 0.0))

        enriched_candidates.append(enriched)

    # 5b. Filter out excluded artists and genres
    excluded_artists = {a.casefold().strip() for a in (constraints.exclude_artists or []) if a and a.strip()}
    excluded_genres = {g.casefold().strip() for g in (constraints.exclude_genres or []) if g and g.strip()}

    filtered_candidates = []
    excluded_count = 0

    for cand in enriched_candidates:
        cand_art = cand.get("artist", "").casefold().strip()
        if any(ea == cand_art or ea in cand_art for ea in excluded_artists):
            excluded_count += 1
            continue

        cand_genres = {g.casefold().strip() for g in cand.get("genres", [])}
        cand_tags = {t.casefold().strip() for t in cand.get("tags", [])}
        all_descriptors = cand_genres | cand_tags

        is_genre_excluded = False
        for eg in excluded_genres:
            if any(eg == desc or eg in desc for desc in all_descriptors):
                is_genre_excluded = True
                break

        if is_genre_excluded:
            excluded_count += 1
            continue

        filtered_candidates.append(cand)

    if excluded_count > 0:
        unmet_constraints.append(
            f"Filtered out {excluded_count} candidate track(s) matching excluded artists or genres."
        )

    # 6. Apply SoundDeck Diversity Ranking
    playlist = rank_tracks(
        candidates=filtered_candidates,
        limit=constraints.limit,
        max_per_artist=constraints.max_per_artist or 2,
        diversity_weight=constraints.diversity_weight,
        score_field="hybrid_score",
    )

    # 7. Add Explanations
    for track in playlist:
        track["explanation"] = generate_track_explanation(track, constraints)

    # 8. Unmet Constraints Analysis
    if len(playlist) < constraints.limit:
        unmet_constraints.append(
            f"Requested {constraints.limit} tracks, but only {len(playlist)} valid tracks satisfied all criteria and artist diversity limits."
        )

    all_playlist_genres = {g for t in playlist for g in t.get("genres", [])}
    for g in constraints.target_genres:
        g_clean = g.lower()
        if not any(g_clean in pg or pg in g_clean for pg in all_playlist_genres):
            unmet_constraints.append(f"Target genre '{g}' was not present in the catalog metadata of selected tracks.")

    all_playlist_moods = {m for t in playlist for m in t.get("moods", [])}
    for m in constraints.target_moods:
        m_clean = m.lower()
        if not any(m_clean in pm or pm in m_clean for pm in all_playlist_moods):
            unmet_constraints.append(f"Target mood '{m}' was not present in the catalog metadata of selected tracks.")

    all_playlist_contexts = {c for t in playlist for c in t.get("contexts", [])}
    for c in constraints.target_contexts:
        c_clean = c.lower()
        if not any(c_clean in pc or pc in c_clean for pc in all_playlist_contexts):
            unmet_constraints.append(f"Target context '{c}' was not present in the catalog metadata of selected tracks.")

    unique_artists = len({t["artist"].casefold() for t in playlist})
    playlist_id = f"sd-{uuid.uuid4().hex[:12]}"
    deduped_unmet = list(dict.fromkeys(unmet_constraints))
    analytics = calculate_playlist_analytics(playlist, unmet_constraints=deduped_unmet)

    return {
        "playlist_id": playlist_id,
        "interpreted_request": constraints.model_dump(),
        "tracks": playlist,
        "summary": {
            "track_count": len(playlist),
            "unique_artist_count": unique_artists,
            "unmet_constraints": deduped_unmet,
        },
        "analytics": analytics,
    }
