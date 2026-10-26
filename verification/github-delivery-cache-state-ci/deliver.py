#!/usr/bin/env python3
"""Commit the verified index and nonforce-push the authorized coherent slice."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

def demand(ok, message):
    if not ok:
        raise ValueError(message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def run(label, argv, timeout=60):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=timeout)
    for stream in ['stdout', 'stderr']:
        (HERE / (label + '.' + stream)).write_bytes(getattr(result, stream))
    (HERE / (label + '.command.json')).write_text(json.dumps({
        'argv': argv, 'started': started, 'exit': result.returncode,
        'stdout_sha256': digest(result.stdout), 'stderr_sha256': digest(result.stderr)}, indent=2) + '\n')
    demand(result.returncode == 0, label + ' failed; inspect retained output')
    return result.stdout

demand(not (HERE / 'receipt.json').exists(), 'One-shot delivery already completed')
prepared = json.loads((HERE / 'prepared.json').read_text())
manifest_path = HERE / 'manifest.json'
demand(len(sys.argv) == 2 and digest(manifest_path.read_bytes()) == sys.argv[1] == prepared['manifest_sha256'], 'Manifest argument')
manifest = json.loads(manifest_path.read_text())
base = manifest['parent']
demand(run('before-head', ['git', 'rev-parse', 'HEAD']).decode().strip() == base, 'Changed base')
demand(run('before-branch', ['git', 'branch', '--show-current']).strip() == b'main', 'Changed branch')
demand(run('before-remote', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split()[0] == base, 'Remote changed')
expected = set(prepared['staged_paths'])
demand(set(run('index-paths', ['git', 'diff', '--cached', '--name-only', '-z']).decode().split('\0')) - {''} == expected, 'Index paths changed')
for row in manifest['members']:
    data = (ROOT / row['path']).read_bytes()
    demand(len(data) == row['bytes'] and digest(data) == row['sha256'], 'Selected working bytes changed: ' + row['path'])
requests = b''.join((':' + r['path'] + '\n').encode() for r in manifest['members'])
result = subprocess.run(['git', 'cat-file', '--batch'], input=requests, cwd=ROOT, capture_output=True, timeout=60, check=True)
cursor = 0
for row in manifest['members']:
    end = result.stdout.index(b'\n', cursor); header = result.stdout[cursor:end].split()
    demand(len(header) == 3 and header[1] == b'blob', 'Missing index blob')
    size = int(header[2]); data = result.stdout[end + 1:end + 1 + size]
    demand(size == row['bytes'] and digest(data) == row['sha256'], 'Index bytes changed: ' + row['path'])
    cursor = end + size + 2
run('git-version', ['git', '--version'])
run('commit', ['git', 'commit', '--quiet', '-m', 'Qualify closed cache-state fixture and add dedicated CI job'])
head = run('after-head', ['git', 'rev-parse', 'HEAD']).decode().strip()
demand(run('parent', ['git', 'rev-parse', 'HEAD^']).decode().strip() == base, 'Commit parent')
demand(set(run('committed-paths', ['git', 'diff-tree', '--no-commit-id', '--no-renames', '--name-only', '-r', '-z', head]).decode().split('\0')) - {''} == expected, 'Commit path mismatch')
demand(not run('index-after', ['git', 'diff', '--cached', '--name-only']), 'Index not empty')
run('push', ['git', 'push', 'origin', 'HEAD:main'], timeout=180)
demand(run('after-remote', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split()[0] == head, 'Remote verification')
receipt = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'commit': head, 'parent': base, 'tree': run('tree', ['git', 'rev-parse', 'HEAD^{tree}']).decode().strip(),
           'status': 'pushed-CI-pending', 'paths': len(expected), 'manifest_sha256': sys.argv[1],
           'manifest_member_bytes': manifest['member_bytes'], 'scope': manifest['scope'],
           'remote_head_verified': True, 'force_push': False,
           'native_runtime_or_public_V2_or_GA_qualified': False}
(HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
