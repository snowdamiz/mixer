#!/usr/bin/env python3
"""Independent finite proposal review; never imports a product or frozen runner."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PLAN = ROOT / 'verification/swift-guarded-snapshot-complete-work-plan'
CORRECTION = ROOT / 'verification/swift-guarded-snapshot-work-quote-arithmetic-correction'
INGRESS = ROOT / 'verification/swift-guarded-snapshot-ingress-work'
AUTHORITY = ROOT / 'verification/swift-guarded-snapshot-scope-authority-correction'
OLD = ROOT / 'verification/swift-initial-profile-construction-implementation'
TREE = '575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896'
MAX = (1 << 64) - 1
LIMIT = 1_000_000_000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def binding(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)}


def body(text, marker, occurrence=0):
    """Lexical fingerprint extraction only, never permission for runtime use."""
    start = -1
    for _ in range(occurrence + 1):
        start = text.index(marker, start + 1)
    marker_start = start
    start = text.rfind('\n', 0, start) + 1
    opening = text.index('{', marker_start)
    position, depth = opening, 0
    while position < len(text):
        if text.startswith('//', position):
            position = text.index('\n', position)
            continue
        if text.startswith('/*', position):
            position = text.index('*/', position + 2) + 2
            continue
        if text[position] == '"':
            position += 1
            while text[position] != '"':
                position += 2 if text[position] == '\\' else 1
            position += 1
            continue
        if text[position] == '{':
            depth += 1
        elif text[position] == '}':
            depth -= 1
            if depth == 0:
                return text[start:position + 1].encode()
        position += 1
    raise AssertionError(marker)


def arithmetic(path):
    parsed = ast.parse(path.read_text())
    functions = [n for n in parsed.body if isinstance(n, ast.FunctionDef)
                 and n.name in {'checked_sum', 'checked_mul', 'emission', 'quote'}]
    assert len(functions) == 4
    namespace = {'MAX64': MAX}
    # Only these four pure arithmetic bodies execute, not an imported module.
    exec(compile(ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[])),
                 str(path) + ':four-arithmetic-bodies-only', 'exec'), namespace)
    return {n.name: n for n in functions}, namespace


def outcome(function, *args):
    try:
        return ('value', function(*args))
    except (OverflowError, TypeError) as error:
        return (type(error).__name__, str(error))


def valid_trace(events, attached):
    """Finite integration-contract model, not an executable product writer."""
    counts = Counter(events)
    once = ['bootstrap', 'prefix', 'ingress', 'construct', 'outer', 'finish']
    if any(counts[name] != 1 for name in once):
        return False
    if counts['attach'] != int(attached):
        return False
    if any(events.index(left) >= events.index(right) for left, right in
           [('bootstrap', 'prefix'), ('prefix', 'ingress'), ('ingress', 'construct'),
            ('construct', 'outer'), ('outer', 'finish')]):
        return False
    if attached and not events.index('ingress') < events.index('attach') < events.index('construct'):
        return False
    admitted = counts['initializer'] == 1
    if admitted:
        paid = ['shell', 'planning', 'shape', 'evaluator', 'emission', 'commit', 'initializer', 'writer', 'complete']
        if any(counts[name] != 1 for name in paid):
            return False
        chain = ['construct'] + paid + ['outer']
        if any(events.index(left) >= events.index(right) for left, right in zip(chain, chain[1:])):
            return False
    elif any(counts[name] for name in ['emission', 'commit', 'writer', 'complete']):
        return False
    return not (set(events) - set(once + ['attach', 'shell', 'planning', 'shape', 'evaluator',
                                      'emission', 'commit', 'initializer', 'writer', 'complete']))


def run():
    groups = Counter()
    inputs = []
    def require(condition, group):
        assert condition, group
        groups[group] += 1
    seals = [(PLAN, '7198ae0748ce0c8c576afc953aef8f3827b0a0d925ea246225245ba4cf000a27', 5, 47303),
             (CORRECTION, 'c7400a6c214ca45c9c169e59238d5788685a88fdae15d1a72217661e222a9a8a', 5, 14731),
             (INGRESS, '75775a7df0048888ab95b40d58831d22e05ea2e3935781904e9a83b57f556561', 15, 189135)]
    for folder, expected, count, size in seals:
        seal_path = folder / 'seal.json'
        require(sha(seal_path.read_bytes()) == expected, 'frozen_packet_custody')
        sealed = json.loads(seal_path.read_text())
        require((sealed['member_count'], sealed['member_bytes']) == (count, size), 'frozen_packet_custody')
        for member in sealed['members']:
            data = (folder / member['path']).read_bytes()
            require((len(data), sha(data)) == (member['bytes'], member['sha256']), 'frozen_packet_custody')
        inputs.append(binding(seal_path))
    release = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-full-work-independent-release.json'
    require(sha(release.read_bytes()) == '36e39ad6f7c9ba674d5327adfd155084bce529bf00c5dc61e03485de9adddeb4', 'frozen_packet_custody')
    inputs.append(binding(release))
    ingress_release = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-ingress-work-independent-release.json'
    require(sha(ingress_release.read_bytes()) == '0902c3ab4f721b615398034ee789b72a4d6b1b6f56d3c4d8830d6296725d073e', 'frozen_packet_custody')
    inputs.append(binding(ingress_release))
    rebindings = json.loads((PLAN / 'input-bindings.json').read_text())
    for member in rebindings['inputs']:
        path = ROOT / member['path']
        require(binding(path) == member, 'inherited_binding')
        inputs.append(binding(path))
    manifest = json.loads((AUTHORITY / 'source-manifest.json').read_text())
    require(manifest['source_tree_sha256'] == TREE and len(manifest['members']) == 144, 'source144_custody')
    require(sha(json.dumps(manifest['members'], sort_keys=True, separators=(',', ':')).encode()) == TREE, 'source144_custody')
    for member in manifest['members']:
        data = (AUTHORITY / 'source/vm' / member['path']).read_bytes()
        require((len(data), sha(data)) == (member['bytes'], member['sha256']), 'source144_custody')
    src, old = AUTHORITY / 'source/vm/src', OLD / 'source/vm/src'
    for member in rebindings['source_rebindings']:
        kind = member['kind']
        if kind in ['unchanged-file', 'unchanged-old-prefix', 'layout-tail-delta']:
            for name in ['old', 'frozen']:
                require(binding(ROOT / member[name]['path']) == member[name], 'inherited_binding')
            a = (ROOT / member['old']['path']).read_bytes()
            b = (ROOT / member['frozen']['path']).read_bytes()
            if kind == 'unchanged-file':
                require(a == b, 'inherited_binding')
            elif kind == 'unchanged-old-prefix':
                require(b.startswith(a.rstrip(b'\n')), 'inherited_binding')
        elif kind == 'unchanged-definition':
            a = body((old / member['source_relative']).read_text(), member['marker'])
            b = body((src / member['source_relative']).read_text(), member['marker'])
            require(a == b and len(b) == member['bytes'] and sha(b) == member['sha256'], 'inherited_binding')
    control = (src / 'experimental_swift_reactor/control.rs').read_text()
    cache = (src / 'experimental_swift_reactor/cache.rs').read_text()
    initial = (src / 'experimental_swift_reactor/cache/initial_profile_v1.rs').read_text()
    local_old = (old / 'experimental_swift_reactor/cache/initial_profile_v1/local_structure.rs').read_text()
    local_new = (src / 'experimental_swift_reactor/cache/initial_profile_v1/local_structure.rs').read_text()
    for marker in ['fn cleanup_fault_with_wasi(', 'fn usage(', 'fn record_cleanup(']:
        require(body(control, marker) == body((old / 'experimental_swift_reactor/control.rs').read_text(), marker), 'completion_envelope_binding')
    old_drop = body((old / 'experimental_swift_reactor/control.rs').read_text(), 'fn drop_proof_with_wasi(')
    require(old_drop.replace(b'proof,', b'body,').replace(b'drop(proof)', b'drop(body)') == body(control, 'fn drop_proof_with_wasi('), 'inherited_binding')
    require(body(initial, 'fn inspect_initial_v1(').count(b'cache.proof()') == 3, 'proof_layout_delta')
    require(body(initial, 'fn write_initial_profile_rows_v1(').count(b'initial.cache.proof()') == 1, 'proof_layout_delta')
    require(body(cache, 'fn construct_partial(').count(b'.proof()') == 1, 'proof_layout_delta')
    require(b'self.body.proof()' in body(control, 'fn proof(&self)'), 'proof_layout_delta')
    require(local_new.startswith(local_old[:local_old.rindex(' Ok(())')].replace('selected.entries!=165', 'selected.entries!=201')), 'proof_layout_delta')
    require('ADOPTION_LAYOUTS_V1.iter().enumerate()' in local_new and 'selected.type_layout[165+index]' in local_new, 'proof_layout_delta')
    loader = (src / 'experimental_swift_reactor/retained_profile_loader_v1.rs').read_text()
    require('ADOPTION_LAYOUTS_V1:[(&str,usize,usize);36]' in loader.replace(' ', ''), 'proof_layout_delta')
    require('word(b, 32) != 144' in loader and 'word(b, 40) != 11' in loader, 'descriptor_requires_new_qualification')
    descriptor_accepts = lambda source_count, support_count: source_count == 144 and support_count == 11
    require(descriptor_accepts(144, 11), 'descriptor_requires_new_qualification')
    require(not descriptor_accepts(145, 11), 'descriptor_requires_new_qualification')
    require(not descriptor_accepts(144, 12), 'descriptor_requires_new_qualification')
    require(body(cache, 'fn allocate_owner(') == body((old / 'experimental_swift_reactor/cache.rs').read_text(), 'fn allocate_owner('), 'unchanged_atomic_unit')
    require('try_update' in body(cache, 'fn allocate_owner(').decode(), 'unchanged_atomic_unit')
    require('try_update' in control, 'unchanged_atomic_unit')

    ingress_ledger = json.loads((INGRESS / 'ledger.json').read_text())
    require(ingress_ledger['source_tree_sha256'] == TREE and ingress_ledger['source_members'] == 144, 'ingress_source_custody')
    require(len(ingress_ledger['source_bindings']) == 64 and len(ingress_ledger['loop_bindings']) == 11, 'ingress_source_custody')
    for member in ingress_ledger['inputs']:
        require(binding(ROOT / member['path']) == member, 'ingress_source_custody')
    for group in ['source_bindings', 'loop_bindings']:
        for member in ingress_ledger[group].values():
            text = (AUTHORITY / 'source/vm' / member['path']).read_text()
            if 'marker' in member:
                fragment = body(text, member['marker'], member['occurrence']).decode()
                fragment = fragment[fragment.index(member['marker']):]
            else:
                fragment = member['source']
                require(fragment in text, 'ingress_source_custody')
            encoded = fragment.encode()
            require(fragment == member['source'] and len(encoded) == member['bytes'] and sha(encoded) == member['sha256'], 'ingress_source_custody')
    ingress_rows = ingress_ledger['rows']
    require(len(ingress_rows) == 64, 'ingress_DAG')
    def expanded(rows, name, active=()):
        assert name not in active
        row = rows[name]
        assert all(type(n) is int and n >= 0 for n in list(row['parts'].values()) + list(row['calls'].values()))
        return sum(row['parts'].values()) + sum(count * expanded(rows, child, active + (name,)) for child, count in row['calls'].items())
    for name, row in ingress_rows.items():
        require(row['binding'] in ingress_ledger['source_bindings'], 'ingress_DAG')
        require(sum(row['parts'].values()) == row['own_actions'], 'ingress_DAG')
        require(expanded(ingress_rows, name) == row['expanded_actions'], 'ingress_DAG')
    incoming = {'W_ingress': 33613, 'W_setup': 68781, 'W_wasi_finish': 7155}
    roots = {'W_ingress': 'selected_into_scope', 'W_setup': 'attach', 'W_wasi_finish': 'wasi_cleanup'}
    for name, root in roots.items():
        require(expanded(ingress_rows, root) == ingress_ledger['exports'][name] == incoming[name], 'ingress_exports')
    require(sum(incoming.values()) == 109549, 'ingress_exports')
    multiplicities = [('adopt_core', 'admit', 5), ('adopt_core', 'check', 2),
                      ('adopt_core', 'snapshot_retire', 1), ('adopt_core', 'finish_owned_cleanup', 1),
                      ('snapshot_retire', 'refund', 2), ('attach', 'attach_inner', 1),
                      ('attach_inner', 'prepare', 1), ('attach_inner', 'wasi_construct', 1),
                      ('attach_inner', 'wasi_complete', 1), ('wasi_construct', 'admit', 5),
                      ('wasi_construct', 'partial_cleanup', 1), ('partial_cleanup', 'drop_reserved', 5),
                      ('wasi_cleanup', 'drop_reserved_with_wasi', 5)]
    for row, child, count in multiplicities:
        require(ingress_rows[row]['calls'][child] == count, 'ingress_multiplicity')
        mutant = copy.deepcopy(ingress_rows)
        mutant[row]['calls'][child] -= 1
        require(any(expanded(mutant, root) != incoming[name] for name, root in roots.items()), 'ingress_call_omission_negative')
    for row, part in [('usage', 'forty_nine_borrowed_leaf_fetch_store_pairs'),
                      ('fail', 'Existing_borrowed_Copy_151_leaves'),
                      ('adopt_core', 'closed_owner_callback_enter_return_checked_add'),
                      ('wasi_construct', 'iovec_array_sixty_four_Span_fetch_store_pair_upper'),
                      ('wasi_construct', 'four_loop_tuple_advance_bind'),
                      ('accounted_construction_bytes', 'thirteen_question_inspect_propagations'),
                      ('wasi_cleanup', 'four_buffer_index_bounds_receiver_take_pattern_decision')]:
        mutant = copy.deepcopy(ingress_rows)
        mutant[row]['parts'].pop(part)
        require(any(expanded(mutant, root) != incoming[name] for name, root in roots.items()), 'ingress_part_omission_negative')
    expected_loops = {'budget17': 17, 'capacity4': 4, 'cleanup4': 4, 'cleanup_header1': 1,
                      'construct4': 4, 'construction13': 13, 'finish3': 3, 'iovec64': 64,
                      'partial4': 4, 'partial_option4': 4, 'partial_vec4': 4}
    for name, maximum in expected_loops.items():
        require(ingress_ledger['loop_bindings'][name]['max_iterations'] == maximum, 'ingress_loop_bounds')
    require(ingress_rows['attach']['own_actions'] + ingress_rows['attach_inner']['own_actions'] == 61, 'no_wrapper_double_join')
    require(ingress_rows['snapshot_foundation_callback']['expanded_actions'] == 19, 'no_unapplied_constcopy_discount')
    require(ingress_rows['snapshot_foundation']['expanded_actions'] == 17 and ingress_rows['accounted_construction_bytes']['expanded_actions'] == 176 and ingress_rows['accounted_header_bytes']['expanded_actions'] == 22, 'no_unapplied_constcopy_discount')

    ledger = json.loads((PLAN / 'ledger.json').read_text())
    rows = json.loads((OLD / 'accounting.json').read_text())['source_action_terms']
    require(ledger['original_added_rows'] == rows and len(rows) == 11, 'fixed_and_split')
    require(sum(row['total'] for row in rows) == 521088, 'fixed_and_split')
    require(ledger['original_row_source_and_requested_IO'] == 450652288, 'fixed_and_split')
    require(sum(ledger['wrapper_rows'].values()) == 1647, 'fixed_and_split')
    require(ledger['wrapper_rows']['construct_scope_and_forward'] == 21 + 19, 'fixed_and_split')
    require(ledger['wrapper_rows']['run_finish_with_retire'] == 813 + 132 + 302, 'fixed_and_split')
    fixed_terms = [450652288, 521088, 521088, 36 * 128 + 4 + 8, 5 * 3, 1647, 4, 2871]
    require(sum(fixed_terms) == ledger['fixed_prepaid_portion'] == 451703621, 'fixed_and_split')
    for index in range(len(fixed_terms)):
        require(sum(fixed_terms[:index] + fixed_terms[index + 1:]) != ledger['fixed_prepaid_portion'], 'omitted_term_negative')
    require(7930 + 31 == 7961 == 2871 + 994 + 4096, 'fixed_and_split')
    require(7930 + 28 != 7961 and 3435 - 3 + 31 == 3463, 'fixed_and_split')
    require(994 <= 16384 and 16384 - 994 == 15390, 'fixed_and_split')
    require(14224 + 1217 + 4096 == 19537, 'fixed_and_split')
    require(291214 + 4259 + 122 * 32 == 299377, 'fixed_and_split')
    require(19537 + 299377 + 32 * 2560 == 400834, 'fixed_and_split')

    ast_old, old_arithmetic = arithmetic(PLAN / 'check.py')
    ast_new, corrected = arithmetic(CORRECTION / 'quote.py')
    for name in ['checked_sum', 'emission', 'quote']:
        require(ast.dump(ast_old[name], include_attributes=False) == ast.dump(ast_new[name], include_attributes=False), 'arithmetic_correction')
    require(outcome(old_arithmetic['checked_mul'], MAX, 1) == ('OverflowError', 'u64 addition'), 'arithmetic_correction')
    require(outcome(corrected['checked_mul'], MAX, 1) == ('value', MAX), 'arithmetic_correction')
    operands = [0, 1, 2, 3, (1 << 32) - 1, 1 << 32, MAX // 2, MAX // 2 + 1, MAX - 1, MAX, -1, MAX + 1, None, 1.0, True, False]
    for a in operands:
        for b in operands:
            expected = ('OverflowError', 'invalid u64 input') if any(not isinstance(x, int) or not 0 <= x <= MAX for x in [a, b]) else (('value', a * b) if a * b <= MAX else ('OverflowError', 'u64 multiplication'))
            require(outcome(corrected['checked_mul'], a, b) == expected, 'independent_mul_grid')
    argspec = ast_new['quote'].args
    require(not argspec.defaults and len(argspec.args) == 7, 'explicit_incoming_interface')
    for args in [(), (0,), (0, 0), (0, 0, 0)]:
        require(outcome(corrected['quote'], *args)[0] == 'TypeError', 'explicit_incoming_interface')
    quote = corrected['quote']
    def independent(ingress, setup, finish, attached, extent, blocks, dispatch):
        return 451703621 + ingress + int(attached) * (setup + finish) + dispatch + 16384 + 19537 + 299377 * blocks + 32 * extent
    for attached in [False, True]:
        for extent in [2560, 4095, 4096, 4097, 69765152]:
            blocks = (extent + 4095) // 4096
            for prices in [(0, 0, 0, 0), (1, 3, 7, 11), (33613, 68781, 7155, 0)]:
                argv = (*prices[:3], attached, extent, blocks, prices[3])
                require(quote(*argv) == independent(*argv), 'independent_quote_values')
    baseline = quote(0, 0, 0, True, 2560, 1, 0)
    require(baseline == 452120839 and quote(0, 0, 0, False, 69765152, 17033, 0) == 7783512847, 'independent_quote_values')
    require(quote(33613, 68781, 7155, False, 2560, 1, 0) == 452154452, 'joined_quote_values')
    require(quote(33613, 68781, 7155, True, 2560, 1, 0) == 452230388, 'joined_quote_values')
    # The quote produces a checked u64; selection separately checks used+quote<=1B.
    for field in [0, 1, 2, 6]:
        for used in [0, 1, 3919]:
            argv = [0, 0, 0, True, 2560, 1, 0]
            argv[field] = LIMIT - baseline - used
            require(used + quote(*argv) == LIMIT, 'limit_equality_plus_one')
            argv[field] += 1
            require(used + quote(*argv) == LIMIT + 1, 'limit_equality_plus_one')
        argv = [0, 0, 0, True, 2560, 1, 0]
        argv[field] = MAX
        require(outcome(quote, *argv)[0] == 'OverflowError', 'join_overflow')
    for field in [4, 5]:
        argv = [0, 0, 0, True, 2560, 1, 0]
        argv[field] = MAX
        require(outcome(quote, *argv)[0] == 'OverflowError', 'join_overflow')
    for attached in [False, True]:
        events = ['bootstrap', 'prefix', 'ingress'] + (['attach'] if attached else []) + ['construct', 'shell', 'planning', 'shape', 'evaluator', 'emission', 'commit', 'initializer', 'writer', 'complete', 'outer', 'finish']
        require(valid_trace(events, attached), 'stage_multiplicity')
        for position in range(len(events)):
            require(not valid_trace(events[:position] + events[position + 1:], attached), 'stage_missing_negative')
            require(not valid_trace(events[:position] + [events[position]] + events[position:], attached), 'stage_repeat_negative')
        for position in range(len(events) - 1):
            moved = events.copy()
            moved[position], moved[position + 1] = moved[position + 1], moved[position]
            require(not valid_trace(moved, attached), 'stage_order_negative')
    begin = body(initial, "fn begin_snapshot_access_v1<'c>(").decode()
    complete = body(initial, 'fn complete(self,storage:SnapshotPhaseStorageV1)').decode()
    core = body(initial, 'fn construct_profile_core_v1<').decode()
    retire = body(initial, 'fn retire_v1(self,control:').decode()
    finish = body(control, 'fn finish_v1(self)').decode()
    require(begin.index('snapshot_debit_v1(planning)') < begin.index('snapshot_shape_v1') < begin.index('proposed_emission_work_v1') < begin.index('snapshot_debit_v1(emission)') < begin.index('snapshot_commit_storage_v1') < begin.index('transfer:Some([0;4096])'), 'funding_source_order')
    require('control.fail(' not in begin and 'Err(AError::WorkAuditPending)' in initial, 'failure_retention')
    require('control.end_construction_phase_with_wasi(storage,previous,wasi)' in complete and 'drop(storage);Ok(())' in complete, 'failure_retention')
    require('let phase_completion=access.complete(storage);' in initial and 'SnapshotOuterV1 {primary,export,phase_completion}' in initial, 'failure_retention')
    require(core.index('branch.export(') < core.index('encode_profile_header_v1') < core.index('write_initial_profile_rows_v1') < core.index('branch.finish('), 'failure_retention')
    variants = ['SlotOccupied', 'SelectionRefused', 'PreparationFailed', 'ConstructionFailed', 'PhaseCompletionFailed', 'HeaderRefused', 'HeaderOwnerCheckFailed', 'HeaderEncoded']
    for variant in variants:
        require(retire.count('InitialProfileConstructionOutcomeV1::' + variant) == 1, 'eight_primary_routes')
    require('failure.rejected_adopted' in retire and 'Some(completion)' in retire, 'failure_retention')
    require('let adopted=self.adopted.take().expect("one-shot actual adopted owner")' in control, 'once_only_ownership')
    require('match adopted{Some(adopted)=>control.drop_proof_with_wasi(adopted,observation),None=>Ok(())}' in finish, 'once_only_ownership')
    require(finish.count('control.finish_owned_cleanup(observation)') == 1 and finish.count('wasi.cleanup(&mut control)') == 1, 'once_only_ownership')
    require('Some(ticket.bytes) != foundation_construction_bytes()' in body(control, 'fn finish_owned_cleanup(').decode(), 'conservative_cleanup')
    require('ConstructionBound' in body(control, 'fn finish_owned_cleanup(').decode(), 'conservative_cleanup')
    require('execution_work:1000000000' in (src / 'experimental_swift_reactor/cache/initial_profile_v1/selected.rs').read_text(), 'unchanged_ceiling')
    for folder, _, _, _ in seals:
        for member in json.loads((folder / 'seal.json').read_text())['members']:
            require(sha((folder / member['path']).read_bytes()) == member['sha256'], 'postflight_frozen_custody')
    return {'schema': 1, 'status': 'bounded-logical-work-plan-and-numeric-join-review-pass',
            'source_tree_sha256': TREE, 'source_members_verified': 144,
            'controls_passed': sum(groups.values()), 'groups': dict(sorted(groups.items())),
            'inputs': inputs, 'fixed_prefix': 451703621,
            'begin_split': {'total': 7961, 'shell': 2871, 'planning_region': 994, 'initializer_emission_once': 4096},
            'incoming_prices': incoming, 'incoming_maximum_join': 109549,
            'minimum_quote_no_WASI_excluding_dispatch_delta': 452154452,
            'minimum_quote_with_WASI_excluding_dispatch_delta': 452230388,
            'material_findings': [], 'ingress_read': True,
            'complete_work_admission_or_runtime_accepted': False,
            'source_check_limit': 'Lexical fingerprints and review preserve provenance but do not authorize release or runtime execution',
            'executed': 'Only independent Python finite controls and four extracted pure arithmetic functions',
            'pending': ['Final source-derived bootstrap/dispatch amendment delta',
                        'Exact final-source compilation/privacy/consume/borrow evidence after implementation',
                        'Source145/support roster genuine descriptor qualification if a file is added',
                        'Complete storage/lifetime selection', 'Writer dispatch', 'Native/device and GA qualification']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    arguments = parser.parse_args()
    result = run()
    data = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    path = HERE / 'results.json'
    if arguments.verify:
        assert path.read_bytes() == data
    else:
        path.write_bytes(data)
    print(json.dumps({k: result[k] for k in ['status', 'controls_passed', 'source_members_verified', 'material_findings', 'ingress_read', 'complete_work_admission_or_runtime_accepted']}, sort_keys=True))


if __name__ == '__main__':
    main()
