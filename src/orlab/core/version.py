import zipfile
from typing import NamedTuple, Tuple

__all__ = ['read_or_version', 'parse_version', 'select_roots', 'PackageRoots']

# OpenRocket 24.12 split net.sf.openrocket into info.openrocket.core (headless)
# and info.openrocket.swing (GUI). Earlier versions use the single net.sf root.
_RENAME_VERSION = (24, 12)


class PackageRoots(NamedTuple):
    core: str   # root package for file/simulation/startup.Application/plugin classes
    swing: str  # root package for GUI classes (GuiModule)


def read_or_version(jar_path: str) -> str:
    """ Reads the OpenRocket version string from the jar's build.properties
        (present at the zip root in every release from 15.03 through 24.12),
        without starting a JVM.
    """
    with zipfile.ZipFile(jar_path) as jar:
        with jar.open("build.properties") as fh:
            for raw in fh.read().decode("utf-8", errors="replace").splitlines():
                line = raw.strip()
                if line.startswith("build.version="):
                    return line.split("=", 1)[1].strip()
    raise ValueError(f"No build.version found in {jar_path} build.properties")


def parse_version(version: str) -> Tuple[int, int]:
    """ Parses the leading numeric components of an OpenRocket version string.
        '23.09' -> (23, 9); '24.12.RC.01' -> (24, 12).
    """
    parts = version.split(".")
    numbers = []
    for part in parts[:2]:
        digits = "".join(ch for ch in part if ch.isdigit())
        if not digits:
            break
        numbers.append(int(digits))
    if len(numbers) < 2:
        raise ValueError(f"Unrecognized OpenRocket version string: {version!r}")
    return numbers[0], numbers[1]


def select_roots(version: str) -> PackageRoots:
    """ Returns the Java package roots for the given OpenRocket version. """
    if parse_version(version) >= _RENAME_VERSION:
        return PackageRoots(core="info.openrocket.core", swing="info.openrocket.swing")
    return PackageRoots(core="net.sf.openrocket", swing="net.sf.openrocket")
