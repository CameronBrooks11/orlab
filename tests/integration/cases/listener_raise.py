"""Runs a simulation with a listener that raises mid-flight and reports how
the exception surfaces in Python.

Usage: python listener_raise.py <jar_path>
"""

import json
import sys
from pathlib import Path

import orlab

ORK = Path(__file__).parents[3] / "examples" / "simple_ork" / "simple.ork"


class Bomb(orlab.AbstractSimulationListener):
    def postStep(self, status):
        raise RuntimeError("boom from python listener")


def main(jar_path):
    with orlab.OpenRocketInstance(jar_path=jar_path) as instance:
        orl = orlab.Helper(instance)
        doc = orl.load_doc(str(ORK))
        sim = doc.getSimulation(0)
        try:
            orl.run_simulation(sim, listeners=[Bomb()])
            outcome = {"propagated": None}
        except Exception as e:
            outcome = {"propagated": type(e).__name__, "message": str(e)[:200]}
        print("RESULT " + json.dumps(outcome))


if __name__ == "__main__":
    main(sys.argv[1])
