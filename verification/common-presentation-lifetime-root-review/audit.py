#!/usr/bin/env python3
"""Root evidence audit for joined presentation lifetimes and CI ordering repair."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
count=0

def bound(path,digest):
 global count
 p=Path(path)
 if not p.is_absolute(): p=ROOT/p
 assert sha(p)==digest,str(p)
 count+=1

def bindings(value):
 if isinstance(value,dict):
  if 'path' in value and 'sha256' in value:
   bound(value['path'],value['sha256']);return
  for k,v in value.items():
   if isinstance(v,dict): bindings(v)
   elif isinstance(v,str) and len(v)==64: bound(k,v)

paths=['verification/common-presentation-lifetime/final-1/receipt.json','verification/common-presentation-lifetime/portable-1/receipt.json','verification/common-presentation-lifetime-review/final-1/receipt.json','verification/cold-start-cleanup-ci-repair/final-1/receipt.json']
receipts=[json.loads((ROOT/p).read_text()) for p in paths]
owner,portable,review,repair=receipts
assert owner['source_tree_sha256']==portable['source_tree_sha256']==review['owner_source_tree_sha256']
for r in receipts:
 for path,digest in r.get('source_files',{}).items(): bound(Path(r['source'])/path,digest)
 for c in r['commands']:
  assert c['exit']==c.get('expected_exit',0),c['name']
  bound(c['log'],c['sha256'])
 bindings(r['artifacts'])
for path,digest in owner['source_files'].items():bound(path,digest)
bindings(portable['extra_inputs']);bindings(portable['real_dependency_modules']);bindings(repair['tool_files'])
bound(repair['native_archive']['path'],repair['native_archive']['sha256'])
bound(owner['testing_macros']['path'],owner['testing_macros']['sha256'])
for r in [owner,review,repair]:
 bound(r['dependency_receipt'],r['dependency_receipt_sha256'])
 d=json.loads((ROOT/r['dependency_receipt']).read_text())
 base=Path(d['dylib']).parents[1]
 for path,digest in r['dependency_artifacts'].items():bound(base/path,digest)
 bound(d['source_manifest'],r['dependency_source_manifest_sha256'])
 source=json.loads((ROOT/d['source_manifest']).read_text())
 for path,digest in source['files'].items():bound(Path(d['source'])/path,digest)
for mode in ['debug','release','tsan']:
 def log(folder,name):return (ROOT/f'verification/{folder}/{mode}-{name}.log').read_text()
 assert 'Executed 14 tests, with 0 failures' in log('common-presentation-lifetime/final-1','xctests')
 assert 'Executed 13 tests, with 0 failures' in log('common-presentation-lifetime-review/final-1','tests')
 model=log('common-presentation-lifetime/final-1','model-tests')
 assert model.count(' skipped.')==1
 assert sum(s.startswith('✔ Test ') and '() passed after ' in s for s in model.splitlines())==13
 for name in ['repaired-pre-admission','original-queued','repaired-queued']:
  assert 'Executed 1 test, with 0 failures' in log('cold-start-cleanup-ci-repair/final-1',name)
 assert 'Executed 8 tests, with 0 failures' in log('cold-start-cleanup-ci-repair/final-1','repaired-unmodified')
 original=log('cold-start-cleanup-ci-repair/final-1','original-pre-admission')
 assert 'XCTAssertEqual failed' in original and 'XCTAssertTrue failed' in original
 for r in receipts:
  for c in r['commands']:
   if c['name'].startswith(mode):assert 'WARNING: ThreadSanitizer' not in (ROOT/c['log']).read_text()
seal_path=ROOT/'verification/common-presentation-lifetime-review/review.json'
seal=json.loads(seal_path.read_text())
bindings(seal['inputs']);bindings(seal['review_inputs'])
assert seal['findings']==[]
assert repair['repaired_test_sha256']==sha(ROOT/'capability-activation/Tests/MixerCapabilityActivationTests/CapabilityColdStartRuntimeTests.swift')
result={'observed_utc':datetime.now(timezone.utc).isoformat(),'command':'python3 verification/common-presentation-lifetime-root-review/audit.py','python':platform.python_version(),'auditor_sha256':sha(Path(__file__)),'verified_bindings':count,'receipts':{p:sha(ROOT/p) for p in paths},'independent_seal_sha256':sha(seal_path),'source_tree_sha256':owner['source_tree_sha256'],'result':'accepted common presentation lifetime and test-only CI ordering repair','review':['Root inspected all changed activation sources, move/finish authority, protected open catches, bind failure cleanup and final-close ordering.','Once-only pre-bind presentation obligation is acquired before model allocation; actual Task.value plus final MainActor retirement precedes typed receipt.','Only exact retired status permits reuse; pending/invariant/quarantine cannot free reservation. Unclaimed store admission drops during close.','Existing queued-native test permits early capacity return only after actual startup and close tails return while the native queue remains held. Deterministic original failure and both real orderings are retained.'],'scope':'Owner14 XCTest and13 Apple model/hidden-window passes plus1explicitvisible skip per Debug/Release/TSan; independent13XCTest plus public/testable API negatives per mode; portable host unsupported branch32cycles per mode. CI repair15expected run outcomes across modes. Root audit only, no additional independent executable rerun.','limitations':['Exact hosted cold-start interleaving remains unproven; replay proves the original test rejected a legal ordering.','TSan instruments rebuilt source; dependencies retain their explicitly recorded uninstrumented objects.','Apple receipts cover view/resource retirement, not destruction of publicly retained model shells.','Android signedUI/C/JNI binding remains unimplemented; portable branch tests are not Android builds.','No physical device, current positive visible-window, immutable consumer, signing/store/customer/operational or GA qualification.']}
(HERE/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'verified_bindings':count,'result':result['result']}))
