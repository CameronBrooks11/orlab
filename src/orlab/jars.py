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
import shlex
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import NamedTuple

from ._pins import DEFAULT_VERSION, PINNED_SHA256
from .core.version import parse_version, read_or_version
from .errors import JarVerificationError

__all__ = ["Installed", "fetch_jar", "find_installed", "jar_cache_dir"]

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


def _sha256_or_none(path: Path) -> str | None:
    """The digest, or None if the file vanished or is unreadable — another
    process evicting concurrently (or the user deleting jars, which the docs
    bless) must read as 'absent', not crash."""
    try:
        return _sha256(path)
    except OSError:
        return None


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
        except urllib.error.HTTPError as e:
            # bare urllib errors don't say what they were fetching; keep the
            # type (a 404 means "no such release", not a network problem)
            e.msg = f"{e.msg} (downloading {url})"
            raise
        except urllib.error.URLError as e:
            e.reason = f"{e.reason} (downloading {url})"
            raise
        digest = _sha256(tmp)
        if digest != expected:
            raise JarVerificationError(
                f"sha256 mismatch downloading {url}: got {digest}, expected {expected}"
            )
        try:
            os.replace(tmp, path)
        except PermissionError as e:
            # another process won the race and holds the entry open; if what
            # it put there verifies, use it
            if _sha256_or_none(path) != expected:
                raise PermissionError(
                    f"cannot update {path}: it is held open by another "
                    "process and does not match the expected digest; close "
                    "whatever holds it and retry"
                ) from e
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
    digest = _sha256_or_none(path)
    if digest is None:
        return None
    if digest != pin:
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

    :raises JarVerificationError: no digest to verify against, or a
        downloaded jar whose digest does not match (a corrupt cached entry
        is evicted and re-downloaded once first).
    :raises ValueError: a malformed version string or digest, or ``sha256=``
        contradicting a shipped pin.
    """
    if version is None:
        version = DEFAULT_VERSION
    if not _VERSION_RE.fullmatch(version):
        raise ValueError(f"not an OpenRocket version string: {version!r}")
    if sha256 is not None:
        sha256 = sha256.lower()
        if not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise ValueError(f"not a sha256 hex digest: {sha256!r}")
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
        cached_digest = _sha256_or_none(path)
        found = f"\nA cached file exists with sha256 {cached_digest}." if cached_digest else ""
        raise JarVerificationError(
            f"orlab {_orlab_version()} has no sha256 pin for OpenRocket {version}, "
            f"so it will not fetch it unverified. Download {url} from a "
            "machine/network you trust, compute its digest (`sha256sum "
            f"OpenRocket-{version}.jar`), and pass it: "
            f"fetch_jar({version!r}, sha256=...). A newer orlab may pin this "
            "version already." + found
        )

    cache.mkdir(parents=True, exist_ok=True)
    digest = _sha256_or_none(path)
    if digest == expected:
        return path
    if digest is not None:
        logger.warning("cached %s failed sha256 verification; re-downloading", path)
        _evict(path)
    _fetch_verified(url, path, expected)
    return path


class Installed(NamedTuple):
    """A discovered desktop OpenRocket installation."""

    jar: Path
    jvm: Path | None  # bundled JVM library, only when its JRE is 17+
    version: str


def find_installed() -> Installed | None:
    """Locates a desktop OpenRocket installation — for users who have the
    app but no separate jar or JDK. Explicit opt-in: the default jar
    resolution never calls this. Typical use::

        inst = orlab.jars.find_installed()
        if inst:
            instance = orlab.OpenRocketInstance(str(inst.jar), jvm_path=inst.jvm)

    Never raises and never downloads; returns None when nothing usable is
    found. ``ORLAB_OR_INSTALL_DIR`` overrides the per-OS search (its parent
    directory conventions still apply inside); setting it to the empty
    string disables discovery entirely. ``jvm`` is the install's bundled
    JVM library when that JRE is Java 17+ (older bundled JREs can't run
    orlab; the jar itself is still usable with your own JDK).
    """
    try:
        override = os.environ.get("ORLAB_OR_INSTALL_DIR")
        if override is not None:
            roots = [Path(override)] if override else []
        else:
            roots = _platform_install_roots()
        for root in roots:
            found = _probe_install_root(root)
            if found is not None:
                return found
    except Exception:  # never-raise contract: discovery is best-effort
        logger.debug("installed-OpenRocket discovery failed", exc_info=True)
    return None


def _platform_install_roots() -> list[Path]:
    if sys.platform.startswith("linux"):
        return _desktop_install_roots()
    if sys.platform == "darwin":
        return [Path("/Applications/OpenRocket.app/Contents/Resources/app")]
    if sys.platform == "win32":
        return [Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "OpenRocket"]
    return []


def _desktop_install_roots() -> list[Path]:
    """Install roots from install4j's .desktop breadcrumbs: the Exec= value
    is a quoted launcher path plus %U-style field codes; the launcher's
    parent directory is the install root."""
    apps = Path.home() / ".local" / "share" / "applications"
    roots = []
    try:
        desktops = sorted(apps.glob("install4j_*-OpenRocket.desktop"))
    except OSError:
        return []
    for desktop in desktops:
        try:
            text = desktop.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            if line.startswith("Exec="):
                launcher = _parse_exec(line[len("Exec=") :])
                if launcher:
                    roots.append(Path(launcher).parent)
                break
    return roots


def _parse_exec(value: str) -> str | None:
    try:
        parts = shlex.split(value)
    except ValueError:
        return None
    return parts[0] if parts else None


def _probe_install_root(root: Path) -> Installed | None:
    if not root.is_dir():
        logger.debug("no OpenRocket install at %s", root)
        return None
    jar = _install_jar(root)
    if jar is None:
        logger.debug("%s has no OpenRocket jar in a known layout", root)
        return None
    try:
        version = read_or_version(str(jar))
        parse_version(version)  # a jar with an unparseable version can't boot
    except Exception:
        logger.debug("%s is not a readable OpenRocket jar", jar, exc_info=True)
        return None
    return Installed(jar=jar, jvm=_bundled_jvm(root), version=version)


def _install_jar(root: Path) -> Path | None:
    """jar/OpenRocket-*.jar (24.12-era layout, newest version wins), else
    OpenRocket.jar at the root (older layout)."""

    def by_version(path: Path) -> tuple[int, tuple[int, int], str]:
        try:
            return (1, parse_version(path.name[len("OpenRocket-") : -len(".jar")]), path.name)
        except ValueError:
            return (0, (0, 0), path.name)

    jar_dir = root / "jar"
    if jar_dir.is_dir():
        candidates = sorted(
            (p for p in jar_dir.glob("OpenRocket-*.jar") if p.is_file()), key=by_version
        )
        if candidates:
            return candidates[-1]
    legacy = root / "OpenRocket.jar"
    return legacy if legacy.is_file() else None


def _bundled_jvm(root: Path) -> Path | None:
    """The install's bundled JVM library, gated on its release file saying
    Java 17+. All three OS layouts are probed unconditionally — synthetic
    trees stay testable on any platform."""
    for jre_home, lib in (
        (root / "jre", root / "jre" / "lib" / "server" / "libjvm.so"),
        (
            root / "jre.bundle" / "Contents" / "Home",
            root / "jre.bundle" / "Contents" / "Home" / "lib" / "server" / "libjvm.dylib",
        ),
        (root / "jre", root / "jre" / "bin" / "server" / "jvm.dll"),
    ):
        if lib.is_file() and _jre_major(jre_home / "release") >= 17:
            return lib
    return None


def _jre_major(release_file: Path) -> int:
    """The major from JAVA_VERSION="17.0.16" in a JRE release file; 0 when
    unreadable or absent. Java 8 reads as 1 ("1.8.0_...") and is rejected
    by the 17+ gate like everything else pre-17."""
    try:
        text = release_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    match = re.search(r'^JAVA_VERSION="?(\d+)', text, re.MULTILINE)
    return int(match.group(1)) if match else 0


def _orlab_version() -> str:
    # naming the installed version in the no-pin error points users at
    # upgrading when the pin exists in a newer release
    try:
        from importlib.metadata import version as dist_version

        return dist_version("orlab")
    except Exception:  # pragma: no cover - metadata missing in odd installs
        return "(this version)"
