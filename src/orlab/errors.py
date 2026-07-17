"""orlab exception types."""

__all__ = [
    "JarVerificationError",
    "NotAnOpenRocketJar",
    "OrlabError",
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
