"""Motor-swap plumbing, jar-free: argument dispatch, mount resolution, and
the accessor-era shims against duck-typed fakes."""

from types import SimpleNamespace

import pytest

from orlab import Helper
from orlab.errors import OrlabError


class _Motor:
    def __init__(self, designation):
        self._d = designation

    def getDesignation(self):
        return self._d


class _Config:
    def __init__(self, motor=None):
        self.motor = motor
        self.delay = 3.0

    def getMotor(self):
        return self.motor

    def setMotor(self, motor):
        self.motor = motor

    def setEjectionDelay(self, seconds):
        self.delay = seconds


class _ModernMount:
    """22.02+ era: getMotorConfig(fcid). Records the fcids it was asked
    about — the sim's OWN id must be passed through opaquely."""

    def __init__(self, name, motor=None, active=True):
        self._name, self._active = name, active
        self.config = _Config(motor)
        self.seen_fcids = []

    def getName(self):
        return self._name

    def isMotorMount(self):
        return self._active

    def getMotorConfig(self, fcid):
        self.seen_fcids.append(fcid)
        return self.config


class _LegacyMount:
    """15.03 era: getMotorConfiguration() map with .get(fcid)."""

    def __init__(self, name, motor=None, active=True):
        self._name, self._active = name, active
        self.config = _Config(motor)
        self.seen_fcids = []

    def getName(self):
        return self._name

    def isMotorMount(self):
        return self._active

    def getMotorConfiguration(self):
        def get(fcid):
            self.seen_fcids.append(fcid)
            return self.config

        return SimpleNamespace(get=get)


class _PlainComponent:
    """Most 15.03 components: no isMotorMount at all — the interface filter
    must exclude these before any method call."""

    def __init__(self, name):
        self._name = name

    def getName(self):
        return self._name


def _helper(components, mount_types):
    h = Helper.__new__(Helper)
    h._instance = SimpleNamespace(or_version="24.12", profile=SimpleNamespace(core_root="fake"))
    h._motor_mount_interface = lambda: mount_types
    rocket = SimpleNamespace(components=components)
    sim = SimpleNamespace(
        getRocket=lambda: rocket,
        getFlightConfigurationId=lambda: "fcid-1",
        getOptions=lambda: SimpleNamespace(),
    )
    return h, sim, rocket


@pytest.fixture(autouse=True)
def _fake_jiterator(monkeypatch):
    import orlab.core.helper as helper_mod

    monkeypatch.setattr(helper_mod, "JIterator", lambda rocket: iter(rocket.components))


def test_unique_active_mount_resolves():
    mount = _ModernMount("Inner Tube", motor=_Motor("A8"))
    h, sim, _ = _helper([_PlainComponent("Nose"), mount], (_ModernMount,))
    assert h._resolve_mount(sim, None) is mount


def test_interface_filter_excludes_plain_components():
    """A component without isMotorMount must never be probed for it."""
    mount = _ModernMount("Inner Tube", motor=_Motor("A8"))
    h, sim, _ = _helper([_PlainComponent("Nose"), _PlainComponent("Fins"), mount], (_ModernMount,))
    assert h._resolve_mount(sim, None) is mount


def test_motor_bearing_mount_breaks_tie():
    empty = _ModernMount("Booster tube")
    loaded = _ModernMount("Inner Tube", motor=_Motor("A8"))
    h, sim, _ = _helper([empty, loaded], (_ModernMount,))
    assert h._resolve_mount(sim, None) is loaded


def test_ambiguous_mounts_valueerror_lists_names():
    a = _ModernMount("Tube A", motor=_Motor("A8"))
    b = _ModernMount("Tube B", motor=_Motor("C6"))
    h, sim, _ = _helper([a, b], (_ModernMount,))
    with pytest.raises(ValueError, match="Tube A, Tube B"):
        h._resolve_mount(sim, None)


def test_named_mount_must_be_active():
    inactive = _ModernMount("Inner Tube", active=False)
    h, sim, _ = _helper([inactive], (_ModernMount,))
    with pytest.raises(ValueError, match="not an active motor mount"):
        h._resolve_mount(sim, "Inner Tube")


def test_legacy_map_accessor_era():
    mount = _LegacyMount("Inner Tube", motor=_Motor("A8"))
    h, sim, _ = _helper([mount], (_LegacyMount,))
    sim.getOptions = lambda: SimpleNamespace(getMotorConfigurationID=lambda: "cfg-1503")
    del sim.getFlightConfigurationId
    assert h.get_motor(sim) == "A8"
    assert set(mount.seen_fcids) == {"cfg-1503"}  # the sim's own id, opaque


def test_modern_fcid_passed_through_opaquely():
    mount = _ModernMount("Inner Tube", motor=_Motor("A8"))
    h, sim, _ = _helper([mount], (_ModernMount,))
    assert h.get_motor(sim) == "A8"
    assert set(mount.seen_fcids) == {"fcid-1"}


def test_mount_object_accepted_directly():
    mount = _ModernMount("Inner Tube", motor=_Motor("A8"))
    h, sim, _ = _helper([mount], (_ModernMount,))
    assert h._resolve_mount(sim, mount) is mount


def test_conflicting_kwargs_rejected(tmp_path):
    mount = _ModernMount("Inner Tube", motor=_Motor("A8"))
    h, sim, _ = _helper([mount], (_ModernMount,))
    h.load_motor = lambda path, designation=None: _Motor("X")
    h.find_motor = lambda d, manufacturer=None: _Motor("X")
    with pytest.raises(ValueError, match="manufacturer"):
        h.set_motor(sim, tmp_path / "m.eng", manufacturer="Estes")
    with pytest.raises(ValueError, match="designation"):
        h.set_motor(sim, "C6", designation="C6")


def test_no_known_accessor_curated_error():
    class WeirdMount:
        def getName(self):
            return "Weird"

        def isMotorMount(self):
            return True

    h, sim, _ = _helper([WeirdMount()], (WeirdMount,))
    with pytest.raises(OrlabError, match="accessor"):
        h.get_motor(sim)


def test_set_motor_dispatch_and_readback(tmp_path, monkeypatch):
    mount = _ModernMount("Inner Tube", motor=_Motor("A8"))
    h, sim, _ = _helper([mount], (_ModernMount,))
    h.find_motor = lambda d, manufacturer=None: _Motor(d.upper())
    h.set_motor(sim, "c6", manufacturer="Estes")
    assert h.get_motor(sim) == "C6"
    assert mount.config.delay == 3.0  # delay=None preserved

    h.set_motor(sim, "b6", manufacturer="Estes", delay=5.0)
    assert mount.config.delay == 5.0

    # file extensions dispatch to load_motor (case-insensitive, PathLike)
    seen = []
    h.load_motor = lambda path, designation=None: (seen.append(path), _Motor("ORLAB45"))[1]
    h.set_motor(sim, tmp_path / "curve.ENG")
    h.set_motor(sim, str(tmp_path / "curve.rse"))
    h.set_motor(sim, str(tmp_path / "bundle.zip"))
    assert len(seen) == 3 and h.get_motor(sim) == "ORLAB45"


def test_set_motor_readback_mismatch_raises():
    class StickyMount(_ModernMount):
        def getMotorConfig(self, fcid):
            # a mount whose assignment never sticks (wrong-config analogue)
            return SimpleNamespace(getMotor=lambda: _Motor("A8"), setMotor=lambda m: None)

    mount = StickyMount("Inner Tube", motor=_Motor("A8"))
    h, sim, _ = _helper([mount], (StickyMount,))
    h.find_motor = lambda d, manufacturer=None: _Motor("C6")
    with pytest.raises(OrlabError, match="did not stick"):
        h.set_motor(sim, "C6", manufacturer="Estes")
