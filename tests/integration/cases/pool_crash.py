"""Worker-crash semantics with a real JVM: successes collected before the
crash are preserved in StudyAborted.partial, and the pool is dead after.

Usage: python pool_crash.py <jar_path>
"""

import json
import os
import sys
from pathlib import Path

import orlab
from orlab.errors import OrlabError, StudyAborted

ORK = Path(__file__).parents[3] / "examples" / "simple_ork" / "simple.ork"


def crash_or_run(helper, sim, task):
    if task.get("crash"):
        os._exit(21)  # a JVM segfault/OOM kill looks exactly like this
    helper.run_simulation(sim, randomize_seed=False)
    return {"apogee": helper.get_summary(sim).apogee}


def main(jar_path):
    pool = orlab.SimulationPool(str(ORK), jar_path, max_workers=1, jvm_args=("-Xmx512m",))
    outcome = {}
    try:
        pool.run([{}, {}, {"crash": True}, {}], worker_fn=crash_or_run)
        outcome["aborted"] = False
    except StudyAborted as e:
        outcome["aborted"] = True
        outcome["reason"] = e.reason
        outcome["partial_ok"] = len(e.partial.results)
        outcome["hint"] = "-Xmx" in str(e)
    try:
        pool.run(1)
        outcome["dead_after"] = False
    except OrlabError:
        outcome["dead_after"] = True
    print("RESULT " + json.dumps(outcome))


if __name__ == "__main__":
    main(sys.argv[1])
