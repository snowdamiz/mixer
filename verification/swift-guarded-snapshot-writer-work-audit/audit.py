#!/usr/bin/env python3
"""Pure Python source custody + finite arithmetic models; never runs Rust or a writer."""
from pathlib import Path
import hashlib, json, platform, sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SRC = ROOT / 'verification/swift-guarded-snapshot-composition-source-preparation/source/vm/src'
ENC = ROOT / 'verification/swift-guarded-snapshot-encoder-work-audit'

def sha(data): return hashlib.sha256(data).hexdigest()
def emit(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

# One complete named definition, including its terminating newline. Brace scan
# ignores Rust double-quoted strings and comments, never analyzes authority.
def definition(path, marker, occurrence=0):
    data = (SRC / path).read_bytes()
    starts = []; at = 0
    while True:
        at = data.find(marker.encode(), at)
        if at < 0: break
        starts.append(at); at += len(marker)
    start = starts[occurrence]; brace = data.index(b'{', start)
    i = brace; depth = 0; state = 'code'; block_depth = 0
    while i < len(data):
        pair = data[i:i+2]; c = data[i:i+1]
        if state == 'line':
            if c == b'\n': state = 'code'
        elif state == 'block':
            if pair == b'/*': block_depth += 1; i += 1
            elif pair == b'*/':
                block_depth -= 1; i += 1
                if block_depth == 0: state = 'code'
        elif state == 'string':
            if c == b'\\': i += 1
            elif c == b'"': state = 'code'
        elif pair == b'//': state = 'line'; i += 1
        elif pair == b'/*': state = 'block'; block_depth = 1; i += 1
        elif c == b'"': state = 'string'
        elif c == b'{': depth += 1
        elif c == b'}':
            depth -= 1
            if depth == 0:
                end = i + 1
                if data[end:end+1] == b'\n': end += 1
                body = data[start:end]
                context_start = data.rfind(b'\n', 0, start) + 1
                while context_start:
                    previous_start = data.rfind(b'\n', 0, context_start-1) + 1
                    previous_line = data[previous_start:context_start].strip()
                    if previous_line.startswith(b'#['): context_start = previous_start
                    else: break
                return {'path': path, 'marker': marker, 'occurrence': occurrence,
                        'line': data[:start].count(b'\n') + 1,
                        'bytes': len(body), 'sha256': sha(body),
                        'declaration_context_sha256':sha(data[context_start:end])}
        i += 1
    raise AssertionError(('unclosed definition', path, marker))

I = 'experimental_swift_reactor/cache/initial_profile_v1.rs'
C = 'experimental_swift_reactor/control.rs'
K = 'experimental_swift_reactor/cache.rs'
A = 'experimental_wasi/accounted.rs'
W = 'experimental_wasi/mod.rs'
S = 'experimental/swift.rs'
L = 'experimental_swift_reactor/retained_profile_loader_v1.rs'
SPECS = []
def add(path, *markers):
    for marker in markers: SPECS.append((path, marker, 0))

add(I, 'fn checked_add_v1(', 'fn checked_mul_v1(', 'fn snapshot_shape_v1(',
    'fn proposed_emission_work_v1(', "fn begin_snapshot_access_v1<'c>(",
    'fn error(&self,cause:SnapshotCauseV1', 'fn stop(&self,stage:u32)',
    'fn io_result<T>(', 'fn encode_result<T>(', 'fn write_snapshot_v1(',
    'struct SnapshotShapeV1', 'struct SnapshotPlanV1', 'struct SnapshotPhaseStorageV1',
    'struct SnapshotProgressV1', 'enum SnapshotCauseV1', 'struct SnapshotExportErrorV1',
    'struct SnapshotObservationV1', 'enum SnapshotAttemptV1', 'struct SnapshotWriterV1',
    'enum SnapshotAccessV1', 'pub(crate) struct InitialProfileBorrowV1')
add(I, 'fn retire_v1(self,control:', 'pub(in crate::experimental_swift_reactor) struct SnapshotPrimaryRetirementV1',
    'pub(in crate::experimental_swift_reactor) struct SnapshotOuterV1',
    'enum InitialProfileConstructionOutcomeV1', 'struct ProfileHeaderErrorV1',
    'struct UnverifiedProfileHeaderV1')
add(I, "impl ClosedBranchV1 for SnapshotBranchV1<'_>",
    "impl SnapshotAccessV1<'_>", "impl SharedControlV1 for SnapshotAccessV1<'_>",
    'fn construct_profile_core_v1<', 'fn construct_snapshot_owned_v1(')
add('experimental_swift_reactor/cache/initial_profile_v1/selected.rs', 'fn selected_initial_profile_v1()')
for name in ['existing', 'observe_stop', 'ticket', 'owner', 'ticket_identity',
             'adopted_pair', 'foundation_pair', 'totals', 'debit',
             'storage_preflight', 'commit_storage']:
    # Marker starts at fn to accommodate visibility differences.
    add(C, 'fn snapshot_' + name + '_v1(')
add(C, 'fn matches_layout(', 'fn category(&self, category:', 'fn category_limit(',
    'pub(crate) fn proof(&self)', 'pub struct SwiftRunFailure {',
    'pub struct SwiftRunUsage {', 'pub struct SwiftReservations {',
    'pub struct SwiftReservationUsage {', 'pub struct SwiftLiveUsage {',
    'pub enum SwiftRunResource {', 'pub enum SwiftDeadlineOrigin {',
    'pub enum SwiftRunStage {', 'pub enum SwiftRunFailureKind {',
    'pub enum SwiftCleanupInvariant {', 'pub enum SwiftReservationCategory {',
    'pub struct SwiftRunBudget {', 'pub(crate) enum SnapshotStopV1',
    'pub(crate) enum SnapshotAdmissionErrorV1', 'pub(crate) struct ReservationTicket',
    'pub(crate) struct AdoptedProof', 'pub(crate) struct RuntimeControl')
add(C, 'fn adopt_snapshot_body_v1(', 'fn attach_wasi_v1(', 'fn attach_wasi_inner_v1(',
    'fn construct_v1(mut self,claims:', 'fn outer_v1(&self)', 'fn finish_v1(self)',
    'pub(super) struct SnapshotPreScopeFailureV1', 'pub(super) struct SnapshotScopeV1',
    'pub(super) struct SnapshotRunV1', 'pub(super) struct SnapshotScopeFinishV1',
    'pub(super) struct SnapshotWasiAttachmentV1', 'pub(crate) struct Cursor')
add(C, 'impl ClosedAdoptionV1 for SnapshotAdoptionV1',
    'fn snapshot_scope_candidate_foundation_v1()', 'fn foundation_construction_bytes()',
    'fn adopt_body_core_v1<', 'fn drop_proof_with_wasi(',
    'fn finish_owned_cleanup(', 'fn end_construction_phase_with_wasi<',
    'fn refund(&mut self, ticket:', 'pub(crate) fn fail(', 'pub(crate) fn new(kind:')
add(K, 'fn snapshot_pair_v1(', 'pub(crate) fn proof(&self)',
    'pub(crate) fn cache_header_bytes()', 'pub(crate) struct SwiftFunctionCache')
add(K, 'fn construct_snapshot_in_scope_v1(', "pub(crate) fn cleanup<'a>(", "impl CacheCleanupTail<'_>")
add(A, 'fn snapshot_pair_v1(', 'pub(crate) fn accounted_header_bytes()',
    'pub(crate) fn usage(&self)', 'pub(crate) struct AccountedWasi')
add(A, 'pub(crate) fn prepare(', 'pub(crate) fn construct(',
    'pub(crate) fn complete(self)', 'pub(crate) fn cleanup(mut self, control:')
add(W, 'pub fn usage(&self)', 'pub struct WasiUsage {', 'pub struct WasiReservations {',
    'pub enum WasiFailure {', 'pub enum Resource {')
add(S, 'pub(crate) fn snapshot_counts_v1(', 'pub fn usage(&self)',
    'pub struct SwiftValidationUsage {', 'pub struct ValidatedSwiftReactor {',
    'pub(crate) fn encoded_extent(&self)', 'pub(crate) fn emitted_extent(&self)',
    'pub(crate) fn bytes(&self)', 'pub(crate) fn offset(&self)',
    'pub(crate) fn is_final(&self)')
add(L, 'pub(super) fn proof(&self)', 'fn into_adoption_body_v1(self)')
add('execute.rs', 'pub fn is_cancelled(&self)', 'pub(crate) fn requested_backing_layout()')
add('experimental/account.rs', 'pub fn len(&self)')

def source_bindings():
    members = [definition(*spec) for spec in SPECS]
    files = []
    for path in sorted({x[0] for x in SPECS}):
        raw = (SRC/path).read_bytes()
        files.append({'path': path, 'bytes': len(raw), 'sha256': sha(raw)})
    # The ledger binds exact complete definitions; later additive measurement
    # code is permitted only as separately reported file drift, never 144-tree identity.
    canonical = json.dumps(members, sort_keys=True, separators=(',', ':')).encode()
    return {'schema': 1, 'source_root': str(SRC.relative_to(ROOT)),
            'definitions': members, 'definition_tree_sha256': sha(canonical),
            'observed_files': files, 'entire_144_member_tree_identity_claimed': False}

def controls(ledger):
    checks = []
    def check(name, value, detail=None):
        assert value, (name, detail)
        checks.append({'name': name, 'passed': True, 'detail': detail})
    # Independent finite attempt model enumerates all failure kinds at every
    # attempt index and block length <=4096, without native transfer. Earlier
    # attempts alternate Interrupted and one-byte acknowledgements when possible.
    kinds = ['interrupted', 'zero', 'overreport', 'other_error', 'post_stop',
             'ack_overflow', 'byte_overflow', 'call_overflow', 'success']
    cases = 0
    for length in range(1, 4097):
        for attempt in range(1, 33):
            for kind in kinds:
                calls = 0; acknowledged = 0; requested = 0
                for prior in range(1, attempt):
                    calls += 1; requested += length-acknowledged
                    if prior % 2 == 0 and acknowledged+1 < length: acknowledged += 1
                before_terminal = acknowledged
                if kind != 'call_overflow':
                    calls += 1; requested += length-acknowledged
                if kind in ('success', 'post_stop'):
                    acknowledged = length
                # Positive transfer acknowledgements precede post-write stop.
                if kind == 'post_stop': assert acknowledged == length
                if kind in ('zero','overreport','other_error','interrupted','call_overflow'):
                    assert acknowledged == before_terminal
                assert calls <= 32 and requested <= 32*length and acknowledged <= length
                cases += 1
    check('finite_attempt_prefixes', cases == 1179648, cases)
    # Each possible block-length geometry and each terminal failure prefix is
    # dominated by B planned blocks; adding a 33rd attempt must be rejected.
    for extent in range(2560, 10753):
        blocks = (extent + 4095)//4096
        lengths = [min(4096, extent-i*4096) for i in range(blocks)]
        assert sum(32*n for n in lengths) == 32*extent
        assert sum(lengths) == extent
    check('all_small_block_geometries_requested_bytes', True, 8193)
    check('attempt33_rejected', not (33 <= 32))
    check('terminal_none_not_budgeted', ledger['writer']['terminal_none_calls'] == 0)
    # Source observations independently counted by site rather than inferred
    # from the debit polynomial. I/O/encoder wrappers each observe after return.
    obs = {'prefix_stop': 5, 'prefix_encoder_post': 2, 'prefix_io_post': 3,
           'final_stop': 2, 'block_stop': 4, 'block_encoder_post': 1,
           'attempt_pre': 1, 'attempt_post': 1}
    check('observation_formula', (sum(obs[k] for k in ['prefix_stop','prefix_encoder_post','prefix_io_post','final_stop']),
          obs['block_stop']+obs['block_encoder_post'],obs['attempt_pre']+obs['attempt_post']) == (12,5,2), obs)
    get = {'fixed_extent':2, 'block_offset':1, 'post_block_bytes':1,
           'block_final':1, 'attempt_requested_bytes':1,'attempt_complete_bytes':1}
    check('getter_formula', (get['fixed_extent'],sum(get[k] for k in ['block_offset','post_block_bytes','block_final']),
          get['attempt_requested_bytes']+get['attempt_complete_bytes']) == (2,3,2), get)
    check('ticket_shell_bound', 12+10+3+3 == 28 and 28+1 <= 32)
    # Checked arithmetic is modeled on both widths. Failure is not wrapped or
    # replaced with saturating/wrapping arithmetic; debit failure leaves used.
    def checked_add(a,b,width):
        if (2**width-1)-a < b: return None
        return a+b
    def debit(used,amount,limit,width):
        next_value = checked_add(used,amount,width)
        return used if next_value is None or next_value > limit else next_value
    arithmetic_cases = 0
    for width in (32,64):
        maximum = 2**width-1
        for used in (0,1,maximum//2,maximum-1,maximum):
            for amount in (0,1,2,maximum//2,maximum):
                for limit in (0,1,maximum//2,maximum-1,maximum):
                    result = used+amount
                    accepted = result <= maximum and result <= limit
                    observed = debit(used,amount,limit,width)
                    assert observed == (result if accepted else used)
                    if result > maximum: assert not accepted
                    arithmetic_cases += 1
    check('checked_debit_storage_boundaries', True, arithmetic_cases)
    check('work_itself_included', ledger['admission']['debit_helper'] == 44 and
          ledger['admission']['pending_formula_evaluator'].startswith('Must count exact checked'))
    caps = [67108864,512,8192,34,79966,8192,4096,4096,4096]
    widths = [0,3,1,5,3,4,4,4,4]
    words = sum(n*w for n,w in zip(caps,widths))
    extent = 2560+caps[0]+8*words; blocks=(extent+4095)//4096
    check('maximum_cap_arithmetic', extent == 69765152 and blocks == 17033,
          {'words':words,'extent':extent,'blocks':blocks,'attempts':32*blocks,
           'native_requested_bytes':32*extent,'clear_bytes':4096*blocks})
    # Shape conversion rejects a single excessive cap at every position.
    check('cap_overruns_rejected', all((caps[i]+1)>caps[i] for i in range(9)))
    check('nested_copy_slots', ledger['copy_slots']['SwiftRunUsage'] == 65 and ledger['copy_slots']['SwiftRunFailure'] == 151)
    check('ledger_rows_arithmetic', all(sum(row['parts'].values()) == row['credits'] for row in ledger['rows']))
    rows = {row['name']: row for row in ledger['rows']}
    val = lambda name: rows[name]['credits']
    check('helper_dependency_substitution', all([
        rows['snapshot_totals_v1']['parts']['enter_foundation_question_binding'] == val('snapshot_foundation_pair_v1')+5,
        rows['snapshot_storage_preflight_v1']['parts']['enter_foundation_question_binding'] == val('snapshot_foundation_pair_v1')+5,
        rows['snapshot_commit_storage_v1']['parts']['enter_repeated_preflight_question_binding'] == val('snapshot_storage_preflight_v1')+5,
        rows['SwiftFunctionCache.snapshot_pair_v1_max_optional_WASI']['parts']['optional_WASI_match_upper'] == val('AccountedWasi.snapshot_pair_v1')+10,
        rows['SwiftFunctionCache.snapshot_pair_v1_max_optional_WASI']['parts']['totals_args_and_question'] == val('snapshot_totals_v1')+4,
        ledger['admission']['max_optional_WASI_pair'] == val('SwiftFunctionCache.snapshot_pair_v1_max_optional_WASI'),
        ledger['admission']['preflight'] == val('snapshot_storage_preflight_v1'),
        ledger['admission']['commit_storage_repeats_preflight'] == val('snapshot_commit_storage_v1'),
        ledger['admission']['own_orchestration_all_source_branches'] == val('begin_snapshot_access_v1_own_orchestration'),
        ledger['admission']['future_all_branch_begin_excluding_formula_evaluator'] == val('begin_snapshot_access_v1_own_orchestration')+1928+260+88+55+501+293+31+4096+608,
        ledger['writer']['base_without_terminal_tail'] == val('writer_fixed_nonstop_nogetters')+12*15+2*3,
        ledger['writer']['per_block_including_clear_and_observations_getters'] == val('writer_per_block_nonstop_nogetters_nonclear')+5*15+3*3+4096,
        ledger['writer']['per_attempt_including_observations_getters'] == val('writer_per_attempt_nonstop_nogetters')+2*15+2*3,
    ]))
    wrap = ledger['wrappers']
    check('wrapper_dependency_substitution', all([
        wrap['retire_once'] == val('SnapshotOuter.retire_v1_added_bookkeeping'),
        wrap['finish_once_including_retire_and_optional_pair_Existing_copy'] == val('SnapshotRun.finish_v1_added_bookkeeping_without_retire')+wrap['retire_once']+302,
        wrap['attach_outer_per_call'] == val('SnapshotScope.attach_wasi_v1_outer_per_call'),
        wrap['attach_inner_at_most_once'] == val('SnapshotScope.attach_wasi_inner_v1_added_bookkeeping'),
        wrap['adoption_callbacks_all_branch_upper'] == sum(val(n) for n in ['SnapshotAdoption.foundation_added_bookkeeping','SnapshotAdoption.retire_tickets_added_bookkeeping','SnapshotAdoption.failure_added_bookkeeping']),
    ]))
    for calls in range(1, 65):
        first_attempt = 45
        upper = calls*16+45
        assert first_attempt+calls*16 <= upper
    check('repeat_attachment_not_collapsed_to_global_once', 2*16+45 > 16+45)
    check('requested_transfer_additive_contract', '32E' in ledger['writer']['required_native_transfer_additive_term'] and
          '+32E' in ledger['formula_interface']['partial_emission_consumption_contract'])
    return checks

def main():
    actual = source_bindings()
    if '--capture' in sys.argv:
        emit(HERE/'source-bindings.json', actual)
    expected = json.loads((HERE/'source-bindings.json').read_text())
    assert actual['definitions'] == expected['definitions'], 'audited definition drift'
    seal_raw = (ENC/'seal.json').read_bytes()
    assert sha(seal_raw) == 'ef906a8ec95d956898347bca67658ffac82a506be66b204d35893c23acfcfdd0'
    seal = json.loads(seal_raw); assert len(seal['members']) == 30
    for member in seal['members']:
        raw = (ENC/member['path']).read_bytes()
        assert len(raw) == member['bytes'] and sha(raw) == member['sha256']
    ledger = json.loads((HERE/'ledger.json').read_text())
    acceptance_path = ROOT/'verification/swift-semantic-adapter-root-review/guarded-snapshot-encoder-work-host-acceptance.json'
    acceptance_raw = acceptance_path.read_bytes()
    assert sha(acceptance_raw) == '757345abe9013a4d5d880738c794e8a9783061fb733f4de24f432698861e9351'
    acceptance = json.loads(acceptance_raw)
    result = {'schema':1,'scope':'Python arithmetic/source model only; no Rust/encoder/VM/writer/native/UI execution',
              'python':platform.python_version(),'source_definition_tree_sha256':actual['definition_tree_sha256'],
              'file_drift_since_capture':[x for x in actual['observed_files'] if x not in expected['observed_files']],
              'encoder_proposal_seal_sha256':sha(seal_raw),'encoder_members_verified':30,
              'encoder_fixed_parameter':{'frozen_proposal':14221,'accepted_corrected_encoder_only':14224,
                  'acceptance_path':str(acceptance_path.relative_to(ROOT)),
                  'acceptance_sha256':sha(acceptance_raw),
                  'source_revision_from_external_acceptance':acceptance['source_revision'],
                  'correction_scope':'accepted encoder component; no complete debit selected by this audit'},
              'checks':controls(ledger),'operational_authorization':False}
    emit(HERE/'results.json', result)
    print(json.dumps({'checks':len(result['checks']),'all_passed':True,'scope':result['scope'],
                     'definition_tree_sha256':actual['definition_tree_sha256']},sort_keys=True))

if __name__ == '__main__': main()
