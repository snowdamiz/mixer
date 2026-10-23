#!/usr/bin/env python3
"""Root isolated instruction/fuel observation prerequisites over committed cache descriptors."""
import argparse
import io
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
base_revision = '45852204fbcced037d8e530876b619d9ed1c2ce1'
raw = subprocess.check_output(['git', 'archive', base_revision, 'vm'], cwd=ROOT)
with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
    tar.extractall(source, filter='data')
overlays = ['vm/src/experimental_swift_reactor/control.rs', 'vm/src/experimental_swift_reactor/control_tests.rs']
for relative in overlays:
    (source / relative).write_bytes((ROOT / relative).read_bytes())
paths = sorted(p for p in (source / 'vm').rglob('*') if p.is_file())
manifest = {str(p.relative_to(source)): sha(p) for p in paths}
for p in paths:
    p.chmod(0o444)
archive = out / 'source.tar.gz'
with tarfile.open(archive, 'w:gz') as tar:
    tar.add(source / 'vm', arcname='vm')
env = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'], CARGO_TARGET_DIR=str(work / 'target'))
receipt = {
    'started_utc': datetime.now(timezone.utc).isoformat(),
    'base_revision': base_revision, 'overlays': overlays,
    'collector_sha256': sha(Path(__file__)),
    'source': str(source), 'source_files': manifest,
    'source_tree_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
    'source_archive': str(archive.relative_to(ROOT)), 'source_archive_sha256': sha(archive),
    'commands': [],
    'scope': 'Isolated private instruction/fuel observation variants over committed4585220 plus only control.rs/control_tests.rs. Actual WASI counters, eleven success/failure cases and sticky no-effect reentry; all-feature Debug/Release and reference checks plus minimal-Swift library, scoped lint and formatting. Active cache/module-gating/Android changes excluded. No executor, full reactor execution, devices, release or GA qualification.',
}
commands = [('rust-version', ['rustc', '-Vv']), ('cargo-version', ['cargo', '-V'])]
for mode in ['debug', 'release']:
    flags = ['--release'] if mode == 'release' else []
    base = ['cargo', 'test', '--locked', '--manifest-path', 'vm/Cargo.toml', *flags, '--all-features']
    commands += [(mode, base), (mode + '-oracles', base + ['--', '--ignored']), (mode + '-minimal-swift', ['cargo', 'test', '--locked', '--manifest-path', 'vm/Cargo.toml', *flags, '--features', 'experimental-swift-reactor', '--lib'])]
commands += [('clippy', ['cargo', 'clippy', '--locked', '--manifest-path', 'vm/Cargo.toml', '--all-features', '--lib', '--bins', '--', '-D', 'warnings']), ('format', ['cargo', 'fmt', '--manifest-path', 'vm/Cargo.toml', '--check'])]
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
