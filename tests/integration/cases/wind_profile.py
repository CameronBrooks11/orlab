"""WindProfile against a real flight: exact band means via the epsilon-step
idiom, plus a nonzero-direction leg pinning the drift sign against
setWindDirection's convention.

Usage: python wind_profile.py <jar_path>
"""

import json
import math
import sys
from pathlib import Path

import numpy as np

import orlab
from orlab.listeners import WindProfile

ORK = Path(__file__).parents[3] / "examples" / "simple_ork" / "simple.ork"


def main(jar_path):
    with orlab.OpenRocketInstance(jar_path=jar_path) as instance:
        orl = orlab.Helper(instance)
        doc = orl.load_doc(str(ORK))
        sim = doc.getSimulation(0)
        sim.getOptions().setRandomSeed(42)

        profile = WindProfile([0.0, 20.0, 20.001, 100.0], [5.0, 5.0, 20.0, 20.0])
        orl.run_simulation(sim, listeners=[profile], randomize_seed=False)
        data = orl.get_timeseries(
            sim,
            [
                orlab.FlightDataType.TYPE_ALTITUDE,
                orlab.FlightDataType.TYPE_WIND_VELOCITY,
            ],
        )
        alt = data[orlab.FlightDataType.TYPE_ALTITUDE]
        wind = data[orlab.FlightDataType.TYPE_WIND_VELOCITY]
        # generous margins: some versions pair the recorded wind with the
        # neighboring step's altitude, smearing the band edge
        low = (alt > 2.0) & (alt < 15.0) & ~np.isnan(wind)
        high = (alt > 25.0) & ~np.isnan(wind)

        # direction leg: wind FROM the east must drift the rocket west,
        # exactly like setWindDirection(pi/2)
        east = WindProfile([0.0, 100.0], [5.0, 5.0], directions_rad=math.pi / 2)
        sim.getOptions().setRandomSeed(42)
        orl.run_simulation(sim, listeners=[east], randomize_seed=False)
        summary = orl.get_summary(sim)

        print(
            "RESULT "
            + json.dumps(
                {
                    "version": instance.or_version,
                    "low_mean": float(wind[low].mean()),
                    "high_mean": float(wind[high].mean()),
                    "low_n": int(low.sum()),
                    "high_n": int(high.sum()),
                    "east_bearing": summary.landing_bearing_deg,
                    "east_distance": summary.landing_distance,
                }
            )
        )


if __name__ == "__main__":
    main(sys.argv[1])
