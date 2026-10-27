#!/usr/bin/env python3
"""Bind the finite control output to preserved original IDs without granting release authority."""
from pathlib import Path
import hashlib
import json

D = Path(__file__).resolve().parent
CONTEXT = '1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'

def identity(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

def main():
    source = json.loads((D / 'inputs/original-three-subjects.json').read_bytes())
    result_path = D / 'run-3/actual-ledger-results.json'
    result = json.loads(result_path.read_bytes())
    receipt = json.loads((D / 'run-3/receipt.json').read_bytes())
    assert receipt['source_context'] == CONTEXT
    controls = (D / 'FiniteLedgerControls.java').read_text().splitlines()
    invoke_line = next(i for i, text in enumerate(controls, 1) if 'Object result=method.invoke' in text)
    control_map = json.loads((D / 'run-3/actual-product-class-map.json').read_bytes())
    subjects = []
    for original in source['subjects']:
        sid = original['id']
        rows = [(index, row) for index, row in enumerate(result['rows']) if row['subject_id'] == sid]
        assert len(rows) == 29
        observer = '$Observer#' in sid
        product = D / 'inputs/product' / original['source_file']
        assert identity(product)['sha256'] == original['source_sha256']
        assert control_map[original['class'] + '.class']['sha256'] == original['class_sha256']
        body_lines = product.read_text().splitlines()
        start = next(i for i, text in enumerate(body_lines, 1) if 'private void remember(Throwable failure)' in text)
        witness = [{'line': i, 'text': body_lines[i - 1]} for i in range(start, start + 5)]
        def join(selected):
            assert selected
            return {'status': 'fresh-own-finite-control-passed-independent-root-selection-pending',
                    'source_context': CONTEXT, 'subject_id': sid, 'subject_class_sha256': original['class_sha256'],
                    'test_source': 'FiniteLedgerControls.java', 'test_source_identity': identity(D / 'FiniteLedgerControls.java'),
                    'test_entry': {'class': 'dev/mixer/android/FiniteLedgerControls', 'method': 'main', 'descriptor': '([Ljava/lang/String;)V'},
                    'exact_invocation': {'line': invoke_line, 'text': controls[invoke_line - 1],
                        'selection': 'getDeclaredMethod("remember", Throwable.class) on exact ordinary subject runtime class; private void descriptor checked'},
                    'results': {'path': 'run-3/actual-ledger-results.json', **identity(result_path), 'zero_based_row_indexes': [i for i, _ in selected]},
                    'actual_rows': [{'index': i, 'sequence': row['sequence'], 'step': row['step'], 'input': row['input'],
                                    'primary_before': row['primary_before'], 'first_fatal_before': row['first_fatal_before'],
                                    'primary': row['primary'], 'first_fatal': row['first_fatal'],
                                    'diagnostics_before': row['diagnostics_before'], 'diagnostics_after': row['diagnostics_after']} for i, row in selected],
                    'final_selected_producer_reexecution_join': None,
                    'final_join_pending_reason': 'These are newly executed own finite host-JVM controls. Final producer integration and independent root policy selection remain explicit separate obligations.'}
        common = {'typed_result': 'Void normal return for null, checked Throwable/Exception, RuntimeException, and Error input. remember itself does not rethrow or wrap any input.',
            'identity_relations': 'primary and first Error are checked with Java == against independent literal sequence oracle arrays; distinct value-equal marker exceptions prevent equals-based identity credit.',
            'count_gate_cleanup_fatal_requirements': 'All non-ledger target fields, all other ledger fields, diagnostic array contents and held local state are unchanged. No concrete B leaf event, bridge effect, sink/event delivery or added suppression occurs during the selected method invocation. Actual enclosing cleanup/refusal/propagation remains pending.'}
        null_oracle = dict(common)
        null_oracle['state_transition'] = ('Every call clears diagnosticsAttached, including null when already true. Null retains primaryFailure/fatalFailure; the independent primary field can remain null after null input.' if observer else 'Null returns before reading/writing ledger and leaves all inspected state unchanged. No diagnosticsAttached field exists on this subject.')
        primary_oracle = dict(common)
        primary_oracle['state_transition'] = 'The first non-null input becomes primary exactly, whether ordinary or Error; a later ordinary/checked/Error input never replaces that exact reference.'
        fatal_oracle = dict(common)
        fatal_oracle['state_transition'] = 'The first Error becomes firstFatal/fatalFailure exactly, independently of ordinary primary; repeated distinct Errors and ordinary inputs preserve that first Error. An explicitly retained Error with null primary is preserved while a later ordinary input first fills primary.'
        unchanged_oracle = dict(common)
        unchanged_oracle['state_transition'] = ('diagnosticsAttached=false is the only scalar diagnostic change. cleanup[8], cleanupFailures[8], pending/acquiring and all other fields retain their before state.' if observer else 'Only ledger.primary and ledger.firstFatal can change. Held outcomes/failure references, object references, counters/flags and other fields retain their before state.')
        cases = [
            {'id': 'ledger-null-exact-source-behavior', 'kind': 'finite-ledger-state-and-identity',
             'required_states': ['null-empty', 'null-after-primary', 'null-after-primary-and-fatal', 'diagnostics-true-and-false-if-present'],
             'oracle': null_oracle, 'execution_join': join([(i, row) for i, row in rows if row['input'] == 'null'])},
            {'id': 'ledger-primary-exact-identity', 'kind': 'finite-ledger-state-and-identity',
             'required_states': ['first-ordinary', 'later-distinct-ordinary', 'ordinary-then-Error', 'Error-then-ordinary', 'checked-Throwable-and-Exception'],
             'oracle': primary_oracle, 'execution_join': join(rows)},
            {'id': 'ledger-first-fatal-exact-identity', 'kind': 'finite-ledger-state-and-identity',
             'required_states': ['ordinary-primary-with-first-Error', 'Error-primary-with-same-first-Error', 'subsequent-distinct-Errors', 'retained-fatal-before-primary'],
             'oracle': fatal_oracle, 'execution_join': join([(i, row) for i, row in rows if row['sequence'] in {'ordinary-then-error', 'error-then-ordinary', 'repeated-distinct-errors', 'retained-fatal-before-primary'}])},
            {'id': 'ledger-held-state-retained-without-own-native-effects', 'kind': 'finite-ledger-state-and-identity',
             'required_states': ['all-unrelated-fields-unchanged', 'held-local-obligation-state-unchanged', 'no-direct-body-native-effect', 'original-exceptions-have-no-added-suppression'],
             'oracle': unchanged_oracle, 'execution_join': join(rows)},
        ]
        for case in cases:
            case.update(applicable_native_site_ids=[], expected_outcome_scope='exact-own-finite-host-JVM-ledger-only',
                no_own_native_callback_rationale='Exact selected emitted body has no invoke instruction; actual invocation identity and state results are fresh. No transitive caller/native behavior is transferred to this body.')
        dispositions = []
        for original_case in original['required_semantic_cases']:
            if original_case == 'first-fatal-exact-identity':
                supporting = ['ledger-first-fatal-exact-identity']
                finite = 'Own method first Error reference retention demonstrated; actual enclosing fatal propagation is pending.'
            elif original_case == 'ordinary-primary-preserved':
                supporting = ['ledger-primary-exact-identity']
                finite = 'Own method first non-null primary reference retention demonstrated; actual enclosing failure reporting is pending.'
            else:
                supporting = ['ledger-held-state-retained-without-own-native-effects']
                finite = 'Own method preserves inspected held state and emits no native work. No enclosing count balancing, reentrancy/refusal, target close or cleanup completion is established.'
            dispositions.append({'id': original_case, 'status': 'retained-finite-component-evidence-enclosing-obligation-pending',
                'required_by': supporting, 'finite_evidence_scope': finite,
                'enclosing_execution_join': None, 'not_deleted_or_runtime_accepted': True})
        subjects.append({'id': sid, 'class': original['class'], 'method': original['method'], 'descriptor': original['descriptor'],
            'source_sha256': original['source_sha256'], 'class_sha256': original['class_sha256'],
            'applicability': 'local-first-failure-ledger-proposed-independent-root-selection-pending',
            'original_categories': original['categories'], 'categories': original['categories'],
            'original_required_case_ids': original['required_semantic_cases'],
            'required_semantic_cases': original['required_semantic_cases'], 'original_case_dispositions': dispositions,
            'required_cases': cases, 'native_sites': [],
            'source_rationale': {'full_selected_source': str(product.relative_to(D)), 'source_witness': witness,
                'actual_invocations': original['actual_invocations'], 'actual_instructions': original['actual_instructions'],
                'manual_disposition': null_oracle['state_transition'] + ' ' + primary_oracle['state_transition'] + ' ' + fatal_oracle['state_transition']},
            'fixture_scope': 'Ordinary selected B leaf constructors plus explicitly documented finite scalar/held-state seeding. The independently retained fatal/null-primary state is source-reachable through Observer.rendererTerminal; other ledgers receive it only as a finite field-independence control. It confers no enclosing lifecycle reachability credit.',
            'behavior_accepted': False, 'native_callback_state_deletion_authorized': False})
    proposal = {'schema': 1, 'status': 'three-source-specific-finite-ledger-controls-passed-independent-root-selection-pending',
        'source_context': CONTEXT, 'source_revision_context': receipt['source_revision_context'],
        'exact_original_subject_ids_preserved': True, 'exact_original_categories_and_case_names_preserved': True,
        'subjects': subjects, 'execution_summary': {'fresh_invocations': result['invocations'], 'checks': result['checks'],
            'exact_product_sources': 16, 'exact_product_classes': 209, 'exact_selected_B_leaves': 87,
            'all_209_emitted_class_identities_match': True, 'run': 'run-3', 'results': identity(result_path)},
        'prior_attempts': [{'run': 'run-1', 'result': 'fixture-construction-refusal-before-any-remember-call',
            'reason': 'Observer.bindRenderer requires initialized; retained exact stderr and initial controls/runner.'},
            {'run': 'run-2', 'result': '66-invocation-2899-check-control-passed',
             'reason_for_expansion': 'Source review identified Observer.rendererTerminal can retain first fatal with null primary. Run-3 adds this independent-component state, checked Throwable/Exception inputs, and actual before-reference records.'}],
        'limitations': ['Finite direct private method execution only; no source, emitted product class, or B leaf byte substitution.',
            'No listener registration, actual native runtime/device, UI, capture or process inventory. No physical/native cleanup credit.',
            'Explicit held-state and initialized fixture seeding is not enclosing lifecycle qualification.',
            'Original callback, count, cleanup, reentrant refusal, close and exception-propagation obligations remain retained and pending.',
            'Final selected producer execution joins, independent root policy selection, OTA and GA remain unaccepted.'],
        'full_matrix_or_policy_or_OTA_or_GA_accepted': False}
    save(D / 'proposal.json', proposal)

if __name__ == '__main__':
    main()
