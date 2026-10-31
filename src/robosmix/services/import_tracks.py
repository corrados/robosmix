from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from robosmix.audio.io import AudioInfo, probe
from robosmix.domain.models import Track, TrackRole
from robosmix.domain.roles import detect_role
from robosmix.store import ProjectStore


@dataclass(frozen=True)
class ImportResult:
    track: Track
    info: AudioInfo
    created: bool


def import_tracks(
    store: ProjectStore,
    paths: list[Path],
    *,
    role: TrackRole | None = None,
) -> list[ImportResult]:
    results: list[ImportResult] = []
    for raw_path in paths:
        path = raw_path.expanduser()
        info = probe(path)
        source_hash = store.add_artifact_file(path, "source_audio")
        chosen_role = role if role is not None else detect_role(path)
        track, created = store.add_track(
            role=chosen_role,
            source_hash=source_hash,
            display_name=path.stem,
            original_path=_stored_path(path, store.root),
        )
        results.append(ImportResult(track=track, info=info, created=created))
    return results


def _stored_path(path: Path, root: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(root.resolve()))
    except ValueError:
        return str(resolved)
