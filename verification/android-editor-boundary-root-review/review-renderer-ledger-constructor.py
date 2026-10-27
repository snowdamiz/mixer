#!/usr/bin/env python3
"""Root data/source review; never executes the producer's frozen runner."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / 'verification/android-renderer-finite-ledger-constructor'
OUT = Path(__file__).resolve().parent
SEAL = '43ee31803039e416efa224e8ae67654b27d073035587da11c66a3d6b8adf9fd6'

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def read(relative):
    return json.loads((PACKET / relative).read_bytes())

def identity(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': digest(raw)}

assert digest((PACKET / 'seal.json').read_bytes()) == SEAL
seal = read('seal.json')
assert len(seal['members']) == seal['member_count'] == 482
paths = set()
for member in seal['members']:
    name = member['path']
    relative = Path(name)
    assert not relative.is_absolute() and '..' not in relative.parts and name not in paths
    paths.add(name)
    path = PACKET / relative
    assert path.is_file() and not path.is_symlink()
    assert identity(path) == {'bytes': member['bytes'], 'sha256': member['sha256']}
actual = set()
for base, dirs, files in os.walk(PACKET, followlinks=False):
    for name in dirs + files:
        assert not (Path(base) / name).is_symlink()
    actual.update((Path(base) / name).relative_to(PACKET).as_posix() for name in files)
assert actual == paths | {'seal.json'}
assert sum(m['bytes'] for m in seal['members']) == 15392855
expected_classes = read('inputs/selected-product-class-map.json')
assert len(expected_classes) == 209
assert read('run-1/actual-product-class-map.json') == expected_classes
for name, expected in expected_classes.items():
    assert identity(PACKET / 'run-1/classes' / name) == expected
results = read('run-1/actual-results.json')
rows = results['rows']
snapshots = read('run-1/snapshots.json')['snapshots']
assert len(rows) == 41 and len(snapshots) == 82
assert results['remember_invocations'] == 32 and results['constructor_invocations'] == 9
assert results['original_boundary_counts'] == [2, 2, 3]
assert results['original_final_counts'] == [0, 0, 0]
seen = set()
for index, row in enumerate(rows):
    assert row['actual_after'] == row['literal_expected_after']
    assert row['counts_before'] == row['counts_after'] == [2, 2, 3]
    assert row['actual_typed_outcome']['exception'] is None
    assert row['native_effects'] == 0
    pair = []
    for when in ['before', 'after']:
        snapshot = snapshots[row['snapshot_' + when + '_index']]
        raw = json.dumps(snapshot, separators=(',', ':'), ensure_ascii=False).encode()
        assert digest(raw) == row['snapshot_' + when + '_sha256']
        pair.append(snapshot)
    before, after = pair
    for key in ['containers', 'throwable_diagnostics', 'native_event_prefix', 'counts']:
        assert before[key] == after[key]
    b, a = dict(before['fields']), dict(after['fields'])
    if index < 32:
        assert row['actual_typed_outcome']['kind'] == 'void'
        for name in ['primary', 'firstFatal']:
            key = 'renderer.ledger/dev.mixer.android.NativeRenderer$CleanupLedger#' + name
            assert a.pop(key) == row['literal_expected_after'][name]
            assert b.pop(key) == row['ledger_before'][name]
    else:
        outcome = row['actual_typed_outcome']
        assert outcome['kind'] == 'constructed-reference'
        assert outcome['constructed_reference'] not in seen
        seen.add(outcome['constructed_reference'])
        assert not row['membership_or_release_authority_inferred']
        assert not row['allocation_failure_qualified']
    assert a == b
commands = read('run-1/commands.json')
assert len(commands) == 4
assert all(c['exit'] == 0 and c['reaped'] and not c['timeout'] for c in commands)
source = (PACKET / 'inputs/product/NativeRenderer.java').read_text()
assert 'PreservationMembership(NativeState state,NativeAppearanceViewsV2.FieldPreservation scope){this.state=state;this.scope=scope;}' in source
assert 'private void rememberV2(Throwable failure){if(failure==null)return;if(v2Cleanup.primary==null)v2Cleanup.primary=failure;' in source
assert 'if(failure instanceof java.lang.Error fatal&&v2Cleanup.firstFatal==null)v2Cleanup.firstFatal=fatal;}' in source
originals = read('inputs/original-two-subjects.json')['subjects']
proposal = read('proposal.json')
assert len(originals) == len(proposal['subjects']) == 2
for original in originals:
    candidate = next(s for s in proposal['subjects'] if s['id'] == original['id'])
    for k, v in original.items():
        assert candidate[k] == v, k
    assert not candidate['finite_control_extension']['original_subject_or_case_accepted']
assert proposal['all_original_enclosing_cases_pending']
receipt = {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'reviewer': 'root', 'status': 'two-exact-finite-renderer-component-facets-selected',
    'source_revision_context': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'producer': {'path': str(PACKET.relative_to(ROOT)), 'seal_sha256': SEAL,
                 'members_verified': 482, 'bytes_verified': 15392855, 'closed_path_set_verified': True},
    'source_context': seal['source_context'],
    'root_review': 'Read exact two product bodies, full literal case sequences, reflected invocation and snapshot assertions, runner and actual rows. Independently verified all 482 members, 209 compiled class identities, 82 snapshot hashes and differences, 41 typed outcomes, exact original subject records and bounded terminal command evidence.',
    'root_fresh_runtime_commands': 0,
    'producer_direct_calls': {'rememberV2': 32, 'PreservationMembership_constructor': 9},
    'repeated_comparisons_not_semantic_case_count': results['checks'],
    'source_specific_limits': [
        'Null Throwable is inert; first primary and first Error references are retained independently.',
        'Private ledger seeds establish field behavior, not enclosing lifecycle reachability.',
        'Constructor stores exactly two final references; null and crossed pairs do not confer membership or release authority.',
        'Nine ordinary fresh allocations do not qualify allocation failure.',
        'Snapshots cover named direct fields, containers, diagnostics and event prefix, not arbitrary global purity.',
        'Fixture close catches product failures and supplies host disposal evidence only.'
    ],
    'original_live_counts': {'entry': [2, 2, 3], 'after_restored_edit': [0, 0, 0]},
    'selected_facet': 'renderer-finite-source-invariants',
    'all_original_enclosing_and_allocation_failure_obligations_pending': True,
    'producer_fresh_final_selected_reexecution_required': True,
    'complete_matrix_canonical_native_OTA_GA_accepted': False,
    'cleanup': read('run-1/cleanup.json'),
    'review_command': ['python3', '-B', str(Path(__file__).relative_to(ROOT))],
    'review_script': identity(Path(__file__)),
}
target = OUT / 'renderer-ledger-constructor-selection.json'
assert not target.exists(), 'one completed review receipt only'
target.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'status': receipt['status'], 'receipt': str(target.relative_to(ROOT)), **identity(target)}))
