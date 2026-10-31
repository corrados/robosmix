from __future__ import annotations

from pathlib import Path

import pytest

from robosmix.domain.models import TrackRole
from robosmix.errors import ProjectExistsError, ProjectNotFoundError, RobosmixError
from robosmix.store import ProjectStore, find_project_root


@pytest.fixture
def store(tmp_path: Path) -> ProjectStore:
    project = ProjectStore.create(tmp_path / "song", "Test Song")
    yield project
    project.close()


def test_create_initializes_project_and_root_commit(store: ProjectStore) -> None:
    project = store.project
    assert project.name == "Test Song"
    assert project.current_branch == "main"
    assert project.schema_version == 1
    assert store.head().message == "Initialize project"
    assert len(store.list_commits()) == 1
    assert store.list_branches() == [("main", store.head().id)]


def test_create_rejects_existing_project(tmp_path: Path) -> None:
    root = tmp_path / "song"
    first = ProjectStore.create(root, "One")
    first.close()
    with pytest.raises(ProjectExistsError):
        ProjectStore.create(root, "Two")


def test_artifact_store_is_content_addressed_and_deduplicated(store: ProjectStore) -> None:
    first = store.add_artifact(b"hello", "text")
    second = store.add_artifact(b"hello", "text")
    assert first == second
    assert store.read_artifact(first) == b"hello"
    assert store.artifact_path(first).is_file()


def test_tracks_are_unique_per_source_hash(store: ProjectStore) -> None:
    track, created = store.add_track(
        role=TrackRole.DRUMS,
        source_hash="a" * 64,
        display_name="kick",
        original_path="kick.wav",
    )
    duplicate, duplicate_created = store.add_track(
        role=TrackRole.BASS,
        source_hash="a" * 64,
        display_name="kick-again",
        original_path="kick.wav",
    )
    assert created is True
    assert duplicate_created is False
    assert duplicate.id == track.id
    assert duplicate.role is TrackRole.DRUMS
    assert store.list_tracks() == [track]


def test_commits_form_a_history(store: ProjectStore) -> None:
    parent = store.head()
    commit = store.create_commit(
        parents=(parent.id,),
        branch="main",
        message="Analyze",
        analysis_hash="b" * 64,
    )
    store.set_branch("main", commit.id)
    assert store.head().id == commit.id
    assert commit.parents == (parent.id,)
    assert len(store.list_commits()) == 2
    assert store.resolve_ref(commit.id).id == commit.id
    assert store.resolve_ref(commit.id[:12]).id == commit.id
    assert store.resolve_ref("main").id == commit.id


def test_unknown_parent_is_rejected(store: ProjectStore) -> None:
    with pytest.raises(RobosmixError, match="unknown parent"):
        store.create_commit(parents=("deadbeef",), branch="main", message="bad")


def test_find_project_root_walks_up(store: ProjectStore, tmp_path: Path) -> None:
    nested = store.root / "a" / "b"
    nested.mkdir(parents=True)
    assert find_project_root(nested) == store.root
    with pytest.raises(ProjectNotFoundError):
        find_project_root(tmp_path / "outside")


def test_open_requires_a_store(tmp_path: Path) -> None:
    with pytest.raises(ProjectNotFoundError):
        ProjectStore.open(tmp_path)
