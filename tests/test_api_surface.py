def test_public_surface_stable():
    import orlab

    assert sorted(orlab.__all__) == [
        "AbstractSimulationListener",
        "FlightDataType",
        "FlightEvent",
        "Helper",
        "JIterator",
        "OpenRocketInstance",
        "OrLogLevel",
    ]
    for name in orlab.__all__:
        assert getattr(orlab, name) is not None


def test_enums_are_coherent():
    from orlab import FlightDataType, FlightEvent, OrLogLevel

    assert all(m.name.startswith("TYPE_") for m in FlightDataType)
    assert len({m.name for m in FlightDataType}) == len(list(FlightDataType))
    assert {"LAUNCH", "APOGEE", "GROUND_HIT"} <= {m.name for m in FlightEvent}
    assert {"ERROR", "WARN", "INFO", "DEBUG"} <= {m.name for m in OrLogLevel}
