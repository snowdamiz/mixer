"""Seal observed correction controls separately from future transport work."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    seal_path = HERE / 'correction-control-seal.json'
    assert not seal_path.exists()
    public = json.loads((HERE / 'public-summary.json').read_bytes())
    api = json.loads((HERE / 'api-compile-summary.json').read_bytes())
    private = json.loads((HERE / 'private-guard-run-1/summary.json').read_bytes())
    assert public['count'] == 39 and public['failures'] == 0
    assert len(api['controls']) == 15 and all(p['expected_disposition_and_attribution'] for p in api['controls'])
    assert private['preflight_failure'] is None and private['case_observations'] == private['passing_case_observations'] == 14 and private['failing_case_observations'] == 0
    for mode in private['modes']:
        assert mode['compile_succeeded'] and mode['run_succeeded'] and mode['protocol_failure'] is None
        assert len(mode['cases']) == 7 and all(c['shape_matches'] and c['full32_matches'] for c in mode['cases'])
    prior_seal = HERE.parent / 'implementation-review-1/review-seal.json'
    assert sha(prior_seal.read_bytes()) == '3c189178c6c8cef3fa2236bbe9d3d0c8cb2806fc4afcf9940bdc7af67a444382'
    prior = json.loads(prior_seal.read_bytes())
    for m in prior['members']:
        raw = (ROOT / m['path']).read_bytes()
        assert len(raw) == m['bytes'] and sha(raw) == m['sha256']
    snapshot = json.loads((HERE / 'candidate-snapshot-manifest.json').read_bytes())
    for m in snapshot['members']:
        for p in [ROOT / m['path'], HERE / 'candidate-snapshot' / m['path']]:
            raw = p.read_bytes()
            assert len(raw) == m['bytes'] and sha(raw) == m['sha256']
    cleanup = []
    for name in ['libmixer_fixture_cache_state.rlib', 'public-driver', 'borrowed-positive.rmeta']:
        p = HERE / 'work' / name
        raw = p.read_bytes()
        item = {'path': str(p.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw), 'all_owned_commands_returned': True}
        p.unlink()
        item['removed'] = not p.exists()
        cleanup.append(item)
    write(HERE / 'public-owned-product-cleanup.json', {'products': cleanup, 'unrelated_paths_removed': False,
        'source_and_raw_evidence_retained': True, 'process_discovery_used': False})
    invocations = [
        {'argv': ['/opt/homebrew/opt/python@3.14/bin/python3.14', '-B', 'verification/swift-cache-state-independent-review/execution-preparation/future_runner.py', '--admission', 'verification/swift-semantic-adapter-root-review/guard-correction-public-review-admission.json', '--admission-sha256', '3230858dae7a43050c03f06c89202447f27627554302b6709df9c8f70b38f559', '--case-set', 'basics', '--start', '0', '--count', '39'], 'exit_code': 0, 'stdout': str(HERE) + '\n'},
        {'argv': ['/opt/homebrew/opt/python@3.14/bin/python3.14', '-B', str((HERE / 'prepare_correction_review.py').relative_to(ROOT))], 'exit_code': 0, 'stdout': '{"public_cases_passed": 39, "expected_API_dispositions": 15, "snapshot_members": 814, "private_runner_ready": true}\n'},
        {'argv': ['/opt/homebrew/opt/python@3.14/bin/python3.14', '-B', str((HERE / 'run_private_guards.py').relative_to(ROOT))], 'exit_code': 0, 'stdout': '{"preflight_failure": null, "observations": 14, "passing": 14, "failing": 0, "summary": "' + str(HERE / 'private-guard-run-1/summary.json') + '"}\n'}]
    write(HERE / 'outer-invocations.json', {'scope': 'Actual outer exec results transcribed; full inner bounded command receipts retained', 'cwd': str(ROOT), 'python': sys.version, 'invocations': invocations})
    write(HERE / 'correction-control-receipt.json', {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
        'status': 'scoped-correction-control-pass', 'candidate_seal_sha256': snapshot['candidate_seal_sha256'],
        'candidate_members_verified': len(snapshot['members']), 'candidate_bytes_verified': sum(m['bytes'] for m in snapshot['members']),
        'initial_review_members_unchanged': len(prior['members']), 'public_four_File_cases_passed': 39,
        'API_expected_attributed_dispositions': 15, 'private_guard_observations_passed': 14,
        'private_guard_modes': ['default', 'optimized'], 'private_from_empty_public_reachability': False,
        'old_library_sources_unchanged': True, 'production_diff_only_shape_q': True,
        'full32_expectations_glue_append_delta_unchanged': True,
        'work_lifetime_or_full_matrix_accepted': False, 'implementation_accepted': False,
        'all_owned_binary_products_hashed_and_removed': True, 'producer_models_harness_tests_executed': False,
        'source_product_mutated': False, 'native_UI_capture_process_discovery_used': False,
        'GA_qualified': False,
        'remaining': 'Initial detailed source accounting/lifetime requests; all unadmitted public bulk/private numeric/fault/layout/IO/budget and terminal matrices. Future content-dedup transport is separate proposal only.'})
    paths = sorted(p for p in HERE.rglob('*') if p.is_file() and p != seal_path)
    paths.append(ROOT / 'docs/swift-cache-state-implementation-review-2.md')
    members = []
    for p in paths:
        assert not p.is_symlink()
        raw = p.read_bytes()
        members.append({'path': str(p.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw)})
    seal = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'scope': 'Immutable correction control results only; later transport-amendment members are outside this explicit member set',
        'command': ['/opt/homebrew/opt/python@3.14/bin/python3.14', '-B', str(Path(__file__).relative_to(ROOT))],
        'python': sys.version, 'script_sha256': sha(Path(__file__).read_bytes()),
        'members': members, 'member_count': len(members), 'member_bytes': sum(m['bytes'] for m in members),
        'implementation_accepted': False, 'GA_qualified': False}
    write(seal_path, seal)
    print(json.dumps({'seal': str(seal_path.relative_to(ROOT)), 'sha256': sha(seal_path.read_bytes()), 'members': len(members), 'bytes': seal['member_bytes']}))


if __name__ == '__main__':
    main()
