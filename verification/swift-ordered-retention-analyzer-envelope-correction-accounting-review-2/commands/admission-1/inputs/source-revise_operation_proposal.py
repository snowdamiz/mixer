#!/usr/bin/env python3
"""Separately owned, non-executing proposal2 amendment.
Reads frozen JSON/source evidence. No old collector imports, Rust/test replay,
source constant edits, or mutation of proposal1/reviews/accepted sources.
"""
from pathlib import Path
import copy,datetime,hashlib,json,math,os,shutil,signal,subprocess,sys
REPO=Path(__file__).resolve().parents[2]
P=Path(__file__).resolve().parent
OLD=P/'commands/operation-ledger-proposal-1'
D=P/'commands/operation-ledger-proposal-2'
REVIEW=REPO/'verification/swift-ordered-retention-analyzer-envelope-correction-accounting-review'
assert not D.exists(), 'proposal2 must be freshly created; never rewrite a frozen proposal'
D.mkdir(parents=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(name,obj):
 q=D/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(obj,indent=2)+'\n')
def load(p):return json.loads(p.read_text())
def cpy(p,name):
 q=D/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
def bounded(argv,name):
 out=D/(name+'.stdout');err=D/(name+'.stderr')
 with out.open('wb') as fo,err.open('wb') as fe:
  child=subprocess.Popen(argv,cwd=REPO,stdout=fo,stderr=fe,start_new_session=True)
  timed=False
  try:code=child.wait(timeout=20)
  except subprocess.TimeoutExpired:
   timed=True;os.killpg(child.pid,signal.SIGTERM)
   try:code=child.wait(timeout=2)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);code=child.wait(timeout=5)
  assert child.poll() is not None
 return {'argv':argv,'exit_code':code,'timed_out':timed,'stdout':out.name,'stderr':err.name,'stdout_sha256':sha(out),'stderr_sha256':sha(err),'child_reaped':True}
def verify_manifest(path,base):
 data=load(path);total=0
 for m in data['members']:
  q=base/m['path'];assert q.stat().st_size==m['bytes'] and sha(q)==m['sha256'],str(q)
  total+=m['bytes']
 return {'path':str(path.relative_to(REPO)),'sha256':sha(path),'members':len(data['members']),'bytes':total}
seals=[('swift-ordered-retention-analyzer-envelope','ea5214e8571277e0a289bb44add5716d8c30e5d0bf3332939f18575ecf3d4eae'),('swift-ordered-retention-analyzer-envelope-accounting-review','225d35ccd2c76c6306f7be21d3931c57a47ba6263897ba1847bfe7995226bf7f'),('swift-ordered-retention-analyzer-envelope-review','03c1986c3a19ae6464ac96cabe7743f6a562118bcb4a05689026df0de2165476'),('swift-ordered-retention-analyzer-envelope-correction-accounting-review','f4b5136a8b513ca208e2f914acfea559d40edfe53a2cfb52a92129c82ec841d0')]
before=[]
for name,h in seals:
 q=REPO/'verification'/name/'seal.json';assert sha(q)==h;before.append(verify_manifest(q,REPO))
oldbefore=verify_manifest(OLD/'manifest.json',OLD)
assert sha(OLD/'manifest.json')=='f3567bdae0835d7f024fcf7e759e197c44a7b4571204b37c80fb6c596e5bc23d'
assert sha(P/'src/envelope.rs')=='e86ef43a99f99245c78308666f91f5147981859ca03fa3f97e62d46993667535'
ledger=copy.deepcopy(load(OLD/'operation-ledger.json'))
rows=ledger['rows'];byid={r['id']:r for r in rows}
corrections=[]
for id in ('BR01','BS01','BP01','S01','S03','F03'):
 r=byid[id]
 for c in r['copies']:
  if ('Result32' in c['edge'] or 'Result<(),Error>32' in c['edge']):
   assert c['bytes']==32
   old=copy.deepcopy(c)
   c['edge']=c['edge'].replace('Result32','Result40').replace('Result<(),Error>32','Result<(),Error>40')
   c['bytes']=40
   corrections.append({'row':id,'old':old,'corrected':copy.deepcopy(c),'same_one_copy_group':True})
assert len(corrections)==6
# Complete declaration/annotation40B, not merely contained AnalyzerError32B.
# No new source operation or transfer is added by this annotation repair.
early_ids=['E01','E09','E10']
early=sum(byid[i]['groups'] for i in early_ids)
assert early==13
newrow={'id':'F05','phase':'wrapper-final-early-input-error','source':'envelope.rs:256-258,375 and241-251 projection,253 finalizer return','scalar_atoms':[],'scalar_operations':0,'scalar_groups':0,'copies':[],'copy_groups':0,'repeat':1,'groups':early,'linked_groups':early,'linked_rows':early_ids,'note':'Dedicated outer-prepaid early-input-error finalization subdivision. Owns E01+E09/EH03+E10 for EVERY input Err (including when finish reservation happened). No new operation is implied: a distinct paid branch-specific reserve owns the identical actual source. In this Err case the separate complete finish47 remains unused, with no refund. On input Ok this entire F05 reserve remains unused and finish47 owns E01-E10. No credits transfer between these branches.'}
rows.append(newrow);byid['F05']=newrow
composition=ledger['charge_composition']
composition['wrapper_final_rows'].append('F05');composition['wrapper_final_total']+=early
assert composition['wrapper_final_total']==42
composition['early_input_error_rows']=early_ids
composition['early_input_error_total']=early
ledger['status']='proposal2-corrected-funding-and-complete-types-requires-independent-source-audit'
ledger['funding_dispatch']={'outer_charge':'F_wrapper=42 paid by budget.report before output_safety/Arena/progress/input observation','input_Err':'F05=13 owns E01+E09/EH03+E10; finish47, if paid, stays unused','input_Ok':'complete finish47 owns E01-E10; observe_inputs Ok entails walk setup/finish reservations succeeded; F05 stays unused','no_extra_runtime_discriminator':'Existing finalize input match determines the source path. S_paid/F_paid are proof variables over successful charge events, never extra Rust owners/arguments or stored booleans.','complete_finalizer_source_executions':1,'no_double_charge_of_executed_work':'One funding owner per actual dynamic finalize execution. All unused prepaid amounts remain truthful reserved credits, never reused/refunded.'}
ledger['no_nested_doublecharge']+=' Proposal2 F05 links the same finalizer rows only on input Err; finish47 links them only on input Ok. Both reserves may succeed but at most one owns the executed path.'
# All copy rows still obey their group arithmetic and repetition.
for r in rows:
 assert r['scalar_operations']==sum(a['count'] for a in r['scalar_atoms'])
 assert r['scalar_groups']==math.ceil(r['scalar_operations']/16)
 assert r['copy_groups']==sum(c['count'] for c in r['copies'])
 if 'linked_groups' not in r:
  assert r['groups']==r['repeat']*(r['scalar_groups']+r['copy_groups'])+r.get('helper_groups',0),r['id']
for key,totalkey in [('leaf_rows','leaf_total'),('wrapper_record_rows','wrapper_record_total'),('setup_rows','setup_actual_bound'),('wrapper_setup_rows','wrapper_setup_total'),('finish_rows','finish_total'),('wrapper_final_rows','wrapper_final_total')]:assert sum(byid[i]['groups']for i in composition[key])==composition[totalkey]
dump('operation-ledger.json',ledger)
num=copy.deepcopy(load(OLD/'numeric-proposal.json'))
num['status']='unselected-proposal2-funding-complete-type-amendment-no-source-execution'
num['proposed']['F']=42
num['proposed']['F_base']=29;num['proposed']['F_early_error']=13
num['public_formula']='534*S_paid+47*F_paid+425*N_B'
num.pop('public_formula_S');num.pop('public_formula_F');num.pop('public_formula_N')
num['symbol_definitions']={'S_paid':'1 iff main budget.setup(534) succeeded, else0','F_paid':'1 iff main budget.report(proposed finish47) succeeded, else0; distinct from F_wrapper42','N_B':'number of successful atomic main budget.replay(B471) reservations, including later read/framing failure and skipped latched leaf','F_wrapper':'fixed outer wrapper-final reservation42=base29+dedicated input-error finalization13; never part of envelope_debit','T_wrapper':'fixed outer wrapper-setup reservation42; distinct from main setup534','no_runtime_new_owner':'S_paid/F_paid are mathematical event indicators, not hidden Rust flags. Progress still stores only reply_valid/debit/reply.'}
num['feasibility']['fixed_new_report_reservation']=47+112+42
num['feasibility']['remaining_reportreserve_after_new_fixed']=3000000-47-112-42
num['feasibility']['steps_before_records_lower_bound']=1048576+640000+42+534+47+112+42
num['feasibility']['arithmetic_record_upper_ignoring_other_existing_costs']=(268435456-num['feasibility']['steps_before_records_lower_bound'])//471
num['feasibility']['finish_plus_G_plus_F_le_reportreserve']=47+112+42<=3000000
num['feasibility']['outer_F_wrapper_dominates_every_finalize']=True
num['feasibility']['unchanged_report_max6245_plus_new201']=6245+47+112+42
num['feasibility']['Budget_new_replay_after_full_IO_report_reserves']=268435456-3000000-263584
num['feasibility']['replay_after_arena_profile_and_full_setupcap']=268435456-3000000-263584-1048576-640000-65536
num['feasibility']['complete_reserve_arithmetic_record_capacity_with8192preflight']=(num['feasibility']['replay_after_arena_profile_and_full_setupcap']-8192)//471+1
num['feasibility']['complete_reserve_capacity_scope']='Arithmetic illustration only: full IO/report and setup caps withheld, accepted arena/profile counts included. Valid input/error/IO/drain behavior still governs actual extent; no guaranteed prefix, full cap or native performance acceptance.'
num['feasibility']['input_Ok_implies_S_paid_and_F_paid']=True
num['zero_leaf_complete_or_limited']['debit_if_setup_and_finish_paid']=581
num['all_path_funding']='finalization-funding-table.json'
num['complete_type_annotation_correction']='unit/walk Result40 replaces erroneous32 labels; AnalyzerError remains32; each transfer still fits one group'
num['source_constants_still_historical_unselected']=True
num['upstream_proposal1_manifest_sha256']=sha(OLD/'manifest.json')
num['review_seal_sha256']=sha(REVIEW/'seal.json')
dump('numeric-proposal.json',num)
# These are all possible phase boundaries; some injected failures are normally
# unreachable under reserves, but their fixed public/error handling still closes.
paths=[
 {'path':'Budget.new fails','outer_F_paid':False,'S_paid':None,'F_paid':None,'N_B':0,'finalize':False,'owner':'outer Err only','public_aggregate':False,'debit':None},
 {'path':'outer T reservation fails','outer_F_paid':False,'S_paid':None,'F_paid':None,'N_B':0,'finalize':False,'owner':'outer Err only','public_aggregate':False,'debit':None},
 {'path':'outer F_wrapper reservation fails','outer_F_paid':False,'S_paid':None,'F_paid':None,'N_B':0,'finalize':False,'owner':'outer Err only','public_aggregate':False,'debit':None},
 {'path':'output safety or Arena construction fails','outer_F_paid':True,'S_paid':None,'F_paid':None,'N_B':0,'finalize':False,'owner':'outer Err only','public_aggregate':False,'debit':None},
 {'path':'initial metadata / fixture context / profile / header returns Err','outer_F_paid':True,'S_paid':0,'F_paid':0,'N_B':0,'finalize':True,'owner':'F05 dedicated13','input':'Err','candidate_initialized':False,'debit':0},
 {'path':'main setup534 reservation fails','outer_F_paid':True,'S_paid':0,'F_paid':0,'N_B':0,'finalize':True,'owner':'F05 dedicated13','input':'Err','candidate_initialized':False,'debit':0},
 {'path':'finish47 reservation fails after main setup succeeds','outer_F_paid':True,'S_paid':1,'F_paid':0,'N_B':0,'finalize':True,'owner':'F05 dedicated13','input':'Err','candidate_initialized':False,'debit':534},
 {'path':'guard112 reservation fails after finish succeeds','outer_F_paid':True,'S_paid':1,'F_paid':1,'N_B':0,'finalize':True,'owner':'F05 dedicated13; finish47 unused/no refund','input':'Err','candidate_initialized':False,'debit':581},
 {'path':'candidate/cell length check or later ordinary read/framing/EOF/final metadata returns Err','outer_F_paid':True,'S_paid':1,'F_paid':1,'N_B':'n>=0','finalize':True,'owner':'F05 dedicated13; finish47 unused/no refund','input':'Err','candidate_initialized':'depends on failure point','debit':'581+425*n'},
 {'path':'limited structural drain fails or footer/EOF/final metadata fails','outer_F_paid':True,'S_paid':1,'F_paid':1,'N_B':'n>=0','finalize':True,'owner':'F05 dedicated13; finish47 unused/no refund','input':'Err','candidate_initialized':True,'debit':'581+425*n'},
 {'path':'complete framing+all final metadata succeeds','outer_F_paid':True,'S_paid':1,'F_paid':1,'N_B':'n>=0','finalize':True,'owner':'complete finish47; F05 unused/no refund','input':'Ok(true)','candidate_initialized':True,'debit':'581+425*n'},
 {'path':'limited bounded structural drain+all final metadata succeeds','outer_F_paid':True,'S_paid':1,'F_paid':1,'N_B':'n>=0','finalize':True,'owner':'complete finish47; F05 unused/no refund','input':'Ok(false)','candidate_initialized':True,'debit':'581+425*n'},
 {'path':'report construction/output write/postwrite check fails after finalization','outer_F_paid':True,'S_paid':'0or1','F_paid':'0or1','N_B':'n>=0','finalize':'already executed once','owner':'F01-F04 outer Err transfer rows; prior finalizer retains own owner','public_aggregate':False,'debit':None},
]
dump('finalization-funding-table.json',{'schema':1,'source_sha256':sha(P/'src/envelope.rs'),'source_call_order':['Budget.new','outer budget.setup(T_wrapper42)','outer budget.report(F_wrapper42)','output_safety','Arena.new','Framing/Progress absent initialization','observe_inputs initial/context/profile/header','main setup534 then debit+=534','main finish47 then debit+=47','guard112 reservation','candidate2048/cells initialize','per record8192preflight then atomic B471 then debit+=425 then decode/framing/optional leaf','bounded limited structural drain/footer/EOF/all final metadata','core finalize unconditionally for returned input result','existing binary report/write/postwrite','aggregate Result232 return'],'paths':paths,'impossible_indicator_combinations':['F_paid=1 while S_paid=0','N_B>0 while either S_paid=0 or F_paid=0','returned input Ok while F_paid=0','any finalize execution before successful F_wrapper admission'],'priority_and_typed_meaning':{'input_Err':'Unavailable; BINDING->FramingUnavailable,BUDGET->FramingLimited,otherwiseFramingInvalid; all state/coordinate/extent/latch/work/instruction fields0; truthful cumulative debit retained','input_Ok_absent':'Unavailable/EnvelopeUnavailable,all extent fields0; debit581 at zero charged records','input_Ok_complete':'private poison first; otherwise last-safe Refused/Closed/CAP/incomplete boundary','input_Ok_limited':'AnalysisLimited for observed/refused/poison; partial last-safe fixture extent only, poison all extent0; absent remainsUnavailable; never normal nonCAPfinish','outer_Err':'no aggregate, therefore no public observation/debit claim'},'mechanical_path_assertions':'F05 covers only Err finalizer path13; finish47 covers only Ok finalizer path; source finalizer called once; unused prepaid reserves never exchanged/refunded','changed_source_required_for_this_proposal':False,'constant_update_still_awaits_root_selection':True})
dump('C2-complete-type-corrections.json',{'schema':1,'findings':'C2','actual_type':'Result<(),AnalyzerError>','actual_bytes':40,'payload_AnalyzerError_bytes':32,'corrections':corrections,'group_count_delta':0,'fresh_independent_probe':'review-evidence/layout/receipt.json','no_type_layout_inferred_from_payload_size':True})
# Complete transfer-edge trace: source and destination both have storage roles,
# while each single directed transfer remains one copy (or explicit chunks).
edges=[]
for r in rows:
 for i,c in enumerate(r['copies']):
  complete=c['bytes'];kind='fixed value/handle; complete width is transfer width'
  if c['edge'].startswith(('Progress144','Progress')) and c['bytes'] in (128,16):complete=144;kind='complete Progress144 split into128+16'
  if 'Result232' in c['edge'] or 'Outcome232' in c['edge']:complete=232;kind='complete aggregate/Result232 split into128+104'
  if 'literal source2048' in c['edge']:complete=2048;kind='complete candidate initializer2048 split16x128'
  edges.append({'row':r['id'],'index':i,'edge':c['edge'],'transfer_chunk_bytes':c['bytes'],'copy_count_per_execution':c['count'],'bounded_repetition':r['repeat'],'complete_value_bytes':complete,'complete_source_plus_destination_bytes':2*complete,'storage_rule':kind,'not_summed_as_simultaneous_peak':'Use explicit role/phase lifetime inventory; repeated copy edges can use the same bounded storage. One transfer source+destination counts two storage places, one work copy.'})
dump('complete-transfer-edge-inventory.json',{'schema':1,'source_sha256':sha(P/'src/envelope.rs'),'C2_complete_unit_walk_Result_bytes':40,'AnalyzerError_bytes':32,'aggregate_Result_bytes':232,'edges':edges,'copy_groups_still_unchanged_except_new_funding_link_not_new_execution':True})
# Carry exact independent source/call/ledger crosswalk and32 actual declarations.
carry=[('findings.json','review-evidence/findings.json'),('seal.json','review-evidence/seal.json'),('framing22-crosswalk.json','framing22-crosswalk.json'),('commands/framing-baseline-admission-1/analyzer.rs','review-evidence/accepted-analyzer.rs'),('commands/framing-baseline-admission-1/swift-ordered-retention-analyzer-library.md','review-evidence/accepted-framing-ledger.md'),('commands/framing-baseline-admission-1/accepted-seal.json','review-evidence/accepted-framing-seal.json'),('proposal_layout.rs','review-evidence/layout/proposal_layout.rs'),('commands/proposal-layout-1/layout.stdout.txt','review-evidence/layout/layout.stdout.txt'),('commands/proposal-layout-1/layout.stderr.txt','review-evidence/layout/layout.stderr.txt'),('commands/proposal-layout-1/receipt.json','review-evidence/layout/receipt.json'),('commands/source-audit-2/early-finalization-path.json','review-evidence/early-finalization-path.json')]
for a,b in carry:cpy(REVIEW/a,b)
layouttypes=['Result<(),AnalyzerError>','Result<bool,AnalyzerError>','Result<u64,AnalyzerError>','Result<Arena,AnalyzerError>','Result<Budget,AnalyzerError>','Result<Stamp,AnalyzerError>','Result<Fixture,AnalyzerError>','FixtureEnvelopeOutcomeV1','Result<FixtureEnvelopeOutcomeV1,AnalyzerError>','FixtureEnvelopeObservationV1','FixtureEnvelopeProgressV1','FixtureEnvelopeReplyV1','StepBudget','CheckedPair','Candidate2048','&mut Candidate2048','&[u8]','&mut [u8]','Option<&[u8]>','Option<&mut [u8]>','Option<&[u8;8]>','Option<u64>','Range<usize>','RangeFrom<usize>','RangeInclusive<u64>','Framing','Reader','Stamp','AnalyzerError','ReplayOutcome','std::fs::Metadata','io::Result<std::fs::Metadata>']
sizes=[40,40,40,40,64,80,80,232,232,128,144,128,16,16,2048,8,16,16,16,16,8,16,16,8,24,80,48,72,32,104,144,152]
dump('actual-complete-types.json',{'schema':1,'origin':'Fresh independent32-layout probe carried byte-for-byte; no new producer layout execution','selected_source_sha256':sha(P/'src/envelope.rs'),'probe_prefix_matches_source':sha(P/'src/envelope.rs')=='e86ef43a99f99245c78308666f91f5147981859ca03fa3f97e62d46993667535','layouts':[{'type':t,'bytes':n}for t,n in zip(layouttypes,sizes)],'producer_cost_dependent_behavior_executed':False,'independent_probe_raw':'review-evidence/layout/layout.stdout.txt'})
# Preserve the accepted framing and original complete composed storage inventory,
# adding explicit correction scope/phase interpretations. No old script executed.
mem=copy.deepcopy(load(REPO/'verification/swift-ordered-retention-analyzer-envelope/logical-inventory.json'))
mem['kind']='correction-proposal2-complete-role-superset-awaiting-independent-final-source-qualification'
mem['source_hashes']['src/envelope.rs']=sha(P/'src/envelope.rs')
mem['source_hashes']['src/analyzer.rs']=sha(P/'src/analyzer.rs')
mem['provenance']={'original_complete_inventory_sha256':sha(REPO/'verification/swift-ordered-retention-analyzer-envelope/logical-inventory.json'),'accepted_inventory_sha256':sha(P/'inputs/accepted-inventory.json'),'reuse':'Same named conservative storage-role/phase superset; original memory arithmetic was independently reconciled, complete amended final-source lifetime qualification remains pending. No old collector imported/executed.'}
mem['complete_types']='actual-complete-types.json'
mem['transfer_edges']='complete-transfer-edge-inventory.json'
mem['unit_walk_result_bytes']=40
mem['core_bool_result_bytes']=40
mem['aggregate_result_bytes']=232
mem['additional_helper_leases']['leaf_locals']['correction_actual_subroles']=[{'role':'prior96 and next96','bytes':192},{'role':'reused word8 plus one LE array temporary8','bytes':16},{'role':'complete native arena slice16/candidate8/record8/steps8 parameters','bytes':40},{'role':'two complete Range16 sources plus two argument destinations','bytes':64},{'role':'twelve complete slice16 caller/callee/return/source/destination view places as a conservative phase union','bytes':192},{'role':'thirty-two native scalar value/control source/caller slots','bytes':256},{'role':'LE scalar source/argument/return handling two native8 values','bytes':16},{'role':'complete stage tuple16 source+binding16','bytes':32},{'role':'sixteen native index/constant/bounds temporary slots','bytes':128}]
assert sum(v['bytes']for v in mem['additional_helper_leases']['leaf_locals']['correction_actual_subroles'])==936
mem['additional_helper_leases']['leaf_locals']['bytes']=1152
mem['additional_helper_leases']['leaf_locals']['roles']='Correction actual named subroles936 fit existing1152 lease; no dynamic prior loop/Pair-return/checkedOption owner remains. word8 is explicitly charged, not hidden. Remaining216 lease bytes unused; no global unassigned margin consumed.'
mem['additional_helper_leases']['new_walk']['correction_actual_subroles']=[{'role':'progress source/argument native borrows','bytes':16},{'role':'decoded record8 source/local and two native borrow places','bytes':32},{'role':'StepBudget16 source+local plus two native borrow places','bytes':48},{'role':'maximum one complete new setup/report Result40 source+caller at a statement boundary','bytes':80},{'role':'native index/branch/control temporaries','bytes':64}]
mem['additional_helper_leases']['new_walk']['roles']='Correction explicit subroles240 within existing256 lease; complete new unit Results are40. Setup/report Results do not retain borrows or survive their statement;3x40 conservative original receiving budget retained by phase union.'
mem['additional_helper_leases']['word_at']['correction_phase_upper']={
 'checked_get':{'roles':{'bytes_parameter':16,'offset_parameter':8,'RangeFrom_source_and_argument':16,'slice_receiver_source_and_argument':32,'OptionSlice_source_and_return':32,'tail_binding':16,'native_index_bounds_error_temporaries':64},'bytes':184},
 'first_chunk':{'roles':{'bytes_parameter':16,'offset_parameter':8,'tail_binding':16,'slice_receiver_source_and_argument':32,'OptionArrayBorrow_source_and_return':16,'array_borrow':8,'native_index_bounds_error_temporaries':64},'bytes':160},
 'decode_and_return':{'roles':{'bytes_parameter':16,'offset_parameter':8,'tail_binding':16,'array_borrow':8,'native8_array_source_argument_return':24,'Pair16_source_return_caller':48,'native_index_bounds_error_temporaries':64},'bytes':184}}
mem['additional_helper_leases']['word_at']['roles']='Explicit complete-type statement-phase upper184 fits existing256 lease. Pair16/OptionSlice16/slice16 and OptionArrayBorrow8/RangeFrom8 remain complete. Temporary get/first_chunk call values end at their statement; retained bytes/offset/tail/array are named in later phases.'
mem['C2_no_inventory_capacity_change']='Original accepted/composed helper leases already used complete40-byte unit Results; corrected six work-edge labels now agree. No32-byte unitResult assumption is retained in active proposal2.'
mem['funding_proof_not_storage_owner']='F05 adds a separately named work reservation, no Rust variable/value/source/caller or retained owner. S_paid/F_paid/N_B are proof event variables only.'
mem['correction_phase_aliases']={'early_input_error_projection':'new_final_projection includes new_core/finalize/project plus unnecessary reason/word_at conservatively; input metadata/Stamp owners remain separately named by accepted metadata2400 bound','after_finish_input_error_projection':'same new_final_projection; no new owner and paid finish47 remains reserved','late_metadata_error_projection':'same new_final_projection plus accepted metadata source/return/Stamp places already globally charged','source_word_range_rewrite':'new_record_leaf_or_guard retained conservative baseline helper chain, with explicit936leaf subroles within1152 and word_at phase184within256; old obsolete slots not used as work credits'}
assert mem['named_role_upper_total']==24656 and mem['reserved_total']==41984
assert all(mem['named_role_upper_by_group'][g]<=n for g,n in mem['reservations'].items())
dump('memory-and-phase-inventory.json',mem)
# Carry the complete unchanged accepted/framing memory role evidence too.
cpy(P/'inputs/accepted-inventory.json','accepted-framing-memory-inventory.json')
life=copy.deepcopy(load(OLD/'ranges-and-lifetimes.json'))
life.pop('actual_known_layouts_historical_probe_not_new_measurement');life.pop('fresh_layout_execution_pending')
life['actual_complete_types']='actual-complete-types.json'
life['complete_type_edge_inventory']='complete-transfer-edge-inventory.json'
life['memory_phase_inventory']='memory-and-phase-inventory.json'
life['actual_complete_unit_walk_result_bytes']=40
life['fresh_independent32_layout_probe_carried']=True
life['new_producer_layout_run_pending']=True
life['no_new_correction_owner']='F05 is work funding only; no new Rust source variable/argument/flag/heap allocation.'
dump('ranges-and-lifetimes.json',life)
# Exact source snapshots remain byte-identical; historical constants not selected.
for name in ['analyzer.rs','envelope.rs']:cpy(P/'src'/name,'source-'+name)
for name in ['correction_tests.rs','envelope_tests.rs','fixture_tests.rs','independent_tests.rs','private_io_tests.rs']:cpy(P/'tests'/name,'source-'+name)
cpy(Path(__file__).resolve(),'source-revise_operation_proposal.py')
for q in sorted((P/'inputs').glob('root-*.json')):cpy(q,q.name)
for n in ['correction-proposal1-review-admission.json','correction-operation-proposal-1-preflight.json']:
 q=REPO/'verification/swift-ordered-retention-analyzer-envelope-root-review'/n
 if q.exists():cpy(q,'root-'+n)
# Human-readable binding proposal explanation is snapshotted, not inferred approval.
doc=REPO/'docs/swift-ordered-retention-analyzer-envelope-correction.md'
if doc.exists():cpy(doc,'proposal.md')
cmds=[bounded(['git','rev-parse','HEAD'],'context-revision'),bounded([sys.executable,'--version'],'python-version')]
assert all(c['exit_code']==0 and not c['timed_out']for c in cmds)
after=[verify_manifest(REPO/'verification'/n/'seal.json',REPO)for n,h in seals]
assert before==after
assert oldbefore==verify_manifest(OLD/'manifest.json',OLD)
dump('scope-and-preservation.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Separate proposal2 only; C1 explicit funding/C2 complete-type labels/crosswalk+memory edges; no source constant change or behavior replay','frozen_input_manifests_before':before,'frozen_input_manifests_after':after,'proposal1_before_after':oldbefore,'source_unchanged':sha(P/'src/envelope.rs')==sha(OLD/'source-envelope.rs'),'selected_source_sha256':sha(P/'src/envelope.rs'),'analyzer_sha256':sha(P/'src/analyzer.rs'),'old_envelope20_test_bytes_unchanged':sha(P/'tests/envelope_tests.rs')==sha(REPO/'verification/swift-ordered-retention-analyzer-envelope/tests/envelope_tests.rs'),'commands':cmds,'python':{'version':sys.version,'executable':sys.executable,'resolved_tool_sha256':sha(Path(sys.executable).resolve())},'collector_policy':'Only git/version children; dedicated start_new_session process groups, timeout20s,SIGTERM then SIGKILL if necessary, wait/reap, stdout/stderr files opened before spawn retained on every path. No child exists at receipt emission. No scratch Rust binary created.','producer_tests_executed':0,'Rust_executions':0,'cost_dependent_behavior_executed':False,'constant_selection':False,'native_capture_UI_or_process_or_device_discovery':False,'files_outside_owned_correction_paths_mutated':False,'pending':['independent proposal2 source/funding/layout/lifetime audit','explicit root numeric selection','fresh producer layout probe and behavioral/cost-boundary replay after selection','66 proposed producer methods accurately separated from independent/public evidence','final upstream inventory/cleanup/freeze']})
manifest={'schema':1,'members':[{'path':str(q.relative_to(D)),'bytes':q.stat().st_size,'sha256':sha(q)}for q in sorted(D.rglob('*'))if q.is_file()and q.name not in ('manifest.json','receipt.json')]}
# Nested copied receipt.json files must be included (only our root receipt excluded).
manifest['members']=[{'path':str(q.relative_to(D)),'bytes':q.stat().st_size,'sha256':sha(q)}for q in sorted(D.rglob('*'))if q.is_file()and q not in (D/'manifest.json',D/'receipt.json')]
dump('manifest.json',manifest)
dump('receipt.json',{'schema':1,'status':'immutable-operation-ledger-proposal2-awaiting-independent-audit-and-root-selection','manifest_sha256':sha(D/'manifest.json'),'members':len(manifest['members']),'bytes':sum(m['bytes']for m in manifest['members']),'source_sha256':sha(P/'src/envelope.rs'),'ledger_sha256':sha(D/'operation-ledger.json'),'numeric_proposal_sha256':sha(D/'numeric-proposal.json'),'memory_inventory_sha256':sha(D/'memory-and-phase-inventory.json'),'funding_table_sha256':sha(D/'finalization-funding-table.json'),'proposed':num['proposed'],'public_formula':num['public_formula'],'constant_selection':False,'cost_dependent_replay':False,'predecessor_manifest_sha256':sha(OLD/'manifest.json'),'independent_review_seal_sha256':sha(REVIEW/'seal.json')})
print(json.dumps(load(D/'receipt.json'),indent=2))
