"""Profile registry, selection, and enum-union consistency — no jar, no JVM."""

import pytest

from orlab import FlightDataType, FlightEvent, Helper
from orlab.core.version import parse_version
from orlab.errors import UnsupportedFlightDataType, UnsupportedOpenRocketVersion
from orlab.profiles import get_profile, profiles, versions_with


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
