"""Explicit successor adoption; references never cross a process boundary."""
import ctypes as C
import dataclasses
import functools
import json
from pathlib import Path
from commands import Commands, digest
from controller import Owned, Window, require, check_snapshot, cleanup
from mac_backend import AX, MacBackend, EXE, RUNTIME, DEVICE
from verify_bindings import HERE

PID = 75452
UID = '4CE0ECC9-1EDA-4543-80FF-9B011DF9044F'
NAME = 'MixerFocusReferenceV9-77741ac2-f3b1-4bab-be51-abf706417a60'
TITLE = NAME + ' – iOS 26.5'
IDENTITY = '75452 Sat Nov  7 21:04:57 2026     ' + EXE
OLD_ATTEMPT = HERE.parent/'apple-safe-keyboard-fix-r3/native-attempt-1'
RECOVERY = HERE.parent/'apple-window-recovery/inspection-1'


def guarded(method):
    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        self.assert_custody()
        try:
            return method(self, *args, **kwargs)
        except BaseException as error:
            self.unknown = True
            self.c.unresolved = True
            if getattr(self, 'preservation_failure', None) is None:
                self.preservation_failure = dict(type=type(error).__name__, message=str(error),
                    ownedUUID=UID, rootRecoveryRequired=True)
            raise
    return wrapped


class ReferenceAX(AX):
    def __init__(self):
        super().__init__()
        self.ax.AXUIElementGetPid.argtypes = [C.c_void_p, C.POINTER(C.c_int)]
        self.ax.AXUIElementGetPid.restype = C.c_int
        self.cf.CFEqual.argtypes = [C.c_void_p, C.c_void_p]
        self.cf.CFEqual.restype = C.c_bool
        self.cf.CFRetain.argtypes = [C.c_void_p]
        self.cf.CFRetain.restype = C.c_void_p
        self.retained = []

    def retain(self, ref):
        held = self.cf.CFRetain(ref)
        require(bool(held), 'Retained AX reference unavailable')
        self.retained.append(held)
        return held

    def equal(self, left, right):
        return bool(self.cf.CFEqual(left, right))

    def pid(self, ref):
        result = C.c_int()
        require(self.ax.AXUIElementGetPid(ref, C.byref(result)) == 0,
                'Invalid/stale AX reference PID')
        return result.value

    def finish(self):
        self.release()
        for ref in reversed(self.retained):
            self.cf.CFRelease(ref)
        self.retained = []


def normalize(raw):
    fields = ['name', 'state', 'deviceTypeIdentifier', 'dataPath', 'logPath']
    return {r['udid']: {**{k: r.get(k) for k in fields}, 'runtime': rt,
                       'deviceType': r['deviceTypeIdentifier']}
            for rt, rows in raw['devices'].items() for r in rows}


def evidence():
    bindings = json.loads((HERE/'evidence-bindings.json').read_text())
    for path, expected in bindings.items():
        p = Path(path)
        require(p.resolve() == p and p.is_file() and digest(p.read_bytes()) == expected,
                'Frozen recovery evidence changed: ' + path)
    receipts = sorted((OLD_ATTEMPT/'commands').glob('*.command.json'))
    require(len(receipts) == 13, 'All thirteen prior command receipts required')
    for path in receipts:
        row = json.loads(path.read_text())
        require(row['reaped'] is True and row['ownedGroupAbsent'] is True and
                row['unknownCustody'] is False and row['nestedCustodyUnknown'] is False and
                type(row['exitCode']) is int and row['exitCode'] == 0 and row['failure'] is None and
                all(s['eof'] is True for s in row['streams'].values()),
                'Prior command lacks terminal custody')
    failed = json.loads((OLD_ATTEMPT/'result.json').read_text())
    require('AX read failed AXWindows: -25204' in failed['failure']['traceback'],
            'Original failure evidence required')
    require(not (OLD_ATTEMPT/'native-invocation-once.json').exists(), 'Prior native invocation exists')
    require(not (OLD_ATTEMPT/'dispatch-result.json').exists(), 'Prior native result exists')
    owned = json.loads((OLD_ATTEMPT/'owned-device.json').read_text())
    require(owned == dict(uuid=UID, name=NAME, runtime=RUNTIME, device_type=DEVICE, window=None),
            'Retained owned resource differs')
    recovery = json.loads((RECOVERY/'result.json').read_text())
    require(recovery['externalBaselineUnchanged'] is True and
            recovery['cleanup']['allTerminalCustody'] is True and
            recovery['cleanup']['scratchRemoved'] is True and
            recovery['frontendIdentity'].strip() == IDENTITY and
            recovery['ax']['trusted'] is True and recovery['ax']['pid'] == PID and
            recovery['ax']['mutations'] == 0, 'Recovery record incomplete')
    baseline = normalize(json.loads((OLD_ATTEMPT/'commands/004-devices.stdout').read_text()))
    require(UID not in baseline, 'Owned UUID was in external baseline')
    observed = recovery['ownedDevice']
    require(observed['name'] == NAME and observed['runtime'] == RUNTIME and
            observed['deviceTypeIdentifier'] == DEVICE and observed['state'] == 'Booted',
            'Recovery owned record mismatch')
    return baseline, recovery


class AdoptionBackend(MacBackend):
    def __init__(self, folder):
        self.folder = Path(folder)
        self.c = Commands(self.folder/'commands')
        self.ax = ReferenceAX()
        self.index = 0
        self.unknown = False
        self.owned = None
        self.references = None
        self.allow_owned_absent = False
        self.closed = False
        self.baseline_windows = None
        self.baseline_frontends = None

    @guarded
    def command(self, label, argv, timeout=45):
        raw = super().command(label, argv, timeout)
        if label == 'inner-baseline':
            rows = normalize(json.loads(raw))
            require({k: v for k, v in rows.items() if k != UID} == self.external_baseline,
                    'External baseline drift in native selection')
            require(rows.get(UID) == self.adopted_device_row, 'Owned device drift in native selection')
        return raw

    @guarded
    def frontends(self):
        actual = self.command('exact-retained-frontend',
                              ['/bin/ps', '-p', str(PID), '-o', 'pid=,lstart=,comm='], 15).strip()
        require(actual == IDENTITY, 'Exact retained frontend identity drift')
        return {PID: actual}

    @guarded
    def read_windows(self):
        require(self.ax.trusted(), 'Fresh Python AX trust absent')
        self.frontends()
        app = self.ax.app(PID)
        result = []
        for ref in self.ax.children(app, 'AXWindows', False):
            require(self.ax.pid(ref) == PID and self.ax.text(ref, 'AXRole') == 'AXWindow',
                    'Window PID/role mismatch')
            result.append((ref, self.ax.text(ref, 'AXTitle')))
        require(all(not self.ax.equal(a[0], b[0]) for i, a in enumerate(result)
                    for b in result[i+1:]), 'Duplicate AX reference')
        return result

    @guarded
    def bind_references(self, recovery):
        require(self.references is None and self.owned is not None, 'Single adoption only')
        rows = self.read_windows()
        try:
            expected = recovery['ax']['windows']
            expected_titles = [w['title'] for w in expected]
            require(len(expected_titles) == len(set(expected_titles)) == 3 and
                    expected_titles.count(TITLE) == 1 and
                    sorted(title for _, title in rows) == sorted(expected_titles),
                    'Unique complete recovered window inventory required')
            # Each outside window must correspond uniquely to a baseline Booted device.
            for title in expected_titles:
                if title == TITLE:
                    continue
                matches = [uid for uid, row in self.external_baseline.items()
                           if row['state'] == 'Booted' and
                           title == row['name'] + ' – iOS ' + row['runtime'].split('iOS-')[-1].replace('-', '.')]
                require(len(matches) == 1, 'Outside window does not bind uniquely to baseline device')
            self.references = [(self.ax.retain(ref), title) for ref, title in rows]
            self.owned = dataclasses.replace(self.owned, window=Window(
                PID, IDENTITY, 'retained-reference-1', TITLE, UID))
            self.record(self.folder/'adopted-window.json', dict(
                window=dataclasses.asdict(self.owned.window),
                identityMechanism='process-local CFRetain + CFEqual + AXUIElementGetPid',
                serializedTokenAuthorizesNothing=True,
                outsideTitles=[t for _, t in self.references if t != TITLE]))
        finally:
            self.ax.release()

    def compare_references(self, rows):
        require(self.references is not None, 'Unbound AX references')
        matched = set()
        owned_ref = None
        for retained, title in self.references:
            matches = [(i, ref, current_title) for i, (ref, current_title) in enumerate(rows)
                       if self.ax.equal(retained, ref)]
            if not matches and title == TITLE and self.allow_owned_absent:
                continue
            require(len(matches) == 1, 'Retained window disappeared or changed reference')
            i, ref, current_title = matches[0]
            require(i not in matched and current_title == title and self.ax.pid(retained) == PID and
                    self.ax.text(retained, 'AXRole') == 'AXWindow' and
                    self.ax.text(retained, 'AXTitle') == title,
                    'Retained window identity stale/reused/changed')
            matched.add(i)
            if title == TITLE:
                owned_ref = ref
        require(len(matched) == len(rows), 'Unclassified/colliding new window')
        return owned_ref

    @guarded
    def windows_for_device(self, uid):
        require(uid == UID and self.owned is not None, 'Unowned window query')
        try:
            ref = self.compare_references(self.read_windows())
            return [self.owned.window] if ref is not None else []
        finally:
            self.ax.release()

    @guarded
    def verify_outside_windows(self):
        if self.references is not None:
            self.windows_for_device(UID)

    @guarded
    def exact_element(self, expected):
        require(self.owned is not None and expected == self.owned.window and expected is not None,
                'Exact adopted window required')
        ref = self.compare_references(self.read_windows())
        require(ref is not None and not self.closed, 'Owned window unavailable')
        return ref

    @guarded
    def close_window(self, expected):
        check_snapshot(self, self.owned, self.external_baseline)
        require(self.ax_trusted(), 'Fresh same-route AX trust required before close')
        try:
            window = self.exact_element(expected)
            button = self.ax.attr(window, 'AXCloseButton')
            require(self.ax.pid(button) == PID and self.ax.flag(button, 'AXEnabled'),
                    'Owned close control unavailable')
            self.ax.press(button)
            self.closed = True
            self.allow_owned_absent = True
        finally:
            self.ax.release()
        self.record(self.folder/'window-close-request.json', dict(
            window=dataclasses.asdict(expected), action='AXPress exact retained AXCloseButton', frontendQuit=False))

    @guarded
    def keyboard_connected(self, expected):
        return super().keyboard_connected(expected)

    @guarded
    def shutdown(self, uid):
        require(uid == UID, 'Unowned shutdown')
        check_snapshot(self, self.owned, self.external_baseline)
        require(self.windows_for_device(uid) == [], 'Owned window must be absent before shutdown')
        return super().shutdown(uid)

    @guarded
    def delete(self, uid):
        require(uid == UID, 'Unowned delete')
        row = check_snapshot(self, self.owned, self.external_baseline)
        require(row is not None and row['state'] == 'Shutdown' and self.windows_for_device(uid) == [],
                'Shutdown and exact owned-window absence required before delete')
        return super().delete(uid)

    def create_owned(self):
        raise RuntimeError('Adoption never creates a device')

    def boot(self, uid):
        raise RuntimeError('Adoption never boots a device')

    def open_owned_window(self, owned):
        raise RuntimeError('Adoption never opens a frontend or window')

    @guarded
    def adopt(self):
        baseline, recovery = evidence()
        require(self.ax_trusted(), 'Fresh Python and osascript AX trust required before adoption')
        self.verify_bindings()
        self.external_baseline = baseline
        self.owned = Owned(UID, NAME, RUNTIME, DEVICE, None)
        row = check_snapshot(self, self.owned, baseline)
        expected_row = {**recovery['ownedDevice'], 'deviceType': DEVICE}
        require(row == expected_row, 'Exact retained Booted device record required')
        self.adopted_device_row = expected_row
        self.bind_references(recovery)
        check_snapshot(self, self.owned, baseline)
        self.record(self.folder/'creation-intent.json', json.loads((OLD_ATTEMPT/'creation-intent.json').read_text()))
        self.record(self.folder/'adoption.json', dict(owned=dataclasses.asdict(self.owned),
                    externalBaseline=baseline, oldControllerResumed=False, devicesCreated=0))
        return self.owned, baseline

    @guarded
    def dispatch_unchanged(self, owned, baseline):
        check_snapshot(self, owned, baseline)
        return super().dispatch_unchanged(owned, baseline)
