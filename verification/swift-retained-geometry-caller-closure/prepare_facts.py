"""Bounded stdlib-only text/hash preparation, never verifier or compiler execution."""
from pathlib import Path
import hashlib
import json
import signal
import sys
import time

signal.alarm(50)
started = time.monotonic()
ROOT = Path('/Users/andreyyurlov/Documents/dev/mixer')
OUT = ROOT / 'verification/swift-retained-geometry-caller-closure'
MAPPING = ROOT / 'verification/swift-retained-capture-terminal-mapping'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()

def write(name, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    (OUT / name).write_bytes(raw)

def pin(name):
    path = ROOT / name
    size = path.stat().st_size
    assert path.is_file() and not path.is_symlink()
    h = hashlib.sha256()
    actual = 0
    with path.open('rb') as stream:
        for raw in iter(lambda: stream.read(1024 * 1024), b''):
            actual += len(raw)
            h.update(raw)
    assert actual == size
    return {'path': name, 'bytes': actual, 'sha256': h.hexdigest()}

initial = json.loads((OUT / 'input-pins-before.json').read_bytes())
assert all(pin(p['path']) == p for p in initial['pins'])
manifest_name = 'verification/swift-guarded-snapshot-root-result-lifetime-implementation/source-manifest.json'
manifest = json.loads((ROOT / manifest_name).read_bytes())
assert manifest['member_count'] == len(manifest['members']) == 146
assert sha(canonical(manifest['members'])) == manifest['tree_sha256'] == '91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f'
source_prefix = 'verification/swift-guarded-snapshot-root-result-lifetime-implementation/source/vm/'
source_names = [source_prefix + row['path'] for row in manifest['members']]
for row, name in zip(manifest['members'], source_names):
    actual = pin(name)
    assert (actual['bytes'], actual['sha256']) == (row['bytes'], row['sha256'])
extra_names = [manifest_name,
    'verification/swift-root-bound-dispatch-retained-capture-v1/plan.json',
    'verification/swift-root-bound-dispatch-retained-capture-v1/runtime/receipt.json',
    'verification/swift-semantic-adapter-root-review/dispatch-physical-verifier-v2-host-release.json']
names = sorted({row['path'] for row in initial['pins']} | set(source_names) | set(extra_names))
before = [pin(name) for name in names]
write('all-input-pins-before.json', {'schema': 1, 'pins': before, 'source146_verified': True,
    'source146_tree_sha256': manifest['tree_sha256'], 'raw_distinct_pair_bytes': 111430754})

target_map = json.loads((MAPPING / 'target-map.json').read_bytes())
targets = {row['id']: row for row in target_map['targets'] if row['id'] in ('Caller', 'Closure')}
assert len(targets) == 2
assert sha((MAPPING / 'seal.json').read_bytes()) == '5ec27f9a01bc046341bd0833044d10c0803ce546f9607dc2595e423c0a5fe569'
acceptance = json.loads((ROOT / 'verification/swift-semantic-adapter-root-review/dispatch-retained-physical-identity-acceptance.json').read_bytes())
assert acceptance['packet']['sha256'] == sha((MAPPING / 'seal.json').read_bytes())
contents = {}
whole_anchors = {}
(OUT / 'excerpts').mkdir(exist_ok=True)
for name, row in targets.items():
    whole_anchors[name] = {}
    for art, field, extension in [('ir', 'llvm_definition', 'll'), ('asm', 'assembly_function', 's')]:
        span = row[field]
        with (ROOT / span['file']['path']).open('rb') as stream:
            stream.seek(span['byte_begin'])
            raw = stream.read(span['byte_end'] - span['byte_begin'])
        assert len(raw) == span['byte_end'] - span['byte_begin']
        assert sha(raw) == span['span_sha256']
        assert raw == (MAPPING / 'excerpts' / (name + '.' + extension)).read_bytes()
        assert len(raw.splitlines()) == span['line_end_inclusive'] - span['line_begin'] + 1
        assert raw.startswith(b'define ') and raw.endswith(b'}\n') if art == 'ir' else raw.endswith(b'\t.cfi_endproc\n')
        contents[(name, art)] = raw
        (OUT / 'excerpts' / (name + '.' + extension)).write_bytes(raw)
        whole_anchors[name][art] = {'artifact': art, 'begin': span['byte_begin'], 'end': span['byte_end'],
            'sha256': sha(raw), 'line_begin': span['line_begin'], 'line_end_inclusive': span['line_end_inclusive'],
            'whole_function': True}
    source = row['source']
    raw = (ROOT / source['file']['path']).read_bytes()[source['byte_begin']:source['byte_end']]
    assert sha(raw) == source['span_sha256']
    (OUT / 'excerpts' / (name + '.rs')).write_bytes(raw)

def lines(name, art, needles):
    """Exact complete-line anchors, not interpreted instructions or proof labels."""
    raw = contents[(name, art)]
    base = targets[name]['llvm_definition' if art == 'ir' else 'assembly_function']
    result = []
    offset = 0
    for index, line in enumerate(raw.splitlines(keepends=True)):
        if any(needle.encode() in line for needle in needles):
            result.append({'artifact': art, 'begin': base['byte_begin'] + offset,
                'end': base['byte_begin'] + offset + len(line), 'sha256': sha(line),
                'line': base['line_begin'] + index, 'text': line.decode().rstrip('\n')})
        offset += len(line)
    assert result
    return result

write('whole-function-bindings.json', {'schema': 1, 'targets': list(targets.values()), 'anchors': whole_anchors,
    'complete_spans_rechecked_against_raw': 4, 'native_identity_acceptance_only': acceptance})
debug = json.loads((MAPPING / 'debug-map.json').read_bytes())
debug_ids = set(range(145131, 145147)) | set(range(242858, 242918))
write('debug-bindings.json', {'schema': 1, 'records': [row for row in debug['records'] if row['id'] in debug_ids],
    'scope': 'Frozen source/file/scope bindings for Caller and Closure only; type graphs are not reinterpreted.'})

instruction_groups = {
    'Caller_SP_and_probe': ('Caller', 'asm', ['stp\tx28', 'sub\tsp', 'ldr\txzr', 'add\tsp', 'ldp\tx28', '\tret']),
    'Caller_frame_pointer': ('Caller', 'asm', ['stp\tx29', 'add\tx29', 'ldp\tx29', '[x29, #-']),
    'Caller_local_slots': ('Caller', 'asm', ['add\tx8, sp, #88', 'add\tx8, sp, #64', 'add\tx8, sp, #136', 'add\tx8, sp, #112']),
    'Caller_IR_allocated_slots': ('Caller', 'ir', [' = alloca ', 'ptr sret([24 x i8])']),
    'Caller_pointer_spills': ('Caller', 'asm', ['[sp]', '[sp, #8]', '[sp, #16]', '[sp, #24]', '[sp, #32]', '[sp, #40]', '[sp, #48]', '[sp, #56]']),
    'Caller_child_and_capture': ('Caller', 'asm', ['sub\tx2, x29, #184', 'stur\tx10', '[x2, #8]', '[x2, #24]', '[x29, #-144]', 'add\tx8, sp, #160', 'dispatch_v1', '_memcpy']),
    'Caller_IR_sret_capture_copy': ('Caller', 'ir', ['define hidden', '%_23 =', '%_25 =', 'ptr %_25', '%16 =', '%17 =', 'ptr align 8 %16', 'ptr %17', 'dispatch_v1', 'ptr align 8 %_0, ptr align 8 %_23']),
    'Closure_SP': ('Closure', 'asm', ['sub\tsp', 'stp\tx29', 'add\tx29', 'ldp\tx29', 'add\tsp', '\tret']),
    'Closure_capture_and_body': ('Closure', 'asm', ['mov\tx9', 'ldr\tx0', 'ldur\tq0', 'mov\tx1', 'str\tq0', 'ldr\tx2', '\tbl']),
    'Closure_IR_sret_and_capture': ('Closure', 'ir', ['define hidden', '%_3 =', '%_2 =', '%0 =', 'llvm.memcpy', '%1 =', '%_5 =', 'run_prepaid_admitted_fixture_v1', 'ret void']),
}
write('instruction-anchors.json', {'schema': 1, 'groups': {key: lines(*value) for key, value in instruction_groups.items()},
    'whole_functions_required': whole_anchors})

def slot(name, start, capacity, role, evidence):
    return {'id': name, 'sp_relative_offset': start, 'entry_sp_offset': start - 14000,
        'capacity_bytes': capacity, 'role': role, 'evidence_group': evidence,
        'mapping_status': 'candidate_semantic_mapping_requires_independent_review'}

caller_slots = [
    slot('child_destination_pointer_spill', 0, 8, 'pointer to %_23, reused after Dispatch', 'Caller_pointer_spills'),
    slot('reservation_result_pointer_spill', 8, 8, 'pointer to %_15', 'Caller_pointer_spills'),
    slot('outer_sret_pointer_spill', 16, 8, 'incoming x8 / LLVM %_0; pointer is not the outer storage', 'Caller_pointer_spills'),
    slot('account_argument_spill', 24, 8, 'incoming x0/account pointer', 'Caller_pointer_spills'),
    slot('fixture_argument_spill', 32, 8, 'incoming x1/fixture pointer', 'Caller_pointer_spills'),
    slot('attempt_argument_spill', 40, 8, 'incoming x2/attempt pointer', 'Caller_pointer_spills'),
    slot('expected_argument_spill', 48, 8, 'incoming x3/expected pointer', 'Caller_pointer_spills'),
    slot('quote_result_pointer_spill', 56, 8, 'pointer to %_7', 'Caller_pointer_spills'),
    slot('_6', 64, 24, 'quote Try::branch destination', 'Caller_local_slots'),
    slot('_7', 88, 24, 'selected_whole_quote_v1 destination', 'Caller_local_slots'),
    slot('_14', 112, 24, 'reservation Try::branch destination', 'Caller_local_slots'),
    slot('_15', 136, 24, 'reserve_whole_v1 destination', 'Caller_local_slots'),
    slot('_23', 160, 13640, 'complete Dispatch child result destination C', 'Caller_child_and_capture'),
    slot('_25', 13800, 48, 'closure capture record; fixture0, attempt8..40, expected40', 'Caller_child_and_capture'),
    slot('account.dbg.spill', 13848, 8, 'account debug spill, x29-136', 'Caller_frame_pointer'),
    slot('fixture.dbg.spill', 13856, 8, 'fixture debug spill, x29-128', 'Caller_frame_pointer'),
    slot('expected.dbg.spill', 13864, 8, 'expected debug spill, x29-120', 'Caller_frame_pointer'),
    slot('val.dbg.spill', 13872, 16, 'quote successful value, x29-112', 'Caller_frame_pointer'),
    slot('quote.dbg.spill', 13888, 16, 'quote binding, x29-96', 'Caller_frame_pointer'),
    slot('val.dbg.spill3', 13904, 16, 'reservation successful value, x29-80', 'Caller_frame_pointer'),
    slot('reservation.dbg.spill', 13920, 16, 'reservation binding, x29-64', 'Caller_frame_pointer'),
    slot('residual.dbg.spill', 13936, 16, 'reservation refusal, x29-48', 'Caller_frame_pointer'),
    slot('residual.dbg.spill6', 13952, 16, 'quote refusal, x29-32', 'Caller_frame_pointer'),
    slot('saved_x28_x27', 13968, 16, 'saved state from preindexed push', 'Caller_SP_and_probe'),
    slot('saved_x29_x30', 13984, 16, 'frame/link saved state', 'Caller_frame_pointer'),
]
# This checks the proposed interval partition only. It does not infer native geometry.
assert caller_slots[0]['sp_relative_offset'] == 0
assert all(a['sp_relative_offset'] + a['capacity_bytes'] == b['sp_relative_offset'] for a, b in zip(caller_slots, caller_slots[1:]))
assert caller_slots[-1]['sp_relative_offset'] + caller_slots[-1]['capacity_bytes'] == 14000

caller_steps = [(0,-32),(-32,-4096),(-4128,-4096),(-8224,-4096),(-12320,-1680),(-14000,12288),(-1712,1680),(-32,32)]
closure_steps = [(0,-48),(-48,48)]
for steps in [caller_steps, closure_steps]:
    assert all(before+delta == next_before for (before,delta),(next_before,_) in zip(steps,steps[1:]))
    assert steps[-1][0]+steps[-1][1] == 0
facts = {
    'schema': 1, 'status': 'SOURCE_BOUND_ALTERNATE_CONFIGURATION_CANDIDATE_FACTS_ONLY',
    'targets_owned': ['Caller','Closure'], 'local_geometry_only': True,
    'complete_capacity_accepted': False, 'semantic_geometry_approved': False,
    'runtime_admission_accepted': False, 'original_capture_qualified': False,
    'whole_capacity_prices_backings_root_funding_product_GA_accepted': False,
    'source146_tree_sha256': manifest['tree_sha256'],
    'coordinate_convention': 'E_C/E_L are respective entry SP; intervals half-open; Caller S_C=E_C-14000; Closure S_L=E_L-48.',
    'Caller': {
        'entry_base': 'E_C', 'frame_pointer': 'x29=E_C-16', 'fixed_reservation_bytes': 14000,
        'entry_sp_interval': [-14000,0], 'explicit_numeric_rebase': 14000,
        'sp_path': [{'before':a,'delta':b,'after':a+b} for a,b in caller_steps],
        'normal_IR_paths': [['start','bb5','bb13','bb14'],['start','bb4','bb10','bb13','bb14'],['start','bb4','bb9','bb14']],
        'normal_assembly_paths': [['entry','LBB4875_1','LBB4875_6','LBB4875_5','ret'],['entry','LBB4875_2','LBB4875_3','LBB4875_6','LBB4875_5','ret'],['entry','LBB4875_2','LBB4875_4','LBB4875_5','ret']],
        'normal_ret_count': 1, 'local_cleanup_or_resume_count': 0,
        'unreachable_IR_block': 'bb3 has no predecessors; not a normal return path',
        'probe_offsets_entry_sp': [-4128,-8224,-12320,-14000],
        'probe_limits': 'Four in-function ldr xzr memory touches. No probe helper call or extra SP adjustment here; guard-page/OS effects and fault paths remain outside this packet.',
        'slots': caller_slots,
        'local_reservation_components': {'native_pointer_spills':64,'mapped_IR_allocated_slots':13904,'saved_state':32},
        'partition_limit': 'These separately mapped intervals partition the observed native reservation; no LLVM-allocation sum was used to derive frame size, and no pointee/backing extent follows.',
        'native_outgoing_stack_argument_area': 'No additional stack adjustment or stack-passed argument block is observed at any bl. Return/capture destinations above reside in the fixed reservation; every external callee peak remains pending.',
        'child_C': {'IR':'%_23','capacity_bytes':13640,'entry_sp_offset':-13840,'end_offset':-200,
            'dispatch_sret':'x8=S_C+160','lifetime':'Native reservation exists through all Caller paths. On the counterfactual success route, C is initialized by Dispatch and retained through the following memcpy; physical reservation persists until epilogue.'},
        'outer_O': {'IR':'%_0','declared_sret_bytes':13640,'operand_alignment_requirement':8,
            'pointer_flow':'incoming x8 saved S_C+16; reloaded as x0 for refusal helpers or final memcpy destination',
            'concrete_arena':None,'entry_rebase':None,'physical_relation_to_C_or_frames':'unknown; no equality or disjointness certificate supplied',
            'success_copy':'llvm.memcpy %_0 <- %_23,13640; native _memcpy x0=O,x1=C,x2=13640',
            'refusal_paths':'Two FromResidual call sites receive incoming %_0 directly; callee write-completeness and peaks are outside this lane.'},
        'closure_record': {'IR':'%_25','entry_sp_offset':-200,'capacity_bytes':48,'dispatch_argument':'x2=E_C-200',
            'capture_fields':[{'name':'fixture','offset':0,'bytes':8},{'name':'attempt','offset':8,'bytes':32},{'name':'expected','offset':40,'bytes':8}],
            'lifetime':'Constructed only on bb9 success route before Dispatch; fixed native reservation is not released early. Exact Dispatch capture-copy identity is delegated to its owned lane.'},
    },
    'Closure': {
        'entry_base':'E_L','frame_pointer':'x29=E_L-16','fixed_reservation_bytes':48,
        'entry_sp_interval':[-48,0],'explicit_numeric_rebase':48,
        'sp_path':[{'before':a,'delta':b,'after':a+b} for a,b in closure_steps],
        'IR_basic_blocks':1,'normal_ret_count':1,'local_cleanup_or_resume_count':0,
        'slots':[{'id':'%_3','entry_sp_offset':-48,'capacity_bytes':32,'role':'attempt argument copy from closure record+8; x1=SP passed to Body'},
                 {'id':'saved_x29_x30','entry_sp_offset':-16,'capacity_bytes':16,'role':'saved state'}],
        'incoming_capture_pointer':'%_1 / native x0 copied to x9; input record is owned/mapped by Dispatch lane',
        'loads':[{'field':'fixture','offset':0,'native_destination':'x0'},{'field':'attempt','offset':8,'bytes':32,'native_destination':'[SP,SP+32), Body x1=SP'},{'field':'expected','offset':40,'native_destination':'x2'}],
        'R_forwarding':{'state':'candidate_resolved_same_pointer','IR':'Body called with exact Closure %_0 sret([13624 x i8]) align8; no GEP/cast/PHI for this pointer',
            'assembly':'No explicit Closure instruction before the Body bl writes x8. Body receives the same incoming hidden return register; preservation across the callee execution is not claimed.',
            'capacity_or_initialization_proved_here':False,'capacity_contract_bytes':13624,
            'lifetime':'Closure local32 stays reserved through Body call and is reclaimed only after Body returns; no result buffer is allocated in Closure.'},
        'native_outgoing_stack_argument_area':'No extra SP adjustment or stack-passed argument block; Body call uses borrowed record fields and local32, with transitive peak pending.',
    },
    'cross_function_base_relations':[
        {'left':'CallerEntrySP','right':'DispatchEntrySP','right_minus_left':-14000,'kind':'candidate_same_base_coordinate_delta','source':'Caller SP unchanged at exact direct Dispatch bl; callee entry semantics still require independent review'},
        {'left':'ClosureEntrySP','right':'BodyEntrySP','right_minus_left':-48,'kind':'candidate_same_base_coordinate_delta','source':'Closure SP unchanged at exact direct Body bl; callee entry semantics still require independent review'}],
    'alignment':{
        'known_physical_base_congruences':[],
        'physical_alignment_for_candidate_native_arenas':None,
        'required_or_assumed_contracts':['LLVM alloca and sret/load/store operands shown with align8 constrain valid addresses; they are recorded as requirements, not new reviewed physical-base facts.',
            'A Caller frame role aligned8 would require E_C congruent0 mod8 because -14000 is divisible8; a Closure frame role aligned8 would require E_L congruent0 mod8 because -48 is divisible8.',
            'All SP deltas preserve a preexisting modulo16 congruence; preservation cannot establish that congruence.',
            'A 16-byte q register access or CFI directive alone does not certify an actual base modulus16 congruence.'],
        'missing':['Independently reviewed entry-SP congruence or applicable pinned ABI premise; actual outer-sret base alignment evidence; complete connected-base relation review.'],
        'numeric_local_union_allowed':False},
    'normal_exception_limits':['Fixed SP paths describe explicit normal returns only. No invoke/landingpad/resume, personality/LSDA or in-function cleanup edge is present in these complete two functions.',
        'CFI records saved-state unwinding conventions but does not bound any external unwind runtime or destructor continuation.',
        'Calls can unwind or fault; no cleanup/destruction peak or OS backing bound is supplied.',
        'No llvm.lifetime.end or source StorageDead is treated as early physical stack release.'],
    'pending_admission':'selected_whole_quote_v1 source returns WholeQuotePending at host_account_v1.rs:76. Native success-route emission does not establish runtime reachability.'}
write('facts.json',facts)

edges=[]
for name in ('Caller','Closure'):
    # Complete whole-function text was separately read/reviewed. This records every
    # emitted bl line and every IR call line; regex or text matching grants nothing.
    asm_calls=lines(name,'asm',['\tbl\t'])
    ir_calls=lines(name,'ir',['  call void '])
    for index,anchor in enumerate(asm_calls):
        destination=anchor['text'].split('\tbl\t',1)[1]
        internal='Dispatch' if name=='Caller' and 'dispatch_v1' in destination else ('Body' if name=='Closure' and 'run_prepaid_admitted_fixture_v1' in destination else 'outside')
        edges.append({'id':name+'_bl_'+str(index),'target':name,'destination':internal,'symbol':destination,'kind':'call',
            'anchor':anchor,'explicit_SP_adjustment_at_edge':False,'transitive_frame_backing_and_unwind_bound':None})
    write(name.lower()+'-call-sites.json',{'schema':1,'whole_function':whole_anchors[name],
        'native_call_sites':asm_calls,'IR_call_sites':ir_calls,
        'intrinsic_note':'Closure attempt32 and Caller capture32 llvm.memcpy lower to the shown in-function q-register copies. Caller final13640 copy lowers to external _memcpy.'})
assert len([e for e in edges if e['target']=='Caller'])==8
assert len([e for e in edges if e['target']=='Closure'])==1
backings = ['acquisition_inputs','acquisition_paths','p0_binding'] + ['file'+str(i) for i in range(5)] + ['executable','proof','error','cancellation','claims']
write('unresolved-obligations.json',{
    'schema':1,'native_edges':edges,
    'outer_escape':'O points outside this lane; concrete base/rebase/extent physical proof, disjointness, upstream lifetime and final destruction are unresolved.',
    'argument_escapes':['account is external P0/root state; reservation words retain its borrow and charge.',
        'fixture pointer refers to ReviewedFixtureBindingV1; its five borrowed Paths, claims and budgets have separate P0 backing.',
        'attempt32 contains expected provenance reference, live Cell reference, association scalar and root ledger reference; pointer widths bound none of their pointees.',
        'expected points to correspondence/provenance/root data whose owner lifetime and acquisition backing are external.',
        'Dispatch receives a pointer to Caller capture record. Closure receives a Dispatch-mapped record pointer; all references loaded from it continue into Body.',
        'Complete child and outer copies preserve ownership obligations, not duplicate owned backings or zero-price references.'],
    'backings':[{'key':key,'capacity_bytes':None,'destruction_complete':False,'conditional_source_obligation':True} for key in backings],
    'destructors':['Source PrepaidOwnedV1::destroy_owned_v1 takes and drops owned payload, drops self, returns a P0 DestroyedStorage token; no assembly for that continuation is covered.',
        'Source Drop for PrepaidOwnedV1 drops retained payload and never refunds while wrapper/source frame is live.',
        'Resource File/OS retirement, optional executable, original proof/error graphs, shared Cancellation, claims/output state, Arc allocator overhead and unwind runtime remain pending.'],
    'missing_base_and_rebase_facts':['Concrete outer ReturnDestination base and rebase; physical relation to Caller child/native frames.',
        'Actual address congruences for CallerEntrySP, ClosureEntrySP and outer destination; numerical rebases do not establish them.',
        'Independent whole-frontier agreement for Caller→Dispatch and Dispatch→Closure→Body entry-SP coordinate deltas.',
        'Body/Dispatch native frames and all cleanup exits belong to their separate lane; no cross-callee peak follows here.'],
    'retained_partitions':['acquisition_operation','acquisition_cleanup','acquisition_storage','P0','C0','C1','C2','C3','C4','C5'],
    'work_prices_root_funding':None,'local_geometry_only':True,'complete_capacity_accepted':False})

capture_plan=json.loads((ROOT/'verification/swift-root-bound-dispatch-retained-capture-v1/plan.json').read_bytes())
frontier=json.loads((ROOT/'verification/swift-root-bound-dispatch-physical-plan/target-frontier.json').read_bytes())
frontier_rows={row['id']:row for row in frontier['targets']}
write('verifier-review-fragments.json',{
    'schema':1,'status':'NOT_A_CERTIFICATE_NOT_INVOKABLE','intended_verifier':'verification/swift-root-bound-dispatch-physical-evidence-v2/source/region_certificate.py',
    'actual_alternate_binding':capture_plan['verifier_binding'],
    'binding_blockers':['Verifier CURRENT_BINDING pins original argv 4022ae1057439fe5ae31d18675a884b2dc3e56f317a8ddced08bfb163a410aaa and original capture plan bed9476b169810452ac0932605784125365f57c897d1e3bf74cd9eaa6ebb8184.',
        'Actual alternate argv 799f61fd0bff3d5eba3849b784e7bc7b699a5ee84a2a814f298f407befb28e75 and plan 15413684daf6815fbc9773c7fecf669f035768116524e567a841bd571c3f31c8 differ; link_dead_code and alternate_configuration are absent from the closed verifier binding schema.',
        'Do not strip alternate flags, relabel as original, synthesize approval or execute this fragment. Separate root-selected source/custody adaptation and independent semantic approval are required.'],
    'native_arena_fragments':[{'id':'A_F'+name,'base':name+'EntrySP','entry_min':-size,'entry_max':0,'rebase':size,
        'reviewed_rebase':False,'evidence':[whole_anchors[name]['asm']],'physical_alignment':None} for name,size in [('Caller',14000),('Closure',48)]],
    'target_frontier_sha256':{name:sha(canonical(frontier_rows[name])) for name in ('Caller','Closure')},
    'whole_cfg_candidate_status':'Whole two-function text has been inspected; independent whole-frontier semantic review and root approval absent.',
    'region_lifetime_sketch':{'FCaller':[0,5],'FClosure':[0,2],'C':'Contained at CallerEntrySP-13840; role belongs to Dispatch and must be rooted in its lane evidence.','O':'External arena/base/relations unresolved; no numeric row.'},
    'not_supplied':['complete semantic_map','certificate','independent semantic approval','root approval','physical base congruence','numeric union','crosscallee peak'],
    'source_inspection_only':True,'verifier_import_or_execution_count':0,'complete_capacity_accepted':False})

after=[pin(name) for name in names]
assert before==after
write('all-input-pins-after.json',{'schema':1,'pins':after,'identical_to_before':True,'source146_verified':True,'source146_tree_sha256':manifest['tree_sha256']})
terminal=json.loads((MAPPING/'terminal-review.json').read_bytes())
write('preparation-receipt.json',{
    'schema':1,'command':'python3 -B verification/swift-retained-geometry-caller-closure/prepare_facts.py',
    'cwd':str(ROOT),'tool_version_from_current_interpreter_without_probe':sys.version,
    'compiler_version_from_saved_pinned_receipt_only':terminal['compiler_tool_version_from_saved_capture_only'],
    'source146_tree_sha256':manifest['tree_sha256'],'input_pin_count':len(before),'all_before_after_pins_identical':True,
    'raw_distinct_pair_bytes':111430754,'raw_limit_bytes':128*1024*1024,'derived_limit_bytes':8*1024*1024,
    'per_command_alarm_seconds':50,'root_per_command_limit_seconds':55,
    'whole_Caller_Closure_function_spans_rechecked':4,'source_spans_rechecked':2,
    'full_local_inputs_read':True,'truncated_evidence_retained':False,
    'display_note':'Exploratory directory/metadata displays exceeded tool display budgets; no semantic finding is based on a partial display. Complete Caller/Closure functions were displayed without truncation and whole local spans independently rehashed.',
    'compiler_native_model_tests_verifier_version_or_process_probe_invocations':0,
    'computer_use_screen_capture_simulator_emulator':False,
    'owned_children_started':0,'native_instances_started':0,'runtime_cleanup_owed':False,
    'scope':'Alternate diagnostic geometry preparation only; original capture missing-target finding and WholeQuotePending unchanged.',
    'independent_review_pending':True,'product_global_metadata_or_frozen_packet_changes':False,
    'output_summary':'facts-prepared-only; all 203 before/after pins identical; 4 whole native spans and 2 source spans rechecked; no compiler/verifier/native invocation',
    'elapsed_seconds_before_seal':time.monotonic()-started,
    'local_geometry_only':True,'complete_capacity_accepted':False})
members=[]
for p in sorted(OUT.rglob('*')):
    if p.is_file() and p.name!='seal.json':
        raw=p.read_bytes();members.append({'path':str(p.relative_to(OUT)),'bytes':len(raw),'sha256':sha(raw)})
assert sum(row['bytes'] for row in members) < 8*1024*1024
write('seal.json',{'schema':1,'status':'FROZEN_CALLER_CLOSURE_ALTERNATE_GEOMETRY_CANDIDATE_FACTS',
    'members':members,'member_count':len(members),'member_bytes':sum(row['bytes'] for row in members),
    'tree_sha256':sha(canonical(members)),'source146_tree_sha256':manifest['tree_sha256'],
    'independent_review_pending':True,'semantic_geometry_approved':False,'local_geometry_only':True,
    'runtime_admission_accepted':False,'original_capture_qualified':False,'complete_capacity_accepted':False})
print(json.dumps({'status':'facts-prepared-only','members':len(members),'derived_member_bytes':sum(row['bytes'] for row in members),
    'input_pins':len(before),'all_before_after_pins_identical':True,'elapsed_seconds':time.monotonic()-started,
    'seal_sha256':sha((OUT/'seal.json').read_bytes())},sort_keys=True))
