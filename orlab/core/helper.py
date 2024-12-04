import jpype
import numpy as np
from copy import copy
from typing import Union, List, Iterable, Dict
from .._enums import *
from ..utils.utils import _get_private_field
from .openrocket_instance import OpenRocketInstance
from .simulation_listener import AbstractSimulationListener  
from .jiterator import JIterator

__all__ = ['Helper']


class Helper:
    """ This class contains a variety of useful helper functions and wrapper for using
        openrocket via jpype. These are intended to take care of some of the more
        cumbersome aspects of calling methods, or provide more 'pythonic' data structures
        for general use.
    """

    def __init__(self, open_rocket_instance: OpenRocketInstance):
        if not open_rocket_instance.started:
            raise Exception("OpenRocketInstance not yet started")

        self.openrocket = open_rocket_instance.openrocket

    def load_doc(self, or_filename):
        """ Loads a .ork file and returns the corresponding openrocket document """

        or_java_file = jpype.java.io.File(or_filename)
        loader = self.openrocket.file.GeneralRocketLoader(or_java_file)
        doc = loader.load()
        return doc

    def save_doc(self, or_filename, doc):
        """ Saves an openrocket document to a .ork file """
        
        or_java_file = jpype.java.io.File(or_filename)
        saver = self.openrocket.file.GeneralRocketSaver()
        saver.save(or_java_file, doc)

    def run_simulation(self, sim, listeners: List[AbstractSimulationListener] = None):
        """ This is a wrapper to the Simulation.simulate() for running a simulation
            The optional listeners parameter is a sequence of objects which extend orl.AbstractSimulationListener.
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

        sim.getOptions().randomizeSeed()  # Need to do this otherwise exact same numbers will be generated for each identical run
        sim.simulate(listener_array)

    def translate_flight_data_type(self, flight_data_type:Union[FlightDataType, str]):
        if isinstance(flight_data_type, FlightDataType):
            name = flight_data_type.name
        elif isinstance(flight_data_type, str):
            name = flight_data_type
        else:
            raise TypeError("Invalid type for flight_data_type")

        return getattr(self.openrocket.simulation.FlightDataType, name)

    def get_timeseries(self, simulation, variables: Iterable[Union[FlightDataType, str]], branch_number=0) \
            -> Dict[Union[FlightDataType, str], np.array]:
        """
        Gets a dictionary of timeseries data (as numpy arrays) from a simulation given specific variable names.

        :param simulation: An openrocket simulation object.
        :param variables: A sequence of FlightDataType or strings representing the desired variables
        :param branch_number:
        :return:
        """

        branch = simulation.getSimulatedData().getBranch(branch_number)
        output = dict()
        for v in variables:
            output[v] = np.array(branch.get(self.translate_flight_data_type(v)))

        return output

    def get_final_values(self, simulation, variables: Iterable[Union[FlightDataType, str]], branch_number=0) \
            -> Dict[Union[FlightDataType, str], float]:
        """
        Gets a the final value in the time series from a simulation given variable names.

        :param simulation: An openrocket simulation object.
        :param variables: A sequence of FlightDataType or strings representing the desired variables
        :param branch_number:
        :return:
        """

        branch = simulation.getSimulatedData().getBranch(branch_number)
        output = dict()
        for v in variables:
            output[v] = branch.get(self.translate_flight_data_type(v))[-1]

        return output

    def translate_flight_event(self, flight_event) -> FlightEvent:
        return {getattr(self.openrocket.simulation.FlightEvent.Type, x.name): x for x in FlightEvent}[flight_event]

    def get_events(self, simulation) -> Dict[FlightEvent, float]:
        """Returns a dictionary of all the flight events in a given simulation.
           Key is FlightEvent and value is a list of all the times at which the event occurs.
        """
        branch = simulation.getSimulatedData().getBranch(0)

        output = dict()
        for ev in branch.getEvents():
            type = self.translate_flight_event(ev.getType())
            if type in output:
                output[type].append(float(ev.getTime()))
            else:
                output[type] = [float(ev.getTime())]

        return output

    def get_component_named(self, root, name):
        """ Finds and returns the first rocket component with the given name.
            Requires a root RocketComponent, usually this will be a RocketComponent.rocket instance.
            Raises a ValueError if no component found.
        """

        for component in JIterator(root):
            if component.getName() == name:
                return component
        raise ValueError(root.toString() + " has no component named " + name)

    def get_all_components(self, root) -> List[jpype.JObject]:
        """ Returns a list of all rocket components in the loaded OpenRocket file.

            :param root: The root RocketComponent (usually obtained from the simulation)
            :return: List of all component objects
        """
        components = []
        for component in JIterator(root):
            components.append(component)
        return components