"""Tabular export (get_dataframe / export_csv), jar-free via duck-typed
branch stubs. The pandas-dependent tests importorskip; the error-message
test runs everywhere."""

import csv
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from orlab import Helper


class _Unit:
    def __init__(self, unit):
        self._unit = unit

    def getUnitGroup(self):
        return self

    def getSIUnit(self):
        return self

    def getUnit(self):
        return self._unit


class _JavaType(_Unit):
    """A fake FlightDataType java constant carrying only its SI unit."""


class _Branch:
    def __init__(self, series):
        self._series = series

    def get(self, java_type):
        return self._series.get(java_type)


TYPES = {
    "TYPE_TIME": _JavaType("s"),
    "TYPE_ALTITUDE": _JavaType("m"),
    "TYPE_ACCELERATION_TOTAL": _JavaType("m/s²"),
    "TYPE_MACH_NUMBER": _JavaType("\u200b"),  # OpenRocket's dimensionless marker
    "TYPE_STABILITY": _JavaType(" \u200b "),
    "TYPE_UNPOPULATED": _JavaType("m"),  # not on the branch: excluded by default
}

SERIES = {
    TYPES["TYPE_TIME"]: [0.0, 1.0, 2.0],
    TYPES["TYPE_ALTITUDE"]: [0.0, 10.0, 20.0],
    TYPES["TYPE_ACCELERATION_TOTAL"]: [30.0, 5.0, 1.0],
    TYPES["TYPE_MACH_NUMBER"]: [0.0, 0.05, 0.08],
    TYPES["TYPE_STABILITY"]: [np.nan, 2.5, 3.0],
}


def _helper():
    h = Helper.__new__(Helper)
    h._instance = SimpleNamespace(
        or_version="24.12",
        profile=SimpleNamespace(flight_data_types=frozenset(TYPES)),
    )
    h.translate_flight_data_type = lambda v: TYPES[v if isinstance(v, str) else v.name]
    h._sim = SimpleNamespace(
        getSimulatedData=lambda: SimpleNamespace(getBranch=lambda i: _Branch(SERIES))
    )
    return h


EXPECTED_LABELS = [
    "TYPE_TIME (s)",  # first, despite name order
    "TYPE_ACCELERATION_TOTAL (m/s²)",
    "TYPE_ALTITUDE (m)",
    "TYPE_MACH_NUMBER",  # zero-width-space unit: no suffix
    "TYPE_STABILITY",  # whitespace+zero-width: no suffix
]


def test_default_columns_populated_profile_types_time_first():
    h = _helper()
    branch = _Branch(SERIES)
    labels = [label for label, _ in h._tabular_columns(branch, None)]
    assert labels == EXPECTED_LABELS  # TYPE_UNPOPULATED excluded


def test_explicit_variables_keep_order_and_accept_strings():
    h = _helper()
    branch = _Branch(SERIES)
    labels = [label for label, _ in h._tabular_columns(branch, ["TYPE_ALTITUDE", "TYPE_TIME"])]
    assert labels == ["TYPE_ALTITUDE (m)", "TYPE_TIME (s)"]


def test_get_dataframe():
    pd = pytest.importorskip("pandas")
    h = _helper()
    frame = h.get_dataframe(h._sim)
    assert list(frame.columns) == EXPECTED_LABELS
    assert len(frame) == 3
    assert frame["TYPE_ALTITUDE (m)"].tolist() == [0.0, 10.0, 20.0]
    assert pd.isna(frame["TYPE_STABILITY"][0])


def test_get_dataframe_error_names_the_extra(monkeypatch):
    h = _helper()
    monkeypatch.setitem(sys.modules, "pandas", None)  # import -> ImportError
    with pytest.raises(ImportError, match=r"pip install orlab\[pandas\]"):
        h.get_dataframe(h._sim)


def test_export_csv_utf8_nan_and_round_trip(tmp_path):
    h = _helper()
    out = tmp_path / "flight.csv"
    h.export_csv(h._sim, out)

    raw = out.read_bytes()
    assert "m/s²".encode() in raw  # utf-8, superscript intact
    assert b"\r\r" not in raw  # newline='' guards Windows double-translation

    with open(out, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == EXPECTED_LABELS
    assert len(rows) == 1 + 3
    stability_column = rows[0].index("TYPE_STABILITY")
    assert rows[1][stability_column] == ""  # NaN -> empty cell
    assert float(rows[2][stability_column]) == 2.5


def test_export_csv_read_back_by_pandas(tmp_path):
    pd = pytest.importorskip("pandas")
    h = _helper()
    out = tmp_path / "flight.csv"
    h.export_csv(h._sim, out)
    frame = pd.read_csv(out)
    assert list(frame.columns) == EXPECTED_LABELS
    assert pd.isna(frame["TYPE_STABILITY"][0])
    assert frame["TYPE_TIME (s)"].tolist() == [0.0, 1.0, 2.0]


def test_explicit_unpopulated_variable_curated_error():
    """Both methods must refuse an unpopulated explicit variable loudly —
    not a raw TypeError (csv) or a silent NaN column (pandas)."""
    h = _helper()
    with pytest.raises(ValueError, match="TYPE_UNPOPULATED is not populated"):
        h._tabular_columns(_Branch(SERIES), ["TYPE_TIME", "TYPE_UNPOPULATED"])


def test_default_columns_tolerate_profile_drift(caplog):
    """A fallback profile listing a constant the live jar dropped must skip
    it with a warning, never abort a default export."""
    import logging

    from orlab.errors import UnsupportedFlightDataType

    h = _helper()
    real_translate = h.translate_flight_data_type

    def translate(v):
        if v == "TYPE_ALTITUDE":
            raise UnsupportedFlightDataType("gone in this jar")
        return real_translate(v)

    h.translate_flight_data_type = translate
    import orlab.core.helper as helper_mod

    helper_mod._absence_warned.discard("TYPE_ALTITUDE")
    with caplog.at_level(logging.WARNING):
        labels = [label for label, _ in h._tabular_columns(_Branch(SERIES), None)]
    assert "TYPE_ALTITUDE (m)" not in labels
    assert "TYPE_TIME (s)" in labels
    assert "TYPE_ALTITUDE" in caplog.text
