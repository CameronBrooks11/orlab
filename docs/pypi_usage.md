# Releasing to PyPI

Releases are published automatically by the `release.yml` workflow using PyPI
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/) — no tokens or
manual uploads.

## Release procedure

1. Bump `version` in `pyproject.toml` on `main` (remove any `.dev` suffix).
2. Tag and create a GitHub release: `gh release create vX.Y.Z --title ... --notes ...`
3. The workflow builds with `uv build`, verifies the dist version matches the
   tag, and publishes. Pre-release versions (`.dev`, `rc`, `a`, `b`) are refused.

## Manual fallback

`workflow_dispatch` on any ref containing the workflow file, with the exact
`expected_version` as input. For a fully local build (no publish):

```
uv build   # produces dist/*.tar.gz and dist/*.whl
```
