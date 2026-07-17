# Simulation setup

## Motor selection and swapping

`Helper.set_motor` changes the motor a simulation **actually flies**:

```python
orl.set_motor(sim, "C6", manufacturer="Estes")   # from OpenRocket's database
orl.set_motor(sim, "my_motor.eng")               # from a thrust-curve file
orl.set_motor(sim, "C6", manufacturer="Estes", delay=5.0)  # + ejection delay (s)
print(orl.get_motor(sim))                        # designation at the sim's config
```

### Why this exists: the silent-failure trap

An OpenRocket document holds several flight configurations, and **the one a
simulation flies is rarely the one the rocket has "selected"** — on the
bundled example rocket the sim flies A8 while the selected configuration
shows C6. Raw-Java motor assignment via the selected configuration
succeeds, changes what the GUI would show, and does absolutely nothing to
your simulation. This trap is why `set_motor` always keys on the
simulation's own flight configuration, on every OpenRocket version, and
reads the assignment back afterwards — a mismatch raises instead of
producing quietly wrong dispersion data.

### Database lookups

`find_motor(designation, manufacturer=None)` searches OpenRocket's own
motor database (fully loaded on every supported version and startup path,
including 24.12 headless). Common hobby designations exist from several
manufacturers — A8, B6, C6 all do — so those lookups **require**
`manufacturer=`: motor choice is safety-relevant and orlab refuses to
guess. One manufacturer's designation can span several motor
sets (different diameters); sets are ordered by diameter then length, and
OpenRocket keeps each set's variants deterministically sorted — so "the"
motor is stable run to run. Manufacturer matching uses OpenRocket's own
alias machinery ("CTI" finds Cesaroni). A miss raises with up to ten near-matches named.

### Thrust-curve files

`load_motor(path)` loads `.eng` (RASP) files through OpenRocket's own
loader — verified end to end; `.rse` and `.zip` are dispatched to the same
loader. No database is involved, so file motors work identically
everywhere. Files holding several motors need `designation=` to pick one.
The loaded motor object can be passed straight to `set_motor` (or the path
can — `set_motor` dispatches on the extension).

`delay=` sets the ejection delay in seconds on the simulation's motor
configuration; omitted, the existing delay is preserved. This is the
*configuration's* delay — with an `.eng` file the RASP header's delay list
describes the motor, but the configuration decides what flies.

### One caveat on 24.12

On OpenRocket 24.12's headless startup path the *component preset*
database is not loaded (an upstream gap) — motors are unaffected, but raw
Java code reaching into component presets will find them empty.

## Everything that's already a one-liner

Launch conditions and uniform wind need no wrapper — they're single calls
on live Java objects, and the verified names live in
[`DECLARATIVE_KEYS`](../api.md#declarative-simulation-options):

```python
opts = sim.getOptions()
opts.setLaunchRodLength(1.5)        # m
opts.setLaunchRodAngle(0.15)        # rad
opts.setLaunchIntoWind(False)       # required for setLaunchRodDirection to act
opts.setLaunchRodDirection(1.2)     # rad — silently ignored while into-wind is on
opts.setLaunchAltitude(1400.0)      # m
opts.setWindSpeedAverage(6.5)       # m/s
opts.setWindDirection(2.1)          # rad
```

Component tweaks are the same story — find the component, call its setter:

```python
nose = orl.get_component_named(sim.getRocket(), "Nose cone")
nose.setMassOverridden(True)
nose.setOverrideMass(0.035)         # kg
```

All values are SI (meters, radians, kilograms, Kelvin); OpenRocket's
setters do no unit conversion.
