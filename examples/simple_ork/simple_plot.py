import os

import numpy as np
from matplotlib import pyplot as plt

import orlab
from orlab import FlightDataType, FlightEvent

with orlab.OpenRocketInstance() as instance:
    orl = orlab.Helper(instance)

    # Load document, run simulation and get data and events

    doc = orl.load_doc(os.path.join("examples/simple_ork", "simple.ork"))
    sim = doc.getSimulation(0)
    orl.run_simulation(sim)
    data = orl.get_timeseries(
        sim,
        [
            FlightDataType.TYPE_TIME,
            FlightDataType.TYPE_ALTITUDE,
            FlightDataType.TYPE_VELOCITY_Z,
        ],
    )
    events = orl.get_events(sim)

    # Make a custom plot of the simulation

    events_to_annotate = {
        FlightEvent.BURNOUT: "Motor burnout",
        FlightEvent.APOGEE: "Apogee",
        FlightEvent.LAUNCHROD: "Launch rod clearance",
    }

    fig = plt.figure()
    ax1 = fig.add_subplot(111)
    ax2 = ax1.twinx()

    ax1.plot(data[FlightDataType.TYPE_TIME], data[FlightDataType.TYPE_ALTITUDE], "b-")
    ax2.plot(data[FlightDataType.TYPE_TIME], data[FlightDataType.TYPE_VELOCITY_Z], "r-")
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Altitude (m)", color="b")
    ax2.set_ylabel("Vertical Velocity (m/s)", color="r")

    def change_color(ax, col):
        for x in ax.get_yticklabels():
            x.set_color(col)

    change_color(ax1, "b")
    change_color(ax2, "r")

    def index_at(t):
        return (np.abs(data[FlightDataType.TYPE_TIME] - t)).argmin()

    for event, times in events.items():
        if event not in events_to_annotate:
            continue
        for time in times:
            ax1.annotate(
                events_to_annotate[event],
                xy=(time, data[FlightDataType.TYPE_ALTITUDE][index_at(time)]),
                xycoords="data",
                xytext=(20, 0),
                textcoords="offset points",
                arrowprops={"arrowstyle": "->", "connectionstyle": "arc3"},
            )

    ax1.grid(True)

# Data is plain numpy by now; the plot needs nothing from the instance
plt.show()
