#!/usr/bin/env python3
"""Check retained exact data-only qualification evidence and current owned product files."""
from pathlib import Path
import hashlib, json
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
seal=json.loads((HERE/'seal.json').read_text())
for path,expected in seal['artifacts'].items():
    if not (ROOT/path).is_file() or sha(ROOT/path)!=expected:raise SystemExit('artifact mismatch: '+path)
collection=hashlib.sha256(''.join(p+'\0'+h+'\n' for p,h in sorted(seal['artifacts'].items())).encode()).hexdigest()
if collection!=seal['artifactCollectionSHA256']:raise SystemExit('collection mismatch')
r=json.loads((HERE/'candidate-1/receipt.json').read_text())
if r['status']!='passed-data-only':raise SystemExit('qualification not passed')
for path,expected in r['inputManifest'].items():
    if sha(HERE/'candidate-1/inputs'/path)!=expected:raise SystemExit('snapshot mismatch: '+path)
for command in r['commands']:
    if command['exit'] or sha(ROOT/command['log'])!=command['sha256']:raise SystemExit('command mismatch: '+command['name'])
for path in seal['ownedProductFiles']:
    if sha(ROOT/path)!=r['inputManifest'][path]:raise SystemExit('live product mismatch: '+path)
print('PASS',len(seal['artifacts']),'sealed artifacts;',len(r['commands']),'successful commands; frozen snapshot and live owned product match')
