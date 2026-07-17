"""Loads simple.ork, runs a zero-wind simulation with a counting listener,
checks the live enum surface against the profile, and prints one RESULT line.

Usage: python happy.py <jar_path>
"""

import json
import sys
from pathlib import Path

import orlab
from orlab.core.openrocket_instance import reflect_live_constants

ORK = Path(__file__).parents[3] / "examples" / "simple_ork" / "simple.ork"


class Counter(orlab.AbstractSimulationListener):
    """OpenRocket clones listeners; count through a shared list."""

    def __init__(self, calls):
        self.calls = calls

    def postStep(self, status):
        self.calls.append(1)


def main(jar_path):
    calls = []
    with orlab.OpenRocketInstance(jar_path=jar_path) as instance:
        orl = orlab.Helper(instance)
        doc = orl.load_doc(str(ORK))
        sim = doc.getSimulation(0)
        opts = sim.getOptions()
        opts.setWindSpeedAverage(0.0)
        opts.setWindTurbulenceIntensity(0.0)
        orl.run_simulation(sim, listeners=[Counter(calls)])

        data = orl.get_timeseries(
            sim, [orlab.FlightDataType.TYPE_ALTITUDE, orlab.FlightDataType.TYPE_VELOCITY_TOTAL]
        )
        events = orl.get_events(sim)

        live_types, live_events = reflect_live_constants(instance.openrocket)
        profile = instance.profile

        print(
            "RESULT "
            + json.dumps(
                {
                    "version": instance.or_version,
                    "apogee": float(max(data[orlab.FlightDataType.TYPE_ALTITUDE])),
                    "vmax": float(max(data[orlab.FlightDataType.TYPE_VELOCITY_TOTAL])),
                    "events": sorted(k.name for k in events),
                    "listener_calls": len(calls),
                    "profile_version": profile.version_string,
                    "extra_types": sorted(live_types - profile.flight_data_types),
                    "missing_types": sorted(profile.flight_data_types - live_types),
                    "extra_events": sorted(live_events - profile.flight_events),
                    "missing_events": sorted(profile.flight_events - live_events),
                }
            )
        )


if __name__ == "__main__":
    main(sys.argv[1])
