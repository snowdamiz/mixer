#!/usr/bin/env python3
"""Replay real cold-start orderings using immutable derived source, never live edits."""
import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument('--name', required=True)
parser.add_argument('--modes', nargs='+', default=['debug', 'release', 'tsan'], choices=['debug', 'release', 'tsan'])
args = parser.parse_args()
assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
out = HERE / args.name
out.mkdir(exist_ok=False)
work = HERE / '.build' / args.name
source = work / 'source'
source.mkdir(parents=True, exist_ok=False)
env = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
dependency = ROOT / 'verification/guest-ui-teardown-window/builds/current-caaa005-1/build-receipt.json'
assert sha(dependency) == '8abd4367111a5cd4f4d4438750bfb24bc588d56e1e98fbe269f781fddd6b799c'
base = json.loads(dependency.read_text())
base_work = Path(base['dylib']).parents[1]
base_source = Path(base['source'])
manifest = json.loads((ROOT / base['source_manifest']).read_text())
for relative, digest in base['artifacts'].items():
    assert sha(base_work / relative) == digest, relative
for relative, digest in manifest['files'].items():
    assert sha(base_source / relative) == digest, relative

files = {}
def freeze(relative, contents):
    dest = source / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(contents)
    files[relative] = sha(dest)
    dest.chmod(0o444)
    return dest

revision = 'd6505ac'
prefix = 'capability-activation/Sources/MixerCapabilityActivation/'
paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', revision, '--', prefix], cwd=ROOT, text=True).splitlines()
for relative in paths:
    if relative.endswith('.swift'):
        freeze(relative, subprocess.check_output(['git', 'show', revision + ':' + relative], cwd=ROOT))
runtime_prefix = 'experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/'
for relative in manifest['files']:
    if relative.startswith(runtime_prefix) and relative.endswith('.swift'):
        freeze(relative, (base_source / relative).read_bytes())
test_path = 'capability-activation/Tests/MixerCapabilityActivationTests/CapabilityColdStartRuntimeTests.swift'
original_test = subprocess.check_output(['git', 'show', '22d048c:' + test_path], cwd=ROOT)
repaired_test = (ROOT / test_path).read_bytes()
assert hashlib.sha256(repaired_test).hexdigest() == '292448a10a86299a55f600ce73b2442b3c84a92543adca4fe8aa7b9b68e4a720'
freeze('original-test.swift.txt', original_test)
freeze('repaired-test.swift.txt', repaired_test)
fixtures = 'capability-activation/Tests/MixerCapabilityActivationTests/Fixtures/'
for relative in subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', revision, '--', fixtures], cwd=ROOT, text=True).splitlines():
    freeze(relative, subprocess.check_output(['git', 'show', revision + ':' + relative], cwd=ROOT))
for name in ['SetupProbe.swift', 'NativeQueueProbe.swift', 'TestSupport.swift', 'run.py']:
    freeze('verification/cold-start-cleanup-ci-repair/' + name, (HERE / name).read_bytes())

# Immutable derived copies preserve every production condition and effect.
setup = source / (prefix + 'CapabilityConcreteAttempt.swift')
setup_original = setup.read_text()
needle = '            try control.requireOpen(deadline: true)\n            let http = try input.consumed.policy.http.map'
assert setup_original.count(needle) == 1
setup_derived = setup_original.replace(needle, '            await ColdStartSetupCIHooks.shared.pauseAfterKVSetup()\n' + needle)
derived_setup = freeze('derived/CapabilityConcreteAttempt.swift', setup_derived.encode())
session = source / (runtime_prefix + 'Session.swift')
session_original = session.read_text()
needle = '                    lifecycle?.constructorReturned()\n                }\n            }\n        } onCancel: { self.cancel() }'
assert session_original.count(needle) == 1
session_derived = session_original.replace(needle, '                    lifecycle?.constructorReturned()\n                }\n                NativeSubmissionCIProbe.recordEnqueued()\n            }\n        } onCancel: { self.cancel() }')
derived_session = freeze('derived/Session.swift', session_derived.encode())
freeze('derived/setup-instrumentation.diff', ''.join(difflib.unified_diff(setup_original.splitlines(keepends=True), setup_derived.splitlines(keepends=True), fromfile='committed/CapabilityConcreteAttempt.swift', tofile='derived/CapabilityConcreteAttempt.swift')).encode())
freeze('derived/native-submission-instrumentation.diff', ''.join(difflib.unified_diff(session_original.splitlines(keepends=True), session_derived.splitlines(keepends=True), fromfile='retained/Session.swift', tofile='derived/Session.swift')).encode())

def test_variant(contents, order):
    text = contents.decode()
    if order == 'unchanged':
        return text
    text = text.replace('    var entered: Bool { condition.lock(); defer { condition.unlock() }; return started }', '    var entered: Bool { condition.lock(); defer { condition.unlock() }; return started }\n    var wasReleased: Bool { condition.lock(); defer { condition.unlock() }; return released }')
    start = text.index('    func testCloseDuringQueuedNativeCreationKeepsCountedOrdinaryAndAdapterTails()')
    end = text.index('    func testFacadeDeinit', start)
    body = text[start:end]
    needle = '        try await stage(f,runtime,storage: true)'
    assert body.count(needle) == 1
    body = body.replace(needle, '        let ciStartup = CIAsyncReturnFlag(), ciClosing = CIAsyncReturnFlag()\n        NativeSubmissionCIProbe.reset()\n' + ('        await ColdStartSetupCIHooks.shared.arm()\n' if order == 'pre-admission' else '') + needle)
    if 'defer { startupReturn.recordReturn() }' in body:
        body = body.replace('defer { startupReturn.recordReturn() }', 'defer { startupReturn.recordReturn(); ciStartup.record() }')
        body = body.replace('defer { closeReturn.recordReturn() }', 'defer { closeReturn.recordReturn(); ciClosing.record() }')
    else:
        body = body.replace('let startup = Task { try await runtime.start() }', 'let startup = Task { defer { ciStartup.record() }; return try await runtime.start() }')
        body = body.replace('let closing = Task { await runtime.close() }', 'let closing = Task { defer { ciClosing.record() }; await runtime.close() }')
    marker = '        let closing = Task {'
    pos = body.index(marker)
    wait = ('        try await eventually("derived real post-KV gate not reached") { await ColdStartSetupCIHooks.shared.isEntered }\n' if order == 'pre-admission' else '        try await eventually("actual native create job not submitted") { NativeSubmissionCIProbe.count == 1 }\n')
    body = body[:pos] + wait + body[pos:]
    marker = '        try await eventually("close did not synchronously stop admission") { (await runtime.recoverySnapshot()).activation.phase == .closed }'
    assert body.count(marker) == 1
    if order == 'pre-admission':
        injection = '''
        try await eventually("real close stop signal not latched") { (await runtime.recoverySnapshot()).activation.terminalCause != nil }
        XCTAssertEqual(NativeSubmissionCIProbe.count, 0)
        await ColdStartSetupCIHooks.shared.release()
        do { _ = try await startup.value } catch {}
        await closing.value
        XCTAssertFalse(gate.wasReleased)
        XCTAssertTrue(ciStartup.didReturn); XCTAssertTrue(ciClosing.didReturn)
        let ciState = await runtime.recoverySnapshot()
        print("CI_ORDER pre-admission occupied=\\(CapabilityAttemptReservation.occupiedSlots) baseline=\\(baseline) pending=\\(ciState.activation.cleanupPending) submissions=\\(NativeSubmissionCIProbe.count) startupReturned=\\(ciStartup.didReturn) closeReturned=\\(ciClosing.didReturn) queueReleased=\\(gate.wasReleased)")
'''
        body = body.replace(marker, marker + injection)
    else:
        injection = '''
        let ciState = await runtime.recoverySnapshot()
        XCTAssertTrue(ciState.activation.cleanupPending)
        XCTAssertEqual(CapabilityAttemptReservation.occupiedSlots, baseline + 1)
        XCTAssertFalse(ciStartup.didReturn); XCTAssertFalse(ciClosing.didReturn)
        XCTAssertFalse(gate.wasReleased)
        XCTAssertEqual(NativeSubmissionCIProbe.count, 1)
        print("CI_ORDER queued occupied=\\(CapabilityAttemptReservation.occupiedSlots) baseline=\\(baseline) pending=\\(ciState.activation.cleanupPending) submissions=\\(NativeSubmissionCIProbe.count) startupReturned=\\(ciStartup.didReturn) closeReturned=\\(ciClosing.didReturn) queueReleased=\\(gate.wasReleased)")
'''
        assert body.count('        gate.release(); do') == 1
        body = body.replace('        gate.release(); do', injection + '        gate.release(); do')
    return text[:start] + body + text[end:]

variants = {
    'original-pre-admission': (original_test, 'pre-admission', 1),
    'repaired-pre-admission': (repaired_test, 'pre-admission', 0),
    'original-queued': (original_test, 'queued', 0),
    'repaired-queued': (repaired_test, 'queued', 0),
    'repaired-unmodified': (repaired_test, 'unchanged', 0),
}
for variant, (contents, order, expected) in variants.items():
    transformed = test_variant(contents, order)
    freeze('derived/' + variant + '.swift', transformed.encode())
    freeze('derived/' + variant + '.diff', ''.join(difflib.unified_diff(contents.decode().splitlines(keepends=True), transformed.splitlines(keepends=True), fromfile='original-test' if variant.startswith('original') else 'repaired-test', tofile='derived/' + variant + '.swift')).encode())

receipt = {
    'started_utc': datetime.now(timezone.utc).isoformat(), 'activation_revision': subprocess.check_output(['git', 'rev-parse', revision], cwd=ROOT, text=True).strip(),
    'original_test_revision': '22d048c', 'repaired_test_sha256': hashlib.sha256(repaired_test).hexdigest(),
    'source': str(source), 'source_files': files, 'source_tree_sha256': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
    'dependency_receipt': str(dependency.relative_to(ROOT)), 'dependency_receipt_sha256': sha(dependency), 'dependency_artifacts': base['artifacts'],
    'dependency_source_manifest_sha256': sha(ROOT / base['source_manifest']),
    'commands': [], 'artifacts': {},
    'scope': 'Verification-only deterministic scheduling in retained derived d6505ac activation sources and exact retained runtime sources. Real signed fixture/validator/KV/native queue and unchanged production predicates; original expected assertion failure retained. Debug/Release/TSan selected modules rebuilt. No live product/test edits.',
    'limitations': [
        'The exact hosted interleaving remains unproven: its log contains only failed observations, no native submission or async-return trace.',
        'Derived gate hooks force legal schedules and observe real queue submission; they are not release product code or a claim the hosted process followed that schedule.',
        'TSan covers rebuilt activation/runtime/probe Swift files. Retained SDK/C/native archive dependencies are digest checked but are not rebuilt or comprehensively TSan instrumented.',
        'No physical devices, published consumer, signing/store/customer/operational/GA qualification, commits or pushes.',
    ],
}
def save(): (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
def stable():
    for relative, digest in files.items(): assert sha(source / relative) == digest, relative
def run(name, argv, expected=0, extra=None):
    stable()
    argv = [str(arg) for arg in argv]
    started = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=source, env=env | (extra or {}), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240)
        data, code = result.stdout, result.returncode
    except subprocess.TimeoutExpired as error:
        data, code = (error.stdout or b'') + b'\nTIMEOUT\n', 124
    log = out / (name + '.log'); log.write_bytes(data)
    receipt['commands'].append({'name': name, 'argv': argv, 'cwd': str(source), 'environment': {'DEVELOPER_DIR': env['DEVELOPER_DIR']} | (extra or {}), 'seconds': time.monotonic() - started, 'exit': code, 'expected_exit': expected, 'log': str(log.relative_to(ROOT)), 'sha256': sha(log)})
    save(); print(name, code, flush=True)
    stable()
    assert code == expected, name
    assert b'WARNING: ThreadSanitizer' not in data, name
    return data.decode(errors='replace')

try:
    run('swift-version', ['xcrun', 'swiftc', '--version'])
    run('xcode-version', ['xcodebuild', '-version'])
    run('git-version', ['git', '--version'])
    run('python-version', ['python3', '--version'])
    run('platform', ['uname', '-a'])
    xctest = run('xctest-path', ['xcrun', '--find', 'xctest']).strip()
    resource = run('clang-resource', ['xcrun', 'clang', '-print-resource-dir']).strip()
    tsan = Path(resource) / 'lib/darwin/libclang_rt.tsan_osx_dynamic.dylib'
    swiftc = Path(run('swiftc-path', ['xcrun', '--find', 'swiftc']).strip())
    clang = Path(run('clang-path', ['xcrun', '--find', 'clang']).strip())
    native_archive = base_source / 'native/lib/libmixer_vm_capability_experimental.a'
    assert sha(native_archive) == base['native_archive_sha256']
    receipt['tool_files'] = {str(path): sha(path) for path in [swiftc, clang, Path(xctest), tsan]}
    receipt['native_archive'] = {'path': str(native_archive), 'sha256': sha(native_archive)}
    original_link = next(row['argv'] for row in base['commands'] if row['name'] == 'link-current-runtime')
    original_runtime = next(row['argv'] for row in base['commands'] if row['name'] == 'compile-MixerExperimentalCapabilityRuntime')
    frameworks = Path(env['DEVELOPER_DIR']) / 'Platforms/MacOSX.platform/Developer/Library/Frameworks'
    overlays = frameworks.parents[1] / 'usr/lib'
    support = source / 'verification/cold-start-cleanup-ci-repair'
    for mode in args.modes:
        products = work / mode
        products.mkdir()
        flags = ['-O'] if mode == 'release' else ['-sanitize=thread'] if mode == 'tsan' else []
        prefix = original_link[:original_link.index('-emit-library')]
        prefix = [str(products / 'swift-cache') if arg == str(base_work / 'swift-cache') else arg for arg in prefix]
        prefix[2:2] = ['-I', str(products)]
        runtime_files = []
        for path in sorted((source / runtime_prefix).glob('*.swift')):
            runtime_files.append(derived_session if path.name == 'Session.swift' else path)
        runtime_object = products / 'MixerExperimentalCapabilityRuntime.o'
        run(mode + '-runtime-link', prefix + flags + ['-whole-module-optimization', '-emit-object', '-emit-module', '-module-name', 'MixerExperimentalCapabilityRuntime', '-emit-module-path', products / 'MixerExperimentalCapabilityRuntime.swiftmodule'] + runtime_files + [support / 'NativeQueueProbe.swift', '-o', runtime_object])
        activation_files = [derived_setup if path.name == 'CapabilityConcreteAttempt.swift' else path for path in sorted((source / 'capability-activation/Sources/MixerCapabilityActivation').glob('*.swift'))]
        library = products / 'libMixerColdStartCI.dylib'
        dependencies = []
        for arg in original_link[original_link.index('-emit-library') + 1:]:
            if arg.endswith('.o') or arg.endswith('.a'):
                dependencies.append(runtime_object if arg.endswith('/MixerExperimentalCapabilityRuntime.o') else arg)
        run(mode + '-activation-link', prefix + flags + ['-emit-library', '-emit-module', '-module-name', 'MixerCapabilityActivation', '-emit-module-path', products / 'MixerCapabilityActivation.swiftmodule'] + activation_files + [support / 'SetupProbe.swift'] + dependencies + ['-Xlinker', '-install_name', '-Xlinker', '@rpath/' + library.name, '-o', library])
        for variant, (_, order, expected) in variants.items():
            bundle = products / (variant + '.xctest')
            executable = bundle / 'Contents/MacOS/MixerColdStartCITests'
            executable.parent.mkdir(parents=True)
            shutil.copytree(source / fixtures, bundle / 'Contents/Resources/Fixtures')
            (bundle / 'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable': executable.name, 'CFBundleIdentifier': 'dev.mixer.cold-start-ci.' + variant, 'CFBundlePackageType': 'BNDL', 'CFBundleVersion': '1'}))
            run(mode + '-' + variant + '-link', prefix + flags + ['-I', overlays, '-F', frameworks, '-emit-library', '-module-name', 'MixerColdStartCITests', source / ('derived/' + variant + '.swift'), support / 'TestSupport.swift', '-L', products, '-lMixerColdStartCI', '-L', overlays, '-Xlinker', '-rpath', '-Xlinker', products, '-Xlinker', '-rpath', '-Xlinker', frameworks, '-Xlinker', '-rpath', '-Xlinker', overlays, '-o', executable])
            selection = [] if order == 'unchanged' else ['-XCTest', 'MixerColdStartCITests.CapabilityColdStartRuntimeTests/testCloseDuringQueuedNativeCreationKeepsCountedOrdinaryAndAdapterTails']
            output = run(mode + '-' + variant, [xctest] + selection + [bundle], expected=expected, extra={'DYLD_INSERT_LIBRARIES': str(tsan)} if mode == 'tsan' else None)
            if expected:
                assert 'XCTAssertEqual failed' in output and 'XCTAssertTrue failed' in output
                assert 'CI_ORDER pre-admission' in output and 'pending=false submissions=0 startupReturned=true closeReturned=true queueReleased=false' in output
            elif order == 'pre-admission':
                assert 'CI_ORDER pre-admission' in output and 'pending=false submissions=0 startupReturned=true closeReturned=true queueReleased=false' in output
            elif order == 'queued':
                assert 'CI_ORDER queued' in output and 'pending=true submissions=1 startupReturned=false closeReturned=false queueReleased=false' in output
            else:
                assert 'Executed 8 tests, with 0 failures' in output
            receipt['artifacts'][mode + '-' + variant] = {'path': str(executable), 'sha256': sha(executable)}
        receipt['artifacts'][mode + '-runtime'] = {str(path): sha(path) for path in [library, runtime_object, products / 'MixerExperimentalCapabilityRuntime.swiftmodule', products / 'MixerCapabilityActivation.swiftmodule']}
        save()
    receipt['result'] = 'All selected original-fail/repaired-pass pre-admission replays, genuine queued-tail checks and unmodified repaired fixture regressions passed expected outcomes.'
except BaseException as error:
    receipt['result'] = 'Failed attempt preserved'
    receipt['problem'] = str(error)
    raise
finally:
    receipt['completed_utc'] = datetime.now(timezone.utc).isoformat()
    save()
