#!/usr/bin/env python3
"""Host-only repair/regression receipts; original V3 findings remain failures."""
import ast
import datetime
import hashlib
import json
import os
import pathlib
import platform
import re
import subprocess
import sys
import time

B = pathlib.Path(__file__).resolve().parent
ROOT = B.parents[1]
V3 = B.parent / 'apple-toggle-keyboard-focus-v3-preparation'
REVIEW = B.parent / 'apple-toggle-keyboard-focus-v3-independent-review'
assert not (B / 'packet-seal.json').exists(), 'Sealed V4 preparation is immutable'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
expected_findings = ['test_CONTRACT_replay_rejects_regressing_host_receipt_time', 'test_CONTRACT_wrong_route_search_cannot_satisfy_selected_route', 'test_CONTRACT_wrong_target_poll_cannot_supply_enabled_window']


def ast_classes(path):
    return {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(path.read_text()).body if isinstance(node, (ast.ClassDef, ast.FunctionDef))}


old_ast = ast_classes(REVIEW / 'test_independent.py')
new_ast = ast_classes(B / 'test_independent_adapted.py')
assert old_ast == new_ast, 'Independent emitter/test assertions must remain unchanged'
cases = [
    ('focused-v4', [sys.executable, '-B', str(B / 'test_v4.py')], 22, 0),
    ('independent-v4', [sys.executable, '-B', str(B / 'test_independent_adapted.py')], 17, 0),
    ('same44-v4-positive-route-fixture-only', [sys.executable, '-B', str(B / 'execute_v4_controls.py')], 44, 0),
    ('sealed-v3-original44', [sys.executable, '-B', str(B / 'execute_v3_controls.py')], 44, 0),
    ('unchanged-v2', [sys.executable, '-B', str(B.parent / 'apple-toggle-keyboard-focus-v2/test_keyboard.py')], 29, 0),
    ('sealed-v3-independent-findings', [sys.executable, '-B', str(B / 'test_independent_adapted.py'), '--sealed-v3'], 17, 1),
]
commands = []
for name, argv, count, code in cases:
    start = time.monotonic()
    p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=60, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    ran = re.search(r'Ran (\d+) tests? in ', p.stderr)
    failures = sorted(set(re.findall(r'^FAIL: (test_\w+)', p.stderr, re.MULTILINE)))
    matched = p.returncode == code and ran is not None and int(ran.group(1)) == count and (failures == expected_findings and 'FAILED (failures=5)' in p.stderr if code else p.stderr.rstrip().endswith('OK'))
    commands.append({'name': name, 'argv': argv, 'cwd': str(ROOT), 'exitCode': p.returncode, 'testsRun': int(ran.group(1)) if ran else 0, 'expectedExitCode': code, 'expectedTestsRun': count, 'failingMethods': failures, 'elapsedSeconds': time.monotonic() - start, 'stdout': p.stdout, 'stderr': p.stderr, 'expectedOutcomeMatched': matched})
argv = [sys.executable, '-B', str(B / 'test_independent_adapted.py'), '--sealed-v3', '--witnesses']
p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=60, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
assert p.returncode == 0, p.stderr
(B / 'sealed-v3-findings-reproduced.json').write_text(p.stdout + '\n')
commands.append({'name': 'sealed-v3-finding-witnesses', 'argv': argv, 'cwd': str(ROOT), 'exitCode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr, 'expectedOutcomeMatched': True})
scratch = B / '.scratch'
assert not list(scratch.iterdir()), 'Host scratch must be empty'
scratch.rmdir()
external = [REVIEW / 'test_independent.py', REVIEW / 'execute_producer_controls.py', REVIEW / 'review-seal.json', V3 / 'test_settings_telemetry.py', B.parent / 'apple-toggle-keyboard-focus-v2/test_keyboard.py']
source = {str(p.relative_to(ROOT)): sha(p) for p in sorted(B.glob('*.py'))}
source.update({str(p.relative_to(ROOT)): sha(p) for p in external})
passed = all(item['expectedOutcomeMatched'] is True for item in commands)
value = {'schema': 'mixer.apple-toggle.keyboard-v4-host-controls.1', 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'command': [sys.executable, '-B', str(pathlib.Path(__file__).resolve().relative_to(ROOT))], 'pythonVersion': sys.version, 'hostVersion': platform.platform(), 'exitCode': 0 if passed else 1, 'testsRun': 22, 'expectedTestsRun': 22, 'allRequiredGroupsPassed': passed, 'commands': commands, 'sourceFiles': source, 'independentClassAndFunctionASTUnchanged': True, 'independentClassAndFunctionASTSHA256': hashlib.sha256(json.dumps(new_ast, sort_keys=True).encode()).hexdigest(), 'same44V4FixtureAdaptation': 'Original assertion module bytes unchanged. Only successful/absent route row emitter metadata aligned with selected V4 fixed row contract; all assertions, production checks and negative controls unchanged.', 'stderr': 'OK' if passed else 'Required group failed; inspect commands', 'nativeExecuted': False, 'compiled': False}
attempt = len(list(B.glob('host-test-attempt-*.json'))) + 1
(B / f'host-test-attempt-{attempt}.json').write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
if not passed:
    for item in commands:
        if not item['expectedOutcomeMatched']: print(item['name'], item.get('stderr'))
    raise SystemExit(1)
(B / 'host-controls.json').write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
print(json.dumps({'status': 'host-repairs-pass-prior-v3-findings-preserved', 'focusedV4': 22, 'independentV4': 17, 'same44AssertionsV4': 44, 'originalV3': 44, 'unchangedV2': 29, 'oldV3Independent': '17 methods, same3finding methods /5failure records reproduced', 'nativeExecuted': False, 'compiled': False}))
