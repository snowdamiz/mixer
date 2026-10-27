"""Post-pass whole-record/output custody only; never reads the compact corpus."""
import datetime
import json
from pathlib import Path
import sys
import time

from correction_support import HERE, USED, ident, verified, verify_preserved_packets, write


def same(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[key], b[key]) for key in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def main():
    start = time.monotonic()
    old_raw = verified('candidate', 'facets-run1/descriptor-facets.json')
    old = json.loads(old_raw)
    new_raw = (HERE / 'facets-run1/descriptor-facets.json').read_bytes()
    new = json.loads(new_raw)
    diagnostic = json.loads(verified('candidate', 'two-row-finding-diagnostic.json'))
    original_findings = {(Path(x['file']).name.replace('.compact.jsonl', ''), x['row']): x for x in diagnostic['records']}
    assert same(old['subjects280'], new['subjects280'])
    assert same(old['historical189'], new['historical189'])
    assert len(old['subjects280']) == 280 and sum(len(x['original_required_cases_retained']) for x in old['subjects280']) == 2705 and len(old['historical189']) == 189
    assert old['execution_closure_native_OTA_GA_accepted'] is new['execution_closure_native_OTA_GA_accepted'] is False
    observations = joined = unmatched = public = 0
    assert len(old['files']) == len(new['files']) == 214
    for before, after in zip(old['files'], new['files']):
        assert before['file'] == after['file'] and same(before['raw_input'], after['raw_input']) and same(before['compact_input'], after['compact_input'])
        assert len(before['rows']) == len(after['rows'])
        for number, (old_row, new_row) in enumerate(zip(before['rows'], after['rows']), 1):
            if old_row.get('status') == 'finding':
                known = original_findings[(before['file'], number)]
                assert same(known['original_selected_completion'], new_row['original_selected_native_completions_retained'][0])
                assert all(same(old_row[key], new_row[key]) for key in old_row)
                unmatched += len(new_row['original_selected_native_completions_retained'])
                observations += len(new_row['original_selected_native_completions_retained'])
                continue
            assert old_row['state'] == new_row['state'] and old_row['family'] == new_row['family'] and old_row['historical_id'] == new_row['historical_id']
            assert old_row['missing_selected_native_completion'] is new_row['missing_selected_native_completion']
            assert len(old_row['native_completions']) == len(new_row['native_completions'])
            for old_completion, new_completion in zip(old_row['native_completions'], new_row['native_completions']):
                assert same(old_completion['original_completion'], new_completion['original_completion'])
                assert same(old_completion['value'], new_completion['value'])
                assert old_completion['status'] == new_completion['status']
                assert all(context['status'] == 'passed' for context in new_completion['parameter_contexts'].values())
                joined += 1
                observations += 1
            if old_row.get('public_result'):
                assert same(old_row['public_result']['actual'], new_row['public_result']['actual'])
                assert same(old_row['public_result']['value'], new_row['public_result']['value'])
                assert new_row['public_result']['binding']['parameter_context']['status'] == 'passed'
                public += 1
    assert (observations, joined, unmatched, public) == (665, 663, 2, 351)
    assert new['counts']['missing_selected_native_completion'] == 844 and new['counts']['no_selected_rows'] == 108
    source = json.loads((HERE / 'source-seal.json').read_text())
    for member in source['members']:
        assert ident((HERE / member['path']).read_bytes()) == {key: member[key] for key in ('bytes', 'sha256')}
    preserved = verify_preserved_packets()
    out = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'passed-whole-record-observation-and-packet-preservation; not-qualified', 'command': [sys.executable, '-B', str(Path(__file__).resolve())], 'python': sys.version, 'source': ident(Path(__file__).resolve().read_bytes()), 'original_facets': ident(old_raw), 'corrected_facets': ident(new_raw), 'source_seal': ident((HERE / 'source-seal.json').read_bytes()), 'exact_original_subject_records': 280, 'exact_original_required_cases': 2705, 'exact_original_historical_records': 189, 'unchanged_original_record_order_and_types': True, 'selected_observations_retained_exactly': observations, 'base_joins_retained_exactly': joined, 'known_inner_delegate_observations_retained_exactly': unmatched, 'public_observations_retained_exactly': public, 'missing_completion_rows': 844, 'no_selected_rows': 108, 'frozen_correction_sources_unchanged': True, 'original_packets_unchanged': preserved, 'external_data_input_manifest': USED, 'compact_corpus_reread': False, 'product_or_native_execution': False, 'elapsed_seconds': time.monotonic() - start, 'independent_review': 'pending', 'whole_subject_or_execution_native_OTA_GA_accepted': False}
    write('whole-record-and-observation-preservation.json', out)
    print(json.dumps({key: out[key] for key in ('status', 'selected_observations_retained_exactly', 'base_joins_retained_exactly', 'known_inner_delegate_observations_retained_exactly', 'elapsed_seconds')}))


if __name__ == '__main__':
    main()
