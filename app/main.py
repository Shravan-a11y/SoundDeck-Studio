import logging
import httpx

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Response

load_dotenv(override=True)

from app.schemas import (
    PlaylistParseRequest,
    PlaylistParseResponse,
    StudioCurateRequest,
    StudioCurateResponse,
    StudioExportRequest,
)
from app.services.ollama_service import (
    parse_playlist_request,
    get_ollama_config,
    check_ollama_health,
    OllamaConnectionError,
    OllamaTimeoutError,
    OllamaModelNotFoundError,
    OllamaResponseValidationError,
    OllamaServiceError,
)
from app.services.musicbrainz import search_tracks
from app.services.lastfm import get_similar_tracks, rank_tracks
from app.services.music_intelligence import (
    get_track_tags,
    enrich_candidate_with_intelligence,
)
from app.services.studio_curator import curate_playlist
from app.services.export import export_playlist_to_csv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sounddeck")

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="SoundDeck Studio",
    description="Local-AI-powered music curation application for independent DJs and event organizers",
    version="0.7.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "name": "SoundDeck Studio",
        "status": "running",
        "version": "0.7.0",
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


@app.get("/api/ai/status")
async def get_ai_status():
    """Check connectivity and model availability for the local Ollama service."""
    base_url, model = get_ollama_config()
    try:
        data = await check_ollama_health(base_url)
        installed_models = [
            m.get("name") for m in data.get("models", []) if isinstance(m, dict)
        ]
        return {
            "status": "connected",
            "base_url": base_url,
            "configured_model": model,
            "model_available": any(
                m == model or m.startswith(f"{model}:") for m in installed_models
            ),
            "installed_models": installed_models,
        }
    except OllamaConnectionError as exc:
        return {
            "status": "disconnected",
            "base_url": base_url,
            "configured_model": model,
            "error": str(exc),
        }
    except Exception as exc:
        return {
            "status": "error",
            "base_url": base_url,
            "configured_model": model,
            "error": str(exc),
        }


@app.post("/api/ai/parse-playlist-request", response_model=PlaylistParseResponse)
async def parse_playlist_request_endpoint(payload: PlaylistParseRequest):
    """
    Parse a natural-language DJ/event playlist request into validated structured constraints
    using the local Ollama open-weight model.
    """
    base_url, model = get_ollama_config()
    try:
        constraints = await parse_playlist_request(
            prompt=payload.prompt,
            base_url=base_url,
            model=model,
        )
        return PlaylistParseResponse(
            constraints=constraints,
            model=model,
        )
    except OllamaConnectionError as exc:
        logger.warning("Ollama connection error: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Local AI service unavailable: {exc}",
        ) from exc
    except OllamaModelNotFoundError as exc:
        logger.warning("Ollama model not found: %s", exc)
        raise HTTPException(
            status_code=404,
            detail=f"Configured model not found: {exc}",
        ) from exc
    except OllamaTimeoutError as exc:
        logger.warning("Ollama request timed out: %s", exc)
        raise HTTPException(
            status_code=504,
            detail=f"Local AI request timed out: {exc}",
        ) from exc
    except OllamaResponseValidationError as exc:
        logger.error("Ollama response validation failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"AI model returned invalid constraints: {exc}",
        ) from exc
    except OllamaServiceError as exc:
        logger.exception("Ollama service error")
        raise HTTPException(
            status_code=502,
            detail=f"Local AI service error: {exc}",
        ) from exc


@app.post("/api/studio/curate", response_model=StudioCurateResponse)
async def studio_curate_endpoint(payload: StudioCurateRequest):
    """
    Curate an intelligent, ranked playlist using natural language interpreted by
    the local Ollama model and filtered/ranked by SoundDeck's recommendation engine.
    """
    try:
        result = await curate_playlist(
            prompt=payload.prompt,
            limit=payload.limit,
            max_per_artist=payload.max_per_artist,
            diversity_weight=payload.diversity_weight,
        )
        return result
    except OllamaConnectionError as exc:
        logger.warning("Ollama connection error in studio curate: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Local AI service unavailable: {exc}",
        ) from exc
    except OllamaModelNotFoundError as exc:
        logger.warning("Ollama model not found in studio curate: %s", exc)
        raise HTTPException(
            status_code=404,
            detail=f"Configured model not found: {exc}",
        ) from exc
    except OllamaTimeoutError as exc:
        logger.warning("Ollama request timed out in studio curate: %s", exc)
        raise HTTPException(
            status_code=504,
            detail=f"Local AI request timed out: {exc}",
        ) from exc
    except OllamaResponseValidationError as exc:
        logger.error("Ollama response validation failed in studio curate: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"AI model returned invalid constraints: {exc}",
        ) from exc
    except OllamaServiceError as exc:
        logger.exception("Ollama service error in studio curate")
        raise HTTPException(
            status_code=502,
            detail=f"Local AI service error: {exc}",
        ) from exc
    except RuntimeError as exc:
        logger.exception("SoundDeck configuration error in studio curate")
        raise HTTPException(
            status_code=503,
            detail=f"Recommendation service configuration error: {exc}",
        ) from exc
    except ValueError as exc:
        logger.exception("Recommendation provider returned an error in studio curate")
        raise HTTPException(
            status_code=502,
            detail=f"Recommendation provider returned an error: {exc}",
        ) from exc
    except httpx.HTTPError as exc:
        logger.exception("Recommendation request failed in studio curate")
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve music metadata from external service",
        ) from exc


@app.post("/api/studio/export.csv")
async def export_studio_playlist_csv(payload: StudioExportRequest):
    """
    Export a curated playlist to CSV with formula injection protection
    and complete metadata/scoring columns.
    """
    csv_text = export_playlist_to_csv(payload.tracks)
    safe_id = "".join(
        c for c in (payload.playlist_id or "sounddeck-playlist")
        if c.isalnum() or c in ("-", "_")
    ).strip() or "sounddeck-playlist"

    filename = f"{safe_id}.csv"
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )

