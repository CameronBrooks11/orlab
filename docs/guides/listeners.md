# Simulation listeners

Listeners are the extension point of the simulation engine: OpenRocket calls
into your Python code at every step, event, and force computation. Subclass
`orlab.AbstractSimulationListener`, override what you need, and pass
instances to `run_simulation`.

```python
import orlab


class ApogeeReporter(orlab.AbstractSimulationListener):
    def __init__(self, results):
        self.results = results  # shared with the caller

    def handleFlightEvent(self, status, flight_event):
        if "APOGEE" in str(flight_event.getType().name()):
            self.results.append(float(status.getRocketPosition().z))
        return True  # let OpenRocket process the event as usual


apogees: list[float] = []
with orlab.OpenRocketInstance() as instance:
    orl = orlab.Helper(instance)
    doc = orl.load_doc("rocket.ork")
    sim = doc.getSimulation(0)
    orl.run_simulation(sim, listeners=[ApogeeReporter(apogees)])
print(apogees)
```

## The hooks

The bridge implements OpenRocket's three listener interfaces; override any
subset:

- **SimulationListener** — `startSimulation(status)`,
  `endSimulation(status, exception)`, `preStep(status)` /
  `postStep(status)`, once per time step. `postStep` is the natural place
  for progress reporting on long runs.
- **SimulationEventListener** — `addFlightEvent(status, event)` /
  `handleFlightEvent(status, event)`, `motorIgnition(...)`,
  `recoveryDeviceDeployment(...)`. Return `True` to let the event proceed,
  `False` to swallow it.
- **SimulationComputationListener** — `pre*`/`post*` pairs around every
  physics computation (`preWindModel`, `postAerodynamicCalculation`,
  `preMassCalculation`, …). Pre-hooks may return an override value; return
  `None` (or `NaN` for scalar hooks) to keep OpenRocket's own computation.

The `status` object is a live Java `SimulationStatus` — query or modify
anything: `status.getSimulationTime()`, `status.getRocketPosition()`,
`status.setRocketPosition(...)`.

## Two rules

1. **OpenRocket clones your listener** (a shallow copy) before the run.
   Mutate shared state — append to a list the caller holds — rather than
   rebinding attributes on `self` and reading them back after the run. In
   the example above `self.results` works because caller and clone share
   the same list object.
2. **Exceptions propagate.** An exception raised in any hook aborts the
   simulation and re-raises from `run_simulation` as the original Python
   exception. Raising is a legitimate way to abort a run early.

## Worked examples

[`examples/simple_ork/monte_carlo.py`](https://github.com/CameronBrooks11/orlab/blob/main/examples/simple_ork/monte_carlo.py)
uses both patterns in one study:

- `AirStart` overrides `startSimulation` to lift the rocket to a randomized
  starting altitude (`status.setRocketPosition(...)`).
- `LandingPoint` overrides `endSimulation` to record the landing
  coordinates into shared lists.
