from __future__ import annotations

import functools
import json
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, NoReturn, cast

import typer

from robosmix import __version__
from robosmix.domain.roles import normalize_role
from robosmix.errors import RobosmixError
from robosmix.services.analysis import analyze_project
from robosmix.services.import_tracks import import_tracks
from robosmix.services.project import init_project, open_project

app = typer.Typer(
    help="AI-assisted mixing and mastering with branchable history.",
    no_args_is_help=True,
    add_completion=False,
)

_PROJECT_OPTION = typer.Option(
    "--project",
    "-p",
    help="Project directory (defaults to the current directory).",
)


def _die(exc: RobosmixError) -> NoReturn:
    typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


def _handle_errors[F: Callable[..., object]](func: F) -> F:
    @functools.wraps(func)
    def wrapper(*args: object, **kwargs: object) -> object:
        try:
            return func(*args, **kwargs)
        except RobosmixError as exc:
            _die(exc)

    return cast(F, wrapper)


def _fmt(value: float | None, digits: int = 2) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


@app.command()
@_handle_errors
def init(
    name: Annotated[str, typer.Argument(help="Project name.")],
    path: Annotated[
        Path, typer.Option("--path", "-p", help="Directory for the new project.")
    ] = Path("."),
) -> None:
    store = init_project(path.expanduser(), name)
    try:
        project = store.project
        head = store.head()
        typer.echo(f"Initialized project {project.name!r} at {project.root}")
        typer.echo(f"Branch {project.current_branch} at {head.id[:12]}")
    finally:
        store.close()


@app.command("import")
@_handle_errors
def import_cmd(
    paths: Annotated[list[Path], typer.Argument(help="Audio files (wav, aiff, flac).")],
    role: Annotated[
        str | None,
        typer.Option("--role", "-r", help="Override the detected role for all files."),
    ] = None,
    project: Annotated[Path, _PROJECT_OPTION] = Path("."),
) -> None:
    selected_role = normalize_role(role) if role is not None else None
    store = open_project(project)
    try:
        results = import_tracks(store, paths, role=selected_role)
        created = sum(1 for result in results if result.created)
        for result in results:
            state = "imported" if result.created else "already imported"
            track = result.track
            typer.echo(f"{state}: {track.display_name} [{track.role.value}] -> {track.id[:12]}")
        typer.echo(f"{created} new track(s); {len(results)} file(s) processed")
    finally:
        store.close()


@app.command()
@_handle_errors
def analyze(
    project: Annotated[Path, _PROJECT_OPTION] = Path("."),
    json_output: Annotated[
        bool, typer.Option("--json", help="Print machine-readable JSON.")
    ] = False,
) -> None:
    store = open_project(project)
    try:
        result = analyze_project(store)
        if json_output:
            payload = {
                "commit": result.commit.to_dict(),
                "tracks": [
                    {
                        "track": item.track.to_dict(),
                        "analysis": item.analysis.to_dict(),
                    }
                    for item in result.items
                ],
            }
            typer.echo(json.dumps(payload, sort_keys=True, indent=2))
            return

        for item in result.items:
            analysis = item.analysis
            track = item.track
            typer.echo(f"{track.display_name} [{track.role.value}]")
            typer.echo(
                f"  duration={analysis.duration_s:.2f}s "
                f"sample_rate={analysis.sample_rate} channels={analysis.channels}"
            )
            typer.echo(
                f"  peak={_fmt(analysis.peak_dbfs)} dBFS "
                f"rms={_fmt(analysis.rms_dbfs)} dBFS "
                f"crest={_fmt(analysis.crest_factor_db)} dB"
            )
            typer.echo(
                f"  integrated={_fmt(analysis.integrated_lufs)} LUFS "
                f"true_peak={_fmt(analysis.true_peak_dbtp)} dBTP"
            )
            typer.echo(
                f"  centroid={_fmt(analysis.spectral_centroid_hz)} Hz "
                f"rolloff={_fmt(analysis.spectral_rolloff_hz)} Hz"
            )
        typer.echo(f"commit {result.commit.id[:12]} on {result.commit.branch}")
    finally:
        store.close()


@app.command()
@_handle_errors
def status(
    project: Annotated[Path, _PROJECT_OPTION] = Path("."),
) -> None:
    store = open_project(project)
    try:
        info = store.project
        head = store.head()
        tracks = store.list_tracks()
        commits = store.list_commits()
        typer.echo(f"Project: {info.name} ({info.id[:12]})")
        typer.echo(f"Root: {info.root}")
        typer.echo(f"Schema: v{info.schema_version}")
        typer.echo(f"Branch: {info.current_branch} -> {head.id[:12]} {head.message}")
        typer.echo(f"Commits: {len(commits)}")
        typer.echo(f"Tracks: {len(tracks)}")
        for track in tracks:
            typer.echo(f"  {track.display_name} [{track.role.value}] {track.source_hash[:12]}")
    finally:
        store.close()


@app.command()
@_handle_errors
def history(
    project: Annotated[Path, _PROJECT_OPTION] = Path("."),
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum commits to show.")] = 20,
) -> None:
    store = open_project(project)
    try:
        info = store.project
        branch_items = store.list_branches()
        for commit in store.list_commits(max(1, limit)):
            marker = "*" if commit.branch == info.current_branch else " "
            names = [name for name, commit_id in branch_items if commit_id == commit.id]
            suffix = f" [{', '.join(names)}]" if names else ""
            typer.echo(f"{marker} {commit.id[:12]} {commit.created_at} {commit.message}{suffix}")
    finally:
        store.close()


@app.command()
def version() -> None:
    typer.echo(f"robosmix {__version__}")


if __name__ == "__main__":
    app()
