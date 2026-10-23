from pathlib import Path
import json,hashlib,gzip,datetime,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];review=ROOT/'verification/android-appearance-resolution-independent-review';producer=ROOT/'verification/android-appearance-resolution'
sha=lambda b:hashlib.sha256(b).hexdigest();bindings={}
def bind(p,digest=None):
 p=Path(p);h=sha(p.read_bytes());assert digest is None or h==digest,str(p);bindings[str(p.relative_to(ROOT))]=h;return h
s=json.loads((review/'seal.json').read_bytes())
actual={str(p.relative_to(review)):sha(p.read_bytes()) for p in sorted(review.rglob('*')) if p.is_file() and '.build' not in p.parts and p!=review/'seal.json'}
assert actual==s['files'] and len(actual)==95
assert sha(json.dumps(actual,sort_keys=True,separators=(',',':')).encode())==s['tree_sha256']
for p,d in actual.items():bind(review/p,d)
bind(review/'seal.json')
a=json.loads((review/'acceptance.json').read_bytes());assert not a['actionable_blockers']
for candidate in ['candidate-1','environment-1']:
 r=json.loads((review/candidate/'receipt.json').read_bytes());assert r['status']=='passed'
 assert sha(json.dumps(r['source_manifest'],sort_keys=True).encode())==r['source_manifest_sha256']
 for p,d in r['source_manifest'].items():bind(ROOT/p,d);bind(review/candidate/'inputs'/p,d)
 for c in r['commands']:assert c['exit_code']==0;bind(ROOT/c['output'],c['output_sha256'])
for p,d in json.loads((review/'candidate-1/producer-evidence-bindings.json').read_bytes()).items():bind(ROOT/p,d)
r=json.loads((producer/'candidate-3/receipt.json').read_bytes());assert r['status']=='passed' and r['swift_debug_release_equal']
for p,d in r['source_manifest'].items():bind(ROOT/p,d);bind(producer/'candidate-3/inputs'/p,d)
for c in r['commands']:assert c['exit_code']==0;bind(ROOT/c['output'],c['output_sha256'])
for mode in ['debug','release']:
 for suffix,rawkey,archivekey in [('.tsv.gz','sha256','archive_sha256'),('.values.jsonl.gz','values_sha256','values_archive_sha256')]:
  p=producer/'candidate-3'/(mode+'-oracle'+suffix);data=p.read_bytes();bind(p,r[mode+'_oracle'][archivekey]);assert sha(gzip.decompress(data))==r[mode+'_oracle'][rawkey]
r=json.loads((review/'candidate-1/receipt.json').read_bytes())
for mode in ['debug','release']:
 for key,suffix in [('tsv','.tsv.gz'),('values','.values.jsonl.gz')]:
  p=review/'candidate-1'/(mode+'-oracle'+suffix);assert sha(gzip.decompress(p.read_bytes()))==r[mode+'_oracle'][key]['sha256']
 for execution in ['default','interpreted']:
  p=review/'candidate-1'/(mode+'-'+execution+'.jsonl.gz');bind(p,r[mode+'_'+execution]['archive_sha256']);assert sha(gzip.decompress(p.read_bytes()))==r[mode+'_'+execution]['sha256']
  text=(review/'candidate-1'/f'java-{mode}-{execution}.log').read_text();assert 'accepted=98 rejected=86 knownPacketBoundary=3' in text and 'assertions=595286' in text
  checked=json.loads((review/'candidate-1'/f'contract-{mode}-{execution}.log').read_text());assert checked=={'cases':187,'contract_assertions':40756,'status':'passed'}
for mode in ['default','interpreted']:assert 'assertions=214 status=passed' in (review/'environment-1'/f'java-{mode}.log').read_text()
for p in [producer/'handoff-summary.json',producer/'README.md',review/'acceptance.json',HERE/'accept.py']:bind(p)
result={'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':'root','decision':'accepted-private-cross-platform-appearance-resolution-data','source_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'binding_count':len(bindings),'bindings':dict(sorted(bindings.items())),'producer_cases_per_run':3907,'independent_cases_per_run':187,'independent_java_assertions_per_run':595286,'independent_contract_assertions_per_run':40756,'environment_assertions_per_java_mode':214,'modes':'Swift Debug/Release x Java default/-Xint; JDK25 runtime targeting Java17','limitations':['Three known packet restrictions retained: explicit HStack first/lastTextBaseline and nested list. These are not parity passes.','Pure immutable data only; sharedCandidate1 remains provisional and does not yet match measured iOS appearance.','Native style/resource/font/display/input/accessibility/ART/physical parity, signed authority, immutable published FieldLog and all GA gates remain pending.']}
(HERE/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',len(bindings),'root bindings; complete independent and producer outputs checked')
