"""orlab exception types."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - annotation only; import would cycle
    from .parallel import StudyResult

__all__ = [
    "JarVerificationError",
    "NotAnOpenRocketJar",
    "OrlabError",
    "StudyAborted",
    "UnsupportedFlightDataType",
    "UnsupportedOpenRocketVersion",
]


class OrlabError(Exception):
    """Base class for all orlab errors."""


class JarVerificationError(OrlabError):
    """A jar's sha256 could not be verified (no pin, or a digest mismatch)."""


class NotAnOpenRocketJar(OrlabError):
    """The jar path does not point to a readable OpenRocket jar."""


class UnsupportedFlightDataType(OrlabError):
    """A FlightDataType constant does not exist in the loaded OpenRocket version."""


class UnsupportedOpenRocketVersion(OrlabError):
    """The OpenRocket jar's version is older than any known profile."""


class StudyAborted(OrlabError):
    """A SimulationPool study ended early. ``reason`` is one of
    ``interrupt``, ``worker-crash``, ``worker-init``, ``task-error``;
    ``partial`` holds every result collected before the abort."""

    def __init__(self, reason: str, partial: "StudyResult", message: str):
        super().__init__(f"study aborted ({reason}): {message}")
        self.reason = reason
        self.partial = partial
        self._message = message

    def __reduce__(self):
        return (StudyAborted, (self.reason, self.partial, self._message))
