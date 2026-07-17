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


TWO_STAGE_2412 = "datafiles/examples/Two stage high power rocket.ork"


def _run_example(orl, jar_path, member):
    with zipfile.ZipFile(jar_path) as jar, jar.open(member) as fh:
        tmp = Path(tempfile.mkdtemp()) / "example.ork"
        tmp.write_bytes(fh.read())
    doc = orl.load_doc(str(tmp))
    sim = doc.getSimulation(0)
    opts = sim.getOptions()
    opts.setWindSpeedAverage(0.0)
    opts.setWindTurbulenceIntensity(0.0)
    opts.setRandomSeed(42)
    orl.run_simulation(sim, randomize_seed=False)
    first = orl.get_summary(sim)
    return [orl.get_summary(sim, branch_number=b) for b in range(first.branch_count)]


def main(jar_path):
    with orlab.OpenRocketInstance(jar_path=jar_path) as instance:
        member = EXAMPLES[instance.or_version]
        orl = orlab.Helper(instance)
        summaries = _run_example(orl, jar_path, member)

        # 24.12's two-stage example has a recovery device on the booster —
        # the only bundled coverage of finite descent fields on a derived
        # (branch > 0) summary
        two_stage = (
            [s.to_dict() for s in _run_example(orl, jar_path, TWO_STAGE_2412)]
            if instance.or_version == "24.12"
            else None
        )

        print(
            "RESULT "
            + json.dumps(
                {
                    "version": instance.or_version,
                    "member": member,
                    "branches": [s.to_dict() for s in summaries],
                    "warning_types": [type(w).__name__ for s in summaries for w in s.warnings],
                    "two_stage": two_stage,
                }
            )
        )


if __name__ == "__main__":
    main(sys.argv[1])
