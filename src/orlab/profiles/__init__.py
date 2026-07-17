"""Version profiles: per-OpenRocket-version facts generated from the jars.

Each or_XX_XX module is emitted by tools/generate_profile.py. The registry
selects the exact profile for a jar's version, or the nearest older one for
versions without a checked-in profile (new releases work day-one unless the
contract drifts; regenerating is one PR).
"""

from typing import NamedTuple

from ..core.version import parse_version
from ..errors import UnsupportedOpenRocketVersion
from . import or_15_03, or_22_02, or_23_09, or_24_12

__all__ = ["Profile", "get_profile", "profiles", "versions_with"]


class Profile(NamedTuple):
    version: tuple[int, int]
    version_string: str
    core_root: str
    swing_root: str
    startup: str  # "gui" (GuiModule) or "core" (OpenRocketCore.initialize)
    flight_data_types: frozenset[str]
    flight_events: frozenset[str]


def _load(mod) -> Profile:
    return Profile(
        version=mod.VERSION,
        version_string=mod.VERSION_STRING,
        core_root=mod.CORE_ROOT,
        swing_root=mod.SWING_ROOT,
        startup=mod.STARTUP,
        flight_data_types=frozenset(mod.FLIGHT_DATA_TYPES),
        flight_events=frozenset(mod.FLIGHT_EVENTS),
    )


profiles: dict[tuple[int, int], Profile] = {
    p.version: p for p in map(_load, (or_15_03, or_22_02, or_23_09, or_24_12))
}


def get_profile(version: str) -> tuple[Profile, bool]:
    """Returns (profile, exact) for an OpenRocket version string.

    Exact match when a profile for that version is checked in; otherwise the
    nearest older profile with exact=False. Raises UnsupportedOpenRocketVersion
    for versions older than the oldest known profile.
    """
    parsed = parse_version(version)
    if parsed in profiles:
        return profiles[parsed], True
    older = [v for v in profiles if v < parsed]
    if not older:
        oldest = min(profiles)
        raise UnsupportedOpenRocketVersion(
            f"OpenRocket {version} is older than the oldest supported version "
            f"({profiles[oldest].version_string})"
        )
    return profiles[max(older)], False


def versions_with(flight_data_type: str) -> tuple[str, ...]:
    """The profiled OpenRocket versions exposing a FlightDataType constant."""
    return tuple(
        profiles[v].version_string
        for v in sorted(profiles)
        if flight_data_type in profiles[v].flight_data_types
    )
