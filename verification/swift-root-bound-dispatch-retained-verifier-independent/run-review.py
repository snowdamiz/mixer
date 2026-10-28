"""One bounded independent pure-Python run. No external children or actual facts."""
from pathlib import Path
import ast
import hashlib
import io
import json
import signal
import sys
import time
import unittest

signal.alarm(55)
started = time.monotonic()
owned = Path(__file__).resolve().parent
root = owned.parents[1]
producer = root / 'verification/swift-root-bound-dispatch-retained-verifier-v1'
v2 = root / 'verification/swift-root-bound-dispatch-physical-evidence-v2'
retained = root / 'verification/swift-root-bound-dispatch-retained-capture-v1'
expected_seal = '8abb6802e73f98982bf863b16175617ca770a72e264364084aa8fa1c84226ee7'
expected_source = '8c8978b167f5d08bac12b51e33f5215f1d703e4860f05981d5d6ad988dac7279'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


seal_raw = (producer / 'freeze/seal.json').read_bytes()
assert sha(seal_raw) == expected_seal
seal = json.loads(seal_raw)
inputs = [producer / 'freeze/seal.json', *[producer / m['path'] for m in seal['members']],
          v2 / 'source/region_certificate.py', v2 / 'source/tests_region_certificate.py',
          v2 / 'input-manifest.json', v2 / 'seal.json',
          retained / 'plan.json', retained / 'base-capture-plan.json',
          retained / 'runtime/capture-observation.json',
          root / 'verification/swift-semantic-adapter-root-review/dispatch-retained-physical-identity-acceptance.json',
          *sorted((owned / 'source').glob('*.py')), Path(__file__), Path(sys.executable)]


def pins():
    rows = []
    for path in inputs:
        raw = path.read_bytes()
        rows.append({'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)})
    return rows


before = pins()
members = []
for member in seal['members']:
    raw = (producer / member['path']).read_bytes()
    assert len(raw) == member['bytes'] and sha(raw) == member['sha256']
    members.append(member)
assert len(members) == seal['member_count'] == 16
assert sum(m['bytes'] for m in members) == seal['member_bytes']
assert sha(canonical(members)) == seal['tree_sha256']
source_members = [m for m in members if m['path'].startswith('source/')]
assert sha(canonical(source_members)) == expected_source == seal['source_tree_sha256']
for name in ('region_certificate.py', 'tests_region_certificate.py', 'tests_retained_binding.py'):
    assert (owned / 'source' / name).read_bytes() == (producer / 'source' / name).read_bytes()


def function_bytes(path, name):
    raw = path.read_bytes()
    lines = raw.splitlines(keepends=True)
    nodes = [node for node in ast.walk(ast.parse(raw))
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
    assert len(nodes) == 1
    node = nodes[0]
    return b''.join(lines[node.lineno - 1:node.end_lineno])


geometry = function_bytes(producer / 'source/region_certificate.py', 'geometry')
assert geometry == function_bytes(v2 / 'source/region_certificate.py', 'geometry')
test_raw = (producer / 'source/tests_region_certificate.py').read_bytes()
test_nodes = [node for node in ast.walk(ast.parse(test_raw))
              if isinstance(node, ast.FunctionDef) and node.name.startswith('test_p')]
assert len(test_nodes) == 16
test_bodies = []
for node in sorted(test_nodes, key=lambda x: x.name):
    raw = function_bytes(producer / 'source/tests_region_certificate.py', node.name)
    assert raw == function_bytes(v2 / 'source/tests_region_certificate.py', node.name)
    test_bodies.append(raw)
static = {
    'schema': 1, 'candidate_seal_sha256': expected_seal,
    'candidate_member_count': len(members), 'candidate_members_verified': True,
    'candidate_source_tree_sha256': expected_source,
    'geometry_byte_identical_to_v2': True, 'geometry_bytes': len(geometry),
    'geometry_sha256': sha(geometry), 'P01_P16_count': len(test_bodies),
    'P01_P16_test_bodies_byte_identical_to_v2': True,
    'P01_P16_test_bodies_sha256': sha(b''.join(test_bodies)),
    'producer_precursor_pass_preserved': json.loads((producer / 'freeze/attempt-1/host-controls.json').read_bytes())['status'] == 'PASS_SYNTHETIC_HOST_CONTROLS',
    'producer_final_pass_preserved': json.loads((producer / 'freeze/host-controls.json').read_bytes())['status'] == 'PASS_SYNTHETIC_HOST_CONTROLS',
    'own_source_copies_byte_identical_to_candidate': True,
    'actual_capture_metadata_only': True, 'actual_geometry_inputs_read_or_executed': 0,
}

scratch = owned / 'command'
assert not scratch.exists()
scratch.mkdir()
sys.path.insert(0, str(owned / 'source'))
stream = io.StringIO()
suite = unittest.defaultTestLoader.discover(str(owned / 'source'), pattern='tests_*.py')
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
output = stream.getvalue()
assert len(output.encode()) <= 1024 * 1024
after = pins()
remaining = sorted(str(path.relative_to(scratch)) for path in scratch.rglob('*'))
if not remaining:
    scratch.rmdir()
elapsed = time.monotonic() - started
import tests_independent
receipt = {
    'schema': 1, 'status': 'PASS_INDEPENDENT_SYNTHETIC_REVIEW' if result.wasSuccessful() else 'FAIL_INDEPENDENT_SYNTHETIC_REVIEW',
    'command': [str(Path(sys.executable)), '-B', str(Path(__file__))],
    'wall_seconds_bound': 55, 'elapsed_seconds': elapsed, 'automatic_retries': 0,
    'python_version_from_prior_pinned_plan_receipt': json.loads((retained / 'plan.json').read_bytes())['python_version_from_this_preparation'],
    'new_version_or_process_queries': 0, 'external_children': 0,
    'compiler_invocations': 0, 'native_runtime_invocations': 0,
    'actual_geometry_input_invocations': 0, 'actual_geometry_inputs_read': 0,
    'candidate_control_methods': 23, 'fresh_independent_methods': 9,
    'test_methods_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
    'skipped': len(result.skipped), 'fresh_scope_checked_verifier_results': tests_independent.RESULTS_CHECKED,
    'before': before, 'after': after, 'pins_unchanged': before == after,
    'owned_synthetic_scratch_removed': not scratch.exists(), 'scratch_remaining': remaining,
    'link_dead_code': True, 'alternate_diagnostic_configuration_only': True,
    'original_capture_qualified': False, 'runtime_admission_accepted': False,
    'local_geometry_only': True, 'complete_capacity_accepted': False,
    'findings': [],
    'synthetic_boundary': 'Absent root approval still permits explicitly synthetic hypothetical geometry after review/seal shape and scope checks; status/hash/target review joins require approval. This confers no actual authority.',
    'limitations': [
        'Metadata-only alignment is not an invocation on actual capture/geometry facts.',
        'No semantic-map review, actual certificate selection, approval construction or actual-input release.',
        'No physical backing/destruction, complete capacity, root funding, runtime admission, canonical integration, FieldLog, OTA or GA acceptance.',
        'Native/UI and local-custody Unit A holds remain in force.',
    ],
}
(owned / 'input-manifest.json').write_bytes(canonical({'schema': 1, 'inputs': before}) + b'\n')
(owned / 'static-review.json').write_text(json.dumps(static, sort_keys=True, indent=2) + '\n')
(owned / 'host-controls.stdout').write_text(output)
(owned / 'host-controls.stderr').write_text('')
(owned / 'review.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
sys.stdout.write(output)
print(json.dumps({k: receipt[k] for k in ('status', 'elapsed_seconds', 'test_methods_run',
      'fresh_scope_checked_verifier_results', 'failures', 'errors', 'pins_unchanged',
      'owned_synthetic_scratch_removed')}))
assert before == after
assert not remaining and not scratch.exists()
assert elapsed < 55
sys.exit(0 if result.wasSuccessful() else 1)
