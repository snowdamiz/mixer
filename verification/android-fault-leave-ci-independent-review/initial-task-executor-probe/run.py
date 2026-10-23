#!/usr/bin/env python3
"""Independent actual Swift/C ordering probe, built only in a private copied tree."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPAIR = ROOT / 'verification/android-fault-leave-ci-repair'
BUILD = HERE / 'build/corrected'
SOURCE = BUILD / 'source'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def require(c, message):
    if not c:
        raise RuntimeError(message)

def main():
    require(not BUILD.exists(), 'Use a fresh independent build directory')
    baseline_path = REPAIR / 'debug-receipt.json'
    baseline = json.loads(baseline_path.read_text())
    require(baseline['status'] == 'passed', 'Expected completed fresh-source baseline')
    baseline_source = REPAIR / 'build/fresh-debug/source'
    for relative, digest in baseline['input_files'].items():
        require(sha(ROOT / relative) == digest, 'Current input changed: ' + relative)
    SOURCE.mkdir(parents=True)
    for relative, digest in baseline['source_files'].items():
        src = baseline_source / relative
        require(sha(src) == digest, 'Baseline snapshot mismatch: ' + relative)
        dst = SOURCE / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    modifications = {}
    def overlay(relative, transformed):
        p = SOURCE / relative
        before = p.read_text()
        after = transformed(before)
        require(before != after, 'Overlay did not change expected file: ' + relative)
        p.write_text(after)
        patch = HERE / (Path(relative).name + '.patch')
        patch.write_text(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                                    fromfile='original/' + relative, tofile='review/' + relative)))
        modifications[relative] = {'before': hashlib.sha256(before.encode()).hexdigest(), 'after': sha(p),
                                   'patch': str(patch.relative_to(ROOT)), 'patch_sha256': sha(patch)}
    overlay('Harness/HostTests.swift', lambda _: (HERE / 'probe.swift').read_text())
    overlay('verification/android-binding-stage4/host-bridge/host_test.h', lambda s: s.replace(
        '#endif', 'void mxish_review_arm_completion(uint64_t owner);\n'
        'int32_t mxish_review_wait_completion(void);\n'
        'void mxish_review_release_completion(void);\n#endif'))
    overlay('verification/android-binding-stage4/host-bridge/host_bridge.c',
            lambda s: s + '\n' + (HERE / 'complete_barrier.c').read_text())
    overlay('capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIAndroidProgress.swift',
            lambda s: s.replace('@_cdecl("mxuit_complete")',
                '@_silgen_name("mxish_review_complete_checkpoint")\n'
                'private func reviewCompletionCheckpoint(_ owner: UInt64)\n\n@_cdecl("mxuit_complete")').replace(
                '    CapabilityAndroidRegistry.shared.control(owner: owner)?.complete(waiter: waiter, kind: kind, result: result)',
                '    reviewCompletionCheckpoint(owner) // Observation barrier only; actual completion follows.\n'
                '    CapabilityAndroidRegistry.shared.control(owner: owner)?.complete(waiter: waiter, kind: kind, result: result)'))
    snapshot = {str(p.relative_to(SOURCE)): sha(p) for p in sorted(SOURCE.rglob('*')) if p.is_file()}
    receipt = {'started_utc': datetime.now(timezone.utc).isoformat(),
        'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'baseline_receipt': str(baseline_path.relative_to(ROOT)), 'baseline_receipt_sha256': sha(baseline_path),
        'baseline_inputs': baseline['input_files'], 'baseline_source_tree_sha256': baseline['source_tree_sha256'],
        'overlays': modifications, 'copied_source_files': snapshot,
        'copied_source_tree_sha256': hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest(),
        'review_inputs': {p.name: sha(p) for p in [Path(__file__), HERE / 'probe.swift', HERE / 'complete_barrier.c']},
        'native_source_revision': baseline['native_source_revision'], 'native_inputs': baseline['native_inputs'],
        'native_receipt': baseline['native_receipt'], 'native_receipt_sha256': baseline['native_receipt_sha256'],
        'commands': [], 'status': 'running',
        'scope': 'Private actual Swift/C binding build with observation-only completion barrier and actual Swift Task executor. '
        'Original transport.c and binding lifecycle otherwise unchanged. The two schedules prove causality, not the exact sparse hosted failure. '
        'Native Rust archive is receipt-bound reused d814055 and is not TSan instrumented. Host ordering only; no device/JNI/release/GA authority.'}
    def save():
        (HERE / 'probe-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    def run(label, argv, timeout=900):
        start = time.monotonic()
        try:
            r = subprocess.run([str(a) for a in argv], cwd=SOURCE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=timeout)
            output, code = r.stdout, r.returncode
        except subprocess.TimeoutExpired as e:
            output, code = (e.stdout or b'') + b'\nTIMEOUT\n', 124
        path = HERE / (label + '.log')
        path.write_bytes(output)
        receipt['commands'].append({'name': label, 'argv': [str(a) for a in argv], 'cwd': str(SOURCE),
            'environment': {k: os.environ[k] for k in ['DEVELOPER_DIR', 'TOOLCHAINS'] if k in os.environ},
            'exit': code, 'seconds': time.monotonic() - start, 'log': str(path.relative_to(ROOT)), 'sha256': sha(path)})
        save()
        print(label, code, flush=True)
        require(code == 0 and b'WARNING: ThreadSanitizer' not in output, 'Command failed: ' + label)
        return output.decode()
    save()
    try:
        run('swift-version', ['xcrun', 'swift', '--version'])
        run('clang-version', ['xcrun', 'clang', '--version'])
        run('platform', ['uname', '-a'])
        native = Path(baseline['native_receipt']).parent
        for relative, digest in baseline['native_inputs'].items():
            require(sha(Path(relative)) == digest, 'Native input mismatch: ' + relative)
        for mode, flags in [('debug', ['-c', 'debug']), ('release', ['-c', 'release']),
                            ('tsan', ['-c', 'debug', '--sanitize', 'thread'])]:
            scratch = BUILD / mode
            build = ['xcrun', 'swift', 'build', '--package-path', SOURCE, '--scratch-path', scratch,
                '--force-resolved-versions', *flags, '--product', 'Stage4HostTests',
                '-Xswiftc', '-enable-testing', '-Xswiftc', '-warnings-as-errors',
                '-Xcc', '-I' + str(native / 'include'), '-Xlinker', '-L' + str(native / 'lib'),
                '-Xswiftc', '-Xcc', '-Xswiftc', '-fmodule-map-file=' + str(SOURCE / 'verification/android-binding-stage4/host-bridge/test.modulemap')]
            run(mode + '-build', build)
            bin_path = run(mode + '-bin-path', ['xcrun', 'swift', 'build', '--package-path', SOURCE,
                '--scratch-path', scratch, *flags, '--show-bin-path']).strip().splitlines()[-1]
            exe = Path(bin_path) / 'Stage4HostTests'
            receipt.setdefault('executables', {})[mode] = {'path': str(exe), 'sha256': sha(exe)}
            for case in ['old', 'fixed']:
                output = run(mode + '-' + case, [exe, case], timeout=90)
                require('REVIEW_PASS ' + case in output, 'Missing exact success marker')
            # Bind every remote dependency to its resolved lock and clean checkout.
            pins = {pin['identity']: pin for pin in json.loads((SOURCE / 'Package.resolved').read_text())['pins']}
            workspace = json.loads((scratch / 'workspace-state.json').read_text())['object']
            checked = {}
            for dep in workspace['dependencies']:
                ref = dep['packageRef']
                if ref['kind'] == 'fileSystem':
                    continue
                identity = ref['identity']; pin = pins[identity]
                require(ref['kind'] == 'remoteSourceControl' and ref['location'] == pin['location'] and
                        dep['state']['checkoutState'] == pin['state'], 'Dependency resolution changed')
                checkout = scratch / 'checkouts' / dep['subpath']
                revision = run(mode + '-' + identity + '-revision', ['git', '-C', checkout, 'rev-parse', 'HEAD']).strip()
                status = run(mode + '-' + identity + '-status', ['git', '-C', checkout, 'status', '--porcelain', '--untracked-files=all'])
                require(revision == pin['state']['revision'] and not status.strip(), 'Dirty/unpinned dependency')
                checked[identity] = {'revision': revision, 'version': pin['state']['version'], 'location': pin['location']}
            require(set(checked) == set(pins), 'Dependency set differs')
            receipt.setdefault('dependency_checkouts', {})[mode] = checked
        for relative, digest in snapshot.items():
            require(sha(SOURCE / relative) == digest, 'Copied source changed: ' + relative)
        for relative, digest in baseline['input_files'].items():
            require(sha(ROOT / relative) == digest, 'Current source changed: ' + relative)
        for relative, digest in baseline['native_inputs'].items():
            require(sha(Path(relative)) == digest, 'Native input changed')
        receipt['status'] = 'passed'
    except BaseException as error:
        receipt['status'] = 'failed'; receipt['error'] = str(error)
        raise
    finally:
        receipt['completed_utc'] = datetime.now(timezone.utc).isoformat(); save()

if __name__ == '__main__':
    main()
