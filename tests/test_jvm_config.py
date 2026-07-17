"""JVM configuration and seed control — no JVM; jpype calls are captured."""

import zipfile

import pytest

import orlab.core.openrocket_instance as oi
from orlab import Helper, OpenRocketInstance


def _fake_jar(tmp_path, version="24.12"):
    jar = tmp_path / "fake.jar"
    with zipfile.ZipFile(jar, "w") as z:
        z.writestr("build.properties", f"build.version={version}\n")
    return str(jar)


@pytest.fixture
def captured_start(monkeypatch):
    """Stubs everything __enter__ touches after argument building and captures
    the startJVM call."""
    calls = {}

    def fake_start(jvm_path, *args):
        calls["jvm_path"] = jvm_path
        calls["args"] = args

    monkeypatch.setattr(oi.jpype, "isJVMStarted", lambda: False)
    monkeypatch.setattr(oi.jpype, "startJVM", fake_start)
    monkeypatch.setattr(oi.jpype, "getDefaultJVMPath", lambda: "/detected/libjvm.so")
    monkeypatch.setattr(OpenRocketInstance, "_start_openrocket", lambda self: None)
    monkeypatch.setattr(OpenRocketInstance, "_warn_on_profile_drift", lambda self: None)
    # __enter__ reassigns these module globals; register them with monkeypatch
    # so teardown restores pristine state for other tests
    monkeypatch.setattr(oi, "_active_jar_path", None)
    monkeypatch.setattr(oi, "_active_core_root", None)
    return calls


def test_jvm_args_rejects_plain_string(tmp_path):
    with pytest.raises(TypeError, match="sequence of strings"):
        OpenRocketInstance(jar_path=_fake_jar(tmp_path), jvm_args="-Xmx4g")


def test_reuse_warns_when_jvm_args_have_no_effect(tmp_path, captured_start, monkeypatch, caplog):
    import logging
    import os

    jar = _fake_jar(tmp_path)
    first = OpenRocketInstance(jar_path=jar, jvm_args=["-Xmx2g"])
    first.__enter__()

    monkeypatch.setattr(oi.jpype, "isJVMStarted", lambda: True)
    monkeypatch.setattr(oi, "_active_jar_path", os.path.abspath(jar))
    monkeypatch.setattr(oi, "_jpackage", lambda dotted: None)
    monkeypatch.setattr(OpenRocketInstance, "_set_or_log_level", lambda self: None)

    second = OpenRocketInstance(jar_path=jar, jvm_args=["-Xmx8g"])
    with caplog.at_level(logging.WARNING, logger="orlab.core.openrocket_instance"):
        second.__enter__()
    assert any("no effect" in r.message for r in caplog.records)

    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="orlab.core.openrocket_instance"):
        first.__enter__()  # the instance that started the JVM must not warn
    assert not caplog.records


def test_jvm_args_and_path_reach_startjvm(tmp_path, captured_start):
    instance = OpenRocketInstance(
        jar_path=_fake_jar(tmp_path),
        jvm_path="/custom/libjvm.so",
        jvm_args=["-Xmx4g", "-Dfoo=bar"],
    )
    instance.__enter__()
    assert captured_start["jvm_path"] == "/custom/libjvm.so"
    assert captured_start["args"][-2:] == ("-Xmx4g", "-Dfoo=bar")


def test_default_jvm_path_detected(tmp_path, captured_start):
    OpenRocketInstance(jar_path=_fake_jar(tmp_path)).__enter__()
    assert captured_start["jvm_path"] == "/detected/libjvm.so"


def test_manual_jvm_path_deprecated_but_honored(tmp_path, captured_start, monkeypatch):
    monkeypatch.setattr(OpenRocketInstance, "MANUAL_JVM_PATH", "/legacy/libjvm.so")
    with pytest.warns(DeprecationWarning, match="jvm_path"):
        OpenRocketInstance(jar_path=_fake_jar(tmp_path)).__enter__()
    assert captured_start["jvm_path"] == "/legacy/libjvm.so"


def test_jvm_path_param_wins_over_manual(tmp_path, captured_start, monkeypatch):
    monkeypatch.setattr(OpenRocketInstance, "MANUAL_JVM_PATH", "/legacy/libjvm.so")
    OpenRocketInstance(jar_path=_fake_jar(tmp_path), jvm_path="/custom/libjvm.so").__enter__()
    assert captured_start["jvm_path"] == "/custom/libjvm.so"


class FakeOptions:
    def __init__(self):
        self.randomized = 0

    def randomizeSeed(self):
        self.randomized += 1


class FakeSim:
    def __init__(self):
        self.options = FakeOptions()
        self.simulated = 0

    def getOptions(self):
        return self.options

    def simulate(self, listener_array):
        self.simulated += 1


class FakeInstance:
    started = True
    or_version = "24.12"

    class openrocket:
        class simulation:
            class listeners:
                AbstractSimulationListener = object


@pytest.fixture
def helper(monkeypatch):
    monkeypatch.setattr("orlab.core.helper.jpype.JArray", lambda cls, dims: lambda n: [])
    return Helper(FakeInstance())


def test_run_simulation_randomizes_seed_by_default(helper):
    sim = FakeSim()
    helper.run_simulation(sim)
    assert sim.options.randomized == 1
    assert sim.simulated == 1


def test_run_simulation_respects_fixed_seed(helper):
    sim = FakeSim()
    helper.run_simulation(sim, randomize_seed=False)
    assert sim.options.randomized == 0
    assert sim.simulated == 1
