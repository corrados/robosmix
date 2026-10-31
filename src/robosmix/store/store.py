from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from robosmix.domain.models import Commit, Project, Track, TrackRole
from robosmix.errors import (
    ProjectExistsError,
    ProjectNotFoundError,
    RobosmixError,
    StoreSchemaError,
)
from robosmix.store.hashing import canonical_json_bytes, sha256_bytes, sha256_file

SCHEMA_VERSION = 1
STORE_DIR = ".robosmix"
DB_NAME = "project.db"
OBJECTS_DIR = "objects"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tracks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    role TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    original_path TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE (project_id, source_hash)
);

CREATE TABLE IF NOT EXISTS artifacts (
    hash TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    size INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS commits (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    parents TEXT NOT NULL,
    branch TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    plan_hash TEXT,
    analysis_hash TEXT,
    recipe TEXT,
    model TEXT
);

CREATE TABLE IF NOT EXISTS commit_artifacts (
    commit_id TEXT NOT NULL REFERENCES commits (id),
    artifact_hash TEXT NOT NULL REFERENCES artifacts (hash),
    role TEXT NOT NULL,
    PRIMARY KEY (commit_id, artifact_hash, role)
);

CREATE TABLE IF NOT EXISTS branches (
    name TEXT PRIMARY KEY,
    commit_id TEXT NOT NULL REFERENCES commits (id),
    updated_at TEXT NOT NULL
);
"""


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def find_project_root(path: Path) -> Path:
    current = path.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / STORE_DIR / DB_NAME).is_file():
            return candidate
    raise ProjectNotFoundError(f"no Robosmix project found at or above {path}")


class ProjectStore:
    def __init__(self, root: Path, connection: sqlite3.Connection) -> None:
        self.root = root
        self._connection = connection

    @property
    def store_dir(self) -> Path:
        return self.root / STORE_DIR

    @property
    def objects_dir(self) -> Path:
        return self.store_dir / OBJECTS_DIR

    @classmethod
    def create(cls, root: Path, name: str) -> ProjectStore:
        root = root.resolve()
        store_dir = root / STORE_DIR
        if store_dir.exists():
            raise ProjectExistsError(f"a Robosmix project already exists at {root}")
        (store_dir / OBJECTS_DIR).mkdir(parents=True)
        connection = sqlite3.connect(store_dir / DB_NAME)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(_SCHEMA)
        store = cls(root, connection)
        with connection:
            connection.executemany(
                "INSERT INTO meta (key, value) VALUES (?, ?)",
                [
                    ("schema_version", str(SCHEMA_VERSION)),
                    ("project_id", _new_id()),
                    ("project_name", name),
                    ("created_at", utc_now()),
                    ("current_branch", "main"),
                ],
            )
        commit = store.create_commit(
            parents=(),
            branch="main",
            message="Initialize project",
        )
        store.set_branch("main", commit.id)
        return store

    @classmethod
    def open(cls, path: Path) -> ProjectStore:
        root = find_project_root(path)
        connection = sqlite3.connect(root / STORE_DIR / DB_NAME)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        row = connection.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        if row is None:
            connection.close()
            raise StoreSchemaError("project store has no schema version")
        if int(row["value"]) != SCHEMA_VERSION:
            connection.close()
            raise StoreSchemaError(
                f"unsupported store schema {row['value']}; expected {SCHEMA_VERSION}"
            )
        return cls(root, connection)

    def close(self) -> None:
        self._connection.close()

    def _meta(self, key: str) -> str:
        row = self._connection.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        if row is None:
            raise StoreSchemaError(f"project store is missing metadata {key!r}")
        return str(row["value"])

    def _set_meta(self, key: str, value: str) -> None:
        with self._connection:
            self._connection.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?) "
                "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    @property
    def project(self) -> Project:
        return Project(
            id=self._meta("project_id"),
            name=self._meta("project_name"),
            root=str(self.root),
            created_at=self._meta("created_at"),
            schema_version=int(self._meta("schema_version")),
            current_branch=self._meta("current_branch"),
        )

    def add_artifact(self, data: bytes, kind: str) -> str:
        digest = sha256_bytes(data)
        destination = self._blob_path(digest)
        if not destination.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            file_descriptor, temporary = tempfile.mkstemp(dir=destination.parent, prefix=".tmp-")
            try:
                with os.fdopen(file_descriptor, "wb") as handle:
                    handle.write(data)
                os.replace(temporary, destination)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        with self._connection:
            self._connection.execute(
                "INSERT OR IGNORE INTO artifacts (hash, kind, size, created_at) "
                "VALUES (?, ?, ?, ?)",
                (digest, kind, len(data), utc_now()),
            )
        return digest

    def add_artifact_file(self, path: Path, kind: str) -> str:
        digest = sha256_file(path)
        destination = self._blob_path(digest)
        if not destination.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            file_descriptor, temporary = tempfile.mkstemp(dir=destination.parent, prefix=".tmp-")
            os.close(file_descriptor)
            try:
                shutil.copyfile(path, temporary)
                os.replace(temporary, destination)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        with self._connection:
            self._connection.execute(
                "INSERT OR IGNORE INTO artifacts (hash, kind, size, created_at) "
                "VALUES (?, ?, ?, ?)",
                (digest, kind, path.stat().st_size, utc_now()),
            )
        return digest

    def _blob_path(self, digest: str) -> Path:
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise RobosmixError(f"invalid artifact hash {digest!r}")
        return self.objects_dir / digest[:2] / digest[2:]

    def artifact_path(self, digest: str) -> Path:
        path = self._blob_path(digest)
        if not path.is_file():
            raise RobosmixError(f"artifact {digest} is missing from the store")
        return path

    def read_artifact(self, digest: str) -> bytes:
        return self.artifact_path(digest).read_bytes()

    def artifact_exists(self, digest: str) -> bool:
        return self._blob_path(digest).is_file()

    def add_track(
        self,
        *,
        role: TrackRole,
        source_hash: str,
        display_name: str,
        original_path: str,
        notes: str = "",
    ) -> tuple[Track, bool]:
        existing = self.get_track_by_source_hash(source_hash)
        if existing is not None:
            return existing, False
        track = Track(
            id=_new_id(),
            project_id=self.project.id,
            role=role,
            source_hash=source_hash,
            display_name=display_name,
            original_path=original_path,
            notes=notes,
            created_at=utc_now(),
        )
        with self._connection:
            self._connection.execute(
                "INSERT INTO tracks "
                "(id, project_id, role, source_hash, display_name, original_path, "
                " notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    track.id,
                    track.project_id,
                    str(track.role),
                    track.source_hash,
                    track.display_name,
                    track.original_path,
                    track.notes,
                    track.created_at,
                ),
            )
        return track, True

    def get_track(self, track_id: str) -> Track | None:
        row = self._connection.execute("SELECT * FROM tracks WHERE id = ?", (track_id,)).fetchone()
        return None if row is None else self._track_from_row(row)

    def get_track_by_source_hash(self, source_hash: str) -> Track | None:
        row = self._connection.execute(
            "SELECT * FROM tracks WHERE project_id = ? AND source_hash = ?",
            (self.project.id, source_hash),
        ).fetchone()
        return None if row is None else self._track_from_row(row)

    def list_tracks(self) -> list[Track]:
        rows = self._connection.execute(
            "SELECT * FROM tracks ORDER BY created_at, display_name"
        ).fetchall()
        return [self._track_from_row(row) for row in rows]

    @staticmethod
    def _track_from_row(row: sqlite3.Row) -> Track:
        return Track(
            id=str(row["id"]),
            project_id=str(row["project_id"]),
            role=TrackRole(row["role"]),
            source_hash=str(row["source_hash"]),
            display_name=str(row["display_name"]),
            original_path=str(row["original_path"]),
            notes=str(row["notes"]),
            created_at=str(row["created_at"]),
        )

    def create_commit(
        self,
        *,
        parents: Iterable[str],
        branch: str,
        message: str,
        plan_hash: str | None = None,
        analysis_hash: str | None = None,
        recipe: str | None = None,
        model: str | None = None,
        artifacts: Iterable[tuple[str, str]] = (),
    ) -> Commit:
        parent_tuple = tuple(parents)
        for parent in parent_tuple:
            if self.get_commit(parent) is None:
                raise RobosmixError(f"unknown parent commit {parent}")
        created_at = utc_now()
        artifact_pairs = tuple(artifacts)
        payload = {
            "parents": list(parent_tuple),
            "branch": branch,
            "message": message,
            "created_at": created_at,
            "plan_hash": plan_hash,
            "analysis_hash": analysis_hash,
            "recipe": recipe,
            "model": model,
            "artifacts": sorted(artifact_pairs),
        }
        commit_id = sha256_bytes(canonical_json_bytes(payload))
        commit = Commit(
            id=commit_id,
            project_id=self.project.id,
            parents=parent_tuple,
            branch=branch,
            message=message,
            created_at=created_at,
            plan_hash=plan_hash,
            analysis_hash=analysis_hash,
            recipe=recipe,
            model=model,
        )
        with self._connection:
            self._connection.execute(
                "INSERT OR IGNORE INTO commits "
                "(id, project_id, parents, branch, message, created_at, "
                " plan_hash, analysis_hash, recipe, model) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    commit.id,
                    commit.project_id,
                    json.dumps(list(commit.parents)),
                    commit.branch,
                    commit.message,
                    commit.created_at,
                    commit.plan_hash,
                    commit.analysis_hash,
                    commit.recipe,
                    commit.model,
                ),
            )
            for artifact_hash, role in artifact_pairs:
                self._connection.execute(
                    "INSERT OR IGNORE INTO commit_artifacts "
                    "(commit_id, artifact_hash, role) VALUES (?, ?, ?)",
                    (commit.id, artifact_hash, role),
                )
        return commit

    def get_commit(self, commit_id: str) -> Commit | None:
        row = self._connection.execute(
            "SELECT * FROM commits WHERE id = ?", (commit_id,)
        ).fetchone()
        return None if row is None else self._commit_from_row(row)

    def list_commits(self, limit: int | None = None) -> list[Commit]:
        query = "SELECT * FROM commits ORDER BY rowid DESC"
        parameters: tuple[object, ...] = ()
        if limit is not None:
            query += " LIMIT ?"
            parameters = (limit,)
        rows = self._connection.execute(query, parameters).fetchall()
        return [self._commit_from_row(row) for row in rows]

    def commit_artifacts(self, commit_id: str) -> list[tuple[str, str]]:
        rows = self._connection.execute(
            "SELECT artifact_hash, role FROM commit_artifacts WHERE commit_id = ? "
            "ORDER BY role, artifact_hash",
            (commit_id,),
        ).fetchall()
        return [(str(row["artifact_hash"]), str(row["role"])) for row in rows]

    def resolve_ref(self, value: str) -> Commit:
        branch = self._connection.execute(
            "SELECT commit_id FROM branches WHERE name = ?", (value,)
        ).fetchone()
        if branch is not None:
            commit = self.get_commit(str(branch["commit_id"]))
            if commit is not None:
                return commit
        matches = self._connection.execute(
            "SELECT id FROM commits WHERE id LIKE ? ORDER BY rowid DESC LIMIT 2",
            (f"{value}%",),
        ).fetchall()
        if len(matches) == 1:
            commit = self.get_commit(str(matches[0]["id"]))
            if commit is not None:
                return commit
        if not matches:
            raise RobosmixError(f"unknown branch or commit {value!r}")
        raise RobosmixError(f"ambiguous commit prefix {value!r}")

    @staticmethod
    def _commit_from_row(row: sqlite3.Row) -> Commit:
        return Commit(
            id=str(row["id"]),
            project_id=str(row["project_id"]),
            parents=tuple(json.loads(row["parents"])),
            branch=str(row["branch"]),
            message=str(row["message"]),
            created_at=str(row["created_at"]),
            plan_hash=row["plan_hash"],
            analysis_hash=row["analysis_hash"],
            recipe=row["recipe"],
            model=row["model"],
        )

    def set_branch(self, name: str, commit_id: str) -> None:
        if self.get_commit(commit_id) is None:
            raise RobosmixError(f"cannot point branch {name!r} at unknown commit")
        with self._connection:
            self._connection.execute(
                "INSERT INTO branches (name, commit_id, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT (name) DO UPDATE SET "
                "commit_id = excluded.commit_id, updated_at = excluded.updated_at",
                (name, commit_id, utc_now()),
            )

    def get_branch(self, name: str) -> Commit | None:
        row = self._connection.execute(
            "SELECT commit_id FROM branches WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            return None
        return self.get_commit(str(row["commit_id"]))

    def list_branches(self) -> list[tuple[str, str]]:
        rows = self._connection.execute(
            "SELECT name, commit_id FROM branches ORDER BY name"
        ).fetchall()
        return [(str(row["name"]), str(row["commit_id"])) for row in rows]

    def head(self, branch: str | None = None) -> Commit:
        name = self.project.current_branch if branch is None else branch
        commit = self.get_branch(name)
        if commit is None:
            raise RobosmixError(f"branch {name!r} has no head")
        return commit

    def checkout_branch(self, name: str) -> None:
        if self.get_branch(name) is None:
            raise RobosmixError(f"unknown branch {name!r}")
        self._set_meta("current_branch", name)
