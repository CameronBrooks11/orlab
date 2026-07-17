"""get_summary across every branch of the jar's own bundled multi-stage
example. The member name is pinned per version — a pinned jar missing its
pinned example is a failure, not a skip.

Usage: python summary_multistage.py <jar_path>
"""

import json
import sys
import tempfile
import zipfile
from pathlib import Path

import orlab

EXAMPLES = {
    "15.03": "datafiles/examples/Three-stage rocket.ork",
    "22.02": "datafiles/examples/Three-stage rocket.ork",
    "23.09": "datafiles/examples/Three-stage rocket.ork",
    "24.12": "datafiles/examples/Three stage low power rocket.ork",
}


def main(jar_path):
    with orlab.OpenRocketInstance(jar_path=jar_path) as instance:
        member = EXAMPLES[instance.or_version]
        with zipfile.ZipFile(jar_path) as jar, jar.open(member) as fh:
            tmp = Path(tempfile.mkdtemp()) / "example.ork"
            tmp.write_bytes(fh.read())

        orl = orlab.Helper(instance)
        doc = orl.load_doc(str(tmp))
        sim = doc.getSimulation(0)
        opts = sim.getOptions()
        opts.setWindSpeedAverage(0.0)
        opts.setWindTurbulenceIntensity(0.0)
        opts.setRandomSeed(42)
        orl.run_simulation(sim, randomize_seed=False)

        summaries = []
        first = orl.get_summary(sim)
        for branch in range(first.branch_count):
            summaries.append(orl.get_summary(sim, branch_number=branch))

        print(
            "RESULT "
            + json.dumps(
                {
                    "version": instance.or_version,
                    "member": member,
                    "branches": [s.to_dict() for s in summaries],
                    "warning_types": [type(w).__name__ for s in summaries for w in s.warnings],
                }
            )
        )


if __name__ == "__main__":
    main(sys.argv[1])
