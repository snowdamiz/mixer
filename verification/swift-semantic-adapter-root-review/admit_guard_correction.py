"""Verify the immutable guard-only correction and admit exact independent replays."""
import datetime
import difflib
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PREFIX = 'verification/swift-cache-state-implementation/correction-1/'
PRODUCER = ROOT / PREFIX

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def bind(path):
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)}

def safe(name):
    p = PurePosixPath(name)
    assert not p.is_absolute() and '..' not in p.parts and '\\' not in name
    current = ROOT
    for part in p.parts:
        current /= part
        assert not current.is_symlink()
    assert stat.S_ISREG(current.lstat().st_mode)
    return current

def verify(name, digest, prefix, documents=()):
    path = safe(name)
    assert sha(path) == digest
    data = json.loads(path.read_bytes())
    seen = set()
    for member in data['members']:
        name = member['path']
        assert name.startswith(prefix) or name in documents, name
        assert name not in seen
        seen.add(name)
        assert bind(safe(name)) == member, name
    assert len(seen) == data['member_count']
    assert sum(m['bytes'] for m in data['members']) == data['member_bytes']
    return data, seen

candidate_name = PREFIX + 'candidate-repo-seal.json'
candidate_sha = 'b141dab4e6c1ecc00bd4dc50a84852ae07b31438bc0126cc724e4b47fbb8f7a6'
candidate, seen = verify(candidate_name, candidate_sha, PREFIX)
assert {p.relative_to(ROOT).as_posix() for p in PRODUCER.rglob('*') if p.is_file()} == seen | {candidate_name}
for member in candidate['members']:
    p = ROOT / member['path']
    assert p.suffix not in ('.rlib', '.pyc', '.rmeta')
    with p.open('rb') as f:
        assert f.read(4) not in (b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\x7fELF')
original, _ = verify('verification/swift-cache-state-implementation/candidate-repo-seal.json',
    'caceb9db9263de46ed876ff109f34eacb8fe13a9bd3ac47758f2bdac5c693ad3',
    'verification/swift-cache-state-implementation/', ('docs/swift-cache-state-implementation.md',))
review_name = 'verification/swift-cache-state-independent-review/implementation-review-1/review-seal.json'
review_sha = '3c189178c6c8cef3fa2236bbe9d3d0c8cb2806fc4afcf9940bdc7af67a444382'
review, _ = verify(review_name, review_sha,
    'verification/swift-cache-state-independent-review/implementation-review-1/', ('docs/swift-cache-state-implementation-review.md',))
for name, digest, document in [
    ('preaccess', '1cc596fe2a49f082701f2130bccfe8a427054071227e7655d15850e9978b3d1c', 'docs/swift-cache-state-implementation-review-plan.md'),
    ('execution-preparation', '07ff2daf1527fa459f68a4056b749ef71282b98f5b5a4ea634ba9ef19dae5ad6', 'docs/swift-cache-state-execution-review-preparation.md'),
]:
    prefix = 'verification/swift-cache-state-independent-review/' + name + '/'
    verify(prefix + 'seal.json', digest, prefix, (document,))

handoff = json.loads((PRODUCER / 'handoff.json').read_bytes())
validation = json.loads((PRODUCER / 'evidence/final-validation.json').read_bytes())
sources = {p.relative_to(PRODUCER).as_posix(): sha(p) for p in (PRODUCER / 'source').rglob('*') if p.is_file()}
assert sources == validation['source_sha256']
source_digest = hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
assert source_digest == handoff['source_tree_digest'] == candidate['source_tree_digest']
assert sha(OUT / 'guard-correction-selection.json') == handoff['selection_sha256'] == candidate['selection_sha256']
assert validation['all_command_dispositions_as_expected'] and validation['unique_methods_per_mode'] == 119
assert validation['api_dispositions_per_mode'] == 25 and validation['api_modes'] == ['debug', 'optimized']
assert not validation['independent_candidate_acceptance'] and not validation['GA_qualified']
catalog = json.loads((PRODUCER / 'evidence/case-catalog.json').read_bytes())
assert len(catalog['cases']) == 124
assert sum(r['final_source_credit'] for r in catalog['cases']) == 62
for mode in ('debug', 'optimized'):
    assert catalog['counts_per_mode'][mode] == handoff['actual_File_counts_per_mode'][mode] == {'final_public_four_File': 29, 'final_private_injected_fault': 2}
for row in catalog['cases']:
    assert sha(PRODUCER / row['case'] / 'result.txt') == row['result_sha256']
    if row['final_source_credit']:
        assert row['final_command_started'] <= row['input_mtime_epoch'] <= row['final_command_ended']
    else:
        assert row['scope'] == 'prior_attempt_zero_final_command_credit' and not row['public_reachability_credit']
    for f in row['files']:
        p = safe(f['content_path'])
        assert p.stat().st_size == f['bytes'] and sha(p) == f['sha256']
cleanup = json.loads((PRODUCER / 'evidence/final-cleanup.json').read_bytes())
assert cleanup['all_started_parents_observed_terminal'] and cleanup['no_build_products_or_scratch_retained']
assert cleanup['no_process_inventory_performed'] and not cleanup['native_runtime_or_capture_started']
original_lib = ROOT / 'verification/swift-cache-state-implementation/source/library'
new_lib = PRODUCER / 'source/library'
for name in ('analyzer.rs', 'envelope.rs'):
    assert (original_lib / name).read_bytes() == (new_lib / name).read_bytes()
before = (original_lib / 'cache_state.rs').read_text()
after = (new_lib / 'cache_state.rs').read_text()
delta_text = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='original/cache_state.rs', tofile='correction-1/cache_state.rs'))
diff_path = OUT / 'guard-correction-production.diff'
assert not diff_path.exists()
diff_path.write_text(delta_text)

original_admission = OUT / 'candidate-public-review-admission.json'
assert sha(original_admission) == 'c238edff3f5ef05a770640a0f67b2d748e6e95108dfe00d93e7d890e42333df0'
public = json.loads(original_admission.read_bytes())
compiler = Path(public['rustc'])
assert sha(compiler) == public['rustc_sha256']
version = subprocess.run([str(compiler), '--version', '--verbose'], cwd=ROOT, capture_output=True, timeout=15)
assert version.returncode == 0 and version.stdout.decode() == public['rustc_version']
public.update({
    'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'command': sys.argv,
    'python': sys.version, 'script_sha256': sha(Path(__file__)),
    'context_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'candidate_seal': candidate_name, 'candidate_seal_sha256': candidate_sha,
    'candidate_members_verified': candidate['member_count'], 'candidate_bytes_verified': candidate['member_bytes'],
    'original_candidate_members_unchanged': original['member_count'],
    'prior_review_seal': review_name, 'prior_review_seal_sha256': review_sha,
    'prior_review_members_verified': review['member_count'], 'prior_review_bytes_verified': review['member_bytes'],
    'source_tree_digest': source_digest,
    'crate_entry': PREFIX + 'source/library/analyzer.rs',
    'source_members': [PREFIX + 'source/library/' + n for n in ('analyzer.rs', 'envelope.rs', 'cache_state.rs')],
    'review_output_directory': 'verification/swift-cache-state-independent-review/implementation-review-2',
    'producer_reported_unique_methods_per_mode': 119, 'producer_new_methods_per_mode': 27,
    'producer_actual_File_case_counts_per_mode': catalog['counts_per_mode'],
    'artifact_classification': bind(PRODUCER / 'evidence/case-catalog.json'),
    'production_diff': bind(diff_path),
    'private_next_step': 'Seven exact previously frozen witnesses separately readmitted below; other private/bulk execution requires separately frozen admission.',
    'accounting_and_lifetime_status': 'Unresolved detailed source proof requests retained; no numeric overrun inferred and no bound accepted.',
    'preliminary_product_hash_limitation': cleanup['preliminary_binary_hash_limitation'],
    'root_preflight_correction': 'First root check expected62 total catalog rows and refused before any admission/compilation. Catalog actually preserves62 prior-attempt rows with zero final-source credit plus62 current rows. Both sets are now hash-verified; only the latter receive final-source credit.',
})
output = OUT / 'guard-correction-public-review-admission.json'
assert not output.exists()
output.write_text(json.dumps(public, indent=2) + '\n')

old_private_path = OUT / 'private-guard-review-admission.json'
assert sha(old_private_path) == 'd52cb249fff84ed893e0f919cefff9095288a725ada60fa06db64743e893a586'
private = json.loads(old_private_path.read_bytes())
proposal = ROOT / 'verification/swift-cache-state-independent-review/implementation-review-1/private-guard-proposal'
delta = json.loads((proposal / 'delta.json').read_bytes())
transformed = {}
for name, addition in delta['append_only_utf8'].items():
    raw = (new_lib / name).read_bytes() + addition.encode()
    transformed[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
assert sha(proposal / delta['additional_file']) == private['glue_source_sha256']
private.update({
    'at': public['at'], 'command': sys.argv, 'python': sys.version, 'script_sha256': sha(Path(__file__)),
    'public_admission_sha256': sha(output), 'candidate_seal': candidate_name, 'candidate_seal_sha256': candidate_sha,
    'transformed_source_hashes': transformed,
    'output_directory': 'verification/swift-cache-state-independent-review/implementation-review-2/private-guard-run-1',
    'source_rebinding': 'Apply unchanged append-only delta and unchanged seven full32 expectations to the three newly admitted source members. Original delta baseline hashes describe original candidate; this admission supplies corrected source and transformed hashes.',
})
private_output = OUT / 'guard-correction-private-review-admission.json'
assert not private_output.exists()
private_output.write_text(json.dumps(private, indent=2) + '\n')
for filename, key in [('work-graph.json', 'packages'), ('gates/ga.json', 'gates')]:
    p = ROOT / filename
    data = json.loads(p.read_bytes())
    row = next(x['fixtureCacheStateContractCandidate'] for x in data[key] if 'fixtureCacheStateContractCandidate' in x)
    row['status'] = 'guard-correction-frozen-root-custody-verified-independent-replay-admitted-accounting-open'
    row['guard_correction'].update({
        'status': 'frozen-admitted-independent-review',
        'candidate_seal': candidate_name, 'candidate_seal_sha256': candidate_sha,
        'members': candidate['member_count'], 'bytes': candidate['member_bytes'],
        'public_admission': bind(output), 'private_admission': bind(private_output),
        'producer_unique_methods_per_mode': 119, 'producer_API_dispositions_per_mode': 25,
        'producer_private_full32_cases_per_mode': 4337, 'public_reachability_credit_for_private_cases': 0,
        'independent_initial_review': {'path': review_name, 'sha256': review_sha, 'members': 899, 'bytes': 118848277},
        'source_accounting_and_lifetime_accepted': False,
    })
    p.write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps({'public': bind(output), 'private': bind(private_output), 'production_diff': bind(diff_path)}))
