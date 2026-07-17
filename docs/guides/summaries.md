# Flight summaries

`Helper.get_summary` turns a simulated flight into one plain-Python record —
the numbers every flight report needs, without hand-rolling timeseries
post-processing:

```python
import orlab

with orlab.OpenRocketInstance() as instance:
    orl = orlab.Helper(instance)
    doc = orl.load_doc("rocket.ork")
    sim = doc.getSimulation(0)
    orl.run_simulation(sim)

    summary = orl.get_summary(sim)
    print(summary)
    print(summary.apogee, summary.max_velocity, summary.descent_rate)
```

`print(summary)` renders a sectioned report (rail departure, ascent,
recovery & descent, landing, warnings). Every field is a builtin float,
int, or str in SI units (`FlightSummary.UNITS` maps fields to units) —
never a Java or numpy type — so summaries pickle cleanly into other
processes and serialize without surprises.

## Dispersion tables

`to_dict()` makes a summary one table row; a study is a list of rows:

```python
summaries = []
for i in range(100):
    randomize(sim)          # your parameter dispersion
    orl.run_simulation(sim)
    summaries.append(orl.get_summary(sim))

rows = [s.to_dict() for s in summaries]

import pandas as pd  # optional — plain dicts work with csv.DictWriter too
table = pd.DataFrame(rows)
print(table[["apogee", "landing_distance", "landing_bearing_deg"]].describe())
```

[`examples/simple_ork/monte_carlo.py`](https://github.com/CameronBrooks11/orlab/blob/main/examples/simple_ork/monte_carlo.py)
is this pattern end to end.

## Field semantics worth knowing

- **Missing means NaN, never None.** A booster branch has no launch-rod
  departure, pre-23.09 OpenRocket computes no `optimum_delay`, a flight
  without a recovery event has no `descent_rate`. When a field is NaN
  because the *loaded OpenRocket version* lacks the underlying data (not
  because of the flight itself), orlab logs one warning per process — so
  version drift can't silently corrupt dispersion statistics.
- **Stability is windowed.** `min_stability_cal`/`max_stability_cal` cover
  launch-rod departure → apogee. OpenRocket 24.12 computes stability
  through post-apogee tumble, where unwindowed minima (−9 cal and worse)
  are meaningless.
- **`time_to_apogee`** on branch 0 is OpenRocket's own figure; the APOGEE
  *event* time in `get_events` can differ by a sample step.
- **Landing is flat-earth**: `landing_x` (east), `landing_y` (north),
  distance and compass bearing derived from them. Geodetic coordinates are
  deliberately not summarized (their stored units changed across OpenRocket
  versions).
- **Pickles are transport, not archive.** Load them with the same orlab
  version that wrote them; for storage, use `to_dict()`/CSV.

## Multi-stage flights

Each stage branch gets its own summary; `branch_count` tells you how many:

```python
for branch in range(orl.get_summary(sim).branch_count):
    print(orl.get_summary(sim, branch_number=branch))
```

Booster branches report NaN for rail-departure and recovery fields they
don't have; their `apogee`/`max_velocity` come from the branch's own data.

## Drogue vs main descent

`descent_rate` averages from the *last* recovery deployment to ground hit
(the main, in a dual-deploy flight). For per-device rates, window the
timeseries yourself with the event times:

```python
import numpy as np

events = orl.get_events(sim)  # get_events(sim, branch_number=...) for stages
drogue_t, main_t = events[orlab.FlightEvent.RECOVERY_DEVICE_DEPLOYMENT][:2]
data = orl.get_timeseries(
    sim, [orlab.FlightDataType.TYPE_TIME, orlab.FlightDataType.TYPE_VELOCITY_Z]
)
t = data[orlab.FlightDataType.TYPE_TIME]
vz = data[orlab.FlightDataType.TYPE_VELOCITY_Z]
window = (t >= drogue_t) & (t <= main_t) & ~np.isnan(vz)
print("drogue descent rate:", -vz[window].mean())
```
