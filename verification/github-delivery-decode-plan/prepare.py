#!/usr/bin/env python3
"""Stage only completed reviewed slices, preserving other active work."""
from pathlib import Path
import collections
import hashlib
import json
import re
import subprocess

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def run(argv, **kw):
    return subprocess.run(argv, cwd=ROOT, capture_output=True, check=True, **kw)


assert not run(['git', 'diff', '--cached', '--name-only']).stdout
paths = set()
for name in ['verification/swift-decode-plan-reuse-accounting-review/seal.json',
             'verification/swift-decode-plan-full-regression/seal.json']:
    seal = ROOT / name
    data = json.loads(seal.read_text())
    paths.add(name)
    for path, value in data['files'].items():
        target = seal.parent / path
        expected = value if isinstance(value, str) else value['sha256']
        assert hashlib.sha256(target.read_bytes()).hexdigest() == expected, target
        paths.add(str(target.relative_to(ROOT)))
    paths.update(data['externalFiles'])
for name in ['apple-focus-system-observation-review', 'apple-focus-system-join-correction',
             'apple-focus-system-join-correction-review', 'apple-focus-system-native-build']:
    seal = ROOT / 'verification' / name / 'handoff.json'
    data = json.loads(seal.read_text())
    paths.add(str(seal.relative_to(ROOT)))
    for path, value in data['members'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == value['sha256'], path
        paths.add(path)
    sidecar = seal.with_suffix('.sha256')
    if sidecar.exists():
        paths.add(str(sidecar.relative_to(ROOT)))
for directory in ['verification/swift-decode-plan-root-integration',
                  'verification/apple-focus-system-observation-root-review',
                  'verification/execution-index-consolidation-2026-10-25',
                  'verification/github-ci-9102ad3e-engine',
                  'verification/github-delivery-finite-diagnostics']:
    paths.update(str(p.relative_to(ROOT)) for p in (ROOT / directory).rglob('*') if p.is_file())
paths.update(['PLAN.md', 'STATUS.md', 'PLAN.history-2026-10-25.md', 'STATUS.history-2026-10-25.md',
              'work-graph.json', 'gates/ga.json', 'docs/swift-decode-plan-integration.md',
              'docs/swift-decode-plan-regression-contract.md',
              'verification/swift-decode-plan-reuse-diagnosis-root-review/accounting-review-acceptance.json',
              'verification/swift-decode-plan-reuse-diagnosis-root-review/independent-verification.stdout',
              'verification/swift-decode-plan-reuse-diagnosis-root-review/independent-verification.stderr',
              'verification/apple-focus-system-observation/handoff.sha256'])
paths.update('vm/src/experimental_swift_reactor/' + n for n in
             ['cache.rs', 'cache_tests.rs', 'execution_tests.rs', 'lifecycle_tests.rs'])
for path in paths:
    target = ROOT / path
    assert target.is_file() and not target.is_symlink() and '..' not in Path(path).parts, path
    assert 'apple-focus-system-runtime-preparation' not in path
    assert 'swift-exact-reactor-after-plan-reuse' not in path
snapshot = {p: {'sha256': hashlib.sha256((ROOT / p).read_bytes()).hexdigest(),
                'bytes': (ROOT / p).stat().st_size} for p in sorted(paths)}
(BASE / 'selected-files.json').write_text(json.dumps(snapshot, indent=2) + '\n')
for file in ['PLAN.md', 'STATUS.md']:
    for link in re.findall(r'\]\(([^)]+)\)', (ROOT / file).read_text()):
        if '://' not in link:
            assert (ROOT / link.split('#')[0]).exists(), (file, link)
gates = json.loads((ROOT / 'gates/ga.json').read_text())['gates']
assert collections.Counter(g['status'] for g in gates) == {'planned': 30, 'running': 8}
assert all(g.get('reviewer') is None for g in gates)
packages = json.loads((ROOT / 'work-graph.json').read_text())['packages']
assert collections.Counter(p['state'] for p in packages) == {'in_progress': 16, 'ready': 2}
run(['git', 'diff', '--check'])
payload = b'\0'.join(p.encode() for p in sorted(paths)) + b'\0'
result = subprocess.run(['git', 'check-ignore', '--stdin', '-z'], cwd=ROOT, input=payload, capture_output=True)
assert result.returncode in [0, 1]
ignored = set(p.decode() for p in result.stdout.split(b'\0') if p)
for filename, selected, force in [('normal.paths', paths - ignored, False), ('ignored-evidence.paths', ignored, True)]:
    target = BASE / filename
    target.write_bytes(b'\0'.join(p.encode() for p in sorted(selected)) + b'\0')
    argv = ['git', 'add'] + (['-f'] if force else []) + ['--pathspec-from-file=' + str(target), '--pathspec-file-nul']
    if selected:
        output = run(argv)
        (BASE / (filename + '.stdout')).write_bytes(output.stdout)
        (BASE / (filename + '.stderr')).write_bytes(output.stderr)
staged = set(run(['git', 'diff', '--cached', '--name-only', '-z']).stdout.decode().strip('\0').split('\0'))
assert staged <= paths
run(['git', 'diff', '--cached', '--check'])
receipt = {'selectedFiles': len(paths), 'stagedFiles': len(staged), 'ignoredEvidenceExplicitlyAdded': len(ignored),
           'stagedBytes': sum(snapshot[p]['bytes'] for p in staged), 'activeLanesExcluded': True,
           'gateStatusAndReviewersUnchanged': True, 'packageStatusUnchanged': True,
           'manifestSHA256': hashlib.sha256((BASE / 'selected-files.json').read_bytes()).hexdigest()}
(BASE / 'staging.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
