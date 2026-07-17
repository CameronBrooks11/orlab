"""Profile registry, selection, generated artifacts — no jar, no JVM."""

import importlib
import importlib.util
import logging
import re
import zipfile
from pathlib import Path

import pytest

from orlab import FlightDataType, FlightEvent, Helper, OpenRocketInstance
from orlab.core.version import parse_version
from orlab.errors import UnsupportedFlightDataType, UnsupportedOpenRocketVersion
from orlab.profiles import get_profile, profiles, versions_with

REPO = Path(__file__).parent.parent
PROFILES_DIR = REPO / "src" / "orlab" / "profiles"


def _load_tool(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_registry_contents():
    assert sorted(profiles) == [(15, 3), (22, 2), (23, 9), (24, 12)]
    for p in profiles.values():
        assert p.flight_data_types and p.flight_events
        assert p.startup in ("gui", "core")
    assert profiles[(24, 12)].startup == "core"
    assert profiles[(23, 9)].startup == "gui"
    assert profiles[(24, 12)].core_root == "info.openrocket.core"
    assert profiles[(23, 9)].core_root == "net.sf.openrocket"


@pytest.mark.parametrize(
    ("version", "expected", "exact"),
    [
        ("23.09", (23, 9), True),
        ("24.12", (24, 12), True),
        ("24.12.RC.01", (24, 12), True),
        ("23.10", (23, 9), False),
        ("26.xx-SNAPSHOT", (24, 12), False),
        ("25.xx.SNAPSHOT", (24, 12), False),
    ],
)
def test_get_profile_selection(version, expected, exact):
    profile, is_exact = get_profile(version)
    assert profile.version == expected
    assert is_exact is exact


def test_get_profile_too_old():
    with pytest.raises(UnsupportedOpenRocketVersion, match="15.03"):
        get_profile("14.11")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("26.xx-SNAPSHOT", (26, 0)),
        ("25.xx.SNAPSHOT", (25, 0)),
        ("24", (24, 0)),
    ],
)
def test_parse_version_snapshots(raw, expected):
    assert parse_version(raw) == expected


def test_versions_with():
    assert versions_with("TYPE_PROPELLANT_MASS") == ("15.03",)
    assert versions_with("TYPE_MOTOR_MASS") == ("22.02", "23.09", "24.12")
    assert versions_with("TYPE_WIND_DIRECTION") == ("24.12",)
    assert versions_with("TYPE_ALTITUDE") == ("15.03", "22.02", "23.09", "24.12")
    assert versions_with("TYPE_NOPE") == ()


def test_enums_match_profile_union():
    """_enums.py is generated from the profiles; hand edits or a forgotten
    regeneration show up here."""
    fdt_union = set().union(*(p.flight_data_types for p in profiles.values()))
    ev_union = set().union(*(p.flight_events for p in profiles.values()))
    assert {m.name for m in FlightDataType} == fdt_union
    assert {m.name for m in FlightEvent} == ev_union


def test_enums_file_is_regeneration_identical():
    """The committed _enums.py is byte-identical to what the generator renders."""
    generate_enums = _load_tool("generate_enums")
    assert generate_enums.render_enums() == (REPO / "src" / "orlab" / "_enums.py").read_text(
        encoding="utf-8"
    )


def test_profile_files_are_regeneration_identical():
    """Each committed profile is byte-identical to a re-render of its own facts
    (guards hand edits; full regeneration from the jar is verified live)."""
    generate_profile = _load_tool("generate_profile")
    for path in sorted(PROFILES_DIR.glob("or_*.py")):
        mod = importlib.import_module(f"orlab.profiles.{path.stem}")
        jar_name = re.search(r"jar: (\S+)", mod.__doc__).group(1)
        sha256 = re.search(r"sha256: (\w+)", mod.__doc__).group(1)
        rendered = generate_profile.render_profile(
            mod.VERSION_STRING,
            jar_name,
            sha256,
            mod.CORE_ROOT,
            mod.SWING_ROOT,
            mod.STARTUP,
            mod.FLIGHT_DATA_TYPES,
            mod.FLIGHT_EVENTS,
        )
        assert rendered == path.read_text(encoding="utf-8"), path.name


def test_no_orphan_profile_modules():
    """Every generated profile module is registered in the registry."""
    on_disk = {path.stem for path in PROFILES_DIR.glob("or_*.py")}
    registered = {f"or_{v[0]:02d}_{v[1]:02d}" for v in profiles}
    assert on_disk == registered


def _fake_jar(tmp_path, version):
    jar = tmp_path / f"fake-{version}.jar"
    with zipfile.ZipFile(jar, "w") as z:
        z.writestr("build.properties", f"build.version={version}\n")
    return str(jar)


def test_instance_warns_on_fallback_profile(tmp_path, caplog):
    with caplog.at_level(logging.WARNING, logger="orlab.core.openrocket_instance"):
        instance = OpenRocketInstance(jar_path=_fake_jar(tmp_path, "26.xx-SNAPSHOT"))
    assert instance.profile.version == (24, 12)
    assert any("nearest older" in r.message for r in caplog.records)


def test_instance_rejects_too_old_jar(tmp_path):
    with pytest.raises(UnsupportedOpenRocketVersion, match="15.03"):
        OpenRocketInstance(jar_path=_fake_jar(tmp_path, "14.11"))


class FakeJavaClass:
    """The java.lang.Class side of a JClass: .class_.getDeclaredFields()."""

    def __init__(self, fields):
        self._fields = fields

    def getDeclaredFields(self):
        return self._fields


class FakeField:
    def __init__(self, name, typ):
        self._name, self._type = name, typ

    def getName(self):
        return self._name

    def getType(self):
        return self._type


class FakeEnumConstant:
    def __init__(self, name):
        self._name = name

    def name(self):
        return self._name


def _fake_openrocket(type_names, event_names):
    fdt_class = FakeJavaClass([])
    fdt_class._fields = [FakeField(n, fdt_class) for n in type_names]

    class FakeFDT:
        class_ = fdt_class

    class FakeEventType:
        @staticmethod
        def values():
            return [FakeEnumConstant(n) for n in event_names]

    class FakeFlightEvent:
        Type = FakeEventType

    class FakeSimulation:
        FlightDataType = FakeFDT
        FlightEvent = FakeFlightEvent

    class FakeOpenRocket:
        simulation = FakeSimulation

    return FakeOpenRocket


def _bare_instance(openrocket, profile):
    instance = OpenRocketInstance.__new__(OpenRocketInstance)
    instance.openrocket = openrocket
    instance.profile = profile
    instance.or_version = profile.version_string
    return instance


def test_drift_alarm_warns_both_directions(caplog):
    profile = profiles[(23, 9)]
    live_types = set(profile.flight_data_types) | {"TYPE_BRAND_NEW"}
    live_events = set(profile.flight_events) - {"APOGEE"}
    instance = _bare_instance(_fake_openrocket(live_types, live_events), profile)

    with caplog.at_level(logging.WARNING, logger="orlab.core.openrocket_instance"):
        instance._warn_on_profile_drift()

    messages = " | ".join(r.message for r in caplog.records)
    assert "TYPE_BRAND_NEW" in messages
    assert "APOGEE" in messages


def test_drift_alarm_never_aborts_startup(caplog):
    class Hostile:
        def __getattr__(self, name):
            raise AttributeError(name)

    instance = _bare_instance(Hostile(), profiles[(23, 9)])
    with caplog.at_level(logging.WARNING, logger="orlab.core.openrocket_instance"):
        instance._warn_on_profile_drift()
    assert any("drift check failed" in r.message for r in caplog.records)


class FakeJavaFlightDataType:
    """Java FlightDataType surface of a 23.09-era jar: modern names, no 24.12
    additions, no 15.03-only names."""

    TYPE_ALTITUDE = object()
    TYPE_MOTOR_MASS = object()


class FakeOpenRocket:
    class simulation:
        FlightDataType = FakeJavaFlightDataType


class FakeInstance:
    started = True
    openrocket = FakeOpenRocket
    or_version = "23.09"


@pytest.fixture
def helper():
    return Helper(FakeInstance())


def test_translate_data_type_present(helper):
    assert (
        helper.translate_flight_data_type(FlightDataType.TYPE_ALTITUDE)
        is FakeJavaFlightDataType.TYPE_ALTITUDE
    )
    assert (
        helper.translate_flight_data_type("TYPE_MOTOR_MASS")
        is FakeJavaFlightDataType.TYPE_MOTOR_MASS
    )


def test_translate_data_type_from_newer_version(helper):
    with pytest.raises(UnsupportedFlightDataType, match=r"available in: 24\.12"):
        helper.translate_flight_data_type(FlightDataType.TYPE_WIND_DIRECTION)


def test_translate_data_type_renamed(helper):
    with pytest.raises(UnsupportedFlightDataType, match=r"available in: 15\.03"):
        helper.translate_flight_data_type(FlightDataType.TYPE_PROPELLANT_MASS)


def test_translate_data_type_unknown_string(helper):
    with pytest.raises(UnsupportedFlightDataType, match="unknown constant"):
        helper.translate_flight_data_type("TYPE_NOPE")
