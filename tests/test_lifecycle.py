"""JVM lifecycle guards — no JVM started; jpype module state is monkeypatched."""

import os
import zipfile

import pytest

import orlab.core.openrocket_instance as oi
from orlab import OpenRocketInstance
from orlab.errors import OrlabError


def _fake_jar(tmp_path, version="23.09"):
    jar = tmp_path / "fake.jar"
    with zipfile.ZipFile(jar, "w") as z:
        z.writestr("build.properties", f"build.version={version}\n")
    return str(jar)


def test_different_jar_raises_clear_error(tmp_path, monkeypatch):
    instance = OpenRocketInstance(jar_path=_fake_jar(tmp_path))
    monkeypatch.setattr(oi.jpype, "isJVMStarted", lambda: True)
    monkeypatch.setattr(oi, "_active_jar_path", "/elsewhere/OpenRocket-24.12.jar")
    with pytest.raises(OrlabError, match="already running with /elsewhere"):
        instance.__enter__()


def test_incomplete_startup_raises_clear_error(tmp_path, monkeypatch):
    instance = OpenRocketInstance(jar_path=_fake_jar(tmp_path))
    monkeypatch.setattr(oi.jpype, "isJVMStarted", lambda: True)
    monkeypatch.setattr(oi, "_active_jar_path", None)
    with pytest.raises(OrlabError, match="never completed"):
        instance.__enter__()


def test_same_jar_reuses_running_jvm(tmp_path, monkeypatch):
    jar = _fake_jar(tmp_path)
    instance = OpenRocketInstance(jar_path=jar)
    sentinel = object()
    monkeypatch.setattr(oi.jpype, "isJVMStarted", lambda: True)
    monkeypatch.setattr(oi, "_active_jar_path", os.path.abspath(jar))
    monkeypatch.setattr(oi, "_active_core_root", sentinel)
    monkeypatch.setattr(oi, "_jpackage", lambda dotted: f"pkg:{dotted}")
    monkeypatch.setattr(OpenRocketInstance, "_set_or_log_level", lambda self: None)

    assert instance.__enter__() is instance
    assert instance.started
    assert instance.openrocket is sentinel

    # __exit__ bookkeeping without a live JVM (the fake isJVMStarted would
    # otherwise send it into real java.awt imports)
    monkeypatch.setattr(oi.jpype, "isJVMStarted", lambda: False)
    instance.__exit__(None, None, None)
    assert not instance.started
