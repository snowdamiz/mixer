#!/usr/bin/env python3
"""Freeze only this owned producer packet and its document."""
import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(1048576):h.update(b)
    return h.hexdigest()
def main():
    assert not (BASE/'seal.json').exists(),'Already frozen; never rewrite a prior seal.'
    receipt=json.loads((BASE/'final-receipt.json').read_text());assert receipt['status']=='producer-passed-independent-review-required'
    assert not any((BASE/'scratch').rglob('*')),'Owned scratch not empty'
    files=[ROOT/'docs/swift-ordered-retention-analyzer-envelope.md']+[p for p in sorted(BASE.rglob('*')) if p.is_file() and p.name not in ('seal.json','seal.sha256')]
    members=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=digest(p)) for p in files]
    value=dict(schema=1,at=datetime.now(timezone.utc).isoformat(),scope='separate-safe-File-fixture-envelope-producer-only-awaiting-independent-review',members=members,excluded=[str((BASE/n).relative_to(ROOT)) for n in ['seal.json','seal.sha256']],storedPrefixValidated=False,fullReplayAccepted=False)
    (BASE/'seal.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
    h=digest(BASE/'seal.json');(BASE/'seal.sha256').write_text(h+'\n')
    print(json.dumps(dict(sha256=h,members=len(members),bytes=sum(m['bytes'] for m in members))))
if __name__=='__main__':main()
