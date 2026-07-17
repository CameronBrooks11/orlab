"""Flight-event translation against fake Java objects — no jar, no JVM."""

import logging

import pytest

from orlab import FlightEvent, Helper


class FakeJavaEventType:
    """Mimics a Java FlightEvent.Type enum constant (has .name())."""

    def __init__(self, name: str):
        self._name = name

    def name(self) -> str:
        return self._name


class FakeEvent:
    def __init__(self, type_name: str, time: float):
        self._type = FakeJavaEventType(type_name)
        self._time = time

    def getType(self):
        return self._type

    def getTime(self) -> float:
        return self._time


class FakeBranch:
    def __init__(self, events):
        self._events = events

    def getEvents(self):
        return self._events


class FakeSimulation:
    def __init__(self, events):
        self._branch = FakeBranch(events)

    def getSimulatedData(self):
        return self

    def getBranch(self, n):
        return self._branch


class FakeInstance:
    started = True
    openrocket = None


@pytest.fixture
def helper():
    return Helper(FakeInstance())


@pytest.mark.parametrize("name", ["LAUNCH", "APOGEE", "GROUND_HIT", "SIM_WARN", "SIM_ABORT"])
def test_translate_known_event(helper, name):
    assert helper.translate_flight_event(FakeJavaEventType(name)) is FlightEvent[name]


def test_translate_unknown_event_raises_value_error(helper):
    with pytest.raises(ValueError, match="SOME_FUTURE_EVENT"):
        helper.translate_flight_event(FakeJavaEventType("SOME_FUTURE_EVENT"))


def test_get_events_collects_times_per_type(helper):
    sim = FakeSimulation(
        [
            FakeEvent("LAUNCH", 0.0),
            FakeEvent("SIM_WARN", 0.5),
            FakeEvent("SIM_WARN", 1.2),
            FakeEvent("APOGEE", 3.4),
            FakeEvent("GROUND_HIT", 9.9),
        ]
    )
    events = helper.get_events(sim)
    assert events[FlightEvent.LAUNCH] == [0.0]
    assert events[FlightEvent.SIM_WARN] == [0.5, 1.2]
    assert events[FlightEvent.APOGEE] == [3.4]
    assert events[FlightEvent.GROUND_HIT] == [9.9]


def test_get_events_skips_unknown_types_with_one_warning(helper, caplog):
    sim = FakeSimulation(
        [
            FakeEvent("LAUNCH", 0.0),
            FakeEvent("SOME_FUTURE_EVENT", 1.0),
            FakeEvent("SOME_FUTURE_EVENT", 2.0),
            FakeEvent("APOGEE", 3.0),
        ]
    )
    with caplog.at_level(logging.WARNING, logger="orlab.core.helper"):
        events = helper.get_events(sim)

    assert events == {FlightEvent.LAUNCH: [0.0], FlightEvent.APOGEE: [3.0]}
    warnings = [r for r in caplog.records if "SOME_FUTURE_EVENT" in r.message]
    assert len(warnings) == 1
