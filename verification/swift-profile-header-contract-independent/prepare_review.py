#!/usr/bin/env python3
"""Capture reviewed source excerpts and synthetic cases; never run product code."""
from pathlib import Path
import ast
import copy
import hashlib
import json
import controls as M

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
PREP = P.parent / 'swift-profile-header-preparation'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def source_witness(name, relative, begin, end):
    raw = (PREP / relative).read_bytes()
    text = raw.decode()
    start = text.index(begin)
    finish = text.index(end, start) + len(end)
    excerpt = text[start:finish]
    return {'id': name, 'producer_relative_path': relative,
            'full_source_bytes': len(raw), 'full_source_sha256': sha(raw),
            'first_line': text.count('\n', 0, start) + 1,
            'last_line': text.count('\n', 0, finish) + 1,
            'excerpt_sha256': sha(excerpt.encode()), 'excerpt': excerpt,
            'scope': 'Read-only source witness; no compiled semantic/ownership or release proof'}


def main():
    inputs = []
    # Live plan/instructions are context only; frozen producer sources are authority.
    # Preserve exact bytes consulted for subsequent root coordination without edits.
    names = ['AGENTS.md', 'mixer-product-plan.md', 'PLAN.md',
             'verification/swift-semantic-adapter-root-review/profile-header-preparation-custody.json',
             'verification/swift-semantic-adapter-root-review/profile-adapter-acceptance.json']
    for name in names:
        raw = (ROOT / name).read_bytes()
        q = P / 'context-inputs' / name
        q.parent.mkdir(parents=True, exist_ok=True)
        assert not q.exists(), 'prepare is one-time; do not overwrite snapshots'
        q.write_bytes(raw)
        inputs.append({'path': name, 'snapshot': str(q.relative_to(P)),
                       'bytes': len(raw), 'sha256': sha(raw)})
    producer_seal = (PREP / 'seal.json').read_bytes()
    inputs.append({'path': 'verification/swift-profile-header-preparation/seal.json',
                   'bytes': len(producer_seal), 'sha256': sha(producer_seal),
                   'scope': 'Retained external frozen packet; all200 members verified by audit_inputs.py'})
    dump(P / 'input-custody.json', {'schema': 1, 'inputs': inputs,
                                  'producer_remains_external_hash_bound_unchanged': True})
    cache = 'inputs/vm/src/experimental_swift_reactor/cache.rs'
    control = 'inputs/vm/src/experimental_swift_reactor/control.rs'
    wasi = 'inputs/vm/src/experimental_wasi/accounted.rs'
    generic = 'inputs/vm/src/experimental/cache/borrowed.rs'
    row = 'inputs/verification/swift-cache-state-profile-adapter/source/vm/src/experimental_swift_reactor/diagnostic_profile.rs'
    specifications = [
        ('cache-fields', cache, 'pub(crate) struct SwiftFunctionCache {', '    header: Option<ReservationTicket>,\n}'),
        ('common-control-optional-pairing', cache, 'fn pairing(', '    wasi.map(|w| w.checked_usage(control, cursor)).transpose()\n}'),
        ('cache-header-owner-preflight', cache, '    fn check_header(', '            .check_reservation_owner(header, self.cursor, self.observation())\n    }'),
        ('cache-proof-and-owner-borrow', cache, '    pub(crate) fn proof(&self)', '        .check_header(self)\n    }'),
        ('constructor-initial-fields', cache, 'impl CacheConstructionPhase<\'_> {', '    fn construct_partial('),
        ('constructor-exact-loops-reservations', cache, '    fn construct_partial(', '    pub(crate) fn complete<T>('),
        ('local-H-formula', cache, 'const fn compute_cache_header_bytes()', 'const fn compute_cache_construction_bytes()'),
        ('budget-definition-maxima', control, 'pub struct SwiftRunBudget {', '#[derive(Clone, Copy, Debug, PartialEq, Eq)]\npub enum SwiftReservationCategory'),
        ('category-byte-vs-global-ticket-inventory', control, 'pub struct SwiftReservationUsage {', 'impl SwiftReservations {'),
        ('safe-zero-byte-admission', control, '    pub(crate) fn admit_with_wasi(', '    /// Aggregate locals/instructions/targets'),
        ('runtime-owner-not-historical-instance', control, '    pub(crate) fn reservation_owner_matches(', '    /// Cleanup-independent validation'),
        ('first-failure-and-live-check', control, '    pub(crate) fn check_with_wasi(', '    fn category_limit('),
        ('optional-WASI-owner-check', wasi, '    pub(crate) fn checked_usage(', '    pub(crate) fn stdout('),
        ('WASI-prepare-no-global-once-marker', wasi, '    pub(crate) fn prepare(', '    pub(crate) fn usage('),
        ('failed-imported-acquire-before-mutation', generic, 'pub(crate) fn pin<M: CacheMode>(', 'pub(crate) struct CacheFields'),
        ('unchanged-row-File-admission', row, 'fn admit_output(', 'fn with_progress('),
        ('row-accepts-independent-snapshot', row, 'pub(crate) fn write_profile_row_body_v1(', '#[cfg(test)]'),
    ]
    witnesses = [source_witness(*args) for args in specifications]
    dump(P / 'source-witnesses.json', {'schema': 1, 'scope': 'Frozen primary source facts only', 'witnesses': witnesses})

    base = M.model()
    cases = []
    q = copy.deepcopy(base); q['wasi_instance'] = 'wasi-B'
    cases.append({'id': 'R2-same-control-different-WASI', 'source': ['common-control-optional-pairing', 'optional-WASI-owner-check', 'cache-fields'],
                  'inputs': {'control_owner': 17, 'cache_ticket_owner': 17, 'supplied_WASI_ticket_owner': 17,
                             'construction_WASI_instance': 'wasi-A', 'supplied_WASI_instance': 'wasi-B'},
                  'existing_common_owner_projection_passes': M.common_owner_preflight_projection(q),
                  'historically_identical': q['wasi_instance'] == q['construction_wasi_instance']})
    q = copy.deepcopy(base); q['wasi_instance'] = q['wasi_owner'] = None
    cases.append({'id': 'R2-Some-to-None', 'source': ['common-control-optional-pairing'],
                  'inputs': {'construction_WASI_instance': 'wasi-A', 'supplied_WASI_instance': None},
                  'existing_common_owner_projection_passes': M.common_owner_preflight_projection(q),
                  'historically_identical': False})
    q = copy.deepcopy(base); q['cache_work'] += 1; q['cache_attempts'] = 1; q['first_failure'] = 'not_defined_function'
    cases.append({'id': 'R3-imported-index-failed-acquisition', 'source': ['failed-imported-acquire-before-mutation', 'cache-header-owner-preflight', 'first-failure-and-live-check'],
                  'inputs': {'absolute_function': 0, 'imported_functions': 34, 'slots': 2, 'pins': 3,
                             'work_before': base['cache_work'], 'work_after': q['cache_work'],
                             'first_failure_after': q['first_failure'], 'nonce_after': q['nonce']},
                  'stated_cache_shape_before': M.stated_cache_shape(base),
                  'stated_cache_shape_after': M.stated_cache_shape(q),
                  'existing_common_owner_projection_passes_after': M.common_owner_preflight_projection(q),
                  'B_equality_after': M.reservation_projection(q),
                  'encoded_header_before_equals_after': M.modeled_header(base, [bytes(32)] * 8) == M.modeled_header(q, [bytes(32)] * 8),
                  'before_first_attempt_after': False})
    q = copy.deepcopy(base); q['unrelated_zero_cache_tickets'] = 1
    cases.append({'id': 'R4-unrelated-zero-byte-Cache-ticket', 'source': ['safe-zero-byte-admission', 'category-byte-vs-global-ticket-inventory'],
                  'inputs': {'admission_category': 'Cache', 'admission_bytes': 0, 'B': base['cache_base'],
                             'cache_current_before': base['cache_current'], 'cache_current_after': q['cache_current'],
                             'global_live_ticket_delta': 1},
                  'B_equality_after': M.reservation_projection(q), 'no_unrelated_ticket_after': False})
    q = copy.deepcopy(base); q['external_build_attestation'] = 'different external claim'
    cases.append({'id': 'R1-same-structure-different-build-claim', 'source': ['local-H-formula'],
                  'inputs': {'all_layout_numbers': 'arbitrary arithmetic witnesses, never measured ABI',
                             'local_shape_equal': base['same_build_shape'] == q['same_build_shape'],
                             'external_claim_A': base['external_build_attestation'], 'external_claim_B': q['external_build_attestation']},
                  'modeled_headers_equal': M.modeled_header(base, [bytes(32)] * 8) == M.modeled_header(q, [bytes(32)] * 8),
                  'external_identity_established': False})
    q = copy.deepcopy(base); q['snapshot_owner_identity'] = 'sealed-owner-B'
    cases.append({'id': 'R5-independent-row-snapshot', 'source': ['row-accepts-independent-snapshot', 'cache-proof-and-owner-borrow'],
                  'inputs': {'cache_guard_proof': base['snapshot_owner_identity'], 'independent_row_snapshot': q['snapshot_owner_identity'],
                             'source_body_bytes_may_be_equal': True},
                  'modeled_headers_equal': M.modeled_header(base, [bytes(32)] * 8) == M.modeled_header(q, [bytes(32)] * 8),
                  'same_actual_owner_established': False})
    q = copy.deepcopy(base); q['budget']['frames'] -= 1
    cases.append({'id': 'all17-omitted-field-header-collision', 'source': ['budget-definition-maxima'],
                  'inputs': {'changed_field': 'frames', 'selected_value': 64, 'actual_value': 63},
                  'modeled_headers_equal': M.modeled_header(base, [bytes(32)] * 8) == M.modeled_header(q, [bytes(32)] * 8),
                  'complete_budget_equality': M.budgets_match(q['budget'], base['selected'])})
    a = copy.deepcopy(base); a['defined'] = 1; a['slots'] = [(None, 0, 0)]; a['slots_len'] = a['slots_cap'] = 1
    q = copy.deepcopy(a); q['budget']['cache_entries'] = 64
    cases.append({'id': 'all17-min-slots-hides-raw-entries-difference', 'source': ['constructor-exact-loops-reservations'],
                  'inputs': {'defined': 1, 'selected_cache_entries': 2, 'actual_cache_entries': 64, 'both_actual_slots': 1},
                  'modeled_headers_equal': M.modeled_header(a, [bytes(32)] * 8) == M.modeled_header(q, [bytes(32)] * 8),
                  'complete_budget_equality': M.budgets_match(q['budget'], a['selected'])})
    dump(P / 'counterexamples.json', {'schema': 1,
                                    'scope': 'Synthetic information-loss witnesses tied to frozen source; no actual Rust execution or authority',
                                    'cases': cases, 'all_real_authority_flags': False})
    parsed = ast.parse((P / 'controls.py').read_bytes())
    names = sorted(n.name for cls in parsed.body if isinstance(cls, ast.ClassDef)
                   for n in cls.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_'))
    assert len(names) == 48 and len(set(names)) == 48
    dump(P / 'test-roster.json', {'schema': 1, 'method_count': 48, 'methods': names,
                                'scope': 'Offline review controls only; no Rust/native tests'})
    print(json.dumps({'context_snapshots': len(inputs) - 1, 'source_witnesses': len(witnesses),
                      'counterexamples': len(cases), 'offline_methods': len(names)}))


if __name__ == '__main__':
    main()
