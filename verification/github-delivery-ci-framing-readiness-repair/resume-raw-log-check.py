"""Resume the prepared delivery, preserving raw CI timestamp-only log lines."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = 'c4c6f3d8ba143effd9a1541ffe6f1692a79de6b9'
RAW = 'verification/github-delivery-component-acceptance-checkpoint/swift-failed-job-api.log'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(name, value):
    with (OUT / name).open('x') as f:
        json.dump(value, f, indent=2)
        f.write('\n')

def command(name, argv, timeout=60):
    start = time.monotonic()
    with (OUT / ('resume-' + name + '.stdout')).open('xb') as out, (OUT / ('resume-' + name + '.stderr')).open('xb') as err:
        result = subprocess.run(argv, cwd=ROOT, stdout=out, stderr=err, timeout=timeout)
    save('resume-' + name + '.command.json', {'argv': argv, 'exit': result.returncode,
         'elapsed_seconds': time.monotonic() - start, 'finished': datetime.now(timezone.utc).isoformat()})
    result.check_returncode()
    return (OUT / ('resume-' + name + '.stdout')).read_text().strip()

assert command('head', ['git', 'rev-parse', 'HEAD']) == BASE
assert command('branch', ['git', 'branch', '--show-current']) == 'main'
assert command('remote', ['git', 'ls-remote', 'origin', 'refs/heads/main']).split()[0] == BASE
manifest = json.loads((OUT / 'manifest.json').read_text())
for row in manifest['members']:
    assert sha(ROOT / row['path']) == row['sha256']
old_index = (OUT / 'index-selected.stdout').read_text().splitlines()
assert command('index', ['git', 'diff', '--cached', '--name-only']).splitlines() == old_index
diagnostic = (OUT / 'index-check.stdout').read_text()
assert diagnostic.count('trailing whitespace.') == 3
assert all(line.startswith(RAW + ':') for line in diagnostic.splitlines() if 'trailing whitespace.' in line)
save('raw-log-preservation-selection.json', {'reason': 'Three original CI timestamp-only lines end in a space. Preserve raw evidence byte for byte; run whitespace check over all selected paths except this one raw log.',
     'raw_path': RAW, 'raw_sha256': sha(ROOT / RAW), 'original_failure_retained': True,
     'original_manifest_sha256': sha(OUT / 'manifest.json'), 'source_test_policy_unchanged': True})
extra = [str(Path(__file__).relative_to(ROOT)), str((OUT / 'raw-log-preservation-selection.json').relative_to(ROOT))]
command('stage', ['git', 'add', '--', *extra])
command('check', ['git', 'diff', '--cached', '--check', '--', '.', ':(exclude)' + RAW])
index = command('selected', ['git', 'diff', '--cached', '--name-only']).splitlines()
assert set(index) == set(old_index) | set(extra)
command('commit', ['git', 'commit', '-m', 'Synchronize framing timeout test startup before timed wait'])
head = command('after-head', ['git', 'rev-parse', 'HEAD'])
tree = command('tree', ['git', 'rev-parse', 'HEAD^{tree}'])
assert command('parent', ['git', 'rev-parse', 'HEAD^']) == BASE
assert set(command('committed-paths', ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD']).splitlines()) == set(index)
assert not command('index-after', ['git', 'diff', '--cached', '--name-only'])
command('push', ['git', 'push', 'origin', 'HEAD:main'], timeout=120)
assert command('remote-after', ['git', 'ls-remote', 'origin', 'refs/heads/main']).split()[0] == head
protected = {'.github/workflows/hosted.yml': 'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57',
             'hosted/lib/mixer_hosted/browser_auth/store.ex': '8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299'}
for path, value in protected.items():
    assert sha(ROOT / path) == value
save('receipt.json', {'at': datetime.now(timezone.utc).isoformat(), 'commit': head, 'tree': tree,
     'parent': BASE, 'manifest_sha256': sha(OUT / 'manifest.json'), 'additional_selected_paths': extra,
     'committed_paths': len(index), 'pushed': True, 'force': False,
     'protected_work_unchanged': protected, 'active_integration_lanes_excluded': True,
     'canonical_product_changed': False, 'CI_pending': True, 'native_OTA_GA_accepted': False})
print(json.dumps({'commit': head, 'tree': tree, 'paths': len(index), 'pushed': True}))
