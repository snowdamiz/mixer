#!/usr/bin/env python3
"""Audit retained direct observations and attach only bounded finite execution joins."""
from pathlib import Path
import copy
import datetime
import hashlib
import json

D = Path(__file__).resolve().parent
RUN = D / 'run-1'
CONTEXT = '1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'
LEDGER_ID = 'dev/mixer/android/NativeRenderer#rememberV2(Ljava/lang/Throwable;)V'
CONSTRUCTOR_ID = 'dev/mixer/android/NativeRenderer$PreservationMembership#<init>(Ldev/mixer/android/NativeRenderer$NativeState;Ldev/mixer/android/NativeAppearanceViewsV2$FieldPreservation;)V'


def identity(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(name, value):
    (D / name).write_text(json.dumps(value, indent=2) + '\n')


def main():
    assert not (D / 'seal.json').exists(), 'closed packet is immutable'
    original = json.loads((D / 'inputs/original-two-subjects.json').read_bytes())
    prepared = json.loads((D / 'inputs/original-two-semantic-proposals.json').read_bytes())
    results = json.loads((RUN / 'actual-results.json').read_bytes())
    rows = results['rows']
    snapshots = json.loads((RUN / 'snapshots.json').read_bytes())['snapshots']
    expected_count = {LEDGER_ID: 32, CONSTRUCTOR_ID: 9}
    assert len(rows) == 41 and len(snapshots) == 82
    assert results['source_context'] == CONTEXT
    assert not (RUN / 'failure.json').exists()
    assert results['original_edit_completed_after_finally_restores']
    assert results['original_boundary_counts'] == [2, 2, 3] and results['original_final_counts'] == [0, 0, 0]
    assert results['fixture_close_returned'] and results['fixture_close_catches_product_failures']
    assert results['constructor_additional_default_fields'] == []
    class_map = json.loads((D / 'inputs/selected-product-class-map.json').read_bytes())
    assert len(class_map) == 209 and json.loads((RUN / 'actual-product-class-map.json').read_bytes()) == class_map
    for name, expected in class_map.items():
        assert identity(RUN / 'classes' / name) == expected
    for row in rows:
        before = snapshots[row['snapshot_before_index']]
        after = snapshots[row['snapshot_after_index']]
        for phase, snapshot in [('before', before), ('after', after)]:
            raw = json.dumps(snapshot, separators=(',', ':'), ensure_ascii=False).encode()
            assert hashlib.sha256(raw).hexdigest() == row['snapshot_' + phase + '_sha256']
        assert row['actual_after'] == row['literal_expected_after']
        assert row['counts_before'] == row['counts_after'] == before['counts'] == after['counts'] == [2, 2, 3]
        assert row['native_effects'] == 0 and row['native_events_before'] == row['native_events_after'] == len(before['native_event_prefix'])
        assert before['native_event_prefix'] == after['native_event_prefix']
        assert before['containers'] == after['containers'] and before['throwable_diagnostics'] == after['throwable_diagnostics']
        bf, af = dict(before['fields']), dict(after['fields'])
        pkey = 'renderer.ledger/dev.mixer.android.NativeRenderer$CleanupLedger#primary'
        fkey = 'renderer.ledger/dev.mixer.android.NativeRenderer$CleanupLedger#firstFatal'
        assert row['actual_typed_outcome']['exception'] is None
        if row['subject_id'] == LEDGER_ID:
            assert row['actual_typed_outcome'] == {'kind': 'void', 'jvm_return_descriptor': 'V', 'reflection_return': None, 'exception': None}
            assert bf[pkey] == row['ledger_before']['primary'] and bf[fkey] == row['ledger_before']['firstFatal']
            assert af[pkey] == row['actual_after']['primary'] and af[fkey] == row['actual_after']['firstFatal']
            del bf[pkey], bf[fkey], af[pkey], af[fkey]
        else:
            assert row['subject_id'] == CONSTRUCTOR_ID
            assert row['actual_typed_outcome']['kind'] == 'constructed-reference'
            assert row['actual_typed_outcome']['reflection_return_class'] == 'dev.mixer.android.NativeRenderer$PreservationMembership'
            assert row['literal_arguments'] == {k: row['actual_after'][k] for k in ['state', 'scope']}
            assert row['actual_after']['fresh_identity'] and row['additional_instance_default_fields'] == []
            assert not row['membership_or_release_authority_inferred'] and not row['allocation_failure_qualified']
        assert bf == af
    constructors = [row for row in rows if row['subject_id'] == CONSTRUCTOR_ID]
    assert len({row['actual_typed_outcome']['constructed_reference'] for row in constructors}) == 9
    assert {(row['literal_arguments']['state'] is None, row['literal_arguments']['scope'] is None) for row in constructors} == {(True, True), (True, False), (False, True), (False, False)}
    commands = json.loads((RUN / 'commands.json').read_bytes())
    assert len(commands) == 4 and all(command['reaped'] and not command['timeout'] and command['exit'] == 0 and command['timeout_seconds'] <= 60 for command in commands)
    compiler = next(command for command in commands if command['name'] == 'compile')['argv']
    assert compiler[1:6] == ['--release', '17', '-proc:none', '-Xlint:all', '-Werror']
    assert not any(argument.startswith('-g') for argument in compiler)
    cleanup = json.loads((RUN / 'cleanup.json').read_bytes())
    assert cleanup['all_started_children_bounded_and_reaped'] and cleanup['owned_compile_scratch_removed'] and cleanup['leased_JDK_preserved']

    def join(subject, indices):
        return {'source_context': CONTEXT, 'subject_id': subject['id'], 'class_sha256': subject['class_sha256'],
            'results': {'path': 'run-1/actual-results.json', **identity(RUN / 'actual-results.json')},
            'snapshots': {'path': 'run-1/snapshots.json', **identity(RUN / 'snapshots.json')},
            'boundary': {'path': 'run-1/boundary.json', **identity(RUN / 'boundary.json')},
            'control_source': {'path': 'FiniteRendererLedgerConstructorControls.java', **identity(D / 'FiniteRendererLedgerConstructorControls.java')},
            'row_indices_zero_based': indices, 'independent_java_reference_identity_checks': True,
            'enclosing_obligations_accepted': False, 'native_callback_matrix_accepted': False}

    subjects, semantic_subjects = [], []
    for source in original['subjects']:
        indices = [index for index, row in enumerate(rows) if row['subject_id'] == source['id']]
        assert len(indices) == expected_count[source['id']]
        assert all(rows[index]['class_sha256'] == source['class_sha256'] for index in indices)
        selected = copy.deepcopy(source)
        cases = []
        for case in source['required_semantic_cases']:
            # These joins cover only finite identity/reference storage facets. The
            # complete original case always retains its pending enclosing scope.
            eligible = source['id'] == LEDGER_ID and case in {'ordinary-primary-preserved', 'first-fatal-exact-identity'}
            eligible = eligible or (source['id'] == CONSTRUCTOR_ID and case in {'ordered-constructor-bound-membership', 'original-transaction-or-presentation-identities'})
            cases.append({'original_case_id': case, 'status': 'pending-enclosing-or-runtime-obligation',
                'original_case_accepted': False,
                'finite_facet': ('literal first primary/first Error reference retention only' if source['id'] == LEDGER_ID else 'exact two constructor-supplied references only; no registration/admission authority') if eligible else None,
                'finite_execution_join': join(source, indices) if eligible else None})
        selected['finite_control_extension'] = {
            'status': 'finite-direct-host-Java-observed-root-selection-pending', 'independent_invocations': len(indices),
            'finite_execution_join': join(source, indices), 'original_subject_or_case_accepted': False,
            'original_case_dispositions': cases,
            'limitations': ['Every original enclosing count/cleanup/fatal propagation/reentrant/admission/allocation-failure case remains pending.',
                'No own native callback matrix or helper return behavior is inferred from scalar Java bodies.',
                'Private ledger seeds establish field independence only, without enclosing lifecycle reachability.',
                'Constructor success/freshness under ordinary allocation does not qualify allocation failure or grant membership authority.']}
        assert {k: v for k, v in selected.items() if k != 'finite_control_extension'} == source
        subjects.append(selected)
        old = next(subject for subject in prepared['subjects'] if subject['id'] == source['id'])
        current = copy.deepcopy(old)
        for case in current['required_cases']:
            if case['id'] == 'renderer-finite-source-invariants':
                case['execution_join'] = join(source, indices)
                case['status'] = 'finite-host-observed-root-selection-pending'
                case['pending_reason'] = 'Bounded direct Java identity/storage observations only; independent root selection and final selected producer execution remain pending.'
            else:
                assert case['execution_join'] is None
                case['status'] = 'pending-enclosing-original-control'
        assert current['original_categories'] == source['categories']
        assert current['original_required_case_ids'] == source['required_semantic_cases']
        semantic_subjects.append(current)
    save('proposal.json', {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'two-finite-Java-body-proposal-root-policy-selection-pending', 'source_context': CONTEXT,
        'source_revision_context': '6450104dc3b02d0f4d4e572c6b05ad7fdc6657b2',
        'original_full280_checklist': original['complete280_checklist'], 'original24_semantic_proposal': prepared['original24_proposal'],
        'original_subject_count': 280, 'original_ids_categories_case_names_and_metadata_preserved': True,
        'subjects': subjects, 'selected_prepared_semantic_subjects': semantic_subjects,
        'all_original_enclosing_cases_pending': True, 'complete_matrix_policy_canonical_native_OTA_GA_accepted': False,
        'generator': identity(Path(__file__)), 'command': ['python3', '-B', 'verification/android-renderer-finite-ledger-constructor/prepare_proposal.py']})
    save('validation.json', {'status': 'passed-retained-artifact-audit', 'direct_invocations': 41,
        'all_82_snapshot_digests_recomputed': True, 'all_non_target_fields_containers_diagnostics_event_prefixes_equal': True,
        'all_209_product_class_hashes_reverified': True, 'constructor_all_four_null_combinations_and_nine_fresh_references': True,
        'exact_original_subjects_categories_case_names_and_metadata_retained': True,
        'original_enclosing_and_allocation_failure_cases_accepted': False,
        'commands_bounded_terminal_reaped_and_scratch_removed': True,
        'scope': 'Artifact consistency audit only; not a second independent runtime execution'})
    save('manifest.json', {'schema': 1, 'status': 'two-finite-host-Java-controls-root-selection-pending',
        'selected_run': 'run-1', 'invocations': 41, 'checks': results['checks'], 'per_subject': expected_count,
        'checks_explanation': '60,537 bounded field/container/identity/event-prefix checks across 41 direct calls, not that many semantic cases or callback states.',
        'control': {'path': 'FiniteRendererLedgerConstructorControls.java', **identity(D / 'FiniteRendererLedgerConstructorControls.java')},
        'selected_exact_control_copy_matches': identity(D / 'FiniteRendererLedgerConstructorControls.java') == identity(RUN / 'FiniteRendererLedgerConstructorControls.java'),
        'source_context': CONTEXT, 'all_209_exact_product_classes_reproduced': True,
        'original_boundary': {'counts': [2, 2, 3], 'path': 'run-1/boundary.json', **identity(RUN / 'boundary.json')},
        'original_final_counts': [0, 0, 0], 'original_edit_completed_after_finally_restores': True,
        'results': {'path': 'run-1/actual-results.json', **identity(RUN / 'actual-results.json')},
        'snapshots': {'path': 'run-1/snapshots.json', **identity(RUN / 'snapshots.json')},
        'every_selected_direct_call_zero_native_effects': True,
        'retained_authoring_preflight_failure': 'authoring-preflight-failure.json',
        'test_authoring_failures': [], 'original_cases_all_pending': True,
        'canonical_native_OTA_GA_accepted': False})
    print('PASS artifact audit: 41 rows, 82 snapshots, 209 exact product classes; original cases remain pending.')


if __name__ == '__main__':
    main()
