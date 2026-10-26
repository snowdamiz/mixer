"""Commit and nonforce-push only the exact reviewed index, retaining output."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

def run(label, argv, timeout=60):
    started = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=timeout)
    (OUT / (label + '.stdout')).write_bytes(result.stdout)
    (OUT / (label + '.stderr')).write_bytes(result.stderr)
    (OUT / (label + '.command.json')).write_text(json.dumps({
        'argv': argv, 'cwd': str(ROOT), 'started': started,
        'ended': datetime.now(timezone.utc).isoformat(), 'exit': result.returncode,
        'stdout_sha256': hashlib.sha256(result.stdout).hexdigest(),
        'stderr_sha256': hashlib.sha256(result.stderr).hexdigest()}, indent=2) + '\n')
    assert result.returncode == 0, (label, result.stderr.decode(errors='replace')[-2000:])
    return result.stdout

assert not (OUT / 'receipt.json').exists(), 'one-shot delivery already ran'
manifest_path = OUT / 'manifest.json'
raw = manifest_path.read_bytes()
assert len(sys.argv) == 2 and hashlib.sha256(raw).hexdigest() == sys.argv[1]
manifest = json.loads(raw)
assert run('before-head', ['git', 'rev-parse', 'HEAD']).decode().strip() == manifest['base']
assert run('before-branch', ['git', 'branch', '--show-current']).decode().strip() == 'main'
assert run('before-remote', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split()[0] == manifest['base']
expected = set(manifest['files']) | set(manifest['deletions']) | {manifest_path.relative_to(ROOT).as_posix()}
assert set(run('index-paths', ['git', 'diff', '--cached', '--name-only', '--no-renames', '-z']).decode().strip('\0').split('\0')) == expected
for name, row in manifest['files'].items():
    data = (ROOT / name).read_bytes()
    assert {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} == row, name
for name in manifest['deletions']:
    assert not (ROOT / name).exists()
run('git-version', ['git', '--version'])
run('commit', ['git', 'commit', '--quiet', '-m', 'Integrate reviewed private Android owner and source profile3'])
head = run('after-head', ['git', 'rev-parse', 'HEAD']).decode().strip()
assert run('parent', ['git', 'rev-parse', 'HEAD^']).decode().strip() == manifest['base']
assert set(run('committed-paths', ['git', 'diff-tree', '--no-commit-id', '--no-renames', '--name-only', '-r', '-z', head]).decode().strip('\0').split('\0')) == expected
assert not run('index-after', ['git', 'diff', '--cached', '--name-only', '-z'])
run('push', ['git', 'push', 'origin', 'HEAD:main'], timeout=180)
assert run('after-remote', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split()[0] == head
receipt = {
    'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'status': 'pushed-CI-pending',
    'commit': head, 'parent': manifest['base'],
    'tree': run('tree', ['git', 'rev-parse', 'HEAD^{tree}']).decode().strip(),
    'paths': len(expected), 'bytes': manifest['bytes'], 'manifest_sha256': sys.argv[1],
    'scope': manifest['scope'], 'remote_head_verified': True, 'force_push': False,
    'canonical_private_owner_and_CLI_development_scope_accepted': True,
    'native_runtime_or_capture_started': False, 'public_V2_selected': False, 'GA_qualified': False,
}
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
