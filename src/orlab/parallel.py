"""The declarative simulation-options contract.

``DECLARATIVE_KEYS`` is the curated set of ``SimulationOptions`` knobs that
are verified to apply-and-read-back identically on every supported
OpenRocket version (15.03, 22.02, 23.09, 24.12 — probed per release, and
re-checked by the profile contract manifest and an all-version integration
case). Dispersion tooling that drives simulations from plain data uses
these names instead of raw Java setters, so a task description like
``{"wind_speed_average": 6.5}`` is portable and validated.

One interaction to know: OpenRocket launches into the wind by default, and
while ``launch_into_wind`` is true the rod-direction getter reports the
into-wind direction — ``launch_rod_direction`` only takes effect together
with ``launch_into_wind: False`` (verified on all four versions).
"""

from types import MappingProxyType
from typing import NamedTuple

__all__ = ["DECLARATIVE_KEYS", "DeclarativeKey"]


class DeclarativeKey(NamedTuple):
    """How one declarative key maps onto SimulationOptions."""

    setter: str
    getter: str
    kind: type  # value type: float or bool
    unit: str  # SI unit for float keys ("" for bool/dimensionless)


# launch_into_wind precedes launch_rod_direction on purpose: appliers that
# set keys in this order get the verified round-trip semantics. Read-only:
# the whitelist changes by release, never at runtime.
DECLARATIVE_KEYS: MappingProxyType[str, DeclarativeKey] = MappingProxyType(
    {
        "launch_rod_length": DeclarativeKey("setLaunchRodLength", "getLaunchRodLength", float, "m"),
        "launch_rod_angle": DeclarativeKey("setLaunchRodAngle", "getLaunchRodAngle", float, "rad"),
        "launch_into_wind": DeclarativeKey("setLaunchIntoWind", "getLaunchIntoWind", bool, ""),
        "launch_rod_direction": DeclarativeKey(
            "setLaunchRodDirection", "getLaunchRodDirection", float, "rad"
        ),
        "launch_altitude": DeclarativeKey("setLaunchAltitude", "getLaunchAltitude", float, "m"),
        "launch_latitude": DeclarativeKey("setLaunchLatitude", "getLaunchLatitude", float, "°"),
        "launch_longitude": DeclarativeKey("setLaunchLongitude", "getLaunchLongitude", float, "°"),
        "wind_speed_average": DeclarativeKey(
            "setWindSpeedAverage", "getWindSpeedAverage", float, "m/s"
        ),
        "wind_direction": DeclarativeKey("setWindDirection", "getWindDirection", float, "rad"),
    }
)
