#!/usr/bin/env python3
"""Offline correction of the phase at which ExUnit selection tags exist."""
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
OLD = LANE / 'prepared-3'
NEW = LANE / 'prepared-4'
FAILED = LANE / 'executions/candidate-3'


def pin(path, relative):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            if time.monotonic() >= DEADLINE:
                raise TimeoutError('offline filter correction exceeded 55 seconds')
            block = stream.read(262144)
            if not block:
                return {'path': str(relative), 'bytes': path.stat().st_size,
                        'sha256': value.hexdigest()}
            value.update(block)


def digest(path):
    return pin(path, path.name)['sha256']


def members(directory):
    return [pin(path, str(path.relative_to(directory)))
            for path in sorted(directory.rglob('*')) if path.is_file()]


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    if NEW.exists():
        raise ValueError('prepared-4 already exists; never overwrite a frozen packet')
    prior_seal = 'c79e8af319b32376d1d6dc4b074436eb10b20bae8415062f6313b1615989a910'
    if digest(OLD / 'freeze.json') != prior_seal:
        raise ValueError('prepared-3 seal differs')
    prior = json.loads((OLD / 'freeze.json').read_text())
    if members(OLD) != sorted(prior['files'] + [pin(OLD / 'freeze.json', 'freeze.json')],
                              key=lambda item: item['path']):
        raise ValueError('prepared-3 byte membership differs')
    if digest(FAILED / 'receipt.json') != '482f38e50f7bf39f46e83296edb0f3250a498865ad033af369daf2a634150372':
        raise ValueError('candidate-3 failed receipt differs')
    failed_before = members(FAILED)
    plan = json.loads((OLD / 'execution-plan.json').read_text())
    for item in plan['canonical_inputs']:
        if pin(ROOT / item['path'], item['path']) != item:
            raise ValueError('canonical input changed: ' + item['path'])
    NEW.mkdir()
    for item in plan['prepared_files']:
        destination = NEW / item['path']
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OLD / item['path'], destination)
    old_runner = (OLD / 'runner.py').read_text()
    runner = old_runner.replace("prepared.name != 'prepared-3'", "prepared.name != 'prepared-4'")
    runner = runner.replace("'candidate-3'", "'candidate-4'")
    ast.parse(runner, filename='runner.py')
    (NEW / 'runner.py').write_text(runner)
    old_bootstrap = (OLD / 'bootstrap.exs').read_text()
    invalid = 'true = Enum.all?(tests, &(&1.tags.test == &1.name))'
    if old_bootstrap.count(invalid) != 1:
        raise ValueError('invalid pre-run tag assertion marker differs')
    corrected = '''# ExUnit 1.20.4 Runner prepares the runtime :test tag before filtering.
# Evaluate the installed filter API with that effective tag, before test setup.
configuration = ExUnit.configuration()
include_filters = Keyword.fetch!(configuration, :include)
exclude_filters = Keyword.fetch!(configuration, :exclude)
true = include_filters == Enum.map(selected, &{:test, &1})
true = exclude_filters == [:test]

decisions =
  Enum.map(tests, fn test ->
    effective_tags = Map.put(test.tags, :test, test.name)
    {test.name, ExUnit.Filters.eval(include_filters, exclude_filters, effective_tags, tests)}
  end)

filter_selected = for {name, :ok} <- decisions, do: name
7 = length(filter_selected)
true = MapSet.new(filter_selected) == MapSet.new(selected)
22 = Enum.count(decisions, fn {_name, decision} -> match?({:excluded, _}, decision) end)'''
    bootstrap = old_bootstrap.replace(invalid, corrected)
    (NEW / 'bootstrap.exs').write_text(bootstrap)
    ast.parse(Path(__file__).read_text(), filename='prepare-v4.py')
    shutil.copyfile(Path(__file__), NEW / 'prepare-v4.py')
    diff = []
    for name, before, after in [('runner.py', old_runner, runner),
                                ('bootstrap.exs', old_bootstrap, bootstrap)]:
        diff.extend(difflib.unified_diff(before.splitlines(keepends=True),
                                        after.splitlines(keepends=True),
                                        fromfile='prepared-3/' + name, tofile='prepared-4/' + name))
    (NEW / 'candidate4-only.diff').write_text(''.join(diff))
    write(NEW / 'source-backed-filter-review.json', {
        'schema': 1, 'scope': 'Official source read plus offline harness correction; no runtime retry',
        'framework_version': 'Elixir ExUnit 1.20.4',
        'primary_sources': [
            {'url': 'https://raw.githubusercontent.com/elixir-lang/elixir/v1.20.4/lib/ex_unit/lib/ex_unit/runner.ex',
             'lines': '257-279',
             'paraphrase': 'Runner adds runtime test-name metadata immediately before evaluating include/exclude filters; compiled test registrations have not yet received that metadata.'},
            {'url': 'https://raw.githubusercontent.com/elixir-lang/elixir/v1.20.4/lib/ex_unit/lib/ex_unit/filters.ex',
             'lines': '166-205',
             'paraphrase': 'Filters.eval/4 accepts include filters, exclude filters, effective tags and the test collection; it returns admission or an exclusion/skip result.'}],
        'observed_failure': 'Candidate-3 compiled all product, four support and full test modules warning-free, then KeyError on pre-run test.tags.test before ExUnit.run or TLS setup.',
        'control': 'Use the installed ExUnit configuration, add only the relevant runtime :test tag, invoke actual ExUnit.Filters.eval/4 and require the admitted set equals the exact seven configured names with 22 exclusions.',
        'framework_implementation_copied': False,
        'canonical_product_test_support_tools_dependencies_schemas_wrapper_unchanged': True,
        'retained_failed_execution_members': failed_before,
        'compiler_or_runtime_invocations': 0})
    plan['selection']['include_filter'] = 'exclude [:test], include seven exact {:test, name_atom} filters; actual ExUnit.Filters.eval/4 verifies the exact selected set using the effective runtime :test tag'
    plan['execution']['command'] = [value.replace('/prepared-3/', '/prepared-4/')
                                     for value in plan['execution']['command']]
    plan['execution']['output_directory'] = plan['execution']['output_directory'].replace('/candidate-3', '/candidate-4')
    plan['created_at'] = datetime.now(timezone.utc).isoformat()
    plan['exunit_filter_phase_correction'] = {
        'prior_plan_sha256': digest(OLD / 'execution-plan.json'),
        'prior_freeze_sha256': prior_seal,
        'prior_failed_receipt_sha256': digest(FAILED / 'receipt.json'),
        'source_review': 'source-backed-filter-review.json',
        'runner_change': 'Only exact prepared-4/candidate-4 path literals',
        'runtime_test_count_contract_unchanged': '29 registered, 7 selected, 22 excluded, zero skipped/failures',
        'compiler_or_runtime_invocations': 0}
    new_names = [item['path'] for item in plan['prepared_files']] + [
        'prepare-v4.py', 'source-backed-filter-review.json', 'candidate4-only.diff']
    plan['prepared_files'] = [pin(NEW / name, name) for name in sorted(new_names)]
    write(NEW / 'execution-plan.json', plan)
    frozen = members(NEW)
    write(NEW / 'freeze.json', {'schema': 1, 'status': 'frozen-unexecuted',
        'sole_excluded_relative_path': 'freeze.json', 'files': frozen,
        'execution_plan_sha256': digest(NEW / 'execution-plan.json'),
        'tree_sha256': hashlib.sha256(''.join(
            item['path'] + '\0' + str(item['bytes']) + '\0' + item['sha256'] + '\n'
            for item in frozen).encode()).hexdigest(),
        'compiler_or_runtime_invocations': 0})
    assert members(FAILED) == failed_before
    assert digest(OLD / 'freeze.json') == prior_seal
    print(json.dumps({'plan_sha256': digest(NEW / 'execution-plan.json'),
        'freeze_sha256': digest(NEW / 'freeze.json'), 'members': len(frozen),
        'retained_failed_execution_files': len(failed_before),
        'elapsed_seconds': round(time.monotonic() - START, 6)}))


if __name__ == '__main__':
    main()
