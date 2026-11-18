#!/usr/bin/env python3
"""Rebuild the private Android host binding without retained local Swift objects."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = (
    'smoke prebind single-join destructor helper-alias fallback late-before late-after '
    'after-reclaim terminal-capacity failed-retire missing-native capacity '
    'facade-acquire-failure endpoint-acquire-failure bind-failure cancelled-preparation '
    'nested fault-leave fault-read fault-write cleanup-exhaustion c-facade-exhaustion '
    'cycles drop-prepared drop-transferred drop-bound-late fallback-ids leased-ingress '
    'partial-retire wrong-final-owner close-before-bind late-progress-fault '
    'rendezvous-reuse queued-close terminal-retire-failure cleanup-wrong-endpoint '
    'cleanup-wrong-lifetime cleanup-wrong-facade'
).split()

PACKAGE = '''// swift-tools-version: 6.2
import PackageDescription
let package = Package(
    name: "MixerAndroidBindingHostChecks",
    platforms: [.macOS(.v14)],
    products: [.executable(name: "Stage4HostTests", targets: ["Stage4HostTests"])],
    dependencies: [
        .package(path: "experimental-capability-runtime"),
        .package(path: "runtime-identity"),
        .package(path: "updates"),
        .package(path: "sdk"),
    ],
    targets: [
        .target(name: "CMixerUITransport", path: ".",
            sources: ["native/android/signed-guest-ui/transport/transport.c"],
            publicHeadersPath: "native/android/signed-guest-ui/binding/include",
            cSettings: [.define("MIXER_UI_TRANSPORT_TESTING")]),
        .target(name: "CMixerUIAndroidHostBridge", dependencies: ["CMixerUITransport"],
            path: "verification/android-binding-stage4/host-bridge",
            sources: ["host_bridge.c"], publicHeadersPath: ".",
            cSettings: [.define("MIXER_UI_TRANSPORT_TESTING")]),
        .target(name: "MixerCapabilityDurableIO",
            path: "capability-activation/Sources/MixerCapabilityDurableIO"),
        .target(name: "MixerCapabilityActivation", dependencies: [
            "MixerCapabilityDurableIO", "CMixerUITransport", "CMixerUIAndroidHostBridge",
            .product(name: "MixerExperimentalCapabilityRuntime", package: "experimental-capability-runtime"),
            .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
            .product(name: "MixerUpdates", package: "updates"),
            .product(name: "MixerCapabilities", package: "sdk"),
            .product(name: "MixerGuest", package: "sdk"),
            .product(name: "MixerUI", package: "sdk"),
            .product(name: "MixerApple", package: "sdk"),
        ], path: "capability-activation/Sources/MixerCapabilityActivation"),
        .executableTarget(name: "Stage4HostTests", dependencies: [
            "MixerCapabilityActivation", "CMixerUITransport", "CMixerUIAndroidHostBridge",
            .product(name: "MixerGuest", package: "sdk"),
            .product(name: "MixerUI", package: "sdk"),
        ], path: "Harness"),
    ],
    swiftLanguageModes: [.v6]
)
'''

def require(condition, message):
    # These are verification gates, so python -O must not disable them.
    if not condition:
        raise RuntimeError(message)


def dependency_checkouts(source, build, run, prefix='dependency'):
    pins = {pin['identity']: pin for pin in json.loads((source / 'Package.resolved').read_text())['pins']}
    workspace = json.loads((build / 'workspace-state.json').read_text())['object']
    result = {}
    for dependency in workspace['dependencies']:
        reference = dependency['packageRef']
        if reference['kind'] == 'fileSystem':
            continue
        identity = reference['identity']
        require(identity not in result, 'Duplicate dependency checkout: ' + identity)
        require(identity in pins and reference['kind'] == 'remoteSourceControl',
                'Unpinned dependency: ' + identity)
        pin = pins[identity]
        require(reference['location'] == pin['location'], 'Dependency origin changed: ' + identity)
        state = dependency['state']['checkoutState']
        require(state == pin['state'], 'Dependency resolution changed: ' + identity)
        checkout = build / 'checkouts' / dependency['subpath']
        revision = run(prefix + '-' + identity + '-revision',
                       ['git', '-C', checkout, 'rev-parse', 'HEAD']).strip()
        status = run(prefix + '-' + identity + '-status',
                     ['git', '-C', checkout, 'status', '--porcelain', '--untracked-files=all'])
        require(revision == pin['state']['revision'], 'Dependency checkout revision changed: ' + identity)
        require(not status.strip(), 'Dependency checkout is dirty: ' + identity)
        result[identity] = {'location': reference['location'], 'revision': revision,
                            'version': state['version'], 'status': status}
    require(set(result) == set(pins), 'Resolved dependency set differs from Package.resolved')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['debug', 'release', 'tsan'], default='debug')
    parser.add_argument('--native-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-native-revision', help='Require the supplied VM archive to use this source commit')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = out / 'source'
    source.mkdir()
    logs = out / 'logs'
    logs.mkdir()
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    native = args.native_root.resolve()
    native_receipt = json.loads((native / 'receipt.json').read_text())
    require(native_receipt['target_selector'] == 'host', 'A host capability VM is required')
    require(native_receipt['feature'] == 'experimental-capability-native', 'Capability VM feature required')
    if args.expected_native_revision:
        require(native_receipt['source_revision'] == args.expected_native_revision, 'Native VM source revision differs')
    require(set(native_receipt['headers']) == {'mixer_vm.h', 'mixer_vm_capability.h', 'mixer_vm_guest_ui.h'},
            'The complete capability VM header set is required')
    native_inputs = {}
    archive = native / 'lib' / 'libmixer_vm_capability_experimental.a'
    require(digest(archive) == native_receipt['library']['sha256'], 'Native VM archive digest differs')
    native_inputs[str(archive)] = digest(archive)
    for name, entry in native_receipt['headers'].items():
        path = native / 'include' / name
        require(digest(path) == entry['sha256'], 'Native header digest differs: ' + name)
        native_inputs[str(path)] = digest(path)
    # Copy tracked dependency source/resources, including tests declared by each
    # package. Never consume a developer's retained .build or verification tree.
    paths = set()
    for package in ['experimental-capability-runtime', 'runtime-identity', 'updates', 'sdk']:
        listed = subprocess.check_output(['git', 'ls-files', '--', package], cwd=ROOT, text=True).splitlines()
        for relative in listed:
            suffix = relative[len(package) + 1:]
            if suffix in ['Package.swift', 'Package.resolved'] or suffix.startswith(('Sources/', 'Tests/')):
                paths.add(relative)
    for directory in ['capability-activation/Sources', 'native/android/signed-guest-ui/binding/include']:
        paths.update(str(p.relative_to(ROOT)) for p in (ROOT / directory).rglob('*') if p.is_file())
    paths.update('native/android/signed-guest-ui/transport/' + p for p in ['transport.c', 'internal.h', 'include/mixer_ui_transport.h'])
    fixture = 'verification/android-binding-stage4/'
    paths.update(fixture + p for p in ['HostEntry.swift', 'HostTests.swift', 'HoldingExecutor.swift'])
    paths.update(fixture + 'host-bridge/' + p for p in ['host_bridge.c', 'mixer_android_host_bridge.h', 'host_test.h', 'module.modulemap', 'test.modulemap'])
    paths.add('capability-activation/Package.resolved')
    inputs = {relative: digest(ROOT / relative) for relative in sorted(paths)}
    for relative in inputs:
        destination = source / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
        require(digest(destination) == inputs[relative] == digest(ROOT / relative), 'Source changed while copying: ' + relative)
    shutil.copyfile(source / (fixture + 'HostEntry.swift'), source / 'capability-activation/Sources/MixerCapabilityActivation/Stage4HostEntry.swift')
    (source / 'Harness').mkdir()
    for name in ['HostTests.swift', 'HoldingExecutor.swift']:
        shutil.copyfile(source / (fixture + name), source / 'Harness' / name)
    shutil.copyfile(source / 'capability-activation/Package.resolved', source / 'Package.resolved')
    (source / 'Package.swift').write_text(PACKAGE)
    snapshot = {str(p.relative_to(source)): digest(p) for p in sorted(source.rglob('*')) if p.is_file()}
    receipt = {
        'started_utc': datetime.now(timezone.utc).isoformat(), 'mode': args.mode,
        'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'runner_sha256': digest(Path(__file__)), 'input_files': inputs,
        'source_files': snapshot,
        'source_tree_sha256': hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest(),
        'native_receipt': str(native / 'receipt.json'), 'native_receipt_sha256': digest(native / 'receipt.json'),
        'native_source_revision': native_receipt['source_revision'],
        'native_inputs': native_inputs, 'commands': [], 'cases_executed': [],
        'scope': 'Fresh SwiftPM build of copied actual production Swift/C, fixed host fixture and existing SDK dependencies. Ordinary host scenarios only; no literal debugger matrix, JNI/Looper/device/signed-UI/release/GA qualification. The real receipt-bound Rust archive is not rebuilt or TSan-instrumented by this runner.',
        'status': 'running',
    }
    def save():
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    def run(label, argv, timeout=900):
        started = time.monotonic()
        try:
            result = subprocess.run([str(x) for x in argv], cwd=source, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=timeout)
            output, code = result.stdout, result.returncode
        except subprocess.TimeoutExpired as error:
            output, code = (error.stdout or b'') + b'\nTIMEOUT\n', 124
        log = logs / (label + '.log')
        log.write_bytes(output)
        receipt['commands'].append({'name': label, 'argv': [str(x) for x in argv], 'cwd': str(source),
                                    'environment': {k: os.environ[k] for k in ['DEVELOPER_DIR', 'TOOLCHAINS'] if k in os.environ},
                                    'exit': code, 'seconds': time.monotonic() - started,
                                    'log': str(log), 'sha256': digest(log)})
        save()
        print(label, code, flush=True)
        if code:
            raise RuntimeError(f'{label} failed; inspect {log}')
        return output.decode()
    save()
    try:
        run('swift-version', ['xcrun', 'swift', '--version'])
        run('clang-version', ['xcrun', 'clang', '--version'])
        mode_flags = ['-c', 'release'] if args.mode == 'release' else ['-c', 'debug']
        if args.mode == 'tsan':
            mode_flags += ['--sanitize', 'thread']
        build = ['xcrun', 'swift', 'build', '--package-path', str(source), '--scratch-path', str(out / 'build'),
                 '--force-resolved-versions', *mode_flags, '--product', 'Stage4HostTests',
                 '-Xswiftc', '-enable-testing', '-Xswiftc', '-warnings-as-errors',
                 '-Xcc', '-I' + str(native / 'include'), '-Xlinker', '-L' + str(native / 'lib'),
                 '-Xswiftc', '-Xcc', '-Xswiftc', '-fmodule-map-file=' + str(source / (fixture + 'host-bridge/test.modulemap'))]
        run('fresh-build', build)
        receipt['dependency_checkouts'] = dependency_checkouts(source, out / 'build', run)
        bin_path = run('bin-path', ['xcrun', 'swift', 'build', '--package-path', str(source), '--scratch-path', str(out / 'build'), *mode_flags, '--show-bin-path']).strip().splitlines()[-1]
        executable = Path(bin_path) / 'Stage4HostTests'
        receipt['executable'] = {'path': str(executable), 'sha256': digest(executable)}
        for scenario in SCENARIOS:
            output = run(scenario, [executable, scenario], timeout=180)
            require(('HOST_PASS ' + scenario) in output.splitlines(), 'Missing exact success marker: ' + scenario)
            receipt['cases_executed'].append(scenario)
            save()
        require(all(digest(source / p) == h for p, h in snapshot.items()), 'Snapshot source changed')
        require(all(digest(Path(p)) == h for p, h in native_inputs.items()), 'Native input changed')
        require(digest(native / 'receipt.json') == receipt['native_receipt_sha256'], 'Native receipt changed')
        require(digest(Path(__file__)) == receipt['runner_sha256'], 'Verification runner changed')
        require(dependency_checkouts(source, out / 'build', run, 'final-dependency') == receipt['dependency_checkouts'],
                'Dependency checkouts changed')
        receipt['status'] = 'passed'
    except BaseException as error:
        receipt['status'] = 'failed'
        receipt['error'] = str(error)
        raise
    finally:
        receipt['completed_utc'] = datetime.now(timezone.utc).isoformat()
        save()

if __name__ == '__main__':
    main()
