#!/usr/bin/env python3
"""Negative controls for the independent diagnostic acceptance boundary."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from preaccess_api import validate_negative

HERE = Path(__file__).absolute().parent

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    output = HERE / 'evidence/preaccess-negative-controls-complete'
    output.mkdir(exist_ok=False)
    contract_path = HERE / 'independent-api-contract.json'
    contract = json.loads(contract_path.read_bytes())
    actual_path = HERE / 'evidence/preaccess-api-complete/receipt.json'
    actual = json.loads(actual_path.read_bytes())
    assert actual['passed'] and len(actual['probes']) == 50
    rows = []
    executable = output / 'must-not-exist'
    def encode(records):
        return '\n'.join(json.dumps(x) for x in records)
    def expect_reject(name, probe, stderr, row):
        try:
            validate_negative(probe, stderr, executable, row)
        except (RuntimeError, ValueError, TypeError) as error:
            rows.append({'name': name, 'rejected': True, 'reason': str(error)})
        else:
            raise AssertionError('Control falsely accepted: ' + name)
    baseline_count = 0
    for mode in ('debug', 'optimized'):
        for probe in contract['probes']:
            if probe['expected_success']:
                continue
            name = mode + '-' + probe['name'].replace('/', '-')
            stderr_path = actual_path.parent / 'commands' / (name + '.stderr')
            text = stderr_path.read_text()
            row = next(r for r in actual['commands'] if r['name'] == name)
            validate_negative(probe, text, executable, row)
            baseline_count += 1
            records = [json.loads(line) for line in text.splitlines() if line.strip()]
            index = next(i for i, record in enumerate(records) if record.get('level') == 'error' and record.get('code'))
            original = records[index]
            mutations = {}
            wrong = deepcopy(records); wrong[index]['code']['code'] = 'E0000'; mutations['wrong-code'] = wrong
            wrong = deepcopy(records); wrong[index]['message'] = 'unrelated compile failure'; mutations['wrong-message'] = wrong
            wrong = deepcopy(records)
            next(s for s in wrong[index]['spans'] if s['is_primary'])['byte_start'] += 1
            mutations['wrong-primary-offset'] = wrong
            wrong = deepcopy(records)
            next(s for s in wrong[index]['spans'] if s['is_primary'])['file_name'] = 'api/unrelated.rs'
            mutations['wrong-primary-source'] = wrong
            wrong = deepcopy(records); wrong[index]['spans'] = [s for s in wrong[index]['spans'] if not s['is_primary']]
            mutations['missing-primary'] = wrong
            wrong = deepcopy(records); wrong.append(deepcopy(original)); mutations['duplicate-error'] = wrong
            wrong = deepcopy(records)
            unrelated = deepcopy(original); unrelated['code']['code'] = 'E0000'
            wrong[index]['children'].append(unrelated); mutations['nested-unrelated-error'] = wrong
            wrong = deepcopy(records); wrong.pop(index); mutations['missing-intended-error'] = wrong
            wrong = deepcopy(records)
            wrong.append({'level': 'error', 'code': None, 'message': 'linker failed for another reason', 'spans': [], 'children': []})
            mutations['unclassified-error'] = wrong
            for mutation, value in mutations.items():
                expect_reject(name + ':' + mutation, probe, encode(value), row)
            for key, value in [('exit', 101), ('timed_out', True), ('child_returned', False), ('owned_group_gone', False), ('descendants_outlived_direct_child', True)]:
                wrong_row = dict(row); wrong_row[key] = value
                expect_reject(name + ':abnormal-' + key, probe, text, wrong_row)
            expect_reject(name + ':duplicate-json-key', probe, text + '\n{"level":"note","level":"error","message":"x"}', row)
            expect_reject(name + ':nonfinite-json', probe, text + '\n{"level":"note","message":NaN}', row)
            executable.write_bytes(b'not executable; presence alone must fail')
            try:
                expect_reject(name + ':unexpected-product', probe, text, row)
            finally:
                executable.unlink()
            if len(probe['primary_spans']) > 1:
                wrong = deepcopy(records)
                removed = False
                spans = []
                for span in wrong[index]['spans']:
                    if span['is_primary'] and not removed:
                        removed = True
                    else:
                        spans.append(span)
                wrong[index]['spans'] = spans
                expect_reject(name + ':one-constructor-field-omitted', probe, encode(wrong), row)
    assert baseline_count == 46 and len(rows) == 784
    result = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
              'python': sys.version, 'script_sha256': digest(Path(__file__)),
              'validator_sha256': digest(HERE / 'preaccess_api.py'),
              'contract_sha256': digest(contract_path), 'actual_receipt_sha256': digest(actual_path),
              'actual_negative_baselines_revalidated': baseline_count,
              'synthetic_controls_rejected': len(rows), 'controls': rows,
              'passed': True, 'scratch_and_products_absent': not executable.exists(),
              'candidate_review_or_full_runtime_claim': False}
    (output / 'receipt.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('PASS: 46 actual diagnostic baselines; 784 unrelated/incomplete failure controls rejected')

if __name__ == '__main__':
    main()
