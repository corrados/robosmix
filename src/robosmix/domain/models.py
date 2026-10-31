from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class TrackRole(StrEnum):
    VOCALS = "vocals"
    BACKING_VOCALS = "backing_vocals"
    DRUMS = "drums"
    PERCUSSION = "percussion"
    BASS = "bass"
    GUITAR = "guitar"
    KEYS = "keys"
    SYNTH = "synth"
    STRINGS = "strings"
    BRASS = "brass"
    OTHER = "other"


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    root: str
    created_at: str
    schema_version: int
    current_branch: str


@dataclass(frozen=True)
class Track:
    id: str
    project_id: str
    role: TrackRole
    source_hash: str
    display_name: str
    original_path: str
    notes: str = ""
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["role"] = str(self.role)
        return data


@dataclass(frozen=True)
class Commit:
    id: str
    project_id: str
    parents: tuple[str, ...]
    branch: str
    message: str
    created_at: str
    plan_hash: str | None = None
    analysis_hash: str | None = None
    recipe: str | None = None
    model: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["parents"] = list(self.parents)
        return data


@dataclass(frozen=True)
class AudioAnalysis:
    sample_rate: int
    channels: int
    frames: int
    duration_s: float
    peak_dbfs: float | None
    rms_dbfs: float | None
    integrated_lufs: float | None
    true_peak_dbtp: float | None
    crest_factor_db: float | None
    spectral_centroid_hz: float | None
    spectral_rolloff_hz: float | None
    band_energy: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
