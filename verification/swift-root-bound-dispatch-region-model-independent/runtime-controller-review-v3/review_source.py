#!/usr/bin/env python3
"""Source/hash review only; never imports or executes the root controller."""
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
P = Q / 'run-dispatch-region-model-v3.py'
LANE = R / 'verification/swift-root-bound-dispatch-region-model-v2'
started = time.monotonic()
checked = {}
paths = {}


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


def load(path, expected):
    raw = path.read_bytes()
    assert len(raw) <= 1048576 and sha(raw) == expected
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def observe(path):
    assert time.monotonic() - started < 55
    assert path.is_file() and not path.is_symlink()
    digest, length = hashlib.sha256(), 0
    with path.open('rb') as stream:
        while chunk := stream.read(262144):
            assert time.monotonic() - started < 55
            digest.update(chunk)
            length += len(chunk)
    return {'bytes': length, 'sha256': digest.hexdigest()}


def pin(row, base=R):
    path = base / row['path']
    actual = observe(path)
    assert actual == {key: row[key] for key in ('bytes', 'sha256')}, path
    key = str(path.relative_to(R)) if path.is_relative_to(R) else str(path)
    assert key not in checked or checked[key] == actual
    checked[key] = actual
    paths[key] = path


raw = P.read_bytes()
assert len(raw) == 12668 and sha(raw) == '53b6386bf796716c259e4a9f4ff709c908dee8e3d2c4d5f5e34f93f54ee7af69'
old = (Q / 'run-dispatch-region-model-v2.py').read_bytes()
assert len(old) == 10258 and sha(old) == 'e7bf73dc8f7816a651c0b987f0efd5b2db59e0e3fff9be92c59a56f469717433'
diff = (Q / 'dispatch-region-controller-v3.diff').read_bytes()
assert diff == ''.join(difflib.unified_diff(old.decode().splitlines(True), raw.decode().splitlines(True),
    fromfile='run-dispatch-region-model-v2.py', tofile='run-dispatch-region-model-v3.py')).encode()
for path, data in [(P, raw), (Q / 'run-dispatch-region-model-v2.py', old), (Q / 'dispatch-region-controller-v3.diff', diff)]:
    pin({'path': str(path), 'bytes': len(data), 'sha256': sha(data)})
plan_sha = '5a2950e97e714e3628546d9b73aa2918c72f23f1221c64806823f978dc2c32e8'
seal_sha = '53ab4e6ef041346dadadbbba69b7e5f5a7c35df004d9f1da753845be15779861'
plan = load(LANE / 'host-test-plan.json', plan_sha)
sealed = load(LANE / 'seal.json', seal_sha)
assert len(sealed['members']) == sealed['member_count'] == 11
assert len({row['path'] for row in sealed['members']}) == 11
assert sha(canonical(sealed['members'])) == sealed['tree_sha256']
for row in sealed['members']:
    assert not Path(row['path']).is_absolute() and '..' not in Path(row['path']).parts
    pin(row, LANE)
pin({'path': str(LANE / 'seal.json'), 'bytes': (LANE / 'seal.json').stat().st_size, 'sha256': seal_sha})
members = {row['path']: row for row in sealed['members']}
manifest = load(LANE / 'input-manifest.json', members['input-manifest.json']['sha256'])
roster = load(LANE / 'test-family-map.json', members['test-family-map.json']['sha256'])
names = ['tests::' + row['rust_test'] for row in roster['families']]
assert len(names) == len(set(names)) == 24
assert plan['source_files'] == manifest['source_files']
assert all(members[Path(row['path']).relative_to(LANE.relative_to(R)).as_posix()]['sha256'] == row['sha256'] for row in plan['source_files'])
for row in manifest['inputs'] + plan['source_files']:
    pin(row)
for key in ('compiler', 'linker_driver', 'link_editor', 'compiler_manifest', 'SDK_manifest'):
    pin(plan[key])
toolchain = load(R / plan['compiler_manifest']['path'], plan['compiler_manifest']['sha256'])
for row in toolchain['members']:
    pin(row, Path(toolchain['root']))
sdk = load(R / plan['SDK_manifest']['path'], plan['SDK_manifest']['sha256'])
for row in sdk['settings']:
    pin(row)

text = raw.decode()
inventory = text[text.index('def generated_inventory('):text.index('def save(')]
assert 'rows, pending, count, size = [], [build], 0, 0' in inventory
assert 'stat.S_ISDIR(build.lstat().st_mode)' in inventory
assert 'with os.scandir(pending.pop()) as entries:' in inventory
assert 'count += 1' in inventory and 'assert count <= 64' in inventory
assert 'entry.stat(follow_symlinks=False)' in inventory
assert 'assert stat.S_ISREG(info.st_mode)' in inventory
assert inventory.index('assert size <= 33554432') < inventory.index('row["sha256"] = digest(')
assert 'sorted(rows' in inventory and 'sorted(build.rglob' not in text
assert text.index('outcome["generated_before"] = generated_inventory') < text.index('buffers = command(plan["commands"][1]')
assert text.index('buffers = command(plan["commands"][1]') < text.index('outcome["generated_after"] = generated_inventory')
assert 'assert outcome["generated_before"] == outcome["generated_after"]' in text
assert 'assert outcome["binary_sha256_before"] == outcome["binary_sha256_after"]' in text
assert 'generated = generated_inventory(build, 49)' in text
assert 'if closed:\n                    shutil.rmtree(build)' in text
assert 'ERRORS.append("cleanup: " + repr(error))' in text and 'ERRORS.append("post: " + repr(error))' in text
assert text.index('verify(53.5)') < text.index('outcome["all_pins_rechecked"] = True')
assert 'passed = not ERRORS and not observed and cutoff < 53.5 and outcome.get("tests_passed") == 24' in text

control = text[text.index('def control('):text.index('def generated_inventory(')]
assert 'data = handle.read(1048577)' in control and 'assert len(data) <= 1048576' in control
assert control.index('hashlib.sha256(data).hexdigest() == expected') < control.index('return json.loads(data')
assert 'assert key not in result' in control and 'parse_constant=' in control
assert 'plan = control(LANE / "host-test-plan.json", PLAN_SHA)' in text
assert 'manifest = control(LANE / "input-manifest.json", sealed["input-manifest.json"]["sha256"])' in text
assert 'roster = control(LANE / "test-family-map.json", sealed["test-family-map.json"]["sha256"])' in text
assert 'toolchain = control(ROOT / plan["compiler_manifest"]["path"], plan["compiler_manifest"]["sha256"])' in text
assert 'control(ROOT / plan["SDK_manifest"]["path"], plan["SDK_manifest"]["sha256"])' in text
assert 'for item in seal["members"]:\n        pins[str(LANE / item["path"])] = item' in text
assert 'pins[str(Path(__file__).resolve())]' in text
assert text.count('test-family-map.json') == 2  # path and sealed member key, one cached read
assert 'expected = {"tests::" + x["rust_test"] for x in roster["families"]}' in text
assert 'len(expected) == len(actual) == 24 and set(actual) == expected' in text
assert 'test result: ok. 24 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;' in text

cutoff = text.index('cutoff = time.monotonic() - START')
assert text.index('observations_sha = digest(') < text.index('signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)') < cutoff
assert cutoff < text.index('observed = SEEN +') < text.index('signal.signal(sig, signal.SIG_IGN)')
assert not any(term in text[cutoff:] for term in ('digest(', 'control(', 'command(', 'json.loads', 'generated_inventory(', 'verify('))
assert 'later signals are outside this receipt' in text[cutoff:]
assert 'os.WEXITED | os.WNOHANG | os.WNOWAIT' in text
assert text.index('for sig, grace in') < text.index('child.wait(timeout=0)')
assert 'record["pid"] == record["pgid"] == record["sid"]' in text
assert text.count('command(plan["commands"][0]') == text.count('command(plan["commands"][1]') == 1
assert 'cap = 262144 if key.data == "stdout" else 524288' in text
assert plan['bounds']['automatic_retries'] == 0 and plan['bounds']['wall_seconds'] == 55

after = {key: observe(path) for key, path in paths.items()}
assert after == checked
with (D / 'controller-reviewed.py.txt').open('xb') as stream:
    stream.write(raw)
with (D / 'controller-delta-reviewed.diff').open('xb') as stream:
    stream.write(diff)
with (D / 'checked-inputs.json').open('x') as stream:
    json.dump(checked, stream, indent=2, sort_keys=True)
    stream.write('\n')
report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'FROZEN_INDEPENDENT_V3_CONTROLLER_SOURCE_REVIEW_C01_C02_C03_CORRECTED_SINGLE_ROOT_ATTEMPT_RECOMMENDED',
    'controller': {'path': str(P.relative_to(R)), 'bytes': len(raw), 'sha256': sha(raw)},
    'previous_controller_sha256': sha(old), 'controller_diff_sha256': sha(diff),
    'host_plan_sha256': plan_sha, 'model_v2_seal_sha256': seal_sha,
    'source146_binding': manifest['source146_contract_binding'],
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(R))], 'cwd': str(R),
    'python': sys.version,
    'python_tool': {'reported_path': sys.executable, 'resolved_path': str(Path(sys.executable).resolve()),
        'sha256': sha(Path(sys.executable).resolve().read_bytes())},
    'review_script_sha256': sha(Path(__file__).read_bytes()),
    'checked_input_members': len(checked), 'before_after_input_tree_sha256': sha(canonical(checked)),
    'before_after_custody_equal': True,
    'corrected_findings': ['C01 iterative no-follow generated membership/type/size pass before hashing and binary launch;repeat after run and cleanup.',
        'C02 all observation/input/artifact hashes precede signal blocking;cutoff precedes pending snapshot;only receipt publication follows.',
        'C03 strict bounded same-memory hashed JSON controls;whole preparation11members+seal and controller in pre/post pins;cached exact24name roster.'],
    'findings': [], 'root_execution_release_recommended': True,
    'recommendation': 'Root may release this exact controller hash for exactly the unchanged v2 plan:one compile and only on success one24-test invocation,55s cumulative,no retry;retain all failures and owned cleanup evidence.',
    'execution_assumptions': ['Execute the exact frozen controller with Python -B and assertions enabled;root release must bind controller and plan digests.',
        'Post-cutoff pending signals sampled conservatively can still reject;no pre-cutoff signal is deliberately omitted by ordering.',
        'Generated inventory checks all directory/file member counts but returned hash rows describe regular files;empty-directory presence is not a byte-content hash claim.',
        'The fixed pinned seal has11unique safe member paths;fixed pinned input rows have no inconsistent hash collisions. This is a finite packet review,not generic future-control validation.'],
    'controller_imported_or_executed': False,
    'compiler_model_test_runtime_version_process_inventory_native_UI_capture_phone_actions': 0,
    'model_test_results_claimed': False, 'actual_physical_prices_grants_funding_ownership_GA_accepted': False,
    'canonical_product_metadata_commit_push_actions': 0,
    'cleanup': 'No compiler/test child or generated build artifact created;no cleanup owed.',
    'elapsed_seconds': time.monotonic() - started}
assert report['elapsed_seconds'] < 55
with (D / 'review-result.json').open('x') as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
    stream.write('\n')
print(json.dumps({'status': report['status'], 'checked_input_members': len(checked),
                  'root_execution_release_recommended': True, 'elapsed_seconds': report['elapsed_seconds']}))
