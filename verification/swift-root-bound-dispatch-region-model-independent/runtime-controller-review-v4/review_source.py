#!/usr/bin/env python3
"""Independent source/custody checks only; no controller/model execution."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import sys
import time

D = Path(__file__).resolve().parent
R = D.parents[2]
Q = R / 'verification/swift-semantic-adapter-root-review'
L = R / 'verification/swift-root-bound-dispatch-region-model-v2'
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
    name = str(path.relative_to(R)) if path.is_relative_to(R) else str(path)
    assert name not in inputs or inputs[name] == actual
    inputs[name], paths[name] = actual, path


def bounded_json(path, expected=None):
    raw = path.read_bytes()
    assert len(raw) <= 1048576
    if expected is not None:
        assert sha(raw) == expected
    pin({'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)})
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


previous_review = D.parent / 'runtime-controller-review-v3'
old_seal = bounded_json(previous_review / 'seal.json', '5e94408a70f8d2d02fbf6c389bad89766bd4572d3e15bc72c3d8bc8e034e880a')
for row in old_seal['members']:
    pin(row, previous_review)
prior = bounded_json(previous_review / 'checked-inputs.json')
for name, row in prior.items():
    pin({'path': name, **row})
terminal = D.parent / 'runtime-terminal-review-1'
terminal_seal = bounded_json(terminal / 'seal.json', '8165637c29c2214f1a806a3891484c1612830d61681e61e6512d9384f1f1fa08')
for row in terminal_seal['members']:
    pin(row, terminal)
terminal_report = bounded_json(terminal / 'review-result.json')
for name, row in terminal_report['input_hashes'].items():
    pin({'path': name, **row})

controller_path = Q / 'run-dispatch-region-model-v4.py'
raw = controller_path.read_bytes()
assert len(raw) == 14401 and sha(raw) == 'bc0806b2307ea2180cc7f99cac8cb30481a4077fec854154aea222ad351074ab'
pin({'path': str(controller_path), 'bytes': len(raw), 'sha256': sha(raw)})
old = (Q / 'run-dispatch-region-model-v3.py').read_bytes()
assert sha(old) == '53b6386bf796716c259e4a9f4ff709c908dee8e3d2c4d5f5e34f93f54ee7af69'
diff_path = Q / 'dispatch-region-controller-v4.diff'
diff = diff_path.read_bytes()
assert diff == ''.join(difflib.unified_diff(old.decode().splitlines(True), raw.decode().splitlines(True),
    fromfile='run-dispatch-region-model-v3.py', tofile='run-dispatch-region-model-v4.py')).encode()
pin({'path': str(diff_path), 'bytes': len(diff), 'sha256': sha(diff)})
plan_path = Q / 'dispatch-region-model-v4-host-plan.json'
plan = bounded_json(plan_path, '4e2959b148ec1ef4a48e708076ac28be2951b633ef5400c4d1be65cd7f8bec8a')
old_plan = bounded_json(L / 'host-test-plan.json', '5a2950e97e714e3628546d9b73aa2918c72f23f1221c64806823f978dc2c32e8')
changed = {'commands', 'environment', 'owned_outputs', 'execution_so_far', 'status', 'root_release_required'}
added = {'previous_attempt', 'controller_change_scope'}
assert set(plan) == set(old_plan) | added
assert all(plan[key] == value for key, value in old_plan.items() if key not in changed)
old_binary = old_plan['owned_outputs']['binary']
new_binary = str(L / 'command-2/model-tests')
for old_command, command in zip(old_plan['commands'], plan['commands'], strict=True):
    expected = json.loads(json.dumps(old_command))
    expected['argv'] = [new_binary if value == old_binary else value for value in expected['argv']]
    assert command == expected
assert plan['environment'] == {**old_plan['environment'], 'TMPDIR': str(L / 'command-2/tmp')}
assert plan['owned_outputs'] == {**old_plan['owned_outputs'], 'binary': new_binary,
    'directory': str(L / 'command-2'), 'temporary_directory': str(L / 'command-2/tmp')}
assert plan['root_release_required'] == {**old_plan['root_release_required'],
    'path': 'verification/swift-semantic-adapter-root-review/dispatch-region-model-v4-host-release.json'}
assert plan['execution_so_far'] == {'this_plan_attempts': 0, 'prior_compiler_records': 1, 'prior_test_runs': 0}
assert plan['previous_attempt']['compiler_exit_unrecorded'] is True
assert plan['previous_attempt']['failure_syscall_unrecorded'] is True and plan['previous_attempt']['tests_run'] == 0
for field in ('receipt', 'later_cleanup'):
    pin(plan['previous_attempt'][field])
for path in (L / 'command-2', Q / 'dispatch-region-model-v4-runtime'):
    try:
        path.lstat()
    except FileNotFoundError:
        pass
    else:
        raise AssertionError('fresh output already exists: ' + str(path))

text = raw.decode()
old_text = old.decode()
for begin, end in [('def control(', 'def save('), ('def save(', 'def call(')]:
    # Second interval includes unchanged absent() and excludes added call().
    prior_end = 'def exited(' if end == 'def call(' else end
    assert text[text.index(begin):text.index(end)] == old_text[old_text.index(begin):old_text.index(prior_end)]
call = text[text.index('def call('):text.index('def exited(')]
assert 'record["active_syscall"] = operation' in call and 'except OSError as error:' in call
assert '"operation": operation' in call and '"errno": error.errno' in call and 'traceback.format_exc(limit=6)' in call
assert 'if error.errno == 1:\n            record["permission_refusal"] = True' in call
exited = text[text.index('def exited('):text.index('def reap_completed(')]
assert 'waitid(WEXITED|WNOHANG|WNOWAIT)' in exited
assert 'record["completion_observation"]' in exited and all(field in exited for field in ('result.si_pid', 'result.si_code', 'result.si_status'))
reap = text[text.index('def reap_completed('):text.index('def close(')]
assert 'os.killpg(' not in reap and 'signal.SIGTERM' not in reap and 'signal.SIGKILL' not in reap
assert reap.index('child.wait(timeout=0)') < reap.index('record.update(reaped=True, returncode=child.returncode)') < reap.index('absence observation')
close = text[text.index('def close('):text.index('def command(')]
assert close.index('if record.get("permission_refusal")') < close.index('if record.get("reaped")') < close.index('if not record.get("custody")')
assert close.index('if exited(child):') < close.index('for sig, grace in')
loop = close[close.index('for sig, grace in'):]
assert loop.index('if exited(child):\n            return reap_completed(record)') < loop.index('lambda: os.killpg(child.pid, sig)')
assert 'record["cleanup_path"] = "completed-child-no-signals"' in close
assert 'record["cleanup_path"] = "still-running-owned-child"' in close
assert 'return reap_completed(record)' in close and 'child.wait(' not in close
assert text.count('lambda: os.killpg(child.pid, sig)') == 1
assert 'pins[str(PLAN_PATH)] = ' in text and 'plan = control(PLAN_PATH, PLAN_SHA)' in text
assert 'OUT = Path(__file__).with_name("dispatch-region-model-v4-runtime")' in text
assert 'buffers = command(plan["commands"][1], plan["environment"], 45)' in text
assert 'command(plan["commands"][0], plan["environment"], 30)' in text
assert text.index('outcome["generated_before"] = generated_inventory') < text.index('buffers = command(plan["commands"][1]')
assert 'assert outcome["generated_before"] == outcome["generated_after"]' in text
assert 'if closed:\n                    shutil.rmtree(build)' in text
cutoff = text.index('cutoff = time.monotonic() - START')
assert text.index('observations_sha = digest(') < text.index('signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)') < cutoff < text.index('observed = SEEN +')
assert not any(token in text[cutoff:] for token in ('digest(', 'control(', 'command(', 'json.loads', 'verify(', 'generated_inventory('))
assert 'passed = not ERRORS and not observed and cutoff < 53.5 and outcome.get("tests_passed") == 24' in text
assert 'len(expected) == len(actual) == 24 and set(actual) == expected' in text
assert 'getpgid(child.pid)' in text and 'getsid(child.pid)' in text
assert 'previous_attempt' not in text  # Provenance rows are metadata,not runtime pre/post inputs.

after = {name: observe(path) for name, path in paths.items()}
assert after == inputs
for name, data in [('controller-reviewed.py.txt', raw), ('controller-delta-reviewed.diff', diff)]:
    with (D / name).open('xb') as stream:
        stream.write(data)
with (D / 'checked-inputs.json').open('x') as stream:
    json.dump(inputs, stream, indent=2, sort_keys=True)
    stream.write('\n')
report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'FROZEN_INDEPENDENT_V4_CONTROLLER_AND_SUCCESSOR_PLAN_SOURCE_REVIEW_SINGLE_ROOT_ATTEMPT_RECOMMENDED',
    'controller_sha256': sha(raw), 'controller_bytes': len(raw), 'diff_sha256': sha(diff),
    'plan_sha256': sha(plan_path.read_bytes()), 'source146_binding': '91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f',
    'source_files': plan['source_files'], 'command': [sys.executable, '-B', str(Path(__file__).relative_to(R))],
    'cwd': str(R), 'python': sys.version,
    'python_tool': {'reported_path': sys.executable, 'resolved_path': str(Path(sys.executable).resolve()),
                    'sha256': sha(Path(sys.executable).resolve().read_bytes())},
    'review_script_sha256': sha(Path(__file__).read_bytes()), 'checked_input_members': len(inputs),
    'before_after_input_tree_sha256': sha(canonical(inputs)), 'before_after_custody_equal': True,
    'findings': [], 'root_execution_release_recommended': True,
    'recommendation': 'Root may release exactly this successor controller and plan with Python-B/assertions enabled for one compile and only on success one24-test run,55s cumulative,no retry;retain all results and exact owned cleanup evidence.',
    'process_control_source_conclusions': [
        'A completed-child observation reaches reap_completed without an active group signal;actual returncode is recorded before read-only group absence.',
        'No active signal follows reap. Running cleanup rechecks WNOWAIT before every signal while custody remains retained.',
        'waitid/reap/active-signal/absence errors retain operation/errno/stack;EPERM latches permission_refusal and later close returns without retry/escalation.',
        'No existing EPERM syscall/cause is inferred or diagnosed by this source correction.'
    ],
    'scope_precision_notes': [
        'Initial getpgid/getsid share an outer traceback line and are not separately named by call();they precede custody and failure cannot authorize active cleanup.',
        'The historical failed receipt/later_cleanup are hash-bound provenance in the new plan and independently verified here.They are not inserted into controller runtime pre/post pins;do not claim runtime-rehash of those two historical receipts.',
        'Generated row equality covers regular-file bytes;directory membership is bounded but empty-directory equality is not claimed.',
        'No runtime availability,compiler exit,tests passing or exact EPERM diagnosis is established.'
    ],
    'preserved_original_failed_attempt': True, 'old_compile_or_test_pass_accepted': False,
    'fresh_outputs_absent_at_review': [str(L / 'command-2'), str(Q / 'dispatch-region-model-v4-runtime')],
    'controller_model_compiler_tests_runtime_import_execution_native_UI_capture_phone_version_process_queries': 0,
    'canonical_product_metadata_commit_push_actions': 0,
    'physical_prices_grants_funding_ownership_GA_accepted': False,
    'cleanup': 'No child or build artifact created by reviewer;no cleanup owed.',
    'elapsed_seconds': time.monotonic() - started}
assert report['elapsed_seconds'] < 55
with (D / 'review-result.json').open('x') as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
    stream.write('\n')
print(json.dumps({key: report[key] for key in ('status', 'checked_input_members', 'root_execution_release_recommended', 'elapsed_seconds')}))
