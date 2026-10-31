from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def stems_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "stems"
    directory.mkdir()
    return directory
