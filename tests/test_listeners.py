"""Dispersion listeners and the typed finder, jar-free: validation, the
pure interpolation math, pickle/spawn/copy contracts."""

import copy
import math
import multiprocessing
import pickle

import pytest

from orlab.listeners import ThrustFactor, WindProfile


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"altitudes_m": [0, 10], "speeds_ms": [5]}, "lengths differ"),
        ({"altitudes_m": [], "speeds_ms": []}, "at least one"),
        ({"altitudes_m": [0, 10, 10], "speeds_ms": [1, 2, 3]}, "strictly increasing"),
        ({"altitudes_m": [10, 0], "speeds_ms": [1, 2]}, "strictly increasing"),
        ({"altitudes_m": [0, 10], "speeds_ms": [1, -2]}, "negative"),
        ({"altitudes_m": [0, 10], "speeds_ms": [1, 2], "directions_rad": [0.1]}, "lengths differ"),
    ],
)
def test_wind_profile_validation(kwargs, match):
    with pytest.raises(ValueError, match=match):
        WindProfile(**kwargs)


def test_wind_at_interpolation_and_clamping():
    profile = WindProfile([0.0, 10.0], [0.0, 10.0])  # from north
    assert profile._wind_at(5.0) == (pytest.approx(0.0), pytest.approx(5.0))
    assert profile._wind_at(-3.0)[1] == pytest.approx(0.0)  # clamped below
    assert profile._wind_at(50.0)[1] == pytest.approx(10.0)  # clamped above


def test_wind_at_vector_interpolation_no_wraparound():
    """359° -> 1° must interpolate through north (v stays ~+speed), not
    swing the long way through south — the reason components, not angles,
    are interpolated."""
    directions = [math.radians(359.0), math.radians(1.0)]
    profile = WindProfile([0.0, 10.0], [5.0, 5.0], directions_rad=directions)
    u, v = profile._wind_at(5.0)
    assert v == pytest.approx(5.0, abs=0.01)  # still blowing from ~north
    assert abs(u) < 0.1


def test_wind_direction_convention_matches_meteorological():
    """directions_rad=pi/2 means wind FROM the east: vector +u (east
    component), zero v — the convention setWindDirection uses (pinned
    against real flights in the integration case)."""
    profile = WindProfile([0.0, 10.0], [5.0, 5.0], directions_rad=math.pi / 2)
    u, v = profile._wind_at(5.0)
    assert u == pytest.approx(5.0)
    assert v == pytest.approx(0.0, abs=1e-12)


def test_scalar_direction_broadcasts():
    profile = WindProfile([0.0, 10.0, 20.0], [1.0, 2.0, 3.0], directions_rad=0.5)
    assert len(profile.u) == 3


@pytest.mark.parametrize("factor", [0.0, -1.5, float("nan")])
def test_thrust_factor_validation(factor):
    with pytest.raises(ValueError, match="positive"):
        ThrustFactor(factor)


def test_thrust_factor_arithmetic():
    assert ThrustFactor(1.5).postSimpleThrustCalculation(None, 30.0) == pytest.approx(45.0)


def _child_check(listener_bytes, queue):
    import jpype

    loaded = pickle.loads(listener_bytes)
    queue.put((jpype.isJVMStarted(), type(loaded).__name__, float(loaded._wind_at(5.0)[1])))


def test_listeners_pickle_copy_and_spawn_round_trip():
    """SimulationPool workers receive listeners by pickle, and OpenRocket
    clones them: both operations must work with no JVM anywhere."""
    profile = WindProfile([0.0, 10.0], [5.0, 5.0])
    factor = ThrustFactor(1.2)
    assert copy.copy(profile)._wind_at(5.0) == profile._wind_at(5.0)
    assert copy.copy(factor).factor == 1.2
    assert pickle.loads(pickle.dumps(factor)).factor == 1.2

    ctx = multiprocessing.get_context("spawn")
    queue = ctx.Queue()
    child = ctx.Process(target=_child_check, args=(pickle.dumps(profile), queue))
    child.start()
    try:
        jvm_started, type_name, v_at_5 = queue.get(timeout=60)
    except Exception:
        child.join(timeout=5)
        pytest.fail(f"spawn child produced nothing (exitcode={child.exitcode})")
    child.join(timeout=60)
    assert jvm_started is False  # the child never had a JVM
    assert type_name == "WindProfile"
    assert v_at_5 == pytest.approx(5.0)


def test_get_components_of_type_unknown_name():
    from types import SimpleNamespace

    from orlab import Helper

    h = Helper.__new__(Helper)
    h._instance = SimpleNamespace(or_version="24.12")
    h.openrocket = SimpleNamespace(rocketcomponent=SimpleNamespace())
    with pytest.raises(ValueError, match="not a rocket-component class in OpenRocket 24.12"):
        h.get_components_of_type(None, "NoSuchComponent")
