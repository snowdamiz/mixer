#!/usr/bin/env python3
"""Original host-only regression receipt for the opt-in Rust capability guest."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
BASE = '4e37b357ae029d9cdf5e5c6b4281d82f61b65f3a'
CONTRACT = '052ebe9fbdc20a41307332086767e7903680bc83ba273c696edf9187be6b6439'
FROZEN = ['vm/include/mixer_vm.h', 'runtime/Sources/CMixerVM/include/mixer_vm.h',
          'contracts/vm-profile-v1.json', 'contracts/vm-session-v1.json',
          'vm/profiles/numeric-v2.json', 'vm/profiles/table-memory-v3.json',
          'vm/src/ffi.rs', 'vm/src/session.rs', 'vm/src/float.rs',
          'vm/src/experimental/mod.rs']

def sha(data):
    return hashlib.sha256(data).hexdigest()

def source_manifest():
    paths = [p for p in (ROOT / 'vm').rglob('*') if p.is_file() and not
             {'target', 'verification', '__pycache__', 'capability_ffi'}.intersection(p.relative_to(ROOT / 'vm').parts)
             and p.name != '.DS_Store']
    paths += [ROOT / p for p in FROZEN if not p.startswith('vm/')]
    paths += [ROOT / p for p in ('AGENTS.md', 'mixer-product-plan.md',
        'docs/experimental-capability-guest-implementation.md', 'docs/guest-capability-abi-proposal.md',
        'contracts/guest-capability-transport-v1.json', 'capabilities/schema/hashes.json')]
    paths += [p for p in (ROOT / 'capabilities/schema').glob('*.json')]
    paths += [Path(__file__)]
    return ''.join(f'{sha(p.read_bytes())}  {p.relative_to(ROOT)}\n' for p in sorted(set(paths)))

def counts(output):
    return {'passed': sum(map(int, re.findall(r'test result: ok\. (\d+) passed;', output))),
            'ignored': sum(map(int, re.findall(r'test result: ok\..*? (\d+) ignored;', output)))}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.name):
        parser.error('name must contain only letters, digits, underscores and hyphens')
    out = ROOT / 'vm/verification/capability-guest' / args.name
    out.mkdir(parents=True, exist_ok=False)
    target = ROOT / 'vm/target/capability-guest-verification'
    env = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ.get('PATH', ''),
               CARGO_TARGET_DIR=str(target))
    receipt = {'schema_version': 1, 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'implementation_agent': {'model': 'gpt-6.1-sol', 'reasoning_effort': 'xhigh'},
        'independent_review': False, 'base_revision': BASE,
        'head_at_start': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'scope': 'macOS arm64 host; opt-in Rust-only actual Wasm/mailbox composition; no device/native I/O/release route',
        'concurrent_lane_excluded': 'root-owned vm/src/capability_ffi/** is not wired or included; no C/native follow-on claim',
        'environment': {'PATH_prefix': '/opt/homebrew/opt/rustup/bin', 'CARGO_TARGET_DIR': str(target)},
        'commands': []}
    def save():
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    def run(name, argv):
        began = time.monotonic()
        result = subprocess.run(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        log = out / (name + '.log'); log.write_text(result.stdout)
        receipt['commands'].append({'name': name, 'argv': argv, 'exit_code': result.returncode,
            'elapsed_host_development_seconds': round(time.monotonic() - began, 6),
            'log': str(log.relative_to(ROOT)), 'sha256': sha(log.read_bytes())})
        save(); print(f'{name}: exit={result.returncode}', flush=True)
        if result.returncode:
            print(result.stdout[-12000:]); raise RuntimeError(name + ' failed')
        return result.stdout
    initial = source_manifest()
    (out / 'source-manifest.sha256').write_text(initial)
    receipt['source_tree_sha256'] = sha(initial.encode())
    receipt['source_manifest'] = str((out / 'source-manifest.sha256').relative_to(ROOT))
    receipt['frozen_files'] = []
    for path in FROZEN:
        before = subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT)
        after = (ROOT / path).read_bytes()
        receipt['frozen_files'].append({'path': path, 'sha256': sha(after), 'equals_base': before == after})
        if before != after: raise RuntimeError('unexpected frozen input change: ' + path)
    # This is a field/source regression check, not executable admission evidence.
    receipt['unchanged_rust_field_definitions'] = []
    for path, marker in [('vm/src/lib.rs', 'pub enum Profile {'), ('vm/src/lib.rs', 'pub struct Limits {'),
                         ('vm/src/decode.rs', 'pub struct Module {'), ('vm/src/execute.rs', 'pub struct Instance {')]:
        old = subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT).decode()
        new = (ROOT / path).read_text()
        old = old[old.index(marker):].split('\n}', 1)[0] + '\n}'
        new = new[new.index(marker):].split('\n}', 1)[0] + '\n}'
        if old != new: raise RuntimeError('field definition changed: ' + marker)
        receipt['unchanged_rust_field_definitions'].append({'path': path, 'marker': marker, 'sha256': sha(new.encode())})
    if sha((ROOT / 'contracts/guest-capability-transport-v1.json').read_bytes()) != CONTRACT:
        raise RuntimeError('coordinated contract changed')
    receipt['transport_contract_sha256'] = CONTRACT
    receipt['versions'] = {key: run('version-' + key, argv).strip() for key, argv in {
        'rustc': ['rustc', '-Vv'], 'cargo': ['cargo', '-V'], 'clippy': ['cargo', 'clippy', '--version'],
        'node': ['node', '--version'], 'clang': ['clang', '--version'],
        'python': [sys.executable, '--version'], 'macos': ['sw_vers'], 'architecture': ['uname', '-m']}.items()}
    run('generator-parity', [sys.executable, '-B', 'vm/tools/generate-capability-terminals.py'])
    run('format', ['cargo', 'fmt', '--manifest-path', 'vm/Cargo.toml', '--check'])
    for label, feature in [('default', []), ('all', ['--all-features'])]:
        run('clippy-' + label, ['cargo', 'clippy', '--locked', '--manifest-path', 'vm/Cargo.toml', '--all-targets', *feature, '--', '-D', 'warnings'])
    base = ['cargo', 'test', '--locked', '--manifest-path', 'vm/Cargo.toml']
    receipt['test_counts'] = {}
    for label, feature in [('default', []), ('all', ['--all-features'])]:
        for build, flags in [('debug', []), ('release', ['--release'])]:
            name = label + '-' + build
            receipt['test_counts'][name] = counts(run(name, base + flags + feature + ['--', '--nocapture']))
    for build, flags in [('debug', []), ('release', ['--release'])]:
        name = 'explicit-oracles-' + build
        receipt['test_counts'][name] = counts(run(name, base + flags + ['--all-features', '--', '--ignored', '--nocapture']))
        run('guest-allocation-' + build, base + flags + ['--features', 'experimental-capability-guest', '--test', 'experimental_capability_guest_allocations', '--', '--nocapture', '--test-threads=1'])
        run('private-guest-' + build, base + flags + ['--features', 'experimental-capability-guest', '--lib', 'experimental_capability_guest', '--', '--nocapture'])
    receipt['public_symbols'] = {}; receipt['artifacts'] = {}; receipt['c_smokes'] = {}
    for label, feature in [('default', []), ('all', ['--all-features'])]:
        run(label + '-release-build', ['cargo', 'build', '--locked', '--manifest-path', 'vm/Cargo.toml', '--release', *feature])
        archive = target / 'release/libmixer_vm.a'; dynamic = target / 'release/libmixer_vm.dylib'
        receipt['artifacts'][label] = {'archive_sha256': sha(archive.read_bytes()), 'dynamic_sha256': sha(dynamic.read_bytes())}
        symbols = run(label + '-symbols', ['nm', '-gU', str(dynamic)])
        receipt['public_symbols'][label] = sorted(set(re.findall(r'\b_mixer_vm_\w+', symbols)))
        for name in ('ffi_smoke', 'ffi_numeric_smoke', 'ffi_table_memory_smoke', 'ffi_session_smoke'):
            executable = target / (label + '-' + name)
            run(label + '-' + name + '-build', ['clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-I', 'vm/include', 'vm/tests/' + name + '.c', str(archive), '-o', str(executable)])
            receipt['c_smokes'][label + '-' + name] = run(label + '-' + name + '-run', [str(executable)]).strip()
    if not receipt['public_symbols']['default'] or receipt['public_symbols']['default'] != receipt['public_symbols']['all']:
        raise RuntimeError('public C symbols changed across features')
    receipt['source_unchanged_during_checks'] = initial == source_manifest()
    if not receipt['source_unchanged_during_checks']: raise RuntimeError('scoped source changed during checks')
    receipt['allocation_scope'] = {
        'method': 'single-test processes, System GlobalAlloc requested Layout sizes; source/caller buffers/preexisting owner and VM excluded from payload intervals; realloc updates account logical live requests after realloc returns and do not measure allocator-internal overlap or RSS',
        'known_negative_boundaries': ['shared Arc allocation refusal SIGABRT', 'existing standard mutex first-lock allocation refusal SIGABRT', 'legacy core/error Strings and cancellation/owner Arcs are not end-to-end fallible'],
        'full_occupancy': {'allocations': 16, 'requested_live_bytes': 8388608, 'requested_peak_bytes': 8388608},
        'invalid_memory_full_quota_ready_poll_ack_close_drop': 'zero new allocations in measured intervals',
        'failed_argument_allocation': 'no token/request published, wrapper closed; bounded36B existing Error String allocated after refusal'}
    receipt['limits'] = ['default profiles1-3/CLI/C/session/stream routes remain Legacy and reject capability imports',
        'Rust-only explicit constructor, inherited v3 grammar/limits; no new Profile or shared process registry',
        'dynamic completion bytes remain trusted opaque data; no strict dynamic codec/grant/native I/O enforcement',
        'no automatic scheduler/Swift continuation integration; cooperative checks do not preempt a native allocation/copy',
        'native caller must retain tickets/owners through actual cleanup; poison ack fails without recovery',
        'independent review, deployment-device, compiler/fullSwift/FieldLog, immutable package, release/store/operations/GA gates remain open']
    receipt['full_fieldlog_admitted_or_executed'] = False
    receipt['completed_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt['result'] = 'scoped host checks passed; independent review and all integration gates pending'
    save()

if __name__ == '__main__':
    main()
