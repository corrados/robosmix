class RobosmixError(Exception):
    """Base class for expected, user-facing Robosmix failures."""


class ProjectNotFoundError(RobosmixError):
    """Raised when no Robosmix project can be found."""


class ProjectExistsError(RobosmixError):
    """Raised when initializing a directory that already has a project."""


class StoreSchemaError(RobosmixError):
    """Raised when the store schema is unsupported or corrupt."""


class TrackImportError(RobosmixError):
    """Raised when an audio file cannot be imported."""


class RoleError(RobosmixError):
    """Raised when a track role is unknown."""
