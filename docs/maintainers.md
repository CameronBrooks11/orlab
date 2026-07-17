# Maintainer notes

Working agreements live in
[AGENTS.md](https://github.com/CameronBrooks11/orlab/blob/main/AGENTS.md);
this page holds the procedures.

## Releasing

Releases publish to PyPI via
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/) — no tokens.

1. Stamp the version: set `version` in `pyproject.toml` (drop the `.dev`
   suffix) and retitle the `[Unreleased]` changelog section, on `main`.
2. `gh release create vX.Y.Z --title "orlab X.Y.Z" --notes ...`
3. `release.yml` gates on `just check && just test`, builds with `uv build`,
   refuses a dist whose version doesn't match the tag (or any pre-release
   string), and publishes. Then bump `main` to the next `.dev0`.

Manual fallback: `workflow_dispatch` on any ref containing the workflow,
with the exact `expected_version` as input.

## Supporting a new OpenRocket release

One PR:

1. `uv run python tools/generate_profile.py <new jar>` — reflects the jar and
   verifies the contract manifest (fails loudly, naming missing members, if
   the jar breaks anything orlab touches).
2. `uv run python tools/generate_enums.py` — regenerates the union enums.
3. Register the new module in `src/orlab/profiles/__init__.py` and add the
   version + sha256 to `src/orlab/_pins.py` and the CI matrix in `ci.yml`
   (the integration suite and `fetch_jar` both read the pins; changing
   `_pins.py` also rolls the CI jar caches).
4. `just test && just test-integration`.

Until that PR lands, the new release runs on the nearest older profile with
a warning (the monthly `canary.yml` run checks exactly this and opens an
issue on failure).

## Test tiers

- `just test` — unit suite, jar-free, sub-second; runs on every push and PR
  (CI test matrix) and gates every release build.
- `just test-integration` — real simulations against every supported jar
  (sha256-pinned, cached in `~/.cache/orlab-jars` or `$ORLAB_JAR_CACHE`);
  `ORLAB_TEST_VERSION=24.12` limits to one version, as the CI matrix does.
