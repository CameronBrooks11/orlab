import zipfile

import pytest

from orlab.core.version import parse_version, read_or_version


def _jar_with_properties(tmp_path, content):
    jar = tmp_path / "fake.jar"
    with zipfile.ZipFile(jar, "w") as z:
        z.writestr("build.properties", content)
    return str(jar)


def test_read_or_version(tmp_path):
    jar = _jar_with_properties(tmp_path, "# comment\nbuild.version=24.12\nother=x\n")
    assert read_or_version(jar) == "24.12"


def test_read_or_version_strips_whitespace(tmp_path):
    jar = _jar_with_properties(tmp_path, "build.version= 23.09 \n")
    assert read_or_version(jar) == "23.09"


def test_read_or_version_missing_key(tmp_path):
    jar = _jar_with_properties(tmp_path, "name=OpenRocket\n")
    with pytest.raises(ValueError):
        read_or_version(jar)


def test_read_or_version_no_properties_entry(tmp_path):
    jar = tmp_path / "empty.jar"
    with zipfile.ZipFile(jar, "w") as z:
        z.writestr("something.txt", "hi")
    with pytest.raises(KeyError):
        read_or_version(str(jar))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("23.09", (23, 9)),
        ("24.12", (24, 12)),
        ("15.03", (15, 3)),
        ("24.12.RC.01", (24, 12)),
        ("24.12.beta.01", (24, 12)),
        ("25.01", (25, 1)),
    ],
)
def test_parse_version(raw, expected):
    assert parse_version(raw) == expected


def test_parse_version_rejects_garbage():
    with pytest.raises(ValueError):
        parse_version("unknown")
