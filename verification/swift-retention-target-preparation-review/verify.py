#!/usr/bin/env python3
"""Read-only historical preparation acceptance binding; does not dispatch anything."""
from pathlib import Path,PurePosixPath
import hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parent.parent;P=ROOT/'verification/swift-retention-target-preparation';F=ROOT/'verification/swift-cache-retention-review'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
seal=json.loads((H/'seal.json').read_text());assert sha(H/'seal.json')==(H/'seal.sha256').read_text().strip()
for name,digest in seal['members'].items():
    n=PurePosixPath(name);assert not n.is_absolute()and '..'not in n.parts
    assert sha(H/name)==digest,name
for name,digest in seal['externalMembers'].items():assert sha(ROOT/name)==digest,name
summary=json.loads((H/'result-summary.json').read_text())
assert summary['preparationAccepted']is True and summary['blockingFindings']==[]
assert summary['preparationSealSHA256']==sha(P/'prepared-seal.json')=='1411f9d65c9e74193707378e044436a2152f451b41b6ac86429cf1a362ca4bea'
assert summary['finiteReviewSealSHA256']==sha(F/'seal.json')=='0d9c15a69baff78ff097f50c0fa8edaa402a6147811742407bdb76fd04c1868f'
prepared=json.loads((P/'prepared-seal.json').read_text())
for name,digest in prepared['files'].items():assert sha(P/name)==digest,name
for name,digest in prepared['externalFiles'].items():assert sha(ROOT/name)==digest,name
for name in ['independent-audit','read-only-packet-verifier']:
    path=H/'commands'/name;receipt=json.loads((path/'receipt.json').read_text());assert receipt['exitCode']==0 and receipt['boundInputsUnchanged']
    assert receipt['stdoutSHA256']==sha(path/'stdout')and receipt['stderrSHA256']==sha(path/'stderr')
assert not summary['targetSelected']and not summary['targetExecuted']and not summary['sourceRestored']and not summary['liveIntegrationAccepted']and not summary['gaAccepted']
print(json.dumps({'verified':True,'reviewMembers':len(seal['members']),'preparationMembers':len(prepared['files']),'preparationAccepted':True,'targetSelectedByThisReview':False,'targetExecutedByThisReview':False,'finiteReviewSealPreserved':True}))
