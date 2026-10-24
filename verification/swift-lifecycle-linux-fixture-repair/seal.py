#!/usr/bin/env python3
"""Seal the final evidence packet and accompanying explanation exactly once."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
assert not (HERE / 'owned-target').exists()
assert not (HERE / 'seal.json').exists(), 'do not replace a sealed packet'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
doc = 'docs/swift-lifecycle-linux-fixture-repair.md'
seal = {'schema': 'mixer.swift-lifecycle.linux-fixture-repair.seal.1',
        'files': {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob('*')) if p.is_file()},
        'externalFiles': {doc: sha(ROOT / doc)},
        'scope': 'Host-only fixture repair; original Linux failure retained; no production or GA credit.'}
(HERE / 'seal.json').write_text(json.dumps(seal, sort_keys=True, indent=2) + '\n')
print(json.dumps({'sealedFiles': len(seal['files']), 'sealSHA256': sha(HERE / 'seal.json')}))
