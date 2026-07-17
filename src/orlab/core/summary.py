"""FlightSummary: the scalar flight report, in plain Python values.

Everything here is deliberately JVM-free: `Helper.get_summary` extracts raw
series and event times from the running OpenRocket and hands them to the
pure functions in this module. That keeps the windowing/derivation logic
unit-testable without a jar, and keeps `FlightSummary` itself picklable
into JVM-less processes (JPype scalars pickle fine inside a JVM process
but fail to load anywhere else — hence the hard builtin-types rule).
"""

import math
from dataclasses import dataclass, fields
from typing import ClassVar

import numpy as np

__all__ = ["FlightSummary"]


@dataclass(frozen=True)
class FlightSummary:
    """Scalar summary of one simulated flight branch.

    All values are builtin floats/ints/strs (never Java or numpy types), in
    SI units per :attr:`UNITS`. Missing or inapplicable values are
    ``math.nan``, never ``None`` — a booster branch has no launch rod
    departure, pre-23.09 OpenRocket computes no optimum delay, a flight
    without a recovery event has no descent rate. The field set only grows;
    pickles are same-orlab-version transport, not an archive format.
    """

    velocity_off_rod: float
    """Speed when leaving the launch rod (m/s); NaN on branches without a
    LAUNCHROD event (boosters)."""
    stability_off_rod_cal: float
    """Stability margin (calibers) at launch rod departure; NaN without a
    LAUNCHROD event."""
    apogee: float
    """Highest altitude above the launch site (m)."""
    time_to_apogee: float
    """Time from liftoff to apogee (s)."""
    max_velocity: float
    """Largest total velocity (m/s)."""
    max_acceleration: float
    """Largest total acceleration (m/s²)."""
    max_mach: float
    """Largest Mach number."""
    min_stability_cal: float
    """Smallest stability margin (calibers) between launch rod departure and
    apogee. The window matters: OpenRocket 24.12 computes stability through
    post-apogee tumble, where unwindowed minima are meaningless."""
    max_stability_cal: float
    """Largest stability margin (calibers) in the same window."""
    velocity_at_deployment: float
    """Total velocity at the last recovery device deployment (m/s); NaN
    without a deployment."""
    descent_rate: float
    """Mean vertical descent speed (m/s, positive down) from the last
    recovery device deployment to ground hit; NaN without a deployment."""
    ground_hit_velocity: float
    """Speed at ground contact (m/s)."""
    landing_x: float
    """Landing position east of the launch site (m, flat-earth)."""
    landing_y: float
    """Landing position north of the launch site (m, flat-earth)."""
    landing_distance: float
    """Straight-line distance from launch site to landing (m)."""
    landing_bearing_deg: float
    """Compass bearing from launch site to landing (degrees, 0 = north,
    90 = east). Numerically defined but physically meaningless when
    landing_distance ≈ 0."""
    flight_time: float
    """Total simulated flight time (s)."""
    optimum_delay: float
    """OpenRocket's optimum ejection delay (s); NaN before OpenRocket
    23.09, which does not compute it."""
    branch_number: int
    """Which stage branch this summary describes (0 = sustainer)."""
    branch_name: str
    """OpenRocket's name for the branch (e.g. "Sustainer")."""
    branch_count: int
    """How many branches the simulation produced."""
    warnings: tuple[str, ...]
    """Simulation warnings, verbatim from OpenRocket (opaque strings)."""

    UNITS: ClassVar[dict[str, str]] = {
        "velocity_off_rod": "m/s",
        "stability_off_rod_cal": "cal",
        "apogee": "m",
        "time_to_apogee": "s",
        "max_velocity": "m/s",
        "max_acceleration": "m/s²",
        "max_mach": "",
        "min_stability_cal": "cal",
        "max_stability_cal": "cal",
        "velocity_at_deployment": "m/s",
        "descent_rate": "m/s",
        "ground_hit_velocity": "m/s",
        "landing_x": "m",
        "landing_y": "m",
        "landing_distance": "m",
        "landing_bearing_deg": "°",
        "flight_time": "s",
        "optimum_delay": "s",
    }

    _SECTIONS: ClassVar[list[tuple[str, list[str]]]] = [
        ("Rail departure", ["velocity_off_rod", "stability_off_rod_cal"]),
        (
            "Ascent",
            [
                "apogee",
                "time_to_apogee",
                "max_velocity",
                "max_acceleration",
                "max_mach",
                "min_stability_cal",
                "max_stability_cal",
                "optimum_delay",
            ],
        ),
        (
            "Recovery & descent",
            ["velocity_at_deployment", "descent_rate", "ground_hit_velocity"],
        ),
        (
            "Landing",
            [
                "landing_x",
                "landing_y",
                "landing_distance",
                "landing_bearing_deg",
                "flight_time",
            ],
        ),
    ]

    def to_dict(self) -> dict:
        """The summary as a flat dict — one dispersion-study row.
        ``pandas.DataFrame([s.to_dict() for s in summaries])`` is the table.
        """
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def __str__(self) -> str:
        lines = [f"Flight summary — branch {self.branch_number} ({self.branch_name})"]
        for section, names in self._SECTIONS:
            lines.append(f"  {section}:")
            for name in names:
                value = getattr(self, name)
                unit = self.UNITS.get(name, "")
                shown = "n/a" if isinstance(value, float) and math.isnan(value) else f"{value:.6g}"
                lines.append(f"    {name.replace('_', ' ')}: {shown}{f' {unit}' if unit else ''}")
        lines.append("  Warnings:")
        if self.warnings:
            lines.extend(f"    - {w}" for w in self.warnings)
        else:
            lines.append("    none")
        return "\n".join(lines)


def _bearing_deg(east: float, north: float) -> float:
    """Compass bearing (0 = north, 90 = east) of the point (east, north).
    OpenRocket's TYPE_POSITION_X is "Position East of launch" and
    TYPE_POSITION_Y "Position North of launch" (verified on 15.03 and
    24.12)."""
    return math.degrees(math.atan2(east, north)) % 360.0


def _value_at(times: np.ndarray, values: np.ndarray, t: float) -> float:
    """The first finite sample at or after time t; NaN when the series is
    empty or holds no finite sample from t on. Skipping NaN samples is
    deliberate: e.g. 22.02/23.09 record stability as NaN at the exact
    launch-rod-departure step and compute it from the next step."""
    if len(times) == 0 or len(values) == 0:
        return math.nan
    start = np.searchsorted(times, t, side="left")
    for idx in range(start, len(values)):
        if not math.isnan(values[idx]):
            return float(values[idx])
    return math.nan


def _window_stats(
    times: np.ndarray, values: np.ndarray, t0: float, t1: float
) -> tuple[float, float]:
    """(min, max) of values over t0 <= time <= t1, ignoring NaN samples.

    The NaN-awareness is load-bearing, not defensive: on 15.03 sustainers
    APOGEE can fire after deployment and the window is only correct because
    post-deployment stability samples are NaN. (NaN, NaN) when the window
    holds no finite samples."""
    if len(times) == 0 or len(values) == 0:
        return (math.nan, math.nan)
    mask = (times >= t0) & (times <= t1) & ~np.isnan(values)
    if not mask.any():
        return (math.nan, math.nan)
    windowed = values[mask]
    return (float(windowed.min()), float(windowed.max()))


def _mean_descent_rate(times: np.ndarray, velocity_z: np.ndarray, t0: float, t1: float) -> float:
    """Mean of -velocity_z over t0 <= time <= t1, ignoring NaN samples;
    NaN when the window holds none."""
    if len(times) == 0 or len(velocity_z) == 0:
        return math.nan
    mask = (times >= t0) & (times <= t1) & ~np.isnan(velocity_z)
    if not mask.any():
        return math.nan
    return float(np.mean(-velocity_z[mask]))
