# Changelog

All notable changes to orlab are documented here. Follows
[Keep a Changelog](https://keepachangelog.com) and
[Semantic Versioning](https://semver.org). History before 0.3.0 was
reconstructed from the git log.

## [0.4.0] — 2026-07-17

### Added

- Version profiles: per-OpenRocket-version facts (package roots, startup path,
  `FlightDataType`/`FlightEvent` constants) generated from the jars by
  `tools/generate_profile.py` and checked in for 15.03, 22.02, 23.09 and
  24.12. Unknown newer versions fall back to the nearest older profile with a
  warning, and a startup drift alarm warns when the loaded jar's constants
  differ from its profile.
- OpenRocket 24.12+ starts fully headless via the official
  `OpenRocketCore.initialize()` bootstrap — no window disposal, no display
  needed, and no private-field reflection on that path.
- `orlab.errors` with `OrlabError`, `UnsupportedFlightDataType` and
  `UnsupportedOpenRocketVersion`.
- Per-version integration harness (`just test-integration`):
  subprocess-per-version cases against sha256-pinned OpenRocket jars
  (downloaded on demand) covering flight sanity, the enum surface against the
  profile, warning/abort events, listener exception propagation, and
  cross-version apogee agreement. CI runs the full matrix — all four
  OpenRocket versions on JDK 17 and 21, no display server — and a monthly
  canary runs the newest upstream release against the newest profile, opening
  an issue on failure.

### Changed

- `FlightDataType`/`FlightEvent` are now generated as the union of constants
  across all profiled versions (four 24.12-only data types added); requesting
  a constant the loaded OpenRocket version does not expose raises
  `UnsupportedFlightDataType` naming the versions that have it (previously a
  raw JPype `AttributeError`). Enum members are now sorted by name — their
  numeric `.value`s shifted and remain non-stable identifiers; use names.
- Snapshot version strings (`26.xx-SNAPSHOT`) parse instead of erroring.

## [0.3.1] — 2026-07-17

### Added

- `FlightEvent.SIM_WARN` and `FlightEvent.SIM_ABORT` (emitted by OpenRocket
  24.12+) and `FlightDataType.TYPE_MOTOR_MASS` (the 22.02+ name for the
  propellant-mass series; `TYPE_PROPELLANT_MASS` remains for 15.03).

### Changed

- Packaging migrated to `pyproject.toml` (hatchling) with a `src/` layout and
  uv-managed environments; `setup.py` removed. Public import surface unchanged.
- `requires-python` raised to `>=3.10`; license metadata now correctly
  declares GPL-2.0-only (matching the LICENSE file).
- Quality gate: `justfile` (fmt / lint / typecheck / check / test through uv),
  ruff + mypy clean, pre-commit with gitleaks, `AGENTS.md`, and a jar-free
  unit-test suite (version detection, package-root selection, iterator
  bridging, API-surface freeze).
- CI: checks and a Python 3.10/3.14 unit-test matrix on every push and PR;
  releases publish to PyPI via Trusted Publishing on the `pypi` environment.

### Fixed

- `Helper.get_events()` no longer crashes on flight event types missing from
  the Python enum — on 24.12, simulation warnings are recorded as `SIM_WARN`
  events and previously raised a bare `KeyError`. Unknown event types from
  future OpenRocket versions are now skipped with a logged warning, and
  `translate_flight_event` raises a clear `ValueError` instead.
- `Helper.get_events()` return annotation matches its actual behavior
  (`Dict[FlightEvent, List[float]]` — a list of times per event).

### Removed

- Dead `orlab._orhelper` shim module and `scripts/debug_jvm.py`.

## [0.3.0] — 2026-07-17

### Added

- OpenRocket **24.12** support (#2): the jar's version is read from its
  `build.properties` before the JVM starts and the Java package roots
  (`net.sf.openrocket` vs `info.openrocket.core`/`info.openrocket.swing`)
  are selected automatically. `instance.or_version` and
  `instance.openrocket_swing` exposed; public API otherwise unchanged.
- OpenRocket 15.03 works on modern JVMs (`--add-opens` at JVM start).
  Verified by real simulations against 15.03, 22.02, 23.09, and 24.12.

## [0.2.x] — 2025

Initial orlab releases (0.2.3–0.2.7): evolution of
[orhelper](https://github.com/SilentSys/orhelper) — driver reorganization into
`core/`/`utils/`, PyPI publication, docs and examples for OpenRocket 23.09.
