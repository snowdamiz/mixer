#!/usr/bin/env python3
"""Verify this independent historical result review without rerunning anything."""
from pathlib import Path,PurePosixPath
import hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parent.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
seal=json.loads((H/'seal.json').read_text());assert sha(H/'seal.json')==(H/'seal.sha256').read_text().strip()
for name,digest in seal['members'].items():
    n=PurePosixPath(name);assert not n.is_absolute()and '..'not in n.parts
    assert sha(H/name)==digest,name
for name,digest in seal['externalMembers'].items():assert sha(ROOT/name)==digest,name
audit=json.loads((H/'audit.json').read_text())
for name,digest in audit['bindings'].items():assert sha(ROOT/name)==digest,name
root=json.loads((ROOT/'verification/swift-retention-runtime/seal.json').read_text())
for item in root['files']:assert sha(ROOT/item['path'])==item['sha256']
summary=json.loads((H/'result-summary.json').read_text())
assert summary['resultEvidenceAccepted']and summary['blockingFindings']==[]and summary['candidateRejectedForLiveIntegration']
assert summary['actualTargetAttempts']==1 and summary['reviewNewAttempts']==0 and not summary['retrySelected']and not summary['liveIntegrationAccepted']and not summary['gaAccepted']
r=json.loads((H/'command/receipt.json').read_text());assert r['exitCode']==0 and r['boundInputsUnchanged']
assert r['stdoutSHA256']==sha(H/'command/stdout')and r['stderrSHA256']==sha(H/'command/stderr')
print(json.dumps({'verified':True,'reviewMembers':len(seal['members']),'rootResultMembers':len(root['files']),'rejectionEvidenceAccepted':True,'candidateRejectedForLiveIntegration':True,'newAttempts':0,'retrySelected':False}))
