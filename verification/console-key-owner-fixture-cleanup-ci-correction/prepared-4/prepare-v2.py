#!/usr/bin/env python3
"""Freeze only the reviewed filesystem-boundary correction; offline, no child."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import difflib
import hashlib
import importlib.util
import json
import shutil
import time

START = time.monotonic()
DEADLINE = START + 55
LANE = Path(__file__).resolve().parent
OLD = LANE / 'prepared-1'
NEW = LANE / 'prepared-2'


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            if time.monotonic() >= DEADLINE:
                raise TimeoutError('offline freeze exceeded 55 seconds')
            block = stream.read(262144)
            if not block:
                return value.hexdigest()
            value.update(block)


def pin(path, relative):
    return {'path': str(relative), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    old_seal = '34ab3c96238e0e8100331d42109d834d313b39bec9b86582e7ffd78080f97019'
    if digest(OLD / 'freeze.json') != old_seal:
        raise ValueError('prior frozen seal differs')
    if NEW.exists() or (LANE / 'executions/candidate-1').exists():
        raise ValueError('new packet exists or prior packet was executed')
    freeze = json.loads((OLD / 'freeze.json').read_text())
    if sorted(str(p.relative_to(OLD)) for p in OLD.rglob('*') if p.is_file()) != sorted(
            [p['path'] for p in freeze['files']] + ['freeze.json']):
        raise ValueError('prior packet membership differs')
    for item in freeze['files']:
        if pin(OLD / item['path'], item['path']) != item:
            raise ValueError('prior frozen member differs: ' + item['path'])
    plan = json.loads((OLD / 'execution-plan.json').read_text())
    NEW.mkdir()
    for item in plan['prepared_files']:
        target = NEW / item['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OLD / item['path'], target)
    original_runner = (OLD / 'runner.py').read_text()
    runner = original_runner.replace('import signal\n', 'import signal\nimport stat\n')
    runner = runner.replace("prepared.name != 'prepared-1'", "prepared.name != 'prepared-2'")
    runner = runner.replace("'candidate-1'", "'candidate-2'")
    marker = '\ndef validate_terminal_artifacts('
    if runner.count(marker) != 1:
        raise ValueError('runner validator insertion marker differs')
    function = '''
def validate_phase_directory(directory, required, deadline):
    ensure(deadline, 'phase membership')
    if not stat.S_ISDIR(directory.lstat().st_mode):
        raise ValueError('phase output must be an ordinary directory, not a symlink')
    expected = set(required) | {'command.json', 'stdout.txt'}
    if len(required) != 8 or len(set(required)) != 8 or len(expected) != 10:
        raise ValueError('exact eight artifact and ten total phase names required')
    entries = []
    for entry in directory.iterdir():
        ensure(deadline, 'phase membership')
        entries.append(entry)
    actual = {entry.name for entry in entries}
    if actual != expected:
        raise ValueError('actual phase directory membership differs; missing=' +
                         repr(sorted(expected - actual)) + '; unexpected=' +
                         repr(sorted(actual - expected)))
    for entry in entries:
        ensure(deadline, 'phase member type')
        if not stat.S_ISREG(entry.lstat().st_mode):
            raise ValueError('phase member must be an ordinary file, not symlink or special type: ' + entry.name)

'''
    runner = runner.replace(marker, '\n' + function + marker)
    old = "            for phase in plan['phases']:\n                phase_output = output / phase['id']\n                names = phase['required_artifacts']\n                for name in names:\n"
    new = "            if not owned_absent or cleanup_errors:\n                raise RuntimeError('phase membership requires confirmed owned child/group cleanup')\n            for phase in plan['phases']:\n                phase_output = output / phase['id']\n                names = phase['required_artifacts']\n                validate_phase_directory(phase_output, names, finalize_deadline)\n                for name in names:\n"
    if runner.count(old) != 1:
        raise ValueError('runner boundary replacement marker differs')
    runner = runner.replace(old, new)
    ast.parse(runner, filename='runner.py')
    (NEW / 'runner.py').write_text(runner)
    for file in ['filesystem-boundary-controls.py', 'prepare-v2.py']:
        ast.parse((LANE / file).read_text(), filename=file)
        shutil.copyfile(LANE / file, NEW / file)
    controls_path = NEW / 'filesystem-boundary-controls.py'
    spec = importlib.util.spec_from_file_location('fixture_boundary_controls', controls_path)
    controls = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controls)
    result = controls.run(NEW / 'runner.py')
    write(NEW / 'filesystem-boundary-controls.json', result)
    diff = ''.join(difflib.unified_diff(original_runner.splitlines(keepends=True),
                                      runner.splitlines(keepends=True),
                                      fromfile='prepared-1/runner.py', tofile='prepared-2/runner.py'))
    (NEW / 'runner-directory-boundary.diff').write_text(diff)
    previous_plan_sha = digest(OLD / 'execution-plan.json')
    new_members = [p['path'] for p in plan['prepared_files']] + [
        'filesystem-boundary-controls.py', 'filesystem-boundary-controls.json',
        'prepare-v2.py', 'runner-directory-boundary.diff']
    plan['prepared_files'] = [pin(NEW / name, name) for name in sorted(new_members)]
    plan['execution']['command'] = [value.replace('/prepared-1/', '/prepared-2/')
                                     for value in plan['execution']['command']]
    plan['execution']['output_directory'] = plan['execution']['output_directory'].replace('/candidate-1', '/candidate-2')
    plan['created_at'] = datetime.now(timezone.utc).isoformat()
    plan['runner_directory_boundary_correction'] = {
        'finding': 'R01', 'prior_plan_sha256': previous_plan_sha,
        'prior_freeze_sha256': old_seal,
        'behavior': 'After confirmed owned child/group cleanup, validate actual phase membership equals exactly eight required artifacts plus command.json and stdout.txt; every member must be an ordinary file. Reject all extras, missing names, symlinks, directories and special types. Never repair or erase the output directory.',
        'product_test_bootstrap_tools_schemas_dependencies_unchanged': True,
        'offline_controls': 'filesystem-boundary-controls.json',
        'prior_fourteen_schema_controls_sha256': digest(LANE / 'offline-validator-controls.json'),
        'compiler_or_runtime_invocations': 0}
    write(NEW / 'execution-plan.json', plan)
    members = [pin(path, str(path.relative_to(NEW))) for path in sorted(NEW.rglob('*')) if path.is_file()]
    write(NEW / 'freeze.json', {'schema': 1, 'status': 'frozen-unexecuted',
        'sole_excluded_relative_path': 'freeze.json', 'files': members,
        'execution_plan_sha256': digest(NEW / 'execution-plan.json'),
        'tree_sha256': hashlib.sha256(''.join(p['path'] + '\0' + str(p['bytes']) + '\0' + p['sha256'] + '\n'
                                            for p in members).encode()).hexdigest(),
        'compiler_or_runtime_invocations': 0})
    # The correction never changes its predecessor, canonical sources or tool pins.
    assert digest(OLD / 'freeze.json') == old_seal
    assert plan['tools'] == json.loads((OLD / 'execution-plan.json').read_text())['tools']
    print(json.dumps({'plan_sha256': digest(NEW / 'execution-plan.json'),
        'freeze_sha256': digest(NEW / 'freeze.json'), 'members': len(members),
        'filesystem_controls': len(result['controls']),
        'elapsed_seconds': round(time.monotonic() - START, 6)}))


if __name__ == '__main__':
    main()
