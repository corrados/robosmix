from __future__ import annotations

import json
from dataclasses import dataclass

from robosmix.audio.analysis import analyze_file
from robosmix.domain.models import AudioAnalysis, Commit, Track
from robosmix.errors import RobosmixError
from robosmix.store import ProjectStore

ANALYSIS_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class TrackAnalysis:
    track: Track
    analysis: AudioAnalysis


@dataclass(frozen=True)
class AnalysisResult:
    commit: Commit
    artifact_hash: str
    items: tuple[TrackAnalysis, ...]


def analyze_project(store: ProjectStore) -> AnalysisResult:
    tracks = sorted(store.list_tracks(), key=lambda track: track.id)
    if not tracks:
        raise RobosmixError("no tracks to analyze; run 'robosmix import' first")

    items: list[TrackAnalysis] = []
    payload_tracks: list[dict[str, object]] = []
    for track in tracks:
        analysis = analyze_file(store.artifact_path(track.source_hash))
        items.append(TrackAnalysis(track=track, analysis=analysis))
        payload_tracks.append(
            {
                "track_id": track.id,
                "display_name": track.display_name,
                "role": str(track.role),
                "source_hash": track.source_hash,
                "analysis": analysis.to_dict(),
            }
        )

    payload = {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "tracks": payload_tracks,
    }
    data = json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")
    artifact_hash = store.add_artifact(data, "analysis")

    head = store.head()
    if head.analysis_hash == artifact_hash:
        return AnalysisResult(commit=head, artifact_hash=artifact_hash, items=tuple(items))

    commit = store.create_commit(
        parents=(head.id,),
        branch=store.project.current_branch,
        message=f"Analyze {len(tracks)} track(s)",
        analysis_hash=artifact_hash,
        artifacts=((artifact_hash, "analysis"),),
    )
    store.set_branch(commit.branch, commit.id)
    return AnalysisResult(commit=commit, artifact_hash=artifact_hash, items=tuple(items))
