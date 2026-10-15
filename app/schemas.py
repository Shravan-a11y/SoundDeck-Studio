from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


def normalize_string_list(items: Optional[List[str]]) -> List[str]:
    """Normalize a list of tag strings: deduplicate, strip, lowercase, filter blanks."""
    if not items:
        return []
    cleaned: list[str] = []
    seen = set()
    for item in items:
        if isinstance(item, str):
            val = " ".join(item.strip().casefold().split())
            if val and val not in seen and len(val) <= 100:
                seen.add(val)
                cleaned.append(val)
    return cleaned[:30]


class PlaylistConstraints(BaseModel):
    seed_artist: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Seed artist name if mentioned or inferred"
    )
    seed_track: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Seed track title if mentioned or inferred"
    )
    target_genres: List[str] = Field(
        default_factory=list,
        description="Target musical genres (e.g. indie, rock, ambient)"
    )
    target_moods: List[str] = Field(
        default_factory=list,
        description="Target moods/vibes (e.g. calm, melancholic, energetic)"
    )
    target_contexts: List[str] = Field(
        default_factory=list,
        description="Target contexts (e.g. studying, late night, workout)"
    )
    exclude_genres: List[str] = Field(
        default_factory=list,
        description="Genres to explicitly avoid or exclude"
    )
    exclude_artists: List[str] = Field(
        default_factory=list,
        description="Artists to explicitly avoid or exclude"
    )
    limit: int = Field(
        default=20,
        ge=5,
        le=50,
        description="Playlist size, between 5 and 50"
    )
    max_per_artist: Optional[int] = Field(
        default=2,
        ge=1,
        le=10,
        description="Maximum tracks allowed per artist"
    )
    diversity_weight: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Artist diversity penalty weight, between 0.0 and 1.0"
    )

    @field_validator("seed_artist", "seed_track", mode="before")
    @classmethod
    def clean_optional_str(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            val = v.strip()
            if not val or val.lower() in ("null", "none"):
                return None
            return val
        return str(v).strip() or None

    @field_validator(
        "target_genres", "target_moods", "target_contexts",
        "exclude_genres", "exclude_artists", mode="before"
    )
    @classmethod
    def clean_tag_lists(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            items = [item.strip() for item in v.split(",") if item.strip()]
            return normalize_string_list(items)
        if isinstance(v, list):
            return normalize_string_list(v)
        return []

    @field_validator("diversity_weight", mode="before")
    @classmethod
    def clean_diversity_weight(cls, v):
        if v is None:
            return 0.2
        if isinstance(v, str):
            v_lower = v.strip().lower()
            if "high" in v_lower or "max" in v_lower:
                return 0.8
            elif "med" in v_lower:
                return 0.5
            elif "low" in v_lower or "min" in v_lower:
                return 0.1
            try:
                return float(v_lower)
            except ValueError:
                return 0.2
        return v

    @field_validator("limit", mode="before")
    @classmethod
    def clean_limit(cls, v):
        if v is None:
            return 20
        return v

    @field_validator("max_per_artist", mode="before")
    @classmethod
    def clean_max_per_artist(cls, v):
        if v is None:
            return 2
        return v


class PlaylistParseRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural language playlist or vibe request"
    )


class PlaylistParseResponse(BaseModel):
    constraints: PlaylistConstraints
    model: str


class StudioCurateRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural language playlist or vibe request"
    )
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        le=50,
        description="Optional playlist size limit between 1 and 50"
    )
    max_per_artist: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="Optional maximum tracks allowed per artist"
    )
    diversity_weight: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional artist diversity penalty weight between 0.0 and 1.0"
    )


class StudioCurateSummary(BaseModel):
    track_count: int = Field(default=0, description="Total number of tracks in curated playlist")
    unique_artist_count: int = Field(default=0, description="Number of distinct artists in playlist")
    unmet_constraints: List[str] = Field(default_factory=list, description="List of constraints that could not be fully met")


class PlaylistAnalytics(BaseModel):
    total_tracks: int = Field(default=0, description="Total number of tracks in playlist")
    unique_artists: int = Field(default=0, description="Number of unique artists")
    artist_distribution: Dict[str, int] = Field(default_factory=dict, description="Track count per artist")
    repetition_ratio: float = Field(default=0.0, description="Ratio of repeated artist appearances to total tracks")
    genre_distribution: Dict[str, int] = Field(default_factory=dict, description="Frequency of each genre")
    mood_distribution: Dict[str, int] = Field(default_factory=dict, description="Frequency of each mood")
    duplicate_track_count: int = Field(default=0, description="Number of duplicate tracks in playlist")
    metadata_coverage: float = Field(default=0.0, description="Fraction of tracks with metadata available")
    average_hybrid_score: Optional[float] = Field(default=None, description="Average hybrid score of tracks")
    average_recommendation_score: Optional[float] = Field(default=None, description="Average final SoundDeck recommendation score")
    unmet_constraints: List[str] = Field(default_factory=list, description="Unmet constraints from curation")
    notes: List[str] = Field(default_factory=list, description="Contextual documentation on metadata accuracy")


class StudioCurateResponse(BaseModel):
    playlist_id: str = Field(..., description="Unique generated playlist identifier")
    interpreted_request: PlaylistConstraints = Field(..., description="Structured constraints extracted by Ollama")
    tracks: List[dict] = Field(default_factory=list, description="Ranked candidate tracks with scores and metadata")
    summary: StudioCurateSummary = Field(..., description="Curated playlist summary and unmet constraints")
    analytics: Optional[PlaylistAnalytics] = Field(default=None, description="Detailed playlist analytics and distributions")


class TrackExportItem(BaseModel):
    ranking_position: Optional[int] = Field(default=None, description="Position in playlist")
    position: Optional[int] = Field(default=None, description="Alternative position key")
    title: str = Field(default="", max_length=500, description="Track title")
    artist: str = Field(default="", max_length=500, description="Artist name")
    album: Optional[str] = Field(default="", max_length=500, description="Album name")
    url: Optional[str] = Field(default=None, description="Last.fm track URL")
    tags: Optional[List[str]] = Field(default_factory=list, description="Raw tags")
    genres: Optional[List[str]] = Field(default_factory=list, description="Classified genres")
    moods: Optional[List[str]] = Field(default_factory=list, description="Classified moods")
    contexts: Optional[List[str]] = Field(default_factory=list, description="Classified contexts")
    match_score: Optional[float] = Field(default=None, description="Last.fm match score")
    hybrid_score: Optional[float] = Field(default=None, description="SoundDeck hybrid score")
    diversity_adjustment: Optional[float] = Field(default=None, description="Diversity penalty")
    sounddeck_score: Optional[float] = Field(default=None, description="Final recommendation score")
    relevance_score: Optional[float] = Field(default=None, description="Relevance score")
    explanation: Optional[str] = Field(default=None, description="Recommendation rationale")

    model_config = {"extra": "allow"}


class StudioExportRequest(BaseModel):
    playlist_id: Optional[str] = Field(default="sounddeck-playlist", max_length=100, description="Playlist identifier for filename")
    tracks: List[TrackExportItem] = Field(default_factory=list, description="Tracks to export to CSV")

    model_config = {"extra": "allow"}
