# Monte-carlo studies

`SimulationPool` runs dispersion studies across worker processes — each
worker boots one JVM (JPype allows exactly one JVM per process, so
parallelism is process-level by construction), loads your `.ork` once, and
flies many simulations against it. Tasks are plain data; results come back
as plain data.

```python
import orlab

if __name__ == "__main__":
    pool = orlab.SimulationPool("rocket.ork", jvm_args=("-Xmx512m",))
    tasks = [{"wind_speed_average": w / 2, "launch_rod_angle": 0.1} for w in range(200)]
    study = pool.run(tasks, seed=42)
    for record in study.to_records():
        print(record["wind_speed_average"], record["apogee"])
```

The `if __name__ == "__main__":` guard is **required** in scripts:
workers start via multiprocessing's *spawn* method (the only start method
that is safe with a JVM and identical on every platform), and spawn
re-imports your script in each worker.

Each task is a mapping of [declarative keys](../api.md#parallel-running-and-declarative-options)
— the `SimulationOptions` knobs verified to behave identically on every
supported OpenRocket version — plus an optional reserved `seed`. The
default result payload is the core summary fields (apogee, max
velocity/acceleration, flight time, landing x/y); per-task failures don't
kill the study (they come back as `study.errors` unless you pass
`on_error="abort"`).

## Beyond the declarative keys: worker_fn

For anything the whitelist doesn't cover — component mutations, listeners,
custom extraction — pass a **module-level, importable** function that
takes over the whole task body:

```python
# workers.py
def disperse(helper, sim, task):
    opts = sim.getOptions()
    opts.setWindSpeedAverage(task["wind"])
    nose = helper.get_component_named(sim.getRocket(), "Nose cone")
    nose.setMassOverridden(True)
    nose.setOverrideMass(task["nose_mass"])
    helper.run_simulation(sim, randomize_seed=False)
    return helper.get_summary(sim)  # FlightSummary is plain data — it travels
```

```python
# study.py
import orlab
from workers import disperse

if __name__ == "__main__":
    pool = orlab.SimulationPool("rocket.ork", jvm_args=("-Xmx512m",))
    study = pool.run(
        [{"wind": 5.0, "nose_mass": 0.02}, {"wind": 8.0, "nose_mass": 0.025}],
        worker_fn=disperse,
    )
```

The contract: **set everything you vary** (workers restore the document's
own option baseline between tasks, but component mutations you make are
yours to manage), call `run_simulation(..., randomize_seed=False)` so the
pool-assigned seed sticks, and return plain-Python data — Java objects
cannot cross process boundaries, which is also why `worker_fn` itself must
be importable. In a **notebook**, functions defined in cells can't be
re-imported by spawn workers — the pool rejects them up front. Write them
to a module first:

```
%%writefile workers.py
def disperse(helper, sim, task):
    ...
```

## Progress bars

`progress(done, total)` is called with `(0, total)` as soon as tasks are
submitted (workers take a few seconds to boot their JVMs — the bar renders
during the wait), then once per completed task. tqdm needs one line and no
dependency in orlab:

```python
from tqdm import tqdm

with tqdm(total=len(tasks)) as bar:
    study = pool.run(tasks, progress=lambda done, total: bar.update(done - bar.n))
```

## Tables

`study.to_records()` is a list of flat dicts (task keys + payload + seed);
a dispersion table is one line of pandas (`pip install 'orlab[pandas]'`):

```python
import pandas as pd

frame = pd.DataFrame(study.to_records())
print(frame[["wind_speed_average", "apogee"]].describe())
```

## Seeds, replay, and reproducibility

- Every task gets a unique pool-assigned seed (deduplicated 31-bit values;
  Java's own `randomizeSeed()` draws a space where 10k-run studies collide).
  Pass `seed=` to make the *derivation* reproducible, or put a `seed` in a
  task to pin that run.
- `SimResult.seed` is the seed the simulation actually used, read back
  after the run — replay any interesting run by resubmitting its task with
  that seed. If a `worker_fn` leaves `randomize_seed=True`,
  `seed_reassigned` flags it and the recorded seed is still the replayable
  one.
- On OpenRocket 24.12, wind-enabled runs draw extra per-process entropy at
  JVM start: a fixed seed reproduces results **within** one process, not
  across processes. Replay-from-recorded-seed inside one worker's lifetime
  is exact; cross-process replay of windy runs is statistical. 24.12 also
  reworked its wind model — treat wind-deviation semantics from older
  scripts as version-dependent.

## Failure modes, memory, sizing

- Per-task exceptions (Python or Java) come back as `SimError` records
  with the full traceback including the Java stack. `on_error="abort"`,
  a worker crash, a worker-boot failure, or ^C raise
  `orlab.errors.StudyAborted` — always with `.partial` holding everything
  collected so far.
- Each worker holds a JVM: budget roughly **0.5–0.7 GB per worker with
  `jvm_args=("-Xmx512m",)`** (measured, OpenRocket 24.12). The default
  `max_workers` is `min(4, cpu_count)`.
- Workers (and their JVMs) stay warm between `run()` calls — reuse the
  pool for follow-up batches, and call `pool.shutdown()` when the study is
  done to release the memory before any long-running analysis.
- Worker JVMs take a few seconds to boot, so tiny studies are faster
  serial — for a handful of runs, loop `run_simulation` in one process
  instead. On the reference machine (Linux, 12 cores), 8 simple.ork
  simulations across 2 workers complete in ~5 s including boots, and a
  warm pool re-runs a 4-task batch in ~0.3 s.

## Serial studies still work

For quick loops, the pre-pool pattern remains exactly right — one
process, one instance, many runs:

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

`run_simulation` randomizes the seed on every call by default — that is
what makes this loop sample rather than repeat one flight. The complete
version — [`examples/simple_ork/monte_carlo.py`](https://github.com/CameronBrooks11/orlab/blob/main/examples/simple_ork/monte_carlo.py)
— also perturbs component masses, air-starts the rocket with a listener,
and reports the dispersion via `get_summary` (note the circular mean for
bearings — angles don't average like scalars).

## The whole pipeline

From a machine with a JDK to a dispersion table:

```python
import orlab
import pandas as pd

if __name__ == "__main__":
    jar = orlab.fetch_jar()                       # verified download, cached
    pool = orlab.SimulationPool("rocket.ork", jar, jvm_args=("-Xmx512m",))
    study = pool.run([{"wind_speed_average": w / 4} for w in range(100)], seed=1)
    table = pd.DataFrame(study.to_records())
    print(table[["wind_speed_average", "apogee"]].describe())
```
