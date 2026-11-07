#!/usr/bin/env python3
"""Close the bounded review without running compiler, producer or product code."""
import hashlib,json,re,sys
from pathlib import Path
from datetime import datetime,timezone
from admit import verify_final,verify_old
ROOT=Path(__file__).resolve().parents[2];OWN=Path(__file__).resolve().parent
ARCH=OWN/'commands/admission-2/archive'
def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):return json.loads(path.read_bytes())
def write(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def main():
 run=OWN/'commands/closure-1';run.mkdir(parents=True,exist_ok=False)
 before=verify_final();old_before=verify_old();copies=[]
 for relative in [
  'verification/swift-ordered-retention-analyzer-envelope-root-review/implementation-accounting-addendum.json',
  'verification/swift-ordered-retention-analyzer-envelope-correction/commands/selected-run-1/executed-runner.py',
 ]:
  data=(ROOT/relative).read_bytes();target=run/'consulted-inputs'/relative
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
  copies.append({'path':relative,'bytes':len(data),'sha256':sha(data),'execution':False})
 assert copies[0]['sha256']=='242b19079476ab4ee8437f4e7df04d8ebb584e899f7dab7bef537c8330f526dc'
 model=read(ROOT/copies[0]['path'])['underfunded_private_leaf']['accepted_model']
 assert model=='Absent state -> InternalPoisoned/debit0; otherwise remaining<128 -> Steps/prior state/debit0 before shape or coordinate checks'
 source=(ARCH/'src/envelope.rs').read_text();assert sha(source.encode())=='7b8237abbaec492e595508eb7456dab38fbb0d92d8d3cd5a88184f7c1082b9d1'
 charge='if !underfunded { steps.remaining -= RECORD_ENVELOPE; steps.spent = RECORD_ENVELOPE; }'
 absence='if arena.len() < 7_731_056 { return poisoned(if underfunded { 0 } else { RECORD_ENVELOPE }); }'
 assert source.index(charge)<source.index(absence)
 ints=lambda parts:tuple(int(x.replace('_','')) for x in parts)
 prior_ranges=[ints(x) for x in re.findall(r'word.copy_from_slice\(&arena\[([\d_]+)\.\.([\d_]+)\]\)',source)]
 commit_edges=[ints(x) for x in re.findall(r'arena\[([\d_]+)\.\.([\d_]+)\].copy_from_slice\(&candidate\[([\d_]+)\.\.([\d_]+)\]\)',source)]
 staged=[ints(x) for x in re.findall(r'candidate\[([\d_]+)\.\.([\d_]+)\].copy_from_slice\(&next\[([\d_]+)\].to_le_bytes\(\)\)',source)]
 cells=[7,9,10,11,12,13,14,64,65,66,160,161]
 expected_arena=[(7729760+8*n,7729760+8*n+8) for n in cells]
 expected_candidate=[(888+8*i,896+8*i,i) for i in range(12)]
 assert prior_ranges==expected_arena and staged==expected_candidate
 assert commit_edges==[(a,b,888+8*i,896+8*i) for i,(a,b) in enumerate(expected_arena)]
 assert max(b for _,b in expected_arena)==7731056 and staged[-1][1]==984<=2048
 assert source.count('let mut candidate: Candidate2048')==1
 write(run/'range-and-retained-owner-proof.json',{'schema':1,'source_sha256':sha(source.encode()),'arena_ranges':expected_arena,'staged_candidate_ranges':staged,'commit_edges':commit_edges,'minimum_arena_length':7731056,'candidate_complete_bytes':2048,'payload_half_open':[888,984],'retained_candidate_declarations':1,'range_proof_scope':'Twelve unrolled read/stage/commit ranges under one exclusive slice and compile-sized candidate; actual bodies identical to reviewed proposal2. This static source check is not a new runtime canary pass.'})
 assert '(steps.remaining == 0 && steps.spent == RECORD_ENVELOPE && reply.words[13] == RECORD_ENVELOPE)' in source
 assert 'steps.spent == 0 && reply.words[0] == 2 && reply.words[1] == 1 && reply.words[13] == 0' in source
 ledger=read(ARCH/'step-inventory.json');rows={r['id']:r for r in ledger['rows']}
 guard_names=ledger['charge_composition']['guard_shared_rows']
 assert guard_names==['L01','L02','L03','L04','L14'] and sum(rows[n]['groups'] for n in guard_names)==112
 guard={'schema':1,'source_sha256':sha(source.encode()),'current_guard_rows':[rows[n] for n in guard_names],
  'current_guard_scope':'Separately prepaid underfunded-prior-state/Steps guard; not selected as a nominally funded absent-state guard.',
  'source_readability_range_preflight':{'line':137,'minimum_length':7731056,'currently_after_private_charge':True},
  'proposal_only':'L01 includes existing range preflight; L14 includes complete poison/helper maximum. A reordered absent-readability path may be a subset of these named rows, but requires its own frozen source mapping, caller validation proof and root funding selection.',
  'numeric_or_funding_amendment_selected_by_reviewer':False,'new_credit_inferred':False,
  'dependent_caller_concern':{'lines':[290,291,292,323],'source_fact':'reply_debit_valid accepts paid425 or underfunded Steps0 only; it rejects a funded poisoned0 result. The walk replaces a rejected result with poisoned425. Normal public construction supplies a full arena; private contract remains material.',
   'required_for_next_proposal':'Bind corrected private poison0/spent0 behavior, caller validation and cumulative main-paid425 independently. No refund of B471/public425.'}}
 write(run/'absence-guard-funding-boundary.json',guard)
 parent=(ARCH/'src/analyzer.rs').read_text().splitlines();final=source.splitlines()
 cross=read(ARCH/'framing22-crosswalk.json');independent=[]
 for point in cross['crosswalk']:
  assert final[point['proposal_line']-1].strip()==point['proposal_statement']
  assert parent[point['accepted_line']-1].strip()==point['accepted_statement']
  independent.append({'role':point['role'],'accepted_line':point['accepted_line'],'accepted_statement':point['accepted_statement'],'selected_line':point['proposal_line'],'selected_statement':point['proposal_statement'],'new_leaf_access_funded_by_inherited22':False})
 assert len(independent)==7
 for exact in ['pub const ARENA_BYTES: usize = 8_388_608;','pub const TRANSIENT_CAP: usize = 65_536;','pub const STEP_LIMIT: u64 = 268_435_456;','pub const REPORT_BYTES: usize = 49_152;','pub const AGGREGATE_REPORT_CAP: usize = 65_536;','const REPORT_RESERVE: u64 = 3_000_000;','const IO_RESERVE: u64 = 263_584;','const SETUP_CAP: u64 = 65_536;','const RECORD_PREFLIGHT: u64 = 8_192;','const RECORD_STEPS: u64 = 22;']:
  assert exact in parent
 assert final[311].strip()=='if budget.replay_left < RECORD_PREFLIGHT { s.limited = true; break; }'
 assert final[312].strip()=='budget.replay(COMBINED_RECORD)?; p.debit += RECORD_ENVELOPE;'
 write(run/'independent-inherited-framing22-crosswalk.json',{'schema':1,'accepted_prefix_preserved':True,'accepted_parent_sha256':'1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b','selected_source_sha256':sha(source.encode()),'rows':independent,'framing22_reproven':False,'all_new_record_operations_separately_owned':True,'mandatory_preflight':8192,'atomic_combined_debit':471})
 # Arguments are immutable external behavior finding, receipt and control paths.
 external=[]
 behavior_base=ROOT/'verification/swift-analyzer-envelope-correction-behavior-review/final-review'
 behavior_seal_raw=(behavior_base/'seal.json').read_bytes()
 assert sha(behavior_seal_raw)=='ee8b9ec9ef3b894e6bc40036aa8951528401414933097849f0c2e4a8aa879cff'
 behavior_seal=read(behavior_base/'seal.json');behavior_map={m['path']:m for m in behavior_seal['members']}
 assert len(behavior_map)==118
 for relative,m in behavior_map.items():
  path=ROOT/relative;assert path.resolve().is_relative_to(ROOT.resolve())
  data=path.read_bytes();assert len(data)==m['bytes'] and sha(data)==m['sha256']
 assert len(sys.argv)>1
 for relative in sys.argv[1:]:
  assert not Path(relative).is_absolute() and '..' not in Path(relative).parts
  data=(ROOT/relative).read_bytes();target=run/'behavior-evidence'/relative
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
  external.append({'path':relative,'bytes':len(data),'sha256':sha(data),'execution':False})
  if not relative.endswith('/seal.json'):assert external[-1]['sha256']==behavior_map[relative]['sha256']
 finding=read(behavior_base/'finding-R2.json');behavior_receipt=read(behavior_base/'final-receipt.json')
 assert sha((behavior_base/'finding-R2.json').read_bytes())=='8ccca728cc7523b2f0622db35dea665327d5e8bc7179e21dca01818f6bd56098'
 assert sha((behavior_base/'final-receipt.json').read_bytes())=='f6f9d5d5d2bbcae177e16f7086f968b781f151623e8c31730dc9002fb7796724'
 assert finding['source_sha256']==sha(source.encode()) and finding['actual_debit_vector']==[0,0,0,425,425,0,0,0,425,425]
 assert (behavior_receipt['methods_passed'],behavior_receipt['methods_failed'])==(18,1)
 behavior_out=(behavior_base/'runs/run-2/independent-tests/stdout.bin').read_text()
 observed=[tuple(map(int,x)) for x in re.findall(r'ABSENT_PRIOR length=(\d+) credits=(\d+) debit=(\d+) remaining=(\d+) spent=(\d+)',behavior_out)]
 assert len(observed)==10 and [x[2] for x in observed]==finding['actual_debit_vector']
 for length,credits,debit,remaining,spent in observed:
  assert length in [0,32] and credits in [0,1,424,425,426]
  assert (debit,remaining,spent)==((0,credits,0) if credits<425 else (425,credits-425,425))
 audit=read(OWN/'commands/audit-1/receipt.json')
 assert audit['operation_rows_checked']==116 and audit['transfer_edges_checked']==108
 findings={'schema':1,'status':'bounds-supported-selected-contract-failed-combined-acceptance-withheld',
  'source_sha256':sha(source.encode()),'new_operation_count_or_lifetime_underbound_found':False,
  'bounds_verdict':'Selected actual-source operation/type/lifetime upper bounds supported on the frozen source and reviewed ownership; no source correction is authorized by this verdict.',
  'combined_final_source_accepted':False,'findings':[{
   'id':'F1','priority':'P1','classification':'confirmed-private-contract-failure-with-dependent-funding-and-validator-correction',
   'source_lines':[132,133,134,137,290,291,292,323],
   'accepted_contract':'Absent backing state -> InternalPoisoned/debit0 before funding threshold; threshold amendment to425 does not change priority.',
   'observed_by_separate_behavior_reviewer':'Lengths0/32 with credits0/1/424 return poisoned0; credits425/426 return poisoned425 and spent425. Selected contract requires debit0 for all ten absent-state cases.',
   'accounting_implication':'Pre-charge absence work needs an explicitly selected prepaid owner independent of private425. Existing G112 row overlap does not itself authorize a new path; do not transfer inactive credits or spend23552 margin.',
   'dependent_validator':'Paid poisoned0 is currently rejected by reply_debit_valid; correction proposal must cover caller validation as well as charge order.',
   'main_debit_preserved':'Every successful main B471 retains public425, including private poison0. No refund.',
   'correction_acceptance':'Requires separately frozen source/funding proposal and exact controls; no source edit or contract reinterpretation performed here.'}],
  'external_behavior_inputs':external,'release_product_or_GA_acceptance':False}
 write(OWN/'findings.json',findings)
 after=verify_final();old_after=verify_old();assert before==after and old_before==old_after
 result={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'invocation':sys.orig_argv,
  'status':findings['status'],'source_sha256':sha(source.encode()),'root_numeric_selection_sha256':'199dfa75b024d04eeef28f2f40165115797a0bbb3d09a2405426172d8339867c',
  'operation_type_lifetime_bounds_supported':True,'combined_final_source_operation_type_lifetime_proof_accepted':False,
  'supersedes_overall_acceptance_interpretation_of':'commands/audit-1/receipt.json combined_final_source_operation_type_lifetime_proof_accepted=true was scoped to static bounds before root-confirmed missing-state control; this closure is authoritative for combined acceptance.',
  'static_audit_receipt_sha256':sha((OWN/'commands/audit-1/receipt.json').read_bytes()),
  'before':before,'after':after,'old_before':old_before,'old_after':old_after,
  'operation_rows_checked':116,'transfer_edges_checked':108,'fresh_producer_layouts_source_raw_verified':32,
  'compiled_source_tree_sha256':audit['compiled_source_tree_sha256'],'compiled_snapshot_members_verified':67,'archive_members_verified':86,'raw_producer_streams_verified':30,
  'named_logical_bytes':24656,'existing_reservation':41984,'transient_cap':65536,'unassigned23552_margin_spent':False,
  'fixed_existing_report':6245,'new_fixed_report':201,'report_upper':6446,'report_reserve':3000000,
  'public_formula':'534*S_paid+47*F_paid+425*N_B','B':471,'mandatory_preflight':8192,'setup_actual':329,'setup_selected':534,'setup_with_wrapper':576,'setup_cap':65536,
  'consulted_extra_inputs':copies,'external_behavior_inputs':external,'external_behavior_seal_verified':{'sha256':sha(behavior_seal_raw),'members':118},
  'historical_evidence':'All old seals/proposals and current producer306 freeze verified unchanged. Earlier runtime failures and seven old probes/32 prior layouts remain historical. This lane did not rerun or relabel them.',
  'own_admission_failure_preserved':'commands/admission-1 expected manifest86; actual85 plus manifest itself is86. Corrected admission-2 passed; not a producer failure.',
  'own_execution':'Python3.14.8 standard-library bookkeeping only; no Rust compile or runtime probe, producer collector, frozen runner, hosted harness, native/UI/capture, device/process discovery, source mutation or commit.',
  'cleanup':'No executable or native/runtime scratch created by this lane. All immutable copied source/model/raw streams, own failed admission and closure evidence retained. No other process touched.',
  'physical_memory_CPU_compiler_OS_qualification':False,'release_product_GA_acceptance':False}
 write(run/'receipt.json',result);write(OWN/'final-review-receipt.json',result)
 output=json.dumps({'status':result['status'],'bounds_supported':True,'combined_accepted':False,'findings':1,'producer_members':306},sort_keys=True)+'\n'
 (run/'stdout.txt').write_text(output);(run/'stderr.txt').write_text('');print(output,end='')
if __name__=='__main__':main()
