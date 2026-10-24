"""Root read-only replay of exact baseline native evidence and cleanup."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUNNER = ROOT / 'verification/android-authored-toggle-input-runner'
RUN = RUNNER / 'runtime/runtime-2'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())

def main():
    seal = read(RUN / 'artifact-seal.json')
    assert not any(p.is_symlink() for p in RUN.rglob('*'))
    files = {str(p.relative_to(RUN)) for p in RUN.rglob('*') if p.is_file()}
    assert files == set(seal) | {'artifact-seal.json'}
    for name, value in seal.items():
        p = RUN / name
        assert sha(p) == value['sha256'] and p.stat().st_size == value['bytes'], name
    receipt = read(RUN / 'receipt.json'); native = read(RUN / 'native-results.json')
    assert native == read(RUN / 'native-results-export.log')
    assert receipt['status'] == 'actual-API37-private-pointer-bounded-subset-passed'
    assert native['status'] == 'passed' and native['failure'] is None and native['cleanupFailure'] is None
    assert native['checks'] == len(native['assertions']) == 429 and all(a['passed'] for a in native['assertions'])
    assert native['gestureActions'] == len(native['summaries']) == 20
    assert native['injectedMotionEvents'] == native['deliveryAndHistoryRows'] == 124
    assert native['cleanupInjectedMotionEvents'] == 0 and native['directNativeCallbackCount'] is None
    assert native['apkSHA256'] == receipt['apkSHA256'] == '24d75ecc19d08f44adc95e2db123936687929ca5a9fcd71f19189865240f6d18'
    assert native['sourceClosureSHA256'] == receipt['sourceClosureSHA256'] == '509ef6a00bbaf034ebbe9dd6d8d3b8716fe96d9600e7fe8fa92fac41ebca3f99'
    assert receipt['apkSHA256'] in (RUN / 'installed-apk-hash.log').read_text()
    assert receipt['target']['ro.build.version.sdk'] == '37' and receipt['target']['ro.product.cpu.abi'] == 'arm64-v8a'
    assert receipt['target']['ro.kernel.qemu'] == '1' and not receipt['physicalTargetsQueried']
    for command in receipt['commands']:
        assert sha(RUN / command['output']) == command['sha256']
        assert not command['ownedCommandGroupCleanup']['after']
        if command['exitCode']:
            assert command['exitCode'] == 1 and command['name'] in ['boot-1', 'port-before-5586', 'port-before-5587', 'port-after-5586', 'port-after-5587']
    for name, value in native['exports'].items():
        p = RUN / name
        assert sha(p) == value['sha256'] and p.stat().st_size == value['bytes']
        assert p.read_bytes() == (RUN / ('export-' + name + '.log')).read_bytes()
    rows = [json.loads(s) for s in (RUN / 'pointer-observations.jsonl').read_text().splitlines()]
    sends = [r for r in rows if r['kind'] == 'worker-send']
    entries = [r for r in rows if r['kind'] == 'activity-entry']
    exits = [r for r in rows if r['kind'] == 'activity-exit']
    assert len(sends) == len(entries) == len(exits) == 124
    timing = []
    for sent in sends:
        key = sent['actionId'], sent['event']['eventTime']
        start = [r for r in entries if (r['actionId'], r['event']['eventTime']) == key]
        end = [r for r in exits if (r['actionId'], r['event']['eventTime']) == key]
        assert len(start) == len(end) == 1
        start, end = start[0], end[0]
        assert sent['exception'] is None and end['exception'] is None and end['returned']
        assert sent['workerBefore'] <= start['workerIndependentUptime'] <= end['uptime'] <= sent['workerAfter']
        assert start['sequence'] == end['sequence'] and start['event'] == end['event']
        lateness = sent['workerBefore'] - sent['scheduledUptime']; assert 0 <= lateness <= 100
        timing.append(lateness)
    expected = [(f'P{i:02}', n, str(int(i != 5))) for n in range(1, 4) for i in range(1, 6)]
    expected += [('P06',1,'0'),('G01',1,'0'),('G02a',1,'0'),('G02b',1,'1'),('G03',1,None)]
    assert [(s['actionId'],s['repetition'],s['commitAcknowledgementCount']) for s in native['summaries']] == expected
    for s in native['summaries']:
        assert s['status'] == 'passed'
        if s['actionId'] == 'P03':
            assert s['before']['nativeChecked'] is False and s['after']['nativeChecked'] is True
            assert int(s['after']['revision']) == int(s['before']['revision']) + 1
    assert receipt['cleanup'] == 'stopped' and not receipt['ownedEmulatorGroupCleanup']['after']
    clean = receipt['extractionCleanup']; assert clean['status'] == 'removed' and clean['pathAbsentAfterCleanup']
    assert clean['files'] == 183 and clean['bytes'] == 172984646 and not Path(clean['path']).exists()
    assert clean['openHoldersCheck']['exitCode'] == 1 and not (RUN / 'extraction-open-holders.log').read_bytes()
    for port in [5586,5587]: assert not (RUN / f'port-after-{port}.log').read_bytes()
    assert not receipt['outputBudget']['overflow']
    # Replay the selected complete packet/state/timing oracle without any device action.
    sys.path.insert(0, str(RUNNER))
    import run
    runner, _, _ = run.load_runner()
    runner._pointer_validate_native(native, RUN, read(RUN / 'source-identity-preinstall.json'))
    processes = subprocess.check_output(['ps', '-axo', 'pid=,pgid=,stat=,command='])
    (HERE / 'baseline-processes-after.log').write_bytes(processes)
    group = str(receipt['ownedEmulatorGroupCleanup']['group'])
    assert not any(len(s.split()) >= 2 and s.split()[1] == group for s in processes.decode().splitlines())
    result = {'schema':1, 'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'status':'passed-root-bounded-pointer-matrix-review', 'nativeAssertions':429, 'actions':20,
              'workerEvents':124, 'matchedSynchronousDeliveries':124, 'observations':len(rows),
              'maxWorkerLatenessMilliseconds':max(timing), 'nativeDurationMilliseconds':native['durationMilliseconds'],
              'exportedFiles':len(native['exports']), 'commandOutputs':len(receipt['commands']),
              'ownedCleanupVerified':True, 'supplementDispatchAuthorized':True, 'gaAccepted':False,
              'scope':'Exact candidate3 API37 arm64 original20-action private coordinator pointer matrix only; component preview/key/AX and renderer authority beyond fixture remain pending.',
              'bindings':{str(p.relative_to(ROOT)):sha(p) for p in RUN.rglob('*') if p.is_file()}}
    for p in [Path(__file__), HERE / 'baseline-processes-after.log']:
        result['bindings'][str(p.relative_to(ROOT))] = sha(p)
    out = HERE / 'baseline-acceptance.json'; assert not out.exists(); out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'bindings'}))

if __name__ == '__main__':
    main()
