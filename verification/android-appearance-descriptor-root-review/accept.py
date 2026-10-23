#!/usr/bin/env python3
import datetime,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;sha=lambda b:hashlib.sha256(b).hexdigest()
bindings={};checks=0
for folder in ['verification/android-appearance-descriptor/candidate-2','verification/android-appearance-descriptor-review/candidate-1']:
 p=ROOT/folder;r=json.loads((p/'receipt.json').read_text());assert r['status']=='passed'
 separators = (',', ':') if '-review/' in folder else (', ', ': ')
 assert sha(json.dumps(r['source_manifest'],sort_keys=True,separators=separators).encode())==r['source_manifest_sha256']
 for path,digest in r['source_manifest'].items():
  for target in [ROOT/path,p/'inputs'/path]:
   assert sha(target.read_bytes())==digest,path;checks+=1;bindings[str(target.relative_to(ROOT))]=digest
 for c in r['commands']:
  assert c['exit_code']==0;path=c['output'];digest=c['output_sha256'];assert sha((ROOT/path).read_bytes())==digest;checks+=1;bindings[path]=digest
 import gzip
 corpus=r['corpus']
 if '-review/' in folder:
  for name,digest in corpus.items():
   arch=p/name;assert sha(arch.read_bytes())==digest;checks+=1;bindings[str(arch.relative_to(ROOT))]=digest
 else:
  arch=p/'cases.tsv.gz';assert sha(arch.read_bytes())==corpus['archive_sha256'];assert sha(gzip.decompress(arch.read_bytes()))==corpus['sha256'];checks+=2;bindings[str(arch.relative_to(ROOT))]=sha(arch.read_bytes())
 bindings[str((p/'receipt.json').relative_to(ROOT))]=sha((p/'receipt.json').read_bytes());checks+=1
summary=ROOT/'verification/android-appearance-descriptor-review/review-summary.json';s=json.loads(summary.read_text());assert s['findings']==[] and s['case_count']==7990 and s['accepted']==182 and s['rejected']==7808
for p in [Path(__file__),summary]:bindings[str(p.relative_to(ROOT))]=sha(p.read_bytes());checks+=1
r={'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'integrator':'root','decision':'accepted-private-immutable-descriptor-data-only','binding_checks':checks,'bindings':bindings,'root_cases':7147,'root_accepted':544,'independent_cases':7990,'independent_accepted':182,'independent_java_assertions_per_mode':89438,'modes':['Java17 default','Java17 -Xint','Swift Debug','Swift Release'],'limits':'Private data decoding and exact acceptance/retained-value agreement only, no diagnostic classification equivalence. No Java default theme. No Android ART/build/runtime, installed font/resource/provenance, native widgets/rendering, JNI or signed health, physical parity, dogfood, release or GA acceptance.'};(HERE/'acceptance.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'checks':checks,'decision':r['decision']}))
