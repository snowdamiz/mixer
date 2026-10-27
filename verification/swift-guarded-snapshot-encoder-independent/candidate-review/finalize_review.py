from pathlib import Path
import datetime,hashlib,json,re,shutil,sys
import run_review as r
def normalized(value):return re.sub(r'\s+','',value)
profiles=('host-debug','host-optimized','unit-debug','unit-optimized')
core=[json.loads((r.HERE/'layouts'/f'{profile}.json').read_text())for profile in profiles]
helper=[json.loads((r.HERE/'helper-layouts'/f'{profile}-additive.json').read_text())for profile in profiles]
assert all(x==core[0]for x in core)and len(core[0])==52
assert all(x['rows']==helper[0]['rows']for x in helper)and len(helper[0]['rows'])==58
for x in helper:assert x['closure_shape_assertions']==4
assert json.loads((r.HERE/'capture-layouts.json').read_text())['profiles']==list(profiles)
producer=json.loads((r.CANDIDATE/'layout-supplement.json').read_text())
existing={normalized(x['name'])for x in core[0]}|{normalized(x[0])for x in producer['assertions']}
additive=[row for row in helper[0]['rows']if normalized(row['name'])not in existing]
def anchor(path,start,end,role):
 p=r.CANDIDATE/'source/vm'/path;lines=p.read_text().splitlines()
 end=min(end,len(lines))
 return {'path':str(p.relative_to(r.REPO)),'file':r.desc(p),'line_start':start,'line_end':end,'role':role,'text':'\n'.join(lines[start-1:end])}
anchors=[
 anchor('src/experimental/swift.rs',986,988,'memory/table Option<(u32,u32)> copies, no-capture refusal closure, Result<(u32,u32),Error> and success patterns'),
 anchor('src/experimental/swift.rs',1163,1188,'metadata Option<&record>/Result<&record,Error>, sid/index shared captures, parameter checked Option<usize> and predicate reference capture'),
 anchor('src/experimental/swift.rs',1253,1257,'array get Option<&u64>, copied Option<u64>, sid/index refusal captures, Result<u64,Error>'),
 anchor('src/experimental/swift.rs',830,839,'Span argument/self reference and checked Option<usize>, predicate shared capture and Result unit'),
 anchor('src/experimental/swift.rs',805,823,'Option<u32>, Type and Option<Type> by-value arguments and match payload copies'),
 anchor('src/experimental/swift.rs',842,880,'actual WasiFunction by-value mapping argument, exhaustive stable vocabulary'),
 anchor('src/experimental/swift.rs',1063,1126,'capacity checked Option<u64> and Some(charge), checked extent/charge additions; fixed nine directories'),
 anchor('src/experimental_swift_reactor/cache/initial_profile_v1.rs',250,270,'actual WASI tuple return/Option wrapping/pattern copies, individual WasiBudget/Grants moves and guard scalar references'),
 anchor('src/experimental_wasi/accounted.rs',432,432,'new immutable helper tuple return from actual same context'),
 anchor('src/experimental_wasi/mod.rs',638,638,'individual actual budget/grants copies into tuple return'),
 anchor('src/experimental_swift_reactor/retained_profile_loader_v1.rs',193,222,'existing identity helper new encoder call: by-value64byte self, output64byte array,8word array into-iterator/enumerate and tuple item'),
 anchor('src/experimental_swift_reactor/retained_profile_loader_v1.rs',1390,1405,'new provenance bridge actual budget reference, eight words, digests/nonce borrowed array and identity encode call/return')]
r.save(r.HERE/'source-place-addendum.json',{
 'schema':1,'status':'additive-independent-source-place-inputs-only-no-admission',
 'candidate_source_tree':'447719d8fef2928674d9d196266408ca72c70ce152cf0251807d2c3bcd7e7c43',
 'producer_roster_complete':False,'producer_core_shapes':52,'producer_supplemental_shapes':27,
 'fresh_helper_shapes':58,'fresh_helper_profiles':list(profiles),'shapes_absent_from_producer_52_plus27_names':additive,
 'source_anchors':anchors,'all_fresh_helper_rows':helper[0]['rows'],
 'compiler_checked_capture_shapes':[
 {'expression':'||field(16,sid,index)','captures':'two shared usize references','bytes':16,'alignment':8},
 {'expression':'|end:usize|end<=source','captures':'one shared usize reference; representative of source-bound predicates','bytes':8,'alignment':8},
 {'expression':'|_:TryFromIntError|SnapshotEncodeErrorV2::Arithmetic','captures':'none','bytes':0,'alignment':1},
 {'expression':'||field(2,0,0)','captures':'none','bytes':0,'alignment':1}],
 'capture_limit':'Four compiler assertions measure capture shapes, not optimized stack reuse or an exhaustive original-expression closure identity matrix. Actual source captures and call-site expression/argument/return/pattern overlaps are explicitly named in anchors; composer must bind their exact selected expressions and multiplicities before any floor.',
 'simultaneous_counts':'Not selected. No complete conservative sum, source-place multiplicity, shared lifetime cutset, consuming scope, or original-control reservation is accepted.',
 'pending_places':'Operational caller/writer/error/stop/work/outer-result/cleanup types do not yet exist in this component and must join separate composition. Existing helper bodies reached by new call sites must be accounted in that composition.',
})
comparisons=[json.loads(p.read_text())for p in sorted((r.HERE/'runs').glob('*/comparison.json'))]
assert len(comparisons)==16 and all(x['status']=='fresh-genuine-independent-byte-semantic-custody-match'for x in comparisons)
assert sum(x['bytes']==9355 for x in comparisons)==4 and sum(x['bytes']==9439 for x in comparisons)==12
privacy=[json.loads((r.HERE/'privacy'/f'{profile}.json').read_text())for profile in profiles]
assert all(len(x['cases'])==32 for x in privacy)
assert sum(case['expected_diagnostics']is not None for x in privacy for case in x['cases'])==116
assert all(case['receipt']['passed']for x in privacy for case in x['cases'])
defaults=[json.loads((r.HERE/'default'/f'{mode}.json').read_text())for mode in('debug','optimized')]
assert all(x['no_host_encoder_export']for x in defaults)
for profile in profiles:
 receipt=json.loads((r.HERE/'commands'/f'{profile}-ordinary'/'receipt.json').read_text())
 assert receipt['passed'] and 'INDEPENDENT_MISSING_SELECTED' in (r.HERE/'commands'/f'{profile}-ordinary'/'stdout').read_text()
for mode in('debug','optimized'):
 for method in('finite_enum_and_option_mappings_v2','span_checks_refuse_bounds_v2'):
  assert '1 passed; 0 failed' in (r.HERE/'commands'/f'enum-span-{mode}-{method}'/'stdout').read_text()
failures=[]
for path in sorted((r.HERE/'commands').glob('*/receipt.json')):
 x=json.loads(path.read_text())
 if not x['passed']:failures.append({'path':str(path.relative_to(r.HERE)),'exit':x['exit'],'diagnostics':x['diagnostics'],'elapsed_seconds':x['elapsed_seconds']})
assert len(failures)==3
assert sum(x['exit']==124 for x in failures)==1
prior=[json.loads((r.HERE/'helper-layouts'/f'{profile}.json').read_text())for profile in('host-debug','host-optimized','unit-debug')]
assert all(x['source']==prior[0]['source']for x in prior)and all(len(x['rows'])==51 for x in prior)
r.save(r.HERE/'timeout-attempt-custody.json',{
 'failed_attempt_receipt':'commands/helper-unit-optimized-compile/receipt.json',
 'failed_outer_exec_session_observed':50659,'failed_outer_exec_exit_observed':1,
 'failed_attempt_original_source_manifest_recorded':False,
 'failed_attempt_source_binding_kind':'reconstructed deterministic equivalence: the unchanged51-shape helper generator and base source produced the identical retained source manifest in three successful configurations; this is not a source hash observed inside the failing receipt',
 'failed_attempt_source_equivalent_manifest':prior[0]['source'],
 'separate_retry_receipt':'commands/helper-unit-optimized-additive-compile/receipt.json',
 'separate_retry_scope':'58 helper shapes plus4 capture size assertions; expanded source rather than an identical51-shape execution',
 'separate_retry_directly_recorded_source':helper[3]['source'],
 'direct_child_cleanup':'Supervisor retained Popen handle, called kill() at55seconds, then wait(); child_reaped=true. The outer Python exec session subsequently completed with exit1.',
 'direct_child_pid_saved':False,'dedicated_process_group_created':False,'descendant_or_group_cleanup_verified':False,
 'cleanup_limit':'No descendant handles were retained; no global process inventory was permitted or used. Descendant/group cleanup is not inferred from retry success or deletion of compiler files.'})
r.custody()
work_inventory=r.manifest(r.WORK)
cleanup={'before':work_inventory,'scope':'Owned candidate-review/work and empty owned privacy/helper scratch roots only; known direct children and outer exec sessions completed/reaped; no foreign process inventory','removed':[],'timeout_descendant_or_process_group_cleanup_verified':False,'timeout_cleanup_evidence':'timeout-attempt-custody.json'}
for path in(r.WORK,r.HERE/'privacy-work',r.HERE/'helper-work'):
 if path.exists():shutil.rmtree(path);cleanup['removed'].append(str(path.relative_to(r.HERE)))
assert not list(r.HERE.rglob('__pycache__'))
cleanup['owned_compiler_scratch_remaining']=False
r.save(r.HERE/'cleanup.json',cleanup)
summary={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'pure-encoder-component-scope-accepted-with-explicit-additive-layout-inputs',
 'candidate_seal_sha256':'eadbe533d23459573ead21c7a9bac54ae929b98cdbc76dd47aebe34b5ceb2b1f',
 'candidate_source_tree_sha256':'447719d8fef2928674d9d196266408ca72c70ce152cf0251807d2c3bcd7e7c43',
 'preaccess_seal_sha256':'c0f8b4987c32a8416aea0d16cbec183498a51b2588a26b13ad3efd8697eb0780',
 'independent_source':json.loads((r.HERE/'independent-source-manifest.json').read_text()),
 'independent_support':json.loads((r.HERE/'independent-support-manifest.json').read_text()),
 'fresh_genuine_byte_semantic_runs':16,'missing_selected_refusals':4,'privacy_positive_cases':12,'privacy_negative_cases':116,'external_privacy_negatives':6,
 'core_layout_shapes_per_profile':52,'additive_helper_shapes_per_profile':58,'capture_shape_assertions_per_profile':4,'profiles':list(profiles),
 'enum_option_and_span_methods':4,'structural_loop_cases':24,'component_behavior_or_privacy_blockers':[],
 'layout_roster_finding':'Producer roster omits helper Result/Option/tuple/capture/identity-call places. Independent source-place-addendum.json names them and freezes measurements; producer roster is not called complete.',
 'retained_failed_commands':failures,'failed_command_resolution':'Two external probes used a non-lib metadata filename and failed E0463; corrected probes require E0603 and pass. One supplementary optimized unit compile reached the55second bound under concurrent compiles; targeted standalone additive retry passed. None is relabeled as a pass.',
 'scope_limits':['No original-control storage/work/deadline/cancellation/stop grant or selected lifetime/consuming cleanup floor','No writer/File acquisition/alias/name/hash/close custody or outer operational outcomes','No complete workload/canonical/native/device/OTA/GA acceptance','WASI zero case has exhausted calls/transfer/work/one-transfer/iovecs/log/grants but retains30000ms deadline; fully all-zero WASI is only synthetic pre-access grammar evidence','Byte block owns no proof authority: block lifetime is the actual caller transfer array. Positive compiler case deliberately permits a filled block to outlive its cursor; live view/cursor still cannot outlive guard borrow. This clarifies the overbroad pre-access wording without changing frozen criteria.'],
 'cleanup':'Known direct children and outer sessions reaped; timeout descendant/process-group cleanup unverified because no handles/group were retained; compiler/scratch files removed; native/UI/capture/process inventory untouched; frozen candidate/preaccess inputs rehashed unchanged; no commits/pushes/canonical edits'}
r.save(r.HERE/'review.json',summary)
print(json.dumps({'status':summary['status'],'fresh_runs':16,'privacy_cases':128,'external_negatives':6,'helper_shapes':58,'omitted_producer_shapes_named':len(additive),'retained_failed_commands':len(failures)},sort_keys=True))
