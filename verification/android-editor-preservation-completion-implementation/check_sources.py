#!/usr/bin/env python3
"""Supplemental custody and bytecode evidence. Never native/OTA authorization."""
from pathlib import Path
import hashlib,json,difflib,datetime,re,subprocess
D=Path(__file__).resolve().parent;B=D.parent/'android-editor-focus-history-correction';A=D.parent/'android-editor-focus-history-independent/actual-review'
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def mapping(folder):return {str(p.relative_to(folder)):ident(p) for p in sorted(folder.rglob('*')) if p.is_file()}
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def save(p,value):p.write_text(json.dumps(value,indent=2)+'\n')
def method(source,signature):
 start=source.index(signature);opening=source.index('{',start);depth=0
 for i in range(opening,len(source)):
  if source[i]=='{':depth+=1
  elif source[i]=='}':
   depth-=1
   if depth==0:return source[start:i+1]
 raise AssertionError(signature)
assert not (D/'seal.json').exists()
base=mapping(B/'source');current=mapping(D/'source');assert len(current)==16 and set(base)==set(current)
changed=[name for name in current if current[name]!=base[name]];assert changed==['NativeAppearanceViewsV2.java','NativeCoordinatorV2.java','NativeRenderer.java']
for name in changed:(D/(name+'.diff')).write_text(''.join(difflib.unified_diff((B/'source'/name).read_text().splitlines(True),(D/'source'/name).read_text().splitlines(True),fromfile='sealed-base/'+name,tofile='preservation-completion/'+name)))
hook='''            if (candidate != null) {
                try { renderer.completeFailedV2(candidate, ledger.primary, ledger.firstFatal); }
                catch (RuntimeException | Error cleanup) { remember(cleanup); }
            }
'''
coordinator=(D/'source/NativeCoordinatorV2.java').read_text();assert coordinator.count(hook)==2
assert coordinator.replace(hook,'')==(B/'source/NativeCoordinatorV2.java').read_text()
unchanged={}
for name,signatures in {'NativeRenderer.java':['private void requireV2Live()','void publishScalarV2(','void sealScalarV2()','private void requireTransactionV2(','private void validateV2('],'NativeAppearanceViewsV2.java':['private boolean denied()','boolean eventsAllowed()','private boolean live()','private void drain()','<T> T dispatch(','<T> T nativeValue(','void close(Attempt expected)','@Override public android.view.inputmethod.InputConnection onCreateInputConnection(']}.items():
 for signature in signatures:
  before=method((B/'source'/name).read_text(),signature);after=method((D/'source'/name).read_text(),signature);assert before==after,(name,signature);unchanged[name+':'+signature]=hashlib.sha256(after.encode()).hexdigest()
assert mapping(D/'host-leaves')==mapping(B/'host-leaves')
assert mapping(D/'cross-source')==mapping(B/'cross-source')
assert ident(D/'tests/EditorImplementationTests.java')==ident(B/'tests/EditorImplementationTests.java')
assert (D/'tests/IndependentFocusHistoryControls.java').read_text().replace('IndependentFocusHistoryControls','FocusHistoryControls')==(A/'FocusHistoryControls.java').read_text()
for signature in ('private static void postAttachRollback()','private static void crossRendererEnd()'):
 assert method((D/'tests/IndependentFocusHistoryControls.java').read_text(),signature)==method((A/'FocusHistoryControls.java').read_text(),signature)
host=D/'runs/host-6';cross=D/'runs/cross-2'
for run in (host,cross):
 assert json.loads((run/'receipt.json').read_text())['status']=='passed-'+run.name.split('-')[0]+'-only'
 assert mapping(run/'inputs/source')==current
 assert mapping(run/'inputs/tests')==mapping(D/'tests')
 source_map=json.loads((run/'source-map.json').read_text());assert source_map==mapping(run/'inputs')
 assert ident(run/'source-map.json')==json.loads((run/'source-freeze.json').read_text())['complete_source_map']
 for name,row in json.loads((run/'class-map.json').read_text()).items():assert ident(run/'classes'/name)==row
for name,row in json.loads((cross/'dex-map.json').read_text()).items():assert ident(cross/'dex'/name)==row
# This check supplements complete-source runtime controls. The success tail has no invocation,
# allocation, explicit throw, monitor or iterator bytecode after the preflight's last athrow.
text=(host/'completion-bytecode.stdout').read_text()
def code(signature,next_signature):
 start=text.index(signature);end=text.index(next_signature,start);return text[start:end]
finish=code('  void finishV2(', '  void validateAttachedV2(')
begin=code('  public void fieldPreservationBegin(', '  public void fieldPreservationEnd(')
proof={}
for name,body in [('finishV2',finish),('fieldPreservationBegin',begin)]:
 instructions=[line for line in body.splitlines() if re.match(r'\s+\d+:',line)];last_throw=max(i for i,line in enumerate(instructions) if re.search(r': athrow\b',line));tail=instructions[last_throw+1:]
 assert tail and all(not re.search(r': (?:invoke\w*|new\w*|anewarray|multianewarray|athrow|monitor\w*)\b',line) for line in tail),(name,tail)
 (D/(name+'-scalar-tail.bytecode')).write_text('\n'.join(tail)+'\n')
 proof[name]={'bytecode_tail_after_last_refusal_athrow':tail[0].strip(),'instruction_count':len(tail),'tail':ident(D/(name+'-scalar-tail.bytecode')),'no_invocation_allocation_explicit_throw_or_monitor':True}
for signature,end in [('  boolean fieldPreservationIdentityV2(', '  private boolean preservationCohortV2('),('  private boolean preservationCohortV2(', '  private boolean preservationFailureFundedV2(')]:
 body=code(signature,end);assert not re.search(r': (?:invoke\w*|new\w*|anewarray|multianewarray)\b',body),signature
proof['preflight_callgraph']={'scalar_only_own_helpers':['fieldPreservationIdentityV2','preservationCohortV2'],'other_success_preflight_call':'java.util.ArrayDeque.isEmpty only','error_only_calls':['Json.bad','sealScalarV2'],'no_success_main_current_Input_snapshot_native_JNI_event_or_owner_calls':True,'fixed_array_membership':'journal.states final array/stateCount constructed before attachment; no production membership mutation'}
save(D/'scalar-completion-proof.json',{'scope':'Actual compiled complete source bytecode plus runtime host probes; not native qualification','host_bytecode':ident(host/'completion-bytecode.stdout'),'cross_bytecode':ident(cross/'completion-bytecode.stdout'),'success_tail':proof,'runtime_probes':{'three_field_success':'runs/host-6/completion-outcomes.stdout','original_commit_interval':'runs/host-6/producer-52.stdout','refresh':'runs/host-6/completion-refresh.stdout'},'limits':['No guarantee of recovery from asynchronous VM interruption between scalar writes','Selection getters are uninstrumented scalar host leaves; individual callback injection at those exact getters is unmodeled. Native runtime remains paused.','Editable getter/span reentry controls use an explicitly adversarial host Editable subclass; they do not prove Android framework behavior.']})
context=subprocess.run(['git','rev-parse','HEAD'],check=True,capture_output=True,text=True,timeout=60).stdout.strip()
save(D/'source-verification.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_revision_context_only':context,'base_product_tree':digest(base),'product_source_tree_digest':digest(current),'host_closure_tree_digest':digest({folder:mapping(D/folder) for folder in ('source','host-leaves','tests')}),'changed_product_files':changed,'unchanged_product_files':[name for name in current if name not in changed],'exact_coordinator_delta':'only two selected completeFailedV2 try/catch blocks; removing those restores whole-file base bytes','unchanged_sensitive_methods':unchanged,'unchanged_owner_core_observer_adapter_and_both_SDK36_guards':True,'selected_final_runs':[host.name,cross.name],'all_final_inputs_and_artifacts_verified':True,'unchanged_finding_witness_assertions':True,'host_leaves_original52_crossJNI_bytes_unchanged':True,'source_map':current})
receipts=[(p,json.loads(p.read_text())) for p in sorted(D.rglob('receipt.json')) if 'cleanup' in json.loads(p.read_text()) and 'scratch_removed' in json.loads(p.read_text())['cleanup']]
assert not [p for p in D.rglob('owned-*') if p.is_dir()]
assert not list(D.rglob('__pycache__'))
assert all(row['cleanup']['scratch_removed'] and row['cleanup']['children_reaped'] and row['cleanup']['native_or_capture_processes_started_or_queried'] is False for _,row in receipts)
save(D/'cleanup.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'owned_child_bound_seconds':60,'all_owned_children_reaped':True,'all_owned_scratch_tmp_removed_including_failed_runs':True,'native_ui_capture_or_process_inventory_started_or_queried':False,'other_projects_touched':False,'run_receipts':[{'path':str(p.relative_to(D)),'status':row['status'],'receipt':ident(p)} for p,row in receipts],'retained':'Source/inputs/classes/dex/commands/output and original failures only; deliberate imbalanced host custody ends with its bounded JVM, not native reclamation evidence'})
print('PASS 16-file source custody; only 3 selected product files changed; exact two coordinator hooks; unchanged witnesses; actual scalar tail bytecode; owned cleanup')
