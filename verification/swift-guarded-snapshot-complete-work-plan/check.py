#!/usr/bin/env python3
"""Own-folder-only source binding and arithmetic proposal; no product execution."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FROZEN = ROOT / 'verification/swift-guarded-snapshot-scope-authority-correction'
OLD = ROOT / 'verification/swift-initial-profile-construction-implementation'
SRC = FROZEN / 'source/vm/src'
OSRC = OLD / 'source/vm/src'
CONTROL = 'experimental_swift_reactor/control.rs'
CACHE = 'experimental_swift_reactor/cache.rs'
INITIAL = 'experimental_swift_reactor/cache/initial_profile_v1.rs'
LOCAL = 'experimental_swift_reactor/cache/initial_profile_v1/local_structure.rs'
TREE = '575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896'
CEILING = 1_000_000_000
MAX64 = (1 << 64) - 1


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def definition(text: str, marker: str, occurrence: int = 0) -> bytes:
    """Balanced lexical body extraction for hashing, never release authorization."""
    pos = -1
    for _ in range(occurrence + 1):
        pos = text.index(marker, pos + 1)
    start = text.rfind('\n', 0, pos) + 1
    opening = text.index('{', pos)
    level = 0
    i = opening
    while i < len(text):
        if text.startswith('//', i):
            i = text.index('\n', i)
            continue
        if text.startswith('/*', i):
            end = text.index('*/', i + 2)
            i = end + 2
            continue
        if text[i] == '"':
            i += 1
            while i < len(text):
                if text[i] == '\\':
                    i += 2
                elif text[i] == '"':
                    i += 1
                    break
                else:
                    i += 1
            continue
        if text[i] == '{':
            level += 1
        elif text[i] == '}':
            level -= 1
            if level == 0:
                return text[start:i + 1].encode()
        i += 1
    raise AssertionError(marker)


def checked_sum(*values: int) -> int:
    out = 0
    for value in values:
        if not isinstance(value, int) or value < 0 or value > MAX64:
            raise OverflowError('invalid u64 input')
        out += value
        if out > MAX64:
            raise OverflowError('u64 addition')
    return out


def checked_mul(a: int, b: int) -> int:
    checked_sum(a, b)
    out = a * b
    if out > MAX64:
        raise OverflowError('u64 multiplication')
    return out


def emission(extent: int, blocks: int) -> int:
    return checked_sum(19537, checked_mul(299377, blocks), checked_mul(32, extent))


def quote(ingress: int, setup: int, wasi_finish: int, attached: bool,
          extent: int, blocks: int, dispatch_delta: int) -> int:
    # Incoming prices are explicit interfaces to the other source ledger,
    # not an authorized product API accepting caller-defined scalar permits.
    return checked_sum(451703621, ingress,
                       checked_sum(setup, wasi_finish) if attached else 0,
                       dispatch_delta, 16384, emission(extent, blocks))


def make():
    checks = 0
    bindings = []
    def require(value):
        nonlocal checks
        assert value
        checks += 1
    def file_binding(path: Path):
        b = path.read_bytes()
        return {'path': str(path.relative_to(ROOT)), 'bytes': len(b), 'sha256': sha(b)}
    manifest = json.loads((FROZEN / 'source-manifest.json').read_text())
    require(manifest['source_tree_sha256'] == TREE)
    require(len(manifest['members']) == 144)
    for member in manifest['members']:
        data = (FROZEN / 'source/vm' / member['path']).read_bytes()
        require(len(data) == member['bytes'] and sha(data) == member['sha256'])
    def compare_file(rel: str, prefix: bool = False):
        a, b = (OSRC / rel).read_bytes(), (SRC / rel).read_bytes()
        if prefix:
            require(b.startswith(a.rstrip(b'\n')))
            span = b[:len(a.rstrip(b'\n'))]
            require(span == a.rstrip(b'\n'))
        else:
            require(a == b)
        bindings.append({'kind': 'unchanged-old-prefix' if prefix else 'unchanged-file',
                         'old': file_binding(OSRC / rel), 'frozen': file_binding(SRC / rel)})
    for rel in ['experimental_swift_reactor/diagnostic_profile.rs',
                'experimental_swift_reactor/cache/initial_profile_v1/header.rs']:
        compare_file(rel)
    compare_file(CACHE, True)
    compare_file('experimental_wasi/accounted.rs', True)
    for rel, markers in [(CONTROL, ['fn check_budget(', 'fn check_with_wasi(', 'fn fail(',
                                    'fn category_limit(', 'fn preflight_bytes(', 'fn commit_bytes(',
                                    'fn admit(', 'fn admit_with_wasi(',
                                    'fn end_construction_phase_with_wasi<T>(',
                                    'fn refund_with_wasi(', 'fn finish_owned_cleanup(']),
                         (INITIAL, ['fn profile_error(', 'fn compare_budget_v1(',
                                    'fn inspect_initial_v1(', 'fn write_initial_profile_rows_v1('])]:
        a, b = (OSRC / rel).read_text(), (SRC / rel).read_text()
        for marker in markers:
            old, frozen = definition(a, marker), definition(b, marker)
            require(old == frozen)
            bindings.append({'kind': 'unchanged-definition', 'source_relative': rel,
                             'marker': marker, 'bytes': len(frozen), 'sha256': sha(frozen)})
    a, b = (OSRC / CONTROL).read_text(), (SRC / CONTROL).read_text()
    old_drop = definition(a, 'fn drop_proof_with_wasi(')
    new_drop = definition(b, 'fn drop_proof_with_wasi(')
    require(old_drop.replace(b'proof,', b'body,').replace(b'drop(proof)', b'drop(body)') == new_drop)
    bindings.append({'kind': 'owned-drop-rename-same-action-shape',
                     'source_relative': CONTROL, 'old_sha256': sha(old_drop), 'frozen_sha256': sha(new_drop)})
    initial = (SRC / INITIAL).read_text()
    inspect = definition(initial, 'fn inspect_initial_v1(').decode()
    bridge = definition(initial, 'fn write_initial_profile_rows_v1(').decode()
    constructor = definition((SRC / CACHE).read_text(), 'fn construct_partial(').decode()
    require(inspect.count('cache.proof()') == 3)
    require(bridge.count('initial.cache.proof()') == 1)
    require(constructor.count('.proof()') == 1)
    getter_old = definition(a, 'fn proof(&self)')
    getter_new = definition(b, 'fn proof(&self)')
    require(b'&self.proof' in getter_old and b'self.body.proof()' in getter_new)
    bindings.append({'kind': 'proof-delegation-delta3-times5', 'source_relative': CONTROL,
                     'old_sha256': sha(getter_old), 'frozen_sha256': sha(getter_new)})
    local_old, local_new = (OSRC / LOCAL).read_text(), (SRC / LOCAL).read_text()
    old_prefix = local_old[:local_old.rindex(' Ok(())')].replace('selected.entries!=165', 'selected.entries!=201')
    require(local_new.startswith(old_prefix))
    require('ADOPTION_LAYOUTS_V1.iter().enumerate()' in local_new)
    require('selected.type_layout[165+index]' in local_new)
    require('entries!=201' in local_new)
    loader = (SRC / 'experimental_swift_reactor/retained_profile_loader_v1.rs').read_text()
    require('ADOPTION_LAYOUTS_V1:[(&str,usize,usize);36]' in loader.replace(' ', ''))
    bindings.append({'kind': 'layout-tail-delta', 'old': file_binding(OSRC / LOCAL),
                     'frozen': file_binding(SRC / LOCAL), 'added_entries': 36})
    require('Err(AError::WorkAuditPending)' in initial)
    require('control.end_construction_phase_with_wasi(storage,previous,wasi)' in initial)
    require('planning=16384u64' in initial)
    require('execution_work:1000000000' in (SRC / 'experimental_swift_reactor/cache/initial_profile_v1/selected.rs').read_text())
    require('combined_bytes:268435456' in (SRC / 'experimental_swift_reactor/cache/initial_profile_v1/selected.rs').read_text())
    old_actions = json.loads((OLD / 'accounting.json').read_text())
    rows = old_actions['source_action_terms']
    require(sum(row['total'] for row in rows) == 521088)
    require(old_actions['accepted_row_source_actions_plus_requested_IO'] == 450652288)
    wrapper = {'construct_scope_and_forward': 40, 'core_guard': 15, 'branch_early': 7,
               'branch_begin': 2, 'branch_export': 13, 'refused_export_copy': 306,
               'branch_finish_with_access_complete': 14, 'run_finish_with_retire': 1247,
               'outer_observation_once': 3}
    require(sum(wrapper.values()) == 1647)
    layout_delta = 36 * 128 + 4 + 8
    require(layout_delta == 4620)
    require(6 + 7 + 18 + 4 <= 128)
    fixed = 450652288 + 521088 + layout_delta + 5 * 3 + sum(wrapper.values()) + 4 + 521088 + 2871
    require(fixed == 451703621)
    require(7930 + 2 + 29 == 7961)
    require(7961 - 2871 - 4096 == 994)
    require(16384 - 994 == 15390)
    require(3435 - 3 + 2 + 29 == 3463)
    require(emission(2560, 1) == 400834)
    require(emission(69765152, 17033) == 7331792842)
    require(quote(0, 0, 0, False, 2560, 1, 0) == 452120839)
    require(quote(0, 0, 0, False, 69765152, 17033, 0) > CEILING)
    for attached in (False, True):
        for price in (0, 1, 29, 1647, 521088):
            q = quote(price, price, price, attached, 2560, 1, 0)
            require(q == 452120839 + price * (3 if attached else 1))
    base = quote(0, 0, 0, False, 2560, 1, 0)
    room = CEILING - base
    require(quote(room, 0, 0, False, 2560, 1, 0) == CEILING)
    require(quote(room + 1, 0, 0, False, 2560, 1, 0) == CEILING + 1)
    for args in [(MAX64, 0, 0, False, 2560, 1, 0), (0, MAX64, 1, True, 2560, 1, 0),
                 (0, 0, 0, False, MAX64, 1, 0), (0, 0, 0, False, 2560, MAX64, 0),
                 (0, 0, 0, False, 2560, 1, MAX64), (-1, 0, 0, False, 2560, 1, 0)]:
        try:
            quote(*args)
        except OverflowError:
            checks += 1
        else:
            raise AssertionError('overflow accepted')
    # Pure admission-order obligations. This is a source-model control, not a
    # fake product writer, owner fixture, clock or VM execution.
    def admitted_trace(events):
        paid_prefix = paid_planning = paid_emission = committed = False
        initialized = completed = False
        for event in events:
            if event == 'prefix':
                if paid_prefix: return False
                paid_prefix = True
            elif event in ('ingress', 'authority', 'begin_shell'):
                if not paid_prefix: return False
            elif event == 'planning_debit':
                if not paid_prefix or paid_planning: return False
                paid_planning = True
            elif event in ('counts_shape', 'evaluator31'):
                if not paid_planning: return False
            elif event == 'emission_debit':
                if not paid_planning or paid_emission: return False
                paid_emission = True
            elif event == 'storage_commit':
                if not paid_emission or committed: return False
                committed = True
            elif event == 'initializer4096':
                if not paid_emission or not committed or initialized: return False
                initialized = True
            elif event == 'writer':
                if not initialized: return False
            elif event == 'complete':
                if not initialized or completed: return False
                completed = True
            elif event == 'finish':
                if not completed: return False
            else:
                raise AssertionError(event)
        return completed
    trace = ['prefix', 'ingress', 'authority', 'begin_shell', 'planning_debit',
             'counts_shape', 'evaluator31', 'emission_debit', 'storage_commit',
             'initializer4096', 'writer', 'complete', 'finish']
    require(admitted_trace(trace))
    for missing in ('prefix', 'planning_debit', 'emission_debit', 'storage_commit', 'complete'):
        require(not admitted_trace([e for e in trace if e != missing]))
    require(not admitted_trace(trace[:10] + ['initializer4096'] + trace[10:]))
    require(not admitted_trace(['evaluator31'] + trace))
    require(not admitted_trace(['authority'] + trace))
    # The pending implementation must preserve nonterminal export refusal,
    # primary progress and the independent end-phase result; a work quote may
    # not mutate first_failure or reclassify conservative ConstructionBound.
    source_begin = definition(initial, "fn begin_snapshot_access_v1<'c>(").decode()
    require('control.fail(' not in source_begin)
    require(source_begin.index('snapshot_debit_v1(planning)') < source_begin.index('proposed_emission_work_v1(&shape)'))
    require(source_begin.index('snapshot_debit_v1(emission)') < source_begin.index('transfer:Some([0;4096])'))
    inputs = ['verification/swift-semantic-adapter-root-review/guarded-snapshot-writer-work-host-acceptance.json',
              'verification/swift-semantic-adapter-root-review/guarded-snapshot-encoder-work-host-acceptance.json',
              'verification/swift-semantic-adapter-root-review/guarded-snapshot-authority-work-host-acceptance.json',
              'verification/swift-semantic-adapter-root-review/guarded-snapshot-emission-bound-host-acceptance.json',
              'verification/swift-semantic-adapter-root-review/guarded-snapshot-emission-storage-host-acceptance.json',
              'verification/swift-semantic-adapter-root-review/initial-profile-component-acceptance.json',
              'verification/swift-initial-profile-construction-independent/actual-review/abstract-action-reconciliation.json',
              'verification/swift-initial-profile-construction-implementation/accounting.json',
              'verification/swift-guarded-snapshot-scope-authority-correction/source-manifest.json',
              'verification/swift-guarded-snapshot-scope-authority-correction/seal.json']
    ledger = {'schema': 1, 'status': 'separable-source-action-proposal-not-dispatch-acceptance',
              'source_tree_sha256': TREE, 'fixed_prepaid_portion': fixed,
              'wrapper_rows': wrapper, 'original_added_rows': rows,
              'original_row_source_and_requested_IO': 450652288,
              'extra_snapshot_completion_envelope': 521088,
              'layout_tail_delta': {'entries': 36, 'per_entry_reused_upper': 128,
                                    'expanded_row_subbound': {'iteration_and_pattern': 6, 'entry_index_borrow_binding': 7,
                                                             'four_field_comparisons_and_conversions': 18, 'or_and_if': 4},
                                    'loop_and_iter_events': 4, 'one_refusal_tail': 8, 'total': layout_delta},
              'proof_delta': {'per_delegate': 3, 'constructor': 1, 'inspect': 3, 'row_bridge': 1, 'total': 15},
              'constructor_selected_static_getter_and_reference': 4,
              'begin_shell': 2871, 'planning': 16384,
              'evaluator': {'old_refusal': 3, 'wrapper': 2, 'helper': 29, 'integrated': 31, 'replacement_delta': 28},
              'begin': {'before_evaluator_integration': 7930, 'after': 7961, 'prepaid_shell': 2871,
                        'post_first_debit_excluding_initializer': 994, 'initializer_in_emission_once': 4096, 'planning_slack': 15390},
              'incoming_ledger_interface': ['W_ingress', 'W_setup', 'W_wasi_finish'],
              'incoming_final_amendment': 'Exact final quote/bootstrap dispatch source-action delta and places; source-selected, not runtime caller-settable',
              'quote': '451703621 + W_ingress + attached*(W_setup+W_wasi_finish) + dispatch_delta + 16384 + 19537 + 299377B + 32E',
              'minimum_without_incoming_prices': 452120839, 'work_ceiling': CEILING,
              'storage_C_S_A_H': 'pending; no floor/grant selection',
              'source_only_checks_passed': checks, 'writer_runtime_executed': False, 'GA_gates_verified': 0}
    return {'input-bindings.json': {'schema': 1, 'source_tree_sha256': TREE,
                                    'inputs': [file_binding(ROOT / p) for p in inputs], 'source_rebindings': bindings},
            'ledger.json': ledger}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    outputs = make()
    for name, obj in outputs.items():
        data = (json.dumps(obj, indent=2, sort_keys=True) + '\n').encode()
        path = HERE / name
        if args.verify:
            assert path.read_bytes() == data, name
        else:
            path.write_bytes(data)
    print(json.dumps({'checks_passed': outputs['ledger.json']['source_only_checks_passed'],
                      'mode': 'verify' if args.verify else 'generate',
                      'fixed_prepaid_portion': outputs['ledger.json']['fixed_prepaid_portion'],
                      'complete_work_accepted': False, 'writer_runtime_executed': False}, sort_keys=True))


if __name__ == '__main__':
    main()
