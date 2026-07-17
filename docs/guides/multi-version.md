# Working across OpenRocket versions

orlab reads the jar's version from its `build.properties` before the JVM
starts and selects a **version profile** — package roots, startup path, and
the flight-data/event constants that version exposes. Profiles are generated
from the jars themselves and checked in for 15.03, 22.02, 23.09, and 24.12.

```python
instance = orlab.OpenRocketInstance(jar_path="OpenRocket-24.12.jar")
print(instance.or_version)               # "24.12"
print(instance.profile.version_string)   # "24.12"
```

## Constants differ between versions

`FlightDataType` and `FlightEvent` are the union across all supported
versions. Requesting a constant the loaded jar doesn't have raises a
precise error:

```python
orl.get_timeseries(sim, [orlab.FlightDataType.TYPE_WIND_DIRECTION])
# on a 23.09 jar:
# UnsupportedFlightDataType: TYPE_WIND_DIRECTION is not available in
# OpenRocket 23.09 (available in: 24.12)
```

Known renames are represented as-is — `TYPE_PROPELLANT_MASS` exists only on
15.03; from 22.02 the same series is `TYPE_MOTOR_MASS`. Catch
`orlab.errors.UnsupportedFlightDataType` to handle either.

Constants newer than orlab's enum (a brand-new OpenRocket release) can be
passed as strings; they resolve against the live jar:

```python
orl.get_timeseries(sim, ["TYPE_MOTOR_MASS"])
```

Flight *events* degrade gracefully in the other direction: event types
orlab doesn't know are skipped by `get_events` with a logged warning, never
a crash. On 24.12, expect `SIM_WARN` events for simulation warnings and
`SIM_ABORT` where older versions raised exceptions.

## Newer releases than orlab knows

A jar newer than the newest profile runs immediately on the **nearest older
profile**, with a warning at instantiation. At startup, orlab compares the
live jar's constants against the profile and logs any drift. Full support
for a new release is one PR — see the
[maintainer notes](../maintainers.md#supporting-a-new-openrocket-release).
A jar older than 15.03 raises `UnsupportedOpenRocketVersion`.

## Comparing versions

One process drives one jar (the JVM cannot be restarted), so comparisons are
subprocess-per-version. orlab's own integration harness is the reference
implementation:
[`tests/integration/`](https://github.com/CameronBrooks11/orlab/tree/main/tests/integration)
spawns a fresh Python per version and asserts, among other things, that the
same rocket's apogee agrees across all four supported versions within 5 %.

```python
import json
import subprocess
import sys

CASE = "case.py"  # loads the ork, simulates, prints json.dumps(results)
results = {
    jar: json.loads(subprocess.run([sys.executable, CASE, jar], capture_output=True, text=True, check=True).stdout)
    for jar in ["OpenRocket-23.09.jar", "OpenRocket-24.12.jar"]
}
```
