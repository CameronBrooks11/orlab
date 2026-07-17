# AGENTS.md

Canonical working agreement for humans and AI agents contributing to this
repository.

## What this project is

`orlab` is a Python module for scripting [OpenRocket](https://openrocket.info/)
from Python via [JPype](https://jpype.readthedocs.io/): load `.ork` files, run
simulations (optionally with custom listeners), and extract time-series,
final values, and flight events as Python/numpy data.

## Build, test, check

Everything runs through `uv` via the `justfile`:

- `just setup` — sync the dev environment
- `just fmt` / `just lint` — ruff format / lint with autofixes
- `just check` — CI-equivalent gate: format check + lint + mypy
- `just test` — unit tests (no OpenRocket jar or JVM needed)

Run `just check && just test` before every commit.

## Hard constraints (learn these before touching core)

- **One JVM per process** (JPype cannot restart a JVM). A process gets exactly
  one `OpenRocketInstance` lifecycle; anything that needs two OpenRocket
  versions (tests, the profile generator) must use subprocesses. See issue #9.
- **OpenRocket's internal API moves between releases.** 24.12 renamed
  `net.sf.openrocket` to `info.openrocket.core`/`info.openrocket.swing`.
  Never hardcode a package root: `orlab/core/version.py` detects the jar
  version (from its `build.properties`, without starting the JVM) and selects
  roots. The multi-version architecture is tracked in epic #3.
- **The public API surface is frozen by test** (`tests/test_api_surface.py`).
  Additions are fine; renames/removals are breaking changes.

## Conventions

- Conventional Commits; PR per slice, linked to its issue; never bypass hooks.
- Releases: bump `version` in `pyproject.toml`, tag `vX.Y.Z`, create a GitHub
  release — `release.yml` publishes to PyPI via Trusted Publishing (the
  workflow refuses version/tag mismatches and pre-release strings).
- Integration testing against real OpenRocket jars is subprocess-per-version
  (epic #3, issue #8); unit tests must stay jar-free so `just test` is fast
  everywhere.
