#!/usr/bin/env python3
"""Root combined Rust regression of immutable Swift descriptors and cache-control prerequisites."""
import argparse
from datetime import datetime, timezone
import hashlib
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
paths = [ROOT / 'vm/Cargo.toml', ROOT / 'vm/Cargo.lock']
for folder in ['vm/src', 'vm/tests', 'vm/tools']:
    paths += [p for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
manifest = {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)}
for relative, digest in manifest.items():
    dest = source / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes((ROOT / relative).read_bytes())
    assert sha(dest) == digest == sha(ROOT / relative)
    dest.chmod(0o444)
archive = out / 'source.tar'
with tarfile.open(archive, 'w') as tar:
    tar.add(source / 'vm', arcname='vm')
env = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'], CARGO_TARGET_DIR=str(work / 'target'))
receipt = {
    'started_utc': datetime.now(timezone.utc).isoformat(),
    'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'collector_sha256': sha(Path(__file__)),
    'source': str(source), 'source_files': manifest,
    'source_tree_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
    'source_archive': str(archive.relative_to(ROOT)), 'source_archive_sha256': sha(archive),
    'commands': [],
    'scope': 'Combined host regression of immutable borrowed Swift execution descriptors, actual WASI/control observation and adopted-owner preconditions, all original Rust features and explicitly selected reference oracles. No cache/executor implementation, full Swift target instantiation/invocation, mobile devices, publication or GA acceptance.',
}
commands = [('rust-version', ['rustc', '-Vv']), ('cargo-version', ['cargo', '-V']), ('node-version', ['node', '--version'])]
for mode in ['debug', 'release']:
    flags = ['--release'] if mode == 'release' else []
    base = ['cargo', 'test', '--locked', '--manifest-path', 'vm/Cargo.toml', *flags, '--all-features']
    commands += [(mode, base), (mode + '-oracles', base + ['--', '--ignored'])]
commands += [('focused-clippy', ['cargo', 'clippy', '--locked', '--manifest-path', 'vm/Cargo.toml', '--all-features', '--lib', '--bins', '--test', 'span_execution', '--test', 'span_execution_allocations', '--test', 'span_execution_oracle', '--test', 'swift_wasi', '--test', 'swift_wasi_allocations', '--test', 'swift_reactor_validation', '--test', 'swift_reactor_validation_allocations', '--', '-D', 'warnings']), ('format', ['cargo', 'fmt', '--manifest-path', 'vm/Cargo.toml', '--check'])]
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
