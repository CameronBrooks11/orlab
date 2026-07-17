"""Applies every DECLARATIVE_KEYS entry (plus setRandomSeed) and reads each
value back, then flies a simulation with those options — the whitelist's
verified-on-every-version claim, checked on every version.

Usage: python declarative_keys.py <jar_path>
"""

import json
import sys
from pathlib import Path

import orlab
from orlab.parallel import DECLARATIVE_KEYS

ORK = Path(__file__).parents[3] / "examples" / "simple_ork" / "simple.ork"

VALUES = {
    "launch_rod_length": 1.5,
    "launch_rod_angle": 0.15,
    "launch_into_wind": False,
    "launch_rod_direction": 1.2,
    "launch_altitude": 1400.0,
    "launch_latitude": 43.5,
    "launch_longitude": -80.5,
    "wind_speed_average": 3.5,
    "wind_direction": 2.1,
}


def main(jar_path):
    with orlab.OpenRocketInstance(jar_path=jar_path) as instance:
        orl = orlab.Helper(instance)
        doc = orl.load_doc(str(ORK))
        sim = doc.getSimulation(0)
        opts = sim.getOptions()

        readback = {}
        for key, spec in DECLARATIVE_KEYS.items():  # declaration order matters
            getattr(opts, spec.setter)(VALUES[key])
            value = getattr(opts, spec.getter)()
            readback[key] = bool(value) if spec.kind is bool else float(value)
        opts.setRandomSeed(123456789)
        readback["random_seed"] = int(opts.getRandomSeed())

        opts.setWindTurbulenceIntensity(0.0)
        orl.run_simulation(sim, randomize_seed=False)
        summary = orl.get_summary(sim)

        print(
            "RESULT "
            + json.dumps(
                {
                    "version": instance.or_version,
                    "applied": VALUES,
                    "readback": readback,
                    "apogee": summary.apogee,
                }
            )
        )


if __name__ == "__main__":
    main(sys.argv[1])
