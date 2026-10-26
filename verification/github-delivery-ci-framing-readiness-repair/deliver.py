"""One-shot exact-path delivery of the independently reviewed CI test repair."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = 'c4c6f3d8ba143effd9a1541ffe6f1692a79de6b9'
REPAIR = ROOT / 'verification/ci-framing-timeout-readiness-repair'
PRIOR = ROOT / 'verification/github-delivery-component-acceptance-checkpoint'
PROTECTED = {
    '.github/workflows/hosted.yml': 'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57',
    'hosted/lib/mixer_hosted/browser_auth/store.ex': '8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299',
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(name, data):
    with (OUT / name).open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')

def command(name, argv, timeout=60):
    start = time.monotonic()
    with (OUT / (name + '.stdout')).open('xb') as out, (OUT / (name + '.stderr')).open('xb') as err:
        result = subprocess.run(argv, cwd=ROOT, stdout=out, stderr=err, timeout=timeout)
    save(name + '.command.json', {'argv': argv, 'exit': result.returncode,
         'elapsed_seconds': time.monotonic() - start, 'finished': datetime.now(timezone.utc).isoformat()})
    result.check_returncode()
    return (OUT / (name + '.stdout')).read_text().strip()

if (OUT / 'manifest.json').exists():
    raise RuntimeError('one-shot delivery already prepared; do not replay')
assert command('branch', ['git', 'branch', '--show-current']) == 'main'
assert command('head', ['git', 'rev-parse', 'HEAD']) == BASE
assert command('remote', ['git', 'ls-remote', 'origin', 'refs/heads/main']).split()[0] == BASE
assert not command('index-before', ['git', 'diff', '--cached', '--name-only'])
for path, digest in PROTECTED.items():
    assert sha(ROOT / path) == digest
test = ROOT / 'scripts/ci/tests/test_analyzer_framing_runner.py'
assert sha(test) == '02f82bbe93dcc59bbce59a733238c44bb8ec6f77cb61cffa7767fa8c9b395955'
assert json.loads((REPAIR / 'receipt.json').read_text())['status'] == 'local-repair-and-independent-timeout-review-passed'
command('diff-check', ['git', 'diff', '--check'])
selected = [ROOT / name for name in ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json',
            'scripts/ci/tests/test_analyzer_framing_runner.py']]
for folder in (REPAIR, PRIOR):
    for path in folder.rglob('*'):
        if path.is_symlink():
            raise ValueError('symlink in root-owned delivery packet')
        if path.is_file():
            selected.append(path)
selected.append(Path(__file__))
rows = [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size, 'sha256': sha(p)}
        for p in sorted(set(selected))]
assert all(not row['path'].startswith('verification/android-editor-source-pair5-') for row in rows)
save('manifest.json', {'schema': 1, 'base': BASE, 'members': rows,
     'scope': 'One CI timeout test plus root evidence/metadata; active integrations excluded',
     'member_count': len(rows), 'member_bytes': sum(r['bytes'] for r in rows)})
paths = [row['path'] for row in rows] + [str((OUT / 'manifest.json').relative_to(ROOT))]
(OUT / 'paths.nul').write_bytes(b''.join(p.encode() + b'\0' for p in paths))
command('stage', ['git', 'add', '--pathspec-from-file=' + str(OUT / 'paths.nul'), '--pathspec-file-nul'])
for row in rows:
    assert sha(ROOT / row['path']) == row['sha256']
index = command('index-selected', ['git', 'diff', '--cached', '--name-only']).splitlines()
assert set(index) <= set(paths) and 'scripts/ci/tests/test_analyzer_framing_runner.py' in index
command('index-check', ['git', 'diff', '--cached', '--check'])
command('commit', ['git', 'commit', '-m', 'Synchronize framing timeout test startup before timed wait'])
head = command('after-head', ['git', 'rev-parse', 'HEAD'])
tree = command('tree', ['git', 'rev-parse', 'HEAD^{tree}'])
assert command('parent', ['git', 'rev-parse', 'HEAD^']) == BASE
assert set(command('committed-paths', ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD']).splitlines()) == set(index)
assert not command('index-after', ['git', 'diff', '--cached', '--name-only'])
command('push', ['git', 'push', 'origin', 'HEAD:main'], timeout=120)
assert command('remote-after', ['git', 'ls-remote', 'origin', 'refs/heads/main']).split()[0] == head
for path, digest in PROTECTED.items():
    assert sha(ROOT / path) == digest
save('receipt.json', {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'commit': head,
     'tree': tree, 'parent': BASE, 'manifest_sha256': sha(OUT / 'manifest.json'),
     'committed_paths': len(index), 'pushed': True, 'force': False,
     'protected_work_unchanged': PROTECTED, 'active_lanes_excluded': True,
     'canonical_product_changed': False, 'CI_pending': True, 'native_OTA_GA_accepted': False})
print(json.dumps({'commit': head, 'tree': tree, 'paths': len(index), 'pushed': True}))
