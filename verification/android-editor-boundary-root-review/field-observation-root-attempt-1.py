"""One-shot root data/custody review of immutable finite host evidence."""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name('field-observation-host-acceptance.json')
AUTHOR = ROOT / 'verification/android-field-preservation-observation-controls'
REVIEW = ROOT / 'verification/android-field-preservation-observation-independent'
assert __debug__ and not OUT.exists()

def identity(path):
    b = path.read_bytes()
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

def load(path):
    return json.loads(path.read_bytes())

def closed(folder, seal_name, expected_hash, expected_count):
    seal = folder / seal_name
    assert identity(seal)['sha256'] == expected_hash
    rows = load(seal)['members']
    names = set()
    for row in rows:
        p = Path(row['path'])
        assert not p.is_absolute() and '..' not in p.parts
        assert row['path'] not in names
        names.add(row['path'])
        assert identity(folder / p) == {k: row[k] for k in ('bytes', 'sha256')}
    files = set()
    for p in folder.rglob('*'):
        assert not p.is_symlink()
        if p.is_file() and p != seal:
            files.add(str(p.relative_to(folder)))
    assert len(rows) == len(names) == expected_count and files == names
    return {'path': str(seal.relative_to(ROOT)), **identity(seal), 'members': len(names),
            'member_bytes': sum(x['bytes'] for x in rows), 'closed_set_rehashed': True}

author = closed(AUTHOR, 'seal.json', '02f4a046dd7f10266e17b804c6b86bd857f19807306bcf17214f9d5914e81250', 171)
review = closed(REVIEW, 'review-seal.json', 'c17e30c16cb83cd6d7b19fb3a180f20243b44e3c2161a544491cab416cf71728', 55)
assert author['member_bytes'] == 2792018
original = load(AUTHOR / 'inputs/original-280-obligations.json')
assert identity(AUTHOR / 'inputs/original-280-obligations.json')['sha256'] == 'c782b54865efc29534908b8ae71b6c83f749ad79af1d62c3d0a4a364772c20b2'
assert len(original['subjects']) == len({r['id'] for r in original['subjects']}) == 280
subjects = [r for r in original['subjects'] if r['class'] == 'dev/mixer/android/NativeAppearanceViewsV2$FieldPreservation' and r['method'] in ('tuple', 'capture', 'exact', 'continuation')]
assert len(subjects) == 4 and load(AUTHOR / 'inputs/exact-four-subject-contracts.json')['subjects'] == subjects
selected = load(AUTHOR / 'run-3/actual-results.json')
exact = load(REVIEW / 'run-exact/actual-results.json')
recovery = load(REVIEW / 'run-recovery/actual-results.json')
assert identity(AUTHOR / 'run-3/actual-results.json') == identity(REVIEW / 'run-exact/actual-results.json')
assert selected == exact and recovery['rows'] == selected['rows']
assert selected['checks'] == 731 and recovery['checks'] == 747
assert selected['invocations'] == recovery['invocations'] == len(selected['rows']) == 56
assert len({r['finite_case'] for r in selected['rows']}) == 56
methods = collections.Counter(r['subject_id'].split('#')[1].split('(')[0] for r in selected['rows'])
assert methods == {'tuple': 29, 'capture': 4, 'exact': 19, 'continuation': 4}
facets = {r['subject_id']: r for r in load(AUTHOR / 'finite-facet-joins.json')['subjects']}
assert set(facets) == {r['id'] for r in subjects}
for r in subjects:
    facet = facets[r['id']]
    indexes = [i for i, row in enumerate(selected['rows']) if row['subject_id'] == r['id']]
    assert facet['actual_row_indexes'] == indexes and facet['actual_finite_invocations'] == len(indexes)
    assert len(r['required_semantic_cases']) == 8
    assert facet['original_required_semantic_cases'] == [{'case': c, 'status': 'pending-original-enclosing-case-not-discharged-by-these-finite-facets'} for c in r['required_semantic_cases']]
    assert facet['finite_facet_only'] and facet['canonical_qualification'] == 'not-granted'
    assert all(facet[k] == r[k] for k in ('categories', 'source_sha256', 'class_sha256'))
source_map = load(AUTHOR / 'inputs/selected-product-source-map.json')
class_map = load(AUTHOR / 'inputs/selected-product-class-map.json')
assert len(source_map) == 16 and len(class_map) == 209
context = hashlib.sha256(json.dumps({'source_map': source_map, 'class_map': class_map}, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
assert context == selected['source_context'] == '1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'
for name, value in source_map.items():
    assert identity(AUTHOR / 'inputs/product' / name) == value
history = load(AUTHOR / 'inputs/historical189-custody.json')
assert identity(ROOT / history['path']) == {k: history[k] for k in ('bytes', 'sha256')}
getters = [g for r in exact['rows'] for g in r['actual_native_getter_outcomes']]
assert len(getters) == selected['getter_entries'] == selected['checking_true_at_entries'] == 22
for g in getters:
    assert g['checking_at_outcome'] and len(g['production_frames']) < 24
    frames = [f for f in g['production_frames'] if f['class'].endswith('$FieldPreservation') and f['method'] == 'exact']
    assert len(frames) == 1 and frames[0]['bci'] == 40 and frames[0]['descriptor'] == '()V'
for r in exact['rows']:
    assert r['actual_Input'] is None
    assert r['counts_before'] == r['counts_after'] == [2, 2, 3]
    assert r['restored_before_original_edit_resumes'] and r['no_membership_release_authority']
assert recovery['host_threads_started'] == recovery['host_threads_joined'] == 3
assert recovery['actual_final_counts'] == [0, 0, 0] and recovery['failure_latch_clear'] and recovery['original_edit_completed_after_restores']
owner, retry = recovery['independent_controls']
assert owner['before'] == owner['after'] and owner['checking_after'] is False
assert owner['getter_outcomes_added'] == owner['actual_event_delta'] == 0
assert owner['exception_type'] == 'java.lang.IllegalStateException' and owner['exception_message'] == 'V2 requires UI owner thread'
assert retry['before'] == retry['after'] and retry['checking_after'] is False
assert retry['no_scope_snapshot_checking_restore_between_attempts'] and retry['final_Record_view_Input_unchanged']
failed, returned = retry['getter_outcomes']
assert failed['completion'] == 'exception' and failed['exception_reference'] == retry['exception_reference']
assert returned['completion'] == 'return' and retry['retry_exception_reference'] == 'null'
assert returned['returned_editable_immutable_value']['reference'] == retry['before']['editable']
command_count = 0
for folder, runs in ((AUTHOR, ('run-1', 'run-2', 'run-3')), (REVIEW, ('run-exact', 'run-recovery'))):
    for run in runs:
        p = folder / run
        cleanup = load(p / 'cleanup.json')
        assert cleanup['all_started_children_reaped'] and cleanup['owned_scratch_removed'] and cleanup['jdk_tool_lease_preserved']
        for c in load(p / 'commands.json'):
            assert c['reaped'] and not c['timeout'] and c['elapsed_seconds'] < 60
            for stream in ('stdout', 'stderr'):
                v = c[stream]
                assert identity(p / v['path']) == {k: v[k] for k in ('bytes', 'sha256')}
            if run != 'run-1':
                assert c['exit'] == 0
            command_count += 1
        if folder == REVIEW:
            assert load(p / 'actual-product-class-map.json') == class_map
assert load(AUTHOR / 'run-1/failure.json')['status'] == 'actual-failed-attempt-no-pass-credit'
assert load(AUTHOR / 'run-1/commands.json')[-1]['exit'] == 1
assert load(AUTHOR / 'run-2/receipt.json')['checks'] == 683
validation = load(REVIEW / 'recovery-validation.json')
assert not validation['post_fixture_close_product_disposal_state_asserted']
review_text = (REVIEW / 'README.md').read_text()
assert 'events=0' in review_text and 'catches product exceptions' in review_text
revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, timeout=60, check=True).stdout.decode().strip()
receipt = {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status': 'accepted-finite-host-observation-and-recovery-facets-only',
    'argv': sys.argv, 'python': sys.version, 'platform': platform.platform(),
    'review_source_revision_context': revision, 'review_script': identity(Path(__file__)),
    'producer': author, 'independent_review': review, 'source_context': context,
    'original280_unchanged': True, 'whole_four_original_records_unchanged': True,
    'original_eight_cases_each_pending': True, 'history189_plus5': history,
    'selected_rows': 56, 'selected_assertions': 731, 'selected_getter_outcomes': 22,
    'selected_by_method': dict(methods), 'actual_getter_BCI': 40,
    'independent_exact_replay': identity(REVIEW / 'run-exact/actual-results.json'),
    'independent_recovery': {'controls': 2, 'additional_actual_exact_calls': 3, 'additional_assertions': 16, 'supplemental_total_assertions': 747, 'actual_owner_thread_event_delta': 0, 'immediate_retry_without_scope_snapshot_checking_restore': True},
    'retained_command_output_pairs_verified': command_count,
    'earlier_attempts': 'run1 failed final-field perturbation preflight retained; run2 56/683 historical; selected run3 56/731',
    'limits': [
        'Shared.capture.events is literal0; shared unchanged assertion does not prove event-log restoration',
        'Fixture close catches product exceptions; completed original edit counts [0,0,0] and cleared scope do not establish full postdisposal state',
        'Seven direct Input support returns remain separate; exact subject Input invocation counts and BCIs remain pending',
        'All original enclosing/helper/allocation/exceptional partial-output and eight-case obligations remain pending',
        'Injected getter exceptions are actual host hook outcomes, not platform-origin native errors',
        'No canonical, complete matrix, execution closure, native, OTA, release or GA qualification',
    ],
    'cleanup': 'Producer and independent own children reaped and scratch removed per verified command/cleanup records; no native/UI/capture/process inventory performed by root',
    'product_or_test_execution_in_this_root_review': False,
}
OUT.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'acceptance': str(OUT.relative_to(ROOT)), **identity(OUT), 'members_verified': 226, 'command_output_pairs': command_count}))
