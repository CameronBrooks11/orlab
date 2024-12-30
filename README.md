# orlab

**orlab** is a Python module designed to simplify interaction and scripting with [OpenRocket](https://openrocket.info/) from Python. It leverages JPype to bridge Python and Java, enabling seamless control over OpenRocket's functionalities. Currently, it supports access to simulation capabilities given an `.ork` file, with the goal of future expansion to enable more sophisticated computational engineering workflows.

This project is an evolution of the original [orhelper](https://github.com/SilentSys/orhelper) library, which hasn't been maintained recently and is limited in scope. **orlab** updates the compatibility with OpenRocket 23.09, reorganizes the code for better structure, and plans to incorporate additional features.

## Table of Contents

- [orlab](#orlab)
  - [Table of Contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Setting Up the JDK](#setting-up-the-jdk)
    - [Linux](#linux)
    - [Windows](#windows)
  - [Usage](#usage)
  - [Development](#development)
  - [Credits](#credits)

## Prerequisites

Before installing **orlab**, ensure you have the following installed on your system:

- **OpenRocket** version **23.09**
  - [Download OpenRocket](https://github.com/openrocket/openrocket/releases/download/release-23.09/OpenRocket-23.09.jar)
- **Adoptium JDK 17 LTS** (or higher?)
  - [Download Adoptium JDK](https://adoptium.net/)
  - Other JDK releases (i.e. 22) have been tested and work, but not thoroughly.
- **Python** version **3.6** or higher

## Installation

1. **Clone the Repository**

   ```
   git clone https://github.com/CameronBrooks11/orlab.git
   cd orlab
   ```

2. **Install the Package**

   Install **orlab** using `pip`:

   ```
   pip install orlab
   ```

   _For development purposes, you can install in editable mode:_

   ```
   pip install -e .
   ```

3. **Download OpenRocket JAR**

   If you haven't already, download the OpenRocket `.jar` file:

   - **Direct Download:** [OpenRocket-23.09.jar](https://github.com/openrocket/openrocket/releases/download/release-23.09/OpenRocket-23.09.jar)

   - **Using `wget` on Linux:**

     ```
     wget https://github.com/openrocket/openrocket/releases/download/release-23.09/OpenRocket-23.09.jar
     ```

4. **Set the `CLASSPATH` Environment Variable**

   Ensure that the `CLASSPATH` includes the path to the OpenRocket `.jar` file. This step is only necessary if the `.jar` file is not located in the current directory.

   ```
   export CLASSPATH=/path/to/OpenRocket-23.09.jar
   ```

   _Replace `/path/to/` with the actual directory path where the `.jar` file is located._

## Setting Up the JDK

### Linux

1. **Install Adoptium JDK 17 LTS**

   Download and install the Adoptium JDK from the [official website](https://adoptium.net/). Check the option to set / override `JAVA_HOME`, unless you have a specific reason not to in which you will need to define `MANUAL_JVM_PATH` in your code.

2. **Set the `JAVA_HOME` Environment Variable**

   If JPype doesn't automatically detect the JDK, manually set the `JAVA_HOME` environment variable:

   - **Find Installation Directory:**

     Locate where Adoptium JDK is installed, e.g., `/usr/lib/jvm/adoptium-17`.

   - **Edit `~/.bashrc`:**

     Open the `.bashrc` file with your preferred text editor:

     ```
     nano ~/.bashrc
     ```

   - **Add the Following Line:**

     ```
     export JAVA_HOME="/usr/lib/jvm/adoptium-17"
     ```

   - **Apply Changes:**

     ```
     source ~/.bashrc
     ```

### Windows

1. **Install Adoptium JDK 17 LTS**

   Download and install the Adoptium JDK from the [official website](https://adoptium.net/).

2. **Set Environment Variables**

   - **Open Environment Variables Settings:**

     Navigate to `Control Panel` > `System` > `Advanced system settings` > `Environment Variables`.

   - **Add `JAVA_HOME`:**

     - Click on `New` under **System variables**.
     - Set **Variable name** to `JAVA_HOME`.
     - Set **Variable value** to the path where Adoptium JDK is installed, e.g., `C:\Program Files\Eclipse Adoptium\jdk-17`.

   - **Update `PATH`:**

     - Select the `Path` variable and click `Edit`.
     - Click `New` and add `%JAVA_HOME%\bin`.

   - **Apply and Close:**

     Click `OK` to apply the changes.

## Usage

After installation and setup, you can start using **orlab** to interact with OpenRocket. Refer to the `examples/` directory for sample scripts demonstrating various functionalities.

For more detailed information and advanced usage, consult the [OpenRocket Wiki on Scripting with Python and JPype](https://github.com/openrocket/openrocket/wiki/Scripting-with-Python-and-JPype).

## Development

If you wish to contribute or modify **orlab**, follow these steps:

1. **Clone the Repository**

   ```
   git clone https://github.com/yourusername/orlab.git
   cd orlab
   ```

2. **Install Dependencies in Editable Mode**

   ```
   pip install -e .
   ```

3. **Make Your Changes**

   Modify the codebase as needed. Ensure that your changes are well-documented and tested.

4. **Run Tests**

   _(Assuming tests are set up)_

   ```
   pytest
   ```

5. **Submit a Pull Request**

   Push your changes to a forked repository and submit a pull request for review.

## Credits

- The original [orhelper](https://github.com/SilentSys/orhelper) project by **SilentSys**
  - **Richard Graham** for the original script: [Source](https://sourceforge.net/p/openrocket/mailman/openrocket-devel/thread/4F17AA0C.1040002@rdg.cc/)
  - **@not7cd** for initial organization and cleanup: [Source](https://github.com/not7cd/orhelper)
- All contributors to the [OpenRocket](https://openrocket.info/) project over the years

---

_Feel free to contribute, report issues, or suggest enhancements!_
