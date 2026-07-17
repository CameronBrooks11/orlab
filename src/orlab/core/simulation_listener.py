from copy import copy

import jpype

from .openrocket_instance import active_core_root

__all__ = ["AbstractSimulationListener"]


class AbstractSimulationListener:
    """Python implementation of OpenRocket's AbstractSimulationListener.
    Subclass it, override the hooks you need, and pass instances to
    ``Helper.run_simulation(sim, listeners=[...])``.

    OpenRocket clones listeners before the run, so collect results through
    shared mutable state (e.g. a list the caller keeps a reference to), not
    by assigning to ``self`` and reading it back afterwards. Exceptions
    raised inside a hook propagate out of ``run_simulation`` intact.

    Hook groups: SimulationListener (``startSimulation``, ``postStep``, …),
    SimulationEventListener (``handleFlightEvent``, …), and
    SimulationComputationListener (``preWindModel``,
    ``postAerodynamicCalculation``, …). Boolean-returning hooks continue the
    simulation/event on True; pre-computation hooks return an override value
    or None/NaN to leave OpenRocket's computation untouched.
    """

    def __str__(self):
        return "'" + "Python simulation listener proxy : " + str(self.__class__.__name__) + "'"

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
        openrocket = active_core_root()
        return jpype.JProxy(
            (
                openrocket.simulation.listeners.SimulationListener,
                openrocket.simulation.listeners.SimulationEventListener,
                openrocket.simulation.listeners.SimulationComputationListener,
                jpype.java.lang.Cloneable,
            ),
            inst=copy(self),
        )
