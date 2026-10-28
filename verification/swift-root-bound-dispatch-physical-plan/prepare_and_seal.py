#!/usr/bin/env python3
"""Freeze a source-only next-slice plan. No compiler/model/verifier is invoked."""
from pathlib import Path
import datetime
import hashlib
import json
import sys
import time

D=Path(__file__).resolve().parent
R=D.parents[1]
SOURCE_TREE='91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f'
VM=R/'verification/swift-guarded-snapshot-root-result-lifetime-implementation/source/vm'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def row(path,base=R):
    assert path.is_file() and not path.is_symlink()
    digest=hashlib.sha256();size=0
    with path.open('rb') as stream:
        while raw:=stream.read(262144):digest.update(raw);size+=len(raw)
    return {'path':path.relative_to(base).as_posix() if path.is_relative_to(base) else str(path),'bytes':size,'sha256':digest.hexdigest()}
def put(name,value):
    with (D/name).open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')
def verify_members(manifest,base,expected_tree=None):
    members=manifest['members']
    assert manifest.get('member_count',len(members))==len(members)
    assert len({item['path'] for item in members})==len(members)
    if 'tree_sha256' in manifest:assert sha(canonical(members))==manifest['tree_sha256']
    if expected_tree:assert manifest['tree_sha256']==expected_tree
    for member in members:assert row(base/member['path'],base)==member
    return [base/member['path'] for member in members]
def sealed(relative,expected):
    path=R/relative;assert row(path)['sha256']==expected
    return [path]+verify_members(json.loads(path.read_bytes()),path.parent)
def lines_scope(path,first,last):
    raw=path.read_bytes();lines=raw.splitlines(keepends=True)
    begin=sum(map(len,lines[:first-1]));end=sum(map(len,lines[:last]))
    return {'file':row(path),'line_begin':first,'line_end_inclusive':last,'byte_begin':begin,'byte_end':end,'span_sha256':sha(raw[begin:end])}
def main():
    start=time.monotonic();assert not (D/'seal.json').exists() and not (D/'command').exists()
    acceptance=R/'verification/swift-semantic-adapter-root-review/dispatch-region-model-v4-acceptance.json'
    assert row(acceptance)['sha256']=='75016d390a06112fce1463b6d84edfe9329442d747c69086b7333f2ed4e7dbe3'
    assert json.loads(acceptance.read_bytes())['status']=='accepted-isolated-synthetic-host-model-only'
    frozen=[]
    for relative,digest in [
        ('verification/swift-root-bound-dispatch-region-model-v2/seal.json','53ab4e6ef041346dadadbbba69b7e5f5a7c35df004d9f1da753845be15779861'),
        ('verification/swift-root-bound-dispatch-region-model-independent/runtime-terminal-review-2/seal.json','7dbc8f943b73705a32d50317cc17ace7552d24f47fd3d0a1e3e27619f01f9600'),
        ('verification/swift-root-bound-dispatch-lifetime-contract/seal.json','1ce05f8759b634e7a8c651a88ea4290b69ba8fde5bb100ed86802a0a5599a882'),
        ('verification/swift-root-bound-layout-warning-classification/seal.json','39976085aa6fd3cebf5c12bb6376358c46b11223df8347b8fb70ef12c20be5ab')]:
        frozen.extend(sealed(relative,digest))
    source_manifest=R/'verification/swift-guarded-snapshot-root-result-lifetime-implementation/source-manifest.json'
    source_doc=json.loads(source_manifest.read_bytes());source_members=verify_members(source_doc,VM,SOURCE_TREE)
    assert len(source_members)==146
    prior_path=R/'verification/swift-root-bound-work-storage-layout-probe-v3/plan.json';prior=json.loads(prior_path.read_bytes())
    toolmanifest=R/'verification/swift-root-bound-work-storage-layout-probe/toolchain-manifest.json'
    tools=json.loads(toolmanifest.read_bytes());tool_members=verify_members(tools,Path(tools['root']))
    sdkmanifest=R/'verification/swift-root-bound-work-storage-layout-probe/sdk-path-settings.json';sdk=json.loads(sdkmanifest.read_bytes())
    assert row(Path(prior['compiler']['path']))==prior['compiler']
    layout_acceptance=R/'verification/swift-semantic-adapter-root-review/root-bound-layout-observation-acceptance.json'
    assert row(layout_acceptance)['sha256']=='5bbed125873c4082ac0d7f62f9e1ee575ff67a96bfd27fe6eadee0a5ff83b9a8'
    mir=R/'verification/swift-root-bound-work-storage-delta-independent/candidate-selected-complete.mir'
    initial=VM/'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
    host=VM/'src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'
    closure=b'|| run_prepaid_admitted_fixture_v1(fixture, attempt, expected)'
    raw=initial.read_bytes();assert raw.count(closure)==1;begin=raw.index(closure)
    targets=[
        {'id':'Caller','name':'run_one_admitted_fixture_v1','source':lines_scope(initial,853,862),'retained_MIR':lines_scope(mir,630,832),
            'required_native_facts':['caller frame','child result destination','outer Result destination','direct dispatch instantiation'],
            'pending_selectors':'selected_whole_quote_v1 remains WholeQuotePending; this compile executes no selector'},
        {'id':'Closure','name':'run_one_admitted_fixture_v1::{closure#0}','source':{'file':row(initial),'byte_begin':begin,'byte_end':begin+len(closure),'span_sha256':sha(closure),'expression':closure.decode()},
            'retained_MIR':lines_scope(mir,833,864),'required_native_facts':['exact 861:36 closure identity','callee return-pointer forwarding','closure frame and return']},
        {'id':'Dispatch','name':'ReservationV1::dispatch_v1<AdmittedFixtureOutcomeV1,exact closure>','source':lines_scope(host,133,141),'retained_MIR':lines_scope(mir,200,251),
            'retained_MIR_is_generic_template_not_native_monomorphization':True,
            'required_native_facts':['unique actual admitted instantiation','action return slot','Option<T> and PrepaidOwned construction','dispatcher frame and returned child destination']},
        {'id':'Body','name':'run_prepaid_admitted_fixture_v1','source':lines_scope(initial,863,883),'retained_MIR':lines_scope(mir,865,1326),
            'complete_return_constructs':[lines_scope(initial,872,872),lines_scope(initial,882,882)],
            'required_native_facts':['all normal return stores','sret destination','complete local native frame','all call and cleanup obligations retained unknown unless separately covered']},
    ]
    put('target-frontier.json',{'schema':1,'source146_tree_sha256':SOURCE_TREE,'targets':targets,
        'known_type_minima_only':[{'role':'AdmittedReturn','bytes':13624,'alignment':8},{'role':'ChildWrap','bytes':13640,'alignment':8},
            {'role':'outer Result if separately stored','bytes':13640,'alignment':8}],
        'unknown_Body_frame_bytes':None,'source_outcome_families':{'setup_failure_prefixes':5,'counterfactual_invariant_fallback':1,'loaded_raw_refusals':2,'loaded_leaf_results':3},
        'not_yet_known':['native symbols and ranges','all physical arena identities/offsets','return-slot/child aliases','native frames and call peaks','backing capacity or final destruction'],
        'destruction_continuation':{'source':lines_scope(initial,884,889),'out_of_this_capture_frontier':True,'no_normal_return_fact_qualifies_destruction_or_unwind_peak':True}})
    output=D/'command';compiler=prior['compiler']['path']
    argv=[compiler,'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin',
        '-C','overflow-checks=yes','-C','panic=unwind']
    for feature in ['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']:
        argv += ['--cfg','feature="'+feature+'"']
    argv += ['--cfg','mixer_bootstrap_one_fixture_v1','-C','opt-level=0','-Zmir-opt-level=0','-C','codegen-units=1','-C','debuginfo=2',
        '--crate-type','rlib',str(VM/'src/lib.rs'),'--error-format=json',
        '--emit=llvm-ir='+str(output/'dispatch.ll')+',asm='+str(output/'dispatch.s')]
    environment=dict(prior['environment']);environment['CARGO_MANIFEST_DIR']=str(VM);environment['TMPDIR']=str(output/'tmp')
    put('capture-plan.json',{'schema':1,'status':'SOURCE_ONLY_PROPOSED_CAPTURE_NOT_RELEASED','approach':'exact-toolchain-physical-region-evidence',
        'source_directory':str(VM),'source_manifest':row(source_manifest),'source_tree_sha256':SOURCE_TREE,'source_edits':0,
        'compiler':prior['compiler'],'version_from_prior_pinned_receipt':prior['toolchain_version'],'toolchain_manifest':row(toolmanifest),'SDK_manifest':row(sdkmanifest),
        'argv':argv,'argv_sha256_canonical_JSON':sha(canonical(argv)),'environment':environment,'cwd':str(R),
        'inspection_only_settings':['codegen-units=1','debuginfo=2'],'qualifies_only_this_exact_build_not_previous_Debug_opt2_or_future_product':True,
        'emit_only':['LLVM IR','assembly'],'linker_invocations':0,'host_binary_invocations':0,'layout_query_invocations':0,'model_test_invocations':0,
        'bounds':{'wall_seconds':55,'work_deadline_seconds':44,'owned_cleanup_deadline_seconds':49,'posthash_deadline_seconds':53.5,
            'compiler_invocations':1,'automatic_retries':0,'maximum_generated_members':64,'maximum_generated_total_bytes':268435456,
            'maximum_stdout_bytes':1048576,'maximum_stderr_bytes':2097152,'formatter_or_version_queries':0},
        'owned_output_directory':str(output),'prelaunch_directory_absent':True,'no_existing_source_or_build_directory_mutation':True,
        'required_before_release':['Root-selected independently reviewed controller delta and exact source pins',
            'Frozen whole-stream expected source-bound baseline warning records and exact success summary; unknown diagnostic refuses',
            'One runtime lane, exact PID/group custody and cleanup, enforced live output/file bounds and input/artifact memory/path hashes',
            'Observed cleanup and all final hashing before one-way signal cutoff; observation before final receipt'],
        'root_release_required':{'path':'verification/swift-semantic-adapter-root-review/dispatch-physical-capture-release.json',
            'exact_capture_plan_sha256_required':True,'exact_reviewed_controller_sha256_required':True,'compiler_lane_released':True,'compiler_invocations':1,'automatic_retries':0},
        'stop_without_fallback':['missing/ambiguous actual function or monomorphization','unclassified diagnostic','timeout or resource/output ceiling','owned custody or cleanup ambiguity','changed input/artifact bytes'],
        'raw_capture_accepts_no_region_fact_or_capacity':True,'compiler_executed_during_this_preparation':0})
    requirements=[
        {'id':'R','must_resolve':['actual body/closure/dispatcher return-pointer identity','13624-byte whole carrier coverage and >=8 alignment','arena/base+offset/capacity','all normal return and pre-wrap lifetime coverage'],
            'must_not_infer':['move implies same storage','Body frame8 covers carrier','equal numeric size implies identity']},
        {'id':'C','must_resolve':['13640-byte complete child and optional distinct outer Result destinations','nested Option/T containment','same-arena offsets or proved separate arenas','phase-wise checked union'],
            'must_not_infer':['child width funds earlier return automatically','contained13624 charged in addition to whole13640','same source variable is physical arena evidence']},
        {'id':'F','must_resolve':['complete native local frame including saved state/padding/spills/outgoing storage','all normal/cleanup SP paths and exits','coexisting caller/dispatcher/closure frames','independent mapping from LLVM slots into native frame'],
            'remains_missing_without_further_evidence':['deeper setup/loader/leaf/stdlib/drop/unwind call peaks','unresolved dynamic adjustments or indirect callees','destruction continuation frames'],
            'must_not_infer':['LLVM alloca total is native frame','StorageDead frees stack bytes','one prologue supplies all-path/transitive peak']},
        {'id':'B','must_retain_unknown':['original acquisition inputs/paths','P0 binding/parent/token storage','exact successful child File prefix','optional executable','original proof and error backing graphs','one shared Cancellation backing','claims/output state'],
            'must_not_infer':['pointer/descriptor width bounds backing','same path/inode deduplicates distinct open ownership','requested Arc bytes equal allocator capacity','drop counter proves healthy File/OS retirement']},
    ]
    put('evidence-requirements.json',{'schema':1,'requirements':requirements,
        'certificate_fields':['exact source/compiler/target/cfg/inspection-flag pins','raw in-memory artifact length/hash and custody','unique source/MIR/native symbol binding',
            'whole relevant function CFG/normal/cleanup exits','arena identity and entry-relative base','checked offset/capacity/alignment','finite phase intervals',
            'instruction/SSA/frame-map byte anchors plus independently reviewed semantic argument','unresolved outgoing call/backing obligations','exact reviewed certificate hash and independent seal'],
        'allowed_outputs':['capture_custody_only','unreviewed_local_region_candidate','reviewed_local_geometry_with_explicit_missing_facts','incomplete_or_invalid'],
        'all_results_local_geometry_only':True,'complete_capacity_accepted':False,'production_authority_constructible':False,
        'retained_partitions':['acquisition operation work','acquisition cleanup work','acquisition storage','P0 work and storage','C0 work and storage','C1 work and storage','C2 work and storage','C3 work and storage','C4 work and storage','C5 work and storage'],
        'unit_rules':['geometry bytes and work units are distinct','no quote/grant/refund selected','no shrinking retained checked six-component sums','no duplicate leaf or skipped parent/token']})
    controls=[
        ('P01','Strict record grammar','duplicate keys, nonfinite/boolean integers, duplicate IDs or unknown fields refuse'),
        ('P02','Actual saved-byte custody','wrong length/hash, bounded-read +1 overflow, changed path pre/post or different in-memory bytes refuse'),
        ('P03','Exact frontier identity','missing/duplicate native function, wrong source cfg/target/compiler, proxy closure or raw-fixture dispatch refuses'),
        ('P04','Complete carrier','missing/13623-byte/expired R refuses; complete13624 synthetic carrier spans all source return constructs'),
        ('P05','Complete child','missing/13639-byte C or unbound separate outer Result refuses;13640 is minimum only'),
        ('P06','No fake Body','Body missing, arbitrary eight-byte frame, LLVM-alloca-only or partial prologue/exit explanation stays incomplete'),
        ('P07','Return-pointer proof','unresolved PHI, cast, indirect call, memcpy origin/destination or mismatched caller-return slot stays unknown'),
        ('P08','Evidence-backed relation','semantic move/equal width/numeric arena ID alone cannot assert alias or disjointness'),
        ('P09','Checked geometry','offset+capacity overflow, invalid alignment, reversed/out-of-frame interval or unit mismatch refuses'),
        ('P10','Finite union arithmetic','explicit same-arena partial/contained overlaps count once; proved separate arenas add; incompatible relation refuses'),
        ('P11','Phase completeness','narrow child begins at ChildWrap; earlier R and coexisting frame must each be covered; expired or skipped segment refuses'),
        ('P12','Native frame containment','slots proven inside full native frame count once; unproven cross-frame relation or omitted outgoing storage stays unknown'),
        ('P13','Transitive and cleanup limits','missing callee bound, dynamic stack/probe helper, cleanup/unwind or destruction frame blocks complete capacity'),
        ('P14','Backing continuity','same semantic backing moves R->C without fresh charge; missing capacity/destruction never becomes zero or a physical bound'),
        ('P15','Review and authority boundary','unsealed certificate or arbitrary ReviewedBound-looking labels cannot produce reviewed geometry; even reviewed local facts produce no quote/grant'),
        ('P16','Capture limits and diagnostics','truncated/oversized/DCE-missing capture, unknown warning/error/summary or changed raw bytes yields no region acceptance and no automatic retry'),
    ]
    put('prospective-controls.json',{'schema':1,'status':'PROPOSED_NOT_IMPLEMENTED_OR_EXECUTED','families':[{'id':i,'subject':s,'required':r,'executed':False} for i,s,r in controls],
        'positive_fixture_scope':'Small independently authored synthetic artifact/certificate byte strings only; no proxy fixture proves actual physical layout.',
        'runtime_failure_branches_not_qualified_by_synthetic_controls':True})
    future='verification/swift-root-bound-dispatch-physical-evidence-v1/source/'
    put('next-slice.json',{'schema':1,'selected_approach':'exact-toolchain physical region capture plus independently reviewed finite certificate',
        'proposed_source_files':[future+'region_certificate.py',future+'tests_region_certificate.py'],
        'implementation_surface':['strict bounded saved-byte/JSON reader','closed four-target certificate schema','pin/span/geometry/lifetime/checked-union checks',
            'exact root-approved certificate/review-seal binding','local_geometry_only output and explicit incomplete facts','16 synthetic control families'],
        'not_a_generic_LLVM_assembly_or_type_normalizer':True,'semantics_review_cannot_be_replaced_by_matching_snippets':True,
        'stages':['Root reviews this source-only plan','Implement/freeze/source-review verifier and synthetic controls; no actual parse',
            'Root separately freezes/reviews exact capture controller, diagnostics and one compiler release','Capture unchanged source once; save whole raw bounded artifacts and terminal custody',
            'Producer maps whole target slices; independent reviewer seals the exact semantic region certificate','Root releases one exact saved-input verifier invocation; review local facts and remaining unknowns'],
        'future_offline_command_template':['/opt/homebrew/opt/python@3.14/bin/python3.14','-B',future+'tests_region_certificate.py'],
        'future_offline_limits':{'wall_seconds':55,'children':0,'compiler_or_version_queries':0,'network':False},
        'commands_not_released_and_source_not_created_by_this_packet':True,
        'canonical_product_source_changes':0,'new_storage_wrapper_selected':False,'current_pending_selectors_unchanged':True,
        'numeric_prices_actual_backing_bounds_root_durability_product_integration_GA_pending':True})
    inputs=[acceptance,layout_acceptance,source_manifest,prior_path,toolmanifest,sdkmanifest,mir,R/'AGENTS.md',R/'mixer-product-plan.md']+frozen
    unique=list(dict.fromkeys(inputs))
    before=[row(path) for path in unique]
    put('input-manifest.json',{'schema':1,'inputs':before,'source146_manifest':row(source_manifest),'source146_members_checked':146,'source146_tree_sha256':SOURCE_TREE,
        'toolchain_manifest':row(toolmanifest),'toolchain_members_checked':len(tool_members),'SDK_settings':[row(Path(item['path'])) for item in sdk['settings']],
        'all_prior_frozen_members_checked':len(frozen),'new_source_or_compiler_commands':0})
    assert [row(path) for path in unique]==before
    verify_members(source_doc,VM,SOURCE_TREE)
    verify_members(tools,Path(tools['root']))
    summary={'status':'SOURCE_ONLY_PHYSICAL_PLAN_FROZEN','approach':'exact-toolchain region evidence','targets':4,'prospective_control_families':16,
        'source_edits':0,'compiler_model_layout_runtime_queries':0,'next_source_files_proposed':2,'complete_capacity_accepted':False}
    (D/'preparation.stdout').write_text(json.dumps(summary,sort_keys=True)+'\n');(D/'preparation.stderr').write_bytes(b'')
    assert time.monotonic()-start<55
    put('preparation-receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command':[str(Path(sys.executable).resolve()),'-B',str(Path(__file__).resolve())],'cwd':str(R),'python':sys.version,'python_tool':row(Path(sys.executable).resolve()),
        'preparation_source':row(Path(__file__).resolve()),'source_tree_sha256':SOURCE_TREE,'capture_plan':row(D/'capture-plan.json'),'input_manifest':row(D/'input-manifest.json'),
        'stdout':row(D/'preparation.stdout'),'stderr':row(D/'preparation.stderr'),'elapsed_seconds':time.monotonic()-start,'wall_ceiling_seconds':55,
        'scope':'Read/hash immutable inputs and author a finite source-only plan; no future verifier or test implementation executed.',
        'compiler_model_layout_formatter_version_runtime_child_native_UI_capture_device_network_global_process_queries':0,'all_prior_packets_unchanged':True})
    members=[row(path,D) for path in sorted(D.rglob('*')) if path.is_file() and path.name!='seal.json']
    seal={'schema':1,'status':'FROZEN_SOURCE_ONLY_DISPATCH_PHYSICAL_EVIDENCE_PLAN_AWAITING_REVIEW','members':members,'member_count':len(members),
        'member_bytes':sum(item['bytes'] for item in members),'tree_sha256':sha(canonical(members)),'capture_plan_sha256':sha((D/'capture-plan.json').read_bytes()),
        'source146_tree_sha256':SOURCE_TREE,'proposed_targets':4,'prospective_control_families':16,'compiler_model_layout_runtime_executed':0,
        'canonical_policy_or_metadata_changed':False,'physical_capacity_prices_backing_bounds_root_funding_product_GA_accepted':False}
    put('seal.json',seal)
    print(json.dumps({'status':seal['status'],'member_count':len(members),'seal_sha256':sha((D/'seal.json').read_bytes()),'tree_sha256':seal['tree_sha256'],
        'capture_plan_sha256':seal['capture_plan_sha256'],'elapsed_seconds':time.monotonic()-start}))
if __name__=='__main__':main()
