#!/usr/bin/env python3
"""Check an immutable baseline export with only the three observer-file overlays."""
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile

root = Path(__file__).resolve().parents[2]
evidence = Path(__file__).resolve().parent
env = dict(os.environ)
env['PATH'] = '/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin:' + env['PATH']
env.pop('MIXER_ALLOCATOR_NOISE', None)
baseline = subprocess.check_output(['git', 'rev-parse', 'e299f1a'], cwd=root, text=True).strip()
export = subprocess.check_output(['git', 'archive', '--format=tar', baseline, 'vm'], cwd=root)
private = Path(tempfile.mkdtemp(prefix='mixer-allocator-observer-'))
snapshot = private/'source'
snapshot.mkdir()
with tarfile.open(fileobj=io.BytesIO(export)) as archive:
    archive.extractall(snapshot, filter='data')
overlay_paths = ['vm/tests/span_function_cache_allocations.rs', 'vm/tests/span_execution_allocations.rs', 'vm/tests/common/allocation_observer.rs']
overlay = {}
for name in overlay_paths:
    content = (root/name).read_bytes()
    (snapshot/name).write_bytes(content)
    overlay[name] = hashlib.sha256(content).hexdigest()

def source():
    paths = sorted(path for path in snapshot.rglob('*') if path.is_file())
    manifest = {str(path.relative_to(snapshot)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    return {'sha256': digest, 'files': manifest}

# Retain every tested source byte as well as a per-file digest manifest.
archive_path = evidence/'tested-vm-snapshot.tar'
with tarfile.open(archive_path, 'w') as archive:
    archive.add(snapshot/'vm', arcname='vm')
for path in snapshot.rglob('*'):
    path.chmod(0o555 if path.is_dir() else 0o444)
snapshot.chmod(0o555)
env['CARGO_TARGET_DIR'] = str(private/'target')
base = ['cargo', 'test', '--locked', '--manifest-path', 'vm/Cargo.toml', '--features', 'experimental-span-execution', '--test', 'span_function_cache_allocations', '--test', 'span_execution_allocations']
commands = []
for release in (False, True):
    for noisy in (False, True):
        name = ('release' if release else 'debug') + ('-noise' if noisy else '-baseline')
        commands.append((name, base + (['--release'] if release else []) + ['--', '--nocapture'], noisy))
commands.append(('clippy', ['cargo', 'clippy', '--locked', '--manifest-path', 'vm/Cargo.toml', '--features', 'experimental-span-execution', '--test', 'span_function_cache_allocations', '--test', 'span_execution_allocations', '--', '-D', 'warnings'], False))
receipt = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'baseline_revision': baseline,
    'baseline_git_tree': subprocess.check_output(['git', 'rev-parse', baseline+'^{tree}'], cwd=root, text=True).strip(),
    'baseline_vm_export_sha256': hashlib.sha256(export).hexdigest(),
    'worktree_revision_at_capture': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
    'private_source': str(snapshot),
    'environment': {'CARGO_TARGET_DIR': env['CARGO_TARGET_DIR']},
    'overlay': overlay,
    'full_snapshot': str(archive_path.relative_to(root)),
    'full_snapshot_sha256': hashlib.sha256(archive_path.read_bytes()).hexdigest(),
    'tools': {tool: subprocess.check_output(command, cwd=snapshot, env=env, text=True).strip() for tool,command in [('rustc',['rustc','-Vv']),('cargo',['cargo','-V']),('clippy',['cargo','clippy','-V'])]},
    'source_before': source(),
    'checks': [],
    'scope': 'Immutable baseline plus test-only observer overlays. Synchronous function-cache/span-execution allocation observations only. No product edits, devices, signing, published package, release or GA qualification.'
}
for name, command, noisy in commands:
    check_env = dict(env)
    if noisy:
        check_env['MIXER_ALLOCATOR_NOISE'] = '1'
    source_before = source()['sha256']
    path = evidence / f'logs/{name}.log'
    with path.open('w') as log:
        log.write('CWD: ' + str(snapshot) + '\n')
        log.write('COMMAND: ' + ('MIXER_ALLOCATOR_NOISE=1 ' if noisy else '') + ' '.join(command) + '\n')
        log.flush()
        result = subprocess.run(command, cwd=snapshot, env=check_env, stdout=log, stderr=subprocess.STDOUT)
        log.write(f'\nEXIT: {result.returncode}\n')
    receipt['checks'].append({'name': name, 'command': command, 'environment': {'MIXER_ALLOCATOR_NOISE': '1'} if noisy else {}, 'exit': result.returncode, 'source_before_sha256': source_before, 'source_after_sha256': source()['sha256'], 'log': str(path.relative_to(root)), 'log_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    print(f'{name}: exit={result.returncode}', flush=True)
receipt['source_after'] = source()
receipt['source_stable'] = receipt['source_before'] == receipt['source_after']
(evidence/'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
raise SystemExit(any(check['exit'] != 0 for check in receipt['checks']))
