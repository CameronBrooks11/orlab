# API reference

The public surface is the seven names importable from `orlab`, plus the
exception types in `orlab.errors`. Everything else is internal.

## OpenRocketInstance

::: orlab.OpenRocketInstance

## Helper

::: orlab.Helper

## AbstractSimulationListener

::: orlab.AbstractSimulationListener

## JIterator

::: orlab.JIterator

## Enums

::: orlab.FlightDataType
    options:
      members: false

::: orlab.FlightEvent
    options:
      members: false

::: orlab.OrLogLevel
    options:
      members: false

`FlightDataType` and `FlightEvent` are generated as the union of constants
across all supported OpenRocket versions; availability on the loaded version
is enforced at translation time with `UnsupportedFlightDataType`.

## Errors

::: orlab.errors
