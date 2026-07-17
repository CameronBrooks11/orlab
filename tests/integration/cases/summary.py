"""get_summary on simple.ork: a zero-wind leg with tight expectations, a
wind-on/turbulence-zero leg with coarse ones, and the summary pickled for
the JVM-less parent to load.

Usage: python summary.py <jar_path>
"""

import base64
import json
import pickle
import sys
from pathlib import Path

import orlab

ORK = Path(__file__).parents[3] / "examples" / "simple_ork" / "simple.ork"


def run(orl, sim, wind):
    opts = sim.getOptions()
    opts.setWindSpeedAverage(wind)
    opts.setWindTurbulenceIntensity(0.0)
    opts.setRandomSeed(42)
    orl.run_simulation(sim, randomize_seed=False)
    return orl.get_summary(sim)


def main(jar_path):
    with orlab.OpenRocketInstance(jar_path=jar_path) as instance:
        orl = orlab.Helper(instance)
        doc = orl.load_doc(str(ORK))
        sim = doc.getSimulation(0)

        calm = run(orl, sim, 0.0)
        windy = run(orl, sim, 5.0)

        print(
            "RESULT "
            + json.dumps(
                {
                    "version": instance.or_version,
                    "calm": calm.to_dict(),
                    "windy": windy.to_dict(),
                    "calm_str": str(calm),
                    "pickle_b64": base64.b64encode(pickle.dumps(calm)).decode(),
                }
            )
        )


if __name__ == "__main__":
    main(sys.argv[1])
