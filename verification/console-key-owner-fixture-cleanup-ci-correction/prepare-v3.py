#!/usr/bin/env python3
"""Offline closure completion only; never launches a compiler or runtime."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import difflib
import hashlib
import json
import shutil
import time

START = time.monotonic()
DEADLINE = START + 55
LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
OLD = LANE / 'prepared-2'
NEW = LANE / 'prepared-3'
FAILED = LANE / 'executions/candidate-2'
SUPPORT = 'hosted/test/support/identity_socket_probe.ex'


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            if time.monotonic() >= DEADLINE:
                raise TimeoutError('offline closure freeze exceeded 55 seconds')
            block = stream.read(262144)
            if not block:
                return value.hexdigest()
            value.update(block)


def pin(path, relative):
    return {'path': str(relative), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def members(directory):
    return [pin(path, str(path.relative_to(directory)))
            for path in sorted(directory.rglob('*')) if path.is_file()]


def main():
    if NEW.exists():
        raise ValueError('prepared-3 already exists; never overwrite a packet')
    predecessor_seals = {
        'prepared-1': '34ab3c96238e0e8100331d42109d834d313b39bec9b86582e7ffd78080f97019',
        'prepared-2': '5ce0557d8cae549b7257a2d0ddfd59f73c4bd59d463fa20377e0038dfd64172e'}
    for name, expected in predecessor_seals.items():
        directory = LANE / name
        if digest(directory / 'freeze.json') != expected:
            raise ValueError('predecessor seal differs: ' + name)
        frozen = json.loads((directory / 'freeze.json').read_text())
        if members(directory) != sorted(frozen['files'] +
                [pin(directory / 'freeze.json', 'freeze.json')], key=lambda p: p['path']):
            raise ValueError('predecessor membership or bytes differ: ' + name)
    failed_before = members(FAILED)
    if digest(FAILED / 'receipt.json') != '3550d2902cc411a5ffbd566f8a6efe0eafc683e6a38527995fc7f8bd74df3f2f':
        raise ValueError('retained failed receipt differs')
    receipt = json.loads((FAILED / 'receipt.json').read_text())
    if receipt['status'] != 'failed' or receipt['cleanup_errors'] != []:
        raise ValueError('expected retained failed execution with completed cleanup')
    plan = json.loads((OLD / 'execution-plan.json').read_text())
    for item in plan['canonical_inputs']:
        if pin(ROOT / item['path'], item['path']) != item:
            raise ValueError('selected canonical input changed: ' + item['path'])
    ast.parse(Path(__file__).read_text(), filename='prepare-v3.py')
    NEW.mkdir()
    for item in plan['prepared_files']:
        target = NEW / item['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OLD / item['path'], target)
    old_runner = (OLD / 'runner.py').read_text()
    runner = old_runner.replace("prepared.name != 'prepared-2'", "prepared.name != 'prepared-3'")
    runner = runner.replace("'candidate-2'", "'candidate-3'")
    ast.parse(runner, filename='runner.py')
    (NEW / 'runner.py').write_text(runner)
    old_bootstrap = (OLD / 'bootstrap.exs').read_text()
    old_roster = '["identity_tls_fixture.ex", "identity_raw_fixture.ex", "identity_dns_fixture.ex"]'
    new_roster = old_roster[:-1] + ', "identity_socket_probe.ex"]'
    if old_bootstrap.count(old_roster) != 1:
        raise ValueError('support roster source marker differs')
    bootstrap = old_bootstrap.replace(old_roster, new_roster)
    bootstrap = bootstrap.replace('length(modules) == 3', 'length(modules) == 4')
    bootstrap = bootstrap.replace('COMPILED 3 frozen canonical support modules',
                                  'COMPILED 4 frozen canonical support modules')
    (NEW / 'bootstrap.exs').write_text(bootstrap)
    destination = NEW / 'inputs' / SUPPORT
    shutil.copyfile(ROOT / SUPPORT, destination)
    shutil.copyfile(Path(__file__), NEW / 'prepare-v3.py')
    diffs = []
    for name, before, after in [('runner.py', old_runner, runner),
                                ('bootstrap.exs', old_bootstrap, bootstrap)]:
        diffs.extend(difflib.unified_diff(before.splitlines(keepends=True),
                                         after.splitlines(keepends=True),
                                         fromfile='prepared-2/' + name, tofile='prepared-3/' + name))
    (NEW / 'candidate3-only.diff').write_text(''.join(diffs))
    support_pin = pin(ROOT / SUPPORT, SUPPORT)
    write(NEW / 'source-closure-review.json', {
        'schema': 1, 'scope': 'Offline source review for a missing full-module compile dependency',
        'added_source': support_pin,
        'module': 'MixerHosted.Identity.SocketProbe',
        'references': ['GenServer', 'Process', 'Map', 'Enum', 'Kernel', ':ssl', ':inet'],
        'references_scope': 'Existing Elixir/OTP tool closure; no other Mixer product or support modules',
        'module_top_level': 'Module documentation, use GenServer and function definitions only; no SocketProbe.start_link or init call during module compilation',
        'runtime_effects': 'Its sampling timer, worker monitors and socket measurements run only when the probe is explicitly started; all probe-using test methods remain unselected',
        'canonical_patch_changed': False, 'selected_methods': 7, 'compiled_methods': 29,
        'product_sources_changed': False, 'predecessor_seals': predecessor_seals,
        'retained_failed_execution_members': failed_before,
        'compiler_or_runtime_invocations': 0})
    plan['test_support'].append(SUPPORT)
    plan['canonical_inputs'].append(support_pin)
    plan['canonical_inputs'].sort(key=lambda p: p['path'])
    plan['source_tree_sha256'] = hashlib.sha256(''.join(
        p['path'] + '\0' + str(p['bytes']) + '\0' + p['sha256'] + '\n'
        for p in plan['canonical_inputs']).encode()).hexdigest()
    plan['source_tree_scope'] = plan['source_tree_scope'].replace('current test/support', 'current test/four support sources')
    for phase in plan['phases']:
        phase['expected'] = phase['expected'].replace('three support modules', 'four support modules')
    plan['execution']['command'] = [value.replace('/prepared-2/', '/prepared-3/')
                                     for value in plan['execution']['command']]
    plan['execution']['output_directory'] = plan['execution']['output_directory'].replace('/candidate-2', '/candidate-3')
    plan['created_at'] = datetime.now(timezone.utc).isoformat()
    plan['full_module_support_closure_correction'] = {
        'prior_plan_sha256': digest(OLD / 'execution-plan.json'),
        'prior_failed_receipt_sha256': digest(FAILED / 'receipt.json'),
        'finding': 'Full canonical test compilation requires SocketProbe.info/1 from unselected test bodies',
        'change': 'Copy existing stable SocketProbe source and compile four support modules; no warning suppression or removed bodies',
        'runner_change': 'Only exact prepared-3/candidate-3 path literals',
        'canonical_product_test_schemas_wrapper_tools_dependencies_unchanged': True,
        'compiler_or_runtime_invocations': 0}
    new_names = [p['path'] for p in plan['prepared_files']] + [
        'inputs/' + SUPPORT, 'prepare-v3.py', 'source-closure-review.json', 'candidate3-only.diff']
    plan['prepared_files'] = [pin(NEW / name, name) for name in sorted(new_names)]
    write(NEW / 'execution-plan.json', plan)
    frozen_members = members(NEW)
    write(NEW / 'freeze.json', {'schema': 1, 'status': 'frozen-unexecuted',
        'sole_excluded_relative_path': 'freeze.json', 'files': frozen_members,
        'execution_plan_sha256': digest(NEW / 'execution-plan.json'),
        'tree_sha256': hashlib.sha256(''.join(
            p['path'] + '\0' + str(p['bytes']) + '\0' + p['sha256'] + '\n'
            for p in frozen_members).encode()).hexdigest(),
        'compiler_or_runtime_invocations': 0})
    if members(FAILED) != failed_before:
        raise ValueError('failed execution bytes changed during source preparation')
    for name, expected in predecessor_seals.items():
        assert digest(LANE / name / 'freeze.json') == expected
    print(json.dumps({'plan_sha256': digest(NEW / 'execution-plan.json'),
        'freeze_sha256': digest(NEW / 'freeze.json'), 'members': len(frozen_members),
        'new_support_sha256': support_pin['sha256'],
        'retained_failed_execution_files': len(failed_before),
        'elapsed_seconds': round(time.monotonic() - START, 6)}))


if __name__ == '__main__':
    main()
