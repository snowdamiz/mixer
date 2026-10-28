#!/usr/bin/env python3
"""Read-only, bounded Git object verification; no product/runtime execution."""
import ast
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
signal.alarm(30)
ALLOWED = [
    ['git', '--version'],
    ['git', '--no-replace-objects', 'rev-parse', 'HEAD', 'HEAD^{tree}'],
    ['git', '--no-replace-objects', 'cat-file', '--batch'],
]
commands = []


def audit(event, args):
    if event == 'subprocess.Popen':
        assert list(args[1]) in ALLOWED and args[2] == ROOT, 'unselected process action'
    elif event.startswith('socket.') or event in {'os.system', 'os.fork', 'os.forkpty', 'os.posix_spawn', 'os.exec', 'os.kill', 'os.killpg'}:
        raise RuntimeError('source verification forbids network/PID/other process actions')


sys.addaudithook(audit)


def row(body):
    return {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}


def git(argv, data=None):
    result = subprocess.run(argv, cwd=ROOT, input=data, capture_output=True, check=True, timeout=10)
    commands.append({'argv': argv, 'timeout_seconds': 10, 'exit_code': result.returncode,
                     'stdin': row(data) if data is not None else None,
                     'stdout': row(result.stdout), 'stderr': result.stderr.decode()})
    return result.stdout


version = git(ALLOWED[0]).decode().strip()
head, tree = git(ALLOWED[1]).decode().splitlines()
source = (ROOT / 'hosted/scripts/test-identity-network.py').read_text()
manifest = next(ast.literal_eval(node.value) for node in ast.parse(source).body
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'FROZEN_MANIFEST' for t in node.targets))
refs = ''.join(head + ':' + path + '\n' for path in sorted(manifest)).encode()
batch = git(ALLOWED[2], refs)
observed = {}
offset = 0
for path in sorted(manifest):
    end = batch.index(b'\n', offset)
    object_id, kind, size_text = batch[offset:end].split()
    assert kind == b'blob'
    size = int(size_text)
    body = batch[end + 1:end + 1 + size]
    assert len(body) == size and batch[end + 1 + size:end + 2 + size] == b'\n'
    observed[path] = row(body)
    offset = end + 2 + size
assert offset == len(batch)
digest = hashlib.sha256(json.dumps(observed, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
assert len(observed) == 177 and observed == manifest
assert digest == '023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e'
result = {'schema': 1, 'python': sys.version, 'git_version': version, 'HEAD': head, 'git_tree': tree,
          'commands': commands, 'source_files': 177, 'source_tree_digest_sha256': digest,
          'manifest': observed, 'scope': 'read-only Git metadata and exact committed blobs; protected working source is deliberately separate',
          'product_runtime': False, 'passed': True}
(OUT / 'committed-source.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'manifest'}, sort_keys=True, indent=2))
