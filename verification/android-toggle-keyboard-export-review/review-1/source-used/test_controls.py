#!/usr/bin/env python3
"""Host rejection controls against the actual immutable completed native export."""
import argparse
import copy
import json
import sys
import tempfile
from pathlib import Path
from types import ModuleType
import collector
import review_support as support


def test(work_root):
    checks = 0
    rejected = []
    oracle = collector.load()
    native = support.read(support.RUNTIME / 'toggle-supplement-results.json')
    metadata = support.read(support.RUNTIME / 'source-identity-predispatch.json')

    def check(value, label):
        nonlocal checks
        checks += 1
        if not value:
            raise AssertionError(label)

    def reject(label, action, contains=None):
        nonlocal checks
        try:
            action()
        except (ValueError, AssertionError, TypeError, KeyError, IndexError) as failure:
            if contains is not None:
                check(contains in str(failure), label + ' failure identity: ' + str(failure))
            checks += 1
            rejected.append({'name': label, 'failure': str(failure), 'type': type(failure).__name__})
            return
        raise AssertionError(label + ' unexpectedly accepted')

    def mutate(label, change, contains=None):
        value = copy.deepcopy(native)
        change(value)
        reject(label, lambda: oracle.validate(value, work_root, metadata), contains)

    result = oracle.validate(native, work_root, metadata)
    check(result['cases'] == 45 and result['assertions'] == 239 and result['originalAssertionCounter'] == 213,
          'actual native complete original case and assertion counters')
    check(result['keyboardSetup'] == {'focusHelpers': 4, 'keyboardSetupEvents': 8, 'nativeKeyTraceRows': 14,
                                     'nativeModeTraceRows': 1, 'focusObservationRows': 32,
                                     'platformButtonPositiveControls': 4}, 'actual full finite keyboard evidence')
    check(result['fixtureCountedEvents'] == 118 and result['boundedConstructedMotionEvents'] == 119,
          'actual counted MotionEvents separate from historical MotionEvent and navigation keys')
    original = (support.PRODUCER / 'keyboard_oracle.py').read_text()
    corrected = collector.derive()
    for name, before, after in reversed(collector.CHANGES):
        check(corrected.count(after) == 1, 'exact sole changed site ' + name)
        corrected = corrected.replace(after, before, 1)
    check(corrected == original, 'entire original collector and predicates recover exactly')
    reject('modified original oracle source', lambda: collector.derive(original + '\n'), 'original keyboard oracle drift')

    for trace_name, label in [('nativeKeyTrace', 'key'), ('nativeModeTrace', 'mode')]:
        for invalid in (True, False, -1, 1, 0.0, 0.5, '0', None, float('nan')):
            mutate(label + ' sequence invalid ' + repr(invalid),
                   lambda value, t=trace_name, invalid=invalid: value['keyboardSetup'][t][0].update(sequence=invalid),
                   'trace contiguous integer sequence')
        mutate(label + ' sequence missing', lambda value, t=trace_name: value['keyboardSetup'][t][0].pop('sequence'),
               'trace contiguous integer sequence')
        mutate(label + ' unknown extra row field', lambda value, t=trace_name: value['keyboardSetup'][t][0].update(arbitrary=True),
               'trace exact schema')
        mutate(label + ' sequence alias rejected',
               lambda value, t=trace_name: value['keyboardSetup'][t][0].update(ordinal=value['keyboardSetup'][t][0].pop('sequence')),
               'trace contiguous integer sequence')
    mutate('key sequence gap', lambda value: value['keyboardSetup']['nativeKeyTrace'][4].update(sequence=5), 'trace contiguous integer sequence')
    mutate('key sequence duplicate', lambda value: value['keyboardSetup']['nativeKeyTrace'][4].update(sequence=3), 'trace contiguous integer sequence')
    mutate('key sequence row order', lambda value: value['keyboardSetup']['nativeKeyTrace'].reverse(), 'trace contiguous integer sequence')
    mutate('mode duplicate sequence row', lambda value: value['keyboardSetup']['nativeModeTrace'].append(copy.deepcopy(value['keyboardSetup']['nativeModeTrace'][0])), 'trace contiguous integer sequence')
    mutate('extra contiguous mode row still rejected', lambda value: value['keyboardSetup']['nativeModeTrace'].append({**value['keyboardSetup']['nativeModeTrace'][0], 'sequence': 1}), 'no extra native key/mode observations')

    for key in ('assertions', 'addedSetupAssertions', 'originalAssertionCounter', 'addedScrollSetupAssertions',
                'addedKeyboardSetupAssertions', 'keyboardSetupEvents'):
        for invalid in (True, -1, 0.5, float('nan'), 9999999):
            mutate('invalid counter ' + key + ' ' + repr(invalid), lambda value, key=key, invalid=invalid: value.update({key: invalid}))
    mutate('counter total mismatch', lambda value: value.update(assertions=240))
    mutate('setup subtotal mismatch', lambda value: value.update(addedScrollSetupAssertions=5))
    mutate('original assertion minimum cannot be supplied by setup', lambda value: value.update(originalAssertionCounter=89, assertions=115), 'component assertion minimum')
    mutate('unknown top field', lambda value: value.update(arbitrary=True), 'keyboard supplement exact schema')
    mutate('native failure is never accepted', lambda value: value.update(status='failed-retained', failure='native focus admitted'), 'component native fixture failed')
    for key in ('apkSHA256', 'sourceClosureSHA256'):
        mutate('wrong source/executable identity ' + key, lambda value, key=key: value.update({key: '0' * 64}), 'component identity ' + key)
    for index in range(45):
        mutate('original case ' + str(index + 1) + ' outcome rejected', lambda value, index=index: value['cases'][index].update(status='failed'), 'component case order/outcome')
    mutate('partial 44-case matrix rejected', lambda value: value['cases'].pop(), 'complete exact component case matrix required')
    mutate('reordered original case matrix rejected', lambda value: value['cases'].reverse(), 'component case order/outcome')
    mutate('original proposal count changed', lambda value: value['cases'][39].update(proposals=0), 'observed proposal/fixture acknowledgement count')
    mutate('original fixture acknowledgement count changed', lambda value: value['cases'][39].update(fixtureAcknowledgements=0), 'observed proposal/fixture acknowledgement count')
    mutate('fixture cannot claim engine authority', lambda value: value.update(authoritativeCommits=1), 'component scope cannot imply engine authority')
    mutate('MotionEvent counter changed', lambda value: value.update(events=119), 'fixture counter must equal direct touch observations plus eighteen worker requests')
    mutate('direct touch route changed', lambda value: value['observations'][0].update(route='fabricated'), 'component direct touch route')
    mutate('final pressed cleanup changed', lambda value: value['observations'][-1].update(pressed=True), 'component final cleanup observation')

    mutations = [
        ('missing setup pair', lambda value: value['keyboardSetup']['requests'].pop()),
        ('missing actual key delivery', lambda value: value['keyboardSetup']['nativeKeyTrace'].pop()),
        ('direct key route instead of Activity hook', lambda value: value['keyboardSetup']['nativeKeyTrace'][0].update(stage='toggle.dispatchKeyEvent')),
        ('activation key instead of navigation', lambda value: value['keyboardSetup']['requests'][0].update(keyCode=23)),
        ('key source mismatch', lambda value: value['keyboardSetup']['nativeKeyTrace'][0].update(source=0)),
        ('key repeat mismatch', lambda value: value['keyboardSetup']['nativeKeyTrace'][0].update(repeat=1)),
        ('key time mismatch', lambda value: value['keyboardSetup']['nativeKeyTrace'][0].update(eventTime=1)),
        ('missing native mode transition', lambda value: value['keyboardSetup']['nativeModeTrace'].clear()),
        ('wrong native mode transition', lambda value: value['keyboardSetup']['nativeModeTrace'][0].update(inTouchMode=True)),
        ('mode observer saturation', lambda value: value['keyboardSetup'].update(modeDropped=1)),
        ('key trace loss', lambda value: value['keyboardSetup'].update(dropped=1)),
        ('observer failure', lambda value: value['keyboardSetup'].update(observerFailures=1)),
        ('missing focus observation', lambda value: value['keyboardSetup']['observations'].pop()),
        ('wrong focus stage', lambda value: value['keyboardSetup']['observations'][2].update(stage='skip')),
        ('native touch mode persists', lambda value: value['keyboardSetup']['observations'][2]['state']['toggle'].update(inTouchMode=True)),
        ('Button request failed', lambda value: value['keyboardSetup']['observations'][3].update(requestReturned=False)),
        ('original toggle request failed', lambda value: value['keyboardSetup']['observations'][5].update(requestReturned=False)),
        ('control remains attached', lambda value: value['keyboardSetup']['observations'][4]['state']['control'].update(attached=True)),
        ('toggle lost focus', lambda value: value['keyboardSetup']['observations'][6]['state'].update(toggleIsFocusOwner=False)),
        ('wrong focus owner identity', lambda value: value['keyboardSetup']['observations'][6]['state']['decorFocusOwner'].update(identity=999)),
        ('ancestor blocks focus', lambda value: value['keyboardSetup']['observations'][2]['state']['ancestors'][0].update(descendantFocusability=393216)),
        ('incomplete ancestors', lambda value: value['keyboardSetup']['observations'][2]['state'].update(ancestorChainComplete=False)),
        ('changed product focus policy', lambda value: value['keyboardSetup']['observations'][2]['state']['toggle'].update(focusableInTouchMode=True)),
        ('non-platform positive control', lambda value: value['keyboardSetup']['observations'][3]['state']['control'].update({'class': 'fixture.BypassButton'})),
        ('toggle outside owned visible area', lambda value: value['keyboardSetup']['observations'][2]['state'].update(toggleOwnedVisible=False)),
        ('setup activates toggle', lambda value: value['keyboardSetup']['observations'][2].update(proposals=1)),
        ('setup geometry changed', lambda value: value['keyboardSetup']['observations'][2]['state']['toggle']['frame'].__setitem__(0, 999)),
        ('unknown focus field', lambda value: value['keyboardSetup']['observations'][2].update(arbitrary=True)),
        ('unknown request field', lambda value: value['keyboardSetup']['requests'][0].update(arbitrary=True)),
    ]
    for label, mutation in mutations:
        mutate(label, mutation)

    failed = support.read(support.RESET / 'runtime/runtime-1/toggle-supplement-results.json')
    check(len(failed['cases']) == 39 and failed['status'] == 'failed-retained' and failed['failure'] == 'java.lang.AssertionError: native focus admitted',
          'actual retained original 39-case native failure identity')
    reject('actual failed 39-case export rejected by corrected keyboard collector', lambda: oracle.validate(failed, work_root, metadata), 'keyboard supplement exact schema')
    reset_source = (support.PRODUCER / 'reset_counter_oracle.py').read_bytes()
    check(support.data_bind(reset_source)['sha256'] == 'd5d21ff8553d8424d902103ebc5767e2b069b2c16a56c65972649b7428b6f046', 'frozen finite reset adapter identity')
    previous = sys.modules.get('support')
    try:
        sys.modules['support'] = support
        reset = ModuleType('sealed_failed_reset_adapter')
        exec(compile(reset_source, 'sealed-reset-counter-oracle', 'exec'), reset.__dict__)
    finally:
        if previous is None:
            sys.modules.pop('support', None)
        else:
            sys.modules['support'] = previous
    reject('actual failed 39-case export remains native failure after its exact two-counter adaptation',
           lambda: reset.validate(failed, work_root, {key: failed[key] for key in ('apkSHA256', 'sourceClosureSHA256')}),
           'component native fixture failed')

    with tempfile.TemporaryDirectory(prefix='.controls-', dir=work_root) as folder:
        out = Path(folder)
        replay = collector.replay(oracle, out)
        check(replay['oracle']['cases'] == 45 and len(replay['replayedReads']) == 5, 'actual finite collector accepts complete retained five-read replay')
        reject('original collector failure reproduced on unchanged raw bytes', lambda: collector.replay(collector.load(False), out), 'native mode trace exact schema')
        instrument = (support.RUNTIME / 'actual-native-component.log').read_bytes()
        reject('native export hash mismatch', lambda: collector.replay(oracle, out, instrument=instrument.replace(b'exportSHA256=77', b'exportSHA256=00')), 'native component JSON export binding')
        reject('instrumentation process failed', lambda: collector.replay(oracle, out, code=1), 'component instrumentation failed')
        reject('native instrumentation status failed', lambda: collector.replay(oracle, out, instrument=instrument.replace(b'status=passed-component-only', b'status=failed-retained')), 'component instrumentation failed')
        reject('missing original screenshot', lambda: collector.replay(oracle, out, overrides={'export-preview-true-true.png': (1, b'')}), 'four actual PNG exports required')
        reject('invalid original screenshot', lambda: collector.replay(oracle, out, overrides={'export-preview-true-true.png': (0, b'x' * 100)}), 'component PNG viewport')
        reject('unknown offline replay response unavailable', lambda: collector.replay(oracle, out, overrides={'native-results-export': (1, b'')}), 'bounded component result export unavailable')
    reject('duplicate JSON fields', lambda: support.read_bytes(b'{"sequence":0,"sequence":1}'), 'duplicate JSON key')
    reject('nonfinite JSON value', lambda: support.read_bytes(b'{"sequence":NaN}'), 'nonfinite JSON constant')
    return {'schema': 1, 'status': 'passed-offline-controls-on-immutable-actual-native-export',
            'checks': checks, 'rejections': rejected, 'rejectedControls': len(rejected),
            'positiveControlUsesActualNativeExport': True, 'fabricatedNativeAcceptance': False,
            'actualFailed39CaseExportRemainsFailed': True, 'originalCollectorFailureReproduced': True,
            'nativeCommandsExecuted': 0, 'GitCommandsExecuted': 0, 'CUACommandsExecuted': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--work-root', type=Path, required=True)
    args = parser.parse_args()
    support.need(args.work_root.resolve().is_relative_to(support.HERE) and args.work_root.is_dir(), 'owned review work root required')
    print(json.dumps(test(args.work_root), indent=2, sort_keys=True, allow_nan=False))
