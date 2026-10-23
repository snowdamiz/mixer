#!/usr/bin/env python3
"""Capture source-bound native evidence for the private accounted WASI seam."""
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = pathlib.Path(__file__).resolve().parent
RUST = pathlib.Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
OUT = BASE / (sys.argv[1] if len(sys.argv) > 1 else 'final')
OUT.mkdir(parents=True, exist_ok=True)
ENV = dict(os.environ, PATH=str(RUST) + ':' + os.environ.get('PATH', ''))
COMMANDS = []


def digest(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def sources():
    paths = list((ROOT / 'vm/src').rglob('*.rs'))
    paths += [ROOT / value for value in [
        'AGENTS.md', 'vm/Cargo.toml', 'vm/Cargo.lock',
        'docs/swift-reactor-execution-stage-design.md',
        'verification/swift-reactor-execution-contract-acceptance.json',
        'verification/swift-runtime-control-root-review/receipt.json',
        'verification/swift-accounted-wasi/verify.py',
        'verification/swift-accounted-wasi/layout_probe.rs',
    ]]
    entries = [digest(path) for path in sorted(paths) if path.is_file()]
    encoded = json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()
    return {'files': entries, 'source_tree_sha256': hashlib.sha256(encoded).hexdigest()}


def run(label, argv):
    start = time.monotonic()
    result = subprocess.run([str(item) for item in argv], cwd=ROOT, env=ENV, capture_output=True)
    stdout = OUT / (label + '.stdout')
    stderr = OUT / (label + '.stderr')
    stdout.write_bytes(result.stdout)
    stderr.write_bytes(result.stderr)
    item = {'label': label, 'argv': [str(item) for item in argv], 'cwd': str(ROOT),
            'exit_code': result.returncode, 'elapsed_seconds': time.monotonic() - start,
            'stdout': digest(stdout), 'stderr': digest(stderr)}
    COMMANDS.append(item)
    print(json.dumps({'label': label, 'exit_code': result.returncode, 'seconds': item['elapsed_seconds']}), flush=True)
    return result


before = sources()
(OUT / 'source-before.json').write_text(json.dumps(before, indent=2) + '\n')
revision_before = run('revision-before', ['git', 'rev-parse', 'HEAD']).stdout.decode().strip()
run('rustc-version', [RUST / 'rustc', '--version', '--verbose'])
run('cargo-version', [RUST / 'cargo', '--version'])
run('python-version', [sys.executable, '--version'])
run('format', [RUST / 'rustfmt', '--check', '--edition', '2021',
               'vm/src/experimental_wasi/accounted.rs', 'vm/src/experimental_wasi/accounted_tests.rs',
               'verification/swift-accounted-wasi/layout_probe.rs'])
run('clippy-library', [RUST / 'cargo', 'clippy', '--manifest-path', 'vm/Cargo.toml', '--all-features', '--lib', '--', '-D', 'warnings'])
observations = {}
for mode in ['debug', 'release']:
    release = ['--release'] if mode == 'release' else []
    run(mode + '-all-feature-library', [RUST / 'cargo', 'test', '--manifest-path', 'vm/Cargo.toml', '--all-features', '--lib', *release, '--', '--nocapture'])
    run(mode + '-standalone-library', [RUST / 'cargo', 'test', '--manifest-path', 'vm/Cargo.toml', '--features', 'experimental-swift-wasi', '--lib', *release, '--', '--nocapture'])
    for feature in ['experimental-swift-wasi', 'experimental-swift-reactor']:
        label = mode + '-' + feature
        built = run(label + '-build', [RUST / 'cargo', 'build', '--manifest-path', 'vm/Cargo.toml', '--features', feature, '--lib', *release])
        if built.returncode:
            continue
        binary = OUT / (label + '-probe')
        compiled = run(label + '-compile-probe', [RUST / 'rustc', '--edition', '2021',
            BASE / 'layout_probe.rs', '--extern', 'mixer_vm=' + str(ROOT / 'vm/target' / mode / 'libmixer_vm.rlib'),
            '-L', 'dependency=' + str(ROOT / 'vm/target' / mode / 'deps'), '-o', binary])
        if compiled.returncode:
            continue
        observed = run(label + '-probe', [binary])
        if observed.returncode == 0:
            observations[label] = json.loads(observed.stdout)
        binary.unlink(missing_ok=True)

baseline = json.loads((BASE / 'baseline/source.json').read_text())
current = (ROOT / 'vm/src/experimental_wasi/mod.rs').read_text()
wiring = '#[cfg(feature = "experimental-swift-reactor")]\npub(crate) mod accounted;\n'
frozen_old_wasi = current.count(wiring) == 1 and current.replace(wiring, '') == baseline['standalone_wasi_source']
frozen_old_tests = digest(ROOT / 'vm/src/experimental_wasi/tests.rs')['sha256'] == baseline['files']['vm/src/experimental_wasi/tests.rs']
revision_after = run('revision-after', ['git', 'rev-parse', 'HEAD']).stdout.decode().strip()
after = sources()
(OUT / 'source-after.json').write_text(json.dumps(after, indent=2) + '\n')
stable = before == after
equivalent = len(observations) == 4 and len({json.dumps(item, sort_keys=True) for item in observations.values()}) == 1
success = all(item['exit_code'] == 0 for item in COMMANDS) and stable and revision_before == revision_after and frozen_old_wasi and frozen_old_tests and equivalent
receipt = {
    'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'scope': 'Private Rust-only accounted WASI prerequisite; original same-full-ABI synthetic proof is consumed, no reactor instantiation or execution.',
    'success': success, 'revision_before': revision_before, 'revision_after': revision_after,
    'source_stable': stable, 'revision_stable': revision_before == revision_after,
    'source_tree_sha256': before['source_tree_sha256'],
    'source_manifest': digest(OUT / 'source-before.json'),
    'commands': COMMANDS,
    'toolchain_files': [digest(RUST / tool) if RUST.is_relative_to(ROOT) else {'path': str(RUST / tool), 'bytes': (RUST / tool).stat().st_size, 'sha256': hashlib.sha256((RUST / tool).read_bytes()).hexdigest()} for tool in ['rustc', 'cargo', 'rustfmt', 'clippy-driver']],
    'frozen_standalone_source_exact_except_additive_private_module_wiring': frozen_old_wasi,
    'frozen_standalone_tests_exact': frozen_old_tests,
    'standalone_debug_release_feature_observations_equal': equivalent,
    'standalone_observations': observations,
    'verified_scope': [
        'Four shared-ledger exact-capacity admissions precede actual buffer allocation; fixed owner and inline ticket/Option sizes included once in persistent WASI header.',
        'Borrowed one-shot constructor phase enlarges existing shared ticket before new wrappers and only caller completion restores the exact prior bound after construct returns.',
        'All four actual allocator null failures and every before/after constructor allocation cancellation/deadline ordinal drop actual partial storage before refunds.',
        'Unchanged WASI counters remain sole active authority; closed owner pairs dispatch to its sealed control and advances runtime host count on entry only.',
        'Exact errno, WASI terminal data and GuestExit including code zero; sticky future calls and cleanup need no allocation, work or services.',
        'Same cancellation backing and earliest carried deadline occupy actual unchanged context fields; internal context check/commit enforce deadline.',
        'Actual native OS random and clocks, default denials, captures and standalone deterministic counter/memory equality are exercised.',
    ],
    'limitations': [
        'No Swift executable owner, cache/executor composition, target 53MB reactor instantiation/initialize/invoke, or corpus qualification.',
        'Host native Debug/Release evidence does not qualify physical iOS/Android, signing, stores, publication, immutable separate-repository FieldLog consumption, operational review or GA.',
        'Logical requested capacities and named conservative wrapper/scratch reservations exclude allocator overhead, RSS and compiler stack measurement.',
        'Cancellation/deadline are cooperative; individual allocation/platform calls are not preempted.',
        'Constructor fault hooks exist only under cfg(test); there is no public service injection.',
        'Unexpected-capacity failure policy is exercised with actual mismatched Vec storage separately; the native allocator returned all requested constructor capacities exactly.',
    ],
}
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'success': success, 'receipt': str(OUT / 'receipt.json'), 'source_stable': stable, 'standalone_source_exact': frozen_old_wasi, 'standalone_observations_equal': equivalent}), flush=True)
sys.exit(0 if success else 1)
