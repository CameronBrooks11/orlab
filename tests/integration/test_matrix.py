"""Per-version integration matrix: each case spawns a fresh Python (JPype
cannot restart a JVM in-process) running a script from cases/ against a real
OpenRocket jar, and asserts on its RESULT line.

Run with: just test-integration          (all versions)
          ORLAB_TEST_VERSION=24.12 ...   (one version, as in the CI matrix)
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

CASES = Path(__file__).parent / "cases"


def run_case(
    script: str, jar: Path | None, env: dict | None = None, cwd: Path | None = None
) -> dict:
    cmd = [sys.executable, str(CASES / script)]
    if jar is not None:
        cmd.append(str(jar))
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
        cwd=cwd,
    )
    assert proc.returncode == 0, f"{script} failed:\n{proc.stdout}\n{proc.stderr}"
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            return json.loads(line[len("RESULT ") :])
    raise AssertionError(f"{script} printed no RESULT line:\n{proc.stdout}")


def test_simulation_and_enum_surface(jar):
    """Full flight sanity plus the profile-corruption detector: on an exact
    profile the live jar's constants must match the profile exactly."""
    version, path = jar
    result = run_case("happy.py", path)

    assert result["version"] == version
    assert result["apogee"] > 10
    assert result["vmax"] > 5
    assert {"LAUNCH", "APOGEE", "GROUND_HIT", "SIMULATION_END"} <= set(result["events"])
    assert result["listener_calls"] > 10

    assert result["profile_version"] == version
    for key in ("extra_types", "missing_types", "extra_events", "missing_events"):
        assert result[key] == [], f"profile drift on {version}: {key}={result[key]}"


def test_warning_events_do_not_crash_get_events(jar):
    """Deployment under thrust: 24.12+ records SIM_WARN/SIM_ABORT events,
    which crashed get_events() before 0.3.1. Older versions must still
    return events without error."""
    version, path = jar
    result = run_case("warn.py", path)
    assert "RECOVERY_DEVICE_DEPLOYMENT" in result["events"]
    if version >= "24.12":
        assert "SIM_WARN" in result["events"]
        assert "SIM_ABORT" in result["events"]


def test_listener_exception_propagates(jar):
    """A Python exception raised in a listener surfaces as itself, with its
    message intact — documented behavior for the listener guide."""
    _, path = jar
    result = run_case("listener_raise.py", path)
    assert result["propagated"] == "RuntimeError"
    assert "boom from python listener" in result["message"]


def test_second_instance_reuses_jvm(jar):
    """Sequential with-blocks in one process work (the JVM is kept alive and
    reused); a different jar path in the same process is refused clearly."""
    _, path = jar
    result = run_case("reuse.py", path)
    assert result["first_apogee"] > 10
    assert result["second_apogee"] > 10
    assert result["conflict"] is not None
    assert "already running" in result["conflict"]


def test_zero_config_boot_from_cache(jar, tmp_path):
    """OpenRocketInstance() with no configuration at all: the resolution
    chain must find (and re-verify) the jar in the fetch_jar cache. The tmp
    cache holds only this cell's jar — copied, so the shared cache stays
    untouched — and cwd is empty."""
    version, path = jar
    cache = tmp_path / "cache"
    cache.mkdir()
    shutil.copy2(path, cache / path.name)
    env = {k: v for k, v in os.environ.items() if k not in ("ORLAB_JAR", "CLASSPATH")}
    env["ORLAB_JAR_CACHE"] = str(cache)

    result = run_case("zero_config.py", None, env=env, cwd=tmp_path)
    assert result["version"] == version
    assert Path(result["jar"]) == cache / path.name
    assert result["apogee"] > 10


def test_discovery_boot_from_fake_install(jar, tmp_path):
    """find_installed on an installer-layout tree (jar/ subdir), booted via
    the documented explicit two-liner. The fake tree has no bundled JRE, so
    this also covers the jvm=None path."""
    version, path = jar
    root = tmp_path / "install"
    (root / "jar").mkdir(parents=True)
    shutil.copy2(path, root / "jar" / path.name)
    env = {k: v for k, v in os.environ.items() if k not in ("ORLAB_JAR", "CLASSPATH")}
    env["ORLAB_OR_INSTALL_DIR"] = str(root)

    result = run_case("discovery_boot.py", None, env=env, cwd=tmp_path)
    assert result["version"] == version
    assert Path(result["jar"]) == root / "jar" / path.name
    assert result["apogee"] > 10


def test_summary_simple(jar):
    """get_summary on simple.ork: tight expectations under fixed seed + zero
    wind (bands recalibrated by probe under this exact configuration), coarse
    ones with wind on, and the pickle loaded HERE — in a process that has
    never started a JVM — proving the cross-process payload contract."""
    import base64
    import math
    import pickle

    version, path = jar
    result = run_case("summary.py", path)
    calm, windy = result["calm"], result["windy"]

    assert 40 < calm["apogee"] < 60
    assert 3.0 < calm["time_to_apogee"] < 4.0
    assert 14 < calm["velocity_off_rod"] < 17
    assert 2.0 < calm["stability_off_rod_cal"] < 4.0
    # the assertion that fails if 24.12 windowing regresses (blind min: -9.6)
    assert 0.5 < calm["min_stability_cal"] < 4.0
    assert 2.5 < calm["max_stability_cal"] < 7.0  # windowed peak is version-dependent (3.1-5.4)
    assert 0.05 < calm["max_mach"] < 0.12
    assert 3.0 < calm["descent_rate"] < 5.0
    assert 3.0 < calm["ground_hit_velocity"] < 5.0
    assert 14 < calm["flight_time"] < 18
    assert calm["landing_distance"] < 1.0
    assert math.isclose(
        calm["landing_distance"], math.hypot(calm["landing_x"], calm["landing_y"]), abs_tol=1e-6
    )
    assert math.isnan(calm["optimum_delay"]) == (version < "23.09")
    assert calm["branch_count"] == 1 and calm["branch_number"] == 0

    # wind on, turbulence zero: coarse properties only
    assert 10 < windy["landing_distance"] < 200
    assert 240 < windy["landing_bearing_deg"] < 300  # default wind blows it west
    assert math.isclose(
        windy["landing_distance"], math.hypot(windy["landing_x"], windy["landing_y"]), abs_tol=1e-6
    )

    # cross-process pickle: this test process has no JVM
    import jpype

    assert not jpype.isJVMStarted()
    loaded = pickle.loads(base64.b64decode(result["pickle_b64"]))
    assert loaded.to_dict().keys() == calm.keys()
    for key, value in calm.items():
        got = getattr(loaded, key)
        if isinstance(value, float) and math.isnan(value):
            assert math.isnan(got)
        elif key == "warnings":
            assert got == tuple(value)
        else:
            assert got == value

    assert result["calm_str"].startswith("Flight summary")


def test_summary_multistage(jar):
    """Every branch of the jar's own bundled three-stage example: boosters
    have no rod departure or deployment (NaN), the sustainer has both; a
    pinned jar missing its pinned example member fails, never skips."""
    import math

    version, path = jar
    result = run_case("summary_multistage.py", path)
    branches = result["branches"]

    assert len(branches) == 3
    sustainer, boosters = branches[0], branches[1:]
    assert sustainer["branch_name"] == "Sustainer"
    assert 200 < sustainer["apogee"] < 350
    assert 8 < sustainer["velocity_off_rod"] < 15
    assert not math.isnan(sustainer["descent_rate"])
    for booster in boosters:
        assert "ooster" in booster["branch_name"]
        assert 5 < booster["apogee"] < 150
        assert math.isnan(booster["velocity_off_rod"])
        assert math.isnan(booster["stability_off_rod_cal"])
        assert math.isnan(booster["descent_rate"])
        assert math.isnan(booster["optimum_delay"])
    # warnings are opaque strings wherever they appear; the older examples
    # actually produce some (the 24.12 example is warning-free)
    assert set(result["warning_types"]) <= {"str"}
    if version < "24.12":
        assert result["warning_types"]


def test_cross_version_apogee_tolerance(all_jars):
    """Same rocket, zero wind: apogee must agree across every version within a
    band. Profiles catch name drift; only result comparison catches semantic
    drift. Runs in the 24.12 cells only (the fixture skips elsewhere)."""
    apogees = {v: run_case("happy.py", path)["apogee"] for v, path in all_jars.items()}
    reference = apogees["24.12"]
    for version, apogee in apogees.items():
        assert abs(apogee - reference) / reference < 0.05, (
            f"apogee on {version} deviates >5% from 24.12: {apogees}"
        )
