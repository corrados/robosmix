from __future__ import annotations

from pathlib import Path

from robosmix.errors import RobosmixError
from robosmix.store import ProjectStore


def init_project(root: Path, name: str) -> ProjectStore:
    project_name = name.strip()
    if not project_name:
        raise RobosmixError("project name must not be empty")
    if root.exists() and not root.is_dir():
        raise RobosmixError(f"project path is not a directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    return ProjectStore.create(root, project_name)


def open_project(path: Path) -> ProjectStore:
    return ProjectStore.open(path)
