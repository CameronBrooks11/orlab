"""FlightSummary derivation logic, jar-free: pure math, windowing rules,
duck-typed FlightData/branch stubs, and the builtin-types contract."""

import math
import pickle
from dataclasses import fields
from types import SimpleNamespace

import numpy as np
import pytest

import orlab.core.helper as helper_mod
from orlab import FlightSummary, Helper
from orlab.core.summary import _bearing_deg, _mean_descent_rate, _value_at, _window_stats
from orlab.errors import OrlabError

# --- pure functions ---


@pytest.mark.parametrize(
    ("east", "north", "expected"),
    [
        (0.0, 1.0, 0.0),  # due north
        (1.0, 0.0, 90.0),  # due east
        (0.0, -1.0, 180.0),  # due south
        (-1.0, 0.0, 270.0),  # due west
        (1.0, 1.0, 45.0),
        (-1.0, -1.0, 225.0),
        (-0.001, 1.0, pytest.approx(359.9427, abs=1e-3)),  # wraparound
    ],
)
def test_bearing_compass_convention(east, north, expected):
    assert _bearing_deg(east, north) == pytest.approx(expected)


def test_value_at_edges():
    t = np.array([0.0, 1.0, 2.0])
    v = np.array([10.0, 20.0, 30.0])
    assert _value_at(t, v, 0.5) == 20.0  # first sample at/after
    assert _value_at(t, v, 2.0) == 30.0
    assert math.isnan(_value_at(t, v, 2.5))  # past the end
    assert math.isnan(_value_at(np.array([]), np.array([]), 0.0))


def test_value_at_skips_nan_samples():
    """22.02/23.09 record stability as NaN at the exact rod-departure step;
    the value is the next finite sample, not NaN."""
    t = np.array([0.0, 1.0, 2.0, 3.0])
    v = np.array([10.0, np.nan, 30.0, 40.0])
    assert _value_at(t, v, 1.0) == 30.0
    assert math.isnan(_value_at(t, np.array([1.0, np.nan, np.nan, np.nan]), 1.0))


def test_window_stats_nan_awareness_is_load_bearing():
    """Synthetic 24.12-style series: stability goes deeply negative in
    post-apogee tumble, and 15.03-style post-deployment samples are NaN.
    The window plus NaN-skip must exclude both."""
    t = np.array([0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0])
    stab = np.array([np.nan, 3.0, 3.5, 5.3, np.nan, -9.6, -6.0])
    # window: rod departure (0.5) to apogee (3.0); tumble at t>3 excluded
    lo, hi = _window_stats(t, stab, 0.5, 3.0)
    assert (lo, hi) == (3.0, 5.3)
    # blind aggregation over everything would see the tumble
    lo_all, _ = _window_stats(t, stab, 0.0, 5.0)
    assert lo_all == -9.6
    # a window with only-NaN samples is (NaN, NaN)
    lo, hi = _window_stats(t, stab, 2.5, 2.9)
    assert math.isnan(lo) and math.isnan(hi)


def test_mean_descent_rate():
    t = np.array([0.0, 1.0, 2.0, 3.0])
    vz = np.array([10.0, -4.0, -5.0, np.nan])
    assert _mean_descent_rate(t, vz, 1.0, 3.0) == pytest.approx(4.5)
    assert math.isnan(_mean_descent_rate(t, vz, 3.0, 3.0))  # only-NaN window
    assert math.isnan(_mean_descent_rate(np.array([]), np.array([]), 0, 1))


# --- duck-typed stubs for get_summary ---


class _Event:
    def __init__(self, name, t):
        self._name, self._t = name, t

    def getType(self):
        return self

    def name(self):
        return self._name

    def getTime(self):
        return self._t


class _Branch:
    """Branch stub: series keyed by constant name (get_summary's
    translate step is stubbed to identity), plus events and a name."""

    def __init__(self, series, events, name="Sustainer", accessor="getName"):
        self._series, self._events = series, events
        if accessor == "getName":
            self.getName = lambda: name
        elif accessor == "getBranchName":
            self.getBranchName = lambda: name

    def get(self, type_name):
        return self._series.get(type_name)

    def getEvents(self):
        return [_Event(n, t) for n, ts in self._events.items() for t in ts]


class _FlightData:
    def __init__(self, branches, warnings=(), **getters):
        self._branches, self._warnings = branches, warnings
        for name, value in getters.items():
            setattr(self, name, lambda v=value: v)

    def getBranchCount(self):
        return len(self._branches)

    def getBranch(self, i):
        return self._branches[i]

    def getWarningSet(self):
        return list(self._warnings)


GETTERS_2412 = {
    "getMaxAltitude": 51.2,
    "getTimeToApogee": 3.47,
    "getMaxVelocity": 29.4,
    "getMaxAcceleration": 144.0,
    "getMaxMachNumber": 0.086,
    "getLaunchRodVelocity": 15.4,
    "getDeploymentVelocity": 2.48,
    "getGroundHitVelocity": 4.16,
    "getFlightTime": 16.0,
    "getOptimumDelay": 2.79,
}

SERIES = {
    "TYPE_TIME": [0.0, 0.25, 1.0, 3.5, 3.75, 10.0, 16.0],
    "TYPE_ALTITUDE": [0.0, 2.0, 30.0, 51.2, 50.0, 20.0, 0.0],
    "TYPE_STABILITY": [np.nan, 3.0, 3.5, 5.3, -9.6, np.nan, np.nan],
    "TYPE_VELOCITY_Z": [0.0, 15.0, 25.0, 0.0, -2.5, -4.0, -4.2],
    "TYPE_VELOCITY_TOTAL": [0.0, 15.4, 25.0, 0.5, 2.5, 4.0, 4.2],
    "TYPE_ACCELERATION_TOTAL": [144.0, 100.0, 10.0, 9.8, 9.8, 0.5, 0.1],
    "TYPE_MACH_NUMBER": [0.0, 0.045, 0.073, 0.001, 0.007, 0.011, 0.012],
    "TYPE_POSITION_X": [0.0, 0.0, 0.1, 0.5, 0.6, 2.0, 3.0],
    "TYPE_POSITION_Y": [0.0, 0.0, 0.2, 1.0, 1.5, 3.5, 4.0],
}

EVENTS = {
    "LAUNCH": [0.0],
    "LAUNCHROD": [0.25],
    "APOGEE": [3.5],
    "RECOVERY_DEVICE_DEPLOYMENT": [3.75],
    "GROUND_HIT": [16.0],
    "SIM_WARN": [3.6],  # unknown-to-enum types must not disturb summaries
}


def _helper(flight_data, version="24.12"):
    h = Helper.__new__(Helper)
    h._instance = SimpleNamespace(or_version=version)
    h.translate_flight_data_type = lambda name: name
    h._sim = SimpleNamespace(getSimulatedData=lambda: flight_data)
    return h


def _summary(flight_data, branch_number=0, version="24.12"):
    h = _helper(flight_data, version)
    return h.get_summary(h._sim, branch_number)


def test_branch0_uses_flightdata_getters_verbatim():
    fd = _FlightData([_Branch(SERIES, EVENTS)], warnings=("w1",), **GETTERS_2412)
    s = _summary(fd)
    assert s.apogee == 51.2
    assert s.velocity_off_rod == 15.4
    assert s.optimum_delay == 2.79
    assert s.min_stability_cal == 3.0  # windowed: tumble sample at 3.75 excluded
    assert s.max_stability_cal == 5.3
    assert s.stability_off_rod_cal == 3.0
    assert s.descent_rate == pytest.approx((2.5 + 4.0 + 4.2) / 3)
    assert s.landing_x == 3.0 and s.landing_y == 4.0
    assert s.landing_distance == 5.0
    assert s.landing_bearing_deg == pytest.approx(math.degrees(math.atan2(3, 4)))
    assert s.warnings == ("w1",)
    assert s.branch_name == "Sustainer"


def test_absent_getter_nans_with_one_warning(caplog, monkeypatch):
    getters = {k: v for k, v in GETTERS_2412.items() if k != "getOptimumDelay"}
    fd = _FlightData([_Branch(SERIES, EVENTS)], **getters)
    import logging

    monkeypatch.setattr(helper_mod, "_absence_warned", set())  # restored after
    with caplog.at_level(logging.WARNING):
        s = _summary(fd, version="22.02")
        _summary(fd, version="22.02")  # second call: no second warning
    assert math.isnan(s.optimum_delay)
    assert caplog.text.count("getOptimumDelay") == 1


def test_branch_name_fallback_to_getbranchname():
    fd = _FlightData(
        [_Branch(SERIES, EVENTS, name="Booster", accessor="getBranchName")], **GETTERS_2412
    )
    assert _summary(fd).branch_name == "Booster"


def test_unsimulated_raises_orlab_error():
    h = _helper(None)
    with pytest.raises(OrlabError, match="run_simulation"):
        h.get_summary(SimpleNamespace(getSimulatedData=lambda: None))


def test_branch_out_of_range_raises_indexerror():
    fd = _FlightData([_Branch(SERIES, EVENTS)], **GETTERS_2412)
    with pytest.raises(IndexError, match="branch 2"):
        _summary(fd, branch_number=2)


def test_booster_branch_no_launchrod_no_deployment():
    """Branch >0 derives from its own series; without LAUNCHROD the window
    starts at the first sample and off-rod fields are NaN; without a
    deployment the descent fields are NaN."""
    events = {"IGNITION": [0.0], "APOGEE": [3.5], "GROUND_HIT": [16.0]}
    booster = _Branch(SERIES, events, name="Booster")
    fd = _FlightData([_Branch(SERIES, EVENTS), booster], **GETTERS_2412)
    s = _summary(fd, branch_number=1)
    assert math.isnan(s.velocity_off_rod)
    assert math.isnan(s.stability_off_rod_cal)
    assert math.isnan(s.velocity_at_deployment)
    assert math.isnan(s.descent_rate)
    assert s.min_stability_cal == 3.0  # window still ends at APOGEE
    assert s.apogee == 51.2  # derived from the branch's own series
    assert s.time_to_apogee == 3.5  # event time, not FlightData getter
    assert math.isnan(s.optimum_delay)  # per-flight, never per-branch
    assert s.branch_number == 1 and s.branch_count == 2


def test_degenerate_flight_degrades_to_nan_never_raises():
    empty = {name: [] for name in SERIES}
    fd = _FlightData([_Branch(empty, {})], **GETTERS_2412)
    s = _summary(fd)
    assert math.isnan(s.min_stability_cal)
    assert math.isnan(s.descent_rate)
    assert math.isnan(s.landing_x)
    assert math.isnan(s.landing_bearing_deg)


# --- the FlightSummary contract ---


def _full_summary():
    fd = _FlightData([_Branch(SERIES, EVENTS)], warnings=("w",), **GETTERS_2412)
    return _summary(fd)


def test_every_field_is_builtin_typed():
    """The process-boundary contract: no jpype or numpy scalar may survive
    into a FlightSummary."""
    s = _full_summary()
    for f in fields(s):
        value = getattr(s, f.name)
        assert type(value) in (float, int, str, tuple), f"{f.name} is {type(value)}"
        if isinstance(value, tuple):
            assert all(type(item) is str for item in value)


def test_units_cover_every_float_field():
    s = _full_summary()
    for f in fields(s):
        if type(getattr(s, f.name)) is float:
            assert f.name in FlightSummary.UNITS, f"no unit for {f.name}"


def test_str_renders_every_field():
    s = _full_summary()
    text = str(s)
    for f in fields(s):
        if f.name == "warnings":
            assert "Warnings" in text
        elif f.name in ("branch_number", "branch_name", "branch_count"):
            # the header line: "branch 0 of 1 (Sustainer)"
            assert f"branch {s.branch_number} of {s.branch_count} ({s.branch_name})" in text
        else:
            # a rendered value line, not a substring anywhere ("apogee" also
            # occurs inside "time to apogee" — the label match must be exact)
            label = f"\n    {f.name.replace('_', ' ')}:"
            assert label in text, f"{f.name} missing from __str__"
    assert "n/a" not in text  # this summary has no NaN fields


def test_str_renders_nan_as_na():
    empty = {name: [] for name in SERIES}
    fd = _FlightData([_Branch(empty, {})], **GETTERS_2412)
    assert "n/a" in str(_summary(fd))


def test_to_dict_round_trip_and_pickle():
    s = _full_summary()
    d = s.to_dict()
    assert FlightSummary(**d) == s
    assert pickle.loads(pickle.dumps(s)) == s
