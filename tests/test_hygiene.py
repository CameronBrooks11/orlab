"""Library-hygiene behavior: logging, jar-path resolution, curated errors."""

import importlib
import logging
import zipfile

import pytest

import orlab.core.openrocket_instance
from orlab import Helper, OpenRocketInstance
from orlab.errors import NotAnOpenRocketJar, OrlabError


def test_import_does_not_configure_root_logger():
    root = logging.getLogger()
    before = list(root.handlers)
    importlib.reload(orlab.core.openrocket_instance)
    assert list(root.handlers) == before


def _fake_jar(tmp_path, version="23.09"):
    jar = tmp_path / "fake.jar"
    with zipfile.ZipFile(jar, "w") as z:
        z.writestr("build.properties", f"build.version={version}\n")
    return str(jar)


def test_jar_path_from_orlab_jar_env(tmp_path, monkeypatch):
    monkeypatch.setenv("ORLAB_JAR", _fake_jar(tmp_path))
    assert OpenRocketInstance().or_version == "23.09"


def test_jar_path_from_classpath_env(tmp_path, monkeypatch):
    monkeypatch.delenv("ORLAB_JAR", raising=False)
    monkeypatch.setenv("CLASSPATH", _fake_jar(tmp_path))
    assert OpenRocketInstance().or_version == "23.09"


def test_orlab_jar_wins_over_classpath(tmp_path, monkeypatch):
    monkeypatch.setenv("ORLAB_JAR", _fake_jar(tmp_path, "24.12"))
    monkeypatch.setenv("CLASSPATH", "/nonexistent/other.jar")
    assert OpenRocketInstance().or_version == "24.12"


def test_missing_jar_mentions_orlab_jar(tmp_path):
    with pytest.raises(FileNotFoundError, match="ORLAB_JAR"):
        OpenRocketInstance(jar_path=str(tmp_path / "missing.jar"))


@pytest.mark.parametrize(
    "make_file",
    [
        lambda p: p.write_text("not a zip at all"),
        lambda p: zipfile.ZipFile(p, "w").close(),  # zip without build.properties
    ],
    ids=["not-a-zip", "no-build-properties"],
)
def test_bad_jar_raises_curated_error(tmp_path, make_file):
    path = tmp_path / "bad.jar"
    make_file(path)
    with pytest.raises(NotAnOpenRocketJar, match="not an OpenRocket jar"):
        OpenRocketInstance(jar_path=str(path))


def test_helper_requires_started_instance(tmp_path):
    instance = OpenRocketInstance(jar_path=_fake_jar(tmp_path))
    with pytest.raises(OrlabError, match="not started"):
        Helper(instance)
