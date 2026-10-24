#!/usr/bin/env python3
"""Read exact failed-run inputs and documentation; never discover/start targets."""
import base64
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SDK = Path('/opt/homebrew/share/android-commandlinetools')
EMULATOR = SDK / 'emulator/emulator'
OUT = HERE / 'analysis-1'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    OUT.mkdir(exist_ok=False)
    receipt = {
        'schema': 1,
        'startedUTC': now(),
        'scope': 'Read-only diagnosis of two exact failed owned boot attempts; no runtime acceptance',
        'collectorSHA256': digest(Path(__file__).read_bytes()),
        'targetDiscovery': False,
        'emulatorLaunches': 0,
        'adbCommands': 0,
        'uiOrCapture': False,
        'processSignals': 0,
        'avdOrSharedNetsimMutations': False,
        'commands': [],
        'inputFiles': [],
        'assertions': [],
    }

    def command(name, argv):
        started = now()
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=15)
        output = result.stdout + result.stderr
        (OUT / (name + '.log')).write_bytes(output)
        receipt['commands'].append({
            'name': name, 'argv': [str(s) for s in argv], 'cwd': str(ROOT),
            'startedUTC': started, 'finishedUTC': now(),
            'exitCode': result.returncode, 'output': name + '.log',
            'outputSHA256': digest(output),
        })
        assert result.returncode == 0, name
        return output.decode()

    def bind(path):
        data = path.read_bytes()
        receipt['inputFiles'].append({
            'path': str(path), 'bytes': len(data), 'sha256': digest(data),
        })
        return data

    def check(label, passed):
        receipt['assertions'].append({'name': label, 'passed': passed})
        assert passed, label

    receipt['observedSourceRevision'] = command('source-revision', ['git', 'rev-parse', 'HEAD']).strip()
    command('python-version', [sys.executable, '--version'])
    command('macos-version', ['/usr/bin/sw_vers'])
    command('emulator-version', [str(EMULATOR), '-version'])
    for option in ('port', 'gpu', 'feature', 'netsim-args', 'packet-streamer-endpoint'):
        command('emulator-help-' + option, [str(EMULATOR), '-help-' + option])
    command('netsimd-help', [str(SDK / 'emulator/netsimd'), '--help'])
    command('netsimd-version', [str(SDK / 'emulator/netsimd'), '--version'])

    for path in (EMULATOR, SDK / 'emulator/qemu/darwin-aarch64/qemu-system-aarch64-headless',
                 SDK / 'emulator/netsimd', SDK / 'emulator/source.properties',
                 SDK / 'emulator/lib/advancedFeatures.ini'):
        bind(path)

    runner = ROOT / 'verification/android-coordinator-runner-cleanup/run.py'
    check('accepted cleanup runner unchanged', digest(bind(runner)) ==
          'cc77d1e449b0f946e12d1ed345b29a8eed392e635462c70c76e81c84714f225e')
    historical = json.loads(bind(ROOT / 'verification/android-native-appearance-v2/emulator-session.json'))
    historical_receipt = json.loads(bind(ROOT / 'verification/android-native-appearance-v2/candidate-16/receipt.json'))
    historical_version = bind(ROOT / 'verification/android-native-appearance-v2/candidate-16/emulator-version.log')
    source_metadata = {path: digest(bind(Path(path))) for path in historical['metadataSHA256']}
    check('current exact source metadata matches historical session', source_metadata == historical['metadataSHA256'])
    save('historical-summary.json', {
        'session': historical,
        'receiptStatus': historical_receipt.get('status'),
        'receiptSourceRevision': historical_receipt.get('sourceRevision'),
        'receiptKeys': sorted(historical_receipt),
        'emulatorVersion': historical_version.decode(),
    })

    runs = []
    for number, pid, stamp in ((1, 12041, '070947'), (2, 13312, '071308')):
        folder = ROOT / f'verification/android-coordinator-runner-cleanup/runtime-{number}'
        run = json.loads(bind(folder / 'receipt.json'))
        instance = json.loads(bind(folder / 'owned-instance.json'))
        log = bind(folder / 'emulator.log').decode()
        check(f'runtime-{number} owned PID matches', instance['pid'] == pid)
        check(f'runtime-{number} historical argv matches', instance['argv'] == historical['argv'])
        check(f'runtime-{number} metadata matches', run['metadataSHA256'] == historical['metadataSHA256'])
        check(f'runtime-{number} failed before boot', run['failure'] == "RuntimeError('owned emulator exited before boot')")
        check(f'runtime-{number} no APK install', not any('install' in c['argv'] for c in run['commands']))
        check(f'runtime-{number} owned process group absent', run['ownedEmulatorGroupCleanup']['after'] == [])
        check(f'runtime-{number} extraction removed', run['extractionCleanup']['pathAbsentAfterCleanup'])
        boot = []
        for c in run['commands']:
            if c['name'].startswith('boot-'):
                text = bind(folder / c['output']).decode().strip()
                boot.append({'name': c['name'], 'startedUTC': c['startedUTC'], 'exitCode': c['exitCode'], 'output': text})
        recorded_processes = bind(folder / 'processes-before.log').decode()
        report_path = Path.home() / f'Library/Logs/DiagnosticReports/qemu-system-aarch64-headless-2026-10-24-{stamp}.ips'
        raw = bind(report_path).decode()
        header_text, body_text = raw.split('\n', 1)
        header, body = json.loads(header_text), json.loads(body_text)
        check(f'runtime-{number} crash report PID matches', body['pid'] == pid)
        check(f'runtime-{number} crash report process matches', body['procName'] == 'qemu-system-aarch64-headless')
        threads = []
        for index, thread in enumerate(body['threads']):
            frames = [{
                'symbol': frame.get('symbol'), 'imageOffset': frame.get('imageOffset'),
                'symbolLocation': frame.get('symbolLocation'),
                'image': body['usedImages'][frame['imageIndex']].get('path')
                    if frame.get('imageIndex') is not None and frame['imageIndex'] < len(body['usedImages']) else None,
            } for frame in thread.get('frames', [])]
            threads.append({'index': index, 'name': thread.get('name'), 'triggered': thread.get('triggered', False), 'frames': frames})
        symbols = [[f.get('symbol') or '' for f in t['frames']] for t in threads]
        check(f'runtime-{number} fault thread is hang detector', any('CrashReporter::GenerateDumpAndDie' in s for s in symbols[body['faultingThread']]))
        blocked = [t['index'] for t, fs in zip(threads, symbols)
                   if any('NetsimWifiForwarder::init' in s for s in fs)
                   and any('netsim::packet::GetChannel' in s for s in fs)
                   and any('virtio_wifi_device_realize' in s for s in fs)]
        check(f'runtime-{number} main device initialization waits on netsim', len(blocked) == 1)
        crash = {
            'sourcePath': str(report_path), 'sourceSHA256': digest(raw.encode()),
            'pid': pid, 'parentPid': body['parentPid'], 'procLaunch': body['procLaunch'],
            'captureTime': body['captureTime'], 'osVersion': header['os_version'],
            'exception': body['exception'], 'termination': body['termination'],
            'faultingThread': body['faultingThread'], 'netsimBlockedThread': blocked[0],
            'threads': threads,
        }
        save(f'runtime-{number}-crash-summary.json', crash)
        runs.append({
            'name': f'runtime-{number}', 'pid': pid, 'argv': instance['argv'],
            'sourceRevision': run['sourceRevision'], 'sourceClosureSHA256': run['sourceClosureSHA256'],
            'observedUTC': run['observedUTC'], 'finishedUTC': run['finishedUTC'],
            'warningsAndErrors': [line for line in log.splitlines() if any(word in line for word in ('WARNING', 'ERROR', 'crashdata'))],
            'recordedSharedNetsim': [line for line in recorded_processes.splitlines() if '/emulator/netsimd ' in line],
            'bootPolls': boot, 'crashSummary': f'runtime-{number}-crash-summary.json',
            'cleanup': {'ownedGroup': run['ownedEmulatorGroupCleanup'], 'extraction': run['extractionCleanup']},
        })
    save('run-summary.json', runs)
    manifest = sorted(receipt['inputFiles'], key=lambda f: f['path'])
    receipt['analysisInputTreeSHA256'] = digest(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode())
    for entry in manifest:
        check('input unchanged at finish: ' + entry['path'], digest(Path(entry['path']).read_bytes()) == entry['sha256'])
    receipt['finishedUTC'] = now()
    receipt['status'] = 'passed-read-only-evidence-checks; no-native-test-pass'
    save('receipt.json', receipt)
    print(json.dumps({'status': receipt['status'], 'assertions': len(receipt['assertions']),
                      'inputTreeSHA256': receipt['analysisInputTreeSHA256'], 'output': str(OUT)}))


if __name__ == '__main__':
    main()
