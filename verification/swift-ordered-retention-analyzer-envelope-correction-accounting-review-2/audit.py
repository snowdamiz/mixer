#!/usr/bin/env python3
"""Independent proposal2 funding/type/edge/phase audit. No Rust or producer run."""
import hashlib
import json
from math import ceil
from pathlib import Path
from datetime import datetime, timezone
import sys
from admit import verify_proposal,verify_old

ROOT=Path(__file__).resolve().parents[2]
OWN=Path(__file__).resolve().parent
INPUT=OWN/'commands/admission-1/inputs'
PRIOR=ROOT/'verification/swift-ordered-retention-analyzer-envelope-correction-accounting-review'
def sha(data):return hashlib.sha256(data).hexdigest()
def load(name):return json.loads((INPUT/name).read_bytes())
def write_json(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def main():
 run=OWN/'commands/audit-1';run.mkdir(parents=True,exist_ok=False)
 before=verify_proposal();old_before=verify_old()
 ledger=load('operation-ledger.json');numeric=load('numeric-proposal.json');funding=load('finalization-funding-table.json')
 memory=load('memory-and-phase-inventory.json');base=load('accepted-framing-memory-inventory.json');edge_inventory=load('complete-transfer-edge-inventory.json')
 types=load('actual-complete-types.json');corrections=load('C2-complete-type-corrections.json')
 source=(INPUT/'source-envelope.rs').read_bytes();parent=(INPUT/'source-analyzer.rs').read_bytes()
 assert sha(source)=='e86ef43a99f99245c78308666f91f5147981859ca03fa3f97e62d46993667535'
 assert sha(parent)=='1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b'
 assert source==(PRIOR/'commands/proposal-admission-1/inputs/source-envelope.rs').read_bytes()
 assert parent==(PRIOR/'commands/proposal-admission-1/inputs/source-analyzer.rs').read_bytes()
 rows={r['id']:r for r in ledger['rows']};assert len(rows)==len(ledger['rows'])==116
 checked=[]
 for row in ledger['rows']:
  scalar=sum(a['count'] for a in row['scalar_atoms']);copies=sum(ceil(c['bytes']/128)*c['count'] for c in row['copies'])
  assert scalar==row['scalar_operations'] and ceil(scalar/16)==row['scalar_groups'] and copies==row['copy_groups']
  assert all(0<c['bytes']<=128 for c in row['copies'])
  total=(ceil(scalar/16)+copies)*row['repeat']+row.get('helper_groups',0)+row.get('linked_groups',0)
  assert total==row['groups'],row['id'];checked.append({'id':row['id'],'groups':total})
 old_ledger=json.loads((PRIOR/'commands/proposal-admission-1/inputs/operation-ledger.json').read_bytes())
 old_rows={r['id']:r for r in old_ledger['rows']}
 assert set(rows)-set(old_rows)=={'F05'} and not(set(old_rows)-set(rows))
 changed={name for name in old_rows if old_rows[name]!=rows[name]}
 assert changed=={'BR01','BS01','BP01','S01','S03','F03'}
 for name in changed:
  for field in ['scalar_atoms','scalar_operations','scalar_groups','copy_groups','repeat','groups','helper_groups','linked_groups']:
   assert old_rows[name].get(field)==rows[name].get(field),(name,field)
 c=ledger['charge_composition'];totals={}
 for names,total_name in [('leaf_rows','leaf_total'),('guard_shared_rows','guard_total'),('wrapper_record_rows','wrapper_record_total'),('setup_rows','setup_actual_bound'),('wrapper_setup_rows','wrapper_setup_total'),('finish_rows','finish_total'),('wrapper_final_rows','wrapper_final_total'),('early_input_error_rows','early_input_error_total')]:
  totals[total_name]=sum(rows[name]['groups'] for name in c[names]);assert totals[total_name]==c[total_name]
 assert totals=={'leaf_total':425,'guard_total':112,'wrapper_record_total':24,'setup_actual_bound':329,'wrapper_setup_total':42,'finish_total':47,'wrapper_final_total':42,'early_input_error_total':13}
 assert rows['F05']['linked_rows']==['E01','E09','E10'] and rows['F05']['linked_groups']==sum(rows[x]['groups'] for x in ['E01','E09','E10'])==13
 assert sum(rows[x]['groups'] for x in ['F01','F02','F03','F04'])==29 and 29+13==42
 path_checks=[]
 for path in funding['paths']:
  if path.get('input')=='Err':
   assert path['finalize'] is True and path['outer_F_paid'] is True and path['owner'].startswith('F05 dedicated13')
   if path['F_paid']==1:assert 'unused/no refund' in path['owner']
   path_checks.append({'path':path['path'],'input':'Err','owner':'F05','groups':13,'outer_F_paid':True,'finish_paid':path['F_paid']})
  elif path.get('input') in ['Ok(true)','Ok(false)']:
   assert path['finalize'] is True and path['S_paid']==path['F_paid']==1 and path['owner']=='complete finish47; F05 unused/no refund'
   path_checks.append({'path':path['path'],'input':path['input'],'owner':'finish','groups':47,'outer_F_paid':True,'finish_paid':1})
 assert len(path_checks)==8 and sum(x['input']=='Err' for x in path_checks)==6
 lines=source.decode().splitlines()
 assert lines[360].strip()=='budget.setup(SETUP_WRAPPER)?; budget.report(FINAL_WRAPPER)?;'
 assert lines[365].strip().startswith('let result = observe_inputs_fixture_envelope_v1(')
 assert lines[374].strip()=='let envelope = finalize(&p, &s, &result, &arena);'
 assert lines[299].strip()=='budget.report(FINISH_ENVELOPE)?; p.debit += FINISH_ENVELOPE;'
 assert 361<366<375 and 299<300<301<302<311
 reused=[]
 for name in ['receipt.json','layout.stdout.txt','layout.stderr.txt','proposal_layout.rs']:
  prior=PRIOR/'commands/proposal-layout-1'/('build/proposal_layout.rs' if name=='proposal_layout.rs' else name)
  if not prior.exists():prior=PRIOR/name
  assert (INPUT/'review-evidence/layout'/name).read_bytes()==prior.read_bytes(),name
  reused.append({'name':name,'sha256':sha(prior.read_bytes()),'reuse_reason':'exact envelope and parent bytes unchanged; exact independent probe evidence copied'})
 actual={entry['type']:entry['bytes'] for entry in types['layouts']};assert len(actual)==32
 assert actual['Result<(),AnalyzerError>']==40 and actual['Result<FixtureEnvelopeOutcomeV1,AnalyzerError>']==232
 assert {x['row'] for x in corrections['corrections']}==changed
 for correction in corrections['corrections']:
  corrected=correction['corrected'];assert corrected in rows[correction['row']]['copies'] and corrected['bytes']==40
  assert ceil(correction['old']['bytes']/128)==ceil(corrected['bytes']/128)==1
 edge_map={(e['row'],e['index']):e for e in edge_inventory['edges']};assert len(edge_map)==len(edge_inventory['edges'])==108
 edge_count=0
 for row in ledger['rows']:
  for i,copy in enumerate(row['copies']):
   edge=edge_map[(row['id'],i)]
   assert (edge['edge'],edge['transfer_chunk_bytes'],edge['copy_count_per_execution'],edge['bounded_repetition'])==(copy['edge'],copy['bytes'],copy['count'],row['repeat'])
   assert edge['complete_source_plus_destination_bytes']==2*edge['complete_value_bytes']
   assert edge['complete_value_bytes']>=copy['bytes']
   edge_count+=1
 assert edge_count==108
 for key,lease in memory['additional_helper_leases'].items():
  if 'correction_actual_subroles' in lease:assert sum(x['bytes'] for x in lease['correction_actual_subroles'])<=lease['bytes'],key
  if 'correction_phase_upper' in lease:
   for phase in lease['correction_phase_upper'].values():assert sum(phase['roles'].values())==phase['bytes']<=lease['bytes']
 assert sum(x['bytes'] for x in memory['additional_helper_leases']['leaf_locals']['correction_actual_subroles'])==936<=1152
 assert sum(x['bytes'] for x in memory['additional_helper_leases']['new_walk']['correction_actual_subroles'])==240<=256
 groups={}
 for name,extra in memory['extra_roles'].items():groups[name]=sum(x['bytes'] for x in extra)+(0 if name=='candidate' else base['named_role_upper_by_group'][name])
 for name,phase in memory['phases'].items():
  derived=base['phases'][phase['accepted_phase']]['control_upper']+sum(memory['additional_helper_leases'][x]['bytes'] for x in phase['additional_helpers'])
  assert derived==phase['control_upper'],name
 groups['control']=max(base['named_role_upper_by_group']['control'],*(p['control_upper'] for p in memory['phases'].values()))
 assert groups==memory['named_role_upper_by_group'] and sum(groups.values())==24656
 assert sum(memory['reservations'].values())==41984<=65536
 assert all(groups[name]<=memory['reservations'][name] for name in groups)
 crosswalk=load('framing22-crosswalk.json');accepted=(INPUT/'review-evidence/accepted-analyzer.rs').read_bytes()
 assert sha(accepted)==crosswalk['accepted_source_sha256']=='ce8f3013f7ecc9ccdb5ca88db75b7019f6af24cff995907d5d95012edb5d1757' and parent.startswith(accepted)
 assert len(crosswalk['crosswalk'])==7
 for point in crosswalk['crosswalk']:
  assert accepted.decode().splitlines()[point['accepted_line']-1].strip()==point['accepted_statement']
  assert lines[point['proposal_line']-1].strip()==point['proposal_statement']
 assert sha((INPUT/'review-evidence/accepted-framing-ledger.md').read_bytes())==crosswalk['accepted_step_declaration']['sha256']
 p=numeric['proposed'];assert p=={'leaf':425,'W':24,'B':471,'G':112,'T':42,'finish':47,'F':42,'setup_selected':534,'setup_actual_bound':329,'F_base':29,'F_early_error':13}
 assert p['B']==22+p['leaf']+p['W']==471<=8192
 assert 534+p['T']==576<=65536 and p['setup_actual_bound']==329<=534
 assert p['finish']+p['G']+p['F']==201<=3000000
 fixed_report=49152//8+32+32+2+35;assert fixed_report==6245 and fixed_report+201==6446<=3000000
 assert 49152+8192==57344<=65536
 after_reserves=268435456-263584-3000000;after_full_setup=after_reserves-1048576-640000-65536
 assert after_reserves==265171872 and after_full_setup==263417760
 assert (after_full_setup-8192)//471+1==559256
 formula_cases=[]
 for s,f,n in [(0,0,0),(1,0,0),(1,1,0),(1,1,1),(1,1,3),(1,1,4194304)]:
  assert f<=s and (n==0 or s==f==1)
  formula_cases.append({'S_paid':s,'F_paid':f,'N_B':n,'envelope_debit':534*s+47*f+425*n})
 assert [x['envelope_debit'] for x in formula_cases]==[0,534,581,1006,1856,1782579781]
 after=verify_proposal();old_after=verify_old();assert before==after and old_before==old_after
 result={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'invocation':sys.orig_argv,
  'status':'proposal2-source-accounting-supported-ready-for-root-selection-not-implementation-acceptance',
  'proposal_before':before,'proposal_after':after,'old_before':old_before,'old_after':old_after,
  'rows_checked':116,'transfer_edge_entries_checked':108,'totals':totals,'funding_paths':path_checks,
  'C1_resolved_for_proposal':True,'C2_resolved_for_proposal':True,'new_actionable_findings':[],
  'reused_layouts':reused,'reused_complete_layout_count':32,'new_Rust_or_runtime_probes':0,
  'memory_groups':groups,'memory_total':24656,'reserved_total':41984,'transient_ceiling':65536,
  'leaf_explicit_subroles':936,'walk_explicit_subroles':240,'word_at_max_phase':184,
  'framing22_operations_mapped':7,'fixed_report_upper':6245,'all_new_report_reservations':201,'combined_report_upper':6446,
  'formula_cases':formula_cases,'coarse_full_reserve_record_arithmetic_upper':559256,'capacity_is_not_guaranteed_prefix':True,
  '425_is_conservative_upper_not_minimal_lower_bound':True,'current_historical128_192_constants_qualified':False,
  'proposal_source_bounds_accepted_for_root_consideration':True,'numeric_values_selected':False,
  'implementation_accepted':False,'combined_final_source_qualified':False,'product_acceptance':False,
  'producer_tests_scripts_or_frozen_runners_executed':False,'native_capture_process_or_device_discovery':False,
  'cleanup':'Only immutable input copies and Python bookkeeping outputs. No Rust compile, runtime probe, binary, simulator/native/capture/process/device work.'}
 write_json(run/'receipt.json',result);write_json(run/'row-checks.json',{'rows':checked})
 write_json(OWN/'findings.json',{'schema':1,'status':'no-new-actionable-findings-in-proposal2','resolved':['C1','C2'],'findings':[],'numeric_values_selected':False,'implementation_accepted':False})
 out=json.dumps({'status':result['status'],'rows':116,'edges':108,'C1_resolved':True,'C2_resolved':True,'new_findings':0,'numeric_selection':False},sort_keys=True)+'\n'
 (run/'stdout.txt').write_text(out);(run/'stderr.txt').write_text('');print(out,end='')
if __name__=='__main__':main()
