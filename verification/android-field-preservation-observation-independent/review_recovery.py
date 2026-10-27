#!/usr/bin/env python3
"""Validate the two supplemental host controls and exact cleanup evidence."""
from pathlib import Path
import hashlib
import json
import sys
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent
ROOT=D.parent.parent
F=ROOT/'verification/android-field-preservation-observation-controls'
def load(p):return json.loads(p.read_bytes())
def identity(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def main():
 exact=load(D/'run-exact/actual-results.json');actual=load(D/'run-recovery/actual-results.json')
 assert actual['rows']==exact['rows'] and actual['invocations']==56 and actual['checks']==747
 assert actual['getter_entries']==actual['checking_true_at_entries']==24
 assert actual['host_threads_started']==actual['host_threads_joined']==3
 assert actual['actual_final_counts']==[0,0,0] and actual['original_edit_completed_after_restores'] and actual['failure_latch_clear']
 owner,retry=actual['independent_controls'];assert owner['control']=='original-exact-owner-thread-exception'
 assert owner['before']==owner['after'] and not owner['checking_after'] and owner['getter_outcomes_added']==owner['actual_event_delta']==0
 assert owner['exception_type']=='java.lang.IllegalStateException' and owner['exception_message']=='V2 requires UI owner thread'
 assert retry['control']=='immediate-exact-retry-after-injected-getter-failure' and retry['before']==retry['after'] and not retry['checking_after']
 assert retry['no_scope_snapshot_checking_restore_between_attempts'] and retry['final_Record_view_Input_unchanged'] and retry['retry_exception_reference']=='null'
 failed,returned=retry['getter_outcomes'];assert failed['completion']=='exception' and failed['exception_reference']==retry['exception_reference'] and returned['completion']=='return'
 assert returned['returned_editable_immutable_value']['reference']==retry['before']['editable'] and returned['returned_editable_immutable_value']['text']=='hello'
 for outcome in (failed,returned):
  assert outcome['checking_at_outcome'] and len(outcome['production_frames'])<24
  assert any(frame['class']=='dev.mixer.android.NativeAppearanceViewsV2$FieldPreservation' and frame['method']=='exact' and frame['descriptor']=='()V' and frame['bci']==40 for frame in outcome['production_frames'])
 toolmaps=[];commands=[];cleanup=[]
 for name in ('run-exact','run-recovery'):
  run=D/name;provenance=load(run/'provenance.json');toolmaps.append(provenance['tools'])
  c=load(run/'cleanup.json');assert c['all_started_children_reaped'] and c['maximum_concurrent_children']==1 and c['owned_scratch_removed'] and c['jdk_tool_lease_preserved'] and c['native_instances_started']==0 and not c['process_inventory_or_other_projects_touched']
  assert not (run/'scratch').exists();cleanup.append({'run':name,**c})
  compile_identity=load(run/'compile-identity.json');assert compile_identity['all_209_exact_matches'] and compile_identity['product_classes']==209 and compile_identity['product_sources']==16 and not compile_identity['BCI_remapping']
  for r in load(run/'commands.json'):
   assert r['exit']==0 and r['reaped'] and not r['timeout'] and r['elapsed_seconds']<60
   for stream in ('stdout','stderr'):
    ref=r[stream];assert identity(run/ref['path'])=={'bytes':ref['bytes'],'sha256':ref['sha256']}
   if r['name']=='compile':
    argv=r['argv'];assert argv[argv.index('--release')+1]=='17' and '-proc:none' in argv and '-Xlint:all' in argv and '-Werror' in argv and not any(x=='-g' or x.startswith('-g:') for x in argv)
   commands.append({'run':name,'name':r['name'],'exit':r['exit'],'elapsed_seconds':r['elapsed_seconds'],'reaped':r['reaped']})
 assert toolmaps[0]==toolmaps[1]
 jdk=ROOT/'verification/android-editor-membership-compiled-boundary-qualification/state-qualification/owned-tool-scratch/jdk-17.0.21+9/Contents/Home'
 assert all(identity(jdk/name)==value for name,value in toolmaps[0].items())
 assert identity(F/'seal.json')['sha256']=='02f4a046dd7f10266e17b804c6b86bd857f19807306bcf17214f9d5914e81250'
 summary={'schema':1,'status':'two-independent-finite-recovery-controls-passed','selected_rows_unchanged':56,'supplemental_controls':2,'supplemental_actual_exact_calls':3,'supplemental_assertions':16,'total_assertions_in_supplemental_run':747,'supplemental_actual_getter_entries_and_outcomes':2,'host_threads_supplemental_run_joined':3,'all209_exact_in_both_runs':True,'checking_false_after_original_owner_thread_exception':True,'actual_owner_thread_control_host_event_delta':0,'immediate_retry_without_scope_snapshot_checking_restore':True,'checking_false_after_identical_injected_exception_and_retry':True,'selected_original_edit_completed_final_counts':[0,0,0],'cleanup':cleanup,'commands':commands,'leased_tool_hashes_preserved':toolmaps[0],'shared_JDK_removed_or_mutated':False,'physical_cleanup_credit':False,'post_fixture_close_product_disposal_state_asserted':False,'post_fixture_close_limit':'unchanged fixture close executes in finally and catches product exceptions; no new full-disposal guarantee','pending':'all original enclosing/helper/allocation/exceptional partial-output obligations and subject Input invocation counts/BCIs remain pending; no canonical, native, release, OTA or GA acceptance'}
 (D/'recovery-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
 print('PASS two supplemental recovery controls; selected56 unchanged, all209 exact,747 assertions, owned scratch removed and shared JDK hashes unchanged')
if __name__=='__main__':main()
