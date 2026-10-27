#!/usr/bin/env python3
"""Write review disposition in this owned directory only; no execution proof."""
import hashlib, json
from pathlib import Path
D=Path(__file__).resolve().parent
R=D.parents[1]
def read(path): return json.loads(path.read_text())
def write(name, value): (D/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
results=read(D/'audit-results.json')
assert results['passed'] and results['assertions']==30395 and results['adverse_cases']==207
private=read(D/'private-interface-audit.json')
storage_path=R/'verification/swift-semantic-adapter-root-review/guarded-snapshot-host-storage-host-acceptance.json'
storage_raw=storage_path.read_bytes()
assert hashlib.sha256(storage_raw).hexdigest()=='9862bbe187dea2e1c6999218604ec43db3d3c9bc28d4fd815615d81dd98df432'
write('contract-clarification-proposal.json',{
 'schema':1,'status':'bounded-amendment-proposed-not-selected',
 'source_tree_sha256':results['source_tree_sha256'] if 'source_tree_sha256' in results else '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
 'host_tree_sha256':'027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2',
 'candidate_seal_sha256':results['candidate_seal_sha256'],
 'proposed_scope':private['direct_adapter_amendment_candidates'],
 'in_unit':'One logical direct Option/Result/Try tag or ownership-transfer event for each exact listed export, plus all actual caller scalar/native operand/result occurrences and separately imported owned payload destruction.',
 'outside_unit':['private standard implementation','panic/unwind implementation','compiler lowering/physical copies','allocator/kernel implementation and private retries','retry-driven reevaluation of a selected pure closed callback','CPU instructions/time/stack/RSS'],
 'scope_caution':'The inherited callee README charges each selected primitive and pure closed callback once and explicitly excludes retry-driven callback reevaluation. Independent review.json still describes private/retry/unwind allowances as mandatory. The selected contract must resolve this wording. This proposal covers the nine direct adapters only and cannot reinterpret another metric or actual dynamic callback execution count.',
 'proof':'Independent graph expansion finds fixed1 and zero authored callback, payload, unsized or native-request edges in each exact direct adapter. Actual caller operand/result surface and real downstream destruction remain separately charged. No additional in-unit event is identified at these nine boundaries.',
 'selection_effect':'If root selects a separately hashed source-bound amendment, a future interface may discharge only these exact mandatory private-boundary obligations as covered. This is contract clarification with no invented numeric zero/one allowance, no subtraction from fixed1, and no extension to other exports.',
 'still_required_before_any_root_grant':['All21 symbols remain in the current frozen work interface until an immutable accepted amendment supersedes the exact listed obligations.','Remaining12 per-export primitive/named-row/payload/native-request rosters need a source-backed per-interface choice.','Finite actual string provenance; exact native path/error requests; actual immutable outer-root/caller and I/U; exact executable/build/session/compiler binding; full work/storage root policy.'],
 'actual_callbacks':'Existing authored callback-edge multiplicities stay charged. This logical metric makes no physical retry or CPU bound; a metric that counts every dynamic callback reevaluation requires another bound.',
 'applied':False,'root_policy_selected':False,'operational_grant':False})
write('attempt-history.json',{
 'schema':1,'preserved_failures':[
  {'path':'recorder-bootstrap-failure.json','scope':'Recorder directory race before child launch; corrected to atomic mkdir loop.'},
  {'path':'commands/attempt-003','scope':'Reviewer treated omitted empty dynamic_resource_elements key in a nested resource leaf as required; corrected to empty-map leaf semantics.'},
  {'path':'commands/attempt-005','scope':'Reviewer matched duplicate method signature outside its frozen source interval; corrected to exact line interval plus exact function-byte digest.'}],
 'successful_replays':{'producer_tests':'commands/attempt-001','producer_derive':'commands/attempt-002','independent_current':'commands/attempt-006'},
 'producer_checks':2504,'producer_test_methods':17,'independent_assertions':30395,'independent_adverse_cases':207,
 'failures_are_not_candidate_failures':True})
write('review.json',{
 'schema':1,'status':'independent-review-passed-conditional-source146-work-composition-only',
 'candidate':{'path':'verification/swift-guarded-snapshot-whole-host-work-composition','seal_sha256':results['candidate_seal_sha256'],'members':50,'bytes':820408},
 'root_release':{'path':'verification/swift-semantic-adapter-root-review/guarded-snapshot-whole-host-work-frozen-release.json','sha256':'e7e5f687469e19ce591c2df0f8f44591863bc93b07d130e9e3d235e771b6f555'},
 'source':{'members':146,'tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185','host_members':11,'host_tree_sha256':'027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'},
 'observed':{'independent_assertions':30395,'independent_adverse_cases':207,'producer_derive_assertions':2504,'producer_test_methods':17,'reviewer_tool_failures_preserved':3,
 'known_work_constant':895084428322997895,'unresolved_symbols':35,'callee_payload_imports':19,'leaf_cuts':33,'entry_visits':53,'source_frame_bindings':8,
 'DecodedFunction':{'inline_bytes':96,'alignment':8,'logical_structural_nodes':8,'price':231526438,'nested_vectors':['Vec<Type>','Vec<DecodedInstruction>','Vec<u32>']},
 'constructor_typed_subset':134288951629,'constructor_extra_AdoptedProof':2420591528,'constructor_actual_typed_payload':136709543157,
 'prestore_source_native_callee_fixed':900979,'store_and_after_source_native_callee_fixed':874193,'loader_cap_work':895083809874789059},
 'scope_decisions':[
 'The exact conditional source arithmetic, qualified resource interfaces and conservative attribution pass. There is no selected whole-host bound.',
 'P0 exists before policy/quote/account/entry and retains the late token-return/release work. I/U are source counts to select, not defaults.',
 'All six work/storage components must commit before setup. P2 and P3 are conservative frame envelopes; they include later returns/shared exits and are not chronological meters. No later action is funded late by this attribution.',
 'The exact AccountedWasi.buffers array-to-slice frontier has4 Option<Ticket> values; Ticket3 logical leaves+Option tag and observed24 native bytes give conservative L112. The inherited2*n remains16 and applies only to that actual field frontier.',
 'L_str is unresolved until all incoming and forwarded provenance is bounded. No static-lifetime, pointer-width, maximum-literal or arbitrary-positive closure is accepted.',
 'Nine exact direct adapters warrant the separate bounded contract-clarification proposal. All21 current private export symbols remain required. Out-of-unit private implementation/retries/CPU do not require an infinite physical proof for the declared logical metric.',
 'The synthetic producer evaluator has no accepted-bound or operational-grant path. It is not a receipt validator. This independent binder rejects exact-unit/tree/schema/authority/symbol-scope mismatches against independently declared scope.',
 'Root storage interface acceptance already exists conditionally; the candidate storage condition is read as a separate composition/integration requirement, not evidence that no scoped storage review exists.'
 ],
 'current_storage_context':{'path':str(storage_path.relative_to(R)),'sha256':hashlib.sha256(storage_raw).hexdigest(),'status':json.loads(storage_raw)['status'],'whole_grant':False,'storage_replayed_by_this_review':False},
 'limitations':['Exact native requests and all21 private export/2 whole-leaf boundary choices are not selected here.','Actual root/caller/policy and immutable fixture/build/session/executable/compiler context remain unselected.','Resource source rows retain their root-accepted scope and partial compiled-correspondence limitation; active binary/native-interface packets were not read.','No product loader/writer/destructor route or healthy cleanup execution ran. Native simulator/emulator/device/UI/capture remain paused; FieldLog/OTA/GA remain separate.'],
 'accepted_whole_host_funding':False,'root_policy_selected':False,'operational_grant':False,'native_or_GA':False})
write('cleanup.json',{'schema':1,'owned_persistent_processes_started':0,'compiler_scratch_created':False,'native_or_capture_started':False,'cleanup':'No runtime or compiler scratch exists. Pure Python children were waited; all created files are retained review evidence in this owned directory.','other_projects_processes_or_data_touched':False,'Git_or_root_metadata_or_candidate_mutation':False})
print(json.dumps({'review_written':True,'whole_host_funding':False,'operational_grant':False},sort_keys=True))
