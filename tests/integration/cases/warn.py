"""Forces parachute deployment at launch (deployment under thrust) so the
engine records warning/abort events, and prints the resulting event names.
On 24.12+ this produces SIM_WARN and SIM_ABORT — the events that crashed
get_events() before 0.3.1.

Usage: python warn.py <jar_path>
"""

import json
import sys
from pathlib import Path

import orlab

ORK = Path(__file__).parents[3] / "examples" / "simple_ork" / "simple.ork"


def main(jar_path):
    with orlab.OpenRocketInstance(jar_path=jar_path) as instance:
        orl = orlab.Helper(instance)
        doc = orl.load_doc(str(ORK))
        sim = doc.getSimulation(0)
        chute = orl.get_component_named(sim.getRocket(), "Parachute")
        if hasattr(chute, "getDeploymentConfigurations"):
            deployment = chute.getDeploymentConfigurations().getDefault()
        else:  # 15.03: singular accessor
            deployment = chute.getDeploymentConfiguration().getDefault()
        deploy_event = type(deployment.getDeployEvent())
        deployment.setDeployEvent(deploy_event.LAUNCH)
        orl.run_simulation(sim)
        events = orl.get_events(sim)
        print("RESULT " + json.dumps({"events": sorted(k.name for k in events)}))


if __name__ == "__main__":
    main(sys.argv[1])
