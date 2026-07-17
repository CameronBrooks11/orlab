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
- `just test-integration` — real-jar matrix (downloads pinned OpenRocket jars
  on first run; `ORLAB_TEST_VERSION=24.12` limits to one version)

Run `just check && just test` before every commit.

## Hard constraints (learn these before touching core)

- **One JVM per process** (JPype cannot restart a JVM). The JVM starts on the
  first `OpenRocketInstance` and stays up until the interpreter exits; later
  instances on the same jar reuse it, a different jar raises `OrlabError`.
  Anything that needs two OpenRocket versions (tests, the profile generator)
  must use subprocesses.
- **OpenRocket's internal API moves between releases.** 24.12 renamed
  `net.sf.openrocket` to `info.openrocket.core`/`info.openrocket.swing`.
  Never hardcode a package root or enum surface: `orlab/core/version.py`
  detects the jar version (from its `build.properties`, without starting the
  JVM) and `orlab/profiles/` carries the per-version facts (roots, startup
  path, constants). Unknown newer versions fall back to the nearest older
  profile with a warning.
- **Profiles and `_enums.py` are generated — never hand-edit them.** For a new
  OpenRocket release: `uv run python tools/generate_profile.py <jar>` (fails
  loudly if the jar breaks orlab's contract manifest), then
  `uv run python tools/generate_enums.py`, register the new module in
  `orlab/profiles/__init__.py`, and ship it all as one PR.
- **The public API surface is frozen by test** (`tests/test_api_surface.py`).
  Additions are fine; renames/removals are breaking changes.

## Conventions

- Conventional Commits; PR per slice, linked to its issue; never bypass hooks.
- `pre-commit` itself is machine-managed tooling (installed system-wide, see
  workstation-configs), not a project dependency — enable with `pre-commit install`.
- Releases: bump `version` in `pyproject.toml`, tag `vX.Y.Z`, create a GitHub
  release — `release.yml` publishes to PyPI via Trusted Publishing (the
  workflow refuses version/tag mismatches and pre-release strings).
- Integration testing against real OpenRocket jars is subprocess-per-version
  (epic #3, issue #8); unit tests must stay jar-free so `just test` is fast
  everywhere.
