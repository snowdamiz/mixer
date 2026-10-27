from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(b): return hashlib.sha256(b).hexdigest()
def read(p): return json.loads(p.read_bytes())
def verify_packet(name,digest,count,size):
 p=ROOT/'verification'/name
 assert sha((p/'seal.json').read_bytes())==digest
 s=read(p/'seal.json'); assert s['member_count']==count
 assert sum(x['bytes'] for x in s['members'])==size
 assert {str(f.relative_to(p)) for f in p.rglob('*') if f.is_file()}=={x['path'] for x in s['members']}|{'seal.json'}
 for x in s['members']:
  b=(p/x['path']).read_bytes(); assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['path']
 return {'path':str(p.relative_to(ROOT)),'seal_sha256':digest,'members':count,'bytes':size,'exact_path_set':True}
selection=ROOT/'verification/swift-semantic-adapter-root-review/typed-result-codec-implementation-selection.json'
assert sha(selection.read_bytes())=='243a10a54d2887e83497190df56eeb1a74763c489eedfd0222dd8665cc034d55'
review=verify_packet('swift-retained-profile-real-binding-contract-review','2b94fd0095c898f427809b8f088d5dc2708cdc3f33c8b12bd9936bb10da4d60e',22,48596)
prep=verify_packet('swift-retained-profile-real-binding-preparation','e6e4b3b1d32ade11ef3136f3e4416e86bb8c0a32889af6bbe62a1799cb093b01',69,859841)
base=ROOT/'verification/swift-initial-profile-construction-implementation'
assert sha((base/'seal.json').read_bytes())=='50d1c32174ee4cbcade6095039261ea0ff8eed05680322bfb59b5de0dd4cd8b1'
sealed={x['path']:x for x in read(base/'seal.json')['members']}
man=read(base/'source-manifest-attempt-12.json'); support=read(base/'host-support-manifest.json')
assert man['member_count']==140 and support['member_count']==11
assert man['tree_sha256']=='71a00fde8a43aef5a7e6104932d3f0ca10a5989fb686c99828937b05aa363c7c'
for m in man['members']:
 rel='source/vm/'+m['path']; s=sealed[rel]; assert all(s[k]==m[k] for k in ['sha256','bytes'])
 target=HERE/rel; target.parent.mkdir(parents=True,exist_ok=True)
 b=(base/rel).read_bytes(); assert sha(b)==m['sha256'] and len(b)==m['bytes']; target.write_bytes(b); assert target.read_bytes()==b
for m in support['members']:
 rel=m['retained_path']; s=sealed[rel]; assert all(s[k]==m[k] for k in ['sha256','bytes'])
 b=(base/rel).read_bytes(); assert sha(b)==m['sha256'] and len(b)==m['bytes']
 target=HERE/rel; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(b); assert target.read_bytes()==b
for name in ['source-manifest-attempt-12.json','host-support-manifest.json']:
 shutil.copyfile(base/name,HERE/('baseline-'+name))
shutil.copyfile(selection,HERE/'selection.json')
(HERE/'custody.json').write_text(json.dumps({'selection_sha256':sha(selection.read_bytes()),'review':review,'preparation':prep,'baseline_seal_sha256':sha((base/'seal.json').read_bytes()),'baseline_distribution':140,'unchanged_host_support':11,'copied_identities_verified_against_seal':151},indent=2)+'\n')
print('Verified frozen review/preparation and copied all 151 sealed baseline identities.')
