"""orlab exception types."""

__all__ = [
    "NotAnOpenRocketJar",
    "OrlabError",
    "UnsupportedFlightDataType",
    "UnsupportedOpenRocketVersion",
]


class OrlabError(Exception):
    """Base class for all orlab errors."""


class NotAnOpenRocketJar(OrlabError):
    """The jar path does not point to a readable OpenRocket jar."""


class UnsupportedFlightDataType(OrlabError):
    """A FlightDataType constant does not exist in the loaded OpenRocket version."""


class UnsupportedOpenRocketVersion(OrlabError):
    """The OpenRocket jar's version is older than any known profile."""
