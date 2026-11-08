"""Outer controller policy. No native work occurs on import or preflight.

A backend must return fresh public observations, not caller-authored eligibility.
There is deliberately no frontend termination operation in the protocol.
"""
from dataclasses import dataclass
import uuid
PROTECTED={'CE7E80FC-64BF-41A0-B07B-60F4D8711808','D55C87E9-F349-49AC-BCD3-3B4B5BE9E010'}
from holds import HELD

class Refused(RuntimeError): pass

def require(condition, message):
    if not condition: raise Refused(message)

@dataclass(frozen=True)
class Window:
    pid: int
    process_identity: str
    identifier: str
    title: str
    device_uuid: str

@dataclass(frozen=True)
class Owned:
    uuid: str
    name: str
    runtime: str
    device_type: str
    window: Window | None


def external(snapshot, owned): return {k:v for k,v in snapshot.items() if k!=owned}

def validate_owned(owned, baseline):
    require(str(uuid.UUID(owned.uuid)).upper()==owned.uuid, 'Exact canonical UUID required')
    require(owned.uuid not in PROTECTED and owned.uuid not in baseline,'Baseline/protected device refused')
    if owned.window:
        w=owned.window
        require(w.pid>1 and w.pid not in HELD, 'Held/invalid frontend refused')
        require(w.device_uuid==owned.uuid and bool(w.identifier) and bool(w.title) and bool(w.process_identity),
            'Unknown window identity refused')


def check_snapshot(backend, owned, baseline):
    guard_custody(backend)
    now=backend.devices()
    window_check=getattr(backend, 'verify_outside_windows', None)
    if window_check is not None: window_check()
    require(external(now,owned.uuid)==baseline, 'External baseline changed; stop and coordinate recovery')
    row=now.get(owned.uuid)
    if row:
        require((row['name'],row['runtime'],row['deviceType'])==(owned.name,owned.runtime,owned.device_type),
                'Owned device identity changed')
    return row


def guard_custody(backend):
    guard=getattr(backend, "assert_custody", None)
    if guard is not None: guard()


def cleanup(backend, owned, baseline):
    """Any unknown identity/drift stops further mutation. Never quits Simulator."""
    guard_custody(backend)
    validate_owned(owned,baseline)
    check_snapshot(backend,owned,baseline)
    if owned.window is None:
        require(backend.windows_for_device(owned.uuid)==[], 'Unidentified window retained; cleanup blocked')
    else:
        require(backend.ax_trusted(), 'AX unavailable; retain window/device for root custody')
        matches=backend.windows_for_device(owned.uuid)
        if matches:
            require(matches==[owned.window], 'Unknown/ambiguous window identity refused')
            backend.close_window(owned.window)
            require(backend.windows_for_device(owned.uuid)==[], 'Owned window still present')
            check_snapshot(backend,owned,baseline)
    row=check_snapshot(backend,owned,baseline)
    if row and row['state']=='Booted':
        backend.shutdown(owned.uuid)
        row=check_snapshot(backend,owned,baseline)
    if row:
        require(row['state']=='Shutdown','Owned device not positively Shutdown')
        backend.delete(owned.uuid)
    require(check_snapshot(backend,owned,baseline) is None,'Owned device still present')
    return dict(cleanupPassed=True,externalBaselineUnchanged=True,ownedDeviceAbsent=True,
                frontendQuitRequested=False,frontendRetention='Do not quit shared Simulator process')


def setup(backend):
    """Permission and exact packet verification precede first mutation."""
    guard_custody(backend)
    require(backend.ax_trusted(), 'Accessibility prerequisite unavailable; no setup allowed')
    backend.verify_bindings()
    baseline=backend.devices()
    owned=backend.create_owned()
    guard_custody(backend)
    validate_owned(owned,baseline)
    try:
        check_snapshot(backend,owned,baseline)
        backend.boot(owned.uuid)
        require(backend.ax_trusted(),'Accessibility revoked before frontend creation')
        owned=backend.open_owned_window(owned)
        guard_custody(backend)
        validate_owned(owned,baseline)
        check_snapshot(backend,owned,baseline)
        require(backend.windows_for_device(owned.uuid)==[owned.window] and owned.window is not None,
                'Exact new window not established')
        require(backend.keyboard_connected(owned.window) is True,'Verified owned-window keyboard connection required')
        return owned,baseline
    except BaseException:
        # Never infer no window after a partially completed open. Backend must
        # reconcile exact creation; cleanup will refuse ambiguous observations.
        cleanup(backend,owned,baseline)
        raise


def dispatch(backend, owned, baseline):
    guard_custody(backend)
    validate_owned(owned,baseline)
    require(backend.ax_trusted(),'Accessibility revoked before dispatch')
    check_snapshot(backend,owned,baseline)
    require(owned.window is not None and backend.windows_for_device(owned.uuid)==[owned.window],
            'Exact owned window required')
    require(backend.keyboard_connected(owned.window) is True,'Keyboard no longer connected')
    backend.verify_bindings()
    return backend.dispatch_unchanged(owned,baseline)
