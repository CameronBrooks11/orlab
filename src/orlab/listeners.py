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
        if not (
            np.all(np.isfinite(altitudes))
            and np.all(np.isfinite(speeds))
            and np.all(np.isfinite(directions))
        ):
            raise ValueError("profile values must be finite")
        if np.any(np.diff(altitudes) <= 0):
            raise ValueError("altitudes_m must be strictly increasing")
        if np.any(speeds < 0):
            raise ValueError("wind speeds cannot be negative")
        self.altitudes = altitudes
        # OpenRocket's from-vector convention (see _wind_at)
        self.u = speeds * np.sin(directions)
        self.v = speeds * np.cos(directions)

    def _wind_at(self, altitude_m: float) -> tuple[float, float]:
        """The interpolated (u, v) Coordinate components at an altitude —
        pure numpy, unit-testable without a JVM.

        Convention note for extenders: OpenRocket's wind Coordinate points
        toward where the wind blows *from* (the stepper ADDS it to rocket
        velocity to form airspeed) — u, v here are from-vector components,
        the sign-inverse of physical airflow components. Wind from the east
        is (+speed, 0), and the rocket drifts west. This reproduces
        OpenRocket's own model exactly; weather-data u/v (eastward/northward
        FLOW) must be negated before use in a custom hook."""
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
        if not math.isfinite(factor) or factor <= 0:
            raise ValueError(f"thrust factor must be positive and finite, got {factor}")
        self.factor = factor

    def postSimpleThrustCalculation(self, status, thrust):
        return float(thrust) * self.factor
