"""Verify immutable producer custody and admit bounded independent public review."""
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PREFIX = 'verification/swift-cache-state-implementation/'
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
        current = current / part
        assert not current.is_symlink(), str(current)
    assert stat.S_ISREG(current.lstat().st_mode)
    return current

def verify_seal(path, expected, prefix, document):
    assert sha(path) == expected
    data = json.loads(path.read_bytes())
    seen = set()
    for member in data['members']:
        name = member['path']
        assert name.startswith(prefix) or name == document, name
        assert name not in seen
        seen.add(name)
        item = bind(safe(name))
        assert item == member, (name, item, member)
    assert len(seen) == data['member_count']
    assert sum(m['bytes'] for m in data['members']) == data['member_bytes']
    return data, seen

seal_name, expected = sys.argv[1:]
assert seal_name.startswith(PREFIX) and seal_name.endswith('.json')
seal_path = safe(seal_name)
candidate, seen = verify_seal(seal_path, expected, PREFIX, 'docs/swift-cache-state-implementation.md')
actual = {p.relative_to(ROOT).as_posix() for p in PRODUCER.rglob('*') if p.is_file()}
actual.add('docs/swift-cache-state-implementation.md')
assert actual == seen | {seal_name}, sorted(actual ^ (seen | {seal_name}))
for m in candidate['members']:
    p = ROOT / m['path']
    assert p.suffix not in ('.rlib', '.pyc')
    with p.open('rb') as f:
        assert f.read(4) not in (b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\x7fELF'), str(p)

upstream = {
    'combined-contract-acceptance.json': 'aac275052af88c802b0594c2d47318898d383b90f20d99a3914a4080c1a76dcc',
    'implementation-selection.json': '012ef007459aa8561da2f3542902b6f4193c8ac06c5c325944502042103acad3',
    'public-getter-selection.json': '80b8b39365e137f5f4db13f8a8348ca79aa17eb5abadf58ac929e3d25aec92e1',
    'execution-preparation-acceptance.json': 'e116b5e77c5f2c0c3b1704f1864b45fdca1558d027e59fb41c7384890b286018',
}
for name, digest in upstream.items():
    assert sha(OUT / name) == digest
preaccess_sha = '1cc596fe2a49f082701f2130bccfe8a427054071227e7655d15850e9978b3d1c'
preparation_sha = '07ff2daf1527fa459f68a4056b749ef71282b98f5b5a4ea634ba9ef19dae5ad6'
reviewer = ROOT / 'verification/swift-cache-state-independent-review'
preaccess, _ = verify_seal(reviewer / 'preaccess/seal.json', preaccess_sha,
    'verification/swift-cache-state-independent-review/preaccess/', 'docs/swift-cache-state-implementation-review-plan.md')
preparation, _ = verify_seal(reviewer / 'execution-preparation/seal.json', preparation_sha,
    'verification/swift-cache-state-independent-review/execution-preparation/', 'docs/swift-cache-state-execution-review-preparation.md')
handoff = json.loads((PRODUCER / 'handoff-final.json').read_bytes())
validation = json.loads((PRODUCER / 'evidence/final-validation.json').read_bytes())
actual_sources = {p.relative_to(PRODUCER).as_posix(): sha(p) for p in (PRODUCER / 'source').rglob('*') if p.is_file()}
assert actual_sources == validation['source_sha256']
source_digest = hashlib.sha256(json.dumps(actual_sources, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
assert source_digest == handoff['source_tree_digest']
assert validation['all_commands_passed'] and validation['unique_methods_per_mode'] == 114
assert not validation['independent_candidate_acceptance'] and not validation['GA_qualified']
classification = json.loads((PRODUCER / 'evidence/final-case-classification.json').read_bytes())
for mode in ('debug', 'optimized'):
    expected_counts = {'final_public_four_File': 29, 'final_private_injected_fault': 2, 'preliminary_zero_final_credit': 2}
    assert classification['counts'][mode] == expected_counts == handoff['final_actual_File_counts_per_mode'][mode]
    rows = [r for r in classification['cases'] if '/' + mode + '/' in r['case']]
    assert {k: sum(r['effective_scope'] == k for r in rows) for k in expected_counts} == expected_counts
    for row in rows:
        assert sha(PRODUCER / row['case'] / 'result.txt') == row['result_sha256']
        within = row['final_command_started'] <= row['input_mtime_epoch'] <= row['final_command_ended']
        assert within == row['final_run_credit']
        if within:
            assert row['final_source_sha256'] == actual_sources
        else:
            assert row['effective_scope'] == 'preliminary_zero_final_credit'
obligations = json.loads((PRODUCER / 'proofs/obligation-dispositions.json').read_bytes())
assert obligations['count'] == 35
assert {o['id'] for o in obligations['obligations']} == {f'P{i:02}' for i in range(1, 36)}
assert all(not o['independent_accepted'] for o in obligations['obligations'])
for o in obligations['obligations']:
    for path in o['evidence']:
        assert PREFIX + path in seen
cleanup = json.loads((PRODUCER / 'evidence/final-cleanup.json').read_bytes())
assert cleanup['all_corrected_runner_started_parents_have_observed_terminal_exits']
assert cleanup['no_build_products_or_bytecode_in_closure'] and cleanup['no_owned_scratch_retained']
assert cleanup['prior_unobserved_orphan_exit_remains_disappearance_only']

compiler = Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc')
assert sha(compiler) == 'dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0'
version_argv = [str(compiler), '--version', '--verbose']
version = subprocess.run(version_argv, capture_output=True, cwd=ROOT, timeout=15)
assert version.returncode == 0
sources = [PREFIX + 'source/library/' + name for name in ('analyzer.rs', 'envelope.rs', 'cache_state.rs')]
assert all(name in seen for name in sources)
for name in sources:
    assert sha(ROOT / name) == handoff['library_sha256'][name.removeprefix(PREFIX)]

admission = {
    'schema': 1, 'status': 'admitted-independent-cache-state-execution',
    'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'command': sys.argv,
    'python': sys.version, 'script_sha256': sha(Path(__file__)),
    'context_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'preaccess_seal_sha256': preaccess_sha,
    'getter_selection_sha256': upstream['public-getter-selection.json'],
    'reviewer_preparation_sha256': preparation_sha,
    'candidate_seal': seal_name, 'candidate_seal_sha256': expected,
    'candidate_members_verified': candidate['member_count'], 'candidate_bytes_verified': candidate['member_bytes'],
    'source_tree_digest': source_digest, 'crate_entry': sources[0], 'source_members': sources,
    'edition': '2021', 'rustc': str(compiler), 'rustc_sha256': sha(compiler),
    'rustc_version': version.stdout.decode(),
    'compiler_command': {'argv': version_argv, 'exit': version.returncode, 'stdout_sha256': hashlib.sha256(version.stdout).hexdigest(), 'stderr_sha256': hashlib.sha256(version.stderr).hexdigest()},
    'review_output_directory': 'verification/swift-cache-state-independent-review/implementation-review-1',
    'selected_case_set': 'basics', 'selected_start': 0, 'selected_count': 39,
    'scope': 'Exact source review P01-P35, sealed independent public four-File basics and API controls only; producer harness/model not imported or executed.',
    'private_execution_authorized': False,
    'private_next_step': 'Propose separately frozen test glue and actual source mapping before private runtime admission.',
    'producer_reported_unique_methods_per_mode': 114, 'producer_new_methods_per_mode': 22,
    'producer_actual_File_case_counts_per_mode': classification['counts'],
    'artifact_classification': bind(PRODUCER / 'evidence/final-case-classification.json'),
    'producer_evidence_is_independent_acceptance': False,
    'source_proof_inventory': 35, 'source_proofs_accepted': False,
    'three_partial_paid_exclusions_runtime_pass_credit': 0,
    'implementation_accepted': False, 'fullReplayAccepted': False, 'storedPrefixValidated': False,
    'semanticMetricsValid': False, 'realBindingVerified': False,
    'native_runtime_or_capture_started': False, 'GA_qualified': False,
}
output = OUT / 'candidate-public-review-admission.json'
assert not output.exists()
output.write_text(json.dumps(admission, indent=2) + '\n')
print(json.dumps(bind(output)))
