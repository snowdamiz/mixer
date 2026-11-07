#!/usr/bin/env python3
"""Read-only accepted-dispatch preflight; never dispatch native work or repair paths."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PARENT = HERE.parent
OLD = PARENT / 'apple-settings-runtime-r2'
DEV = '/Applications/Xcode_26.6.app/Contents/Developer'
START = time.monotonic()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stable(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def put(name, value):
    with (HERE / name).open('xb') as stream:
        stream.write(stable(value))


def identity(path):
    info = path.lstat()
    assert path.resolve() == path and stat.S_ISREG(info.st_mode), str(path)
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=sha(raw), mode=stat.S_IMODE(info.st_mode))


def main():
    assert not (HERE / 'result.json').exists(), 'Preflight already recorded; no retries'
    scratch = Path(tempfile.mkdtemp(prefix='mixer-20261107-apple-tab-keyboard-', dir='/tmp')).resolve()
    commands = []
    watched = {}
    try:
        selected_path = PARENT / 'apple-tab-keyboard-root-selection.json'
        selected_raw = selected_path.read_bytes()
        selected = json.loads(selected_raw)
        assert selected['maximumNativeAttempts'] == 1 and selected['builds'] == 0
        assert selected['originalTwoAttemptBudget'] == dict(previouslyConsumed=1, selectedRemaining=1, automaticRetries=0)
        for key, binding in {'experiment': selected['experiment'], **selected['bindings']}.items():
            if isinstance(binding, dict) and 'path' in binding and 'sha256' in binding:
                path = REPO / binding['path']
                watched[str(path)] = identity(path)
                assert watched[str(path)]['sha256'] == binding['sha256'], key
        watched[str(selected_path)] = identity(selected_path)
        for name in ['packet.json', 'dispatch_successor.py', 'run_r2.py', 'materialize.py',
                     'relocated-source-custody.json', 'result.json', 'one-attempt-marker.json']:
            path = OLD / name
            watched[str(path)] = identity(path)
        for name, row in json.loads((OLD / 'packet.json').read_bytes())['files'].items():
            assert identity(OLD / name) == {k: v for k, v in row.items() if k != 'kind'}, name
        custody = json.loads((OLD / 'relocated-source-custody.json').read_bytes())
        retained_checks = []
        for group in custody:
            root = Path(group['retainedPath'])
            for name, row in group['members'].items():
                path = root / name
                actual = identity(path)
                assert actual['bytes'] == row['bytes'] and actual['sha256'] == row['sha256'], name
                watched[str(path)] = actual
            retained_checks.append(dict(originalPath=group['originalPath'],
                originalPathExists=Path(group['originalPath']).exists(), retainedPath=str(root),
                checkedFiles=len(group['members']), bytesUnchanged=True,
                recordedMemberTreeSHA256=group['memberTreeSHA256']))
        raw_manifest = json.loads((OLD / 'raw-artifacts.json').read_bytes())
        raw_root = Path(raw_manifest['root'])
        for name, row in raw_manifest['members'].items():
            path = raw_root / name
            actual = identity(path)
            assert actual['bytes'] == row['bytes'] and actual['sha256'] == row['sha256'], name
            watched[str(path)] = actual
        baseline = json.loads((OLD / 'result.json').read_bytes())
        predicates = []

        def collect(value):
            if isinstance(value, dict):
                if 'actualNativeFocusTraversal' in value:
                    predicates.append(value)
                for child in value.values():
                    collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)

        collect(baseline)
        assert predicates and all(len(p) == 20 and sum(v is True for v in p.values()) == 19
                                  and p['actualNativeFocusTraversal'] is False for p in predicates)
        put('baseline-preservation.json', dict(rawManifestSHA256=sha((OLD / 'raw-artifacts.json').read_bytes()),
            rawRoot=str(raw_root), checkedRawFiles=len(raw_manifest['members']), rawBytesExact=True,
            Settings=baseline['Settings'], Tab=baseline['Tab'], originalPredicateSets=predicates,
            relocation=retained_checks))
        environment = {}
        for name, argv in [
            ('revision', ['git', 'rev-parse', 'HEAD']),
            ('os', ['/usr/bin/sw_vers']),
            ('kernel', ['/usr/bin/uname', '-a']),
            ('xcode', [DEV + '/usr/bin/xcodebuild', '-version']),
            ('swift', ['/usr/bin/xcrun', 'swiftc', '--version']),
            ('sdk', ['/usr/bin/xcrun', '--sdk', 'iphonesimulator', '--show-sdk-version']),
            ('simulators-before', ['/usr/bin/xcrun', 'simctl', 'list', 'devices', '--json']),
            ('runtimes', ['/usr/bin/xcrun', 'simctl', 'list', 'runtimes', '--json'])]:
            before = time.monotonic()
            process = subprocess.run(argv, cwd=REPO,
                env={**os.environ, 'DEVELOPER_DIR': DEV, 'PYTHONDONTWRITEBYTECODE': '1', 'TMPDIR': str(scratch)},
                capture_output=True, timeout=45)
            (HERE / (name + '.stdout')).write_bytes(process.stdout)
            (HERE / (name + '.stderr')).write_bytes(process.stderr)
            commands.append(dict(argv=argv, cwd=str(REPO), developerDirectory=DEV, exitCode=process.returncode,
                elapsedSeconds=time.monotonic()-before, stdoutSHA256=sha(process.stdout), stderrSHA256=sha(process.stderr)))
            assert process.returncode == 0, name
            environment[name] = process.stdout.decode()
        environment.update(python=sys.version, pythonExecutable=str(Path(sys.executable).resolve()),
            pythonExecutableSHA256=sha(Path(sys.executable).resolve().read_bytes()))
        put('environment.json', environment)
        runtimes = json.loads(environment['runtimes'])['runtimes']
        runtime = next(r for r in runtimes if r['identifier'] == 'com.apple.CoreSimulator.SimRuntime.iOS-26-5')
        assert runtime['isAvailable'] and runtime['buildversion'] == '23F77'
        spec = importlib.util.spec_from_file_location('_unchanged_accepted_dispatcher', OLD / 'dispatch_successor.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        old_markers = {str(p): identity(p) for p in (module.BASE / 'dispatch-attempts').glob('*.json')}
        phase = {'verifier': True}
        denied = []

        def audit(event, args):
            if phase['verifier'] and (event in ['subprocess.Popen', 'os.system', 'os.kill', 'os.killpg',
                'os.posix_spawn', 'os.exec'] or event.startswith('socket.')):
                denied.append(event)
                raise RuntimeError('Read-only verifier forbids native/process/socket operation: ' + event)

        sys.addaudithook(audit)
        try:
            value = module.verify()
            verifier = dict(verified=value, error=None)
        except Exception as error:
            verifier = dict(verified=None, error=dict(type=type(error).__name__, message=str(error),
                traceback=traceback.format_exc()))
        finally:
            phase['verifier'] = False
        verifier.update(dispatchCalled=False, nativeOperationsBlocked=denied,
            unchangedDispatcherSHA256=identity(OLD / 'dispatch_successor.py')['sha256'])
        put('accepted-dispatch-preflight.json', verifier)
        assert verifier['error'] and verifier['error']['type'] == 'FileNotFoundError', verifier
        missing = OLD / 'sealed-inputs/verification/apple-passive-lifecycle-runtime-preparation/prepare.py'
        assert str(missing) in verifier['error']['message'] and not missing.exists(), verifier
        assert old_markers == {str(p): identity(p) for p in (module.BASE / 'dispatch-attempts').glob('*.json')}
        assert watched == {name: identity(Path(name)) for name in watched}
        after = subprocess.run(['/usr/bin/xcrun', 'simctl', 'list', 'devices', '--json'], cwd=REPO,
            env={**os.environ, 'DEVELOPER_DIR': DEV, 'PYTHONDONTWRITEBYTECODE': '1', 'TMPDIR': str(scratch)},
            capture_output=True, timeout=45)
        (HERE / 'simulators-after.stdout').write_bytes(after.stdout)
        (HERE / 'simulators-after.stderr').write_bytes(after.stderr)
        commands.append(dict(argv=['/usr/bin/xcrun', 'simctl', 'list', 'devices', '--json'],
            cwd=str(REPO), developerDirectory=DEV, exitCode=after.returncode,
            stdoutSHA256=sha(after.stdout), stderrSHA256=sha(after.stderr)))
        assert after.returncode == 0

        def states(raw):
            return {r['udid']: {k: r.get(k) for k in ['name', 'state', 'deviceTypeIdentifier']}
                    for rows in json.loads(raw)['devices'].values() for r in rows}

        before_states = states(environment['simulators-before'])
        after_states = states(after.stdout)
        assert before_states == after_states
        protected = ['CE7E80FC-64BF-41A0-B07B-60F4D8711808', 'D55C87E9-F349-49AC-BCD3-3B4B5BE9E010']
        assert all(after_states[p]['state'] == 'Booted' for p in protected)
        put('input-identities.json', watched)
        put('commands.json', commands)
        result = dict(status='ineligible-before-XCTest', hypothesis='persistent Simulator hardware keyboard connection',
            experimentOutcome='not-tested', blocker='Accepted unchanged dispatcher cannot load its relocated sealed baseline.',
            missingRequiredPath=str(missing), retainedBaselinePath=custody[0]['retainedPath'],
            rootSelectionSHA256=sha(selected_raw), sourceBindings=selected['bindings'],
            sourceIdentityAuthority='Exact archive/manifest bytes; checkout revision is context only.',
            nativeAttempts=0, builds=0, automaticRetries=0,
            originalAttemptBudget=dict(maximum=2, previouslyConsumed=1, consumedHere=0, remaining=1),
            methodResults=dict(Settings='Not run', Tab='Not run'), officialImport='Not run',
            originalTwentyPredicates='Retained baseline checked: 19 true; actualNativeFocusTraversal false. No new verdict.',
            publicSimulatorUIInspected=False, ownedWindowHardwareKeyboardVerified=False,
            nativeDispatchEligibility=False, independentReviewNeededForAnyNewLauncherPacket=True,
            remediation='Root may restore the exact sealed-inputs tree at its bound path under coordinated ownership, or supply an independently reviewed successor packet. Rerun preflight before native setup.',
            writesLimitedTo='New apple-tab-keyboard-runtime directory and unique /tmp scratch only.',
            acceptedSourceRuntimeProductsAndPacketsUnchanged=True, checkedInputFiles=len(watched),
            noNewDispatchMarker=True, frontendBaseline='Not collected: no frontend launched; stopped before native setup.',
            cleanup=dict(noOwnedSimulatorCreated=True, noFrontendOrWindowLaunched=True, noListenerOpened=True,
                allSimulatorStatesPreserved=True, protectedSimulators={p: after_states[p]['state'] for p in protected},
                innerFiveRuntimeCleanupChecks='Not applicable: runtime not entered; no new pass claimed.',
                globalPreferencesChanged=False, heldProcessesProbedOrSignalled=False,
                parentIndexAccessed=False, gitMutations=0, phones='disconnected; no discovery',
                children=0, commits=0, pushes=0, scratch=str(scratch)),
            elapsedSeconds=time.monotonic()-START, finishedAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            GAQualified=False)
    finally:
        shutil.rmtree(scratch)
    result['cleanup']['scratchAbsent'] = not scratch.exists()
    put('result.json', result)
    report = '''Experiment stopped before XCTest; final native attempt remains unconsumed.

The unchanged accepted dispatcher verify() fails with FileNotFoundError at
apple-settings-runtime-r2/sealed-inputs/verification/apple-passive-lifecycle-runtime-preparation/prepare.py.
The accepted source-custody record says that 275-file sealed tree was moved to
/private/tmp/mixer-20261107-apple-settings-runtime-agcvpnc6/sealed-baseline.
All 275 retained file bytes still match their custody record. The accepted
dispatcher still binds the absent old location. No path overrides, monkeypatches,
symlinks, packet changes, source approval bypass, or dispatch() calls occurred.

Restoring the old tree writes outside this lane's ownership. Relocating or
replacing the launcher packet requires independent review before dispatch.
The no-children instruction prevents obtaining that review within this lane.
Root must coordinate exact-path restoration or provide a reviewed successor,
then repeat preflight before creating the single owned Simulator/frontend.

Native attempts 0; builds 0; retries 0. Original budget: 1 previously consumed,
1 remaining. Settings/Tab not run; hardware-keyboard isolation/UI/menu checked
state not tested. This neither supports nor refutes the keyboard hypothesis.
No official import or new 20-predicate verdict is claimed. Original failed raw
evidence remains exact; the baseline retains Settings Passed / Tab Failed,
with actualNativeFocusTraversal false and the other 19 original predicates true.

Accepted packet, candidate archive/template/review and products remain exact.
Current host tools and source revision are in environment.json; exact bindings
are in result.json/input-identities.json. Commands and output are retained.
Runtime/build identities remain the selected Xcode 26.6 / iOS 26.5 (23F77),
compile tree f402eba7b6fa8abf2671e3a95441351dace37f291a9d55024232c9112b2720fb,
runtime tree 02e26e6868ef0949c3c0757c0691281817489dabbffa699090a1a2cc88bf2652,
products 495f83c4702f7b229be495756f0a524c700f07159c5e21975dea471d118a8904.

No simulator/frontend/window/listener was created. Before/after device states
match, and both protected UUIDs remain Booted. No global preferences, held
processes, frozen lanes, historical V5, phones or parent index were touched.
Unique /tmp scratch was removed. Inner five runtime cleanups were not entered;
their prior passing evidence remains history, not a new cleanup receipt.
No source changes, delegation, commits, pushes, or GA acceptance.
'''
    with (HERE / 'REPORT.txt').open('x') as stream:
        stream.write(report)
    print(json.dumps(dict(status=result['status'], nativeAttempts=0, remainingAttempts=1,
        blocker=result['blocker'], cleanupPassed=result['cleanup']['scratchAbsent'])))


if __name__ == '__main__':
    main()
