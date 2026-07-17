"""Two sequential OpenRocketInstance blocks in one process (the JVM is reused),
then an instance for a different jar path, which must fail with a clear error.

Usage: python reuse.py <jar_path>
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

import orlab
from orlab.errors import OrlabError

ORK = Path(__file__).parents[3] / "examples" / "simple_ork" / "simple.ork"


def apogee_once(jar_path):
    with orlab.OpenRocketInstance(jar_path=jar_path) as instance:
        orl = orlab.Helper(instance)
        doc = orl.load_doc(str(ORK))
        sim = doc.getSimulation(0)
        orl.run_simulation(sim)
        data = orl.get_timeseries(sim, [orlab.FlightDataType.TYPE_ALTITUDE])
        return float(max(data[orlab.FlightDataType.TYPE_ALTITUDE]))


def main(jar_path):
    first = apogee_once(jar_path)
    second = apogee_once(jar_path)  # same process, same jar: JVM reused

    # A different jar path (same bytes, elsewhere) must be refused clearly.
    with tempfile.TemporaryDirectory() as tmp:
        other = Path(tmp) / "copy.jar"
        shutil.copy(jar_path, other)
        try:
            orlab.OpenRocketInstance(jar_path=str(other)).__enter__()
            conflict = None
        except OrlabError as e:
            conflict = str(e)[:200]

    print(
        "RESULT "
        + json.dumps({"first_apogee": first, "second_apogee": second, "conflict": conflict})
    )


if __name__ == "__main__":
    main(sys.argv[1])
