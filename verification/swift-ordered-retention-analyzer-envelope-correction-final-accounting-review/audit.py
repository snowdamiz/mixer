#!/usr/bin/env python3
"""Independent final source/ledger/archive/raw-layout accounting; no producer run."""
import ast,difflib,hashlib,json,struct,sys
from math import ceil
from pathlib import Path
from datetime import datetime,timezone
from admit import verify_final,verify_old
ROOT=Path(__file__).resolve().parents[2];OWN=Path(__file__).resolve().parent
ADMIT=OWN/'commands/admission-2';ARCH=ADMIT/'archive';META=ADMIT/'metadata';RAW=ADMIT/'raw'
PRIOR=ROOT/'verification/swift-ordered-retention-analyzer-envelope-correction-accounting-review-2/commands/admission-1/inputs'
def sha(data):return hashlib.sha256(data).hexdigest()
def load(path):return json.loads(path.read_bytes())
def write_json(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def main():
 run=OWN/'commands/audit-1';run.mkdir(parents=True,exist_ok=False)
 before=verify_final();old_before=verify_old();selection=load(META/'root-numeric-selection.json')
 assert sha((META/'root-numeric-selection.json').read_bytes())=='199dfa75b024d04eeef28f2f40165115797a0bbb3d09a2405426172d8339867c'
 selected=selection['selected'];assert selected=={'leaf':425,'W':24,'B':471,'G':112,'T':42,'finish':47,'F':42,'setup_selected':534,'setup_actual_bound':329,'F_base':29,'F_early_error':13}
 source=(ARCH/'src/envelope.rs').read_bytes();prior=(PRIOR/'source-envelope.rs').read_bytes();parent=(ARCH/'src/analyzer.rs').read_bytes()
 assert sha(source)=='7b8237abbaec492e595508eb7456dab38fbb0d92d8d3cd5a88184f7c1082b9d1' and sha(parent)=='1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b'
 expected=prior.decode()
 replacements=[('const FINISH_ENVELOPE: u64 = 8;','const FINISH_ENVELOPE: u64 = 47;'),('const RECORD_ENVELOPE: u64 = 128;','const RECORD_ENVELOPE: u64 = 425;'),('const SETUP_WRAPPER: u64 = 20;','const SETUP_WRAPPER: u64 = 42;'),('const FINAL_WRAPPER: u64 = 44;','const FINAL_WRAPPER: u64 = 42;'),('const UNDERFUNDED_GUARD: u64 = 36;','const UNDERFUNDED_GUARD: u64 = 112;'),('// HISTORICAL, UNQUALIFIED numeric constants; operation proposal does not select them.','// Selected operation-ledger partition W01..W09; outer F42 includes early-error13.'),('const WRAPPER_GROUPS: [u64; 12] = [4, 3, 3, 5, 4, 3, 3, 3, 3, 3, 3, 5];','const WRAPPER_GROUPS: [u64; 9] = [1, 3, 1, 2, 3, 2, 1, 5, 6];'),('    + WRAPPER_GROUPS[8] + WRAPPER_GROUPS[9] + WRAPPER_GROUPS[10] + WRAPPER_GROUPS[11];','    + WRAPPER_GROUPS[8];'),('    // Current historical orchestration prepays128. Its unqualified guard reserve,','    // Selected orchestration prepays425. Its separate fixed112-credit guard,')]
 for old,new in replacements:assert expected.count(old)==1;expected=expected.replace(old,new)
 assert expected.encode()==source and parent==(PRIOR/'source-analyzer.rs').read_bytes()
 independent_diff=''.join(difflib.unified_diff(prior.decode().splitlines(True),source.decode().splitlines(True),fromfile='reviewed-proposal2',tofile='selected-final'))
 (run/'independent-source-delta.diff').write_text(independent_diff)
 implementation=load(META/'implementation-delta.json');assert implementation['additional_source_control_flow_or_owners'] is False
 source_deltas=[d for d in implementation['diffs'] if d['path']=='src/envelope.rs'];assert len(source_deltas)==1 and source_deltas[0]['baseline_sha256']==sha(prior) and source_deltas[0]['selected_sha256']==sha(source)
 ledger=load(ARCH/'step-inventory.json');old_ledger=load(PRIOR/'operation-ledger.json')
 assert ledger['rows']==old_ledger['rows'] and ledger['charge_composition']==old_ledger['charge_composition']
 assert ledger['source_sha256']==sha(source) and ledger['root_numeric_selection_sha256']==sha((META/'root-numeric-selection.json').read_bytes())
 rows={r['id']:r for r in ledger['rows']};assert len(rows)==116
 for row in rows.values():
  scalar=sum(a['count'] for a in row['scalar_atoms']);copies=sum(ceil(c['bytes']/128)*c['count'] for c in row['copies'])
  assert scalar==row['scalar_operations'] and ceil(scalar/16)==row['scalar_groups'] and copies==row['copy_groups']
  assert (ceil(scalar/16)+copies)*row['repeat']+row.get('linked_groups',0)+row.get('helper_groups',0)==row['groups']
 composition=ledger['charge_composition'];totals={}
 for names,total in [('leaf_rows','leaf_total'),('guard_shared_rows','guard_total'),('wrapper_record_rows','wrapper_record_total'),('setup_rows','setup_actual_bound'),('wrapper_setup_rows','wrapper_setup_total'),('finish_rows','finish_total'),('wrapper_final_rows','wrapper_final_total'),('early_input_error_rows','early_input_error_total')]:
  totals[total]=sum(rows[n]['groups'] for n in composition[names]);assert totals[total]==composition[total]
 assert totals=={'leaf_total':425,'guard_total':112,'wrapper_record_total':24,'setup_actual_bound':329,'wrapper_setup_total':42,'finish_total':47,'wrapper_final_total':42,'early_input_error_total':13}
 assert [rows[f'W{i:02d}']['groups'] for i in range(1,10)]==[1,3,1,2,3,2,1,5,6]
 edges=load(ARCH/'complete-transfer-edge-inventory.json');assert edges['edges']==load(PRIOR/'complete-transfer-edge-inventory.json')['edges'] and edges['source_sha256']==sha(source)
 edge_map={(e['row'],e['index']):e for e in edges['edges']};assert len(edge_map)==108
 for row in rows.values():
  for i,c in enumerate(row['copies']):
   e=edge_map[(row['id'],i)];assert (e['edge'],e['transfer_chunk_bytes'],e['copy_count_per_execution'],e['bounded_repetition'])==(c['edge'],c['bytes'],c['count'],row['repeat'])
   assert e['complete_source_plus_destination_bytes']==2*e['complete_value_bytes'] and e['complete_value_bytes']>=c['bytes']
 funding=load(ARCH/'finalization-funding-table.json');assert funding['paths']==load(PRIOR/'finalization-funding-table.json')['paths'] and funding['source_sha256']==sha(source)
 for p in funding['paths']:
  if p.get('input')=='Err':assert p['outer_F_paid'] is True and p['owner'].startswith('F05 dedicated13')
  if p.get('input') in ['Ok(true)','Ok(false)']:assert p['S_paid']==p['F_paid']==1 and p['owner']=='complete finish47; F05 unused/no refund'
 lines=source.decode().splitlines();assert lines[360].strip()=='budget.setup(SETUP_WRAPPER)?; budget.report(FINAL_WRAPPER)?;'
 assert lines[374].strip()=='let envelope = finalize(&p, &s, &result, &arena);'
 assert lines[298].strip()=='budget.setup(SETUP_ENVELOPE)?; p.debit += SETUP_ENVELOPE;'
 assert lines[299].strip()=='budget.report(FINISH_ENVELOPE)?; p.debit += FINISH_ENVELOPE;'
 assert lines[300].strip()=='budget.report(UNDERFUNDED_GUARD)?;' and lines[301].strip()=='let mut candidate: Candidate2048 = [0u8; 2048];'
 assert lines[312].strip()=='budget.replay(COMBINED_RECORD)?; p.debit += RECORD_ENVELOPE;'
 assert source.decode().count('let mut candidate: Candidate2048')==1
 assert 'p.reply.words[0] == 3 || p.reply.words[1] == 15' in source.decode()
 memory=load(ARCH/'logical-inventory.json');base=load(ARCH/'inputs/accepted-inventory.json');prior_mem=load(PRIOR/'memory-and-phase-inventory.json')
 for key in ['additional_helper_leases','extra_roles','phases','named_role_upper_by_group','reservations']:assert memory[key]==prior_mem[key],key
 groups={name:sum(x['bytes'] for x in extra)+(0 if name=='candidate' else base['named_role_upper_by_group'][name]) for name,extra in memory['extra_roles'].items()}
 for phase in memory['phases'].values():assert base['phases'][phase['accepted_phase']]['control_upper']+sum(memory['additional_helper_leases'][x]['bytes'] for x in phase['additional_helpers'])==phase['control_upper']
 groups['control']=max(base['named_role_upper_by_group']['control'],*(p['control_upper'] for p in memory['phases'].values()))
 assert groups==memory['named_role_upper_by_group'] and sum(groups.values())==24656
 assert sum(memory['reservations'].values())==41984<=65536 and memory['unassigned_margin_unused']==23552
 assert all(groups[n]<=memory['reservations'][n] for n in groups)
 for lease in memory['additional_helper_leases'].values():
  if 'correction_actual_subroles' in lease:assert sum(x['bytes'] for x in lease['correction_actual_subroles'])<=lease['bytes']
  for phase in lease.get('correction_phase_upper',{}).values():assert sum(phase['roles'].values())==phase['bytes']<=lease['bytes']
 crosswalk=load(ARCH/'framing22-crosswalk.json');accepted=(PRIOR/'review-evidence/accepted-analyzer.rs').read_bytes();assert parent.startswith(accepted) and len(crosswalk['crosswalk'])==7
 for point in crosswalk['crosswalk']:assert lines[point['proposal_line']-1].strip()==point['proposal_statement']
 receipt=load(META/'commands/selected-run-1/receipt.json');compiled=ADMIT/'compiled-inputs/commands/selected-run-1'
 inputs=receipt['source_inputs'];assert len(inputs)==67
 for item in inputs:
  data=(compiled/'sources'/item['path']).read_bytes();assert len(data)==item['bytes'] and sha(data)==item['sha256']
  assert data==(ARCH/item['path']).read_bytes()
 tree=sha(json.dumps(inputs,sort_keys=True,separators=(',',':')).encode());assert tree==receipt['source_tree_sha256']=='d0db86c1432c8f8ebda38de13f89f11622cb152d73df26b0fdea04e8b07cc8d5'
 assert (compiled/'build/inputs/framing.rs').read_bytes()==parent+(ARCH/'tests/private_io_tests.rs').read_bytes()
 assert (compiled/'build/inputs/envelope.rs').read_bytes()==source
 assert (compiled/'build/independent_tests.rs').read_bytes()==(ARCH/'tests/independent_tests.rs').read_bytes()
 for name in ['envelope_tests.rs','correction_tests.rs','selected_tests.rs','fixture_tests.rs','private_io_tests.rs','independent_tests.rs']:assert (compiled/'build/tests'/name).read_bytes()==(ARCH/'tests'/name).read_bytes()
 for name in ['oracle-425.bin','oracle-budget-425.bin']:assert (compiled/'build/inputs'/name).read_bytes()==(ARCH/'inputs'/name).read_bytes()
 command_map={c['name']:c for c in receipt['commands']};assert len(command_map)==15
 for command in command_map.values():
  assert command['child_reaped'] and not command['timed_out']
  for s in ['stdout','stderr']:assert sha((RAW/command[s]).read_bytes())==command[s+'_sha256']
 assert '--crate-type=rlib' in command_map['compile-selected-library']['argv'] and '--test' in command_map['compile-selected-tests']['argv']
 assert command_map['compile-selected-library']['argv'][0].endswith('/rustc') and '-Dwarnings' in command_map['compile-selected-library']['argv']
 assert command_map['compile-selected-library']['argv'][-3].endswith('/sources/src/analyzer.rs')
 assert command_map['compile-selected-tests']['argv'][-3].endswith('/build/independent_tests.rs')
 out=(RAW/'fresh-selected-envelope26.stdout').read_text();framing=(RAW/'fresh-selected-framing44.stdout').read_text()
 assert '26 passed; 0 failed' in out and '44 passed; 0 failed' in framing
 marker='CORRECTED_ACTUAL_COMPLETE_LAYOUTS=';assert out.count(marker)==1
 observed=ast.literal_eval(out.split(marker,1)[1].splitlines()[0])
 expected_layouts=[40,40,40,40,64,80,80,232,232,128,144,128,16,16,2048,8,16,16,16,16,8,16,16,8,24,80,48,72,32,104,144,152]
 assert observed==expected_layouts==[x['bytes'] for x in load(ARCH/'actual-complete-layouts.json')['layouts']]
 actual_test=(ARCH/'tests/selected_tests.rs').read_text();assert 'size_of::<Result<(), AnalyzerError>>()' in actual_test and 'size_of::<io::Result<std::fs::Metadata>>()' in actual_test
 block=actual_test.split('    let actual = [',1)[1].split('    ];',1)[0];assert block.count('size_of::<')==32
 assert (compiled/'build/tests/selected_tests.rs').read_text()==actual_test
 assert 'ENVELOPE_ORACLE_CASES=16170' in out and 'CORRECTED_FINITE_BUDGET_CASES=5544' in out
 assert sum(line.endswith(': test') for line in (RAW/'list-selected-tests.stdout').read_text().splitlines())==70
 old_model=(ARCH/'inputs/fsm-model.py').read_bytes();new_model=(ARCH/'inputs/fsm-model-425.py').read_bytes()
 assert sha(old_model)=='15480f7b67bd3705cd485a51dd1b5c87e64cb0fa6854414d9fa2daa7595ed488'
 assert old_model.count(b'RECORD_DEBIT = 128')==1 and old_model.replace(b'RECORD_DEBIT = 128',b'RECORD_DEBIT = 425')==new_model
 old_oracle=(ARCH/'inputs/oracle.bin').read_bytes();new_oracle=(ARCH/'inputs/oracle-425.bin').read_bytes();assert len(old_oracle)==len(new_oracle)==16170*44*8
 oracle_delta_cases=0
 for old_case,new_case in zip(struct.iter_unpack('<44Q',old_oracle),struct.iter_unpack('<44Q',new_oracle)):
  expected_case=list(old_case);assert expected_case[41] in [0,128];expected_case[41]=425 if expected_case[41]==128 else 0
  assert tuple(expected_case)==new_case;oracle_delta_cases+=1
 budget=(ARCH/'inputs/oracle-budget-425.bin').read_bytes();assert len(budget)==5544*45*8;hist={0:0,424:0,425:0,426:0}
 for case in struct.iter_unpack('<45Q',budget):
  state=case[:12];credits=case[28];reply=case[29:];assert credits in hist;hist[credits]+=1
  assert reply[13]==(0 if credits<425 else 425)
  if credits<425:assert reply==(2,1,state[0],state[7],state[4],state[5],state[3],state[8],state[9],state[11],state[10],state[1],state[2],0,0,0)
 assert set(hist.values())=={1386}
 for field in ['fixture_tests.rs','independent_tests.rs','private_io_tests.rs']:assert (ARCH/'tests'/field).read_bytes()==(ARCH/'baseline/tests'/field).read_bytes()
 assert (ARCH/'baseline/tests/envelope_tests.rs').read_bytes()==(PRIOR/'source-envelope_tests.rs').read_bytes()
 assert 22+425+24==471<=8192 and 534+42==576<=65536 and 47+112+42==201
 assert 49152//8+32+32+2+35==6245 and 6245+201==6446<=3000000 and 49152+8192==57344<=65536
 assert 'CORRECTED_EARLY_ERROR mode=0 steps=1055670 envelope_debit=0 outer_final=42 early_projection=13' in out
 assert 'CORRECTED_EARLY_ERROR mode=1 steps=1056716 envelope_debit=0 outer_final=42 early_projection=13' in out
 assert 581+425*509==216906 and 534+47+425*4194304==1782579781<2**64
 after=verify_final();old_after=verify_old();assert before==after and old_before==old_after
 result={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'invocation':sys.orig_argv,
  'status':'selected-final-source-operation-type-lifetime-proof-supported-no-accounting-findings',
  'before':before,'after':after,'old_before':old_before,'old_after':old_after,'source_sha256':sha(source),'parent_sha256':sha(parent),'compiled_source_tree_sha256':tree,
  'exact_allowed_source_delta_verified':True,'runtime_body_control_flow_and_owners_unchanged':True,
  'operation_rows_checked':116,'transfer_edges_checked':108,'framing22_mappings':7,'ledger_totals':totals,
  'fresh_producer_layouts_source_raw_verified':32,'compiled_snapshot_members_verified':67,'archive_members_verified':86,'commands_raw_streams_verified':30,
  'finite_selected_oracle_numeric_delta_cases_verified':oracle_delta_cases,'budget_oracle_credit_distribution':hist,
  'producer_observed_host_methods':70,'producer_observed_comparisons':21714,'independent_behavior_controls':'separate concurrent review; not reclassified as this lane passes',
  'memory_groups':groups,'named_logical_bytes':24656,'reserved_logical_bytes':41984,'transient_ceiling':65536,'unassigned23552_margin_spent':False,
  'fixed_existing_report':6245,'new_fixed_report':201,'complete_report_upper':6446,
  'C1_prepaid_all_path_funding_confirmed':True,'C2_complete_type_sizes_confirmed':True,'public_formula':'534*S_paid+47*F_paid+425*N_B',
  'combined_final_source_operation_type_lifetime_proof_accepted':True,'findings':[],
  'root_numeric_contract_selected':True,'this_review_changes_selection':False,'full_behavior_acceptance_delegated_to_root':True,
  'physical_memory_CPU_compiler_OS_qualification':False,'implementation_release_product_GA_acceptance':False,
  'new_runtime_probe_or_Rust_compile':False,'producer_or_frozen_runner_executed':False,'native_capture_process_or_device_discovery':False,
  'cleanup':'Own admission and audit Python only; no executable, native/runtime scratch, or producer runner created. Immutable archive copies and all raw evidence retained. Initial reviewer manifest-count assumption retained separately.'}
 write_json(run/'receipt.json',result);write_json(OWN/'findings.json',{'schema':1,'status':'no-accounting-findings-final-selected-source','findings':[],'combined_final_source_operation_type_lifetime_proof_accepted':True,'release_or_product_acceptance':False})
 write_json(run/'oracle-accounting.json',{'selected_model_only_change':'RECORD_DEBIT128->425','old_oracle_cases':16170,'selected_oracle_cases_only_debit_changed':oracle_delta_cases,'budget_cases':5544,'credit_histogram':hist,'model_not_executed_by_reviewer':True})
 output=json.dumps({'status':result['status'],'operation_rows':116,'transfer_edges':108,'fresh_layouts_verified':32,'named_logical_bytes':24656,'findings':0},sort_keys=True)+'\n'
 (run/'stdout.txt').write_text(output);(run/'stderr.txt').write_text('');print(output,end='')
if __name__=='__main__':main()
