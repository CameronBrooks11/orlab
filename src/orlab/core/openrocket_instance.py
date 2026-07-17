import logging
import os
import zipfile
from typing import Any

import jpype

from .._enums import OrLogLevel
from ..errors import NotAnOpenRocketJar, OrlabError
from ..profiles import get_profile
from ..utils.utils import _get_private_field
from .version import read_or_version

__all__ = ["OpenRocketInstance"]

# State of the running OpenRocket, set when an instance starts. Module state
# is safe here: JPype allows exactly one JVM (and therefore one OpenRocket
# version) per process. The JVM outlives instances (JPype cannot restart one);
# it ends with the interpreter.
_active_core_root = None
_active_jar_path: str | None = None  # abspath of the jar the running JVM loaded


def active_core_root():
    """Returns the JPackage core root of the started OpenRocket instance."""
    if _active_core_root is None:
        raise RuntimeError("No OpenRocketInstance has been started in this process")
    return _active_core_root


def _jpackage(dotted: str):
    """Resolves a dotted package name to a jpype JPackage object."""
    parts = dotted.split(".")
    pkg = jpype.JPackage(parts[0])
    for part in parts[1:]:
        pkg = getattr(pkg, part)
    return pkg


def reflect_live_constants(core_pkg) -> tuple[set, set]:
    """Reflects the FlightDataType and FlightEvent constant names from the
    running OpenRocket. Shared by the drift alarm and the profile generator so
    both always apply the same filter.
    """
    fdt_cls = core_pkg.simulation.FlightDataType
    types = {
        str(f.getName())
        for f in fdt_cls.class_.getDeclaredFields()
        if f.getType() == fdt_cls.class_
    }
    events = {str(v.name()) for v in core_pkg.simulation.FlightEvent.Type.values()}
    return types, events


logger = logging.getLogger(__name__)


def _default_jar_path() -> str:
    """Resolved at instantiation time (not import time): ORLAB_JAR, then the
    first existing jar on the legacy CLASSPATH (which may hold a separator-
    joined list), then a cwd-relative fallback."""
    jar = os.environ.get("ORLAB_JAR")
    if jar:
        return jar
    for entry in os.environ.get("CLASSPATH", "").split(os.pathsep):
        if entry.endswith(".jar") and os.path.exists(entry):
            return entry
    return "OpenRocket-23.09.jar"


class OpenRocketInstance:
    """Use with the 'with' construct: entering starts the JVM and OpenRocket
    on first use. The JVM cannot be restarted in a process (JPype), so it
    stays up after the block and ends with the interpreter — a later
    ``with OpenRocketInstance(...)`` on the same jar reuses it (sequential
    blocks and notebook re-runs work); a different jar raises OrlabError.
    """

    # Optionally define the path to the JVM manually
    MANUAL_JVM_PATH = None
    # MANUAL_JVM_PATH = r'C:\Program Files\Java\jdk-22\bin\server\jvm.dll'
    # MANUAL_JVM_PATH = r'C:\Program Files\Eclipse Adoptium\jdk-21.0.5.11-hotspot\bin\server\jvm.dll'
    # MANUAL_JVM_PATH = r'C:\Program Files\Eclipse Adoptium\jdk-17.0.13.11-hotspot\bin\server\jvm.dll'

    def __init__(self, jar_path: str | None = None, log_level: OrLogLevel | str = OrLogLevel.ERROR):
        """jar_path is the full path of the OpenRocket .jar file to use;
        defaults to $ORLAB_JAR, then $CLASSPATH, then ./OpenRocket-23.09.jar.
        log_level can be either OFF, ERROR, WARN, INFO, DEBUG, TRACE and ALL
        """
        self.openrocket: Any = None  # JPackage core root once started
        self.started = False

        jar_path = jar_path or _default_jar_path()
        if not os.path.exists(jar_path):
            raise FileNotFoundError(
                f"Jar file {os.path.abspath(jar_path)} does not exist "
                "(pass jar_path or set ORLAB_JAR)"
            )
        self.jar_path = jar_path
        try:
            self.or_version = read_or_version(jar_path)
            # UnsupportedOpenRocketVersion (too-old jar) passes through untouched
            self.profile, exact = get_profile(self.or_version)
        except (zipfile.BadZipFile, KeyError, ValueError) as e:
            # covers a corrupt zip, missing build.properties/build.version,
            # and an unparseable version string
            raise NotAnOpenRocketJar(
                f"{os.path.abspath(jar_path)} is not an OpenRocket jar ({e})"
            ) from e
        if not exact:
            logger.warning(
                "No profile for OpenRocket %s; falling back to the nearest older "
                "profile (%s). Newer constants may be missing from orlab's enums.",
                self.or_version,
                self.profile.version_string,
            )

        if isinstance(log_level, str):
            self.or_log_level = OrLogLevel[log_level]
        else:
            self.or_log_level = log_level

    def __enter__(self):
        global _active_core_root, _active_jar_path

        if jpype.isJVMStarted():
            requested = os.path.abspath(self.jar_path)
            if _active_jar_path is None:
                raise OrlabError(
                    "This process's JVM is running but OpenRocket startup never "
                    "completed (an earlier attempt failed). JPype cannot restart "
                    "a JVM — fix the cause and retry in a new process."
                )
            if requested != _active_jar_path:
                raise OrlabError(
                    f"A JVM is already running with {_active_jar_path}, and JPype "
                    "cannot restart a JVM — one process can use only one OpenRocket "
                    f"jar. Use a new process for {requested}."
                )
            # Same jar: reuse the running OpenRocket.
            self.openrocket = _active_core_root
            self.openrocket_swing = _jpackage(self.profile.swing_root)
            self._set_or_log_level()
            self.started = True
            return self

        # Use MANUAL_JVM_PATH if set, otherwise get default JVM path
        jvm_path = self.MANUAL_JVM_PATH or jpype.getDefaultJVMPath()

        logger.info(
            f"Starting JVM from {jvm_path} CLASSPATH={self.jar_path} (OpenRocket {self.or_version})"
        )

        # --add-opens: OpenRocket <= 15.03 bundles a Guice that reflects into
        # java.lang, which the module system blocks on modern JVMs. Harmless
        # on newer OpenRocket versions.
        jvm_args = [
            "-ea",
            "--add-opens=java.base/java.lang=ALL-UNNAMED",
            f"-Djava.class.path={self.jar_path}",
        ]
        if self.profile.startup == "core":
            jvm_args.append("-Djava.awt.headless=true")
        jpype.startJVM(jvm_path, *jvm_args)

        try:
            self._start_openrocket()
        except Exception as e:
            raise OrlabError(
                "OpenRocket startup failed after the JVM launched; the JVM cannot "
                "be restarted, so retry in a new process once the cause is fixed."
            ) from e

        _active_jar_path = os.path.abspath(self.jar_path)
        self._warn_on_profile_drift()
        self.started = True

        return self

    def _start_openrocket(self):
        """Bootstraps OpenRocket inside the (fresh) JVM."""
        global _active_core_root

        # ----- Java imports -----
        # Package roots come from the version profile (OpenRocket 24.12 renamed
        # net.sf.openrocket to info.openrocket.core + info.openrocket.swing).
        self.openrocket = _jpackage(self.profile.core_root)
        self.openrocket_swing = _jpackage(self.profile.swing_root)
        _active_core_root = self.openrocket
        # -----

        if self.profile.startup == "core":
            # Official headless bootstrap (24.12+). PluginModule must be passed
            # explicitly: the Java no-arg initialize() adds it internally, but
            # JPype dispatches a zero-arg call to the varargs overload with an
            # empty module array, and startup then fails on unbound plugins.
            self.openrocket.startup.OpenRocketCore.initialize(self.openrocket.plugin.PluginModule())
        else:
            # Minimally viable translation of openrocket.startup.SwingStartup
            guice = jpype.JPackage("com").google.inject.Guice
            gui_module = self.openrocket_swing.startup.GuiModule()
            plugin_module = self.openrocket.plugin.PluginModule()

            injector = guice.createInjector(gui_module, plugin_module)

            app = self.openrocket.startup.Application
            app.setInjector(injector)

            gui_module.startLoader()

            # Ensure that loaders are done loading before continuing
            # Without this there seems to be a race condition bug that leads to the whole thing freezing
            preset_loader = _get_private_field(gui_module, "presetLoader")
            preset_loader.blockUntilLoaded()
            motor_loader = _get_private_field(gui_module, "motorLoader")
            motor_loader.blockUntilLoaded()

        self._set_or_log_level()

    def _set_or_log_level(self):
        LoggerFactory = jpype.JPackage("org").slf4j.LoggerFactory
        Logger = jpype.JPackage("ch").qos.logback.classic.Logger
        or_logger = LoggerFactory.getLogger(Logger.ROOT_LOGGER_NAME)
        or_logger.setLevel(self._translate_log_level())

    def __exit__(self, ex, value, tb):
        # Dispose any open windows (usually just a loading screen); the JVM
        # itself stays up — JPype cannot restart one, so shutting it down here
        # would break every later OpenRocketInstance in this process. It ends
        # with the interpreter. Existing Helpers and listeners stay usable.
        if jpype.isJVMStarted():
            for window in jpype.java.awt.Window.getWindows():
                window.dispose()

        self.started = False
        logger.info("OpenRocketInstance closed (JVM stays up for reuse)")

    def _warn_on_profile_drift(self):
        """Compares the live jar's constants against the profile (drift alarm).
        Pure diagnostics: must never abort startup, whatever the jar looks like.
        """
        try:
            live_types, live_events = reflect_live_constants(self.openrocket)
        except Exception as e:
            logger.warning("Profile drift check failed on OpenRocket %s: %s", self.or_version, e)
            return
        for kind, live, known in (
            ("FlightDataType", live_types, self.profile.flight_data_types),
            ("FlightEvent", live_events, self.profile.flight_events),
        ):
            extra = live - known
            if extra:
                logger.warning(
                    "OpenRocket %s exposes %s constants not in the %s profile: %s "
                    "(regenerate with tools/generate_profile.py)",
                    self.or_version,
                    kind,
                    self.profile.version_string,
                    ", ".join(sorted(extra)),
                )
            gone = known - live
            if gone:
                logger.warning(
                    "Profile %s lists %s constants the loaded jar lacks: %s",
                    self.profile.version_string,
                    kind,
                    ", ".join(sorted(gone)),
                )

    def _translate_log_level(self):
        # ----- Java imports -----
        Level = jpype.JPackage("ch").qos.logback.classic.Level
        # -----

        return getattr(Level, self.or_log_level.name)
