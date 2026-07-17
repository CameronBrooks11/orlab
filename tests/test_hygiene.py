"""Library-hygiene behavior: logging, jar-path resolution, curated errors."""

import subprocess
import sys
import zipfile

import pytest

from orlab import Helper, OpenRocketInstance
from orlab.errors import NotAnOpenRocketJar, OrlabError


def test_import_does_not_configure_root_logger():
    """Must run in a fresh interpreter: under pytest the root logger already
    has handlers, which would make basicConfig (the regression) a no-op."""
    probe = (
        "import logging, orlab; "
        "assert not logging.getLogger().handlers, 'root logger got handlers'; "
        "assert logging.getLogger().level == logging.WARNING"
    )
    subprocess.run([sys.executable, "-c", probe], check=True, timeout=60)


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


def test_classpath_list_selects_first_existing_jar(tmp_path, monkeypatch):
    import os

    real = _fake_jar(tmp_path)
    monkeypatch.delenv("ORLAB_JAR", raising=False)
    monkeypatch.setenv("CLASSPATH", os.pathsep.join(["/nonexistent/a.jar", real, "/other/b.jar"]))
    assert OpenRocketInstance().or_version == "23.09"


def _zip_with_properties(p, content):
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("build.properties", content)


@pytest.mark.parametrize(
    "make_file",
    [
        lambda p: p.write_text("not a zip at all"),
        lambda p: zipfile.ZipFile(p, "w").close(),  # zip without build.properties
        lambda p: _zip_with_properties(p, "name=OpenRocket\n"),  # no build.version line
        lambda p: _zip_with_properties(p, "build.version=banana\n"),  # unparseable version
    ],
    ids=["not-a-zip", "no-build-properties", "no-build-version", "unparseable-version"],
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
