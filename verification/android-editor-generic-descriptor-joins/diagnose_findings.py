"""Focused explanation of the two retained findings; no corpus replay."""
import datetime
import json
from pathlib import Path
import sys
import time

import check_descriptor_joins as d


def main():
    start = time.monotonic()
    inputs = d.Inputs()
    joiner = d.Joiner(inputs)
    old = d.loads((d.HERE / 'facets-run1/descriptor-facets.json').read_bytes())
    d.need(len(old['findings']) == 2, 'exact original two findings')
    selected = next(x for x in joiner.ledger['files'] if x['file'] == 'boundary-162.rows.jsonl.gz')
    compact = selected['input_path'] + '.compact.jsonl'
    rows = list(map(d.loads, inputs.read(compact).splitlines()))
    records = []
    for finding in old['findings']:
        d.need(finding['file'] == compact and finding['row'] in (3, 5), 'only selected two exact row diagnostics')
        row = rows[finding['row'] - 1]
        d.need(len(row['selected_actual_native_completions']) == 1, 'exact selected original completion')
        completion = row['selected_actual_native_completions'][0]
        key, ins, owner, method = joiner.compiled_call(completion['production_frames'][0])
        d.need(ins['mnemonic'] == 'invokespecial' and ins['target'] == {'owner': 'android/widget/Switch', 'name': 'performAccessibilityAction', 'descriptor': '(ILandroid/os/Bundle;)Z'} and owner == 'android/widget/TextView', 'exact super call and inherited TextView resolution')
        inner = next(x for x in method['instructions'] if x['bci'] == 128)
        d.need(inner['mnemonic'] == 'invokespecial' and inner['target'] == {'owner': 'android/view/View', 'name': 'performAccessibilityAction', 'descriptor': '(ILandroid/os/Bundle;)Z'}, 'exact TextView inner View delegation')
        d.need(completion['method'] == 'View.performAccessibilityAction' and completion['completion'] == 'return' and completion['value'] == {'kind': 'boolean', 'value': False}, 'unchanged original inner normal completion')
        sources = {}
        for source_name in ['NativeAppearanceViewsV2.java', 'TextView.java', 'View.java']:
            data = inputs.read(d.RUN / source_name)
            lines = data.decode().splitlines()
            selected_lines = [{'line': number, 'text': line} for number, line in enumerate(lines, 1) if 'performAccessibilityAction' in line and (source_name != 'NativeAppearanceViewsV2.java' or 1530 <= number <= 1545)]
            sources[source_name] = {**d.identity(data), 'selected_lines': selected_lines}
        records.append({'file': compact, 'row': finding['row'], 'state': row['state'], 'historical_id': row['historical_id'], 'original_finding': finding, 'original_selected_completion': completion, 'compiled_product_call': {'class': key[0], 'method': key[1], 'descriptor': key[2], 'bci': key[3], 'opcode': ins['mnemonic'], 'callee': ins['target'], 'class_sha256': joiner.classmap[key[0] + '.class']['sha256']}, 'resolved_callee': {'class': owner, 'method': 'performAccessibilityAction', 'descriptor': '(ILandroid/os/Bundle;)Z', 'class_sha256': joiner.classmap[owner + '.class']['sha256'], 'literal_strings': sorted(method['literal_strings'])}, 'resolved_callee_inner_delegation': inner, 'sources': sources, 'classification': 'recorded-inner-View-completion-does-not-supply-resolved-TextView-callee-normal-outcome', 'scope': 'Descriptor grammar and Boolean type agree, but exact normal callee outcome producer attribution is not established. Only the separately selected composing-attributes adapter is authorized; no broader delegated-return rule is enabled.', 'resolved_callee_normal_completion': 'pending', 'original_data_changed': False})
    totals = {'rows': sum(len(x.get('rows', [])) for x in joiner.ledger['files']), 'raw_compact_files': sum('input_path' in x for x in joiner.ledger['files']), 'selected_events': sum(r['selected_events'] for x in joiner.ledger['files'] for r in x.get('rows', [])), 'selected_completions': sum(r['selected_native_completions'] for x in joiner.ledger['files'] for r in x.get('rows', [])), 'missing_selected_completion_rows': sum(r['missing_selected_native_completion'] for x in joiner.ledger['files'] for r in x.get('rows', [])), 'no_selected_rows': sum(r['selected_events'] == 0 for x in joiner.ledger['files'] for r in x.get('rows', []))}
    report = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'command': [sys.executable, '-B', str(Path(__file__).resolve())], 'python': sys.version, 'python_executable': sys.executable, 'source': d.identity(Path(__file__).resolve().read_bytes()), 'frozen_pass_source_seal': d.identity((d.HERE / 'source-seal.json').read_bytes()), 'original_report': d.identity((d.HERE / 'facets-run1/descriptor-facets.json').read_bytes()), 'unchanged_original_totals': totals, 'records': records, 'exact_focused_input_manifest': inputs.used, 'elapsed_seconds': time.monotonic() - start, 'status': 'two-source-backed-attribution-findings-preserved; no-new-delegation-rule', 'corpus_rerun': False, 'runtime_or_native_execution': False, 'independent_review': 'pending', 'qualification': False}
    d.write_json(d.HERE / 'two-row-finding-diagnostic.json', report)
    print(json.dumps({'status': report['status'], 'original_totals': totals, 'seconds': report['elapsed_seconds']}))


if __name__ == '__main__':
    main()
