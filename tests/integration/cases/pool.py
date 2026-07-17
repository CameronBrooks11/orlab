"""SimulationPool against real JVM workers: declarative tasks, worker_fn
variants (Python error, listener, Java exception), seed semantics, warm
reuse.

Usage: python pool.py <jar_path>   (runs with 2 workers, -Xmx512m)
"""

import json
import os
import sys
from pathlib import Path

import jpype

import orlab

ORK = Path(__file__).parents[3] / "examples" / "simple_ork" / "simple.ork"


class Counter(orlab.AbstractSimulationListener):
    def __init__(self, calls):
        self.calls = calls

    def postStep(self, status):
        self.calls.append(1)


def listener_fn(helper, sim, task):
    calls = []
    helper.run_simulation(sim, listeners=[Counter(calls)], randomize_seed=False)
    return {"steps": len(calls), "pid": os.getpid()}


def java_error_fn(helper, sim, task):
    jpype.java.lang.Integer.parseInt("not a number")


def value_error_fn(helper, sim, task):
    raise ValueError("python-side failure")


def reseeding_fn(helper, sim, task):
    # forgets randomize_seed=False: the recorded seed must be the readback
    helper.run_simulation(sim)
    return {"apogee": helper.get_summary(sim).apogee}


def main(jar_path):
    pool = orlab.SimulationPool(str(ORK), jar_path, max_workers=2, jvm_args=("-Xmx512m",))
    declarative = pool.run(
        [{"wind_speed_average": float(w), "launch_rod_angle": 0.1} for w in range(8)],
        seed=42,
    )
    listener_study = pool.run([{}, {}], worker_fn=listener_fn)
    errors = pool.run([{}, {}], worker_fn=java_error_fn)
    perrors = pool.run([{}], worker_fn=value_error_fn)
    reseeded = pool.run([{"seed": 1234}], worker_fn=reseeding_fn)
    warm = pool.run(3, seed=7)
    pool.shutdown()

    print(
        "RESULT "
        + json.dumps(
            {
                "version": (lambda: __import__("orlab").core.version.read_or_version(jar_path))(),
                "apogees": [r.payload["apogee"] for r in declarative.results],
                "declarative_ok": len(declarative.results),
                "seeds_distinct": len({r.seed for r in declarative.results}),
                "worker_pids": sorted({r.payload["pid"] for r in listener_study.results}),
                "listener_steps": [r.payload["steps"] for r in listener_study.results],
                "java_error_type": errors.errors[0].error_type if errors.errors else None,
                "java_error_tb_has_stack": (
                    "at java." in errors.errors[0].traceback
                    or "NumberFormatException" in errors.errors[0].traceback
                    if errors.errors
                    else False
                ),
                "python_error": [perrors.errors[0].error_type, perrors.errors[0].message]
                if perrors.errors
                else None,
                "reseeded_flag": reseeded.results[0].seed_reassigned,
                "reseeded_seed_recorded": reseeded.results[0].seed != 1234,
                "warm_ok": len(warm.results),
            }
        )
    )


if __name__ == "__main__":
    main(sys.argv[1])
