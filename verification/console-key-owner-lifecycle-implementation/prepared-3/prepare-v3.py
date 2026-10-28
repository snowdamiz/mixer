#!/usr/bin/env python3
"""Freeze candidate 3 after the single recorded formatting pass; no runtime child."""
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
PRIOR = LANE / 'prepared-2'
PREPARED = LANE / 'prepared-3'
FORMATTING = LANE / 'formatting-pass-1'
PRIOR_EXECUTION = LANE / 'executions/candidate-2'
REVIEW = ROOT / 'verification/console-key-owner-lifecycle-independent/review-2'
SOURCES = ['hosted/lib/mixer_hosted/identity/admission.ex',
           'hosted/lib/mixer_hosted/identity/key_owner.ex',
           'hosted/test/mixer_hosted/identity/key_owner_lifecycle_test.exs']


def budget():
    if time.monotonic() >= DEADLINE:
        raise TimeoutError('candidate-3 offline preparation exceeded 55 seconds')


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            budget()
            data = stream.read(262144)
            if not data:
                return value.hexdigest()
            value.update(data)


def pin(path, relative=None):
    return {'path': str(relative if relative is not None else path),
            'bytes': path.stat().st_size, 'sha256': sha(path)}


def strict(pairs):
    value = {}
    for key, field in pairs:
        if key in value:
            raise ValueError('duplicate JSON key: ' + key)
        value[key] = field
    return value


def read(path):
    return json.loads(path.read_text(), object_pairs_hook=strict,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def inventory(path, excluded=None):
    return [pin(file, str(file.relative_to(path))) for file in sorted(path.rglob('*'))
            if file.is_file() and str(file.relative_to(path)) != excluded]


def verify_packet(path, seal_name, expected_sha):
    if sha(path / seal_name) != expected_sha:
        raise ValueError('prior seal differs: ' + str(path))
    seal = read(path / seal_name)
    if inventory(path, seal_name) != seal['files']:
        raise ValueError('prior packet exact membership/bytes differ: ' + str(path))
    return seal


def main():
    if PREPARED.exists():
        raise ValueError('prepared-3 exists; preserve versioned packet')
    verify_packet(PRIOR, 'freeze.json', 'd59a6d3987a3dd892b24bc2fbefba079926dcbb8ade28ad9c429ddd4a54f19ef')
    verify_packet(FORMATTING, 'seal.json', 'fef6619cd13eced0d40b5dec0925d44e0b49eb80a41eb5c15ec52b6b38a25003')
    if sha(REVIEW / 'review-seal.json') != '9cf9490dd5dd50d36321ec0e8f4da365c83e5add87026690bec8a6c9c508e689':
        raise ValueError('independent review-2 seal differs')
    execution_before = inventory(PRIOR_EXECUTION)
    application = read(FORMATTING / 'application-receipt.json')
    if application['status'] != 'exact-recorded-formatter-output-applied':
        raise ValueError('formatter output application missing')
    plan = read(PRIOR / 'execution-plan.json')
    for source in SOURCES:
        record = next(item for item in application['files'] if item['path'] == source)
        old = (PRIOR / 'inputs' / source).read_bytes()
        output = (FORMATTING / 'outputs' / Path(source).name).read_bytes()
        current = (ROOT / source).read_bytes()
        if output != current or sha(ROOT / source) != record['formatter_output_sha256']:
            raise ValueError('current source does not equal recorded formatter output: ' + source)
        if old.translate(None, b' \t\r\n\v\f') != current.translate(None, b' \t\r\n\v\f'):
            raise ValueError('non-whitespace source bytes changed: ' + source)
    PREPARED.mkdir()
    for path in sorted(PRIOR.rglob('*')):
        budget()
        relative = str(path.relative_to(PRIOR))
        if path.is_file() and relative not in ['execution-plan.json', 'freeze.json']:
            destination = PREPARED / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
    for source in SOURCES:
        shutil.copyfile(ROOT / source, PREPARED / 'inputs' / source)
    runner = PREPARED / 'runner.py'
    before_runner = runner.read_text()
    after_runner = before_runner.replace("prepared.name != 'prepared-2'", "prepared.name != 'prepared-3'", 1)
    after_runner = after_runner.replace("output = lane / 'executions' / 'candidate-2'", "output = lane / 'executions' / 'candidate-3'", 1)
    if before_runner == after_runner:
        raise ValueError('exact runner path substitutions missing')
    ast.parse(after_runner, filename='prepared-3/runner.py')
    runner.write_text(after_runner)
    (PREPARED / 'candidate-3-paths.diff').write_text(''.join(difflib.unified_diff(
        before_runner.splitlines(keepends=True), after_runner.splitlines(keepends=True),
        fromfile='prepared-2/runner.py', tofile='prepared-3/runner.py')))
    shutil.copyfile(FORMATTING / 'formatting-only.diff', PREPARED / 'canonical-formatting-only.diff')
    shutil.copyfile(LANE / 'prepare-v3.py', PREPARED / 'prepare-v3.py')
    for path in sorted(FORMATTING.rglob('*')):
        budget()
        if path.is_file():
            destination = PREPARED / 'formatting-evidence' / path.relative_to(FORMATTING)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
    for name in ['review-seal.json', 'REVIEW.md']:
        destination = PREPARED / 'independent-review-2' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REVIEW / name, destination)
    canonical = []
    for expected in plan['canonical_inputs']:
        observed = pin(ROOT / expected['path'], expected['path'])
        if expected['path'] not in SOURCES and observed != expected:
            raise ValueError('unrelated canonical input changed: ' + expected['path'])
        canonical.append(observed)
    plan['canonical_inputs'] = canonical
    plan['source_tree_sha256'] = hashlib.sha256(''.join(item['path'] + '\0' + str(item['bytes']) + '\0' + item['sha256'] + '\n' for item in canonical).encode()).hexdigest()
    plan['created_at'] = datetime.now(timezone.utc).isoformat()
    plan['candidate'] = 3
    plan['supersedes_unexecuted_plan_sha256'] = None
    plan['supersedes_formatting_failed_plan_sha256'] = sha(PRIOR / 'execution-plan.json')
    plan['prior_freeze_preserved_sha256'] = sha(PRIOR / 'freeze.json')
    plan['independent_review_2_seal_sha256'] = sha(REVIEW / 'review-seal.json')
    plan['execution']['command'][2] = str(PREPARED / 'runner.py')
    plan['execution']['output_directory'] = str(LANE / 'executions/candidate-3')
    plan['formatting_only_correction'] = {
        'formatting_seal_sha256': sha(FORMATTING / 'seal.json'),
        'formatting_plan_sha256': sha(FORMATTING / 'execution-plan.json'),
        'formatting_receipt_sha256': sha(FORMATTING / 'receipt.json'),
        'source_application_receipt': 'formatting-evidence/application-receipt.json',
        'formatter_vm_invocations': 1, 'formatter_versions': {'elixir': '1.20.4', 'otp_release': '29'},
        'non_whitespace_source_bytes_unchanged': True, 'behavioral_changes_intended': False,
        'candidate_3_compiler_test_runtime_invocations': 0,
        'runner_diff': 'Only prepared-2/3 path guard and candidate-2/3 output literal substitutions.',
        'phase_bootstraps_common_schemas_tests_cases_and_tool_closure': 'Identical to independently reviewed prepared-2 except the recorded canonical whitespace formatting.'}
    amendment = {
        'schema': 1, 'status': 'formatting-output-applied-candidate-3-unexecuted-awaiting-root-review',
        'prior_candidate_2_failure': 'Original defect reproduced, corrected seven tests passed and strict thirteen-artifact validation succeeded; final phase failed read-only formatting equality for admission.ex.',
        'prior_execution_files': execution_before,
        'prior_freeze_preserved_sha256': sha(PRIOR / 'freeze.json'),
        'formatting_seal_sha256': sha(FORMATTING / 'seal.json'),
        'formatting_receipt_sha256': sha(FORMATTING / 'receipt.json'),
        'canonical_changes': application['files'],
        'runner_changes': 'Only prepared/output candidate numbering from 2 to 3.',
        'runtime_plan_changes': False, 'product_test_cases_added': False,
        'original_phase_corrected_phase_bootstraps_compile_common_and_strict_schema_unchanged': True,
        'candidate_3_runtime_compiler_test_invocations': 0,
        'pending': plan['pending']}
    save(PREPARED / 'formatting-correction-amendment.json', amendment)
    for name in ['bootstrap.exs', 'bootstrap-original.exs', 'compile-common.exs', 'required-artifact-schemas.json']:
        if (PRIOR / name).read_bytes() != (PREPARED / name).read_bytes():
            raise ValueError('reviewed runtime closure changed: ' + name)
    plan['prepared_files'] = inventory(PREPARED)
    save(PREPARED / 'execution-plan.json', plan)
    members = inventory(PREPARED)
    freeze = {
        'schema': 1, 'status': 'frozen-unexecuted-formatting-only-candidate-awaiting-review-and-root-release',
        'candidate': 3, 'sole_excluded_relative_path': 'freeze.json', 'files': members,
        'tree_sha256': hashlib.sha256(''.join(item['path'] + '\0' + str(item['bytes']) + '\0' + item['sha256'] + '\n' for item in members).encode()).hexdigest(),
        'execution_plan_sha256': sha(PREPARED / 'execution-plan.json'),
        'prior_freeze_sha256': sha(PRIOR / 'freeze.json'),
        'formatting_seal_sha256': sha(FORMATTING / 'seal.json'),
        'candidate_3_runtime_compiler_test_invocations': 0}
    save(PREPARED / 'freeze.json', freeze)
    verify_packet(PRIOR, 'freeze.json', 'd59a6d3987a3dd892b24bc2fbefba079926dcbb8ade28ad9c429ddd4a54f19ef')
    if inventory(PRIOR_EXECUTION) != execution_before:
        raise ValueError('prior candidate-2 execution bytes changed')
    print(json.dumps({'status': freeze['status'], 'execution_plan_sha256': freeze['execution_plan_sha256'],
        'freeze_sha256': sha(PREPARED / 'freeze.json'), 'members': len(members),
        'source_tree_sha256': plan['source_tree_sha256'], 'runtime_invocations': 0,
        'elapsed_seconds': round(time.monotonic() - START, 6)}))


if __name__ == '__main__':
    main()
