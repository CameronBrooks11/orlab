import os
import jpype
import logging
from typing import Union
from .._enums import OrLogLevel
from ..utils.utils import _get_private_field

__all__ = ['OpenRocketInstance']

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLASSPATH = os.environ.get("CLASSPATH", "OpenRocket-23.09.jar")

class OpenRocketInstance:
    """ This class is designed to be called using the 'with' construct. This
        will ensure that no matter what happens within that context, the 
        JVM will always be shutdown.
    """

    # Optionally define the path to the JVM manually
    MANUAL_JVM_PATH = None  
    #MANUAL_JVM_PATH = r'C:\Program Files\Java\jdk-22\bin\server\jvm.dll'  
    #MANUAL_JVM_PATH = r'C:\Program Files\Eclipse Adoptium\jdk-21.0.5.11-hotspot\bin\server\jvm.dll'
    #MANUAL_JVM_PATH = r'C:\Program Files\Eclipse Adoptium\jdk-17.0.13.11-hotspot\bin\server\jvm.dll'

    def __init__(self, jar_path: str = CLASSPATH, log_level: Union[OrLogLevel, str] = OrLogLevel.ERROR):
        """ jar_path is the full path of the OpenRocket .jar file to use
            log_level can be either OFF, ERROR, WARN, INFO, DEBUG, TRACE and ALL
        """
        self.openrocket = None
        self.started = False

        if not os.path.exists(jar_path):
            raise FileNotFoundError(f"Jar file {os.path.abspath(jar_path)} does not exist")
        self.jar_path = jar_path

        if isinstance(log_level, str):
            self.or_log_level = OrLogLevel[log_level]
        else:
            self.or_log_level = log_level

    def __enter__(self):
        # Use MANUAL_JVM_PATH if set, otherwise get default JVM path
        jvm_path = self.MANUAL_JVM_PATH or jpype.getDefaultJVMPath()

        logger.info(f"Starting JVM from {jvm_path} CLASSPATH={self.jar_path}")

        jpype.startJVM(jvm_path, "-ea", f"-Djava.class.path={self.jar_path}")

        # ----- Java imports -----
        self.openrocket = jpype.JPackage("net").sf.openrocket
        guice = jpype.JPackage("com").google.inject.Guice
        LoggerFactory = jpype.JPackage("org").slf4j.LoggerFactory
        Logger = jpype.JPackage("ch").qos.logback.classic.Logger
        # -----

        # Effectively a minimally viable translation of openrocket.startup.SwingStartup
        gui_module = self.openrocket.startup.GuiModule()
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

    def _translate_log_level(self):
        # ----- Java imports -----
        Level = jpype.JPackage("ch").qos.logback.classic.Level
        # -----

        return getattr(Level, self.or_log_level.name)
