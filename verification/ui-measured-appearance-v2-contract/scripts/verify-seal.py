#!/usr/bin/env python3
"""Verify retained design evidence; no native or release authority is inferred."""
from pathlib import Path
import hashlib
import json
import sys
HERE=Path(__file__).resolve().parents[1]; ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((HERE/'receipt.json').read_text())
if receipt['status']!='passed-design-only': raise SystemExit('receipt is not a design-check pass')
for path,digest in receipt['artifacts'].items():
    if sha(ROOT/path)!=digest: raise SystemExit('artifact changed: '+path)
collection=hashlib.sha256(''.join(p+'\0'+h+'\n' for p,h in sorted(receipt['artifacts'].items())).encode()).hexdigest()
if collection!=receipt['artifactCollectionSHA256']: raise SystemExit('artifact collection mismatch')
lock=json.loads((HERE/'input-lock.json').read_text())
manifest=lock['inputs']
tree=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
if tree!=lock['inputTreeSHA256'] or tree!=receipt['inputTreeSHA256']: raise SystemExit('input tree mismatch')
for path,digest in manifest.items():
    if sha(HERE/'inputs'/path)!=digest: raise SystemExit('retained input changed: '+path)
if '--check-live' in sys.argv:
    for path,digest in manifest.items():
        if sha(ROOT/path)!=digest: raise SystemExit('live input changed: '+path)
if any(c['exit']!=0 or sha(ROOT/c['log'])!=c['sha256'] for c in receipt['commands']):
    raise SystemExit('command/log mismatch')
print(json.dumps({'status':'passed-design-seal-only','artifactBindings':len(receipt['artifacts']),
    'inputBindings':len(manifest),'commandCount':len(receipt['commands']),'collectionSHA256':collection,
    'liveInputsChecked':'--check-live' in sys.argv},sort_keys=True))
