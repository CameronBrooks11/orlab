"""Integration-test fixtures: real OpenRocket jars via orlab's own fetcher —
sha256-pinned (orlab._pins), cached in ORLAB_JAR_CACHE. The suite exercising
fetch_jar for every jar it runs is deliberate dogfooding.
"""

import os

import pytest

from orlab._pins import PINNED_SHA256 as JARS
from orlab.jars import fetch_jar as jar_path


@pytest.fixture(params=sorted(JARS), ids=lambda v: f"or{v}")
def jar(request):
    version = os.environ.get("ORLAB_TEST_VERSION")
    if version and request.param != version:
        pytest.skip(f"ORLAB_TEST_VERSION={version}")
    return request.param, jar_path(request.param)


@pytest.fixture
def all_jars():
    """Every supported version's jar — for cross-version comparisons.
    Skips before downloading anything in matrix cells other than 24.12, so
    per-version CI caches hold only their own jar."""
    only = os.environ.get("ORLAB_TEST_VERSION")
    if only not in (None, "24.12"):
        pytest.skip("cross-version comparison runs in the 24.12 cells only")
    return {v: jar_path(v) for v in sorted(JARS)}
