import jpype
import jpype._jvmfinder as jvmfinder
import os

# Print JAVA_HOME and PATH for verification
print("JAVA_HOME:", os.environ.get('JAVA_HOME'))
print("PATH:", os.environ.get('PATH'))

# Print JPype's JVM search paths
finder = jvmfinder._JVMFinder()
try:
    print("Finder JVM path:", finder.get_jvm_path())
except Exception as e:
    print("Error finding JVM path:", e)

# Manually set the JVM path
jvm_path = r'C:\Program Files\Java\jdk-22\bin\server\jvm.dll'
print("Manual JVM path:", jvm_path)

# Attempt to start JVM with manual path
try:
    jpype.startJVM(jvm_path, "-ea")
    print("JVM started successfully")
except Exception as e:
    print("Error starting JVM:", e)
