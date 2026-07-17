"""Fetch-by-version OpenRocket jar management: verified download and cache.

``fetch_jar`` downloads a release jar from GitHub, verifies its sha256
against the pins shipped in :mod:`orlab._pins` (or a caller-supplied digest
for unpinned versions), and caches it. Verification is not optional: the
cache never holds a jar whose digest was not checked, and cache hits are
re-verified on every call.

This module is stdlib-only and never touches the JVM.
"""

import hashlib
import logging
import os
import re
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from ._pins import DEFAULT_VERSION, PINNED_SHA256
from .errors import JarVerificationError

__all__ = ["fetch_jar", "jar_cache_dir"]

logger = logging.getLogger(__name__)

RELEASE_URL = (
    "https://github.com/openrocket/openrocket/releases/download/release-{v}/OpenRocket-{v}.jar"
)

_VERSION_RE = re.compile(r"[0-9A-Za-z.\-]+")
_DOWNLOAD_TIMEOUT_S = 60


def jar_cache_dir() -> Path:
    """The directory ``fetch_jar`` caches jars in: ``$ORLAB_JAR_CACHE``,
    else ``$XDG_CACHE_HOME/orlab-jars``, else ``~/.cache/orlab-jars``.
    """
    env = os.environ.get("ORLAB_JAR_CACHE")
    if env:
        return Path(env)
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "orlab-jars"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: Path) -> None:
    """Streams url into dest. Test seam: unit tests replace this to avoid
    the network; everything above it (temp file, verify, replace) runs real.
    """
    with urllib.request.urlopen(url, timeout=_DOWNLOAD_TIMEOUT_S) as resp, open(dest, "wb") as fh:
        while chunk := resp.read(1 << 20):
            fh.write(chunk)


def _evict(path: Path) -> None:
    """Removes a cache entry; a PermissionError means another process holds
    the file open (Windows), which is its problem to resolve, not corruption
    to crash on.
    """
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except PermissionError:
        logger.warning("could not remove %s (in use by another process)", path)


def _fetch_verified(url: str, path: Path, expected: str) -> None:
    """Downloads url into path's directory and moves it to path only after
    the digest checks out. The cache never holds an unverified jar.
    """
    logger.warning("downloading %s (%s)", url, path.name)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".part")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        try:
            _download(url, tmp)
        except urllib.error.URLError as e:
            # bare urllib errors don't say what they were fetching
            raise urllib.error.URLError(f"{e} while downloading {url}") from e
        digest = _sha256(tmp)
        if digest != expected:
            raise JarVerificationError(
                f"sha256 mismatch downloading {url}: got {digest}, expected {expected}"
            )
        try:
            os.replace(tmp, path)
        except PermissionError:
            # another process won the race and holds the entry open; if what
            # it put there verifies, use it
            if not (path.exists() and _sha256(path) == expected):
                raise
    finally:
        _evict(tmp)


def _cached_jar(version: str) -> Path | None:
    """The cache path for a pinned version if present and verified, else
    None. Never downloads; evicts (with a warning) entries that no longer
    match their pin.
    """
    pin = PINNED_SHA256.get(version)
    if pin is None:
        return None
    path = jar_cache_dir() / f"OpenRocket-{version}.jar"
    if not path.exists():
        return None
    if _sha256(path) != pin:
        logger.warning("cached %s failed sha256 verification; removing it", path)
        _evict(path)
        return None
    return path


def fetch_jar(version: str | None = None, *, sha256: str | None = None) -> Path:
    """Downloads (or returns the cached copy of) the OpenRocket jar for
    ``version``, verified by sha256. ``version=None`` means the default,
    ``orlab._pins.DEFAULT_VERSION``.

    Versions orlab pins are verified against the shipped pin. Any other
    version requires ``sha256=`` — compute it yourself from a copy you
    trust; there is no way to skip verification.

    :raises JarVerificationError: no digest to verify against, or a digest
        mismatch that survived one re-download.
    :raises ValueError: a malformed version string, or ``sha256=``
        contradicting a shipped pin.
    """
    if version is None:
        version = DEFAULT_VERSION
    if not _VERSION_RE.fullmatch(version):
        raise ValueError(f"not an OpenRocket version string: {version!r}")
    if sha256 is not None:
        sha256 = sha256.lower()
    pin = PINNED_SHA256.get(version)
    if pin is not None and sha256 is not None and sha256 != pin:
        raise ValueError(
            f"sha256= for OpenRocket {version} contradicts orlab's pin: "
            f"given {sha256}, pinned {pin}"
        )
    expected = pin or sha256
    url = RELEASE_URL.format(v=version)
    cache = jar_cache_dir()
    path = cache / f"OpenRocket-{version}.jar"

    if expected is None:
        found = f"\nA cached file exists with sha256 {_sha256(path)}." if path.exists() else ""
        raise JarVerificationError(
            f"orlab {_orlab_version()} has no sha256 pin for OpenRocket {version}, "
            f"so it will not fetch it unverified. Download {url} from a "
            "machine/network you trust, compute its digest (`sha256sum "
            f"OpenRocket-{version}.jar`), and pass it: "
            f"fetch_jar({version!r}, sha256=...). A newer orlab may pin this "
            "version already." + found
        )

    cache.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if _sha256(path) == expected:
            return path
        logger.warning("cached %s failed sha256 verification; re-downloading", path)
        _evict(path)
    _fetch_verified(url, path, expected)
    return path


def _orlab_version() -> str:
    # naming the installed version in the no-pin error points users at
    # upgrading when the pin exists in a newer release
    try:
        from importlib.metadata import version as dist_version

        return dist_version("orlab")
    except Exception:  # pragma: no cover - metadata missing in odd installs
        return "(this version)"
