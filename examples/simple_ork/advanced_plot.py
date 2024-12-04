# advanced_plot.py

import os
import numpy as np
from matplotlib import pyplot as plt

import orlab
from orlab import FlightDataType

with orlab.OpenRocketInstance() as instance:
    orl = orlab.Helper(instance)

    # Load the document and get the simulation
    doc = orl.load_doc(os.path.join("examples/simple_ork", "simple.ork"))
    sim = doc.getSimulation(0)
    orl.run_simulation(sim)

    # Retrieve multiple flight data types
    data = orl.get_timeseries(
        sim,
        [
            FlightDataType.TYPE_TIME,
            FlightDataType.TYPE_ALTITUDE,
            FlightDataType.TYPE_VELOCITY_TOTAL,
            FlightDataType.TYPE_ACCELERATION_TOTAL,
            FlightDataType.TYPE_THRUST_FORCE,
            FlightDataType.TYPE_DRAG_FORCE,
            FlightDataType.TYPE_MASS,
            FlightDataType.TYPE_MACH_NUMBER,
            FlightDataType.TYPE_AOA,  # Angle of Attack
            FlightDataType.TYPE_CG_LOCATION,
            FlightDataType.TYPE_CP_LOCATION,
        ],
    )

    # Create subplots for various flight parameters
    fig, axs = plt.subplots(4, 2, figsize=(15, 20))

    # Adjust spacing between plots
    plt.subplots_adjust(hspace=0.5, wspace=0.3)

    # Altitude vs Time
    axs[0, 0].plot(data[FlightDataType.TYPE_TIME], data[FlightDataType.TYPE_ALTITUDE], "b-")
    axs[0, 0].set_xlabel("Time (s)")
    axs[0, 0].set_ylabel("Altitude (m)")
    axs[0, 0].set_title("Altitude vs Time")
    axs[0, 0].grid(True)

    # Total Velocity vs Time
    axs[0, 1].plot(data[FlightDataType.TYPE_TIME], data[FlightDataType.TYPE_VELOCITY_TOTAL], "r-")
    axs[0, 1].set_xlabel("Time (s)")
    axs[0, 1].set_ylabel("Velocity (m/s)")
    axs[0, 1].set_title("Total Velocity vs Time")
    axs[0, 1].grid(True)

    # Total Acceleration vs Time
    axs[1, 0].plot(data[FlightDataType.TYPE_TIME], data[FlightDataType.TYPE_ACCELERATION_TOTAL], "g-")
    axs[1, 0].set_xlabel("Time (s)")
    axs[1, 0].set_ylabel("Acceleration (m/s²)")
    axs[1, 0].set_title("Total Acceleration vs Time")
    axs[1, 0].grid(True)

    # Thrust and Drag Forces vs Time
    axs[1, 1].plot(data[FlightDataType.TYPE_TIME], data[FlightDataType.TYPE_THRUST_FORCE], "m-", label="Thrust Force")
    axs[1, 1].plot(data[FlightDataType.TYPE_TIME], data[FlightDataType.TYPE_DRAG_FORCE], "c-", label="Drag Force")
    axs[1, 1].set_xlabel("Time (s)")
    axs[1, 1].set_ylabel("Force (N)")
    axs[1, 1].set_title("Thrust and Drag Forces vs Time")
    axs[1, 1].legend()
    axs[1, 1].grid(True)

    # Mass vs Time
    axs[2, 0].plot(data[FlightDataType.TYPE_TIME], data[FlightDataType.TYPE_MASS], "k-")
    axs[2, 0].set_xlabel("Time (s)")
    axs[2, 0].set_ylabel("Mass (kg)")
    axs[2, 0].set_title("Mass vs Time")
    axs[2, 0].grid(True)

    # Mach Number vs Time
    axs[2, 1].plot(data[FlightDataType.TYPE_TIME], data[FlightDataType.TYPE_MACH_NUMBER], "b-")
    axs[2, 1].set_xlabel("Time (s)")
    axs[2, 1].set_ylabel("Mach Number")
    axs[2, 1].set_title("Mach Number vs Time")
    axs[2, 1].grid(True)

    # Angle of Attack vs Time
    axs[3, 0].plot(data[FlightDataType.TYPE_TIME], data[FlightDataType.TYPE_AOA], "r-")
    axs[3, 0].set_xlabel("Time (s)")
    axs[3, 0].set_ylabel("Angle of Attack (deg)")
    axs[3, 0].set_title("Angle of Attack vs Time")
    axs[3, 0].grid(True)

    # CG and CP Locations vs Time
    axs[3, 1].plot(data[FlightDataType.TYPE_TIME], data[FlightDataType.TYPE_CG_LOCATION], "g-", label="CG Location")
    axs[3, 1].plot(data[FlightDataType.TYPE_TIME], data[FlightDataType.TYPE_CP_LOCATION], "m-", label="CP Location")
    axs[3, 1].set_xlabel("Time (s)")
    axs[3, 1].set_ylabel("Location (m)")
    axs[3, 1].set_title("CG and CP Locations vs Time")
    axs[3, 1].legend()
    axs[3, 1].grid(True)

# Show the plot
plt.show()
