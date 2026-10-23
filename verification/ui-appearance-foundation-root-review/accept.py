#!/usr/bin/env python3
import datetime,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
P=ROOT/'verification/ui-appearance-foundation/candidate-1';R=ROOT/'verification/ui-appearance-foundation-review/candidate-2'
sha=lambda b:hashlib.sha256(b).hexdigest()
p=json.loads((P/'receipt.json').read_text());r=json.loads((R/'receipt.json').read_text());lock=json.loads((P/'input-lock.json').read_text())
assert p['status']==r['status']=='passed'
assert sha(json.dumps(lock['files'],sort_keys=True,separators=(',',':')).encode())==lock['tree_sha256']==p['source_tree_sha256']==r['producer_source_tree_sha256']
bindings={};checks=0
for path,digest in lock['files'].items():
 for target in [ROOT/path,P/'inputs'/path]:
  assert sha(target.read_bytes())==digest,path;checks+=1;bindings[str(target.relative_to(ROOT))]=digest
for path,digest in r['product_sha256'].items():assert sha((ROOT/path).read_bytes())==digest;checks+=1;bindings[path]=digest
for path,digest in r['reviewed_input_sha256'].items():assert sha((ROOT/path).read_bytes())==digest;checks+=1;bindings[path]=digest
for receipt in [p,r]:
 for command in receipt['commands']:
  assert command['exit_code']==0
  path=command['log'];digest=command['log_sha256'];assert sha((ROOT/path).read_bytes())==digest;checks+=1;bindings[path]=digest
for key,receipt in [('artifacts',p),('review_artifacts',r)]:
 for path,meta in receipt[key].items():
  data=(ROOT/path).read_bytes();assert sha(data)==meta['sha256'] and len(data)==meta['bytes'];checks+=1;bindings[path]=meta['sha256']
for mode in ['debug','release']:
 x=r['results'][mode];assert x['assertions']==2507093 and x['descriptorCases']==5153 and x['accepted']==535 and x['rejected']==4618 and not x['failures']
for path in [Path(__file__),P/'receipt.json',R/'receipt.json',R.parent/'review-summary.json',R.parent/'README.md']:
 bindings[str(path.relative_to(ROOT))]=sha(path.read_bytes());checks+=1
result={'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'decision':'accepted-pure-values-codec-math-default-only','integrator':'root','independent_reviewer':'appearance_foundation_review','source_tree_sha256':lock['tree_sha256'],'binding_checks':checks,'bindings':bindings,'producer_sdk_tests_per_mode':66,'independent_descriptor_cases_per_mode':5153,'independent_assertions_per_mode':2507093,'mobile_scope':'iOS arm64 and officialSwift6.3.3 Androidarm64 MixerCore/MixerUI module compilation, no execution','limits':'No native rendering, installed resources/fonts, signed authority, design parity, physical devices, FieldLog publication or GA qualification. sharedCandidate1 tokens remain provisional after baseline capture. Some compiled module artifact hashes are local observations; source snapshots and command logs are retained.'}
(HERE/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'checks':checks,'decision':result['decision']}))
