#!/usr/bin/env python3
"""Bounded offline custody/source/runner parser checks; never starts a child."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json
import runpy
import sys
import tempfile
import time

START = time.monotonic()
DEADLINE = START + 55
LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
PREPARED = LANE / 'prepared-1'


def budget():
    if time.monotonic() >= DEADLINE:
        raise TimeoutError('offline audit exceeded 55 seconds')


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            budget()
            chunk = stream.read(262144)
            if not chunk:
                return value.hexdigest()
            value.update(chunk)


def strict(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key: ' + key)
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_text(), object_pairs_hook=strict,
                      parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))


def verify_pin(path, pin):
    if not path.is_file() or path.stat().st_size != pin['bytes'] or digest(path) != pin['sha256']:
        raise ValueError('pin mismatch: ' + str(path))


def main():
    freeze = read(PREPARED / 'freeze.json')
    expected = sorted(p['path'] for p in freeze['files'])
    actual = sorted(str(p.relative_to(PREPARED)) for p in PREPARED.rglob('*')
                    if p.is_file() and str(p.relative_to(PREPARED)) != 'freeze.json')
    if expected != actual:
        raise ValueError('exact freeze membership mismatch')
    for pin in freeze['files']:
        verify_pin(PREPARED / pin['path'], pin)
    plan = read(PREPARED / 'execution-plan.json')
    if freeze['execution_plan_sha256'] != digest(PREPARED / 'execution-plan.json'):
        raise ValueError('frozen plan digest mismatch')
    for pin in plan['canonical_inputs']:
        verify_pin(ROOT / pin['path'], pin)
    for pin in plan['tools']:
        verify_pin(Path(pin['path']), pin)
    prepared_pins = sorted(p['path'] for p in plan['prepared_files'])
    if sorted(prepared_pins + ['execution-plan.json']) != actual:
        raise ValueError('plan prepared membership mismatch')
    for pin in plan['prepared_files']:
        verify_pin(PREPARED / pin['path'], pin)
    for name in ['runner.py', 'prepare.py', 'audit.py']:
        ast.parse((PREPARED / name).read_text(), filename=name)
    before_owner = (LANE / 'beforeimages/hosted/lib/mixer_hosted/identity/key_owner.ex').read_text()
    expected_owner = before_owner.replace('  defp initialize(options, fixture) do\n',
        '  defp initialize(options, fixture) do\n    Process.flag(:trap_exit, true)\n\n', 1).replace(
        '    Admission.close(s.name)\n', '    Admission.close(s.name, s.table)\n', 1)
    if (ROOT / 'hosted/lib/mixer_hosted/identity/key_owner.ex').read_text() != expected_owner:
        raise ValueError('KeyOwner changed outside exact selected correction')
    before_admission = (LANE / 'beforeimages/hosted/lib/mixer_hosted/identity/admission.ex').read_text()
    expected_admission = before_admission.replace(
        '  def close(owner), do: :persistent_term.erase({__MODULE__, owner})\n',
        '  # Publication and close are serialized by the registered owner\'s lifecycle.\n'
        '  # This ownership check is not an atomic compare-and-erase operation.\n'
        '  def close(owner, table) do\n'
        '    if :ets.info(table, :owner) == self() and\n'
        '         :persistent_term.get({__MODULE__, owner}, nil) == table,\n'
        '      do: :persistent_term.erase({__MODULE__, owner}),\n'
        '      else: false\n'
        '  rescue\n'
        '    ArgumentError -> false\n'
        '  end\n', 1)
    if (ROOT / 'hosted/lib/mixer_hosted/identity/admission.ex').read_text() != expected_admission:
        raise ValueError('Admission changed outside exact selected correction')
    test = (ROOT / plan['test_source']).read_text()
    for number in range(1, 8):
        if test.count('  test "KOL' + str(number).zfill(2) + ' ') != 1:
            raise ValueError('prospective test membership differs')
    if 'start_fixture(' in test or 'enabled: true' in test or ':persistent_term.erase' in test:
        raise ValueError('test crossed ordinary-disabled lifecycle boundary')
    runner = runpy.run_path(str(PREPARED / 'runner.py'), run_name='offline_audit_only')
    parser_controls = []
    for text, name in [('{"a":1,"a":2}', 'duplicate'), ('{"a":NaN}', 'NaN'),
                       ('{"a":Infinity}', 'Infinity'), ('{"a":-Infinity}', '-Infinity')]:
        with tempfile.TemporaryDirectory(prefix='mixer-lifecycle-offline-json-') as scratch:
            path = Path(scratch) / 'input.json'
            path.write_text(text)
            try:
                runner['read_json'](path)
            except ValueError:
                parser_controls.append(name)
            else:
                raise ValueError('runner parser accepted ' + name)
    limits = plan['limits']
    if not 0 < limits['work_seconds'] < limits['cleanup_cutoff_seconds'] < limits['finalization_cutoff_seconds'] < limits['total_seconds'] == 55:
        raise ValueError('deadline partitions differ')
    receipt = {'schema': 1, 'status': 'offline-source-and-custody-checks-passed-runtime-pending',
               'at': datetime.now(timezone.utc).isoformat(),
               'execution_plan_sha256': digest(PREPARED / 'execution-plan.json'),
               'freeze_sha256': digest(PREPARED / 'freeze.json'),
               'exact_freeze_members': len(actual), 'source_roster_count': len(plan['source_roster']),
               'dependency_app_count': len(plan['dependencies']), 'tool_pin_count': len(plan['tools']),
               'exact_selected_production_patch': True, 'initial_beforeimages_preserved': True,
               'runner_python_AST': 'parsed', 'parser_rejection_controls': parser_controls,
               'runtime_compiler_formatter_version_invocations': 0,
               'note': 'These are Python offline checks. Elixir syntax, warnings, runtime behavior, original regression and KOL01-KOL07 are still unrun.',
               'elapsed_seconds': round(time.monotonic() - START, 6)}
    (LANE / 'offline-audit.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
