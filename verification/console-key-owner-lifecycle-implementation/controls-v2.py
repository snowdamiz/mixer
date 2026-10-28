#!/usr/bin/env python3
"""Pure Python artifact-validator controls; no child processes or product runtime."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import copy
import json
import runpy
import sys
import tempfile
import time

START = time.monotonic()
DEADLINE = START + 55
LANE = Path(__file__).resolve().parent


def budget():
    if time.monotonic() >= DEADLINE:
        raise TimeoutError('pure Python validator controls exceeded 55 seconds')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', type=Path, default=LANE / 'prepared-2/runner.py')
    parser.add_argument('--output', type=Path, default=LANE / 'controls-v2.json')
    args = parser.parse_args()
    runner = runpy.run_path(str(args.runner.resolve()), run_name='pure_python_artifact_controls')
    packet = runner['read_json'](args.runner.resolve().parent / 'required-artifact-schemas.json', 16384)
    validate = runner['validate_terminal_artifacts']
    original = {
        'original_defect_reproduced': True, 'component_stopped': True, 'owner_stopped': True,
        'workers_stopped': True, 'table_gone': True, 'public_denial': True,
        'product_application_not_started': True}
    original_cleanup = {
        'component_stopped': True, 'owner_stopped': True, 'workers_stopped': True,
        'table_gone': True, 'dead_pointer_intentionally_retained_until_vm_exit': True}
    ordinary = {
        'component_stopped': True, 'observed_exact_children_stopped': True, 'owner_absent': True,
        'workers_absent': True, 'admission_absent': True, 'resume_result': ':ok', 'stop_result': ':ok'}
    runtime = {
        'elixir': '1.20.4', 'otp_release': '29', 'node': 'nonode@nohost',
        'schedulers_online': 2, 'product_application_started': False}
    good = {
        'original/original-regression.json': original,
        'original/original-cleanup.json': original_cleanup,
        'corrected/exunit-result.json': {'total': 7, 'failures': 0, 'skipped': 0, 'excluded': 0},
        'corrected/postconditions.json': {
            'test_owners_absent': True, 'test_workers_absent': True,
            'test_admission_absent': True, 'default_owner_absent': True,
            'default_repo_absent': True, 'product_application_not_started': True,
            'cleanup_receipts': 7},
        'corrected/KOL04-cleanup.json': {'admission_absent': True, 'exact_tables_deleted': True},
        'corrected/KOL06-cleanup.json': {
            'owner_absent': True, 'workers_absent': True, 'admission_absent': True},
        'original/runtime.json': dict(runtime), 'corrected/runtime.json': dict(runtime)}
    for number in ['01', '02', '03', '05', '07']:
        good['corrected/Elixir.MixerHosted.Identity.KeyOwnerLifecycleTest.KOL' + number + 'Owner-cleanup.json'] = dict(ordinary)
    validate(good, packet)
    alternative = copy.deepcopy(good)
    for path, value in alternative.items():
        if 'resume_result' in value:
            value['resume_result'] = ':already_stopped'
            value['stop_result'] = ':already_stopped'
    validate(alternative, packet)
    controls = []

    def reject(value, name):
        budget()
        try:
            validate(value, packet)
        except ValueError as error:
            controls.append({'name': name, 'result': 'rejected', 'error': str(error)})
        else:
            raise ValueError('malformed artifact fixture accepted: ' + name)

    reject([], 'aggregate-array')
    reject(None, 'aggregate-null')
    missing_artifact = copy.deepcopy(good)
    missing_artifact.pop('original/runtime.json')
    reject(missing_artifact, 'aggregate-missing-runtime')
    extra_artifact = copy.deepcopy(good)
    extra_artifact['unrelated.json'] = {}
    reject(extra_artifact, 'aggregate-unknown-artifact')
    for path, map_value in good.items():
        for malformed in [{}, {'unrelated': True}, {'only_result': False}, [], None, True, 1]:
            changed = copy.deepcopy(good)
            changed[path] = malformed
            reject(changed, path + ':malformed-map:' + json.dumps(malformed))
        for key, field in map_value.items():
            changed = copy.deepcopy(good)
            del changed[path][key]
            reject(changed, path + ':missing:' + key)
            if type(field) is bool:
                malformed_fields = [not field, int(field), float(field), str(field), None, {}, []]
            elif type(field) is int:
                malformed_fields = [bool(field), float(field), str(field), None, {}, [], field + 1]
            elif type(field) is str:
                malformed_fields = ['', ':error', True, 1, 1.0, None, {}, []]
            else:
                raise ValueError('unexpected independent good-fixture field type')
            for malformed in malformed_fields:
                changed = copy.deepcopy(good)
                changed[path][key] = malformed
                reject(changed, path + ':field:' + key + ':' + json.dumps(malformed))
        changed = copy.deepcopy(good)
        changed[path]['unexpected_result'] = ':ok'
        reject(changed, path + ':unknown-result-suffix-key')
    post_only = copy.deepcopy(good)
    post_only['corrected/postconditions.json'] = {'cleanup_receipts': 7}
    reject(post_only, 'review-counterexample-postconditions-only-count')
    boolean_zero = copy.deepcopy(good)
    boolean_zero['corrected/exunit-result.json'].update(failures=False, skipped=False, excluded=False)
    reject(boolean_zero, 'review-counterexample-boolean-zero-counts')
    float_counts = copy.deepcopy(good)
    float_counts['corrected/exunit-result.json'] = {'total': 7.0, 'failures': 0.0, 'skipped': 0.0, 'excluded': 0.0}
    reject(float_counts, 'review-counterexample-float-counts')
    strict_controls = []
    for text, name in [('{"a":1,"a":2}', 'duplicate'), ('{"a":NaN}', 'NaN'),
                       ('{"a":Infinity}', 'Infinity'), ('{"a":-Infinity}', '-Infinity')]:
        budget()
        with tempfile.TemporaryDirectory(prefix='mixer-lifecycle-v2-json-control-') as scratch:
            path = Path(scratch) / 'input.json'
            path.write_text(text)
            try:
                runner['read_json'](path)
            except ValueError:
                strict_controls.append(name)
            else:
                raise ValueError('strict JSON parser accepted ' + name)
    receipt = {
        'schema': 1, 'status': 'passed-pure-python-artifact-validator-controls',
        'at': datetime.now(timezone.utc).isoformat(),
        'python': sys.version, 'command': 'python3 -B controls-v2.py --runner prepared-2/runner.py',
        'good_fixture_artifacts': len(good), 'good_fixture_acceptances': 2,
        'malformed_fixture_rejections': len(controls), 'controls': controls,
        'strict_json_rejections': strict_controls,
        'subprocess_invocations': 0, 'elixir_version_formatter_compiler_product_runtime_invocations': 0,
        'elapsed_seconds': round(time.monotonic() - START, 6)}
    args.output.write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'controls'}))


if __name__ == '__main__':
    main()
