"""Bounded finite controls only. No corpus pass or external evidence writes."""
import argparse
import collections
import copy
import datetime
import io
import json
from pathlib import Path
import sys
import time
import unittest

from correction_support import HERE, ROOT, CANDIDATE, PREACCESS, REVIEW, USED, baseline_joiner, ident, load_corrected, source_module, verified, verify_preserved_packets, write


def replace_exact(value, replacements):
    if isinstance(value, dict):
        return {key: replace_exact(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_exact(item, replacements) for item in value]
    return replacements.get(value, value) if isinstance(value, str) else value


def coherent_receiver(joiner, module, number):
    file = next(x for x in joiner.ledger['files'] if x['file'] == 'boundary-162.rows.jsonl.gz')
    rows = list(map(module.loads, joiner.inputs.read(file['input_path'] + '.compact.jsonl').splitlines()))
    original = rows[number - 1]
    baseline = joiner.row(original, file['rows'][number - 1], file['file'])['native_completions'][0]
    observed = original['selected_actual_native_completions'][0]
    binding = next(x for x in original['native_receiver_bindings'] if x['global_identity'] == observed['receiver_identity'])
    replacements = {binding['global_identity']: 'missing.NativeSwitch@999', binding['row_identity']: 'missing.NativeSwitch@row-' + str(binding['ordinal'])}
    row = replace_exact(copy.deepcopy(original), replacements)
    next(x for x in row['native_receiver_bindings'] if x['global_identity'] == 'missing.NativeSwitch@999')['class'] = 'missing.NativeSwitch'
    result = joiner.row(row, file['rows'][number - 1], file['file'])['native_completions'][0]
    return {'row': number, 'state': original['state'], 'mutation': replacements, 'baseline': baseline, 'coherent_mutation_result': result}


def main(output):
    start = time.monotonic()
    output.mkdir(parents=True, exist_ok=False)

    def save(name, value):
        write(str(output.relative_to(HERE) / name), value)

    preserved_before = verify_preserved_packets()
    d = load_corrected()

    def suite(name, filename):
        raw = (HERE / filename).read_bytes()
        module = source_module(name, raw, HERE / filename)
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
        (output / (name + '.txt')).write_text(stream.getvalue())
        return {'tests': result.testsRun, 'successful': result.wasSuccessful(), 'failures': [{'id': test.id(), 'traceback': detail} for test, detail in result.failures], 'errors': [{'id': test.id(), 'traceback': detail} for test, detail in result.errors], 'source': ident(raw)}

    unchanged = suite('unchanged24', 'original_producer_tests.py')
    old_test_source = verified('candidate', 'test_descriptor_joins.py')
    assert unchanged['source'] == ident(old_test_source)
    stale_only = unchanged['tests'] == 24 and len(unchanged['failures']) == 1 and not unchanged['errors'] and unchanged['failures'][0]['id'].startswith('unchanged24.DescriptorJoinTests.test_full_descriptor_grammar')
    save('unchanged24-results.json', {**unchanged, 'expected_stale_F2_assertion_only': stale_only, 'note': 'Original expectation rejects valid ()Lfoo/(Bar; and is intentionally retained unchanged.'})
    migrated = suite('migrated24', 'test_descriptor_joins.py')
    focused = suite('focused8', 'test_review_corrections.py')
    save('migrated24-results.json', migrated)
    save('focused8-results.json', focused)

    inputs = d.Inputs()
    j = d.Joiner(inputs)
    specimens = json.loads(verified('preaccess', 'frozen-specimens.json'))
    plan_raw = verified('preaccess', 'preaccess-controls.json')
    controls = json.loads(plan_raw)['controls']
    assert len(controls) == 119
    original_facets = d.loads(verified('candidate', 'facets-run1/descriptor-facets.json'))
    declared = json.loads(verified('preaccess', 'public-family-source-map.json'))
    assert all(j.contract[x['family']]['name'] == x['method'] and j.contract[x['family']]['descriptor'] == x['descriptor'] and j.contract[x['family']]['declaring_class'] == x['declaring_product_class'] for x in declared)

    def archive(member):
        # Compatibility adapter for the exact reviewed evaluator's data accessor.
        # Only its already-released reference-tree member paths are accepted.
        assert member.startswith('reference-tree/')
        return inputs.read(member[len('reference-tree/'):])

    evaluator = source_module('_selected_independent_control_evaluator', (HERE / 'independent_control_evaluator.py').read_bytes(), HERE / 'independent_control_evaluator.py')
    evaluator.__dict__.update({'d': d, 'j': j, 'specimens': specimens, 'PREACCESS': PREACCESS, 'original_facets': original_facets, 'archive': archive})
    results = []
    for control in controls:
        try:
            passed, actual, note = evaluator.evaluate(control)
            classification = 'passed' if passed else 'failed'
        except d.Refusal as failure:
            passed = control['expected'].startswith('reject') or control['expected'] in ('missing-unresolved-zero-native-credit',)
            actual, note = {'refusal': str(failure)}, None
            classification = 'passed' if passed else 'failed'
        except Exception as failure:
            actual, note = {'exception': type(failure).__name__, 'message': str(failure)}, None
            classification = 'harness-error'
        results.append({'id': control['id'], 'layer': control['layer'], 'expected': control['expected'], 'classification': classification, 'actual': actual if control['layer'] in ('descriptor-helper-only', 'type-helper-only', 'output-preservation') or classification != 'passed' else {'expected_observed': True}, 'note': note})
    counts = dict(collections.Counter(item['classification'] for item in results))
    save('original119-results.json', {'source_plan': ident(plan_raw), 'count': len(results), 'classifications': counts, 'results': results})

    # Reproduce all three original findings without executing any old wrapper,
    # archive harness, full auditor, native code or preexisting bytecode cache.
    old, old_j = baseline_joiner()
    old_receivers = [coherent_receiver(old_j, old, number) for number in (6, 7)]
    old_grammar = []
    descriptors = [x['descriptor'] for x in json.loads(verified('review', 'postaccess-source-findings.json'))]
    for text in descriptors:
        try:
            old_grammar.append({'descriptor': text, 'unexpected_result': old.descriptor(text)})
        except old.Refusal as failure:
            old_grammar.append({'descriptor': text, 'old_refusal': str(failure)})
    budget_text = '(' + 'I' * 255 + ')V'
    old_args, old_result = old.descriptor(budget_text)
    old_control_report = json.loads(verified('review', 'original119-controls-results.json'))
    old_budget_control = next(x for x in old_control_report['results'] if x['id'] == 'descriptor-parameter-units-255-True')
    reproduction = {'F1': {'reproduced': all(x['coherent_mutation_result']['receiver']['status'] == 'unresolved' and x['coherent_mutation_result']['status'].startswith('joined-') for x in old_receivers), 'controls': old_receivers}, 'F2': {'reproduced': all('old_refusal' in x for x in old_grammar), 'controls': old_grammar}, 'F3': {'reproduced': len(old_args) == 255 and old_budget_control['classification'] == 'failed', 'old_descriptor_result': [old_args, old_result], 'unchanged_independent_old_candidate_diagnostic': old_budget_control}, 'original_checker_source': ident(verified('candidate', 'check_descriptor_joins.py')), 'original_review_findings': json.loads(verified('review', 'findings.json')), 'source_only_reader': True, 'no_corpus_pass': True}
    save('original-three-findings-reproduced.json', reproduction)

    new_grammar = [{'descriptor': text, 'result': d.descriptor(text), 'status': 'passed-JVMS-ClassName-grammar-only'} for text in descriptors]
    new_receivers = [coherent_receiver(j, d, number) for number in (6, 7)]
    for item in new_receivers:
        result = item['coherent_mutation_result']
        assert result['receiver']['status'] == 'unresolved' and result['status'].startswith('unresolved-')
        assert result['value']['normal_return'] == 'pending'
        assert result['value']['actual'] == item['baseline']['value']['actual']
    save('postaccess-three-grammar-results.json', new_grammar)
    save('postaccess-two-coherent-receiver-results.json', new_receivers)
    preserved_after = verify_preserved_packets()
    assert preserved_before == preserved_after
    save('exact-input-manifest.json', {'external_sealed_inputs': USED, 'corrected_utility_data_inputs': inputs.used, 'baseline_utility_data_inputs': old_j.inputs.used, 'old19_preaccess22_review21_preserved': preserved_after})
    success = stale_only and migrated['tests'] == 24 and migrated['successful'] and focused['tests'] == 8 and focused['successful'] and counts == {'passed': 119} and all(reproduction[key]['reproduced'] for key in ('F1', 'F2', 'F3'))
    summary = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'passed-selected-correction-controls' if success else 'failed-selected-correction-controls', 'unchanged24': {'tests': unchanged['tests'], 'expected_stale_F2_assertion_only': stale_only, 'successful': unchanged['successful']}, 'migrated24': {'tests': migrated['tests'], 'successful': migrated['successful']}, 'focused8': {'tests': focused['tests'], 'successful': focused['successful']}, 'independent119': counts, 'postaccess_grammar': len(new_grammar), 'postaccess_coherent_receiver': len(new_receivers), 'original_three_findings_reproduced': all(reproduction[key]['reproduced'] for key in ('F1', 'F2', 'F3')), 'elapsed_seconds': time.monotonic() - start, 'command': [sys.executable, '-B', str(Path(__file__).resolve()), '--output', str(output)], 'python': sys.version, 'python_executable': sys.executable, 'no_corpus_pass': True, 'no_native_or_product_execution': True, 'cache_loader_used': False, 'packets_preserved': preserved_after, 'independent_review': 'pending'}
    save('summary.json', summary)
    print(json.dumps(summary))
    return 0 if success else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert args.output.resolve().is_relative_to(HERE)
    sys.exit(main(args.output.resolve()))
