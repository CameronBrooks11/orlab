import zipfile

__all__ = ["read_or_version", "parse_version"]


def read_or_version(jar_path: str) -> str:
    """Reads the OpenRocket version string from the jar's build.properties
    (present at the zip root in every release from 15.03 through 24.12),
    without starting a JVM.
    """
    with zipfile.ZipFile(jar_path) as jar, jar.open("build.properties") as fh:
        for raw in fh.read().decode("utf-8", errors="replace").splitlines():
            line = raw.strip()
            if line.startswith("build.version="):
                return line.split("=", 1)[1].strip()
    raise ValueError(f"No build.version found in {jar_path} build.properties")


def parse_version(version: str) -> tuple[int, int]:
    """Parses the leading numeric components of an OpenRocket version string.
    '23.09' -> (23, 9); '24.12.RC.01' -> (24, 12). Snapshot builds use a
    placeholder minor and either separator ('26.xx-SNAPSHOT', '25.xx.SNAPSHOT');
    the placeholder parses as 0 so the major still selects roots and profiles.
    """
    parts = version.replace("-", ".").split(".")
    major_digits = "".join(ch for ch in parts[0] if ch.isdigit())
    if not major_digits:
        raise ValueError(f"Unrecognized OpenRocket version string: {version!r}")
    minor_digits = "".join(ch for ch in parts[1] if ch.isdigit()) if len(parts) > 1 else ""
    return int(major_digits), int(minor_digits) if minor_digits else 0
