import logging
import math
from collections.abc import Iterable

import jpype
import numpy as np

from .._enums import FlightDataType, FlightEvent
from ..errors import OrlabError, UnsupportedFlightDataType
from ..profiles import versions_with
from .jiterator import JIterator
from .openrocket_instance import OpenRocketInstance
from .simulation_listener import AbstractSimulationListener
from .summary import FlightSummary, _bearing_deg, _mean_descent_rate, _value_at, _window_stats

__all__ = ["Helper"]

logger = logging.getLogger(__name__)

# names already warned about in this process: version-absence warnings fire
# once, not once per summary, so dispersion loops stay readable
_absence_warned: set[str] = set()


def _warn_absent_once(what: str, version: str) -> None:
    if what not in _absence_warned:
        _absence_warned.add(what)
        logger.warning(
            "%s is not available in OpenRocket %s; the corresponding summary field(s) will be NaN",
            what,
            version,
        )


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

    def get_events(self, simulation, branch_number: int = 0) -> dict[FlightEvent, list[float]]:
        """Returns a dictionary of all the flight events in a given simulation.
        Key is FlightEvent and value is a list of all the times at which the event occurs.
        Event types not known to this orlab version are skipped with a warning.

        :param branch_number: Stage branch to read (0 = sustainer).
        """
        branch = simulation.getSimulatedData().getBranch(branch_number)

        output: dict[FlightEvent, list[float]] = {}
        unknown: set[str] = set()
        for name, times in self._events_by_name(branch).items():
            try:
                event = FlightEvent[name]
            except KeyError:
                if name not in unknown:
                    unknown.add(name)
                    logger.warning("Skipping unknown flight event type %s", name)
                continue
            output[event] = times

        return output

    @staticmethod
    def _events_by_name(branch) -> dict[str, list[float]]:
        """One traversal of a branch's events, keyed by stable string names —
        shared by get_events (enum-gated view) and get_summary (which must
        see every event regardless of orlab's enum vintage)."""
        output: dict[str, list[float]] = {}
        for ev in branch.getEvents():
            output.setdefault(str(ev.getType().name()), []).append(float(ev.getTime()))
        return output

    def get_summary(self, simulation, branch_number: int = 0) -> FlightSummary:
        """Returns the scalar flight report for one branch as a
        :class:`~orlab.FlightSummary` — plain-Python values only, safe to
        pickle into JVM-less processes.

        Branch 0 uses OpenRocket's own FlightData summary getters verbatim;
        other branches derive the same numbers from their own time series.
        Missing/inapplicable values are NaN (see the field docs). Degenerate
        flights degrade to NaN; an unsimulated simulation raises OrlabError.

        :param branch_number: Stage branch to summarize (0 = sustainer).
        """
        branch_number = int(branch_number)  # builtin-types contract incl. numpy ints
        flight_data = simulation.getSimulatedData()
        if flight_data is None or int(flight_data.getBranchCount()) == 0:
            raise OrlabError("Simulation has no flight data; call run_simulation first")
        branch_count = int(flight_data.getBranchCount())
        if not 0 <= branch_number < branch_count:
            raise IndexError(f"branch {branch_number} out of range (simulation has {branch_count})")
        branch = flight_data.getBranch(branch_number)
        version = self._instance.or_version

        times = self._branch_series(branch, "TYPE_TIME")
        altitude = self._branch_series(branch, "TYPE_ALTITUDE")
        stability = self._branch_series(branch, "TYPE_STABILITY")
        velocity_z = self._branch_series(branch, "TYPE_VELOCITY_Z")
        velocity_total = self._branch_series(branch, "TYPE_VELOCITY_TOTAL")
        events = self._events_by_name(branch)

        def at_event(name: str, series: np.ndarray, which: int = 0) -> float:
            if name not in events:
                return math.nan
            return _value_at(times, series, events[name][which])

        # stability window: launch rod departure -> apogee. Boosters have no
        # LAUNCHROD (window starts at their first sample, off-rod values NaN);
        # a flight without an APOGEE event windows to its highest sample.
        t_rod = events["LAUNCHROD"][0] if "LAUNCHROD" in events else None
        if "APOGEE" in events:
            t_apogee = events["APOGEE"][0]
        elif len(altitude) and not np.isnan(altitude).all():
            t_apogee = float(times[int(np.nanargmax(altitude))])
        else:
            t_apogee = None
        window_start = t_rod if t_rod is not None else (float(times[0]) if len(times) else None)
        if window_start is not None and t_apogee is not None:
            min_stab, max_stab = _window_stats(times, stability, window_start, t_apogee)
        else:
            min_stab, max_stab = math.nan, math.nan

        t_deploy = (
            events["RECOVERY_DEVICE_DEPLOYMENT"][-1]
            if "RECOVERY_DEVICE_DEPLOYMENT" in events
            else None
        )
        t_ground = (
            events["GROUND_HIT"][0]
            if "GROUND_HIT" in events
            else (float(times[-1]) if len(times) else None)
        )
        if t_deploy is not None and t_ground is not None:
            descent_rate = _mean_descent_rate(times, velocity_z, t_deploy, t_ground)
        else:
            descent_rate = math.nan

        if branch_number == 0:

            def scalar(getter: str) -> float:
                fn = getattr(flight_data, getter, None)
                if fn is None:
                    _warn_absent_once(f"FlightData.{getter}", version)
                    return math.nan
                return float(fn())

            apogee = scalar("getMaxAltitude")
            time_to_apogee = scalar("getTimeToApogee")
            max_velocity = scalar("getMaxVelocity")
            max_acceleration = scalar("getMaxAcceleration")
            max_mach = scalar("getMaxMachNumber")
            velocity_off_rod = scalar("getLaunchRodVelocity")
            velocity_at_deployment = scalar("getDeploymentVelocity")
            ground_hit_velocity = scalar("getGroundHitVelocity")
            flight_time = scalar("getFlightTime")
            optimum_delay = scalar("getOptimumDelay")
        else:
            acceleration = self._branch_series(branch, "TYPE_ACCELERATION_TOTAL")
            mach = self._branch_series(branch, "TYPE_MACH_NUMBER")

            def series_max(series: np.ndarray) -> float:
                if len(series) == 0 or np.isnan(series).all():
                    return math.nan
                return float(np.nanmax(series))

            apogee = series_max(altitude)
            time_to_apogee = t_apogee if t_apogee is not None else math.nan
            max_velocity = series_max(velocity_total)
            max_acceleration = series_max(acceleration)
            max_mach = series_max(mach)
            velocity_off_rod = at_event("LAUNCHROD", velocity_total)
            velocity_at_deployment = at_event("RECOVERY_DEVICE_DEPLOYMENT", velocity_total, -1)
            ground_hit_velocity = at_event("GROUND_HIT", velocity_total)
            flight_time = float(times[-1]) if len(times) else math.nan
            # policy: reported for the sustainer only, where FlightData's own
            # figure is authoritative
            optimum_delay = math.nan

        pos_x = self._branch_series(branch, "TYPE_POSITION_X")
        pos_y = self._branch_series(branch, "TYPE_POSITION_Y")
        landing_x = float(pos_x[-1]) if len(pos_x) else math.nan
        landing_y = float(pos_y[-1]) if len(pos_y) else math.nan
        landing_distance = math.hypot(landing_x, landing_y)

        if hasattr(branch, "getName"):
            branch_name = str(branch.getName())
        elif hasattr(branch, "getBranchName"):
            branch_name = str(branch.getBranchName())
        else:
            branch_name = ""

        # bounded at apogee: the NaN-skip must not report a post-apogee
        # (tumble-regime) sample as the off-rod margin
        off_rod_stability = math.nan
        if t_rod is not None:
            off_rod_stability = _value_at(
                times, stability, t_rod, t_max=t_apogee if t_apogee is not None else math.inf
            )

        return FlightSummary(
            velocity_off_rod=velocity_off_rod,
            stability_off_rod_cal=off_rod_stability,
            apogee=apogee,
            time_to_apogee=time_to_apogee,
            max_velocity=max_velocity,
            max_acceleration=max_acceleration,
            max_mach=max_mach,
            min_stability_cal=min_stab,
            max_stability_cal=max_stab,
            velocity_at_deployment=velocity_at_deployment,
            descent_rate=descent_rate,
            ground_hit_velocity=ground_hit_velocity,
            landing_x=landing_x,
            landing_y=landing_y,
            landing_distance=landing_distance,
            landing_bearing_deg=_bearing_deg(landing_x, landing_y),
            flight_time=flight_time,
            optimum_delay=optimum_delay,
            branch_number=branch_number,
            branch_name=branch_name,
            branch_count=branch_count,
            warnings=tuple(str(w) for w in flight_data.getWarningSet()),
        )

    def _tabular_columns(self, branch, variables):
        """Resolves (label, java_type) columns for tabular export. Default:
        every profile data type populated on the branch, TYPE_TIME first,
        the rest in name order."""
        if variables is None:
            names = sorted(self._instance.profile.flight_data_types)
            if "TYPE_TIME" in names:
                names.remove("TYPE_TIME")
                names.insert(0, "TYPE_TIME")
            candidates = [(n, self.translate_flight_data_type(n)) for n in names]
            return [
                (self._column_label(jt, name), jt)
                for name, jt in candidates
                if branch.get(jt) is not None
            ]
        columns = []
        for v in variables:
            java_type = self.translate_flight_data_type(v)
            name = v.name if isinstance(v, FlightDataType) else str(v)
            columns.append((self._column_label(java_type, name), java_type))
        return columns

    @staticmethod
    def _column_label(java_type, name: str) -> str:
        """ "NAME (unit)" from the jar's own SI unit string; units that are
        only whitespace/zero-width-space (OpenRocket's dimensionless marker)
        get no suffix."""
        unit = str(java_type.getUnitGroup().getSIUnit().getUnit())
        if not unit.replace("\u200b", "").strip():
            return name
        return f"{name} ({unit})"

    def get_dataframe(self, simulation, variables=None, branch_number: int = 0):
        """The branch's timeseries as a pandas DataFrame, one column per
        variable, labeled ``NAME (SI unit)``. Requires the ``orlab[pandas]``
        extra; everything else in orlab works without pandas.

        :param variables: FlightDataTypes or constant names; default: every
            profile data type populated on the branch.
        :param branch_number: Stage branch to read (0 = sustainer).
        """
        try:
            import pandas  # type: ignore[import-untyped]  # optional extra, no stubs
        except ImportError as e:
            raise ImportError(
                "pandas is required for get_dataframe — pip install orlab[pandas]"
            ) from e
        branch = simulation.getSimulatedData().getBranch(branch_number)
        columns = self._tabular_columns(branch, variables)
        return pandas.DataFrame(
            {label: np.asarray(branch.get(java_type), dtype=float) for label, java_type in columns}
        )

    def export_csv(self, simulation, path, variables=None, branch_number: int = 0) -> None:
        """Writes the branch's timeseries as UTF-8 CSV with ``NAME (SI
        unit)`` headers — stdlib only, no pandas needed. NaN samples become
        empty cells (``pandas.read_csv`` reads them back as NaN).

        :param variables: FlightDataTypes or constant names; default: every
            profile data type populated on the branch.
        :param branch_number: Stage branch to read (0 = sustainer).
        """
        import csv

        branch = simulation.getSimulatedData().getBranch(branch_number)
        columns = self._tabular_columns(branch, variables)
        series = [np.asarray(branch.get(java_type), dtype=float) for _, java_type in columns]
        # newline='' and explicit utf-8: text-mode newline translation would
        # write \r\r\n on Windows, and locale encodings choke on m/s²
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow([label for label, _ in columns])
            for row in zip(*series, strict=True):
                writer.writerow(["" if math.isnan(value) else repr(float(value)) for value in row])

    def _branch_series(self, branch, type_name: str) -> np.ndarray:
        """A branch's series for a FlightDataType constant name as a float
        array; empty when the loaded version lacks the type (warned once per
        process) or the branch holds no such series."""
        try:
            java_type = self.translate_flight_data_type(type_name)
        except UnsupportedFlightDataType:
            _warn_absent_once(type_name, self._instance.or_version)
            return np.array([])
        values = branch.get(java_type)
        if values is None:
            return np.array([])
        return np.asarray(values, dtype=float)

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
