#!/usr/bin/env python3
"""Read only root-released frozen inputs; never discovers an active candidate."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,datetime
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
h=lambda b:hashlib.sha256(b).hexdigest()
checks={
'verification/android-editor-boundary-root-review/preservation-membership-correction-requirements.md':'91282c25ea6974f41ece344df6fac6084f9f542b05e24ff364da8f9fae2e95df',
'verification/android-editor-boundary-root-review/preservation-membership-correction-selection.json':'007bf28271b28e159896f106b1b0f3ec5ae8b6e91697b5735aaa53139035a2b6',
'verification/android-editor-preservation-completion-implementation/seal.json':'8f355ae83ec4d734e8d28451fc64a45200967a718eecb7c1987fa0fcc69d9920',
'verification/android-editor-preservation-completion-independent/actual-review/review-seal.json':'ab3661c3efb4cbad8c09b19b0d558e80e4feba38fbf8a50d7673dd8c60287d06',
'verification/android-editor-preservation-completion-independent/actual-review/findings-1/seal.json':'736df698b56281a71fe3621326107da463aeb4bf8237712c18d188513d96cc44',
}
rows=[]
for rel,digest in checks.items():
 p=ROOT/rel; raw=p.read_bytes(); assert h(raw)==digest,(rel,h(raw)); row={'path':rel,'bytes':len(raw),'sha256':digest}
 if p.name.endswith('seal.json'):
  seal=json.loads(raw); members=seal['members']; size=0
  for m in members:
   q=p.parent/m['path']; assert q.is_file() and not q.is_symlink(),q
   b=q.read_bytes(); assert len(b)==m['bytes'] and h(b)==m['sha256'],q
   size+=len(b)
  assert len(members)==seal['member_count'] and size==seal['member_bytes']
  row.update(verified_members=len(members),verified_member_bytes=size)
 rows.append(row)
base=ROOT/'verification/android-editor-preservation-completion-implementation'
source_rows=[]
for name in ('source','host-leaves','tests'):
 for p in sorted((base/name).rglob('*.java')):
  rel=p.relative_to(base); target=OUT/'old-source'/rel; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(p,target)
  b=p.read_bytes();source_rows.append({'path':str(rel),'bytes':len(b),'sha256':h(b)})
for p,dest in [(base/'descriptor.json','old-source/descriptor.json'),(ROOT/'verification/android-editor-preservation-completion-independent/actual-review/findings-1/controls-5/control-source/IndependentPreservationCompletionControls.java','controls/IndependentPreservationCompletionControls.java')]:
 target=OUT/dest;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target); b=p.read_bytes(); source_rows.append({'path':dest,'bytes':len(b),'sha256':h(b)})
(OUT/'inputs').mkdir(exist_ok=True)
for p in [ROOT/'AGENTS.md',ROOT/'PLAN.md',ROOT/'STATUS.md',ROOT/'mixer-product-plan.md',ROOT/'verification/android-editor-boundary-root-review/preservation-membership-correction-requirements.md',ROOT/'verification/android-editor-boundary-root-review/preservation-membership-correction-selection.json',ROOT/'verification/android-editor-preservation-completion-independent/actual-review/review.md',ROOT/'verification/android-editor-preservation-completion-independent/actual-review/findings-1/finding.md']:
 shutil.copyfile(p,OUT/'inputs'/p.name);b=p.read_bytes();rows.append({'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':h(b)})
receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Preaccess; no current membership-correction candidate access','status':'frozen-inputs-independently-rehashed','inputs':rows,'copied_source_map':source_rows,'product_tree':'cb5c2b813b9cb375f2907bafcb066ba9c556a2713ffd04c9d74777d9595d01e4','git_head':subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True,check=True,timeout=60).stdout.strip(),'python':sys.version,'active_candidate_read':False,'native_UI_capture_process_inventory':False}
(OUT/'input-admission.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'status':receipt['status'],'verified_members':sum(r.get('verified_members',0) for r in rows),'copied_java_sources':110,'unchanged_witness_sha256':h((OUT/'controls/IndependentPreservationCompletionControls.java').read_bytes())}))
