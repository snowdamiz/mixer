#!/usr/bin/env python3
"""Independent read-only packet validation; outputs stay in this review lane."""
from pathlib import Path
import collections
import copy
import hashlib
import json
import platform
import sys
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent
ROOT=D.parent.parent
F=ROOT/'verification/android-field-preservation-observation-controls'
CONTEXT='1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'
SEAL='02f4a046dd7f10266e17b804c6b86bd857f19807306bcf17214f9d5914e81250'
def identity(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def load(p):return json.loads(p.read_bytes())
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def validate_contracts(original,contracts,facets,results):
 subjects=original['subjects'];assert len(subjects)==280 and len({x['id'] for x in subjects})==280
 selected={x['id']:x for x in subjects if x['class']=='dev/mixer/android/NativeAppearanceViewsV2$FieldPreservation' and x['method'] in ('tuple','capture','exact','continuation')}
 assert len(selected)==4
 assert contracts['subjects']==list(selected.values()),'whole original record projection changed'
 joined={x['subject_id']:x for x in facets['subjects']};assert set(joined)==set(selected)
 for key,record in selected.items():
  facet=joined[key];indices=[i for i,row in enumerate(results['rows']) if row['subject_id']==key]
  assert len(record['required_semantic_cases'])==8
  assert facet['actual_row_indexes']==indices and facet['actual_finite_invocations']==len(indices),'facet row projection changed'
  assert facet['categories']==record['categories'] and facet['source_sha256']==record['source_sha256'] and facet['class_sha256']==record['class_sha256']
  assert facet['original_required_semantic_cases']==[{'case':x,'status':'pending-original-enclosing-case-not-discharged-by-these-finite-facets'} for x in record['required_semantic_cases']]
  assert facet['finite_facet_only'] and facet['allocation_exceptional_partial_output_obligations']=='pending' and facet['canonical_qualification']=='not-granted'
 return selected

def validate_rows(results):
 assert results['source_context']==CONTEXT and results['invocations']==56 and results['checks']==731
 rows=results['rows'];assert len(rows)==56 and len({x['finite_case'] for x in rows})==56
 assert collections.Counter(x['subject_id'].split('#')[1].split('(')[0] for x in rows)=={'tuple':29,'capture':4,'exact':19,'continuation':4}
 assert results['getter_entries']==results['checking_true_at_entries']==22
 assert results['host_threads_started']==results['host_threads_joined']==2
 assert results['actual_original_boundary_counts']==[2,2,3] and results['actual_final_counts']==[0,0,0] and results['original_edit_completed_after_restores']
 assert results['failure_latch_clear'] and results['no_final_field_or_exhaustion_mutations']
 assert len(results['original_boundary'])<24
 direct=[];getters=[];getters_by_wrapper=collections.Counter();exception_rows=[]
 final_names=('reference','field','record','original','selected','editable','renderer','candidate','journal','before','predecessor','disposition','loss_observation','hooks_reference')
 for row in rows:
  before,after=row['actual_before'],row['actual_after']
  assert all(before[k]==after[k] for k in final_names)
  assert row['counts_before']==row['counts_after']==[2,2,3] and row['restored_before_original_edit_resumes'] and row['no_membership_release_authority']
  assert row['actual_Input'] is None and row['exact_Input_invocation_counts_and_BCIs']=='pending: original final Input unchanged; no forwarding interceptor'
  oracle=row['independent_expected_before_invocation'];support=oracle.get('separate_support_call')
  if support:
   assert support['method']=='editorLossObservation' and support['descriptor']=='()J' and support['receiver']==row['original_final_Input_reference']
   assert support['attribution']=='direct support observation before tuple; no claim about tuple call count/BCI'
   direct.append(support['actual_return_long'])
  if 'independent_tuple_oracle' in oracle:
   o=oracle['independent_tuple_oracle'];assert before==after and row['snapshot_before']==row['snapshot_after'] and not row['actual_native_getter_outcomes']
   if o['expected_exception'] is None:assert row['actual_result']==o['expected_boolean'] and row['actual_method_completion']=='normal'
   else:assert row['exception_type']=='java.lang.IllegalStateException' and row['exception_message']==o['expected_exception']
  else:
   assert after['checking']==oracle['expected_checking_after']
   assert row['exception_message']==oracle['expected_exception_message']
   if oracle['guard'] is not None:assert not row['actual_native_getter_outcomes']
   if not row['subject_id'].endswith('#capture()V'):assert row['snapshot_before']==row['snapshot_after']
   if row['actual_result'] is not None:
    m=row['actual_result'];assert m['mode']==oracle['actual_original_mode'] and m['fence']==oracle['actual_original_fence'] and m['token']==oracle['actual_original_token']
    assert m['field_lease']==before['reference'] and m['reference']!=before['original'] and m['editor_lease']==m['replacement_lease']=='null'
  for getter in row['actual_native_getter_outcomes']:
   getters.append(getter);getters_by_wrapper[row['subject_id'].split('#')[1].split('(')[0]]+=1
   assert getter['checking_at_outcome'] and len(getter['production_frames'])<24
   exact=[f for f in getter['production_frames'] if f['class']=='dev.mixer.android.NativeAppearanceViewsV2$FieldPreservation' and f['method']=='exact']
   assert len(exact)==1 and exact[0]['descriptor']=='()V' and exact[0]['bci']==40,'actual exact getter BCI changed'
   if getter['completion']=='exception':
    assert getter['exception_reference']==row['exact_exception_reference'] and getter['returned_editable_immutable_value'] is None
    exception_rows.append(row['finite_case'])
   else:
    assert getter['completion']=='return' and getter['returned_editable_immutable_value']['reference']==getter['actual_value_reference']
    assert getter['exception_reference']=='null'
 # Literal observed returned-buffer values; comparisons do not infer unobserved Input calls.
 expected_spans={
  'actual-getter-composing-added':[[0,0,256]],
  'seeded-two-real-composing-spans-and-noncomposing-span':[[0,2,289],[0,1,273],[0,0,33]],
  'seeded-actual-getter-normal':[[0,2,289],[0,1,273],[0,0,33]],
  'seeded-actual-getter-composing-removed':[[0,1,273],[0,0,33]],
  'seeded-actual-getter-composing-start':[[0,1,273],[0,0,33],[1,2,289]],
  'seeded-actual-getter-composing-end':[[0,1,273],[0,0,33],[0,3,289]],
  'seeded-actual-getter-composing-flags':[[0,1,273],[0,0,33],[0,2,305]],
  'seeded-actual-getter-composing-order':[[0,1,273],[0,0,33],[0,2,289]],
  'seeded-actual-getter-noncomposing-added':[[0,2,289],[0,1,273],[0,0,33],[0,0,0]],
 }
 for row in rows:
  for getter in row['actual_native_getter_outcomes']:
   case=row['finite_case'];buffer=getter['actual_original_editable_and_selection_at_outcome'];value=getter['returned_editable_immutable_value']
   assert [buffer['selection_start'],buffer['selection_end']]==([0,3] if case=='actual-getter-selection-start' else [1,0] if case=='actual-getter-selection-end' else [1,3])
   if value is not None:
    assert value['text']==('hello!' if case in ('actual-getter-text','no-return-on-content-change') else 'hello')
    assert [[span['start'],span['end'],span['flags']] for span in value['span_values_in_order']]==expected_spans.get(case,[])
    assert (value['reference']!=row['actual_before']['editable'])==(case=='actual-getter-foreign-buffer')
   snapshot=row['snapshot_after'];assert snapshot['text_value']=='hello' and [snapshot['start'],snapshot['end']]==[1,3]
   assert snapshot['bounds_values_in_order']==([0,2,289,0,1,273] if case.startswith('seeded-') else [])
 assert direct==[2,2,3,4294967298,-9223372036854775808,9223372036854775806,-1]
 assert len(getters)==22 and exception_rows==['installed-snapshot-retained-on-getter-failure','actual-getter-throw','exact-getter-exception-propagates']
 return {'rows':len(rows),'checks':results['checks'],'getter_outcomes':len(getters),'getter_outcomes_by_wrapper':dict(getters_by_wrapper),'getter_exception_cases':exception_rows,'getter_frame_counts':sorted({len(x['production_frames']) for x in getters}),'boundary_frames':len(results['original_boundary']),'separate_Input_support_returns':direct,'exact_Input_subject_counts_and_BCIs':'pending, not inferred from direct supports','event_log_restoration_assertion':'not established: Shared.capture.events is literal 0'}

def main():
 assert identity(F/'seal.json')['sha256']==SEAL
 seal=load(F/'seal.json');members=seal['members'];expected={x['path']:x for x in members};actual={str(p.relative_to(F)) for p in F.rglob('*') if p.is_file() and p!=F/'seal.json'}
 assert len(members)==len(expected)==171 and set(expected)==actual and sum(x['bytes'] for x in members)==2792018
 for name,r in expected.items():
  p=F/name;assert not p.is_symlink() and not Path(name).is_absolute() and '..' not in Path(name).parts
  assert identity(p)=={'bytes':r['bytes'],'sha256':r['sha256']}
 original=load(F/'inputs/original-280-obligations.json');contracts=load(F/'inputs/exact-four-subject-contracts.json');facets=load(F/'finite-facet-joins.json');selected=load(F/'run-3/actual-results.json')
 records=validate_contracts(original,contracts,facets,selected);summary=validate_rows(selected)
 source_map=load(F/'inputs/selected-product-source-map.json');class_map=load(F/'inputs/selected-product-class-map.json');roster=load(F/'inputs/source-roster.json')
 assert len(source_map)==16 and len(class_map)==209 and hashlib.sha256(json.dumps({'source_map':source_map,'class_map':class_map},sort_keys=True,separators=(',',':')).encode()).hexdigest()==CONTEXT
 for name,expected_source in source_map.items():assert identity(F/'inputs/product'/name)==expected_source
 assert len(roster)==106 and collections.Counter(x['role'] for x in roster)=={'unchanged-exact-product16':16,'unchanged-B87':79,'accepted-v4-derivative':8,'unchanged-released-original-fixture':1,'released-descriptor':1,'all-original280-unchanged':1}
 # Compare only exact custody files; no upstream harness or broad packet execution.
 original_roster=next(x for x in roster if x['role']=='all-original280-unchanged')
 assert identity(ROOT/original_roster['origin'])==identity(F/original_roster['path'])
 history=load(F/'inputs/historical189-custody.json');assert identity(ROOT/history['path'])=={'bytes':history['bytes'],'sha256':history['sha256']}
 failures=load(F/'run-1/failure.json');assert failures['status']=='actual-failed-attempt-no-pass-credit' and load(F/'run-1/commands.json')[-1]['exit']==1
 assert not (F/'run-1/receipt.json').exists()
 assert load(F/'run-2/receipt.json')['checks']==683 and load(F/'run-3/receipt.json')['checks']==731
 for run in ('run-1','run-2','run-3'):
  cleanup=load(F/run/'cleanup.json');assert cleanup['all_started_children_reaped'] and cleanup['owned_scratch_removed'] and cleanup['jdk_tool_lease_preserved']
  for c in load(F/run/'commands.json'):
   assert c['reaped'] and not c['timeout'] and c['elapsed_seconds']<60
   for stream in ('stdout','stderr'):
    r=c[stream];assert identity(F/run/r['path'])=={'bytes':r['bytes'],'sha256':r['sha256']}
 negatives=[]
 for label in ('whole-original-record-change','facet-index-reassignment','getter-BCI-remapping'):
  a,b,c,d=map(copy.deepcopy,(original,contracts,facets,selected))
  if label=='whole-original-record-change':b['subjects'][0]['returns_and_throws'][0]['bci']+=1
  elif label=='facet-index-reassignment':c['subjects'][0]['actual_row_indexes'][0]=29
  else:next(f for r in d['rows'] for g in r['actual_native_getter_outcomes'] for f in g['production_frames'] if f['class'].endswith('$FieldPreservation') and f['method']=='exact')['bci']=41
  try:validate_contracts(a,b,c,d);validate_rows(d)
  except AssertionError:negatives.append({'control':label,'altered_in_memory_only':True,'rejected':True})
  else:raise AssertionError('negative control incorrectly accepted '+label)
 replay=load(D/'run-exact/actual-results.json');assert replay==selected,'fresh exact replay differs from frozen selected results'
 assert identity(D/'run-exact/actual-results.json')==identity(F/'run-3/actual-results.json')
 save(D/'inspection.json',{'schema':1,'status':'independently-validated-finite-host-facets-only','frozen_seal':identity(F/'seal.json'),'member_count':171,'member_bytes':2792018,'source_context':CONTEXT,'source_revision_context':seal['source_revision_context'],'product_sources':16,'product_classes':209,'original280_byte_identity':True,'whole_four_original_records_preserved':True,'required_semantic_cases_per_record':8,'finite_facet_projections_exact':True,'historical189_plus5_identity':history,'run1_failure_preserved':True,'run2_historical683_pass_preserved':True,'selected_summary':summary,'fresh_replay_byte_identical':identity(D/'run-exact/actual-results.json'),'negative_validator_controls':negatives,'python':sys.version,'platform':platform.platform(),'runner':identity(Path(__file__)),'native_UI_capture_process_inventory_or_Git_mutations':False,'all_original_case_enclosing_helper_allocation_exceptional_partial_output_obligations':'retained pending; no finite substitution'})
 print('PASS independent packet review: 171 members, exact original4 projection, exact replay56/731, three in-memory rejection controls')
if __name__=='__main__':main()
