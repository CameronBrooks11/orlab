"""find_motor as the very first operation in a fresh process: the motor
database must be completely loaded on every version and startup path
(the 24.12 core path's providers block until loaded — decided pre-merge,
asserted here so a regression is loud, not a flaky mystery).

Usage: python cold_start_motor_db.py <jar_path>
"""

import json
import sys
import time

import orlab


def main(jar_path):
    with orlab.OpenRocketInstance(jar_path=jar_path) as instance:
        orl = orlab.Helper(instance)
        t0 = time.time()
        motor = orl.find_motor("C6", manufacturer="Estes")
        elapsed = time.time() - t0
        database = orl.openrocket.startup.Application.getMotorSetDatabase()
        print(
            "RESULT "
            + json.dumps(
                {
                    "version": instance.or_version,
                    "designation": str(motor.getDesignation()),
                    "sets": len(list(database.getMotorSets())),
                    "first_lookup_s": round(elapsed, 2),
                }
            )
        )


if __name__ == "__main__":
    main(sys.argv[1])
