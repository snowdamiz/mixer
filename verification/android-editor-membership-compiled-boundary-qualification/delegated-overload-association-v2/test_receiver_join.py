"""Actual all-state rows plus hostile receiver/raw-data substitutions."""
import argparse
import copy
import gzip
import hashlib
import json
import platform
import signal
import sys
from pathlib import Path
import delegated_raw_v2 as api


def identity(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def own(row):
    return [item for item in row['actual_native_outcomes'] if item['method'] == 'BaseInputConnection.setComposingRegion']


def both(row, change):
    for item in own(row):
        change(item)


def selected_raw(row):
    return [item for item in row['native_sequence'] if item['method'] == 'BaseInputConnection.setComposingRegion']


def main():
    signal.alarm(60)
    parser = argparse.ArgumentParser()
    parser.add_argument('--producer-raw', required=True, type=Path)
    parser.add_argument('--replay-raw', required=True, type=Path)
    parser.add_argument('--receiver-fixture', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    assert not args.output.exists()
    policy, _ = api.load_policy()
    positives = {}
    inputs = {}
    rows = []
    for name, path in [('producer', args.producer_raw), ('fresh-replay', args.replay_raw)]:
        with gzip.open(path, 'rt') as stream:
            actual = [json.loads(line) for line in stream]
        assert len(actual) == 13 and len({row['state'] for row in actual}) == 13
        rows = actual if name == 'producer' else rows
        positives[name] = [api.validate_delegated_raw(row) for row in actual]
        inputs[name] = {'path': str(path), **identity(path)}
    base = next(row for row in rows if row['state'] == 'current')
    negatives = []

    def refuses(name, change, original=base, bridge_only=False):
        row = copy.deepcopy(original)
        change(row)
        try:
            api.validate_receiver_bindings(row, policy) if bridge_only else api.validate_delegated_raw(row)
        except api.DelegatedReceiverRefusal as failure:
            negatives.append({'name': name, 'refused': True, 'reason': str(failure)})
            return
        raise AssertionError('accepted hostile receiver/raw data: ' + name)

    def drop(row, indexes):
        pair = own(row)
        row['actual_native_outcomes'] = [item for item in row['actual_native_outcomes'] if all(item is not pair[index] for index in indexes)]

    def wrong_caller(row):
        neighbor = next(item['production_frames'] for item in row['actual_native_outcomes']
                        if item['production_frames'] and item['production_frames'] != own(row)[0]['production_frames'])
        both(row, lambda item: item.__setitem__('production_frames', copy.deepcopy(neighbor)))

    def swap(row):
        pair = own(row)
        a, b = (row['actual_native_outcomes'].index(item) for item in pair)
        row['actual_native_outcomes'][a], row['actual_native_outcomes'][b] = pair[1], pair[0]

    # Retain all sixteen original pair-level refusal controls against the new composed API.
    for name, mutation in [
        ('wrong-descriptor', lambda row: own(row)[1].__setitem__('descriptor', '(I)Z')),
        ('wrong-order', swap),
        ('wrong-value', lambda row: own(row)[1]['value'].__setitem__('value', False)),
        ('boolean-as-integer', lambda row: own(row)[1]['value'].__setitem__('value', 1)),
        ('wrong-receiver', lambda row: own(row)[1].__setitem__('receiver_identity', 'foreign-actual-receiver')),
        ('wrong-frame', lambda row: own(row)[1].__setitem__('production_frames', [])),
        ('coherent-other-actual-caller', wrong_caller),
        ('wrong-event', lambda row: own(row)[1].__setitem__('native_event_sequence_index', own(row)[1]['native_event_sequence_index'] + 1)),
        ('boolean-event-index', lambda row: own(row)[1].__setitem__('native_event_sequence_index', True)),
        ('wrong-phase', lambda row: own(row)[1].__setitem__('native_event_phase', 'entry')),
        ('missing-outer-completion', lambda row: drop(row, [1])),
        ('missing-inner-completion', lambda row: drop(row, [0])),
        ('missing-both-completions', lambda row: drop(row, [0, 1])),
        ('doubled-completion', lambda row: row['actual_native_outcomes'].append(copy.deepcopy(own(row)[1]))),
        ('missing-explicit-delegation-marker', lambda row: own(row)[1].pop('native_outcome_association')),
        ('extra-native-entry-count', lambda row: row.__setitem__('native_target_entries', 2)),
    ]:
        refuses('retained16/' + name, mutation)

    def coherent_receiver(row):
        row['original_target'] = 'android.view.inputmethod.BaseInputConnection@999'
        both(row, lambda item: item.__setitem__('receiver_identity', row['original_target']))

    def intervening(row):
        at = own(row)[0]['native_event_sequence_index']
        event = copy.deepcopy(row['native_sequence'][at])
        event['phase'] = 'entry'
        row['native_sequence'].insert(at + 1, event)
        row['operation_end_sequence'] += 1

    # Retain the independent nine coherent mutation witnesses.
    for name, mutation in [
        ('wrong-one-frame', lambda row: own(row)[1].__setitem__('production_frames', [])),
        ('missing-both-frames', lambda row: both(row, lambda item: item.__setitem__('production_frames', []))),
        ('coherent-truncated-frame-chain', lambda row: both(row, lambda item: item.__setitem__('production_frames', item['production_frames'][:1]))),
        ('coherent-wrong-event-index', lambda row: both(row, lambda item: item.__setitem__('native_event_sequence_index', item['native_event_sequence_index'] + 1))),
        ('coherent-wrong-receiver', coherent_receiver),
        ('coherent-wrong-native-value', lambda row: both(row, lambda item: item.__setitem__('value', {'kind': 'boolean', 'value': False}))),
        ('wrong-outer-descriptor', lambda row: own(row)[1].__setitem__('descriptor', '(II)Z')),
        ('intervening-raw-native-entry', intervening),
        ('duplicate-outer-completion', lambda row: row['actual_native_outcomes'].append(copy.deepcopy(own(row)[1]))),
    ]:
        refuses('independent9/' + name, mutation)

    def binding(row):
        return next(item for item in row['native_receiver_bindings'] if item['global_identity'] == row['original_target'])

    def altered_raw_ordinal(row):
        for event in selected_raw(row):
            event['receiver_identity'] = 'android.view.inputmethod.BaseInputConnection@row-999999'

    def coherent_ordinal(row):
        altered_raw_ordinal(row)
        item = binding(row)
        item['ordinal'] = 999999
        item['row_identity'] = 'android.view.inputmethod.BaseInputConnection@row-999999'

    def missing_binding(row):
        item = binding(row)
        row['native_receiver_bindings'] = [other for other in row['native_receiver_bindings'] if other is not item]

    def extra_unused(row):
        item = copy.deepcopy(binding(row))
        item['ordinal'] = len(row['native_receiver_bindings']) + 1
        item['row_identity'] = item['class'] + '@row-' + str(item['ordinal'])
        item['global_identity'] = item['class'] + '@999999'
        row['native_receiver_bindings'].append(item)

    for name, mutation in [
        ('root-witness-both-raw-ordinals-replaced', altered_raw_ordinal),
        ('coherent-ordinal-and-binding-replaced', coherent_ordinal),
        ('missing-entire-receiver-map', lambda row: row.pop('native_receiver_bindings')),
        ('missing-selected-original-binding', missing_binding),
        ('duplicate-selected-binding', lambda row: row['native_receiver_bindings'].append(copy.deepcopy(binding(row)))),
        ('unused-extra-receiver-binding', extra_unused),
        ('binding-class-substitution', lambda row: binding(row).__setitem__('class', 'android.view.View')),
        ('binding-global-substitution', lambda row: binding(row).__setitem__('global_identity', binding(row)['class'] + '@999999')),
        ('binding-boolean-ordinal', lambda row: binding(row).__setitem__('ordinal', True)),
        ('binding-floating-ordinal', lambda row: binding(row).__setitem__('ordinal', float(binding(row)['ordinal']))),
        ('mapping-unknown-extra-field', lambda row: binding(row).__setitem__('approved', True)),
        ('absent-both-raw-and-outcome-receiver', lambda row: (selected_raw(row)[0].pop('receiver_identity'), own(row)[0].pop('receiver_identity'))),
        ('compact-only-row', lambda row: (row.pop('native_sequence'), row.pop('frame_sets'))),
    ]:
        refuses('receiver/' + name, mutation)

    fixture = json.loads(args.receiver_fixture.read_bytes())
    same_class_positive = api.validate_receiver_bindings(fixture, policy)
    assert len(fixture['native_receiver_bindings']) == 2 and fixture['native_receiver_bindings'][0]['class'] == fixture['native_receiver_bindings'][1]['class']

    def swap_globals(row):
        a, b = row['native_receiver_bindings']
        a['global_identity'], b['global_identity'] = b['global_identity'], a['global_identity']

    def swap_selected_raw_receiver(row):
        row['native_sequence'][0]['receiver_identity'] = row['native_receiver_bindings'][1]['row_identity']

    for name, mutation in [
        ('swapped-two-actual-same-class-global-bindings', swap_globals),
        ('selected-raw-event-swapped-to-actual-same-class-neighbor', swap_selected_raw_receiver),
        ('duplicate-actual-same-class-global-identity', lambda row: row['native_receiver_bindings'][1].__setitem__('global_identity', row['native_receiver_bindings'][0]['global_identity'])),
        ('duplicate-actual-same-class-ordinal', lambda row: row['native_receiver_bindings'][1].__setitem__('ordinal', 1)),
        ('missing-actual-foreign-receiver-binding', lambda row: row['native_receiver_bindings'].pop()),
    ]:
        refuses('same-class/' + name, mutation, fixture, bridge_only=True)

    for state in ('fatal', 'ordinary-throw-after-callback', 'fatal-throw-after-callback'):
        row = next(row for row in rows if row['state'] == state)
        result = api.validate_delegated_raw(row)
        assert result['actual_normal_native_returns'] == 0 and result['native_result'].startswith('pending')
        refuses('exception/' + state + '/identity-substitution', lambda changed: own(changed)[0].__setitem__('original_exception_identity', 'different@1'), row)
    result = {'schema': 2, 'inputs': inputs, 'same_class_fixture': {'path': str(args.receiver_fixture), **identity(args.receiver_fixture)},
              'api_source': identity(Path(api.__file__)), 'policy_sha256': api.POLICY_SHA256,
              'python': sys.version, 'python_executable': sys.executable, 'platform': platform.platform(),
              'argv': sys.argv, 'positive_rows': positives, 'actual_same_class_bridge_positive': same_class_positive,
              'negative_controls': negatives, 'all_26_actual_rows_consistent': True,
              'all_controls_refused': True, 'native_body_exception_and_helper_results': 'pending; no inference from clean/hook-exception',
              'execution_closure_native_OTA_GA': 'pending', 'qualified': False}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    signal.alarm(0)
    print(json.dumps({'actual_raw_states': 26, 'actual_same_class_bridge': 1, 'refusals': len(negatives), 'qualified': False}))


if __name__ == '__main__':
    main()
