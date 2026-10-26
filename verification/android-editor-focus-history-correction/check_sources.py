#!/usr/bin/env python3
"""Supplemental source custody; executable tests, not syntax, establish host behavior."""
from pathlib import Path
import hashlib,json,difflib,datetime,sys,subprocess
D=Path(__file__).resolve().parent;B=D.parent/'android-editor-replacement-implementation'
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def mapping(folder):return {str(p.relative_to(folder)):ident(p) for p in sorted(folder.rglob('*')) if p.is_file()}
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def save(p,value):p.write_text(json.dumps(value,indent=2)+'\n')
def method(text,signature):
 start=text.index(signature);opening=text.index('{',start);depth=0
 for cursor in range(opening,len(text)):
  if text[cursor]=='{':depth+=1
  elif text[cursor]=='}':
   depth-=1
   if depth==0:return text[start:cursor+1]
 raise AssertionError(signature)
assert not (D/'seal.json').exists(),'Frozen packet is immutable'
base=mapping(B/'source');current=mapping(D/'source');assert set(base)==set(current)
changed=[name for name in current if base[name]!=current[name]]
assert changed==['NativeAppearanceViewsV2.java','NativeRenderer.java'],changed
old=(B/'source/NativeAppearanceViewsV2.java').read_text();new=(D/'source/NativeAppearanceViewsV2.java').read_text()
unchanged_methods=[]
for signature in ('private boolean denied()','boolean eventsAllowed()','private boolean live()','private void drain()','<T> T dispatch(','<T> T nativeValue(','void close(Attempt expected)','@Override public android.view.inputmethod.InputConnection onCreateInputConnection('):
 assert method(old,signature)==method(new,signature),signature
 unchanged_methods.append(signature)
for name in ('NativeAppearanceViewsV2.java','NativeRenderer.java'):
 (D/(name+'.diff')).write_text(''.join(difflib.unified_diff((B/'source'/name).read_text().splitlines(True),(D/'source'/name).read_text().splitlines(True),fromfile='frozen-base/'+name,tofile='focus-history/'+name)))
host=D/'runs'/sys.argv[1];cross=D/'runs'/sys.argv[2]
for run in (host,cross):
 assert json.loads((run/'receipt.json').read_text())['status']=='passed-'+run.name.split('-')[0]+'-only'
 assert mapping(run/'inputs/source')==current
 source_map=json.loads((run/'source-map.json').read_text())
 assert all(source_map[str(p.relative_to(run/'inputs'))]==ident(p) for p in (run/'inputs').rglob('*') if p.is_file())
 assert ident(run/'source-map.json')==json.loads((run/'source-freeze.json').read_text())['complete_source_map']
 assert json.loads((run/'source-freeze.json').read_text())['frozen_before_compiler'] is True
 for name,row in json.loads((run/'class-map.json').read_text()).items():assert ident(run/'classes'/name)==row
for name,row in json.loads((cross/'dex-map.json').read_text()).items():assert ident(cross/'dex'/name)==row
assert mapping(D/'host-leaves')==mapping(B/'host-leaves')
assert ident(D/'tests/EditorImplementationTests.java')==ident(B/'tests/EditorImplementationTests.java')
context=subprocess.run(['git','rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip()
save(D/'source-verification.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_revision_context_only':context,'base_product_tree':digest(base),'product_source_tree_digest':digest(current),'host_closure_tree_digest':digest({folder:mapping(D/folder) for folder in ('source','host-leaves','tests')}),'changed_product_files':changed,'unchanged_product_files':[name for name in current if name not in changed],'unchanged_sensitive_methods':unchanged_methods,'unchanged_complete_files_preserve':['NativeCoordinatorV2.java: both disposal guards and commit/finish interval','NativeOwnerV2.java and NativeRenderer requireV2Live SDK36 guards: owner complete byte identity; renderer guard body separately verified below','NativeEditorConnectionV2.java: all selected descriptor policies','OwnerLifecycleV2.java: owner/core lifecycle','NativeEnvironmentV2.java: observer/reporting API'],'selected_final_runs':[host.name,cross.name],'run_product_snapshots_match_current':True,'host_leaves_and_producer_52_controls_unchanged':True,'source_map':current,'scope':'Supplemental byte custody and selected unchanged-body checks only; no native/OTA/GA authority'})
assert method((B/'source/NativeRenderer.java').read_text(),'private void requireV2Live()')==method((D/'source/NativeRenderer.java').read_text(),'private void requireV2Live()')
receipts=[(p,json.loads(p.read_text())) for p in sorted((D/'runs').glob('*/receipt.json'))]
scratch=[str(p.relative_to(D)) for p in (D/'runs').rglob('owned-focus-history-*') if p.is_dir()]
assert not scratch,scratch
assert not list(D.rglob('__pycache__'))
assert all(row['cleanup']['scratch_removed'] and row['cleanup']['children_reaped'] and row['cleanup']['native_or_capture_processes_started_or_queried'] is False for _,row in receipts)
save(D/'cleanup.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'all_owned_children_returned_and_reaped':True,'scratch_removed_including_failed_runs':True,'native_ui_capture_processes_started_or_queried':False,'owned_run_receipts':[{'path':str(p.relative_to(D)),'status':row['status'],'receipt':ident(p)} for p,row in receipts],'retained':'Source/inputs/classes/dex/commands/output/failure evidence only','other_projects_touched':False})
print('PASS exact complete-source custody; two product files changed; all owned scratch/children cleaned')
