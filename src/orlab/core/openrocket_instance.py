import logging
import os
from typing import Any

import jpype

from .._enums import OrLogLevel
from ..profiles import get_profile
from ..utils.utils import _get_private_field
from .version import read_or_version

__all__ = ["OpenRocketInstance"]

# The core package root of the running OpenRocket, set when an instance starts.
# Module state is safe here: JPype allows exactly one JVM (and therefore one
# OpenRocket version) per process.
_active_core_root = None


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


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLASSPATH = os.environ.get("CLASSPATH", "OpenRocket-23.09.jar")


class OpenRocketInstance:
    """This class is designed to be called using the 'with' construct. This
    will ensure that no matter what happens within that context, the
    JVM will always be shutdown.
    """

    # Optionally define the path to the JVM manually
    MANUAL_JVM_PATH = None
    # MANUAL_JVM_PATH = r'C:\Program Files\Java\jdk-22\bin\server\jvm.dll'
    # MANUAL_JVM_PATH = r'C:\Program Files\Eclipse Adoptium\jdk-21.0.5.11-hotspot\bin\server\jvm.dll'
    # MANUAL_JVM_PATH = r'C:\Program Files\Eclipse Adoptium\jdk-17.0.13.11-hotspot\bin\server\jvm.dll'

    def __init__(self, jar_path: str = CLASSPATH, log_level: OrLogLevel | str = OrLogLevel.ERROR):
        """jar_path is the full path of the OpenRocket .jar file to use
        log_level can be either OFF, ERROR, WARN, INFO, DEBUG, TRACE and ALL
        """
        self.openrocket: Any = None  # JPackage core root once started
        self.started = False

        if not os.path.exists(jar_path):
            raise FileNotFoundError(f"Jar file {os.path.abspath(jar_path)} does not exist")
        self.jar_path = jar_path
        self.or_version = read_or_version(jar_path)
        self.profile, exact = get_profile(self.or_version)
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
        global _active_core_root

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

        # ----- Java imports -----
        # Package roots come from the version profile (OpenRocket 24.12 renamed
        # net.sf.openrocket to info.openrocket.core + info.openrocket.swing).
        self.openrocket = _jpackage(self.profile.core_root)
        self.openrocket_swing = _jpackage(self.profile.swing_root)
        _active_core_root = self.openrocket
        LoggerFactory = jpype.JPackage("org").slf4j.LoggerFactory
        Logger = jpype.JPackage("ch").qos.logback.classic.Logger
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

        or_logger = LoggerFactory.getLogger(Logger.ROOT_LOGGER_NAME)
        or_logger.setLevel(self._translate_log_level())

        self._warn_on_profile_drift()

        self.started = True

        return self

    def __exit__(self, ex, value, tb):

        # Dispose any open windows (usually just a loading screen) which can prevent the JVM from shutting down
        for window in jpype.java.awt.Window.getWindows():
            window.dispose()

        jpype.shutdownJVM()
        logger.info("JVM shut down")
        self.started = False

        if ex is not None:
            logger.exception("Exception while calling OpenRocket", exc_info=(ex, value, tb))

    def _warn_on_profile_drift(self):
        """Compares the live jar's constants against the profile (drift alarm)."""
        fdt_cls = self.openrocket.simulation.FlightDataType
        live_types = {
            str(f.getName())
            for f in fdt_cls.class_.getDeclaredFields()
            if f.getType() == fdt_cls.class_
        }
        live_events = {str(v.name()) for v in self.openrocket.simulation.FlightEvent.Type.values()}
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
