"""ThrustFactor against a real flight: factor 1.5 lifts apogee materially
above the same-seed zero-wind baseline.

Usage: python thrust_factor.py <jar_path>
"""

import json
import sys
from pathlib import Path

import orlab
from orlab.listeners import ThrustFactor

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
        baseline = orl.get_summary(sim).apogee

        opts.setRandomSeed(42)
        orl.run_simulation(sim, listeners=[ThrustFactor(1.5)], randomize_seed=False)
        boosted = orl.get_summary(sim).apogee

        print(
            "RESULT "
            + json.dumps({"version": instance.or_version, "baseline": baseline, "boosted": boosted})
        )


if __name__ == "__main__":
    main(sys.argv[1])
