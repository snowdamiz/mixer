#!/usr/bin/env python3
"""Verify final live bindings and retained evidence; no native authority."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
seal=json.loads((HERE/'seal.json').read_text())
for p,h in seal['bindings'].items():
 if sha(ROOT/p)!=h:raise SystemExit('live binding changed: '+p)
receipt_path=ROOT/seal['receipt'];receipt=json.loads(receipt_path.read_text())
if sha(receipt_path)!=seal['receiptSHA256'] or receipt['status']!='passed-data-only':raise SystemExit('receipt mismatch')
inputs=receipt_path.parent/'inputs'
for p,h in receipt['inputManifest'].items():
 if sha(inputs/p)!=h:raise SystemExit('frozen input changed: '+p)
for p,h in receipt['artifacts'].items():
 if '/build/' not in p and sha(ROOT/p)!=h:raise SystemExit('retained artifact changed: '+p)
print('PASS Android V2 final bindings, frozen actual sources, exact corpus and retained output hashes; data-only')
