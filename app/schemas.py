from typing import Optional, List
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

    @field_validator("target_genres", "target_moods", "target_contexts", mode="before")
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
