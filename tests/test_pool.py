"""SimulationPool, jar-free: pure validation/seed logic, constructor
checks, and behavioral tests through the _test_init seam under a REAL spawn
pool (worker processes, no JVM)."""

import sys
import zipfile
from types import SimpleNamespace

import pytest

import orlab.parallel as parallel
from orlab import SimulationPool
from orlab.errors import OrlabError, StudyAborted
import _pool_stubs


@pytest.fixture
def ork(tmp_path):
    path = tmp_path / "rocket.ork"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("rocket.ork", "<openrocket><simulation name='a'></simulation></openrocket>")
    return path


@pytest.fixture
def jar(tmp_path):
    path = tmp_path / "OpenRocket-24.12.jar"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("build.properties", "build.version=24.12\n")
    return path


def _pool(ork, jar, **kwargs):
    kwargs.setdefault("max_workers", 2)
    kwargs.setdefault("_test_init", _pool_stubs.fake_init)
    return SimulationPool(ork, str(jar), **kwargs)


# --- pure validation ---


def test_heterogeneous_key_sets_rejected(ork, jar):
    pool = _pool(ork, jar)
    with pytest.raises(ValueError, match="share one key set"):
        pool.run([{"wind_speed_average": 1.0}, {"launch_rod_angle": 0.1}])


def test_unknown_keys_rejected_naming_whitelist(ork, jar):
    pool = _pool(ork, jar)
    with pytest.raises(ValueError, match="worker_fn"):
        pool.run([{"wind_speed": 1.0}])


def test_rod_direction_without_into_wind_rejected(ork, jar):
    """The silent no-op the declarative contract exists to catch: rod
    direction is hijacked by the into-wind default."""
    pool = _pool(ork, jar)
    with pytest.raises(ValueError, match="launch_into_wind"):
        pool.run([{"launch_rod_direction": 1.2}])


@pytest.mark.parametrize("seed", [2**31, -(2**31) - 1, 1.5, "42", True])
def test_bad_task_seed_rejected(ork, jar, seed):
    pool = _pool(ork, jar)
    with pytest.raises((OverflowError, TypeError)):
        pool.run([{"wind_speed_average": 1.0, "seed": seed}])


def test_bool_for_float_key_rejected(ork, jar):
    pool = _pool(ork, jar)
    with pytest.raises(TypeError, match="number"):
        pool.run([{"wind_speed_average": True}])


def test_lambda_worker_fn_rejected_with_guidance(ork, jar):
    pool = _pool(ork, jar)
    with pytest.raises(ValueError, match="module level"):
        pool.run(1, worker_fn=lambda h, s, t: None)


def test_notebook_main_worker_fn_rejected(ork, jar, monkeypatch):
    """A function from an interactive __main__ pickles fine but dies opaquely
    after N JVM boots — reject it up front."""

    def fn(helper, sim, task):
        return None

    fn.__module__ = "__main__"
    monkeypatch.setitem(sys.modules, "__main__", SimpleNamespace())  # no __file__
    pool = _pool(ork, jar)
    with pytest.raises(ValueError, match="notebook"):
        pool.run(1, worker_fn=fn)


def test_seed_derivation_deterministic_and_deduplicated():
    tasks = [{} for _ in range(50)] + [{"seed": 7}, {"seed": -3}]
    a = SimulationPool._derive_seeds(tasks, seed=123)
    b = SimulationPool._derive_seeds(tasks, seed=123)
    assert a == b  # study seed reproduces the derivation
    assert len(set(a)) == len(a)  # no collisions
    assert a[-2:] == [7, -3]  # task overrides win
    c = SimulationPool._derive_seeds(tasks, seed=124)
    assert c != a


# --- constructor validation ---


def test_missing_ork_rejected(tmp_path, jar):
    with pytest.raises(FileNotFoundError, match="ork"):
        SimulationPool(tmp_path / "missing.ork", str(jar))


def test_bad_jar_rejected(ork, tmp_path):
    from orlab.errors import NotAnOpenRocketJar

    bad = tmp_path / "bad.jar"
    bad.write_text("not a jar")
    with pytest.raises(NotAnOpenRocketJar):
        SimulationPool(ork, str(bad))


def test_simulation_index_bounds_checked_without_jvm(ork, jar):
    with pytest.raises(IndexError, match="simulation_index"):
        SimulationPool(ork, str(jar), simulation_index=3)


def test_max_tasks_per_child_needs_311(ork, jar, monkeypatch):
    monkeypatch.setattr(parallel.sys, "version_info", (3, 10, 8))
    with pytest.raises(OrlabError, match="3.11"):
        SimulationPool(ork, str(jar), max_tasks_per_child=5)


def test_bad_worker_stdout_rejected(ork, jar):
    with pytest.raises(ValueError, match="worker_stdout"):
        SimulationPool(ork, str(jar), worker_stdout="tee")


def test_empty_tasks_no_pool(ork, jar):
    pool = _pool(ork, jar)
    study = pool.run([])
    assert study.results == () and study.errors == ()
    assert pool._executor is None  # no workers were ever started


# --- behavioral: real spawn pool, fake workers ---


def test_declarative_run_results_ordered_and_seeded(ork, jar):
    pool = _pool(ork, jar)
    calls = []
    study = pool.run(
        [{"wind_speed_average": float(i)} for i in range(6)],
        seed=42,
        progress=lambda done, total: calls.append((done, total)),
    )
    assert [r.index for r in study.results] == list(range(6))
    assert len({r.seed for r in study.results}) == 6
    assert not any(r.seed_reassigned for r in study.results)
    assert all(r.payload["apogee"] == 51.0 for r in study.results)
    assert calls[0] == (0, 6) and calls[-1] == (6, 6)
    assert len(calls) == 7
    records = study.to_records()
    assert records[3]["wind_speed_average"] == 3.0 and "apogee" in records[3]


def test_worker_fn_error_is_data_and_pool_survives(ork, jar):
    pool = _pool(ork, jar)
    study = pool.run(
        [{"x": 1}, {"x": 2}, {"x": 3}],
        worker_fn=_pool_stubs.value_error_fn,
    )
    assert study.results == ()
    assert len(study.errors) == 3
    assert study.errors[0].error_type == "ValueError"
    assert "deliberate failure" in study.errors[0].message
    with pytest.raises(OrlabError, match="3 of 3"):
        study.raise_if_errors()
    # same pool immediately reusable
    again = pool.run([{"x": 5}], worker_fn=_pool_stubs.ok_fn)
    assert again.results[0].payload["value"] == 10


def test_on_error_abort(ork, jar):
    pool = _pool(ork, jar)
    with pytest.raises(StudyAborted) as exc:
        pool.run([{"x": 1}] * 3, worker_fn=_pool_stubs.value_error_fn, on_error="abort")
    assert exc.value.reason == "task-error"


def test_unpicklable_payload_is_task_error_with_context(ork, jar):
    pool = _pool(ork, jar)
    study = pool.run([{}], worker_fn=_pool_stubs.unpicklable_payload_fn)
    assert study.errors and "pickle" in study.errors[0].message.lower()


def test_worker_crash_aborts_with_partial(ork, jar):
    pool = _pool(ork, jar, max_workers=1)
    tasks = [{"x": 1}, {"crash": True}]
    with pytest.raises(StudyAborted) as exc:
        pool.run(tasks, worker_fn=_dispatch_fn)
    assert exc.value.reason == "worker-crash"
    assert "-Xmx" in str(exc.value)
    # pool is dead afterwards
    with pytest.raises(OrlabError, match="dead"):
        pool.run(1)


def test_init_failure_single_report(ork, jar):
    pool = _pool(ork, jar, _test_init=_pool_stubs.failing_init)
    with pytest.raises(StudyAborted) as exc:
        pool.run(4, worker_fn=_pool_stubs.ok_fn)
    assert exc.value.reason == "worker-init"
    assert "deliberate init failure" in str(exc.value)


def test_progress_exception_cancels_run_pool_reusable(ork, jar):
    pool = _pool(ork, jar)

    def bad_progress(done, total):
        if done >= 1:
            raise RuntimeError("bar exploded")

    with pytest.raises(RuntimeError, match="bar exploded"):
        pool.run(4, worker_fn=_pool_stubs.ok_fn, progress=bad_progress)
    study = pool.run([{"x": 2}], worker_fn=_pool_stubs.ok_fn)
    assert study.results[0].payload["value"] == 4


def test_state_bleed_snapshot_restore(ork, jar):
    """run() with wind varied, then a second run() that doesn't set wind:
    the second run must see the document baseline, not run 1's last task."""
    pool = _pool(ork, jar, max_workers=1)
    pool.run([{"wind_speed_average": 9.9}])
    study = pool.run([{"launch_rod_angle": 0.2}], worker_fn=_pool_stubs.echo_options_fn)
    assert study.results[0].payload["wind"] == 2.0  # the fake baseline value


def _dispatch_fn(helper, sim, task):
    if task.get("crash"):
        return _pool_stubs.crash_fn(helper, sim, task)
    return _pool_stubs.ok_fn(helper, sim, task)
