from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from robosmix.cli.main import app
from tests.helpers import write_sine

runner = CliRunner()


def test_full_import_analyze_history_workflow(tmp_path: Path) -> None:
    project = tmp_path / "song"
    kick = write_sine(tmp_path / "kick.wav", frequency=60.0, duration_s=1.0)
    bass = write_sine(tmp_path / "bass_di.wav", frequency=80.0, duration_s=1.0)

    result = runner.invoke(app, ["init", "Test Song", "--path", str(project)])
    assert result.exit_code == 0, result.output
    assert "Initialized project 'Test Song'" in result.output

    result = runner.invoke(app, ["import", str(kick), str(bass), "--project", str(project)])
    assert result.exit_code == 0, result.output
    assert "imported: kick [drums]" in result.output
    assert "imported: bass_di [bass]" in result.output
    assert "2 new track(s)" in result.output

    result = runner.invoke(app, ["import", str(kick), "--project", str(project)])
    assert result.exit_code == 0, result.output
    assert "already imported: kick [drums]" in result.output
    assert "0 new track(s)" in result.output

    result = runner.invoke(app, ["status", "--project", str(project)])
    assert result.exit_code == 0, result.output
    assert "Tracks: 2" in result.output
    assert "Branch: main" in result.output

    result = runner.invoke(app, ["analyze", "--project", str(project), "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert len(payload["tracks"]) == 2
    assert payload["commit"]["branch"] == "main"
    first_commit = payload["commit"]["id"]

    result = runner.invoke(app, ["analyze", "--project", str(project), "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["commit"]["id"] == first_commit

    result = runner.invoke(app, ["history", "--project", str(project)])
    assert result.exit_code == 0, result.output
    assert "Analyze 2 track(s)" in result.output
    assert "Initialize project" in result.output


def test_role_override_and_validation(tmp_path: Path) -> None:
    project = tmp_path / "song"
    take = write_sine(tmp_path / "take_01.wav", duration_s=1.0)

    assert runner.invoke(app, ["init", "Roles", "--path", str(project)]).exit_code == 0

    result = runner.invoke(
        app,
        ["import", str(take), "--role", "vox", "--project", str(project)],
    )
    assert result.exit_code == 0, result.output
    assert "take_01 [vocals]" in result.output

    result = runner.invoke(
        app,
        ["import", str(take), "--role", "theremin", "--project", str(project)],
    )
    assert result.exit_code == 1
    assert "unknown role" in result.output


def test_missing_project_is_a_clean_error(tmp_path: Path) -> None:
    result = runner.invoke(app, ["status", "--project", str(tmp_path / "missing")])
    assert result.exit_code == 1
    assert "error:" in result.output


def test_analyze_without_tracks_is_a_clean_error(tmp_path: Path) -> None:
    project = tmp_path / "empty"
    assert runner.invoke(app, ["init", "Empty", "--path", str(project)]).exit_code == 0

    result = runner.invoke(app, ["analyze", "--project", str(project)])
    assert result.exit_code == 1
    assert "no tracks to analyze" in result.output


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.output.strip().startswith("robosmix ")
