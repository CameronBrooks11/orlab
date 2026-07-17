"""Motor swapping, fully deterministic (fixed seed, zero wind): the
sim-fcid rule, the selected-config silent no-op pinned forever, DB and
.eng-file swaps changing apogee, delay semantics.

Usage: python motor_swap.py <jar_path>
"""

import json
import sys
from pathlib import Path

import orlab

ORK = Path(__file__).parents[3] / "examples" / "simple_ork" / "simple.ork"
ENG = Path(__file__).parents[1] / "fixtures" / "orlab45.eng"


def run(orl, sim):
    sim.getOptions().setRandomSeed(42)
    orl.run_simulation(sim, randomize_seed=False)
    return orl.get_summary(sim)


def main(jar_path):
    with orlab.OpenRocketInstance(jar_path=jar_path) as instance:
        orl = orlab.Helper(instance)
        doc = orl.load_doc(str(ORK))
        sim = doc.getSimulation(0)
        opts = sim.getOptions()
        opts.setWindSpeedAverage(0.0)
        opts.setWindTurbulenceIntensity(0.0)

        out = {"version": instance.or_version, "initial": orl.get_motor(sim)}
        stock = run(orl, sim).apogee
        out["stock_apogee"] = stock

        # the classic silent failure: assign to the rocket's SELECTED
        # config via raw Java — the sim must be unaffected
        rocket = sim.getRocket()
        selected_fcid = None
        if hasattr(rocket, "getSelectedConfiguration"):
            selected_fcid = rocket.getSelectedConfiguration().getId()
        sim_fcid = orl._sim_fcid(sim)
        out["fcids_differ"] = selected_fcid is not None and str(selected_fcid) != str(sim_fcid)
        if selected_fcid is not None:
            mount = orl._resolve_mount(sim, None)
            wrong = orl._motor_config(mount, selected_fcid)
            if wrong is not None:
                wrong.setMotor(orl.find_motor("C6", manufacturer="Estes"))
                out["after_wrong_fcid"] = run(orl, sim).apogee

        # the right way: set_motor keys on the sim's own fcid
        orl.set_motor(sim, "C6", manufacturer="Estes")
        out["c6"] = {"designation": orl.get_motor(sim), "apogee": run(orl, sim).apogee}

        # file-loaded motor with an explicit ejection delay: the DEPLOYMENT
        # timing must reflect the delay we set, not the file's default
        orl.set_motor(sim, str(ENG), delay=2.0)
        summary_short = run(orl, sim)
        events_short = orl.get_events(sim)
        orl.set_motor(sim, str(ENG), delay=5.0)
        summary_long = run(orl, sim)
        events_long = orl.get_events(sim)
        deploy_short = events_short[orlab.FlightEvent.RECOVERY_DEVICE_DEPLOYMENT][0]
        deploy_long = events_long[orlab.FlightEvent.RECOVERY_DEVICE_DEPLOYMENT][0]
        burnout_short = events_short[orlab.FlightEvent.BURNOUT][0]
        burnout_long = events_long[orlab.FlightEvent.BURNOUT][0]
        out["eng"] = {
            "designation": orl.get_motor(sim),
            "apogee": summary_long.apogee,
            "apogee_short_delay": summary_short.apogee,
            "deploy_delta": (deploy_long - burnout_long) - (deploy_short - burnout_short),
        }

        print("RESULT " + json.dumps(out))


if __name__ == "__main__":
    main(sys.argv[1])
