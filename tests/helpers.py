from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf


def write_sine(
    path: Path,
    *,
    frequency: float = 440.0,
    sample_rate: int = 48_000,
    duration_s: float = 2.0,
    amplitude: float = 0.5,
    channels: int = 1,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    time = np.arange(int(sample_rate * duration_s)) / sample_rate
    mono = (amplitude * np.sin(2.0 * np.pi * frequency * time)).astype(np.float32)
    data = np.column_stack([mono] * channels) if channels > 1 else mono
    sf.write(path, data, sample_rate)
    return path
