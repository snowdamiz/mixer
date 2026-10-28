#!/usr/bin/env python3
"""Derive separately frozen candidate 2 without executing a product/runtime child."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import difflib
import hashlib
import json
import runpy
import shutil
import sys
import time

START = time.monotonic()
DEADLINE = START + 55
LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
ORIGINAL = LANE / 'prepared-1'
PREPARED = LANE / 'prepared-2'
REVIEW = ROOT / 'verification/console-key-owner-lifecycle-independent/review-1'

VALIDATOR = '''def expand_artifact_schemas(packet):
    if type(packet) is not dict or type(packet.get('required_artifacts')) is not int or packet['required_artifacts'] != 13:
        raise ValueError('required artifact schema count must be integer 13')
    schemas = dict(packet['schemas'])
    for name, paths in packet['shared_schema_bindings'].items():
        for path in paths:
            if path in schemas:
                raise ValueError('duplicate artifact schema binding: ' + path)
            schemas[path] = packet['shared_schemas'][name]
    if len(schemas) != 13:
        raise ValueError('exact thirteen artifact schemas required')
    return schemas


def validate_terminal_artifacts(artifacts, packet):
    schemas = expand_artifact_schemas(packet)
    if type(artifacts) is not dict or set(artifacts) != set(schemas):
        raise ValueError('exact required artifact path membership differs')
    for path, schema in schemas.items():
        value = artifacts[path]
        if type(value) is not dict or set(value) != set(schema):
            raise ValueError('exact artifact field membership differs: ' + path)
        for key, rule in schema.items():
            field = value[key]
            kind = rule['type']
            if kind == 'boolean':
                matches = type(rule.get('value')) is bool and field is rule['value']
            elif kind == 'integer':
                matches = type(rule.get('value')) is int and type(field) is int and field == rule['value']
            elif kind == 'string':
                if 'enum' in rule:
                    matches = type(field) is str and field in rule['enum']
                else:
                    matches = type(field) is str and field == rule['value']
            else:
                raise ValueError('unsupported artifact schema field type: ' + kind)
            if not matches:
                raise ValueError('artifact field type/value differs: ' + path + ':' + key)


'''

FORMATTER = '''# Read-only formatting qualification for the three authored canonical files.
# hosted/.formatter.exs contains only inputs, so these are its default options.
for relative <- [
      "hosted/lib/mixer_hosted/identity/admission.ex",
      "hosted/lib/mixer_hosted/identity/key_owner.ex",
      "hosted/test/mixer_hosted/identity/key_owner_lifecycle_test.exs"
    ] do
  path = Path.join(__DIR__, "inputs/" <> relative)
  original = File.read!(path)
  formatted = Code.format_string!(original, file: path) |> IO.iodata_to_binary()

  if original != formatted <> "\\n",
    do: raise("read-only formatting equality failed: " <> relative)
end

IO.puts("FORMAT CHECK 3 authored canonical files; unchanged=3")

'''


def budget():
    if time.monotonic() >= DEADLINE:
        raise TimeoutError('offline candidate-2 preparation exceeded 55 seconds')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            budget()
            data = stream.read(262144)
            if not data:
                return h.hexdigest()
            h.update(data)


def pin(path, relative=None):
    return {'path': str(relative if relative is not None else path),
            'bytes': path.stat().st_size, 'sha256': digest(path)}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def strict(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key: ' + key)
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_text(), object_pairs_hook=strict,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def verify_original():
    if digest(ORIGINAL / 'freeze.json') != '2169ba480aed74fcdac967908e578275fd7ebf3ca12d5f54448a3d61604b91a9':
        raise ValueError('prepared-1 freeze changed')
    frozen = read(ORIGINAL / 'freeze.json')
    actual = sorted(str(p.relative_to(ORIGINAL)) for p in ORIGINAL.rglob('*')
                    if p.is_file() and str(p.relative_to(ORIGINAL)) != 'freeze.json')
    if actual != sorted(item['path'] for item in frozen['files']):
        raise ValueError('prepared-1 exact membership changed')
    for item in frozen['files']:
        if pin(ORIGINAL / item['path'], item['path']) != item:
            raise ValueError('prepared-1 frozen member changed: ' + item['path'])


def main():
    if PREPARED.exists():
        raise ValueError('prepared-2 exists; do not rewrite a versioned candidate')
    verify_original()
    review_seal = REVIEW / 'review-seal.json'
    if digest(review_seal) != '378d1e6681ac625049bf53ce9f87a1b7168fcf2b2a3c00ab56a70210c2537131':
        raise ValueError('independent review seal changed')
    for item in read(review_seal)['files']:
        if pin(REVIEW / item['path'], item['path']) != item:
            raise ValueError('review member differs: ' + item['path'])
    PREPARED.mkdir()
    for source in sorted(ORIGINAL.rglob('*')):
        budget()
        if source.is_file() and str(source.relative_to(ORIGINAL)) not in ['execution-plan.json', 'freeze.json']:
            destination = PREPARED / source.relative_to(ORIGINAL)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    runner_path = PREPARED / 'runner.py'
    runner = runner_path.read_text()
    runner = runner.replace("prepared.name != 'prepared-1'", "prepared.name != 'prepared-2'", 1)
    runner = runner.replace("output = lane / 'executions' / 'candidate-1'", "output = lane / 'executions' / 'candidate-2'", 1)
    runner = runner.replace('def main():\n', VALIDATOR + 'def main():\n', 1)
    start = runner.index("            original = artifact_observations['original/original-regression.json']\n")
    end = runner.index('        except BaseException as exc:\n', start)
    runner = runner[:start] + (
        "            schema_packet = read_json(prepared / plan['artifact_schemas'], 16384)\n"
        '            validate_terminal_artifacts(artifact_observations, schema_packet)\n') + runner[end:]
    ast.parse(runner, filename='prepared-2/runner.py')
    runner_path.write_text(runner)
    bootstrap = PREPARED / 'bootstrap.exs'
    bootstrap.write_text(bootstrap.read_text().replace('passed =\n', FORMATTER + 'passed =\n', 1))
    schema = REVIEW / 'required-artifact-schemas.json'
    shutil.copyfile(schema, PREPARED / 'required-artifact-schemas.json')
    for file in ['prepare-v2.py', 'controls-v2.py']:
        ast.parse((LANE / file).read_text(), filename=file)
        shutil.copyfile(LANE / file, PREPARED / file)
    controls = runpy.run_path(str(LANE / 'controls-v2.py'), run_name='pure_python_controls_in_prepare_v2')
    saved_args = sys.argv
    try:
        sys.argv = ['controls-v2.py', '--runner', str(runner_path), '--output', str(PREPARED / 'validator-controls.json')]
        controls['main']()
    finally:
        sys.argv = saved_args
    control_receipt = read(PREPARED / 'validator-controls.json')
    control_receipt['command'] = 'python3 -B prepare-v2.py; controls-v2.py main called in-process without a child'
    write(PREPARED / 'validator-controls.json', control_receipt)
    plan = read(ORIGINAL / 'execution-plan.json')
    for item in plan['canonical_inputs']:
        if pin(ROOT / item['path'], item['path']) != item:
            raise ValueError('canonical selected input changed: ' + item['path'])
    additional = [ROOT / 'hosted/.formatter.exs', schema, review_seal, REVIEW / 'REVIEW.md']
    for source in additional:
        relative = str(source.relative_to(ROOT))
        plan['canonical_inputs'].append(pin(source, relative))
        destination = PREPARED / 'inputs' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    if (ROOT / 'hosted/.formatter.exs').read_text() != '[\n  inputs: ["mix.exs", "{config,lib,test,priv,scripts}/**/*.{ex,exs}"]\n]\n':
        raise ValueError('formatter configuration changed; must separately review nondefault options')
    plan['canonical_inputs'].sort(key=lambda item: item['path'])
    plan['source_tree_sha256'] = hashlib.sha256(''.join(
        item['path'] + '\0' + str(item['bytes']) + '\0' + item['sha256'] + '\n'
        for item in plan['canonical_inputs']).encode()).hexdigest()
    plan['created_at'] = datetime.now(timezone.utc).isoformat()
    plan['candidate'] = 2
    plan['supersedes_unexecuted_plan_sha256'] = digest(ORIGINAL / 'execution-plan.json')
    plan['prior_freeze_preserved_sha256'] = digest(ORIGINAL / 'freeze.json')
    plan['independent_review_seal_sha256'] = digest(review_seal)
    plan['artifact_schemas'] = 'required-artifact-schemas.json'
    plan['execution']['command'][2] = str(PREPARED / 'runner.py')
    plan['execution']['output_directory'] = str(LANE / 'executions/candidate-2')
    plan['phases'][1]['expected'] += ' Read-only Code.format_string! equality for the three authored canonical files in the same VM.'
    plan['formatter_amendment'] = {
        'root_requested': True, 'phase': 'corrected', 'extra_vms': 0,
        'files': ['hosted/lib/mixer_hosted/identity/admission.ex', 'hosted/lib/mixer_hosted/identity/key_owner.ex', plan['test_source']],
        'behavior': 'Code.format_string! with default options and final newline equality; read-only; stdout marker only after all three equal.',
        'configuration': 'hosted/.formatter.exs is pinned source evidence containing only inputs; configuration code is not executed.',
        'canonical_product_and_test_files_changed': False}
    plan['runner_correction'] = {
        'finding': 'R01', 'required_artifacts': 13,
        'behavior': 'Exact artifact path/field key sets; boolean identity, type(value) is int, exact string values or accepted result enums.',
        'pure_python_controls': 'validator-controls.json',
        'product_tests_added': False, 'runtime_scope_expanded': False}
    diff_parts = []
    for name in ['runner.py', 'bootstrap.exs']:
        diff_parts.extend(difflib.unified_diff((ORIGINAL / name).read_text().splitlines(keepends=True),
            (PREPARED / name).read_text().splitlines(keepends=True),
            fromfile='prepared-1/' + name, tofile='prepared-2/' + name))
    (PREPARED / 'selected-correction.diff').write_text(''.join(diff_parts))
    amendment = {
        'schema': 1, 'status': 'source-and-pure-python-only-correction-awaiting-root-review',
        'prepared_1_preserved': True, 'prepared_1_plan_sha256': digest(ORIGINAL / 'execution-plan.json'),
        'prepared_1_freeze_sha256': digest(ORIGINAL / 'freeze.json'),
        'review_seal_sha256': digest(review_seal),
        'runner_changes': ['Exact thirteen-artifact schema validation and strict boolean/integer/string types',
                           'Exact prepared-2 guard and candidate-2 execution output'],
        'explicit_root_formatter_amendment': plan['formatter_amendment'],
        'unchanged': ['All eighteen ordinary identity sources', 'Seven lifecycle product test cases',
                      'Original-beforeimage phase/bootstrap', 'compile-common.exs', 'Five dependency apps',
                      '969 tool pins', '40/46/52/55 deadlines', 'Resource cleanup, signal cutoff and runtime scope'],
        'pure_python_good_acceptances': control_receipt['good_fixture_acceptances'],
        'pure_python_malformed_rejections': control_receipt['malformed_fixture_rejections'],
        'runtime_version_formatter_compiler_product_invocations': 0}
    write(PREPARED / 'correction-amendment.json', amendment)
    plan['prepared_files'] = [pin(p, str(p.relative_to(PREPARED))) for p in sorted(PREPARED.rglob('*')) if p.is_file()]
    write(PREPARED / 'execution-plan.json', plan)
    members = [pin(p, str(p.relative_to(PREPARED))) for p in sorted(PREPARED.rglob('*')) if p.is_file()]
    freeze = {
        'schema': 1, 'status': 'frozen-awaiting-independent-review-unexecuted',
        'candidate': 2, 'sole_excluded_relative_path': 'freeze.json', 'files': members,
        'tree_sha256': hashlib.sha256(''.join(item['path'] + '\0' + str(item['bytes']) + '\0' + item['sha256'] + '\n' for item in members).encode()).hexdigest(),
        'execution_plan_sha256': digest(PREPARED / 'execution-plan.json'),
        'prior_freeze_sha256': digest(ORIGINAL / 'freeze.json'),
        'review_seal_sha256': digest(review_seal),
        'compiler_runtime_formatter_version_invocations': 0}
    write(PREPARED / 'freeze.json', freeze)
    verify_original()
    print(json.dumps({'status': freeze['status'], 'execution_plan_sha256': freeze['execution_plan_sha256'],
        'freeze_sha256': digest(PREPARED / 'freeze.json'), 'members': len(members),
        'pure_python_good_acceptances': control_receipt['good_fixture_acceptances'],
        'pure_python_malformed_rejections': control_receipt['malformed_fixture_rejections'],
        'elapsed_seconds': round(time.monotonic() - START, 6)}))


if __name__ == '__main__':
    main()
