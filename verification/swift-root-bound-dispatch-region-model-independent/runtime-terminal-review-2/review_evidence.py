#!/usr/bin/env python3
"""Review saved host receipts/streams and custody only; never rerun model or probes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time

D = Path(__file__).resolve().parent
R = D.parents[2]
Q = R / 'verification/swift-semantic-adapter-root-review'
L = R / 'verification/swift-root-bound-dispatch-region-model-v2'
T = Q / 'dispatch-region-model-v4-runtime'
started = time.monotonic()
inputs, paths = {}, {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def pairs(items):
    result = {}
    for key, value in items:
        assert key not in result
        result[key] = value
    return result


def observe(path):
    assert time.monotonic() - started < 55
    assert path.is_file() and not path.is_symlink(), path
    digest, size = hashlib.sha256(), 0
    with path.open('rb') as stream:
        while chunk := stream.read(262144):
            assert time.monotonic() - started < 55
            size += len(chunk)
            digest.update(chunk)
    return {'bytes': size, 'sha256': digest.hexdigest()}


def pin(row, base=R):
    path = base / row['path']
    actual = observe(path)
    assert actual == {key: row[key] for key in ('bytes', 'sha256')}, path
    key = str(path.relative_to(R)) if path.is_relative_to(R) else str(path)
    assert key not in inputs or inputs[key] == actual
    inputs[key], paths[key] = actual, path


def read(path, expected=None):
    raw = path.read_bytes()
    assert len(raw) <= 1048576
    if expected is not None:
        assert sha(raw) == expected
    pin({'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)})
    return raw


def load(path, expected=None):
    return json.loads(read(path, expected), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


source_review = D.parent / 'runtime-controller-review-v4'
review_seal = load(source_review / 'seal.json', 'eef2f143c2664fb644e0e9571d80d964037e2d5f86e3b9c0fee842a1e7b818b3')
for row in review_seal['members']:
    pin(row, source_review)
for name, row in load(source_review / 'checked-inputs.json').items():
    pin({'path': name, **row})
release = load(Q / 'dispatch-region-model-v4-host-release.json', 'a56971cf26a81c5a871b95cd8b4e756845f1e56d88e816f81992e35cf4fbf9f1')
plan_path = Q / 'dispatch-region-model-v4-host-plan.json'
plan = load(plan_path, '4e2959b148ec1ef4a48e708076ac28be2951b633ef5400c4d1be65cd7f8bec8a')
controller_path = Q / 'run-dispatch-region-model-v4.py'
assert sha(read(controller_path)) == release['controller_sha256'] == 'bc0806b2307ea2180cc7f99cac8cb30481a4077fec854154aea222ad351074ab'
assert release['plan_sha256'] == sha(plan_path.read_bytes())
assert release['compiler_invocations'] == release['host_test_invocations'] == 1 and release['automatic_retries'] == 0
assert release['model_only'] is True and release['product_or_GA_accepted'] is False
for row in release['independent_reviews'] + [release['source_seal']]:
    pin(row)
receipt = load(T / 'receipt.json')
obs_raw = read(T / 'observations.json', receipt['observations_sha256'])
obs = json.loads(obs_raw, object_pairs_hook=pairs)
assert sha(obs_raw) == '0bfde494f9042102833271c1300bc24d2262f02b91a171be02e256a572455ec3'
assert receipt['status'] == 'passed' and receipt['plan_sha256'] == obs['plan_sha256'] == release['plan_sha256']
assert receipt['model_only'] is True and obs['model_only'] is True
assert receipt['product_physical_funding_or_GA_acceptance'] is False
assert receipt['observed_signals'] == [] and receipt['signal_cutoff_seconds'] < 53.5 < plan['bounds']['wall_seconds']
assert obs['errors'] == [] and obs['tests_passed'] == 24
assert obs['owned_groups_closed'] is True and obs['generated_directory_removed'] is True
assert obs['all_pins_rechecked'] is True and obs['source_files'] == plan['source_files']
assert obs['compiler_version'] == plan['compiler_version_from_prior_receipt']

# Independently reconstruct the finite runtime input roster, without calling any
# controller function. Its historical hashes are reported by reviewed code;
# current values are independently rechecked here.
sealed = load(L / 'seal.json', release['source_seal']['sha256'])
member_rows = {row['path']: row for row in sealed['members']}
manifest = load(L / 'input-manifest.json', member_rows['input-manifest.json']['sha256'])
roster = load(L / 'test-family-map.json', member_rows['test-family-map.json']['sha256'])
runtime_pins = {}


def runtime_pin(row, base=R):
    path = base / row['path']
    key = str(path)
    actual = {field: row[field] for field in ('bytes', 'sha256')}
    assert key not in runtime_pins or runtime_pins[key] == actual
    runtime_pins[key] = actual
    pin(row, base)


for row in manifest['inputs'] + plan['source_files']:
    runtime_pin(row)
runtime_pin({'path': str(plan_path), **inputs[str(plan_path.relative_to(R))]})
runtime_pin(release['source_seal'])
for row in sealed['members']:
    runtime_pin(row, L)
runtime_pin({'path': str(controller_path), **inputs[str(controller_path.relative_to(R))]})
for key in ('compiler', 'linker_driver', 'link_editor', 'compiler_manifest', 'SDK_manifest'):
    runtime_pin(plan[key])
toolchain = load(R / plan['compiler_manifest']['path'], plan['compiler_manifest']['sha256'])
for row in toolchain['members']:
    runtime_pin(row, Path(toolchain['root']))
sdk = load(R / plan['SDK_manifest']['path'], plan['SDK_manifest']['sha256'])
for row in sdk['settings']:
    runtime_pin(row)
assert len(runtime_pins) == obs['pins'] == 117

assert len(obs['commands']) == 2
assert [row['kind'] for row in obs['commands']] == ['compile', 'host-tests']
streams = {}
for index, record in enumerate(obs['commands']):
    assert record['argv'] == plan['commands'][index]['argv']
    assert record['environment'] == plan['environment'] and record['cwd'] == plan['cwd'] == str(R)
    assert record['returncode'] == plan['commands'][index]['expected_exit'] == 0
    assert record['pid'] == record['pgid'] == record['sid']
    assert record['custody'] is True and record['reaped'] is True and record['group_absent'] is True
    assert record['cleanup_path'] == 'completed-child-no-signals'
    assert record.get('signals', []) == [] and record.get('syscall_errors', []) == []
    assert record.get('permission_refusal', False) is False
    completed = record['completion_observation']
    assert completed['pid'] == record['pid'] and completed['code'] == 1 and completed['status'] == 0
    assert record['start_seconds'] < record['end_seconds'] < (30 if index == 0 else 45)
    for field, cap in [('stdout', 262144), ('stderr', 524288)]:
        row = record[field]
        data = read(T / row['file'], row['sha256'])
        assert len(data) == row['bytes'] <= cap
        streams[(record['kind'], field)] = data
assert obs['commands'][0]['end_seconds'] < obs['commands'][1]['start_seconds']
assert len({record['pid'] for record in obs['commands']}) == 2
assert streams[('compile', 'stdout')] == streams[('compile', 'stderr')] == streams[('host-tests', 'stderr')] == b''
output = streams[('host-tests', 'stdout')].decode('utf-8')
expected = ['tests::' + row['rust_test'] for row in roster['families']]
actual = re.findall(r'^test (\S+) \.\.\. ok$', output, re.M)
assert len(expected) == len(set(expected)) == len(actual) == len(set(actual)) == 24
assert set(actual) == set(expected)
assert output.count('running 24 tests') == 1
assert len(re.findall(r'^test result: ok\. 24 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in [0-9.]+s$', output, re.M)) == 1
assert not re.search(r'^test \S+ \.\.\. (?!ok$)', output, re.M)

generated = [{'path': 'model-tests', 'bytes': 2195320,
              'sha256': 'ca8b7433ce7a409a9e2e01944154f56511577b3b0586864498ad3446ea562514'}]
assert obs['generated_before'] == obs['generated_after'] == obs['generated'] == generated
assert obs['binary_sha256_before'] == obs['binary_sha256_after'] == generated[0]['sha256']
assert sum(row['bytes'] for row in generated) <= plan['bounds']['maximum_generated_bytes']
assert len(generated) <= plan['bounds']['maximum_generated_members']
try:
    Path(plan['owned_outputs']['directory']).lstat()
except FileNotFoundError:
    build_absent = True
else:
    build_absent = False
assert build_absent
previous = load(R / plan['previous_attempt']['receipt']['path'], plan['previous_attempt']['receipt']['sha256'])
later_cleanup = load(R / plan['previous_attempt']['later_cleanup']['path'], plan['previous_attempt']['later_cleanup']['sha256'])
assert previous['status'] == 'failed' and later_cleanup['compiler_exit_not_recorded'] is True and later_cleanup['tests_run'] == 0
implementation_path = R / 'verification/swift-root-bound-dispatch-lifetime-contract/IMPLEMENTATION.md'
implementation = read(implementation_path, '3909f11d54592604ad5c978d278c5e055af2ecdbac44d14689e107689301de99').decode()
assert 'permission to prepare the next narrow physical/capacity evidence plan' in implementation
assert 'not a\nfunding receipt' in implementation
after = {name: observe(path) for name, path in paths.items()}
assert after == inputs
report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'FROZEN_INDEPENDENT_TERMINAL_REVIEW_MODEL_ONLY_HOST_24_TEST_SLICE_ACCEPTABLE',
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(R))], 'cwd': str(R), 'python': sys.version,
    'python_tool': {'reported_path': sys.executable, 'resolved_path': str(Path(sys.executable).resolve()),
                    'sha256': sha(Path(sys.executable).resolve().read_bytes())},
    'review_script_sha256': sha(Path(__file__).read_bytes()),
    'root_release_sha256': inputs[str((Q / 'dispatch-region-model-v4-host-release.json').relative_to(R))]['sha256'],
    'controller_sha256': release['controller_sha256'], 'plan_sha256': release['plan_sha256'],
    'source146_binding': manifest['source146_contract_binding'], 'source_files': plan['source_files'],
    'compiler_version_from_prior_pinned_receipt': obs['compiler_version'],
    'runtime_input_roster_count': len(runtime_pins), 'runtime_input_roster_tree_sha256': sha(canonical(runtime_pins)),
    'reviewer_checked_input_count': len(inputs), 'reviewer_before_after_input_tree_sha256': sha(canonical(inputs)),
    'reviewer_before_after_custody_equal': True,
    'compile_commands': 1, 'compile_exit': 0, 'compiler_output_bytes': 0,
    'host_test_commands': 1, 'tests_passed': 24, 'failed_ignored_measured_filtered': 0,
    'expected_test_names': expected, 'observed_test_names': actual,
    'owned_child_pids': [record['pid'] for record in obs['commands']],
    'both_WNOWAIT_exit0_reaped_groups_absent_no_active_signals': True,
    'binary': generated[0], 'pre_post_final_generated_file_rows_equal': True, 'owned_build_directory_absent': True,
    'signal_cutoff_seconds': receipt['signal_cutoff_seconds'], 'observed_signals': [],
    'errors': [], 'historical_receipt_preserved_failed': True,
    'acceptance_recommended': 'ISOLATED_SYNTHETIC_HOST_MODEL_ONLY',
    'accepted_boundary': 'Exactly reviewed model/test source v2,oneDebug aarch64-apple-darwin rustc1.99 compile and24finite synthetic host tests under separately selected v4 controller/plan. Normal completed-child controller path observed twice with no active signals. No actual File/allocator/product dispatch/destruction path qualified.',
    'next_small_source_step': 'Prepare and review a separate narrow physical/capacity evidence plan for the dispatch return boundary:complete AdmittedReturn13624,Body frame and ChildWrap13640. Choose exact-toolchain region evidence or a reviewed implementation that makes storage explicit. Define required arena/offset/capacity/alignment/liveness/alias/backing evidence and fail-closed unknowns before authorizing another code slice.',
    'pending': ['Actual physical regions and complete backing upper bounds','Call/return/destruction frame capacity','Numeric work/storage prices and production whole quote','Root durable funding/custody','Product integration and real File/error/drop behavior','Native/device/FieldLog/OTA/GA'],
    'limits': ['This reviewer parsed saved evidence only;no compiler/controller/model/tests or process probes repeated.',
        'Historical runtime pin checks are reported by the reviewed executed controller;current values and exact finite117-pin roster independently rechecked.',
        'No old EPERM cause diagnosed;success observes the new normal-completion path,not failure/timeout/EPERM branch qualification.',
        'Same binary bytes as failed attempt do not supply the old missing exit/reap or test pass.',
        'ModelOnly remains mandatory for fitting Synthetic or ReviewedBound-looking hypotheses;selectors remain pending.',
        'Generated row equality concerns regular-file bytes;empty-directory identity is not asserted.'],
    'new_compiler_controller_model_runtime_test_version_native_UI_capture_phone_process_queries': 0,
    'canonical_product_metadata_commit_push_actions': 0,
    'physical_prices_grants_funding_ownership_product_GA_accepted': False,
    'cleanup': 'Original v4 controller records owned groups closed and generated directory removed;reviewer created no child/build artifact.',
    'elapsed_seconds': time.monotonic() - started}
assert report['elapsed_seconds'] < 55
for name, value in [('review-result.json', report), ('checked-inputs.json', inputs), ('runtime-input-roster.json', runtime_pins)]:
    with (D / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
print(json.dumps({key: report[key] for key in ('status', 'runtime_input_roster_count', 'reviewer_checked_input_count',
    'compile_exit', 'tests_passed', 'acceptance_recommended', 'elapsed_seconds')}))
