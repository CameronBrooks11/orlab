import math
import os
from random import gauss

import numpy as np

import orlab


class LandingPoints(list):
    "A list of flight summaries with ability to run simulations and populate itself"

    def add_simulations(self, num):
        with orlab.OpenRocketInstance() as instance:
            # Load the document and get simulation
            orl = orlab.Helper(instance)
            doc = orl.load_doc(os.path.join(os.path.dirname(__file__), "simple.ork"))
            sim = doc.getSimulation(0)

            # Randomize various parameters
            opts = sim.getOptions()
            rocket = sim.getRocket()

            # Run num simulations and add to self
            for p in range(num):
                print("Running simulation ", p)

                opts.setLaunchRodAngle(math.radians(gauss(45, 5)))  # 45 +- 5 deg in direction
                opts.setLaunchRodDirection(math.radians(gauss(0, 5)))  # 0 +- 5 deg in direction
                opts.setWindSpeedAverage(gauss(15, 5))  # 15 +- 5 m/s in wind
                for component_name in (
                    "Nose cone",
                    "Body tube",
                ):  # 5% in the mass of various components
                    component = orl.get_component_named(rocket, component_name)
                    mass = component.getMass()
                    component.setMassOverridden(True)
                    component.setOverrideMass(mass * gauss(1.0, 0.05))

                airstarter = AirStart(
                    gauss(1000, 50)
                )  # simulation listener to drop from 1000 m +- 50
                orl.run_simulation(sim, listeners=(airstarter,))
                self.append(orl.get_summary(sim))

    def print_stats(self):
        ranges = [s.landing_distance for s in self]
        bearings = [math.radians(s.landing_bearing_deg) for s in self]
        # Bearings are angles: average them as unit vectors, not raw numbers
        # (the arithmetic mean of 1 deg and 359 deg is 180 deg, not 0 deg).
        mean_bearing = math.atan2(np.mean(np.sin(bearings)), np.mean(np.cos(bearings))) % (
            2 * math.pi
        )
        print(
            f"Rocket landing zone {np.mean(ranges):3.2f} m +- {np.std(ranges):3.2f} m "
            f"bearing {math.degrees(mean_bearing):3.2f} deg from launch site. "
            f"Based on {len(self)} simulations."
        )


class AirStart(orlab.AbstractSimulationListener):
    def __init__(self, altitude):
        self.start_altitude = altitude

    def startSimulation(self, status):
        position = status.getRocketPosition()
        position = position.add(0.0, 0.0, self.start_altitude)
        status.setRocketPosition(position)


if __name__ == "__main__":
    points = LandingPoints()
    points.add_simulations(20)
    points.print_stats()
