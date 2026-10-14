import logging
import httpx

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query

load_dotenv(override=True)

from app.services.musicbrainz import search_tracks
from app.services.lastfm import get_similar_tracks, rank_tracks
from app.services.music_intelligence import (
    get_track_tags,
    enrich_candidate_with_intelligence,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sounddeck")

app = FastAPI(
    title="SoundDeck",
    description="AI-powered music discovery and playlist intelligence",
    version="0.6.0",
)


@app.get("/")
async def root():
    return {
        "name": "SoundDeck",
        "status": "running",
        "version": "0.6.0",
    }


@app.get("/api/tracks/search")
async def find_tracks(
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=10, ge=1, le=25),
):
    try:
        tracks = await search_tracks(q, limit)

        return {
            "query": q,
            "count": len(tracks),
            "tracks": tracks,
        }

    except httpx.HTTPError as exc:
        logger.exception("MusicBrainz request failed")
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve music metadata",
        ) from exc


@app.get("/api/playlists/generate")
async def generate_playlist(
    artist: str = Query(min_length=1, max_length=200),
    track: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=20, ge=1, le=50),
    max_per_artist: int = Query(default=2, ge=1, le=10),
    diversity_weight: float = Query(default=0.15, ge=0, le=1),
    metadata_limit: int = Query(default=10, ge=0, le=15),
):
    try:
        seed_tags = await get_track_tags(artist, track)

        candidates = await get_similar_tracks(
            artist=artist,
            track=track,
            limit=50,
        )

        enriched_candidates = []
        enriched_count = 0

        for index, candidate in enumerate(candidates):
            if index < metadata_limit and seed_tags:
                try:
                    candidate_tags = await get_track_tags(
                        candidate["artist"],
                        candidate["title"],
                    )

                    enriched = enrich_candidate_with_intelligence(
                        candidate=candidate,
                        seed_tags=seed_tags,
                        candidate_tags=candidate_tags,
                    )

                    enriched_candidates.append(enriched)
                    enriched_count += 1

                except (ValueError, httpx.HTTPError):
                    logger.warning(
                        "Metadata enrichment failed for %s - %s",
                        candidate.get("artist"),
                        candidate.get("title"),
                        exc_info=True,
                    )
                    enriched_candidates.append(candidate)

            else:
                enriched_candidates.append(candidate)

        # Candidates without enriched metadata retain their Last.fm score.
        for candidate in enriched_candidates:
            if "hybrid_score" not in candidate:
                candidate["hybrid_score"] = candidate.get(
                    "match_score", 0.0
                )

        playlist = rank_tracks(
            candidates=enriched_candidates,
            limit=limit,
            max_per_artist=max_per_artist,
            diversity_weight=diversity_weight,
            score_field="hybrid_score",
        )

        return {
            "seed": {
                "artist": artist,
                "track": track,
                "tags": seed_tags,
            },
            "count": len(playlist),
            "method": "SoundDeck genre, mood, context, relevance and diversity ranking",
            "scoring_weights": {
                "lastfm": 0.60,
                "genre": 0.20,
                "mood": 0.15,
                "context": 0.05,
            },
            "settings": {
                "max_per_artist": max_per_artist,
                "diversity_weight": diversity_weight,
                "metadata_limit": metadata_limit,
                "enriched_tracks": enriched_count,
            },
            "playlist": playlist,
        }

    except RuntimeError as exc:
        logger.exception("SoundDeck configuration error")
        raise HTTPException(
            status_code=503,
            detail="Recommendation service configuration error",
        ) from exc

    except ValueError as exc:
        logger.exception("Recommendation provider returned an error")
        raise HTTPException(
            status_code=502,
            detail="Recommendation provider returned an error",
        ) from exc

    except httpx.HTTPError as exc:
        logger.exception("Recommendation request failed")
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve related tracks",
        ) from exc
