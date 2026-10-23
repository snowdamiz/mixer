#!/usr/bin/env python3
"""Audit the exact producer tests, compiler branch and source-only review."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
qpath=HERE/'2026-10-23-candidate-1/receipt.json';q=load(qpath)
assert q['status']=='six cases passed in debug release and Swift TSan'
assert sha(HERE/'run.py')==q['driver_sha256']
for name,d in q['inputs'].items():assert sha(ROOT/name)==d and sha(Path(q['source_export'])/Path(name).name)==d
for files in q['products'].values():
 for name,d in files.items():assert sha(Path(name))==d
for row in q['commands']:assert row['exit_code']==0 and sha(qpath.parent/row['log'])==row['log_sha256']
for b in q['binaries'].values():assert sha(Path(b['path']))==b['sha256']
xpath=HERE/'xctest-branch-2/receipt.json';x=load(xpath)
assert x['status']=='XCTest conditional branch typechecked' and x['inputs']==q['inputs']
for row in x['commands']:assert row['exit_code']==0 and sha(xpath.parent/(row['name']+'.log'))==row['log_sha256']
reviewpath=ROOT/'verification/capability-attempt-signals-review/receipt.json'
assert sha(reviewpath)=='347560704e338ee03bc5621e1e62e644a34afc88e490abac03317e466e9d6ab0'
review=load(reviewpath);assert not review['findings']
receipt={'status':'six producer cases pass debug/release/Swift TSan; XCTest branch typechecks; independent source review has no findings',
 'inputs':q['inputs'],'producer_receipt_sha256':sha(qpath),'xctest_branch_receipt_sha256':sha(xpath),'source_review_sha256':sha(reviewpath),'seal_source_sha256':sha(Path(__file__)),
 'scope':'Internal fixed failure/effects latch, not a coordinator or durable transition.128 commit races and128 concurrent terminal reports per mode.',
 'limitations':q['limitations']+['Independent review is source-only. Single counted consumer, acyclic ownership, finish/join and publication ordering remain coordinator requirements.','Initial standalone XCTest typecheck omitted platform framework path; corrected search path passes without source edits.','No complete package/device/hosted/GA qualification inferred from these direct compiler runs.']}
(HERE/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(receipt['status'])
