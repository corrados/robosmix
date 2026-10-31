from __future__ import annotations

from pathlib import Path

import pytest

from robosmix.domain.models import TrackRole
from robosmix.domain.roles import detect_role, normalize_role
from robosmix.errors import RoleError


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("kick.wav", TrackRole.DRUMS),
        ("snare_top.flac", TrackRole.DRUMS),
        ("bass_di.wav", TrackRole.BASS),
        ("lead_vocal.wav", TrackRole.VOCALS),
        ("backing_vox.wav", TrackRole.BACKING_VOCALS),
        ("acoustic_gtr.aiff", TrackRole.GUITAR),
        ("strings.wav", TrackRole.STRINGS),
        ("unknown_take.wav", TrackRole.OTHER),
    ],
)
def test_detects_role_from_filename(filename: str, expected: TrackRole) -> None:
    assert detect_role(Path(filename)) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("vox", TrackRole.VOCALS),
        ("BG Vox", TrackRole.BACKING_VOCALS),
        ("bgv", TrackRole.BACKING_VOCALS),
        ("gtr", TrackRole.GUITAR),
        ("keys", TrackRole.KEYS),
        ("perc", TrackRole.PERCUSSION),
        ("misc", TrackRole.OTHER),
    ],
)
def test_normalizes_role_aliases(value: str, expected: TrackRole) -> None:
    assert normalize_role(value) is expected


def test_rejects_unknown_role() -> None:
    with pytest.raises(RoleError, match="unknown role"):
        normalize_role("theremin")
