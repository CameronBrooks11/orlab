"""export_csv against a real flight: default columns, per-version unit
headers, NaN cells. Prints the header row and shape facts for the parent to
pin.

Usage: python tabular.py <jar_path>
"""

import csv
import json
import sys
import tempfile
from pathlib import Path

import orlab

ORK = Path(__file__).parents[3] / "examples" / "simple_ork" / "simple.ork"


def main(jar_path):
    with orlab.OpenRocketInstance(jar_path=jar_path) as instance:
        orl = orlab.Helper(instance)
        doc = orl.load_doc(str(ORK))
        sim = doc.getSimulation(0)
        opts = sim.getOptions()
        opts.setWindSpeedAverage(0.0)
        opts.setWindTurbulenceIntensity(0.0)
        opts.setRandomSeed(42)
        orl.run_simulation(sim, randomize_seed=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "flight.csv"
            orl.export_csv(sim, out)
            with open(out, newline="", encoding="utf-8") as fh:
                rows = list(csv.reader(fh))
        header, data_rows = rows[0], rows[1:]

        time_series = orl.get_timeseries(sim, [orlab.FlightDataType.TYPE_TIME])
        stability_column = header.index("TYPE_STABILITY")

        print(
            "RESULT "
            + json.dumps(
                {
                    "version": instance.or_version,
                    "header": header,
                    "rows": len(data_rows),
                    "time_samples": len(time_series[orlab.FlightDataType.TYPE_TIME]),
                    "first_stability_cell": data_rows[0][stability_column],
                    "any_empty_stability": any(r[stability_column] == "" for r in data_rows),
                    "last_time_cell": data_rows[-1][0],
                }
            )
        )


if __name__ == "__main__":
    main(sys.argv[1])
