"""The epic's summary-table composition, end to end: a parent process with
its own live JVM coexists with pool workers, and a worker_fn returns full
FlightSummary objects across the spawn boundary.

Usage: python pool_compose.py <jar_path>
"""

import json
import math
import sys
from pathlib import Path

import orlab

ORK = Path(__file__).parents[3] / "examples" / "simple_ork" / "simple.ork"


def summary_fn(helper, sim, task):
    opts = sim.getOptions()
    opts.setWindSpeedAverage(task["wind"])
    opts.setWindTurbulenceIntensity(0.0)
    helper.run_simulation(sim, randomize_seed=False)
    return helper.get_summary(sim)  # a full FlightSummary crosses the boundary


def main(jar_path):
    # the parent runs its own simulation first — pool workers must coexist
    # with a parent JVM
    with orlab.OpenRocketInstance(jar_path=jar_path) as instance:
        orl = orlab.Helper(instance)
        doc = orl.load_doc(str(ORK))
        sim = doc.getSimulation(0)
        sim.getOptions().setWindSpeedAverage(0.0)
        sim.getOptions().setWindTurbulenceIntensity(0.0)
        orl.run_simulation(sim)
        parent_apogee = orl.get_summary(sim).apogee

    pool = orlab.SimulationPool(str(ORK), jar_path, max_workers=2, jvm_args=("-Xmx512m",))
    study = pool.run([{"wind": 0.0}, {"wind": 5.0}, {"wind": 10.0}], worker_fn=summary_fn)
    pool.shutdown()

    rows = [s.payload.to_dict() for s in study.results]
    print(
        "RESULT "
        + json.dumps(
            {
                "parent_apogee": parent_apogee,
                "pool_ok": len(study.results),
                "payload_type": type(study.results[0].payload).__name__,
                "apogees": [r["apogee"] for r in rows],
                "windy_drifts_more": rows[2]["landing_distance"] > rows[0]["landing_distance"],
                "fields_finite": all(
                    not math.isnan(r["apogee"]) and not math.isnan(r["descent_rate"]) for r in rows
                ),
            }
        )
    )


if __name__ == "__main__":
    main(sys.argv[1])
