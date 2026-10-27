#!/usr/bin/env python3
"""Validate all own joins and freeze this closed finite-control packet."""
from pathlib import Path
import datetime
import hashlib
import json

D = Path(__file__).resolve().parent

def identity(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

def main():
    proposal = json.loads((D / 'proposal.json').read_bytes())
    originals = json.loads((D / 'inputs/original-three-subjects.json').read_bytes())['subjects']
    actual = json.loads((D / 'run-3/actual-ledger-results.json').read_bytes())
    assert [s['id'] for s in proposal['subjects']] == [s['id'] for s in originals]
    assert len(proposal['subjects']) == 3 and actual['invocations'] == 87 and actual['checks'] == 3823
    assert identity(D / 'FiniteLedgerControls.java') == json.loads((D / 'run-3/receipt.json').read_bytes())['control']
    assert identity(D / 'run_controls.py') == json.loads((D / 'inputs/provenance.json').read_bytes())['runner']
    for old, new in zip(originals, proposal['subjects']):
        assert old['categories'] == new['categories'] == new['original_categories']
        assert old['required_semantic_cases'] == new['required_semantic_cases'] == new['original_required_case_ids']
        assert [case['id'] for case in new['original_case_dispositions']] == old['required_semantic_cases']
        for case in new['required_cases']:
            join = case['execution_join']
            assert join['source_context'] == proposal['source_context']
            assert join['subject_id'] == old['id'] and join['subject_class_sha256'] == old['class_sha256']
            assert {key: join['results'][key] for key in ('bytes', 'sha256')} == identity(D / join['results']['path'])
            for index in join['results']['zero_based_row_indexes']:
                assert actual['rows'][index]['subject_id'] == old['id']
                assert actual['rows'][index]['class_sha256'] == old['class_sha256']
            assert join['final_selected_producer_reexecution_join'] is None
        assert new['behavior_accepted'] is False and new['native_callback_state_deletion_authorized'] is False
    for name in ('run-1', 'run-2', 'run-3'):
        cleanup = json.loads((D / name / 'cleanup.json').read_bytes())
        assert cleanup['all_started_children_reaped'] and cleanup['scratch_removed']
        assert cleanup['native_instances_started'] == 0 and cleanup['native_cleanup_credit'] is False
    assert not proposal['full_matrix_or_policy_or_OTA_or_GA_accepted']
    for path in D.rglob('*'):
        assert not path.is_symlink(), path
    members = [{'path': path.relative_to(D).as_posix(), **identity(path)} for path in sorted(D.rglob('*'))
               if path.is_file() and path.relative_to(D).as_posix() not in {'manifest.json', 'seal.json'}]
    save(D / 'manifest.json', {'schema': 1, 'scope': 'Closed three-method finite host-JVM identity-control packet; root policy and final integration pending',
        'members': members})
    members.append({'path': 'manifest.json', **identity(D / 'manifest.json')})
    members.sort(key=lambda row: row['path'])
    save(D / 'seal.json', {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'three-finite-ledger-controls-passed-root-selection-pending', 'source_context': proposal['source_context'],
        'member_count': len(members), 'member_bytes': sum(row['bytes'] for row in members), 'members': members,
        'scope': 'Only exact three finite remember(Throwable) methods and retained original obligations; no original packet/canonical source/index/commit/push mutation; no native or physical cleanup credit',
        'complete_matrix_policy_native_OTA_GA_accepted': False})
    sealed = json.loads((D / 'seal.json').read_bytes())
    for member in sealed['members']:
        assert identity(D / member['path']) == {key: member[key] for key in ('bytes', 'sha256')}
    closed = {path.relative_to(D).as_posix() for path in D.rglob('*') if path.is_file()}
    assert closed == {row['path'] for row in sealed['members']} | {'seal.json'}
    print(json.dumps({'seal': identity(D / 'seal.json'), 'members': len(members), 'closed_members_verified': True,
        'subjects': 3, 'invocations': 87, 'checks': 3823, 'source_context': proposal['source_context']}))

if __name__ == '__main__':
    main()
