#!/usr/bin/env python3
"""Verify frozen constructor evidence and record root's scoped source review."""
from pathlib import Path
import datetime
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
PRODUCER = ROOT / 'verification/android-renderer-state-journal-constructor-controls'
REVIEW = ROOT / 'verification/android-renderer-state-journal-constructor-independent'

def read(path):
    return json.loads(path.read_bytes())

def verify(root, expected, count, total):
    assert hashlib.sha256((root / 'seal.json').read_bytes()).hexdigest() == expected
    seal = read(root / 'seal.json')
    paths = set()
    for member in seal['members']:
        relative = Path(member['path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        assert str(relative) not in paths
        paths.add(str(relative))
        path = root / relative
        assert path.is_file() and not path.is_symlink()
        raw = path.read_bytes()
        assert len(raw) == member['bytes']
        assert hashlib.sha256(raw).hexdigest() == member['sha256']
    assert len(paths) == count and sum(m['bytes'] for m in seal['members']) == total
    all_paths = list(root.rglob('*'))
    assert not any(p.is_symlink() for p in all_paths)
    assert {str(p.relative_to(root)) for p in all_paths if p.is_file()} == paths | {'seal.json'}
    return {'path': str(root.relative_to(ROOT)), 'seal_sha256': expected,
            'members_verified': count, 'bytes_verified': total, 'closed_path_set_verified': True}

producer = verify(PRODUCER, 'd134612993dd5d2071c55e2f63c2ee93fbaea503f5123e146a839ee89354a279', 152, 2814411)
independent = verify(REVIEW, 'f2944a1ebbe2969e290efd65a09f70d1a98b9b1df6da0acb5c287773fc0da733', 27, 1105960)
original = read(PRODUCER / 'run-3/actual-results.json')
replayed = read(REVIEW / 'run-1/producer-results.json')
assert original == replayed
assert original['invocations'] == len(original['rows']) == 85
assert original['finite_rows'] == 15 and original['callback_rows'] == 70
assert original['original_boundary_counts'] == [2, 2, 3]
assert original['original_final_counts'] == [0, 0, 0]
expected = read(ROOT / 'verification/android-renderer-finite-membership-controls/inputs/selected-product-class-map.json')
assert len(expected) == 209
assert read(PRODUCER / 'run-3/actual-product-class-map.json') == expected
assert read(REVIEW / 'run-1/actual-product-class-map.json') == expected
fresh = read(REVIEW / 'run-1/independent-results.json')
assert fresh['independent_cases'] == len(fresh['rows']) == 3 and fresh['checks'] == 104
assert fresh['final_counts'] == [0, 0, 0]
assert [len(row['all_unfiltered_passive_outcomes']) for row in fresh['rows']] == [1, 2, 6]
for row in fresh['rows']:
    assert row['counts'] == [2, 2, 3] and row['callback_scope_only']
    for outcome in row['all_unfiltered_passive_outcomes']:
        assert outcome['completion'] == 'return'
        assert len(outcome['frames']) < 24
        assert outcome['frames'][0]['method'] == '<init>'
commands = read(REVIEW / 'run-1/commands.json')
assert len(commands) == 6
assert all(c['exit'] == 0 and c['reaped'] and not c['timeout'] for c in commands)
review = read(REVIEW / 'review.json')
assert review['verdict'] == 'accept-scoped-host-constructor-facets' and not review['required_amendments']
receipt = {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'reviewer': 'root', 'status': 'two-constructor-host-object-result-and-callback-facets-selected',
    'producer': producer, 'independent_review': independent,
    'source_context': review['source_context'],
    'root_review': 'Read both exact product constructors, producer hook/result assertions, complete independent three-case harness, findings and raw outcome records. Reverified both closed packets, exact replay equality, all209 class maps, actual original counts and bounded terminal command evidence.',
    'root_fresh_runtime_commands': 0,
    'producer_and_replay': {'direct_calls_each': 85, 'checks_each': 2556,
        'finite_rows_each': 15, 'callback_rows_each': 70, 'exact_native_tuples': 5,
        'normal_enclosing_objects_each': 65, 'exact_enclosing_exceptions_each': 20,
        'tuple_selected_nonvoid_return_observations_each': 30},
    'fresh_independent_controls': {'cases': 3, 'checks': 104, 'unfiltered_nonvoid_returns': 9},
    'source_specific_limits': [
        'Thirty returns are tuple-selected observations, never the unfiltered total for all85 producer calls.',
        'These snapshot constructors do not enforce outer fence/generation freshness or confer membership/completion/release authority.',
        'Terminal/dirty perturbations qualify constructor callback behavior only, not real enclosing transaction rejection.',
        'Void getLocationInWindow has observed successful enclosing array contents, not a fabricated nonvoid return.',
        'Unhooked getters/children/span helpers have finite host object-result evidence only.',
        'Independent alias control is injected host state with no ordinary reachability claim.',
        'Producer initial setup failure lacks its original runner snapshot; run2 is historical, not extra final credit.',
        'Fixture close may catch product disposal errors; no physical cleanup credit.'
    ],
    'pending': review['pending'],
    'producer_fresh_final_selected_reexecution_required': True,
    'complete_matrix_execution_closure_canonical_native_OTA_GA_accepted': False,
    'cleanup': review['cleanup'],
    'review_command': ['python3', '-B', str(Path(__file__).relative_to(ROOT))],
    'review_python_version': sys.version,
    'review_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
}
target = Path(__file__).with_name('renderer-state-journal-constructor-selection.json')
assert not target.exists(), 'one completed review receipt only'
target.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'status': receipt['status'], 'receipt': str(target.relative_to(ROOT)),
                  'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}))
