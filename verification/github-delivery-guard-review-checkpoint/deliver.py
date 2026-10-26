"""Commit/push the previously reviewed exact index, retaining command evidence."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
def run(label, argv, timeout=120):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    p = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=timeout)
    (OUT / (label + '.stdout')).write_bytes(p.stdout)
    (OUT / (label + '.stderr')).write_bytes(p.stderr)
    (OUT / (label + '.command.json')).write_text(json.dumps({'argv': argv, 'cwd': str(ROOT), 'started': started,
        'ended': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'exit': p.returncode,
        'stdout_sha256': hashlib.sha256(p.stdout).hexdigest(), 'stderr_sha256': hashlib.sha256(p.stderr).hexdigest()}, indent=2) + '\n')
    assert p.returncode == 0, (label, p.stderr.decode(errors='replace')[-2000:])
    return p.stdout

manifest_path = OUT / 'manifest.json'
raw = manifest_path.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '4f8a34f6e56f425f6a1c6a6b059de178321b7db5e531a6f7c1187bb67f434ff6'
m = json.loads(raw)
assert run('before-head', ['git', 'rev-parse', 'HEAD']).decode().strip() == m['base']
assert run('before-remote', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split()[0] == m['base']
expected = set(m['files']) | {manifest_path.relative_to(ROOT).as_posix()}
assert set(run('index-paths', ['git', 'diff', '--cached', '--name-only', '-z']).decode().strip('\0').split('\0')) == expected
for name, row in m['files'].items():
    data = (ROOT / name).read_bytes()
    assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256'], name
run('git-version', ['git', '--version'])
run('commit', ['git', 'commit', '--quiet', '-m', 'Preserve guard correction and independent rejection evidence'])
head = run('after-head', ['git', 'rev-parse', 'HEAD']).decode().strip()
assert run('parent', ['git', 'rev-parse', 'HEAD^']).decode().strip() == m['base']
assert set(run('committed-paths', ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', '-z', head]).decode().strip('\0').split('\0')) == expected
assert not run('index-after', ['git', 'diff', '--cached', '--name-only', '-z'])
run('push', ['git', 'push', 'origin', 'HEAD:main'], timeout=180)
assert run('after-remote', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split()[0] == head
receipt = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status': 'pushed-CI-pending', 'commit': head, 'parent': m['base'],
    'tree': run('tree', ['git', 'rev-parse', 'HEAD^{tree}']).decode().strip(),
    'paths': len(expected), 'bytes': m['bytes'], 'manifest_sha256': hashlib.sha256(raw).hexdigest(),
    'scope': m['scope'], 'remote_head_verified': True, 'force_push': False,
    'canonical_product_sources_changed': False, 'implementation_accepted': False,
    'native_runtime_or_capture_started': False, 'GA_qualified': False}
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
