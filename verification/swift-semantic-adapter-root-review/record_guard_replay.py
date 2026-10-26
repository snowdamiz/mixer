"""Record sealed independent controls without accepting unrun implementation gates."""
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

def bind(p):
    raw = p.read_bytes()
    return {'path': p.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def verify(relative, digest):
    p = ROOT / relative
    assert bind(p)['sha256'] == digest
    data = json.loads(p.read_bytes())
    if isinstance(data['members'], list):
        members = data['members']
    else:
        members = [{'path': k, **v} for k, v in data['files'].items()]
    assert len({x['path'] for x in members}) == len(members)
    for member in members:
        name = PurePosixPath(member['path'])
        assert not name.is_absolute() and '..' not in name.parts
        file = ROOT
        for part in name.parts:
            file /= part
            assert not file.is_symlink()
        assert bind(file) == member
    return bind(p), len(members), sum(x['bytes'] for x in members)

swift, count, size = verify('verification/swift-cache-state-independent-review/implementation-review-2/correction-control-seal.json',
    '13b4e77974be545bb34274ddba68b6b3b159e8d2287390dcffff864373d136c5')
assert (count, size) == (1241, 118873096)
android, acount, asize = verify('verification/android-private-owner-independent-review/implementation-review-2/manifest.json',
    'f9f1b610a6a7bfb7918be64f27b19b95a44682348168407c5af079405ca289ab')
assert (acount, asize) == (464, 9232067)
base = ROOT / 'verification/swift-cache-state-independent-review/implementation-review-2'
public = json.loads((base / 'public-summary.json').read_bytes())
private = json.loads((base / 'private-guard-run-1/summary.json').read_bytes())
assert public['count'] == 39 and public['failures'] == 0
assert private['case_observations'] == private['passing_case_observations'] == 14
assert private['failing_case_observations'] == 0 and private['preflight_failure'] is None
for mode in private['modes']:
    assert mode['compile_succeeded'] and mode['run_succeeded'] and mode['protocol_failure'] is None
    assert len(mode['cases']) == 7
    for case in mode['cases']:
        assert len(case['observed_words']) == 32 and case['observed_words'] == case['expected_words']
        assert case['observed_shape'] == case['expected_shape'] and not case['differences']
assert not private['public_reachability_established'] and not private['candidate_harness_or_models_executed']
ar = json.loads((ROOT / 'verification/android-private-owner-independent-review/implementation-review-2/receipt.json').read_bytes())
assert ar['distinct_targeted_controls'] == 14 and ar['distinct_controls_passed'] == 13
assert ar['confirmed_product_boundary_failures'] == 1 and ar['reviewer_setup_failures_retained'] == 2
assert not ar['full_site_matrix_complete'] and not ar['implementation_accepted']
receipt = {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'command': sys.argv, 'python': sys.version, 'script': bind(Path(__file__)),
    'status': 'independent-correction-controls-pass-accounting-and-full-qualification-open',
    'swift_control_seal': swift, 'swift_members_verified': count, 'swift_bytes_verified': size,
    'public_File_basics_passed': 39, 'API_expected_dispositions': 15,
    'private_guard_cases_per_mode': 7, 'private_guard_modes': 2, 'private_guard_all32_matches': 14,
    'resolved_scope': 'Previously reproduced Q9/Q10 private guard defects only; public from-empty reachability not inferred.',
    'android_rejected_review_seal': android, 'android_members_verified': acount, 'android_bytes_verified': asize,
    'android_distinct_controls': 14, 'android_passing_controls': 13, 'android_product_failures': 1,
    'android_reviewer_setup_failures_preserved': 2,
    'source_accounting_lifetime_and_full_matrices_accepted': False,
    'implementation_accepted': False, 'native_runtime_or_capture_started': False, 'GA_qualified': False,
}
path = OUT / 'guard-correction-control-results.json'
assert not path.exists()
path.write_text(json.dumps(receipt, indent=2) + '\n')
for filename, key in [('work-graph.json', 'packages'), ('gates/ga.json', 'gates')]:
    p = ROOT / filename
    data = json.loads(p.read_bytes())
    row = next(x['fixtureCacheStateContractCandidate'] for x in data[key] if 'fixtureCacheStateContractCandidate' in x)
    row['status'] = 'guard-correction-independent-controls-pass-source-accounting-and-full-matrices-open'
    row['guard_correction']['status'] = '39-public-15-API-14-private-observations-pass-accounting-open'
    row['guard_correction']['independent_control_results'] = bind(path)
    a = next(x['privateOwnerEffectContractCandidate'] for x in data[key] if 'privateOwnerEffectContractCandidate' in x)
    a['frozen_candidate3']['independent_review_manifest'] = android
    p.write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps(bind(path)))
