from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import soundfile as sf

from robosmix.errors import TrackImportError

SUPPORTED_AUDIO_EXTENSIONS = frozenset({".wav", ".wave", ".aif", ".aiff", ".flac"})


@dataclass(frozen=True)
class AudioInfo:
    sample_rate: int
    channels: int
    frames: int
    duration_s: float
    format: str


def probe(path: Path) -> AudioInfo:
    if not path.is_file():
        raise TrackImportError(f"audio file not found: {path}")
    if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
        raise TrackImportError(f"unsupported audio format {path.suffix!r}; supported: {supported}")
    try:
        info = sf.info(str(path))
    except (RuntimeError, sf.LibsndfileError) as exc:
        raise TrackImportError(f"cannot read audio file {path}: {exc}") from exc
    if info.frames <= 0 or info.samplerate <= 0:
        raise TrackImportError(f"audio file has no samples: {path}")
    return AudioInfo(
        sample_rate=int(info.samplerate),
        channels=int(info.channels),
        frames=int(info.frames),
        duration_s=float(info.frames) / float(info.samplerate),
        format=str(info.format),
    )
