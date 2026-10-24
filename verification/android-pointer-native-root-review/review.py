"""Root read-only review of the failed API37 pointer run; never starts a device."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = ROOT / 'verification/android-pointer-timing-correction/runtime/runtime-1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())


def verify():
    seal = read(RUN / 'artifact-seal.json')
    paths = [p for p in RUN.rglob('*') if p.is_file()]
    assert not any(p.is_symlink() for p in RUN.rglob('*'))
    assert {str(p.relative_to(RUN)) for p in paths} == set(seal) | {'artifact-seal.json'}
    for name, item in seal.items():
        path = RUN / name
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], name
    receipt = read(RUN / 'receipt.json')
    native = read(RUN / 'native-results.json')
    assert native == read(RUN / 'native-results-export.log')
    assert receipt['status'] == 'failed-native-attempt-retained'
    assert receipt['failure'] == "ValueError('native fixture did not pass')"
    assert native['status'] == 'failed' and native['checks'] == 53
    assert native['failure'] == 'java.lang.AssertionError: exact authoritative revision acknowledgement count'
    assert native['cleanupFailure'] is None and native['directNativeCallbackCount'] is None
    assert len(native['assertions']) == 53
    assert [a for a in native['assertions'] if not a['passed']] == [
        {'check': 'exact authoritative revision acknowledgement count', 'passed': False}]
    assert native['injectedMotionEvents'] == native['deliveryAndHistoryRows'] == 14
    assert native['cleanupInjectedMotionEvents'] == 0 and native['gestureActions'] == 3
    assert receipt['physicalTargetsQueried'] is False
    assert receipt['target']['ro.build.version.sdk'] == '37'
    assert receipt['target']['ro.product.cpu.abi'] == 'arm64-v8a'
    assert receipt['target']['ro.kernel.qemu'] == '1'
    assert native['apkSHA256'] == receipt['apkSHA256'] == '57e82e4e98cdc61581c0639603ec6efa500a66d8d2754f6b47ece89c8165d714'
    assert native['sourceClosureSHA256'] == receipt['sourceClosureSHA256'] == '9082e2de1327bd0784d752db5dfbe4484751d565b3410e01e78664321467f5ce'
    assert receipt['apkSHA256'] in (RUN / 'installed-apk-hash.log').read_text()
    assert len(receipt['commands']) == 43
    allowed_nonzero = {'port-before-5586', 'port-before-5587', 'boot-1', 'port-after-5586', 'port-after-5587'}
    for command in receipt['commands']:
        assert sha(RUN / command['output']) == command['sha256']
        assert command['exitCode'] == (1 if command['name'] in allowed_nonzero else 0)
        assert command['ownedCommandGroupCleanup']['after'] == []
    for name, item in native['exports'].items():
        assert (RUN / name).stat().st_size == item['bytes'] and sha(RUN / name) == item['sha256']
        assert (RUN / name).read_bytes() == (RUN / ('export-' + name + '.log')).read_bytes()
    rows = [json.loads(line) for line in (RUN / 'pointer-observations.jsonl').read_text().splitlines()]
    assert len(rows) == 63
    sends = [r for r in rows if r['kind'] == 'worker-send']
    entries = [r for r in rows if r['kind'] == 'activity-entry']
    exits = [r for r in rows if r['kind'] == 'activity-exit']
    assert len(sends) == len(entries) == len(exits) == 14
    assert len({(r['actionId'], r['event']['eventTime']) for r in sends}) == 14
    timing = []
    for worker in sends:
        key = worker['actionId'], worker['event']['eventTime']
        matches = [r for r in entries if (r['actionId'], r['event']['eventTime']) == key]
        ends = [r for r in exits if (r['actionId'], r['event']['eventTime']) == key]
        assert len(matches) == len(ends) == 1
        entry, end = matches[0], ends[0]
        assert worker['exception'] is None and end['exception'] is None and end['returned']
        assert worker['workerBefore'] <= entry['workerIndependentUptime'] <= end['uptime'] <= worker['workerAfter']
        assert worker['event']['eventTime'] <= entry['workerIndependentUptime']
        assert 0 <= worker['workerBefore'] - worker['scheduledUptime'] <= 100
        assert entry['sequence'] == end['sequence'] and entry['event'] == end['event']
        for event in [worker['event'], entry['event']]:
            assert event['flags'] == 0 and event['history'] == [] and event['pointerCount'] == 1
            assert event['actionIndex'] == 0 and event['source'] == 4098
        assert worker['event']['action'] == entry['event']['action']
        timing.append({'action': key[0], 'eventTime': key[1], 'workerBefore': worker['workerBefore'],
                       'entry': entry['workerIndependentUptime'], 'exit': end['uptime'],
                       'workerAfter': worker['workerAfter'], 'lateness': worker['workerBefore'] - worker['scheduledUptime']})
    summaries = native['summaries']
    assert [(s['actionId'], s['repetition'], s['status']) for s in summaries] == [('P01', 1, 'passed'), ('P02', 1, 'passed')]
    assert [(s['before']['revision'], s['after']['revision'], s['before']['nativeChecked'], s['after']['nativeChecked']) for s in summaries] == [('1', '2', False, True), ('2', '3', True, False)]
    assert all(s['commitAcknowledgementCount'] == '1' for s in summaries)
    sequence = read(RUN / 'pointer-sequence-3.json')
    assert sequence['actionId'] == 'P03' and sequence['before']['revision'] == '3'
    action_sends = [r for r in sends if r['actionId'] == 'P03-1']
    assert len(action_sends) == len(sequence['events']) == 10
    for sent, expected in zip(action_sends, sequence['events']):
        event = sent['event']; pointer = event['pointers'][0]
        assert event['eventTime'] == sequence['downTime'] + expected['offsetMilliseconds']
        assert event['action'] == expected['action']
        assert pointer['x'] == expected['x'] and pointer['y'] == expected['y'] and pointer['pressure'] == expected['pressure']
    after = next(r['state'] for r in rows if r['kind'] == 'after-send' and r['actionId'] == 'P03-1')
    before = sequence['before']
    for key in ['revision', 'values', 'nativeValues', 'packetSHA256', 'taskIdentities', 'nativeChecked', 'scrollY', 'editors']:
        assert before[key] == after[key], key
    assert after['current'] and not after['retired'] and not after['rendererRetired'] and after['lastNativeInputFailure'] is None
    assert receipt['cleanup'] == 'stopped' and receipt['ownedEmulatorGroupCleanup']['after'] == []
    cleanup = receipt['extractionCleanup']
    assert cleanup['status'] == 'removed' and cleanup['pathAbsentAfterCleanup'] and not Path(cleanup['path']).exists()
    assert cleanup['files'] == 179 and cleanup['bytes'] == 172952201
    assert cleanup['openHoldersCheck']['exitCode'] == 1 and (RUN / 'extraction-open-holders.log').read_bytes() == b''
    for port in [5586, 5587]:
        assert (RUN / f'port-after-{port}.log').read_bytes() == b''
    assert not receipt['outputBudget']['overflow']
    return {'artifactFiles': len(seal), 'commandOutputs': 43, 'exportedFiles': len(native['exports']),
            'observationRows': 63, 'matchedSynchronousDeliveries': 14, 'assertionsPassed': 52,
            'assertionsFailed': 1, 'completedActions': ['P01-1', 'P02-1'], 'failedAction': 'P03-1',
            'failedActionRevisionBeforeAfter': ['3', '3'], 'nativeChecksAcceptedAsFullMatrix': False,
            'nativeInternalCause': 'not established; diagnosis is separate', 'timing': timing,
            'ownedEmulatorGroupCleaned': True, 'ownedExtractedBytesRemoved': 172952201,
            'apkSHA256': receipt['apkSHA256'], 'sourceClosureSHA256': receipt['sourceClosureSHA256'],
            'target': receipt['target'], 'physicalTargetsQueried': False}


if __name__ == '__main__':
    result = verify()
    if '--record' in sys.argv:
        assert not (HERE / 'receipt.json').exists(), 'preserve the root review'
        commands = []
        for argv, name in [([sys.executable, '-B', 'verification/android-pointer-timing-correction/check_packet.py'], 'host-packet-replay'),
                           (['ps', '-axo', 'pid=,pgid=,stat=,command='], 'processes-after')]:
            run = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
            output = HERE / (name + '.log'); output.write_bytes(run.stdout + run.stderr)
            commands.append({'argv': argv, 'exitCode': run.returncode, 'output': output.name, 'sha256': sha(output)})
            assert run.returncode == 0
        group = read(RUN / 'receipt.json')['ownedEmulatorGroupCleanup']['group']
        process_lines = (HERE / 'processes-after.log').read_text().splitlines()
        assert not any(len(line.split()) >= 2 and line.split()[1] == str(group) for line in process_lines)
        unrelated = [line.strip() for line in process_lines if '-avd morse-api37' in line]
        bindings = {str(p.relative_to(ROOT)): {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in RUN.rglob('*') if p.is_file()}
        for p in [Path(__file__), HERE / 'host-packet-replay.log', HERE / 'processes-after.log']:
            bindings[str(p.relative_to(ROOT))] = {'bytes': p.stat().st_size, 'sha256': sha(p)}
        result.update({'schema': 1, 'status': 'verified-failed-native-attempt', 'rootAcceptedFullPointerMatrix': False,
                       'command': [sys.executable, '-B', str(Path(__file__)), '--record'], 'pythonVersion': sys.version,
                       'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       'commands': commands, 'unrelatedEmulatorObservedUntouched': unrelated,
                       'bindings': bindings, 'gaAccepted': False})
        (HERE / 'receipt.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    else:
        saved = read(HERE / 'receipt.json')
        for name, binding in saved['bindings'].items():
            assert sha(ROOT / name) == binding['sha256'] and (ROOT / name).stat().st_size == binding['bytes']
    print(json.dumps({k: v for k, v in result.items() if k not in ['bindings', 'timing', 'commands']}))
