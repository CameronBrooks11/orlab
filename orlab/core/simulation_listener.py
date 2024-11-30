from copy import copy
import jpype

__all__ = ['AbstractSimulationListener']


class AbstractSimulationListener:
    """ This is a python implementation of openrocket.simulation.listeners.AbstractSimulationListener.
        Subclasses of this are suitable for passing to helper.run_simulation.
    """

    def __str__(self):
        return (
                "'"
                + "Python simulation listener proxy : "
                + str(self.__class__.__name__)
                + "'"
        )

    def toString(self):
        return str(self)

    # SimulationListener
    def startSimulation(self, status) -> None:
        pass

    def endSimulation(self, status, simulation_exception) -> None:
        pass

    def preStep(self, status) -> bool:
        return True

    def postStep(self, status) -> None:
        pass

    def isSystemListener(self) -> bool:
        return False

    # SimulationEventListener
    def addFlightEvent(self, status, flight_event) -> bool:
        return True

    def handleFlightEvent(self, status, flight_event) -> bool:
        return True

    def motorIgnition(self, status, motor_id, motor_mount, motor_instance) -> bool:
        return True

    def recoveryDeviceDeployment(self, status, recovery_device) -> bool:
        return True

    # SimulationComputationListener
    def preAccelerationCalculation(self, status):
        return None

    def preAerodynamicCalculation(self, status):
        return None

    def preAtmosphericModel(self, status):
        return None

    def preFlightConditions(self, status):
        return None

    def preGravityModel(self, status):
        return float("nan")

    def preMassCalculation(self, status):
        return None

    def preSimpleThrustCalculation(self, status):
        return float("nan")

    def preWindModel(self, status):
        return None

    def postAccelerationCalculation(self, status, acceleration_data):
        return None

    def postAerodynamicCalculation(self, status, aerodynamic_forces):
        return None

    def postAtmosphericModel(self, status, atmospheric_conditions):
        return None

    def postFlightConditions(self, status, flight_conditions):
        return None

    def postGravityModel(self, status, gravity):
        return float("nan")

    def postMassCalculation(self, status, mass_data):
        return None

    def postSimpleThrustCalculation(self, status, thrust):
        return float("nan")

    def postWindModel(self, status, wind):
        return None

    def clone(self):
        return jpype.JProxy((
            jpype.JPackage("net").sf.openrocket.simulation.listeners.SimulationListener,
            jpype.JPackage("net").sf.openrocket.simulation.listeners.SimulationEventListener,
            jpype.JPackage("net").sf.openrocket.simulation.listeners.SimulationComputationListener,
            jpype.java.lang.Cloneable,),
            inst=copy(self))
