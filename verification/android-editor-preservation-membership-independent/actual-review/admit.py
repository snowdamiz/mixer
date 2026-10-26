from pathlib import Path
import hashlib,json,shutil,datetime,subprocess,sys
D=Path(__file__).resolve().parent;R=D.parents[2]
def ident(p):b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
inputs={
'verification/android-editor-preservation-membership-correction/seal.json':'620bfefe8cde4b63c2101db76af991fcc1933276f9c1e8d8d1aa1e3db8f0bf0e',
'verification/android-editor-preservation-membership-independent/preaccess/seal.json':'1890771da4c76e8010a196a7cd2f5c4a9ebdef2f915878367e079c1c7accd863',
'verification/android-editor-boundary-root-review/preservation-membership-candidate-custody.json':'a0d868342c67c0bea238f08bb1fc97b221f41fcc8cd3bac08810f5522fa8338a',
'verification/android-editor-boundary-root-review/preservation-membership-preaccess-custody.json':'13b62674b42bc9bfb1e24f071108bcca9c456d11aba0a8896be019aa9d0f1c87'}
rows=[]
for rel,sha in inputs.items():
 p=R/rel;assert ident(p)['sha256']==sha,(p,ident(p));j=json.loads(p.read_text());row={'path':rel,**ident(p)}
 if 'members'in j:
  assert len(j['members'])==j['member_count'];size=0
  for m in j['members']:
   q=p.parent/m['path'];assert not q.is_symlink() and q.is_file() and ident(q)=={k:m[k] for k in ('bytes','sha256')},q;size+=m['bytes']
  assert size==j['member_bytes'];manifest=json.loads((p.parent/'manifest.json').read_text());assert {m['path']:m for m in manifest['members']}=={m['path']:m for m in j['members'] if m['path']!='manifest.json'}
  row.update(verified_members=j['member_count'],verified_bytes=size)
 rows.append(row)
base=R/'verification/android-editor-preservation-membership-correction'
for folder in ('source','host-leaves','tests','cross-source'):shutil.copytree(base/folder,D/'frozen'/folder)
for name in ('descriptor.json','implementation.md','scalar-completion-proof.json','source-verification.json','summary.json','NativeRenderer.java.diff','run.py'):
 target=D/'frozen'/name;shutil.copyfile(base/name,target)
ctrl=D/'independent-controls';ctrl.mkdir()
pre=R/'verification/android-editor-preservation-membership-independent/preaccess'
shutil.copyfile(pre/'controls/IndependentMembershipControls.java',ctrl/'IndependentMembershipControls.java')
shutil.copyfile(pre/'controls/IndependentPreservationCompletionControls.java',ctrl/'IndependentPreservationCompletionControls.java')
shutil.copyfile(R/'verification/android-editor-preservation-completion-independent/actual-review/controls/FocusHistoryControls.java',ctrl/'FocusHistoryControls.java')
assert ident(ctrl/'IndependentPreservationCompletionControls.java')['sha256']=='73c01e685e0eb768109535b85284c06e2abfa752b4443a9401f3d091ae2b2686'
assert ident(ctrl/'FocusHistoryControls.java')['sha256']=='5f120d62cc8559c40e92fb609c368caf88870712b7e70567f306f419ce57caae'
old=pre/'old-source';changed=[]
for p in sorted((D/'frozen/source').glob('*.java')):
 if p.read_bytes()!=(old/'source'/p.name).read_bytes():changed.append(p.name)
assert changed==['NativeRenderer.java']
for folder in ('host-leaves','cross-source'):
 original=old/folder if folder=='host-leaves' else R/'verification/android-editor-preservation-completion-implementation/cross-source'
 assert {str(p.relative_to(original)):ident(p) for p in original.rglob('*') if p.is_file()}=={str(p.relative_to(D/'frozen'/folder)):ident(p) for p in (D/'frozen'/folder).rglob('*') if p.is_file()}
for p in (old/'tests').glob('*.java'):assert p.read_bytes()==(D/'frozen/tests'/p.name).read_bytes()
def mapping(p):return {str(q.relative_to(p)):ident(q) for q in sorted(p.rglob('*')) if q.is_file()}
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
product=digest(mapping(D/'frozen/source'));host=digest({f:mapping(D/'frozen'/f) for f in ('source','host-leaves','tests')})
assert product=='a5e4888b96995bf768062bd9c2f1573dc440a4fe22270a205ab5550e79f625e4' and host=='3ea68dc45ab5235edde6bdaea9b38045e6d60c6f8ae54583b5544a9e00c4d021'
revision=subprocess.run(['git','rev-parse','HEAD'],cwd=R,capture_output=True,text=True,timeout=60,check=True)
save(D/'admission.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'authorization':'Root explicitly released exact frozen candidate in this agent message before access','inputs':rows,'product_tree':product,'complete_host_tree':host,'changed_product_files':changed,'other15_product_files_original86leaves_crossJNI_prior8tests_byte_identical':True,'frozen_source_map':mapping(D/'frozen'),'independent_controls_map':mapping(ctrl),'git_head_context':revision.stdout.strip(),'python':sys.version,'no_native_UI_capture_or_process_inventory':True})
print('ADMITTED',sum(r.get('verified_members',0) for r in rows),'members; exact source copied; changed',changed,'product',product)
