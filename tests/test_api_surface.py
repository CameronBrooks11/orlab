def test_public_surface_stable():
    import orlab

    assert sorted(orlab.__all__) == [
        "AbstractSimulationListener",
        "FlightDataType",
        "FlightEvent",
        "FlightSummary",
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

    assert sorted(orlab.jars.__all__) == [
        "Installed",
        "fetch_jar",
        "find_installed",
        "jar_cache_dir",
    ]
    for name in orlab.jars.__all__:
        assert getattr(orlab.jars, name) is not None


def test_parallel_surface_stable():
    import orlab.parallel

    assert sorted(orlab.parallel.__all__) == ["DECLARATIVE_KEYS", "DeclarativeKey"]
    assert sorted(orlab.parallel.DECLARATIVE_KEYS) == [
        "launch_altitude",
        "launch_into_wind",
        "launch_latitude",
        "launch_longitude",
        "launch_rod_angle",
        "launch_rod_direction",
        "launch_rod_length",
        "wind_direction",
        "wind_speed_average",
    ]
    # launch_into_wind must precede launch_rod_direction in declaration
    # order: appliers that iterate the mapping get round-trip semantics
    keys = list(orlab.parallel.DECLARATIVE_KEYS)
    assert keys.index("launch_into_wind") < keys.index("launch_rod_direction")
    for spec in orlab.parallel.DECLARATIVE_KEYS.values():
        assert spec.setter.startswith("set") and spec.getter.startswith("get")
        assert spec.kind in (float, bool)


def test_enums_are_coherent():
    from orlab import FlightDataType, FlightEvent, OrLogLevel

    assert all(m.name.startswith("TYPE_") for m in FlightDataType)
    assert len({m.name for m in FlightDataType}) == len(list(FlightDataType))
    assert {"LAUNCH", "APOGEE", "GROUND_HIT"} <= {m.name for m in FlightEvent}
    assert {"ERROR", "WARN", "INFO", "DEBUG"} <= {m.name for m in OrLogLevel}
