"""Installed-OpenRocket discovery: layouts, JRE gating, never-raise, and
its isolation from the default resolution chain."""

import zipfile

import pytest

import orlab.jars as jars
from orlab.core.openrocket_instance import _resolve_default_jar


@pytest.fixture(autouse=True)
def _no_ambient_discovery(monkeypatch, tmp_path):
    """These tests must see only their synthetic trees — not this machine's
    real installs, env, cwd, or cache."""
    monkeypatch.delenv("ORLAB_OR_INSTALL_DIR", raising=False)
    monkeypatch.delenv("ORLAB_JAR", raising=False)
    monkeypatch.delenv("CLASSPATH", raising=False)
    monkeypatch.setenv("ORLAB_JAR_CACHE", str(tmp_path / "cache"))
    monkeypatch.setattr(jars, "_platform_install_roots", lambda: [])
    monkeypatch.chdir(tmp_path)


def _write_jar(path, version="24.12"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("build.properties", f"build.version={version}\n")


def _write_jre(root, layout, java_version):
    """Creates a bundled-JRE skeleton: layout is 'linux', 'mac', or 'win'."""
    home, lib = {
        "linux": (root / "jre", root / "jre" / "lib" / "server" / "libjvm.so"),
        "mac": (
            root / "jre.bundle" / "Contents" / "Home",
            root / "jre.bundle" / "Contents" / "Home" / "lib" / "server" / "libjvm.dylib",
        ),
        "win": (root / "jre", root / "jre" / "bin" / "server" / "jvm.dll"),
    }[layout]
    lib.parent.mkdir(parents=True, exist_ok=True)
    lib.write_bytes(b"")
    if java_version is not None:
        (home / "release").write_text(f'JAVA_VERSION="{java_version}"\n', encoding="utf-8")
    return lib


@pytest.mark.parametrize("layout", ["linux", "mac", "win"])
def test_modern_layout_with_java17_jre(tmp_path, monkeypatch, layout):
    root = tmp_path / "install"
    _write_jar(root / "jar" / "OpenRocket-24.12.jar")
    lib = _write_jre(root, layout, "17.0.16")
    monkeypatch.setenv("ORLAB_OR_INSTALL_DIR", str(root))

    inst = jars.find_installed()
    assert inst == jars.Installed(
        jar=root / "jar" / "OpenRocket-24.12.jar", jvm=lib, version="24.12"
    )


def test_legacy_root_jar_layout_and_old_jre(tmp_path, monkeypatch):
    root = tmp_path / "install"
    _write_jar(root / "OpenRocket.jar", version="22.02")
    _write_jre(root, "linux", "11.0.2")  # pre-17: jar usable, jvm not
    monkeypatch.setenv("ORLAB_OR_INSTALL_DIR", str(root))

    inst = jars.find_installed()
    assert inst is not None
    assert inst.version == "22.02"
    assert inst.jar == root / "OpenRocket.jar"
    assert inst.jvm is None


@pytest.mark.parametrize("java_version", ["1.8.0_345", "11.0.2", None])
def test_jre_gate_rejects_pre17_and_missing_release(tmp_path, monkeypatch, java_version):
    root = tmp_path / "install"
    _write_jar(root / "jar" / "OpenRocket-24.12.jar")
    _write_jre(root, "linux", java_version)
    monkeypatch.setenv("ORLAB_OR_INSTALL_DIR", str(root))

    inst = jars.find_installed()
    assert inst is not None and inst.jvm is None


def test_newest_versioned_jar_wins(tmp_path, monkeypatch):
    root = tmp_path / "install"
    _write_jar(root / "jar" / "OpenRocket-23.09.jar", version="23.09")
    _write_jar(root / "jar" / "OpenRocket-24.12.jar", version="24.12")
    monkeypatch.setenv("ORLAB_OR_INSTALL_DIR", str(root))

    inst = jars.find_installed()
    assert inst is not None and inst.version == "24.12"


def test_empty_override_disables_discovery(tmp_path, monkeypatch):
    monkeypatch.setattr(
        jars, "_platform_install_roots", lambda: pytest.fail("probed despite disable")
    )
    monkeypatch.setenv("ORLAB_OR_INSTALL_DIR", "")
    assert jars.find_installed() is None


@pytest.mark.parametrize(
    "make_root",
    [
        lambda root: None,  # missing entirely
        lambda root: root.mkdir(parents=True),  # empty dir
        lambda root: _write_jar(root / "jar" / "OpenRocket-24.12.jar", version="banana"),
        lambda root: (
            (root / "jar").mkdir(parents=True),
            (root / "jar" / "OpenRocket-24.12.jar").write_text("not a zip"),
        ),
    ],
    ids=["missing-root", "empty-root", "unparseable-version", "not-a-zip"],
)
def test_garbage_candidates_never_raise(tmp_path, monkeypatch, make_root):
    root = tmp_path / "install"
    make_root(root)
    monkeypatch.setenv("ORLAB_OR_INSTALL_DIR", str(root))
    assert jars.find_installed() is None


def test_desktop_exec_parsing(tmp_path, monkeypatch):
    """The real install4j format: quoted launcher path plus %U field code;
    the launcher's parent is the install root."""
    apps = tmp_path / "home" / ".local" / "share" / "applications"
    apps.mkdir(parents=True)
    root = tmp_path / "opt" / "OpenRocket"
    root.mkdir(parents=True)
    (apps / "install4j_abc123-OpenRocket.desktop").write_text(
        f'[Desktop Entry]\nType=Application\nExec="{root}/OpenRocket"  %U\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(jars.Path, "home", classmethod(lambda cls: tmp_path / "home"))

    assert jars._desktop_install_roots() == [root]


@pytest.mark.parametrize("value", ["", '"unclosed quote', "   "])
def test_exec_parsing_tolerates_garbage(value):
    assert jars._parse_exec(value) is None


def test_instance_accepts_pathlike_jvm_path(tmp_path):
    """find_installed returns jvm as a Path; jpype's startJVM rejects
    PathLike, so OpenRocketInstance must coerce to str at construction."""
    from orlab import OpenRocketInstance

    jar = tmp_path / "fake.jar"
    _write_jar(jar)
    jvm = tmp_path / "libjvm.so"  # a Path, as find_installed returns
    instance = OpenRocketInstance(str(jar), jvm_path=jvm)
    assert instance.jvm_path == str(jvm)
    assert type(instance.jvm_path) is str


def test_chain_never_calls_discovery(tmp_path, monkeypatch):
    monkeypatch.setattr(
        jars, "find_installed", lambda: pytest.fail("resolution chain called find_installed")
    )
    jar = tmp_path / "explicit.jar"
    _write_jar(jar)
    monkeypatch.setenv("ORLAB_JAR", str(jar))
    assert _resolve_default_jar() == (str(jar), "ORLAB_JAR")
    monkeypatch.delenv("ORLAB_JAR")
    with pytest.raises(FileNotFoundError):
        _resolve_default_jar()  # a full miss must not fall back to discovery
