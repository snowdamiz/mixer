#!/usr/bin/env python3
"""Host-only verification; records evidence without editing engine source."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
ENV = dict(os.environ)
ENV['PATH'] = '/opt/homebrew/opt/rustup/bin:' + ENV['PATH']
ENV['CARGO_TARGET_DIR'] = '/tmp/mixer-capability-mailbox-2026-10-22-target'
receipt = {
    'schema': 1,
    'scope': 'nondefault standalone Rust mailbox host tests; no guest/C/native/activation/release/device admission',
    'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'cwd': str(ROOT),
    'base_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'environment': {key: ENV[key] for key in ('PATH', 'CARGO_TARGET_DIR')},
    'commands': [],
}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def command(name, args):
    start = time.monotonic()
    log = OUT / (name + '.log')
    with log.open('w') as handle:
        result = subprocess.run(args, cwd=ROOT, env=ENV, stdout=handle, stderr=subprocess.STDOUT)
    entry = {'name': name, 'argv': args, 'exit_code': result.returncode,
             'seconds': round(time.monotonic() - start, 3), 'log': str(log.relative_to(ROOT)),
             'log_sha256': digest(log)}
    receipt['commands'].append(entry)
    print(f'{name}: exit={result.returncode}; {entry["seconds"]}s', flush=True)
    save()
    if result.returncode:
        print(log.read_text()[-12000:], flush=True)
        raise SystemExit(result.returncode)

def save():
    (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

sources = [ROOT / 'vm' / 'Cargo.toml', ROOT / 'vm' / 'Cargo.lock']
for folder in ('vm/src', 'vm/tests', 'vm/include', 'vm/profiles'):
    sources += [p for p in (ROOT / folder).rglob('*') if p.is_file()]
sources += [ROOT / p for p in ('AGENTS.md', 'mixer-product-plan.md',
    'docs/guest-capability-abi-proposal.md', 'contracts/vm-profile-v1.json',
    'contracts/vm-session-v1.json', 'runtime/Sources/CMixerVM/include/mixer_vm.h')]
sources = sorted(set(sources))
manifest = ''.join(f'{digest(path)}  {path.relative_to(ROOT)}\n' for path in sources)
(OUT / 'source-manifest.sha256').write_text(manifest)
receipt['source_tree_sha256'] = hashlib.sha256(manifest.encode()).hexdigest()
receipt['source_manifest'] = 'vm/verification/capability-mailbox/source-manifest.sha256'
receipt['source_file_count'] = len(sources)
receipt['verification_driver'] = {'path': 'vm/verification/capability-mailbox/verify.py', 'sha256': digest(Path(__file__))}
frozen = [p for p in sources if str(p.relative_to(ROOT)) in (
    'vm/src/decode.rs', 'vm/src/execute.rs', 'vm/src/float.rs', 'vm/src/validate.rs',
    'vm/src/ffi.rs', 'vm/src/session.rs', 'vm/include/mixer_vm.h',
    'runtime/Sources/CMixerVM/include/mixer_vm.h', 'contracts/vm-profile-v1.json',
    'contracts/vm-session-v1.json') or 'vm/profiles/' in str(p.relative_to(ROOT))]
receipt['frozen_inputs'] = []
for path in frozen:
    relative = str(path.relative_to(ROOT))
    baseline = subprocess.check_output(['git', 'show', f'{receipt["base_revision"]}:{relative}'], cwd=ROOT)
    receipt['frozen_inputs'].append({'path': relative, 'sha256': digest(path),
        'equals_base_revision': baseline == path.read_bytes()})
assert all(item['equals_base_revision'] for item in receipt['frozen_inputs'])
receipt['known_limitations'] = [
    'macOS std mutex first-lock allocator refusal aborts; negative child transcript expected in allocation logs',
    'typed Rust failures and opaque bytes are not the proposed strict wire payload',
    'caller must retain mailbox through exit ack; no process/session registry ceiling integration',
    'no Wasm imports/profile, C ABI/panic guarantee, fuel/byte charging, native/grant/scheduler or release admission',
    'host-only tests do not qualify physical iOS/Android, compiler, immutable packages, store, operations or GA',
]
save()
for name, args in (
    ('rustc', ['rustc', '-Vv']), ('cargo', ['cargo', '-V']),
    ('rustfmt', ['rustfmt', '--version']), ('clippy-version', ['cargo', 'clippy', '--version']),
    ('node', ['node', '--version']), ('python', [sys.executable, '--version']),
    ('host', ['uname', '-a']), ('macos', ['sw_vers']), ('git', ['git', '--version']),
):
    command('version-' + name, args)
command('format', ['cargo', 'fmt', '--manifest-path', 'vm/Cargo.toml', '--check'])
command('clippy', ['cargo', 'clippy', '--locked', '--manifest-path', 'vm/Cargo.toml', '--all-targets', '--all-features', '--', '-D', 'warnings'])
base = ['cargo', 'test', '--locked', '--manifest-path', 'vm/Cargo.toml']
command('default-debug', base)
command('default-release', base + ['--release'])
features = ['--features', 'experimental-capability-mailbox,experimental-stream-validation']
command('combined-debug', base + features)
command('combined-release', base + ['--release'] + features)
command('combined-ignored-debug', base + features + ['--', '--ignored'])
command('combined-ignored-release', base + ['--release'] + features + ['--', '--ignored'])
for profile in ('debug', 'release'):
    command('allocation-' + profile, base + ([] if profile == 'debug' else ['--release']) +
        ['--features', 'experimental-capability-mailbox', '--test', 'experimental_capability_allocations', '--', '--nocapture', '--test-threads=1'])
current = ''.join(f'{digest(path)}  {path.relative_to(ROOT)}\n' for path in sources)
receipt['source_unchanged_during_checks'] = current == manifest
assert receipt['source_unchanged_during_checks']
receipt['completed_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
receipt['result'] = 'host checks passed; all integration and qualification limitations remain open'
save()
