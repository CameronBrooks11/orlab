"""get_components_of_type on the bundled rocket: concrete classes and the
MotorMount interface, plus the unknown-name error.

Usage: python typed_find.py <jar_path>
"""

import json
import sys
from pathlib import Path

import orlab

ORK = Path(__file__).parents[3] / "examples" / "simple_ork" / "simple.ork"


def main(jar_path):
    with orlab.OpenRocketInstance(jar_path=jar_path) as instance:
        orl = orlab.Helper(instance)
        doc = orl.load_doc(str(ORK))
        rocket = doc.getSimulation(0).getRocket()

        out = {"version": instance.or_version}
        for type_name in ("BodyTube", "NoseCone", "TrapezoidFinSet", "MotorMount"):
            found = orl.get_components_of_type(rocket, type_name)
            out[type_name] = sorted(str(c.getName()) for c in found)
        try:
            orl.get_components_of_type(rocket, "NoSuchComponent")
            out["unknown_error"] = None
        except ValueError as e:
            out["unknown_error"] = str(e)[:60]
        print("RESULT " + json.dumps(out))


if __name__ == "__main__":
    main(sys.argv[1])
