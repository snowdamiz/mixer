"""Read-only source/input custody verification; optionally record the observed result."""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def packet(name,digest,count,size):
 p=ROOT/'verification'/name;raw=(p/'seal.json').read_bytes();assert sha(raw)==digest
 s=json.loads(raw);assert s['member_count']==len(s['members'])==count
 assert sum(m['bytes'] for m in s['members'])==size
 assert {str(f.relative_to(p)) for f in p.rglob('*') if f.is_file()}=={m['path'] for m in s['members']}|{'seal.json'}
 for m in s['members']:
  b=(p/m['path']).read_bytes();assert len(b)==m['bytes'] and sha(b)==m['sha256'],m['path']
 return {'seal_sha256':digest,'member_count':count,'member_bytes':size,'exact_path_set':True}
def verify():
 selection=ROOT/'verification/swift-semantic-adapter-root-review/typed-result-codec-implementation-selection.json'
 selected='243a10a54d2887e83497190df56eeb1a74763c489eedfd0222dd8665cc034d55'
 assert sha(selection.read_bytes())==selected and selection.read_bytes()==(HERE/'selection.json').read_bytes()
 prep=packet('swift-retained-profile-real-binding-preparation','e6e4b3b1d32ade11ef3136f3e4416e86bb8c0a32889af6bbe62a1799cb093b01',69,859841)
 review=packet('swift-retained-profile-real-binding-contract-review','2b94fd0095c898f427809b8f088d5dc2708cdc3f33c8b12bd9936bb10da4d60e',22,48596)
 base=ROOT/'verification/swift-initial-profile-construction-implementation';seal_raw=(base/'seal.json').read_bytes()
 assert sha(seal_raw)=='50d1c32174ee4cbcade6095039261ea0ff8eed05680322bfb59b5de0dd4cd8b1'
 sealed={m['path']:m for m in json.loads(seal_raw)['members']}
 baseline=json.loads((HERE/'baseline-source-manifest-attempt-12.json').read_bytes())
 assert sha((HERE/'baseline-source-manifest-attempt-12.json').read_bytes())==sealed['source-manifest-attempt-12.json']['sha256']
 assert sha((HERE/'baseline-host-support-manifest.json').read_bytes())==sealed['host-support-manifest.json']['sha256']
 assert baseline['member_count']==140 and baseline['tree_sha256']=='71a00fde8a43aef5a7e6104932d3f0ca10a5989fb686c99828937b05aa363c7c'
 for m in baseline['members']:
  rel='source/vm/'+m['path'];b=(base/rel).read_bytes();assert sha(b)==m['sha256'] and len(b)==m['bytes']
  assert sealed[rel]['sha256']==m['sha256'] and sealed[rel]['bytes']==m['bytes']
  if m['path']=='src/experimental_swift_reactor/mod.rs':
   assert (HERE/rel).read_bytes()==b+b'\n// Pure unverified typed-result data; no public export or runtime route.\nmod diagnostic_result_v1;\n'
  else:assert (HERE/rel).read_bytes()==b
 support=json.loads((HERE/'baseline-host-support-manifest.json').read_bytes())
 for m in support['members']:
  rel=m['retained_path'];b=(base/rel).read_bytes()
  assert sha(b)==m['sha256'] and len(b)==m['bytes'] and (HERE/rel).read_bytes()==b
  assert sealed[rel]['sha256']==m['sha256'] and sealed[rel]['bytes']==m['bytes']
 source=json.loads((HERE/'source-manifest.json').read_bytes());members=[]
 for p in sorted((HERE/'source/vm').rglob('*')):
  if p.is_file():
   b=p.read_bytes();members.append({'path':str(p.relative_to(HERE/'source/vm')),'bytes':len(b),'sha256':sha(b)})
 assert source['member_count']==len(members)==142 and source['members']==members
 assert source['tree_sha256']==sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode())
 assert {str(p.relative_to(HERE)) for p in (HERE/'host').rglob('*') if p.is_file()}=={m['retained_path'] for m in support['members']}
 receipt=json.loads((HERE/'receipt.json').read_bytes());assert receipt['source_tree_sha256']==source['tree_sha256']
 assert receipt['runner']['sha256']==sha((HERE/'run_checks.py').read_bytes())
 return {'root_selection_sha256':selected,'preparation':prep,'independent_review':review,'baseline_seal_sha256':sha(seal_raw),'baseline_distribution_verified':140,'baseline_host_support_verified':11,'candidate_source_tree_sha256':source['tree_sha256'],'candidate_distribution':142,'candidate_host_support':11,'existing_changed_distribution_paths':['src/experimental_swift_reactor/mod.rs'],'all_other_original_distribution_and_host_support_bytes_identical':True,'no_source_or_support_sidecar':True}
if __name__=='__main__':
 report=verify()
 if '--record' in sys.argv:(HERE/'input-custody-after.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 print(json.dumps(report,sort_keys=True))
