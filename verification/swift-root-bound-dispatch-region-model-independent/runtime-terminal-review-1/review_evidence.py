#!/usr/bin/env python3
"""Offline terminal evidence/source review. No process calls or model execution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

D = Path(__file__).resolve().parent
R = D.parents[2]
Q = R / 'verification/swift-semantic-adapter-root-review'
T = Q / 'dispatch-region-model-v2-runtime'
L = R / 'verification/swift-root-bound-dispatch-region-model-v2'
started = time.monotonic()
inputs = {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        assert key not in result
        result[key] = value
    return result


def read(path):
    assert time.monotonic() - started < 55
    raw = path.read_bytes()
    assert len(raw) < 1048576
    inputs[str(path.relative_to(R))] = {'bytes': len(raw), 'sha256': sha(raw)}
    return raw


def load(path):
    return json.loads(read(path), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


receipt = load(T / 'receipt.json')
observation_raw = read(T / 'observations.json')
assert sha(observation_raw) == receipt['observations_sha256'] == '129a6b079fa6853be17794577425375dce3c1079dcb18591821116067f5c49be'
observation = json.loads(observation_raw, object_pairs_hook=pairs)
absence = load(T / 'exact-owned-cleanup-check-1.json')
later = load(T / 'later-cleanup.json')
release = load(Q / 'dispatch-region-model-v2-host-release.json')
plan = load(L / 'host-test-plan.json')
assert inputs[str((L / 'host-test-plan.json').relative_to(R))]['sha256'] == '5a2950e97e714e3628546d9b73aa2918c72f23f1221c64806823f978dc2c32e8'
controller = read(Q / 'run-dispatch-region-model-v3.py')
assert sha(controller) == release['controller_sha256'] == '53b6386bf796716c259e4a9f4ff709c908dee8e3d2c4d5f5e34f93f54ee7af69'
assert receipt['plan_sha256'] == observation['plan_sha256'] == release['plan_sha256']
assert receipt['status'] == 'failed' and receipt['model_only'] is True
assert receipt['product_physical_funding_or_GA_acceptance'] is False
assert receipt['observed_signals'] == []
assert observation['owned_groups_closed'] is False
assert observation['generated_directory_removed'] is False
assert observation['all_pins_rechecked'] is True and observation['pins'] == 116
assert len(observation['commands']) == 1
command = observation['commands'][0]
assert command['kind'] == 'compile' and command['pid'] == command['pgid'] == command['sid'] == 89514
assert command['custody'] is True
assert command['argv'] == plan['commands'][0]['argv']
assert command['environment'] == plan['environment'] and command['cwd'] == str(R)
assert 'returncode' not in command and 'reaped' not in command and 'tests_passed' not in observation
for field in ('stdout', 'stderr'):
    row = command[field]
    raw = read(T / row['file'])
    assert len(raw) == row['bytes'] == 0 and sha(raw) == row['sha256']
assert observation['errors'] == ['PermissionError: [Errno 1] Operation not permitted',
                                 "cleanup: PermissionError(1, 'Operation not permitted')"]
generated = [{'path': 'model-tests', 'bytes': 2195320,
              'sha256': 'ca8b7433ce7a409a9e2e01944154f56511577b3b0586864498ad3446ea562514'}]
assert observation['generated'] == later['generated_files'] == generated
assert later['compiler_exit_not_recorded'] is True and later['tests_run'] == 0
assert later['original_failed_receipt_preserved'] is True and later['generated_directory_removed'] is True
assert later['absence_receipt'] == 'exact-owned-cleanup-check-1.json'
assert absence['leader_absent'] is True and absence['group_absent'] is True
build = Path(plan['owned_outputs']['directory'])
try:
    build.lstat()
except FileNotFoundError:
    build_absent = True
else:
    build_absent = False
assert build_absent
for row in plan['source_files']:
    raw = read(R / row['path'])
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
assert observation['source_files'] == plan['source_files']
source = controller.decode()
close = source[source.index('def close('):source.index('def command(')]
assert close.index('for sig, grace in') < close.index('while not exited(child)') < close.index('child.wait(timeout=0)')
assert 'record.get("custody")' in close
assert 'if not record.get("reaped") and exited(child):\n                if not close(record):' in source
# Source identifies candidate syscall sites, not the actual failing call.
assert all(token in source for token in ('os.waitid(', 'os.killpg(', 'os.getpgid(', 'os.getsid(', 'child.wait('))
before = dict(inputs)
for name, expected in before.items():
    raw = (R / name).read_bytes()
    assert {'bytes': len(raw), 'sha256': sha(raw)} == expected
report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'FROZEN_INDEPENDENT_FAILED_ATTEMPT_TERMINAL_REVIEW_NO_EXIT_OR_TEST_QUALIFICATION',
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(R))], 'cwd': str(R),
    'python': sys.version, 'review_script_sha256': sha(Path(__file__).read_bytes()),
    'python_tool': {'reported_path': sys.executable, 'resolved_path': str(Path(sys.executable).resolve()),
                    'sha256': sha(Path(sys.executable).resolve().read_bytes())},
    'input_hashes': inputs, 'before_after_custody_equal': True,
    'controller_sha256': sha(controller), 'plan_sha256': receipt['plan_sha256'],
    'source146_binding': '91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f',
    'original_result': 'FAILED_IMMUTABLE', 'recorded_compiler_invocations': 1, 'recorded_test_invocations': 0,
    'compiler_pid_pgid_sid': 89514,
    'recorded_command_interval_seconds': command['end_seconds'] - command['start_seconds'],
    'original_exit_or_reap_result_recorded': False,
    'generated_artifact': generated[0], 'compiler_success_accepted': False, 'tests_passed_accepted': False,
    'original_owned_group_closure_accepted': False,
    'later_absence_and_bounded_generated_removal_receipts_consistent': True,
    'owned_generated_directory_currently_absent': build_absent,
    'EPERM_syscall': 'UNRECORDED',
    'hypothesis': 'Unconditional normal-completion group signaling is one plausible source site;the receipts do not identify it or prove the proposed change fixes EPERM.',
    'successor_source_contract': [
        'Record phase/syscall/arguments/errno and WNOWAIT result before/after each process-control step;do not replace missing status with inferred compiler success.',
        'For a positively WNOWAIT-completed owned child,reap exactly that child without TERM/KILL;record actual returncode,then observe group absence read-only.',
        'After reaping,never signal that numeric group to resolve a live/ambiguous absence result;retain failure/artifacts if absence cannot be established.',
        'Only a still-running owned child in failure/timeout cleanup may receive signals while original leader custody remains retained.',
        'EPERM remains a failed/unknown process-control result;record and stop escalation without alternate kill methods or implicit retry.',
        'Preserve all original receipts/source/artifact hashes;any successor requires a separately selected plan/controller and fresh owned output paths.',
        'Retain prior capped outputs,one compile+conditional one24-test run,cumulative55s,pin/inventory/binary checks and finite signal cutoff.'
    ],
    'unexecuted_finite_expectations': [
        'WNOWAIT completed exit0:zero active signals,reap/returncode0,group absence required before advancing.',
        'WNOWAIT completed nonzero:zero active signals,reap/nonzero recorded,no test launch.',
        'Completed leader with group still present after reaping:no active post-reap signal;unknown closure/failure and preserve artifacts.',
        'Still-running failure/timeout:only retained exact owned custody permits signal;EPERM records failed syscall and no alternate action.',
        'waitid/reap/probe EPERM:original status remains unknown;no successful completion or closure claim.',
        'Failure before second command:recorded compiler/test attempt counts remain1/0,not1/1 or24 passing tests.'
    ],
    'new_controller_execution_released': False,
    'compiler_model_controller_runtime_test_version_native_UI_capture_phone_process_queries_by_reviewer': 0,
    'new_signals_or_binary_execution_by_reviewer': 0,
    'canonical_product_metadata_commit_push_actions': 0,
    'physical_prices_grants_funding_ownership_GA_accepted': False,
    'scope': 'Offline review of released terminal evidence and narrow prospective process-closure behavior only;no execution/replay.',
    'elapsed_seconds': time.monotonic() - started}
assert report['elapsed_seconds'] < 55
with (D / 'review-result.json').open('x') as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
    stream.write('\n')
print(json.dumps({key: report[key] for key in ('status', 'recorded_compiler_invocations',
    'recorded_test_invocations', 'original_exit_or_reap_result_recorded', 'EPERM_syscall', 'elapsed_seconds')}))
