"""Importable stand-ins for SimulationPool behavioral tests.

Must live in an importable module (not inside a pytest test module): spawn
workers re-import everything by reference, and test-module paths are the
classic cross-OS import-flake source the Windows CI cell would hit.
"""

import os
import time


def ok_fn(helper, sim, task):
    return {"value": task.get("x", 0) * 2, "pid": os.getpid()}


def value_error_fn(helper, sim, task):
    raise ValueError(f"deliberate failure for task {task}")


def crash_fn(helper, sim, task):
    os._exit(17)  # simulates a worker process death (JVM crash / OOM)


def slow_fn(helper, sim, task):
    time.sleep(task.get("sleep", 0.2))
    return {"slept": True}


def unpicklable_payload_fn(helper, sim, task):
    return lambda: None  # the worker-side pickle check must catch this


class FakeOptions:
    """Records setter calls; genuine get/set semantics for every
    DECLARATIVE_KEYS entry plus the seed."""

    def __init__(self):
        self.values = {
            "setLaunchRodLength": 1.0,
            "setLaunchRodAngle": 0.0,
            "setLaunchIntoWind": True,
            "setLaunchRodDirection": 1.5707963267948966,
            "setLaunchAltitude": 0.0,
            "setLaunchLatitude": 45.0,
            "setLaunchLongitude": 0.0,
            "setWindSpeedAverage": 2.0,
            "setWindDirection": 1.5707963267948966,
            "setRandomSeed": 0,
        }
        self.set_log = []

    def __getattr__(self, name):
        if name.startswith("set"):

            def setter(value, _name=name):
                self.values[_name] = value
                self.set_log.append((_name, value))

            return setter
        if name.startswith("get"):
            return lambda _name=name: self.values["set" + _name[3:]]
        raise AttributeError(name)


class FakeSummary:
    apogee = 51.0
    max_velocity = 29.0
    max_acceleration = 140.0
    flight_time = 16.0
    landing_x = 1.0
    landing_y = 2.0


class FakeSim:
    def __init__(self):
        self.options = FakeOptions()
        self.runs = 0

    def getOptions(self):
        return self.options


class FakeHelper:
    def __init__(self, sim):
        self.sim = sim

    def run_simulation(self, sim, listeners=None, *, randomize_seed=True):
        sim.runs += 1

    def get_summary(self, sim):
        return FakeSummary()


def fake_init(worker_state):
    """JVM-free _test_init hook: populates worker state with the fakes."""
    sim = FakeSim()
    worker_state.update(
        helper=FakeHelper(sim),
        sim=sim,
        baseline={
            "launch_rod_length": 1.0,
            "launch_rod_angle": 0.0,
            "launch_into_wind": True,
            "launch_rod_direction": 1.5707963267948966,
            "launch_altitude": 0.0,
            "launch_latitude": 45.0,
            "launch_longitude": 0.0,
            "wind_speed_average": 2.0,
            "wind_direction": 1.5707963267948966,
        },
        init_error=None,
    )


def failing_init(worker_state):
    raise RuntimeError("deliberate init failure")


def echo_options_fn(helper, sim, task):
    """Returns the option values seen at task time — the state-bleed probe."""
    opts = sim.getOptions()
    return {"wind": opts.getWindSpeedAverage(), "length": opts.getLaunchRodLength()}
