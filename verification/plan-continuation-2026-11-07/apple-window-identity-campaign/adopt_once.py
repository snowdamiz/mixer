"""Prospective root selection: adopt the retained resource once; never reset R3."""
import json
import sys
import traceback
from pathlib import Path
from commands import digest, write
from controller import require, dispatch, cleanup
from adoption import AdoptionBackend, UID, PID, IDENTITY, HERE


def validate_terminal(native):
    require(type(native) is dict and native.get('schema') == 'mixer.apple-focus-reference-runtime.9' and
            type(native.get('runPassed')) is bool and native.get('gaAccepted') is False,
            'Inner result shape invalid; retain nested custody')
    gates = native.get('cleanupResults')
    expected = {'loopback-server-shutdown', 'loopback-server-close', 'loopback-thread-join',
                'ephemeral-capability-workspace-removal', 'owned-simulator-and-baseline-reconciliation'}
    require(type(gates) is list and len(gates) == 5 and
            all(type(g) is dict and type(g.get('resource')) is str and g.get('passed') is True for g in gates) and
            {g['resource'] for g in gates} == expected and
            'sessionFailure' in native and native['sessionFailure'] is None and
            type(native.get('xcodebuildExitCode')) is int and native['xcodebuildExitCode'] in (0, 65) and
            native.get('reportingFailures') == [],
            'Inner terminal evidence incomplete; retain nested custody')


def validate_native_binding(folder, plan, backend):
    require(digest((folder/'root-selection.json').read_bytes()) == plan['selectionSHA256'],
            'Native root selection changed')
    require(json.loads((folder/'native-invocation-once.json').read_text()) ==
            dict(packetSHA256=plan['packetSHA256'], selectionSHA256=plan['selectionSHA256']),
            'Native invocation binding missing/changed')
    row = backend.c.events[-1]
    require(row['operation'] == 'native-dispatch' and row['argv'] == plan['argv'] and
            row['timeoutSeconds'] == 950 and row['unknownCustody'] is False and
            row['nestedCustodyUnknown'] is False and row['reaped'] is True and
            row['ownedGroupAbsent'] is True and type(row['exitCode']) is int and row['exitCode'] == 0 and
            all(stream['eof'] is True for stream in row['streams'].values()),
            'Native bound command custody incomplete')


def run(mode, folder, reviewed_seal_sha):
    require(mode in ('adopt-reviewed-once', 'cleanup-reviewed-once'), 'Explicit adoption selection required')
    seal_path = HERE/'candidate-seal.json'
    require(digest(seal_path.read_bytes()) == reviewed_seal_sha, 'Reviewed successor seal required')
    seal = json.loads(seal_path.read_text())
    require(Path(sys.executable).resolve() == Path(seal['pythonExecutable']).resolve() and
            digest(Path(sys.executable).resolve().read_bytes()) == seal['pythonExecutableSHA256'],
            'Exact selected Python route required')
    for name, expected in seal['sourceFiles'].items():
        require(digest((HERE/name).read_bytes()) == expected, 'Source differs: ' + name)
    folder = Path(folder)
    require(folder.resolve() == folder and folder.parent == HERE and not folder.exists(),
            'Fresh owned successor output required')
    folder.mkdir()
    # The successor owns its own no-retry reservation. R3's reservation is immutable.
    write(HERE/'adoption-once.json', dict(mode=mode, output=str(folder),
          reviewedSealSHA256=reviewed_seal_sha, ownedUUID=UID, frontendPID=PID,
          frontendIdentity=IDENTITY, oldControllerResumed=False))
    backend = None
    owned = baseline = None
    outcome = dict(mode=mode, ownedUUID=UID, frontendPID=PID, gaAccepted=False, nativeAttempts=0, nativeDispatchInvocations=0)
    try:
        backend = AdoptionBackend(folder)
        owned, baseline = backend.adopt()
        write(folder/'external-baseline.json', baseline)
        if mode == 'cleanup-reviewed-once':
            outcome['readiness'] = 'Root explicitly selected exact cleanup only'
        elif backend.keyboard_connected(owned.window) is not True:
            outcome['readiness'] = 'Keyboard not connected; cleanup without native attempt'
        else:
            plan = dispatch(backend, owned, baseline)
            write(folder/'exact-dispatch-command.json', plan)
            outcome['nativeDispatchInvocations'] = 1
            outcome['nativeAttempts'] = 'unknown-until-bound-terminal-result'
            backend.native_dispatch(plan['argv'])
            native = json.loads((folder/'dispatch-result.json').read_text())
            validate_terminal(native)
            validate_native_binding(folder, plan, backend)
            outcome['nativeAttempts'] = 1
            outcome['native'] = native
            # The unchanged producer may already have removed the owned device/window.
            backend.allow_owned_absent = True
        outcome['outerCleanup'] = cleanup(backend, owned, baseline)
    except BaseException as error:
        if backend is not None:
            backend.unknown = True
            backend.c.unresolved = True
        outcome['failure'] = dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc())
    finally:
        if backend is not None:
            if getattr(backend, 'preservation_failure', None) is not None:
                outcome['preservationFailure'] = backend.preservation_failure
            # Local reference release only: no AX observations/actions after UNKNOWN.
            backend.ax.finish()
        outcome['reviewApprovalClaimed'] = False
        outcome['frontendQuitRequested'] = False
        write(folder/'result.json', outcome)
    require('failure' not in outcome, 'Successor retained failure; no automatic retry or cleanup')
    return outcome


if __name__ == '__main__':
    require(len(sys.argv) == 6 and sys.argv[2] == UID and sys.argv[3] == str(PID),
            'Mode, exact retained UUID/PID, fresh output and reviewed seal required')
    run(sys.argv[1], sys.argv[4], sys.argv[5])
