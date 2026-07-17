"""Integration-test fixtures: real OpenRocket jars, fetched and sha256-pinned.

Jars land in ORLAB_JAR_CACHE (default ~/.cache/orlab-jars), downloaded from
GitHub releases on first use. Every use re-verifies the pinned sha256.
"""

import hashlib
import os
import urllib.request
from pathlib import Path

import pytest

JARS = {
    "15.03": "2bbc4b1b57d99fd169f4119e221b934f007b88c437295f388a81cd3df5da84e3",
    "22.02": "1e26b83abb6d846e63bcc560f6bf16afe9c370378b614c0aacbfc6ece4ae07c8",
    "23.09": "65cc0ab68a536fc33fc02a84c416725523a82745e100356efd9ff890b43bfcd0",
    "24.12": "4959b72f52f5f607941e9722abbb7b7f0c4a38ebbbf84204a329db9f31c4f897",
}
URL = "https://github.com/openrocket/openrocket/releases/download/release-{v}/OpenRocket-{v}.jar"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def jar_path(version: str) -> Path:
    cache = Path(os.environ.get("ORLAB_JAR_CACHE", Path.home() / ".cache" / "orlab-jars"))
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"OpenRocket-{version}.jar"
    if not path.exists():
        tmp = path.with_suffix(".part")
        urllib.request.urlretrieve(URL.format(v=version), tmp)
        tmp.rename(path)
    digest = _sha256(path)
    if digest != JARS[version]:
        path.unlink()
        raise RuntimeError(
            f"OpenRocket-{version}.jar sha256 mismatch: got {digest}, "
            f"expected {JARS[version]} (removed; rerun to re-download)"
        )
    return path


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
