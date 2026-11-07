#!/usr/bin/env python3
"""Freeze only this owned correction. No execution of Rust, old collectors or tests."""
from pathlib import Path
import datetime,difflib,hashlib,json,tarfile
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
RUN=P/'commands/selected-run-1';PROP=P/'commands/operation-ledger-proposal-2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def desc(p,base=P):return {'path':str(p.relative_to(base)),'bytes':p.stat().st_size,'sha256':sha(p)}
def read(p):return json.loads(p.read_text())
def write(n,v):(P/n).write_text(json.dumps(v,indent=2)+'\n')
def verify(m,base):
 for x in m['members']:
  q=base/x['path'];assert q.stat().st_size==x['bytes']and sha(q)==x['sha256'],str(q)
assert not(P/'seal.json').exists()
r=read(RUN/'receipt.json');assert r['status']=='passed'and r['methods_passed']==70 and r['fresh_finite_model_comparisons']==21714
source=sha(P/'src/envelope.rs');assert source==r['source_sha256']=='7b8237abbaec492e595508eb7456dab38fbb0d92d8d3cd5a88184f7c1082b9d1'
assert r['source_tree_sha256']=='d0db86c1432c8f8ebda38de13f89f11622cb152d73df26b0fdea04e8b07cc8d5'
# All run inputs stay exact after its70/layout/API success; no replay needed.
for x in r['source_inputs']:
 q=RUN/'sources'/x['path'];assert sha(q)==x['sha256']
 if x['path'].split('/')[0] in ('src','tests','inputs'):
  assert sha(P/x['path'])==x['sha256'],x['path']
for x in r['upstream_after']:
 path=ROOT/x['path'];assert sha(path)==x['sha256']
 verify(read(path),path.parent if path.name=='manifest.json'else ROOT)
assert not any((P/'scratch').rglob('*'))
assert all(c['child_reaped'] and not c['timed_out']for c in r['commands'])
selection=read(P/'inputs/root-correction-numeric-contract-selection.json');assert selection['numeric_contract_selected']
selectionhash=sha(P/'inputs/root-correction-numeric-contract-selection.json')
# Selected source binding; preserve every immutable reviewed row unchanged.
for src,dst in [('operation-ledger.json','step-inventory.json'),('memory-and-phase-inventory.json','logical-inventory.json'),('complete-transfer-edge-inventory.json','complete-transfer-edge-inventory.json'),('finalization-funding-table.json','finalization-funding-table.json'),('framing22-crosswalk.json','framing22-crosswalk.json')]:
 v=read(PROP/src)
 v['reviewed_proposal2_source_sha256']=v.get('source_sha256',v.get('proposal_envelope_sha256'))
 v['source_sha256']=source;v['root_numeric_selection_sha256']=selectionhash
 v['selected_source_delta']='Only selected constants/compile-time W01-W09 partition/comments; runtime code and owned values identical to reviewed proposal2.'
 v['numeric_contract_selected']=True;v['final_source_independent_acceptance']=False
 if src=='memory-and-phase-inventory.json':
  v['source_hashes']['src/envelope.rs']=source;v['source_hashes']['src/analyzer.rs']=sha(P/'src/analyzer.rs')
  v['actual_complete_types']='actual-complete-layouts.json';v['kind']='selected-correction-actual-complete-roles-awaiting-final-independent-source-review'
 if src=='operation-ledger.json':v['status']='root-selected-numeric-operation-rows-bound-to-final-source-awaiting-final-independent-review'
 write(dst,v)
# Compare production token-bearing lines outside compile-time constants, allowing
# only the already reviewed explanatory comment edit. This is a custody check,
# never semantic/release authority or a substitute for actual70 behavioral tests.
code=lambda t:'\n'.join(l for l in t.splitlines()[19:]if not l.lstrip().startswith('//'))
assert code((PROP/'source-envelope.rs').read_text())==code((P/'src/envelope.rs').read_text())
files=[('src/envelope.rs',PROP/'source-envelope.rs',P/'src/envelope.rs'),('tests/envelope_tests.rs',P/'baseline/tests/envelope_tests.rs',P/'tests/envelope_tests.rs'),('tests/correction_tests.rs',P/'baseline/tests/correction_tests.rs',P/'tests/correction_tests.rs'),('inputs/fsm-model-425.py',P/'inputs/fsm-model.py',P/'inputs/fsm-model-425.py')]
delta=[]
for name,a,b in files:delta.append({'path':name,'baseline_sha256':sha(a),'selected_sha256':sha(b),'diff':''.join(difflib.unified_diff(a.read_text().splitlines(True),b.read_text().splitlines(True),fromfile='preserved-baseline/'+name,tofile=name))})
delta.append({'path':'tests/selected_tests.rs','new':True,'methods':4,'sha256':sha(P/'tests/selected_tests.rs'),'purpose':'selected constants/32layouts, exact early-error prepaid charges, full arena/candidate private guard atomicity,5544budget oracle cases'})
for name in ('fixture_tests.rs','independent_tests.rs','private_io_tests.rs'):assert sha(P/'tests'/name)==sha(P/'baseline/tests'/name)
assert sha(P/'src/analyzer.rs')==sha(P/'baseline/src/analyzer.rs')
assert(P/'inputs/fsm-model-425.py').read_bytes()==(P/'inputs/fsm-model.py').read_bytes().replace(b'RECORD_DEBIT = 128',b'RECORD_DEBIT = 425')
write('implementation-delta.json',{'schema':1,'root_numeric_selection_sha256':selectionhash,'source_sha256':source,'parent_source_sha256':sha(P/'src/analyzer.rs'),'baseline44_files_unchanged':True,'baseline20_byte_identical_preserved':True,'source_delta_paths':['src/envelope.rs'],'test_delta_paths':['tests/envelope_tests.rs','tests/correction_tests.rs','tests/selected_tests.rs'],'model_delta_paths':['inputs/fsm-model-425.py','inputs/oracle-425.bin','inputs/oracle-budget-425.bin','inputs/oracle-425.json'],'additional_source_control_flow_or_owners':False,'diffs':delta})
stdout=(RUN/'fresh-selected-envelope26.stdout').read_text()
layouts=json.loads(next(l.split('=',1)[1]for l in stdout.splitlines()if l.startswith('CORRECTED_ACTUAL_COMPLETE_LAYOUTS=')))
prev=read(PROP/'actual-complete-types.json')['layouts'];assert layouts==[x['bytes']for x in prev]
write('actual-complete-layouts.json',{'schema':1,'source_sha256':source,'source_tree_sha256':r['source_tree_sha256'],'origin':'Fresh selected Rust70-method executable, selected_contract_and_all_thirty_two_complete_declarations_are_actual passed','raw_output':str((RUN/'fresh-selected-envelope26.stdout').relative_to(P)),'raw_output_sha256':sha(RUN/'fresh-selected-envelope26.stdout'),'layouts':prev,'complete_unit_Result':40,'complete_aggregate_Result':232,'physical_memory_or_CPU_qualification':False})
# Final archive contains exact code/test/model/proof inputs (including historical
# baseline), not executables or a second invocation of any old runner.
archive_files=[]
for name in ('src','tests','inputs','baseline'):
 archive_files += [q for q in (P/name).rglob('*')if q.is_file()]
for name in ('selected-contract-delta.json','implementation-delta.json','derive_selected_oracle.py','apply_selected_contract.py','run_selected_checks.py','step-inventory.json','logical-inventory.json','complete-transfer-edge-inventory.json','finalization-funding-table.json','framing22-crosswalk.json','actual-complete-layouts.json'):
 archive_files.append(P/name)
archive_files=sorted(set(archive_files))
assert not any(q.suffix=='.pyc'for q in archive_files)
write('source-test-model-manifest.json',{'schema':1,'source_sha256':source,'compiled_source_tree_sha256':r['source_tree_sha256'],'members':[desc(q)for q in archive_files]})
with tarfile.open(P/'selected-source-test-model.tar.gz','w:gz')as tf:
 tf.add(P/'source-test-model-manifest.json',arcname='source-test-model-manifest.json')
 for q in archive_files:tf.add(q,arcname=str(q.relative_to(P)))
# Reconcile all memberbytes in the archive itself without extraction.
with tarfile.open(P/'selected-source-test-model.tar.gz','r:gz')as tf:
 for x in read(P/'source-test-model-manifest.json')['members']:
  f=tf.extractfile(x['path']);assert f is not None
  b=f.read();assert len(b)==x['bytes']and hashlib.sha256(b).hexdigest()==x['sha256']
testfiles=[desc(q)for q in sorted((P/'tests').glob('*.rs'))]
modelfiles=[desc(P/'inputs'/name)for name in ('fsm-model.py','fsm-model-425.py','oracle.bin','oracle-425.bin','oracle-budget-425.bin','oracle-425.json')]
jsonhash=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
write('final-receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'producer-selected-correction-passed-frozen-for-independent-behavior-and-final-accounting','root_numeric_contract_selected':True,'root_selection_sha256':selectionhash,'source_sha256':source,'parent_analyzer_sha256':sha(P/'src/analyzer.rs'),'compiled_source_tree_sha256':r['source_tree_sha256'],'test_tree_sha256':jsonhash(testfiles),'test_files':testfiles,'model_tree_sha256':jsonhash(modelfiles),'model_files':modelfiles,'source_test_model_archive':desc(P/'selected-source-test-model.tar.gz'),'source_test_model_manifest_sha256':sha(P/'source-test-model-manifest.json'),'run_receipt':str((RUN/'receipt.json').relative_to(P)),'run_receipt_sha256':sha(RUN/'receipt.json'),'producer_methods':{'unchanged_framing':44,'numeric_adapted_original_envelope':20,'added_correction_contract':6,'total_passed':70,'failed':0,'ignored':0},'fresh_finite_model_comparisons':{'selected425_complete_cases':16170,'threshold_matrix':5544,'total':21714,'scope':'Fresh selected425 source vs separately derived425model; all old historical model/oracle bytes immutable; no retired count reused'},'fresh_actual_complete_layouts':32,'API':{'positive':1,'expected_negative':5},'production_delta':'root-selected constants, compile-time9 W group partition and comments only after reviewed correction; no new runtime controlflow/owner/helper','exact_delta_paths':'implementation-delta.json','source_operation_rows':116,'complete_transfer_edges':108,'named_logical_bytes':24656,'transient_reservation':41984,'transient_ceiling':65536,'public_counter':'534*S_paid+47*F_paid+425*N_B','zero_call_paid_debit':581,'main_B':471,'mandatory_preflight':8192,'new_fixed_report':201,'existing_plus_new_report_upper':6446,'frozen_upstream_members_verified':4147,'frozen_proposal_members_verified':57,'first_failure_retained':'commands/operation-ledger-proposal-2-attempt-1: proposal builder memory subtotal assertion1036->actual936, same1152lease; exact script/partial files/tool traceback retained','selected_run_failures_or_timeouts':0,'owned_scratch_archive':r['scratch_archive'],'scratch_children_cleanup':{'all_children_reaped':r['children_reaped'],'owned_scratch_removed':r['owned_scratch_removed_after_children_reaped'],'binaries_hashed_and_removed':r['binaries_removed'],'no_native_UI_capture_or_process_or_device_discovery':True},'invocations':{'numeric_delta':['/opt/homebrew/opt/python@3.14/bin/python3.14','-B',str(P/'apply_selected_contract.py')],'fresh_collector':['/opt/homebrew/opt/python@3.14/bin/python3.14','-B',str(P/'run_selected_checks.py'),'selected-run-1'],'final_freeze':['/opt/homebrew/opt/python@3.14/bin/python3.14','-B',str(Path(__file__).resolve())]},'limitations':['independent selected-source behavior and final accounting still pending','no engine/CLI/product/CI/rootmetadata integration or commit/push','no semantic replay/source applicability/metrics/realbinding/custody/release authority','native/physical/device/signing/store/FieldLog/customer/operations/GA remainunqualified','logical roles are not physical stack/RSS/compiler/OS/CPU performance','historical independent64timeout remainsunqualified']})
# Final source/test/model files still match the fresh executed snapshot.
for x in r['source_inputs']:
 if x['path'].split('/')[0]in('src','tests','inputs'):assert sha(P/x['path'])==x['sha256']
# All old seals and immutable proposal1/2 stay exact at freeze.
for x in r['upstream_after']:
 path=ROOT/x['path'];assert sha(path)==x['sha256'];verify(read(path),path.parent if path.name=='manifest.json'else ROOT)
allfiles=[ROOT/'docs/swift-ordered-retention-analyzer-envelope-correction.md']+[q for q in sorted(P.rglob('*'))if q.is_file()and q.name not in('seal.json','seal.sha256')]
# Do not exclude carried historical nested seal.json files: only top-level ours.
allfiles=[ROOT/'docs/swift-ordered-retention-analyzer-envelope-correction.md']+[q for q in sorted(P.rglob('*'))if q.is_file()and q not in(P/'seal.json',P/'seal.sha256')]
assert not any(q.suffix=='.pyc'for q in allfiles)
members=[desc(q,ROOT)for q in allfiles]
write('seal.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Separate selected fixture-envelope correction producer freeze;70hostmethods21714freshmodelcomparisons32layouts and API controls; independent final behavior/accounting pending','numeric_contract_selected':True,'implementation_accepted':False,'fullReplayAccepted':False,'storedPrefixValidated':False,'semanticMetricsValid':False,'members':members,'excluded':[str((P/'seal.json').relative_to(ROOT)),str((P/'seal.sha256').relative_to(ROOT))]})
(P/'seal.sha256').write_text(sha(P/'seal.json')+'\n')
verify(read(P/'seal.json'),ROOT)
largest=max(members,key=lambda x:x['bytes'])
print(json.dumps({'seal_sha256':sha(P/'seal.json'),'members':len(members),'bytes':sum(x['bytes']for x in members),'max_member':largest,'source_sha256':source,'test_tree_sha256':jsonhash(testfiles),'model_tree_sha256':jsonhash(modelfiles),'archive':desc(P/'selected-source-test-model.tar.gz'),'compiled_source_tree_sha256':r['source_tree_sha256'],'fresh_methods':70,'fresh_comparisons':21714,'cleanup':True},indent=2))
