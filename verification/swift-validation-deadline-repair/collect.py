#!/usr/bin/env python3
"""Freeze and exercise only the real-deadline allocation test repair."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--name', required=True)
name = parser.parse_args().name
assert name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in name)
out = HERE / name
out.mkdir(exist_ok=False)
work = HERE / '.build' / name
source = work / 'source'
source.mkdir(parents=True, exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
revision = '39199ae5475de5d03926807ce60add5dcb0741c2'
raw = subprocess.check_output(['git', 'archive', revision, 'vm'], cwd=ROOT)
with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
    tar.extractall(source, filter='data')
overlay = 'vm/tests/swift_reactor_validation_allocations.rs'
(source / overlay).write_bytes((ROOT / overlay).read_bytes())
manifest = {str(p.relative_to(source)): sha(p) for p in sorted((source / 'vm').rglob('*')) if p.is_file()}
for relative in manifest:
    (source / relative).chmod(0o444)
archive = out / 'source.tar.gz'
with tarfile.open(archive, 'w:gz') as tar:
    tar.add(source / 'vm', arcname='vm')
env = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'], CARGO_TARGET_DIR=str(work / 'target'))
receipt = {
    'started_utc': datetime.now(timezone.utc).isoformat(),
    'base_revision': revision, 'overlays': [overlay],
    'collector_sha256': sha(Path(__file__)),
    'source_files': manifest,
    'source_tree_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
    'source_archive': str(archive.relative_to(ROOT)), 'source_archive_sha256': sha(archive),
    'commands': [],
    'scope': 'Only test timing resilience: every allocation ordinal still must actually enter its injected real-clock delay, fail with Deadline, make exactly ordinal allocations, and clean without leaks or reallocations. Deterministic zero-budget early expiry, successful retry, and bounded exhaustion run in the same original observer lane. No runtime or validation budget change; no active cache/Android sources, physical devices, full target execution or GA acceptance.',
}
commands = [('rust-version', ['rustc', '-Vv']), ('cargo-version', ['cargo', '-V']), ('format', ['rustfmt', '--edition', '2021', '--check', '--config', 'skip_children=true', overlay])]
for mode in ['debug', 'release']:
    flags = ['--release'] if mode == 'release' else []
    base = ['cargo', 'test', '--locked', '--manifest-path', 'vm/Cargo.toml', *flags, '--features', 'experimental-swift-reactor', '--test', 'swift_reactor_validation_allocations', '--', '--nocapture']
    commands.append((mode, base))
commands.append(('clippy-test', ['cargo', 'clippy', '--locked', '--manifest-path', 'vm/Cargo.toml', '--all-features', '--test', 'swift_reactor_validation_allocations', '--', '-D', 'warnings']))
failed = False
for label, argv in commands:
    start = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=source, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
        data, code = result.stdout, result.returncode
    except subprocess.TimeoutExpired as error:
        data, code = (error.stdout or b'') + b'\nTIMEOUT\n', 124
    log = out / (label + '.log')
    log.write_bytes(data)
    stable = all(sha(source / p) == h for p, h in manifest.items())
    receipt['commands'].append({'label': label, 'argv': argv, 'cwd': str(source), 'environment': {'CARGO_TARGET_DIR': env['CARGO_TARGET_DIR'], 'PATH': env['PATH']}, 'exit': code, 'seconds': time.monotonic() - start, 'log': str(log.relative_to(ROOT)), 'sha256': sha(log), 'source_stable': stable})
    failed |= code != 0 or not stable
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(label, code, 'source_stable', stable, flush=True)
receipt.update(passed=not failed, completed_utc=datetime.now(timezone.utc).isoformat())
(out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
raise SystemExit(1 if failed else 0)
