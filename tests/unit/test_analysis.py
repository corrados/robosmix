from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from robosmix.audio.analysis import analyze_array, analyze_file
from tests.helpers import write_sine


def test_analyzes_sine_wave(tmp_path: Path) -> None:
    path = write_sine(tmp_path / "sine.wav", frequency=440.0, duration_s=2.0)
    analysis = analyze_file(path)

    assert analysis.sample_rate == 48_000
    assert analysis.channels == 1
    assert analysis.duration_s == pytest.approx(2.0, abs=1e-6)
    assert analysis.peak_dbfs == pytest.approx(-6.02, abs=0.05)
    assert analysis.rms_dbfs == pytest.approx(-9.03, abs=0.05)
    assert analysis.crest_factor_db == pytest.approx(3.01, abs=0.05)
    assert analysis.integrated_lufs == pytest.approx(-9.76, abs=0.2)
    assert analysis.true_peak_dbtp == pytest.approx(-6.02, abs=0.1)
    assert analysis.spectral_centroid_hz == pytest.approx(440.0, abs=10.0)
    assert analysis.spectral_rolloff_hz == pytest.approx(440.0, abs=10.0)
    assert 0.0 <= sum(analysis.band_energy.values()) <= 1.000001


def test_silence_has_no_level_metrics() -> None:
    silence = np.zeros(48_000, dtype=np.float32)
    analysis = analyze_array(silence, 48_000)

    assert analysis.peak_dbfs is None
    assert analysis.rms_dbfs is None
    assert analysis.integrated_lufs is None
    assert analysis.true_peak_dbtp is None
    assert analysis.crest_factor_db is None
    assert analysis.spectral_centroid_hz is None
    assert analysis.spectral_rolloff_hz is None
    assert analysis.band_energy == {}


def test_short_signal_skips_loudness() -> None:
    short = (0.1 * np.sin(2 * np.pi * 100 * np.arange(100) / 48_000)).astype(np.float32)
    analysis = analyze_array(short, 48_000)

    assert analysis.duration_s == pytest.approx(100 / 48_000)
    assert analysis.integrated_lufs is None
    assert analysis.peak_dbfs is not None


def test_stereo_channels_are_preserved(tmp_path: Path) -> None:
    path = write_sine(tmp_path / "stereo.wav", channels=2)
    analysis = analyze_file(path)
    assert analysis.channels == 2
    assert math.isfinite(analysis.peak_dbfs or math.nan)
