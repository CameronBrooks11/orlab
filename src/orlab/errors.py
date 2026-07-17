"""orlab exception types."""

__all__ = [
    "OrlabError",
    "UnsupportedFlightDataType",
    "UnsupportedOpenRocketVersion",
]


class OrlabError(Exception):
    """Base class for all orlab errors."""


class UnsupportedFlightDataType(OrlabError):
    """A FlightDataType constant does not exist in the loaded OpenRocket version."""


class UnsupportedOpenRocketVersion(OrlabError):
    """The OpenRocket jar's version is older than any known profile."""
