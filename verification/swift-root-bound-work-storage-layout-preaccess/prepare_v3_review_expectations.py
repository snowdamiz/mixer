#!/usr/bin/env python3
"""Freeze independent finite-cutoff expectations before any V3 producer access.

This reads only the already frozen independent review stage. It does not import
producer code, run a producer checker, launch a child, or inspect V3 membership.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN_STAGES = [
    ('preaccess-seal.json', '001ec6fbfb69a6c784083615323df670c9d932ecace8fd598fc68447867d9d67', 22),
    ('review-01-seal.json', 'edbf7e50d0d8b1847ac75d391d47ba6a16c17e73e6811b153203b8cafe5fc15c', 5),
    ('review-02-seal.json', '8409755f4e955a4ccdc2132eeea5b3218aee44fbe87127d288f434360852a0fa', 5),
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate object key')
        value[key] = item
    return value


def load(path):
    return json.loads(path.read_bytes(), object_pairs_hook=unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def main():
    started = time.monotonic()
    verified = []
    seen = set()
    for name, expected, count in FROZEN_STAGES:
        path = HERE / name
        assert path.is_file() and not path.is_symlink()
        assert sha(path.read_bytes()) == expected, name
        seal = load(path)
        assert len(seal['members']) == seal['member_count'] == count
        assert sha(canonical(seal['members'])) == seal['tree_sha256']
        for row in seal['members']:
            assert row['path'] not in seen, row['path']
            seen.add(row['path'])
            member = HERE / row['path']
            assert member.is_file() and not member.is_symlink()
            raw = member.read_bytes()
            assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], row['path']
        verified.append({'path': name, 'sha256': expected, 'members_verified': count,
                         'tree_sha256': seal['tree_sha256']})
    oracle = load(HERE / 'preaccess-oracle.json')
    assert sha((HERE / 'preaccess-oracle.json').read_bytes()) == '8e1b8b65d1d7ac62438c0d9f8b7e32f9dbd4be2deccba427a12594b7f580220e'
    assert oracle['original_source146_tree'] == '91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f'
    assert oracle['diagnostic_source146_tree'] == '2ec0d8555d6a18d7c8222984faaec3a1543c1a1b800f4b90381f70571215516e'
    correction = load(HERE / 'preaccess-oracle-correction.json')
    assert correction['correction'] == {
        'path': ['closure_queries', 1, 'expression', 'column_end'],
        'old': 144, 'new': 15,
        'reason': 'Multiline span end column is the last line length plus one, not start column plus complete token length.'}
    assert correction['source_bytes_tree_identity_or_query_strategy_changed'] is False
    assert load(HERE / 'prepared-packet-review-01.json')['independent_synthetic_controls_passed'] == 34
    v2 = load(HERE / 'prepared-packet-review-02.json')
    assert v2['R01_duplicate_keys_closed'] and v2['R02_launch_and_cleanup_entry_closed']
    assert v2['remaining_finding']['id'] == 'R02-publication'
    cases = [
        {'id': 'C01', 'inject': 'During constructor before process assignment',
         'expect': 'Record and return; successful constructor handle retained; eventual cleanup closes only that owned child; pre-cutoff request rejects.'},
        {'id': 'C02', 'inject': 'Constructor raises after a handled signal',
         'expect': 'Pre-cutoff request rejects; no invented handle; constructor failure retained; no claim that a never-retained child was closed.'},
        {'id': 'C03', 'inject': 'During owned cleanup or its wait',
         'expect': 'Record and return without interrupting cleanup; preserve child handle and exact closure evidence; pre-cutoff request rejects.'},
        {'id': 'C04', 'inject': 'After cleanup and before posthash or diagnostic parsing completes',
         'expect': 'Record and return; request belongs to pre-cutoff set and rejects even if cleanup/hash/parser later succeeds.'},
        {'id': 'C05', 'inject': 'Immediately before one-way cutoff assignment',
         'expect': 'Handler observes cutoff incomplete; observation belongs to pre-cutoff set; accepted receipt is forbidden.'},
        {'id': 'C06', 'inject': 'Between one-way cutoff assignment and pre-cutoff snapshot',
         'expect': 'Handler observes cutoff complete; record only as outside completed observation; do not insert into frozen pre-cutoff set or retroactively reject.'},
        {'id': 'C07', 'inject': 'After pre-cutoff snapshot and before observation write',
         'expect': 'Same post-cutoff semantics; no further compiler/hash/parser work; final evidence expressly limits signal coverage to cutoff.'},
        {'id': 'C08', 'inject': 'During observation write',
         'expect': 'Post-cutoff record and return; accepted receipt may follow only after observation write succeeds; no promise that late record is in published snapshot.'},
        {'id': 'C09', 'inject': 'During final receipt write',
         'expect': 'Post-cutoff record and return; published observation already exists; receipt explicitly covers only pre-cutoff handler observations.'},
        {'id': 'C10', 'inject': 'Observation write fails',
         'expect': 'Final accepted receipt must not be published; retained failure may coexist with partial observation bytes but never a completed accepted receipt.'},
        {'id': 'C11', 'inject': 'Final receipt write fails',
         'expect': 'Observation retained; no successfully completed accepted receipt is claimed by the runner.'},
    ]
    report = {
        'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
        'status': 'FROZEN_INDEPENDENT_V3_EXPECTATIONS_BEFORE_V3_ACCESS',
        'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))],
        'python': sys.version, 'elapsed_seconds': time.monotonic() - started,
        'script_sha256': sha(Path(__file__).read_bytes()),
        'frozen_stages_verified': verified, 'unique_frozen_members_verified': len(seen),
        'original_oracle_sha256': sha((HERE / 'preaccess-oracle.json').read_bytes()),
        'source146_tree': oracle['original_source146_tree'],
        'diagnostic146_tree': oracle['diagnostic_source146_tree'],
        'multiline_coordinate_correction_preserved': True,
        'v3_packet_accessed': False, 'producer_code_imported_or_replayed': False,
        'compiler_runtime_version_native_ui_capture_invocations': 0,
        'retained_decision': {'R01': 'closed in V2', 'R02_launch_cleanup_entry': 'closed in V2',
                              'R02_publication': 'requires exact frozen V3 review'},
        'required_order': ['compiler child and owned group closure', 'source and toolchain posthash',
                           'terminal diagnostic parser', 'one-way cutoff assignment',
                           'freeze all pre-cutoff handler observations', 'record pre-cutoff interruption refusal',
                           'publish observation successfully', 'publish final accepted receipt'],
        'cutoff_requirements': [
            'Assign the irreversible cutoff flag before taking any pre-cutoff signal snapshot.',
            'A handler chooses pre/post classification from cutoff state at handler observation, then records and returns in all phases.',
            'Every pre-cutoff handler observation rejects; no late handler may append to the frozen pre-cutoff set.',
            'No compiler, hash or parser work follows cutoff; cutoff time is the explicit finite observation endpoint.',
            'Post-cutoff signals are outside completed observation and are never promised in receipt snapshots.',
            'No inherited blocked signal mask or preexec action is introduced.',
            'Observation publication failure cannot leave a completed accepted receipt.',
            'Producer controls are retained evidence to read, not replay; fresh independent synthetic models are not actual compiler qualification.'
        ],
        'independent_review_cases': cases,
        'execution_contract': oracle['execution_contract'],
        'additional_deadlines_seconds': {'work': 44, 'cleanup': 49, 'posthash': 53.5},
        'independent_terminal_diagnostic_refusals_remain': True,
        'release_recommended': False,
        'all_actual_layout_prices_backing_peaks_funding_ownership_native_FieldLog_OTA_GA_pending': True,
        'cleanup': 'No compiler, runtime, native or capture process started; none owed.'}
    with (HERE / 'v3-preaccess-expectations.json').open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ('status', 'unique_frozen_members_verified',
          'v3_packet_accessed', 'compiler_runtime_version_native_ui_capture_invocations', 'release_recommended')}))


if __name__ == '__main__':
    main()
