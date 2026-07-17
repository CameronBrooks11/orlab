# API reference

The public surface is the ten names importable from `orlab`, plus the
exception types in `orlab.errors`, the jar utilities in `orlab.jars`, the
parallel-running machinery in `orlab.parallel`, and the dispersion
listeners in `orlab.listeners`. Everything else is internal.

## OpenRocketInstance

::: orlab.OpenRocketInstance

## Helper

::: orlab.Helper

## AbstractSimulationListener

::: orlab.AbstractSimulationListener

## JIterator

::: orlab.JIterator

## FlightSummary

::: orlab.FlightSummary

## Jar management

::: orlab.jars.fetch_jar

::: orlab.jars.jar_cache_dir

## Enums

::: orlab.FlightDataType
    options:
      members: false
      show_root_heading: true
      heading_level: 3

::: orlab.FlightEvent
    options:
      members: false
      show_root_heading: true
      heading_level: 3

::: orlab.OrLogLevel
    options:
      members: false
      show_root_heading: true
      heading_level: 3

`FlightDataType` and `FlightEvent` are generated as the union of constants
across all supported OpenRocket versions; availability on the loaded version
is enforced at translation time with `UnsupportedFlightDataType`.

## Parallel running and declarative options

::: orlab.parallel

## Dispersion listeners

::: orlab.listeners

## Errors

::: orlab.errors
