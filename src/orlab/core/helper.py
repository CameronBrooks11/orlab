import logging
from collections.abc import Iterable

import jpype
import numpy as np

from .._enums import FlightDataType, FlightEvent
from ..errors import OrlabError, UnsupportedFlightDataType
from ..profiles import versions_with
from .jiterator import JIterator
from .openrocket_instance import OpenRocketInstance
from .simulation_listener import AbstractSimulationListener

__all__ = ["Helper"]

logger = logging.getLogger(__name__)


class Helper:
    """This class contains a variety of useful helper functions and wrapper for using
    openrocket via jpype. These are intended to take care of some of the more
    cumbersome aspects of calling methods, or provide more 'pythonic' data structures
    for general use.
    """

    def __init__(self, open_rocket_instance: OpenRocketInstance):
        if not open_rocket_instance.started:
            raise OrlabError(
                "OpenRocketInstance not started — enter it first "
                "('with OpenRocketInstance(...) as instance:')"
            )

        self._instance = open_rocket_instance
        self.openrocket = open_rocket_instance.openrocket

    def load_doc(self, or_filename):
        """Loads a .ork file and returns the corresponding openrocket document"""

        or_java_file = jpype.java.io.File(or_filename)
        loader = self.openrocket.file.GeneralRocketLoader(or_java_file)
        doc = loader.load()
        return doc

    def save_doc(self, or_filename, doc):
        """Saves an openrocket document to a .ork file"""

        or_java_file = jpype.java.io.File(or_filename)
        saver = self.openrocket.file.GeneralRocketSaver()
        saver.save(or_java_file, doc)

    def run_simulation(
        self,
        sim,
        listeners: list[AbstractSimulationListener] | None = None,
        *,
        randomize_seed: bool = True,
    ):
        """This is a wrapper to the Simulation.simulate() for running a simulation
        The optional listeners parameter is a sequence of objects which extend orl.AbstractSimulationListener.

        By default the simulation's random seed is randomized before each run
        (identical repeated runs would otherwise produce identical numbers —
        the behavior naive monte-carlo loops rely on). Pass
        randomize_seed=False to respect the seed already set on the options.
        Note: on OpenRocket 24.12 the wind model draws additional per-process
        entropy, so a fixed seed reproduces results within one process but not
        across processes when wind is enabled.
        """

        if listeners is None:
            # this method takes in a vararg of SimulationListeners, which is just a fancy way of passing in an array, so
            # we have to pass in an array of length 0 ..
            listener_array = jpype.JArray(
                self.openrocket.simulation.listeners.AbstractSimulationListener, 1
            )(0)
        else:
            listener_array = [
                jpype.JProxy(
                    (
                        self.openrocket.simulation.listeners.SimulationListener,
                        self.openrocket.simulation.listeners.SimulationEventListener,
                        self.openrocket.simulation.listeners.SimulationComputationListener,
                        jpype.java.lang.Cloneable,
                    ),
                    inst=c,
                )
                for c in listeners
            ]

        if randomize_seed:
            sim.getOptions().randomizeSeed()
        sim.simulate(listener_array)

    def translate_flight_data_type(self, flight_data_type: FlightDataType | str):
        """Translates a FlightDataType (or constant name) to the Java constant.
        Raises UnsupportedFlightDataType when the loaded OpenRocket version
        does not expose it (constants differ across versions).
        """
        if isinstance(flight_data_type, FlightDataType):
            name = flight_data_type.name
        elif isinstance(flight_data_type, str):
            name = flight_data_type
        else:
            raise TypeError("Invalid type for flight_data_type")

        java_type = getattr(self.openrocket.simulation.FlightDataType, name, None)
        if java_type is None:
            loaded = self._instance.or_version
            available = versions_with(name)
            detail = f"available in: {', '.join(available)}" if available else "unknown constant"
            raise UnsupportedFlightDataType(
                f"{name} is not available in OpenRocket {loaded} ({detail})"
            )
        return java_type

    def get_timeseries(
        self, simulation, variables: Iterable[FlightDataType | str], branch_number=0
    ) -> dict[FlightDataType | str, np.ndarray]:
        """
        Gets a dictionary of timeseries data (as numpy arrays) from a simulation given specific variable names.

        :param simulation: An openrocket simulation object.
        :param variables: A sequence of FlightDataType or strings representing the desired variables
        :param branch_number: Stage branch to read (0 = sustainer).
        :return: Dict keyed by the requested variables; values are numpy arrays.
        """

        branch = simulation.getSimulatedData().getBranch(branch_number)
        output: dict[FlightDataType | str, np.ndarray] = {}
        for v in variables:
            output[v] = np.array(branch.get(self.translate_flight_data_type(v)))

        return output

    def get_final_values(
        self, simulation, variables: Iterable[FlightDataType | str], branch_number=0
    ) -> dict[FlightDataType | str, float]:
        """
        Gets a the final value in the time series from a simulation given variable names.

        :param simulation: An openrocket simulation object.
        :param variables: A sequence of FlightDataType or strings representing the desired variables
        :param branch_number: Stage branch to read (0 = sustainer).
        :return: Dict keyed by the requested variables; values are the final samples.
        """

        branch = simulation.getSimulatedData().getBranch(branch_number)
        output: dict[FlightDataType | str, float] = {}
        for v in variables:
            output[v] = branch.get(self.translate_flight_data_type(v))[-1]

        return output

    def translate_flight_event(self, flight_event) -> FlightEvent:
        """Translates a Java FlightEvent.Type constant to the FlightEvent enum.
        Raises ValueError for event types this orlab version does not know
        (newer OpenRocket releases add types; get_events skips them instead).
        """
        name = str(flight_event.name())
        try:
            return FlightEvent[name]
        except KeyError:
            raise ValueError(
                f"Unknown flight event type {name!r} from the loaded OpenRocket version"
            ) from None

    def get_events(self, simulation) -> dict[FlightEvent, list[float]]:
        """Returns a dictionary of all the flight events in a given simulation.
        Key is FlightEvent and value is a list of all the times at which the event occurs.
        Event types not known to this orlab version are skipped with a warning.
        """
        branch = simulation.getSimulatedData().getBranch(0)

        output: dict[FlightEvent, list[float]] = {}
        unknown: set[str] = set()
        for ev in branch.getEvents():
            java_type = ev.getType()
            try:
                event = self.translate_flight_event(java_type)
            except ValueError:
                name = str(java_type.name())
                if name not in unknown:
                    unknown.add(name)
                    logger.warning("Skipping unknown flight event type %s", name)
                continue
            output.setdefault(event, []).append(float(ev.getTime()))

        return output

    def get_component_named(self, root, name):
        """Finds and returns the first rocket component with the given name.
        Requires a root RocketComponent, usually this will be a RocketComponent.rocket instance.
        Raises a ValueError if no component found.
        """

        for component in JIterator(root):
            if component.getName() == name:
                return component
        raise ValueError(root.toString() + " has no component named " + name)

    def get_all_components(self, root) -> list[jpype.JObject]:
        """Returns a list of all rocket components in the loaded OpenRocket file.

        :param root: The root RocketComponent (usually obtained from the simulation)
        :return: List of all component objects
        """
        components = []
        for component in JIterator(root):
            components.append(component)
        return components
