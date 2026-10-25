#!/usr/bin/env python3
"""Read-only review closure verification and finite support replay."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(65536):
            h.update(chunk)
    return h.hexdigest()


assert sys.dont_write_bytecode
assert digest(BASE / 'seal.json') == (BASE / 'seal.sha256').read_text().strip()
seal = json.loads((BASE / 'seal.json').read_bytes())
excluded = {BASE / 'seal.json', BASE / 'seal.sha256'}
actual = {'docs/swift-ordered-retention-analyzer-review.md'} | {
    str(p.relative_to(ROOT)) for p in BASE.rglob('*') if p.is_file()
    and p not in excluded}
assert actual == {row['path'] for row in seal['members']}
for row in seal['members']:
    path = ROOT / row['path']
    assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256']
result = json.loads((BASE / 'result.json').read_bytes())
assert result['passed']
for packet in result['upstream_after']:
    path = ROOT / packet['seal']
    assert digest(path) == packet['sha256']
    for row in json.loads(path.read_bytes())['members']:
        member = ROOT / row['path']
        assert member.stat().st_size == row['bytes'] and digest(member) == row['sha256']
env = dict(os.environ, **result['environment'])
snapshot = Path(result['environment']['REVIEW_DESIGN_SNAPSHOT'])
frozen = snapshot / 'verification/swift-ordered-retention-analyzer-design'
for test_base, pattern in ((frozen, 'test_model.py'), (BASE, 'test_independent.py')):
    subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s',
                    str(test_base), '-p', pattern, '-v'], cwd=ROOT, env=env,
                   check=True, timeout=60)
binary = ROOT / result['binary']['path']
assert digest(binary) == result['binary']['sha256']
subprocess.run([str(binary)], cwd=ROOT, env=env, check=True, timeout=60)
verdict = json.loads((BASE / 'final-receipt.json').read_bytes())
print(json.dumps({'scope': 'finite design review only', 'verdict': verdict['verdict'],
                  'design_seal': result['design_seal'], 'members': len(seal['members']),
                  'fullReplayAccepted': False}, sort_keys=True))
