# orlab

**orlab** scripts [OpenRocket](https://openrocket.info/) from Python via
[JPype](https://jpype.readthedocs.io/): load `.ork` files, run simulations
(optionally with custom listeners), and extract time series, final values,
and flight events as Python/numpy data.

```python
import orlab

with orlab.OpenRocketInstance(jar_path="OpenRocket-24.12.jar") as instance:
    orl = orlab.Helper(instance)
    doc = orl.load_doc("rocket.ork")
    sim = doc.getSimulation(0)
    orl.run_simulation(sim)

    data = orl.get_timeseries(
        sim, [orlab.FlightDataType.TYPE_TIME, orlab.FlightDataType.TYPE_ALTITUDE]
    )
    events = orl.get_events(sim)  # {FlightEvent.APOGEE: [3.51], ...}
```

## Supported OpenRocket versions

| OpenRocket | Status |
| ---------- | ------ |
| 24.12 | CI-tested (JDK 17, 21) |
| 23.09 | CI-tested (JDK 17, 21) |
| 22.02 | CI-tested (JDK 17, 21) |
| 15.03 | CI-tested (JDK 17, 21) |
| newer releases | forward fallback: run day-one on the nearest older profile, with a warning |

orlab detects the jar's version before the JVM starts and adapts to it —
package roots, startup path, and available flight-data constants all come
from checked-in, generated version profiles. Every version above runs real
simulations in CI, with no display server, and a monthly canary checks the
newest upstream release.

## Where next

- [Getting started](getting-started.md) — install, first simulation, the
  things worth knowing before a big run
- [API reference](api.md) — the full public surface, generated from the
  docstrings
- [Examples on GitHub](https://github.com/CameronBrooks11/orlab/tree/main/examples/simple_ork)
  — plots, a monte-carlo dispersion study, and design optimization
