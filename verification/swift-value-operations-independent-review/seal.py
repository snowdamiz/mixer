#!/usr/bin/env python3
"""Seal only this bounded review's final inputs, outputs and independent decision."""
from pathlib import Path
import datetime, hashlib, json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
encode=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
successful=[]
for directory in (HERE/'results').iterdir():
    if not (directory/'receipt.json').exists():continue
    receipt=json.loads((directory/'receipt.json').read_text())
    if receipt['status']=='passed-selected-native-outcomes-accounting-review-separate':successful.append(directory)
OUT=max(successful)
receipt=json.loads((OUT/'receipt.json').read_text())
summary=json.loads((OUT/'verified-summary.json').read_text())
accounting=json.loads((OUT/'accounting-audit.json').read_text())
completion=json.loads((OUT/'completion-receipt.json').read_text())
assert receipt['sourceTreeSHA256']==summary['sourceTreeSHA256']==accounting['sourceTreeSHA256']
assert completion['status']=='passed-separate-metadata-replay-and-final-saved-checks'
assert completion['metadata']['passed']==1
assert len(receipt['binaries'])==8 and sum(x['passed'] for x in receipt['binaries'])==92
assert accounting['fields']==227 and accounting['typedPositions']==561
decision=dict(schema=1,status='INDEPENDENT_REVIEW_NO_BLOCKING_FINDINGS_FOR_PRIVATE_ZERO_FRAME_VALUE_OPERATIONS',
    sourceTreeSHA256=receipt['sourceTreeSHA256'],sourceCount=receipt['sourceCount'],producerSealSHA256=receipt['producerSealSHA256'],
    receipt=str((OUT/'receipt.json').relative_to(ROOT)),receiptSHA256=sha(OUT/'receipt.json'),
    verifiedSummarySHA256=sha(OUT/'verified-summary.json'),accountingAuditSHA256=sha(OUT/'accounting-audit.json'),
    completionReceiptSHA256=sha(OUT/'completion-receipt.json'),separateMetadataTests=1,
    selectedUnmodifiedProductTestExecutions=48,derivedIndependentTestExecutions=44,
    producerExecutableHashesAndRuntimeListsVerified=48,layoutConfigurations=8,fields=227,typedPositions=561,
    limitations=['macOS aarch64 host only','selected operation tests; not full product suite','derived probes add test-only wiring, not product instrumentation',
                 'logical named storage, not physical stack/RSS measurement','no initialize/invoke/run/active-frame/host/branch/memory implementation accepted',
                 '26 existing broad lint diagnostics remain','no simulator/emulator/physical-device/full Swift target/package/publication/GA qualification',
                 'root acceptance and final physical matrix remain separate'],
    rejectedCandidate1='rejected-candidate-1/findings.json',
    failedReviewerAttempts=['results/20261024T013720860263Z/receipt.json','results/20261024T013734663310Z/receipt.json'])
(HERE/'decision.json').write_bytes(encode(decision))
files={}
for p in sorted(HERE.rglob('*')):
    if not p.is_file():continue
    relative=p.relative_to(HERE)
    if 'build' in relative.parts or '__pycache__' in relative.parts or relative==Path('seal.json'):continue
    files[str(p.relative_to(ROOT))]=sha(p)
doc=ROOT/'docs/swift-value-operations-independent-review.md'
files[str(doc.relative_to(ROOT))]=sha(doc)
seal=dict(schema=1,status=decision['status'],observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
          sourceTreeSHA256=receipt['sourceTreeSHA256'],decisionSHA256=sha(HERE/'decision.json'),files=files)
(HERE/'seal.json').write_bytes(encode(seal))
assert all(sha(ROOT/name)==expected for name,expected in files.items())
print(json.dumps(dict(status=seal['status'],files=len(files),sourceTreeSHA256=seal['sourceTreeSHA256']),indent=2))
