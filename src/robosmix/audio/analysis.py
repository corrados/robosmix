from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from numpy.typing import NDArray
from scipy.signal import resample_poly

from robosmix.domain.models import AudioAnalysis

_TRUE_PEAK_OVERSAMPLE = 4
_TRUE_PEAK_BLOCK_SECONDS = 10.0
_SPECTRAL_WINDOW_SECONDS = 10
_ROLLOFF_FRACTION = 0.85

_BANDS: tuple[tuple[str, float, float], ...] = (
    ("low", 0.0, 120.0),
    ("low_mid", 120.0, 500.0),
    ("mid", 500.0, 2000.0),
    ("high_mid", 2000.0, 6000.0),
    ("high", 6000.0, math.inf),
)


def analyze_file(path: Path) -> AudioAnalysis:
    data, sample_rate = sf.read(path, dtype="float32", always_2d=True)
    return analyze_array(data, int(sample_rate))


def analyze_array(data: NDArray[np.float32], sample_rate: int) -> AudioAnalysis:
    if data.ndim == 1:
        data = data[:, np.newaxis]
    frames, channels = data.shape
    duration_s = float(frames) / float(sample_rate) if sample_rate > 0 else 0.0

    peak = float(np.max(np.abs(data))) if frames > 0 else 0.0
    rms = float(np.sqrt(np.mean(np.square(data.astype(np.float64))))) if frames > 0 else 0.0
    peak_dbfs = _to_db(peak)
    rms_dbfs = _to_db(rms)
    crest_factor_db = (
        peak_dbfs - rms_dbfs if peak_dbfs is not None and rms_dbfs is not None else None
    )

    centroid, rolloff, bands = _spectral_features(data, sample_rate)

    return AudioAnalysis(
        sample_rate=sample_rate,
        channels=channels,
        frames=frames,
        duration_s=duration_s,
        peak_dbfs=peak_dbfs,
        rms_dbfs=rms_dbfs,
        integrated_lufs=_integrated_loudness(data, sample_rate, duration_s),
        true_peak_dbtp=_true_peak_dbtp(data, sample_rate),
        crest_factor_db=crest_factor_db,
        spectral_centroid_hz=centroid,
        spectral_rolloff_hz=rolloff,
        band_energy=bands,
    )


def _to_db(value: float) -> float | None:
    if value <= 0.0 or not math.isfinite(value):
        return None
    return float(20.0 * math.log10(value))


def _finite(value: float) -> float | None:
    return float(value) if math.isfinite(value) else None


def _integrated_loudness(
    data: NDArray[np.float32], sample_rate: int, duration_s: float
) -> float | None:
    if duration_s < 0.4 or not np.all(np.isfinite(data)):
        return None
    try:
        meter = pyln.Meter(sample_rate)
        return _finite(float(meter.integrated_loudness(data)))
    except (ValueError, ZeroDivisionError):
        return None


def _true_peak_dbtp(data: NDArray[np.float32], sample_rate: int) -> float | None:
    if data.size == 0 or sample_rate <= 0:
        return None
    block = max(1, int(sample_rate * _TRUE_PEAK_BLOCK_SECONDS))
    peak = 0.0
    for start in range(0, data.shape[0], block):
        chunk = data[start : start + block]
        if chunk.shape[0] == 0:
            continue
        oversampled = resample_poly(chunk, _TRUE_PEAK_OVERSAMPLE, 1, axis=0)
        peak = max(peak, float(np.max(np.abs(oversampled))))
    return _to_db(peak)


def _spectral_features(
    data: NDArray[np.float32], sample_rate: int
) -> tuple[float | None, float | None, dict[str, float]]:
    if data.size == 0 or sample_rate <= 0:
        return None, None, {}
    mono = data.mean(axis=1).astype(np.float64)
    window_length = min(mono.size, sample_rate * _SPECTRAL_WINDOW_SECONDS)
    if window_length < 8:
        return None, None, {}
    start = max(0, (mono.size - window_length) // 2)
    window = mono[start : start + window_length]
    window = window - float(window.mean())
    if not np.any(window):
        return None, None, {}

    windowed = window * np.hanning(window.size)
    spectrum = np.abs(np.fft.rfft(windowed))
    frequencies = np.fft.rfftfreq(window.size, d=1.0 / sample_rate)
    total = float(spectrum.sum())
    if total <= 0.0 or not math.isfinite(total):
        return None, None, {}

    centroid = float((frequencies * spectrum).sum() / total)
    cumulative = np.cumsum(spectrum)
    rolloff_index = int(np.searchsorted(cumulative, _ROLLOFF_FRACTION * cumulative[-1]))
    rolloff = float(frequencies[min(rolloff_index, frequencies.size - 1)])

    bands: dict[str, float] = {}
    for name, low, high in _BANDS:
        mask = (frequencies >= low) & (frequencies < high)
        bands[name] = round(float(spectrum[mask].sum()) / total, 6)

    return centroid, rolloff, bands
