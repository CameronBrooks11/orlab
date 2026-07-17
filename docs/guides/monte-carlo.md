# Monte-carlo studies

The pattern: **one instance, one loaded document, many simulations** —
randomize parameters between runs and collect a
[flight summary](summaries.md) per run.

```python
import math
from random import gauss

import orlab

apogees = []
with orlab.OpenRocketInstance() as instance:
    orl = orlab.Helper(instance)
    doc = orl.load_doc("rocket.ork")
    sim = doc.getSimulation(0)
    opts = sim.getOptions()

    for _ in range(100):
        opts.setLaunchRodAngle(math.radians(gauss(45, 5)))
        opts.setWindSpeedAverage(gauss(15, 5))
        orl.run_simulation(sim)
        apogees.append(orl.get_summary(sim).apogee)
```

The complete version —
[`examples/simple_ork/monte_carlo.py`](https://github.com/CameronBrooks11/orlab/blob/main/examples/simple_ork/monte_carlo.py)
— also perturbs component masses (`setMassOverridden` /
`setOverrideMass`), air-starts the rocket from a randomized altitude with a
listener, reads landing points from `get_summary`, and reports the
dispersion (note the circular mean for bearings — angles don't average
like scalars).

## Seeds and reproducibility

`run_simulation` **randomizes the simulation seed on every call** — that is
what makes the loop above sample rather than repeat one flight. For a
reproducible single run instead:

```python
sim.getOptions().setRandomSeed(42)
orl.run_simulation(sim, randomize_seed=False)
```

Repeated fixed-seed runs are bit-identical within a process. On OpenRocket
24.12, the wind model draws extra entropy at JVM startup, so a fixed seed
does **not** reproduce across processes when wind is enabled.

## The one-JVM constraint

JPype allows one JVM per process, and orlab keeps it alive until the
interpreter exits — so run the whole study inside one process (the loop
above), and prefer *one* `OpenRocketInstance` block over entering and
exiting per simulation (re-entry works, but buys nothing). Restarting
Python between simulations throws away several seconds of JVM/OpenRocket
startup each time.

That same constraint means parallelism is process-level: split the sample
count across worker *processes* (each with its own JVM), not threads. Large
studies may also want a bigger heap:
`OpenRocketInstance(jvm_args=("-Xmx4g",))`.
