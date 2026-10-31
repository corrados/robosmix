from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import NoReturn

from robosmix.errors import PlanValidationError

MIX_PLAN_SCHEMA_VERSION = 1
MAX_EQ_BANDS = 8
MAX_TRACKS = 256

MIN_TRACK_GAIN_DB = -24.0
MAX_TRACK_GAIN_DB = 12.0
MIN_PAN = -1.0
MAX_PAN = 1.0
MIN_HIGH_PASS_HZ = 20.0
MAX_HIGH_PASS_HZ = 400.0
MIN_EQ_FREQ_HZ = 20.0
MAX_EQ_FREQ_HZ = 20_000.0
MIN_EQ_GAIN_DB = -12.0
MAX_EQ_GAIN_DB = 12.0
MIN_EQ_Q = 0.1
MAX_EQ_Q = 10.0
MIN_COMPRESSOR_THRESHOLD_DB = -60.0
MAX_COMPRESSOR_THRESHOLD_DB = 0.0
MIN_COMPRESSOR_RATIO = 1.0
MAX_COMPRESSOR_RATIO = 10.0
MIN_COMPRESSOR_ATTACK_MS = 1.0
MAX_COMPRESSOR_ATTACK_MS = 100.0
MIN_COMPRESSOR_RELEASE_MS = 20.0
MAX_COMPRESSOR_RELEASE_MS = 1_000.0
MIN_SATURATION = 0.0
MAX_SATURATION = 1.0
MIN_REVERB_SEND = 0.0
MAX_REVERB_SEND = 0.5
MIN_LIMITER_CEILING_DB = -12.0
MAX_LIMITER_CEILING_DB = -0.1
MIN_STEREO_WIDTH = 0.0
MAX_STEREO_WIDTH = 2.0
MIN_TARGET_LUFS = -40.0
MAX_TARGET_LUFS = -5.0
MIN_TARGET_TRUE_PEAK_DB = -3.0
MAX_TARGET_TRUE_PEAK_DB = -0.1

_TRACK_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_MAX_TRACK_KEY_LENGTH = 128
_MAX_FLAVOR_LENGTH = 64
_MAX_GENRE_LENGTH = 80
_MAX_RECIPE_LENGTH = 500
_MAX_RATIONALE_LENGTH = 1_000


def _fail(path: str, message: str) -> NoReturn:
    raise PlanValidationError(f"{path}: {message}")


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _fail(path, "must be an object")
    for key in value:
        if not isinstance(key, str):
            _fail(path, "keys must be strings")
    return value


def _check_keys(data: Mapping[str, object], allowed: set[str], path: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        _fail(path, f"unknown field(s): {', '.join(unknown)}")


def _required(data: Mapping[str, object], name: str, path: str) -> object:
    if name not in data:
        _fail(f"{path}.{name}", "is required")
    return data[name]


def _optional(data: Mapping[str, object], name: str, default: object) -> object:
    return data.get(name, default)


def _number(value: object, path: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(path, "must be a number")
    number = float(value)
    if not math.isfinite(number):
        _fail(path, "must be finite")
    if number < minimum or number > maximum:
        _fail(path, f"must be between {minimum:g} and {maximum:g}")
    return number


def _integer(value: object, path: str, expected: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(path, "must be an integer")
    if value != expected:
        _fail(path, f"must be {expected}")
    return value


def _text(value: object, path: str, maximum_length: int, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        _fail(path, "must be a string")
    if not allow_empty and not value.strip():
        _fail(path, "must not be empty")
    if len(value) > maximum_length:
        _fail(path, f"must be at most {maximum_length} characters")
    return value


def _eq_bands(value: object, path: str) -> tuple[EqBand, ...]:
    if not isinstance(value, (list, tuple)):
        _fail(path, "must be an array")
    if len(value) > MAX_EQ_BANDS:
        _fail(path, f"must contain at most {MAX_EQ_BANDS} bands")
    for index, band in enumerate(value):
        if not isinstance(band, EqBand):
            _fail(f"{path}[{index}]", "must be an EqBand")
    return tuple(value)


def _rounded(value: float) -> float:
    return round(value, 6)


@dataclass(frozen=True)
class EqBand:
    freq_hz: float
    gain_db: float
    q: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "freq_hz", _number(self.freq_hz, "eq.freq_hz", MIN_EQ_FREQ_HZ, MAX_EQ_FREQ_HZ)
        )
        object.__setattr__(
            self, "gain_db", _number(self.gain_db, "eq.gain_db", MIN_EQ_GAIN_DB, MAX_EQ_GAIN_DB)
        )
        object.__setattr__(self, "q", _number(self.q, "eq.q", MIN_EQ_Q, MAX_EQ_Q))

    def to_dict(self) -> dict[str, float]:
        return {
            "freq_hz": _rounded(self.freq_hz),
            "gain_db": _rounded(self.gain_db),
            "q": _rounded(self.q),
        }

    @classmethod
    def from_dict(cls, value: object, path: str = "eq") -> EqBand:
        data = _mapping(value, path)
        _check_keys(data, {"freq_hz", "gain_db", "q"}, path)
        return cls(
            freq_hz=_number(
                _required(data, "freq_hz", path), f"{path}.freq_hz", MIN_EQ_FREQ_HZ, MAX_EQ_FREQ_HZ
            ),
            gain_db=_number(
                _required(data, "gain_db", path), f"{path}.gain_db", MIN_EQ_GAIN_DB, MAX_EQ_GAIN_DB
            ),
            q=_number(_optional(data, "q", 1.0), f"{path}.q", MIN_EQ_Q, MAX_EQ_Q),
        )


@dataclass(frozen=True)
class Compressor:
    threshold_db: float
    ratio: float
    attack_ms: float
    release_ms: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "threshold_db",
            _number(
                self.threshold_db,
                "compressor.threshold_db",
                MIN_COMPRESSOR_THRESHOLD_DB,
                MAX_COMPRESSOR_THRESHOLD_DB,
            ),
        )
        object.__setattr__(
            self,
            "ratio",
            _number(self.ratio, "compressor.ratio", MIN_COMPRESSOR_RATIO, MAX_COMPRESSOR_RATIO),
        )
        object.__setattr__(
            self,
            "attack_ms",
            _number(
                self.attack_ms,
                "compressor.attack_ms",
                MIN_COMPRESSOR_ATTACK_MS,
                MAX_COMPRESSOR_ATTACK_MS,
            ),
        )
        object.__setattr__(
            self,
            "release_ms",
            _number(
                self.release_ms,
                "compressor.release_ms",
                MIN_COMPRESSOR_RELEASE_MS,
                MAX_COMPRESSOR_RELEASE_MS,
            ),
        )

    def to_dict(self) -> dict[str, float]:
        return {
            "threshold_db": _rounded(self.threshold_db),
            "ratio": _rounded(self.ratio),
            "attack_ms": _rounded(self.attack_ms),
            "release_ms": _rounded(self.release_ms),
        }

    @classmethod
    def from_dict(cls, value: object, path: str = "compressor") -> Compressor:
        data = _mapping(value, path)
        _check_keys(data, {"threshold_db", "ratio", "attack_ms", "release_ms"}, path)
        return cls(
            threshold_db=_number(
                _required(data, "threshold_db", path),
                f"{path}.threshold_db",
                MIN_COMPRESSOR_THRESHOLD_DB,
                MAX_COMPRESSOR_THRESHOLD_DB,
            ),
            ratio=_number(
                _required(data, "ratio", path),
                f"{path}.ratio",
                MIN_COMPRESSOR_RATIO,
                MAX_COMPRESSOR_RATIO,
            ),
            attack_ms=_number(
                _required(data, "attack_ms", path),
                f"{path}.attack_ms",
                MIN_COMPRESSOR_ATTACK_MS,
                MAX_COMPRESSOR_ATTACK_MS,
            ),
            release_ms=_number(
                _required(data, "release_ms", path),
                f"{path}.release_ms",
                MIN_COMPRESSOR_RELEASE_MS,
                MAX_COMPRESSOR_RELEASE_MS,
            ),
        )


@dataclass(frozen=True)
class Limiter:
    ceiling_db: float = -1.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "ceiling_db",
            _number(
                self.ceiling_db,
                "limiter.ceiling_db",
                MIN_LIMITER_CEILING_DB,
                MAX_LIMITER_CEILING_DB,
            ),
        )

    def to_dict(self) -> dict[str, float]:
        return {"ceiling_db": _rounded(self.ceiling_db)}

    @classmethod
    def from_dict(cls, value: object, path: str = "limiter") -> Limiter:
        data = _mapping(value, path)
        _check_keys(data, {"ceiling_db"}, path)
        return cls(
            ceiling_db=_number(
                _optional(data, "ceiling_db", -1.0),
                f"{path}.ceiling_db",
                MIN_LIMITER_CEILING_DB,
                MAX_LIMITER_CEILING_DB,
            )
        )


@dataclass(frozen=True)
class TrackMix:
    gain_db: float = 0.0
    pan: float = 0.0
    high_pass_hz: float | None = None
    eq: tuple[EqBand, ...] = ()
    compressor: Compressor | None = None
    saturation: float = 0.0
    reverb_send: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "gain_db",
            _number(self.gain_db, "track.gain_db", MIN_TRACK_GAIN_DB, MAX_TRACK_GAIN_DB),
        )
        object.__setattr__(self, "pan", _number(self.pan, "track.pan", MIN_PAN, MAX_PAN))
        if self.high_pass_hz is not None:
            object.__setattr__(
                self,
                "high_pass_hz",
                _number(
                    self.high_pass_hz,
                    "track.high_pass_hz",
                    MIN_HIGH_PASS_HZ,
                    MAX_HIGH_PASS_HZ,
                ),
            )
        object.__setattr__(self, "eq", _eq_bands(self.eq, "track.eq"))
        if self.compressor is not None and not isinstance(self.compressor, Compressor):
            _fail("track.compressor", "must be a Compressor or null")
        object.__setattr__(
            self,
            "saturation",
            _number(self.saturation, "track.saturation", MIN_SATURATION, MAX_SATURATION),
        )
        object.__setattr__(
            self,
            "reverb_send",
            _number(self.reverb_send, "track.reverb_send", MIN_REVERB_SEND, MAX_REVERB_SEND),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "gain_db": _rounded(self.gain_db),
            "pan": _rounded(self.pan),
            "high_pass_hz": None if self.high_pass_hz is None else _rounded(self.high_pass_hz),
            "eq": [band.to_dict() for band in self.eq],
            "compressor": None if self.compressor is None else self.compressor.to_dict(),
            "saturation": _rounded(self.saturation),
            "reverb_send": _rounded(self.reverb_send),
        }

    @classmethod
    def from_dict(cls, value: object, path: str = "track") -> TrackMix:
        data = _mapping(value, path)
        _check_keys(
            data,
            {"gain_db", "pan", "high_pass_hz", "eq", "compressor", "saturation", "reverb_send"},
            path,
        )
        high_pass = _optional(data, "high_pass_hz", None)
        if high_pass is not None:
            high_pass = _number(
                high_pass, f"{path}.high_pass_hz", MIN_HIGH_PASS_HZ, MAX_HIGH_PASS_HZ
            )
        compressor = _optional(data, "compressor", None)
        return cls(
            gain_db=_number(
                _optional(data, "gain_db", 0.0),
                f"{path}.gain_db",
                MIN_TRACK_GAIN_DB,
                MAX_TRACK_GAIN_DB,
            ),
            pan=_number(_optional(data, "pan", 0.0), f"{path}.pan", MIN_PAN, MAX_PAN),
            high_pass_hz=high_pass,
            eq=tuple(
                EqBand.from_dict(band, f"{path}.eq[{index}]")
                for index, band in enumerate(_array(_optional(data, "eq", []), f"{path}.eq"))
            ),
            compressor=(
                None
                if compressor is None
                else Compressor.from_dict(compressor, f"{path}.compressor")
            ),
            saturation=_number(
                _optional(data, "saturation", 0.0),
                f"{path}.saturation",
                MIN_SATURATION,
                MAX_SATURATION,
            ),
            reverb_send=_number(
                _optional(data, "reverb_send", 0.0),
                f"{path}.reverb_send",
                MIN_REVERB_SEND,
                MAX_REVERB_SEND,
            ),
        )


def _array(value: object, path: str) -> list[object]:
    if not isinstance(value, list):
        _fail(path, "must be an array")
    return value


@dataclass(frozen=True)
class MasterMix:
    eq: tuple[EqBand, ...] = ()
    compressor: Compressor | None = None
    limiter: Limiter = Limiter()
    stereo_width: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "eq", _eq_bands(self.eq, "master.eq"))
        if self.compressor is not None and not isinstance(self.compressor, Compressor):
            _fail("master.compressor", "must be a Compressor or null")
        if not isinstance(self.limiter, Limiter):
            _fail("master.limiter", "must be a Limiter")
        object.__setattr__(
            self,
            "stereo_width",
            _number(self.stereo_width, "master.stereo_width", MIN_STEREO_WIDTH, MAX_STEREO_WIDTH),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "eq": [band.to_dict() for band in self.eq],
            "compressor": None if self.compressor is None else self.compressor.to_dict(),
            "limiter": self.limiter.to_dict(),
            "stereo_width": _rounded(self.stereo_width),
        }

    @classmethod
    def from_dict(cls, value: object, path: str = "master") -> MasterMix:
        data = _mapping(value, path)
        _check_keys(data, {"eq", "compressor", "limiter", "stereo_width"}, path)
        compressor = _optional(data, "compressor", None)
        limiter = _optional(data, "limiter", {"ceiling_db": -1.0})
        return cls(
            eq=tuple(
                EqBand.from_dict(band, f"{path}.eq[{index}]")
                for index, band in enumerate(_array(_optional(data, "eq", []), f"{path}.eq"))
            ),
            compressor=(
                None
                if compressor is None
                else Compressor.from_dict(compressor, f"{path}.compressor")
            ),
            limiter=Limiter.from_dict(limiter, f"{path}.limiter"),
            stereo_width=_number(
                _optional(data, "stereo_width", 1.0),
                f"{path}.stereo_width",
                MIN_STEREO_WIDTH,
                MAX_STEREO_WIDTH,
            ),
        )


@dataclass(frozen=True)
class MixTarget:
    genre: str
    reference_recipe: str
    integrated_lufs: float
    true_peak_db: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "genre", _text(self.genre, "target.genre", _MAX_GENRE_LENGTH))
        object.__setattr__(
            self,
            "reference_recipe",
            _text(
                self.reference_recipe,
                "target.reference_recipe",
                _MAX_RECIPE_LENGTH,
                allow_empty=True,
            ),
        )
        object.__setattr__(
            self,
            "integrated_lufs",
            _number(
                self.integrated_lufs,
                "target.integrated_lufs",
                MIN_TARGET_LUFS,
                MAX_TARGET_LUFS,
            ),
        )
        object.__setattr__(
            self,
            "true_peak_db",
            _number(
                self.true_peak_db,
                "target.true_peak_db",
                MIN_TARGET_TRUE_PEAK_DB,
                MAX_TARGET_TRUE_PEAK_DB,
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "genre": self.genre,
            "reference_recipe": self.reference_recipe,
            "integrated_lufs": _rounded(self.integrated_lufs),
            "true_peak_db": _rounded(self.true_peak_db),
        }

    @classmethod
    def from_dict(cls, value: object, path: str = "target") -> MixTarget:
        data = _mapping(value, path)
        _check_keys(data, {"genre", "reference_recipe", "integrated_lufs", "true_peak_db"}, path)
        return cls(
            genre=_text(_required(data, "genre", path), f"{path}.genre", _MAX_GENRE_LENGTH),
            reference_recipe=_text(
                _required(data, "reference_recipe", path),
                f"{path}.reference_recipe",
                _MAX_RECIPE_LENGTH,
                allow_empty=True,
            ),
            integrated_lufs=_number(
                _required(data, "integrated_lufs", path),
                f"{path}.integrated_lufs",
                MIN_TARGET_LUFS,
                MAX_TARGET_LUFS,
            ),
            true_peak_db=_number(
                _required(data, "true_peak_db", path),
                f"{path}.true_peak_db",
                MIN_TARGET_TRUE_PEAK_DB,
                MAX_TARGET_TRUE_PEAK_DB,
            ),
        )


@dataclass(frozen=True)
class MixPlan:
    flavor: str
    target: MixTarget
    tracks: Mapping[str, TrackMix]
    master: MasterMix
    rationale: str
    schema_version: int = MIX_PLAN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _integer(self.schema_version, "schema_version", MIX_PLAN_SCHEMA_VERSION)
        object.__setattr__(self, "flavor", _text(self.flavor, "flavor", _MAX_FLAVOR_LENGTH))
        if not isinstance(self.target, MixTarget):
            _fail("target", "must be a MixTarget")
        if not isinstance(self.master, MasterMix):
            _fail("master", "must be a MasterMix")
        object.__setattr__(
            self, "rationale", _text(self.rationale, "rationale", _MAX_RATIONALE_LENGTH)
        )
        tracks = _mapping(self.tracks, "tracks")
        if len(tracks) > MAX_TRACKS:
            _fail("tracks", f"must contain at most {MAX_TRACKS} tracks")
        normalized: dict[str, TrackMix] = {}
        for raw_key, value in tracks.items():
            key = _text(raw_key, "tracks.<key>", _MAX_TRACK_KEY_LENGTH)
            if not _TRACK_KEY_RE.fullmatch(key):
                _fail(f"tracks.{key}", "must be a stable track identifier")
            if not isinstance(value, TrackMix):
                _fail(f"tracks.{key}", "must be a TrackMix")
            normalized[key] = value
        object.__setattr__(self, "tracks", MappingProxyType(normalized))
        if self.master.limiter.ceiling_db > self.target.true_peak_db:
            _fail(
                "master.limiter.ceiling_db",
                "must not exceed the target true peak",
            )

    def validate_track_ids(self, track_ids: Iterable[str]) -> None:
        known = set(track_ids)
        unknown = sorted(set(self.tracks) - known)
        if unknown:
            _fail("tracks", f"unknown track id(s): {', '.join(unknown)}")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "flavor": self.flavor,
            "target": self.target.to_dict(),
            "tracks": {
                track_id: self.tracks[track_id].to_dict() for track_id in sorted(self.tracks)
            },
            "master": self.master.to_dict(),
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, value: object) -> MixPlan:
        data = _mapping(value, "plan")
        _check_keys(
            data,
            {"schema_version", "flavor", "target", "tracks", "master", "rationale"},
            "plan",
        )
        tracks_data = _mapping(_required(data, "tracks", "plan"), "plan.tracks")
        tracks = {
            _text(key, "plan.tracks.<key>", _MAX_TRACK_KEY_LENGTH): TrackMix.from_dict(
                track, f"plan.tracks.{key}"
            )
            for key, track in tracks_data.items()
        }
        return cls(
            schema_version=_integer(
                _required(data, "schema_version", "plan"),
                "plan.schema_version",
                MIX_PLAN_SCHEMA_VERSION,
            ),
            flavor=_text(_required(data, "flavor", "plan"), "plan.flavor", _MAX_FLAVOR_LENGTH),
            target=MixTarget.from_dict(_required(data, "target", "plan"), "plan.target"),
            tracks=tracks,
            master=MasterMix.from_dict(_required(data, "master", "plan"), "plan.master"),
            rationale=_text(
                _required(data, "rationale", "plan"),
                "plan.rationale",
                _MAX_RATIONALE_LENGTH,
            ),
        )
