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
        "fetch_jar",
    ]
    for name in orlab.__all__:
        assert getattr(orlab, name) is not None


def test_errors_surface_stable():
    """Exception types escape through public entry points — they are public API."""
    import orlab.errors

    assert sorted(orlab.errors.__all__) == [
        "JarVerificationError",
        "NotAnOpenRocketJar",
        "OrlabError",
        "UnsupportedFlightDataType",
        "UnsupportedOpenRocketVersion",
    ]
    for name in orlab.errors.__all__:
        assert issubclass(getattr(orlab.errors, name), Exception)


def test_jars_surface_stable():
    import orlab.jars

    assert sorted(orlab.jars.__all__) == ["fetch_jar", "jar_cache_dir"]
    for name in orlab.jars.__all__:
        assert getattr(orlab.jars, name) is not None


def test_enums_are_coherent():
    from orlab import FlightDataType, FlightEvent, OrLogLevel

    assert all(m.name.startswith("TYPE_") for m in FlightDataType)
    assert len({m.name for m in FlightDataType}) == len(list(FlightDataType))
    assert {"LAUNCH", "APOGEE", "GROUND_HIT"} <= {m.name for m in FlightEvent}
    assert {"ERROR", "WARN", "INFO", "DEBUG"} <= {m.name for m in OrLogLevel}
