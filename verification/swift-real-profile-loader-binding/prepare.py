"""Copy exact frozen source/support bytes; never rerun frozen producers."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(b): return hashlib.sha256(b).hexdigest()
def load(p): return json.loads(p.read_bytes())
def sealed(name,digest,complete):
 p=ROOT/'verification'/name
 b=(p/'seal.json').read_bytes(); assert sha(b)==digest
 s=load(p/'seal.json'); sm={m['path']:m for m in s['members']}
 if complete:
  assert {str(f.relative_to(p)) for f in p.rglob('*') if f.is_file()}==set(sm)|{'seal.json'}
  for name,m in sm.items():
   b=(p/name).read_bytes(); assert len(b)==m['bytes'] and sha(b)==m['sha256'],name
 return p,s,sm
base,bs,bm=sealed('swift-initial-profile-construction-implementation','50d1c32174ee4cbcade6095039261ea0ff8eed05680322bfb59b5de0dd4cd8b1',False)
codec,cs,cm=sealed('swift-typed-result-codec-implementation','4f5e0ffd63c343511948d1bacc933698cd36369f94b3b96f3047ff325cd94b86',True)
checks=[]
for name,digest in [('swift-typed-result-codec-independent','8f22a9842cb609027d6f6cbe808eefb13d56cd52b68ef6cddec9a9926f5fc16b'),('swift-retained-profile-real-binding-preparation','e6e4b3b1d32ade11ef3136f3e4416e86bb8c0a32889af6bbe62a1799cb093b01'),('swift-retained-profile-real-binding-contract-review','2b94fd0095c898f427809b8f088d5dc2708cdc3f33c8b12bd9936bb10da4d60e')]:
 p,s,_=sealed(name,digest,True); checks.append({'path':str(p.relative_to(ROOT)),'seal_sha256':digest,'members':s['member_count'],'bytes':sum(m['bytes'] for m in s['members']),'all_members_verified':True})
source=load(codec/'source-manifest.json'); support=load(codec/'baseline-host-support-manifest.json'); original=load(base/'source-manifest-attempt-12.json')
assert source['member_count']==142 and support['member_count']==11 and original['member_count']==140
for m in original['members']:
 rel='source/vm/'+m['path']; assert all(bm[rel][k]==m[k] for k in ['bytes','sha256']); b=(base/rel).read_bytes(); assert len(b)==m['bytes'] and sha(b)==m['sha256']
for m in source['members']:
 rel='source/vm/'+m['path']; assert all(cm[rel][k]==m[k] for k in ['bytes','sha256']); b=(codec/rel).read_bytes(); assert len(b)==m['bytes'] and sha(b)==m['sha256']; target=HERE/rel; target.parent.mkdir(parents=True,exist_ok=True); assert not target.exists(); target.write_bytes(b)
for m in support['members']:
 rel=m['retained_path']; assert all(cm[rel][k]==m[k] for k in ['bytes','sha256']); b=(codec/rel).read_bytes(); assert len(b)==m['bytes'] and sha(b)==m['sha256']; target=HERE/rel; target.parent.mkdir(parents=True,exist_ok=True); assert not target.exists(); target.write_bytes(b)
for name,value in [('baseline-source-manifest.json',source),('baseline-host-support-manifest.json',support),('input-custody.json',{'codec_seal_sha256':sha((codec/'seal.json').read_bytes()),'codec_root_acceptance_observed':False,'codec_all235_members_verified':True,'codec_bytes':sum(m['bytes'] for m in cs['members']),'accepted_baseline_seal_sha256':sha((base/'seal.json').read_bytes()),'accepted_baseline_source140_verified':True,'source142_copied':True,'host11_unchanged_copied':True,'other_frozen_packets':checks})]: (HERE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
print('Copied exact frozen source142 + host11; complete codec/review/preparation custody verified; no implementation or acceptance implied.')
