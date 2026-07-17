"""Discovers a (fake, installer-layout) OpenRocket install via
ORLAB_OR_INSTALL_DIR and boots it explicitly — the documented find_installed
flow — through a full simulation.

Usage: python discovery_boot.py   (ORLAB_OR_INSTALL_DIR points at the tree)
"""

import json
from pathlib import Path

import orlab
from orlab.jars import find_installed

ORK = Path(__file__).parents[3] / "examples" / "simple_ork" / "simple.ork"


def main():
    inst = find_installed()
    assert inst is not None, "discovery found nothing"
    with orlab.OpenRocketInstance(str(inst.jar), jvm_path=inst.jvm) as instance:
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
                    "jar": str(inst.jar),
                    "jvm": str(inst.jvm) if inst.jvm else None,
                    "apogee": float(max(data[orlab.FlightDataType.TYPE_ALTITUDE])),
                }
            )
        )


if __name__ == "__main__":
    main()
