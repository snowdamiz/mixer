#!/usr/bin/env python3
"""Freeze only the owned accounting review and its document."""
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
from admit import verify_final,verify_old
ROOT=Path(__file__).resolve().parents[2];OWN=Path(__file__).resolve().parent
DOC=ROOT/'docs/swift-ordered-retention-analyzer-envelope-correction-final-accounting-review.md'
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def main():
 assert not (OWN/'seal.json').exists()
 final=json.loads((OWN/'final-review-receipt.json').read_bytes())
 assert final['operation_type_lifetime_bounds_supported'] is True
 assert final['combined_final_source_operation_type_lifetime_proof_accepted'] is False
 findings=json.loads((OWN/'findings.json').read_bytes());assert len(findings['findings'])==1 and findings['findings'][0]['id']=='F1'
 run=OWN/'commands/freeze-1';run.mkdir(parents=True,exist_ok=False)
 producer=verify_final();old=verify_old()
 write(run/'receipt.json',{'schema':1,'at':datetime.now(timezone.utc).isoformat(),'invocation':sys.orig_argv,'python':sys.version,'python_executable':str(Path(sys.executable).resolve()),'source_scope':'Final selected7b8237 bounds only; semantic R2 failure preserved; combined acceptance withheld.','producer_unchanged':producer,'old_unchanged':old,'native_capture_or_runtime_started':False,'producer_runner_executed':False,'cleanup':'Only owned immutable source/evidence copies remain; no executable or native/runtime scratch created or other process touched.','failure_receipts_retained':['commands/admission-1/receipt.json','commands/closure-1/behavior-evidence/verification/swift-analyzer-envelope-correction-behavior-review/final-review/runs/run-2/independent-tests/receipt.json']})
 files=sorted([p for p in OWN.rglob('*') if p.is_file()]+[DOC],key=lambda p:str(p.relative_to(ROOT)))
 assert not any(p.suffix in ['.pyc','.rlib'] or p.is_symlink() for p in files)
 members=[]
 for p in files:
  b=p.read_bytes();members.append({'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':sha(b)})
 seal={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'status':'frozen-bounds-supported-combined-acceptance-withheld-F1','members':members,'member_count':len(members),'bytes':sum(m['bytes'] for m in members),'source_sha256':'7b8237abbaec492e595508eb7456dab38fbb0d92d8d3cd5a88184f7c1082b9d1','scope':'Only owned final accounting review and document. Historical freezes/producer remain unchanged.'}
 write(OWN/'seal.json',seal);digest=sha((OWN/'seal.json').read_bytes());(OWN/'seal.sha256').write_text(digest+'\n')
 for m in members:
  data=(ROOT/m['path']).read_bytes();assert len(data)==m['bytes'] and sha(data)==m['sha256']
 assert producer==verify_final() and old==verify_old()
 print(json.dumps({'seal_sha256':digest,'members':len(members),'bytes':seal['bytes'],'bounds_supported':True,'combined_accepted':False,'findings':1},sort_keys=True))
if __name__=='__main__':main()
