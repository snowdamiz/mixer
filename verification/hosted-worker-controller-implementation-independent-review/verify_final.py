#!/usr/bin/env python3
import hashlib,json,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((HERE/'receipt.json').read_text())
for e in receipt['artifacts']:
    p=ROOT/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],str(p)
with tarfile.open(ROOT/receipt['review_fixture_archive']['path']) as tar:
    for m in tar:
        assert hashlib.sha256(tar.extractfile(m).read()).hexdigest()==sha(ROOT/m.name),m.name
assert not Path(receipt['cleanup']['owned_scratch']).exists()
assert receipt['independent_groups_failed']==3 and receipt['producer_groups_passed']==28
check={'status':'passed','scope':'independent-rejected-packet-integrity-and-recorded-cleanup-only','review_decision':receipt['status'],'receipt_sha256':sha(HERE/'receipt.json'),'artifacts_verified':len(receipt['artifacts'])}
(HERE/'snapshot-check.json').write_text(json.dumps(check,indent=2)+'\n');print(json.dumps(check))
