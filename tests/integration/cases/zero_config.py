"""Boots OpenRocketInstance() with zero explicit configuration: no jar_path,
no ORLAB_JAR, no CLASSPATH, empty cwd — the jar must be found (and
re-verified) in the fetch_jar cache by the default resolution chain.

Usage: python zero_config.py   (ORLAB_JAR_CACHE points at a seeded cache)
"""

import json
from pathlib import Path

import orlab

ORK = Path(__file__).parents[3] / "examples" / "simple_ork" / "simple.ork"


def main():
    with orlab.OpenRocketInstance() as instance:
        orl = orlab.Helper(instance)
        doc = orl.load_doc(str(ORK))
        sim = doc.getSimulation(0)
        opts = sim.getOptions()
        opts.setWindSpeedAverage(0.0)
        opts.setWindTurbulenceIntensity(0.0)
        orl.run_simulation(sim)
        data = orl.get_timeseries(sim, [orlab.FlightDataType.TYPE_ALTITUDE])

        print(
            "RESULT "
            + json.dumps(
                {
                    "version": instance.or_version,
                    "jar": str(instance.jar_path),
                    "apogee": float(max(data[orlab.FlightDataType.TYPE_ALTITUDE])),
                }
            )
        )


if __name__ == "__main__":
    main()
