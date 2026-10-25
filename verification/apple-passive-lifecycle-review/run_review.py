#!/usr/bin/env python3
"""Finite independent source/host review; writes only this review lane."""
import datetime
import difflib
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tarfile
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/apple-passive-lifecycle-observer'
SWIFT = pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc')
SDK = pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
CONTEXT = '6b8aba350224ed19f678669bdbea6b359d8de68b'
EXPECTED_HANDOFF = '9e30a9aeef107094d70b17fc83fc632f0278af9d0384a58564cd7b0456efbd75'
EXPECTED_ARCHIVE = '042c47cc39166ad25e475a5f213815e2aab926590a520e3eb51e0e04cd97774e'
EXPECTED_BASELINE = 'd1262c1e16a4decdca0ecbfdc278b7eaa1282f47d68776bfdede235157019cda'
sha = lambda data: hashlib.sha256(data).hexdigest()
stable = lambda value: (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
binding = lambda path: {'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}
commands = []
checks = []

def check(label, condition):
    assert condition, label
    checks.append(label)

def members(path):
    with tarfile.open(path) as archive:
        entries = archive.getmembers()
        check('safe unique regular archive members ' + path.name,
              all(m.isfile() and not m.name.startswith('/') and '..' not in pathlib.PurePosixPath(m.name).parts for m in entries)
              and len({m.name for m in entries}) == len(entries))
        return {m.name: archive.extractfile(m).read() for m in entries}

check('exact producer handoff', sha((PRODUCER / 'handoff.json').read_bytes()) == EXPECTED_HANDOFF)
check('exact candidate archive', sha((PRODUCER / 'review-source-package.tar.gz').read_bytes()) == EXPECTED_ARCHIVE)
baseline_path = ROOT / 'verification/apple-focus-system-observation/review-source-package.tar.gz'
check('exact accepted baseline', sha(baseline_path.read_bytes()) == EXPECTED_BASELINE)
handoff = json.loads((PRODUCER / 'handoff.json').read_bytes())
for name, expected in handoff['members'].items():
    check('sealed producer member ' + name, binding(ROOT / name) == expected)
candidate = members(PRODUCER / 'review-source-package.tar.gz')
baseline = members(baseline_path)
changed = sorted(n for n in baseline if candidate.get(n) != baseline[n])
added = sorted(set(candidate) - set(baseline))
check('40 to 42 members with 39 byte exact', len(baseline) == 40 and len(candidate) == 42 and len(set(baseline) - set(candidate)) == 0 and sum(candidate[n] == b for n, b in baseline.items()) == 39)
check('only existing main changes', changed == ['accepted/source/Prototype/main.swift'])
check('only two helpers added', added == ['accepted/source/Prototype/PassiveLifecycleData.swift', 'accepted/source/Prototype/PassiveLifecycleObserver.swift'])
check('twelve Prototype and 37 total Swift members', sum(n.startswith('accepted/source/Prototype/') and n.endswith('.swift') for n in candidate) == 12 and sum(n.endswith('.swift') for n in candidate) == 37)
check('four unchanged harness Swift members', sum(n.startswith('accepted/harness/') and n.endswith('.swift') for n in candidate) == 4 and all(candidate[n] == b for n, b in baseline.items() if n.startswith('accepted/harness/')))
source_members = {n: {'bytes': len(b), 'sha256': sha(b)} for n, b in sorted(candidate.items())}
(HERE / 'source-manifest.json').write_bytes(stable({'sourceContextRevision': CONTEXT, 'archiveSHA256': EXPECTED_ARCHIVE, 'members': source_members, 'changed': changed, 'added': added}))
patch = ''.join(difflib.unified_diff(baseline[changed[0]].decode().splitlines(keepends=True), candidate[changed[0]].decode().splitlines(keepends=True), fromfile='accepted-baseline/' + changed[0], tofile='candidate/' + changed[0]))
(HERE / 'independent-main.patch').write_text(patch)
inputs = {
    str(path.relative_to(ROOT)): binding(path) for path in [
        PRODUCER / 'handoff.json', PRODUCER / 'review-source-package.tar.gz',
        baseline_path, ROOT / 'verification/apple-focus-system-native-result/result.json',
        ROOT / 'verification/apple-focus-system-runtime-preparation/native-run-v8-d9a1ae2b-ef02-4db2-b2ff-4979213c8236/runtime/captures/0001-after-1.json']}
(HERE / 'input-bindings.json').write_bytes(stable(inputs))
(HERE / 'context-read-bindings.json').write_bytes(stable({str(path.relative_to(ROOT)): binding(path) for path in [ROOT / 'AGENTS.md', ROOT / 'PLAN.md']}))
(HERE / 'structural-checks.json').write_bytes(stable({'passed': True, 'checks': checks, 'scope': 'Independent archive and sealed input integrity; source-shape alone has no release or native authority.'}))

scratch = HERE / '.host-work'
assert not scratch.exists()
scratch.mkdir()
(scratch / 'cache').mkdir()
(scratch / 'tmp').mkdir()
(scratch / 'PassiveLifecycleData.swift').write_bytes(candidate['accepted/source/Prototype/PassiveLifecycleData.swift'])
explicit = {'TMPDIR': str(scratch / 'tmp') + '/', 'CLANG_MODULE_CACHE_PATH': str(scratch / 'cache'), 'SWIFT_MODULECACHE_PATH': str(scratch / 'cache'), 'LC_ALL': 'C'}
env = os.environ.copy()
env.update(explicit)

def run(name, argv, timeout=55):
    start = time.monotonic()
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    timed_out = False
    try:
        result = subprocess.run([str(v) for v in argv], cwd=ROOT, env=env, capture_output=True, timeout=timeout)
        stdout, stderr, code = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as exc:
        stdout, stderr, code, timed_out = exc.stdout or b'', exc.stderr or b'', None, True
    (HERE / (name + '.stdout')).write_bytes(stdout)
    (HERE / (name + '.stderr')).write_bytes(stderr)
    commands.append({'name': name, 'argv': [str(v) for v in argv], 'cwd': str(ROOT), 'explicitEnvironment': explicit,
        'startedUTC': started, 'elapsedSeconds': time.monotonic() - start, 'timeoutSeconds': timeout, 'timedOut': timed_out,
        'exitCode': code, 'stdoutSHA256': sha(stdout), 'stderrSHA256': sha(stderr), 'sourceArchiveSHA256': EXPECTED_ARCHIVE,
        'sourceContextRevision': CONTEXT})
    (HERE / 'commands.json').write_bytes(stable(commands))
    print(json.dumps({'command': name, 'exitCode': code, 'stdoutBytes': len(stdout), 'stderrBytes': len(stderr)}), flush=True)
    assert code == 0, stderr.decode(errors='replace')
    return stdout

passed = False
producer_summary = independent_summary = None
try:
    run('python-version', [sys.executable, '--version'])
    run('producer-read-only-audit', [sys.executable, '-B', PRODUCER / 'audit.py'])
    run('swift-version', [SWIFT, '--version'])
    run('compile-exact-producer-host', [SWIFT, '-swift-version', '6', '-sdk', SDK, '-target', 'arm64-apple-macosx26.0', '-module-cache-path', scratch / 'cache', '-parse-as-library', scratch / 'PassiveLifecycleData.swift', PRODUCER / 'HostTests.swift', '-o', scratch / 'producer-host'])
    original = ROOT / 'verification/apple-focus-system-runtime-preparation/native-run-v8-d9a1ae2b-ef02-4db2-b2ff-4979213c8236/runtime/captures/0001-after-1.json'
    producer_summary = json.loads(run('execute-exact-producer-host', [scratch / 'producer-host', original]).decode().splitlines()[-1])
    run('compile-independent-host', [SWIFT, '-swift-version', '6', '-sdk', SDK, '-target', 'arm64-apple-macosx26.0', '-module-cache-path', scratch / 'cache', '-parse-as-library', scratch / 'PassiveLifecycleData.swift', HERE / 'HostReview.swift', '-o', scratch / 'independent-host'])
    independent_summary = json.loads(run('execute-independent-host', [scratch / 'independent-host', original]).decode().splitlines()[-1])
    passed = producer_summary['passed'] and independent_summary['passed']
finally:
    shutil.rmtree(scratch)
    sdk_settings = SDK / 'SDKSettings.json'
    (HERE / 'sdk-settings.json').write_bytes(sdk_settings.read_bytes())
    (HERE / 'sdk-binding.json').write_bytes(stable({'path': str(SDK), 'resolvedPath': str(SDK.resolve()), 'settings': binding(sdk_settings)}))
    receipt = {'schema': 1, 'passed': passed, 'sourceContextRevision': CONTEXT, 'candidateHandoffSHA256': EXPECTED_HANDOFF,
        'sourceArchiveSHA256': EXPECTED_ARCHIVE, 'sourceMemberTreeSHA256': sha(stable(source_members)),
        'structuralChecks': len(checks), 'producerHost': producer_summary, 'independentHost': independent_summary,
        'testedSources': {name: binding(path) for name, path in {
            'exact-candidate-archive': PRODUCER / 'review-source-package.tar.gz',
            'exact-producer-HostTests.swift': PRODUCER / 'HostTests.swift', 'independent-HostReview.swift': HERE / 'HostReview.swift'}.items()},
        'exactCompiledFoundationMember': source_members['accepted/source/Prototype/PassiveLifecycleData.swift'],
        'uikitCompiled': False, 'genericSimulatorBuilds': 0, 'nativeExecutions': 0, 'nativeQueries': 0, 'networkCalls': 0,
        'physicalPhones': 'disconnected-deferred', 'gaAccepted': False,
        'scope': 'Independent source review and finite macOS Foundation controls only; no UIKit adapter execution.',
        'ownedHostScratchRemoved': not scratch.exists()}
    (HERE / 'host-receipt.json').write_bytes(stable(receipt))
    print(json.dumps(receipt, sort_keys=True), flush=True)
