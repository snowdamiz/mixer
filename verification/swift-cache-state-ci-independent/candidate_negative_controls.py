#!/usr/bin/env python3
"""Independent negative controls against exact frozen candidate validators."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time

HERE = Path(__file__).absolute().parent
PRODUCER = HERE.parent / 'swift-cache-state-ci-preparation'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    path = HERE / 'candidate-copy/check_cache_state.py'
    assert digest(path) == '92bf2c0ca453ad9cae8ad6274d2248870af1cad4f4044039afde28f806d4392d'
    spec = importlib.util.spec_from_file_location('independent_closed_candidate_controls', path)
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    out = HERE / 'evidence/candidate-negative-controls'
    out.mkdir(exist_ok=False)
    work = out / 'scratch'
    work.mkdir()
    rows = []
    def reject(name, fn, *args):
        try:
            fn(*args)
        except (RuntimeError, OSError, ValueError, TypeError) as error:
            rows.append({'name': name, 'rejected': True, 'reason': str(error)})
        else:
            raise AssertionError('Falsely accepted control: ' + name)
    baselines = {'API_actual_errors': 0, 'method_lists': 0, 'method_executions': 0,
                 'layouts': 0, 'synthetic_case_inventory': 0}
    api = json.loads((HERE / 'independent-api-contract.json').read_bytes())
    actual = json.loads((HERE / 'evidence/preaccess-api-complete/receipt.json').read_bytes())
    api_base = HERE / 'evidence/preaccess-api-complete/inputs'
    product = work / 'unexpected-product'
    for mode in ('debug', 'optimized'):
        for probe in api['probes']:
            if probe['expected_success']:
                continue
            name = mode + '-' + probe['name'].replace('/', '-')
            stderr = (HERE / 'evidence/preaccess-api-complete/commands' / (name + '.stderr')).read_text()
            row = next(r for r in actual['commands'] if r['name'] == name)
            candidate.verify_negative(probe, stderr, api_base, product, row)
            baselines['API_actual_errors'] += 1
            records = [json.loads(line) for line in stderr.splitlines() if line.strip()]
            index = next(i for i, d in enumerate(records) if d['level'] == 'error' and d.get('code'))
            original = records[index]
            mutations = {}
            bad = deepcopy(records); bad[index]['code']['code'] = 'E0000'; mutations['wrong-code'] = bad
            bad = deepcopy(records); bad[index]['message'] = 'unrelated compile failure'; mutations['wrong-message'] = bad
            bad = deepcopy(records); next(s for s in bad[index]['spans'] if s['is_primary'])['byte_start'] += 1; mutations['wrong-primary-offset'] = bad
            bad = deepcopy(records); next(s for s in bad[index]['spans'] if s['is_primary'])['file_name'] = 'api/unrelated.rs'; mutations['wrong-source'] = bad
            bad = deepcopy(records); bad[index]['spans'] = [s for s in bad[index]['spans'] if not s['is_primary']]; mutations['missing-primary'] = bad
            bad = deepcopy(records); bad.append(deepcopy(original)); mutations['duplicate-error'] = bad
            bad = deepcopy(records); nested = deepcopy(original); nested['code']['code'] = 'E0000'; bad[index]['children'].append(nested); mutations['nested-unrelated-error'] = bad
            bad = deepcopy(records); bad.pop(index); mutations['missing-error'] = bad
            bad = deepcopy(records); bad.append({'level': 'error', 'message': 'linker failure', 'code': None, 'spans': [], 'children': []}); mutations['unclassified-error'] = bad
            for mutation, changed in mutations.items():
                reject(name + ':' + mutation, candidate.verify_negative, probe, '\n'.join(json.dumps(d) for d in changed), api_base, product, row)
            for key, value in [('exit', 101), ('timed_out', True), ('child_returned', False), ('owned_group_gone', False), ('descendants_outlived_child', True), ('output_capped', True)]:
                changed_row = dict(row); changed_row[key] = value
                reject(name + ':' + key, candidate.verify_negative, probe, stderr, api_base, product, changed_row)
            reject(name + ':duplicate-json', candidate.verify_negative, probe, stderr + '\n{"level":"note","level":"error","message":"x"}', api_base, product, row)
            reject(name + ':nonfinite-json', candidate.verify_negative, probe, stderr + '\n{"level":"note","message":NaN}', api_base, product, row)
            product.write_bytes(b'unexpected product')
            try:
                reject(name + ':emitted-product', candidate.verify_negative, probe, stderr, api_base, product, row)
            finally:
                product.unlink()
            if len(probe['primary_spans']) > 1:
                bad = deepcopy(records); removed = False; keep = []
                for span in bad[index]['spans']:
                    if span['is_primary'] and not removed:
                        removed = True
                    else:
                        keep.append(span)
                bad[index]['spans'] = keep
                reject(name + ':missing-one-private-field', candidate.verify_negative, probe, '\n'.join(json.dumps(d) for d in bad), api_base, product, row)
    expected = json.loads((candidate.PACK / 'inventories/methods.json').read_bytes())
    reference = PRODUCER / 'runs/rust-1-99-final2'
    for mode in ('debug', 'optimized'):
        for lane in ('host', 'producer', 'independent', 'controls'):
            listing = (reference / 'commands' / (lane + '-' + mode + '-list.stdout')).read_text()
            candidate.verify_methods(listing, expected[lane]); baselines['method_lists'] += 1
            groups = expected['producer_debug_partition'] if lane == 'producer' and mode == 'debug' else [{'name': 'all', 'methods': expected[lane]}]
            for group in groups:
                text = (reference / 'commands' / (lane + '-' + mode + '-' + group['name'] + '.stdout')).read_text()
                filtered = len(expected[lane]) - len(group['methods'])
                candidate.verify_methods(text, group['methods'], True, filtered); baselines['method_executions'] += 1
                reject(lane + '-' + mode + '-' + group['name'] + ':wrong-filtered', candidate.verify_methods, text, group['methods'], True, filtered + 1)
                reject(lane + '-' + mode + '-' + group['name'] + ':ignored', candidate.verify_methods, text.replace('0 ignored;', '1 ignored;'), group['methods'], True, filtered)
            reject(lane + '-' + mode + ':missing-listed-method', candidate.verify_methods, listing.replace(expected[lane][0] + ': test\n', '', 1), expected[lane])
            reject(lane + '-' + mode + ':duplicate-list', candidate.verify_methods, listing + listing, expected[lane])
    layouts = json.loads((candidate.PACK / 'inventories/layouts.json').read_bytes())
    text = (reference / 'commands/host-debug-all.stdout').read_text()
    candidate.verify_layouts(text, layouts); baselines['layouts'] += 1
    reject('layout-duplicate', candidate.verify_layouts, text + '\n' + text, layouts)
    reject('layout-mutated-size', candidate.verify_layouts, text.replace('size=488', 'size=487'), layouts)
    pack = work / 'pack'
    shutil.copytree(candidate.PACK, pack)
    candidate.verify_pack(pack)
    for name, operation in [('extra-file', 'extra'), ('missing-source', 'missing'), ('mutated-source', 'mutated'), ('manifest', 'manifest'), ('symlink', 'symlink'), ('fifo', 'fifo')]:
        target = pack / ('manifest.json' if operation == 'manifest' else 'api/loan.rs')
        before = target.read_bytes()
        if operation == 'extra':
            extra = pack / 'unlisted'; extra.write_bytes(b'x')
        elif operation == 'missing':
            target.unlink()
        elif operation in ('mutated', 'manifest'):
            target.write_bytes(before + b'\n')
        elif operation == 'symlink':
            target.unlink(); target.symlink_to(pack / 'api/receipt.rs')
        elif operation == 'fifo':
            target.unlink(); os.mkfifo(target)
        try:
            reject('pack-' + name, candidate.verify_pack, pack)
        finally:
            if operation == 'extra':
                extra.unlink()
            else:
                target.unlink(missing_ok=True); target.write_bytes(before)
    candidate.verify_pack(pack)
    for name in ('', '.', '../x', '/x', 'a//b', './a', 'a/../b', 'a/./b', '.git/x', 'a\\b', 'x\x00'):
        reject('unsafe-path:' + repr(name), candidate.member, name)
    synthetic = work / 'synthetic-cases'; synthetic.mkdir()
    synthetic_expected = {'cases': []}
    for index in range(31):
        name = 'case-' + str(index).zfill(3); case = synthetic / name; case.mkdir()
        data = str(index).encode(); raw = {}
        for filename in ('input-0.bin', 'input-1.bin', 'input-2.bin', 'report.bin'):
            (case / filename).write_bytes(data); raw[filename] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        first = 'synthetic complete result ' + str(index)
        (case / 'result.txt').write_text(first + '\ninput_stamps_before_and_after=[]\n')
        synthetic_expected['cases'].append({'case': name, 'scope': 'synthetic-validator-only', 'actual_complete32': [0] * 32 if index < 29 else None, 'aggregate_present': index < 29, 'raw': raw, 'result_first_line': first})
    candidate.verify_cases(synthetic, synthetic_expected); baselines['synthetic_case_inventory'] += 1
    test = synthetic / 'case-000/result.txt'; before = test.read_bytes()
    test.write_bytes(before.replace(b'synthetic complete result', b'changed result'))
    reject('case-complete-result-mutated', candidate.verify_cases, synthetic, synthetic_expected); test.write_bytes(before)
    extra = synthetic / 'case-000/extra'; extra.write_bytes(b'x')
    reject('case-extra-file', candidate.verify_cases, synthetic, synthetic_expected); extra.unlink()
    report = synthetic / 'case-000/report.bin'; before = report.read_bytes(); report.write_bytes(before + b'x')
    reject('case-report-mutated', candidate.verify_cases, synthetic, synthetic_expected); report.write_bytes(before)
    shutil.rmtree(synthetic / 'case-030')
    reject('case-missing', candidate.verify_cases, synthetic, synthetic_expected)
    assert baselines == {'API_actual_errors': 46, 'method_lists': 8, 'method_executions': 25, 'layouts': 1, 'synthetic_case_inventory': 1}
    retained_work_inventory = candidate.inventory(work)
    shutil.rmtree(work)
    receipt = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
        'python': sys.version, 'script_sha256': digest(Path(__file__)), 'runner_sha256': digest(path),
        'baselines': baselines, 'controls_rejected': len(rows), 'controls': rows,
        'controlled_inputs_inventory_before_cleanup': retained_work_inventory,
        'scratch_removed': not work.exists(), 'normal_runner_execution_claimed': False,
        'historical_outputs_reused_only_to_exercise_validators': True,
        'actual_fresh_API_outputs_from_own_preaccess_run': True, 'passed': True}
    (out / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print('PASS exact candidate validators:', len(rows), 'negative controls;', baselines)

if __name__ == '__main__':
    main()
