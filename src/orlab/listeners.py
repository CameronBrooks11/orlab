"""Canned dispersion listeners.

Both listeners hold only plain-Python/numpy state, so they pickle across
:class:`~orlab.SimulationPool`'s process boundary and survive OpenRocket's
listener cloning. The clone semantics matter for extenders: OpenRocket runs
a *copy* of your listener, so instance attributes mutated inside hooks are
invisible to the caller afterwards — these two are read-only by design;
subclasses must not accumulate results on ``self`` (share a list instead,
as the listeners guide shows).
"""

import math

import numpy as np

from .core.openrocket_instance import active_core_root
from .core.simulation_listener import AbstractSimulationListener

__all__ = ["ThrustFactor", "WindProfile"]


class WindProfile(AbstractSimulationListener):
    """Deterministic altitude-dependent wind, replacing OpenRocket's wind
    model **including its turbulence** — the cross-version mechanism for
    layered-wind studies (the only native alternative is 24.12-only).

    ``altitudes_m`` must be strictly increasing; ``speeds_ms`` are wind
    speeds at those altitudes; ``directions_rad`` (scalar or per-point) is
    the direction the wind blows *from*, matching
    ``setWindDirection`` (0 = from north, π/2 = from east — verified: both
    produce identical drift). Between points, the wind *vector* is
    interpolated component-wise (no 359°→1° wraparound artifacts; under
    strong direction shear the interpolated magnitude dips below the
    endpoint speeds — inherent to vector interpolation). Outside the range,
    the end values hold. A sharp layer needs an epsilon step:
    ``altitudes_m=[0, 20, 20.001, 30]``.
    """

    def __init__(self, altitudes_m, speeds_ms, directions_rad=0.0):
        altitudes = np.asarray(altitudes_m, dtype=float)
        speeds = np.asarray(speeds_ms, dtype=float)
        directions = np.asarray(directions_rad, dtype=float)
        if directions.ndim == 0:
            directions = np.full(len(altitudes), float(directions))
        if len(altitudes) != len(speeds) or len(altitudes) != len(directions):
            raise ValueError("altitudes_m, speeds_ms, directions_rad lengths differ")
        if len(altitudes) == 0:
            raise ValueError("at least one profile point is required")
        if np.any(np.diff(altitudes) <= 0):
            raise ValueError("altitudes_m must be strictly increasing")
        if np.any(speeds < 0):
            raise ValueError("wind speeds cannot be negative")
        self.altitudes = altitudes
        # the wind VECTOR components; meteorological "from" convention
        self.u = speeds * np.sin(directions)
        self.v = speeds * np.cos(directions)

    def _wind_at(self, altitude_m: float) -> tuple[float, float]:
        """The interpolated wind vector (u east-component, v north) at an
        altitude — pure numpy, unit-testable without a JVM."""
        u = float(np.interp(altitude_m, self.altitudes, self.u))
        v = float(np.interp(altitude_m, self.altitudes, self.v))
        return u, v

    def postWindModel(self, status, wind):
        altitude = float(status.getRocketPosition().z)
        u, v = self._wind_at(altitude)
        return active_core_root().util.Coordinate(u, v, 0.0)


class ThrustFactor(AbstractSimulationListener):
    """Multiplies every thrust sample by a constant factor — the classic
    motor-variation dispersion knob (thrust curves vary batch to batch).
    """

    def __init__(self, factor: float):
        factor = float(factor)
        if not factor > 0 or math.isnan(factor):
            raise ValueError(f"thrust factor must be positive, got {factor}")
        self.factor = factor

    def postSimpleThrustCalculation(self, status, thrust):
        return float(thrust) * self.factor
