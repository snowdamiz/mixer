#!/usr/bin/env python3
"""One explicit root-selected dispatch; bounded outer observation, no native retry."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PYTHON = '/opt/homebrew/opt/python@3.14/bin/python3.14'
PRODUCER = ROOT / 'verification/apple-focus-reference-runtime-v5-namespace-correction'
PACKET = '6c57bc5552a4f7e0e21ff1fdd589b270aa98b483f366f78bd88de2e26c0fd7dc'
DEVELOPER = '/Applications/Xcode_26.6.app/Contents/Developer'
OUTER_SECONDS = 1200
INTERRUPT_GRACE = 120
SIGNAL_GRACE = 8
OUTPUT_LIMIT = 32 * 1024 * 1024
GROUP_OBSERVATIONS = []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def group_absent(group):
    try:
        os.killpg(group, 0)
    except ProcessLookupError:
        return True
    except PermissionError as error:
        row = dict(targetProcessGroup=group, signalZero='unknown-permission-error',
                   error=str(error), fallbackArgv=['/bin/ps','-axo','pid=,ppid=,pgid='])
        try:
            result = subprocess.run(row['fallbackArgv'], capture_output=True, timeout=5)
            row.update(exitCode=result.returncode, stderr=result.stderr.decode(errors='replace'))
            if result.returncode != 0:
                raise RuntimeError('Complete process table query failed')
            entries = [tuple(map(int,line.split())) for line in result.stdout.decode().splitlines() if line.strip()]
            if not all(len(entry) == 3 for entry in entries):
                raise ValueError('Incomplete process table row')
            matching = [entry for entry in entries if entry[2] == group]
            row.update(complete=True, matchingRows=matching, state='present' if matching else 'absent')
            GROUP_OBSERVATIONS.append(row)
            return not matching
        except BaseException as fallback_error:
            row.update(complete=False, state='unknown', failureType=type(fallback_error).__name__, failure=str(fallback_error))
            GROUP_OBSERVATIONS.append(row)
            return None
    except BaseException as error:
        GROUP_OBSERVATIONS.append(dict(targetProcessGroup=group,state='unknown',complete=False,
                                       failureType=type(error).__name__,failure=str(error)))
        return None
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root-selection', required=True)
    parser.add_argument('--root-selection-sha256', required=True)
    args = parser.parse_args()
    selection = Path(args.root_selection)
    assert selection.is_absolute() and selection.resolve() == selection and not selection.is_symlink()
    raw = selection.read_bytes()
    assert sha(raw) == args.root_selection_sha256
    root = json.loads(raw)
    assert root['schema'] == 'mixer.apple-focus-reference-root-selection.5'
    assert root['packetSHA256'] == PACKET
    assert sha((PRODUCER / 'packet.json').read_bytes()) == PACKET
    output = BASE / ('outer-run-' + root['runID'])
    output.mkdir(mode=0o755)
    argv = [PYTHON, '-B', str(PRODUCER / 'prepare.py'), 'dispatch',
            '--reviewed-packet', PACKET, '--root-selection', str(selection),
            '--root-selection-sha256', args.root_selection_sha256]
    receipt = dict(schema=1, scope='Outer process observation only; no changed native budgets or retry',
                   startedUTC=utc(), argv=argv, cwd=str(ROOT),
                   rootSelectionSHA256=sha(raw), runID=root['runID'],
                   sourceRevisionLabel='7744c1cc28b24a46f4339b25b38ce4d0cf76cbe8',
                   sourceRevisionMeaning='Existing root decision label; no Git query',
                   sourceTreeSHA256=root['sourceTreeSHA256'], productArchiveSHA256=root['productArchiveSHA256'],
                   driverSHA256=sha(Path(__file__).read_bytes()), python=sys.version,
                   pythonExecutable=str(Path(sys.executable).resolve()),
                   outerSeconds=OUTER_SECONDS, interruptGraceSeconds=INTERRUPT_GRACE,
                   signalGraceSeconds=SIGNAL_GRACE, signals=[], physicalPhones='disconnected-deferred',
                   emergencyNativeCleanupOwner='root; outer observer never deletes devices or signals child sessions')
    write(output / 'intent.json', receipt)
    process = subprocess.Popen(argv, cwd=ROOT, env={**os.environ, 'DEVELOPER_DIR': DEVELOPER,
                               'PYTHONDONTWRITEBYTECODE': '1'}, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    receipt.update(PID=process.pid, processGroup=process.pid, startNewSession=True)
    write(output / 'started.json', receipt)
    selector = selectors.DefaultSelector()
    streams = {}
    for name, pipe in [('stdout', process.stdout), ('stderr', process.stderr)]:
        os.set_blocking(pipe.fileno(), False)
        selector.register(pipe, selectors.EVENT_READ, name)
        streams[name] = dict(file=(output / (name + '.log')).open('xb'),
                             observedBytes=0, retainedBytes=0, digest=hashlib.sha256(), eof=False)
    started = time.monotonic()
    deadline = started + OUTER_SECONDS
    stage = 0
    timed_out = False
    observation_error = None
    try:
        while True:
            for key, _ in selector.select(timeout=0.25):
                row = streams[key.data]
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    row['eof'] = True
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                row['observedBytes'] += len(chunk)
                room = max(0, OUTPUT_LIMIT - row['retainedBytes'])
                retained = chunk[:room]
                row['file'].write(retained)
                row['digest'].update(retained)
                row['retainedBytes'] += len(retained)
            code = process.poll()
            if code is not None and not selector.get_map() and group_absent(process.pid) is True:
                break
            now = time.monotonic()
            if now < deadline:
                continue
            timed_out = True
            if stage == 3:
                break
            sig = [signal.SIGINT, signal.SIGTERM, signal.SIGKILL][stage]
            sent = False
            # Only signal while the original owned group leader is still this child.
            # Child sessions (including XCTest) stay with its reviewed observer/root.
            if process.poll() is None:
                try:
                    os.killpg(process.pid, sig)
                    sent = True
                except ProcessLookupError:
                    pass
            receipt['signals'].append(dict(signal=sig.name, sent=sent, elapsedSeconds=now-started))
            deadline = now + (INTERRUPT_GRACE if stage == 0 else SIGNAL_GRACE)
            stage += 1
    except BaseException as error:
        observation_error = dict(failureType=type(error).__name__, failure=str(error))
    selector.close()
    for row in streams.values():
        row['file'].close()
        del row['file']
        row['retainedSHA256'] = row.pop('digest').hexdigest()
    for pipe in [process.stdout, process.stderr]:
        if not pipe.closed:
            pipe.close()
    receipt.update(finishedUTC=utc(), elapsedSeconds=time.monotonic()-started,
                   exitCode=process.poll(), outerTimeout=timed_out, streams=streams,
                   ownedProcessGroupAbsent=group_absent(process.pid), retryAttempted=False)
    receipt.update(groupObservations=GROUP_OBSERVATIONS, observationError=observation_error)
    receipt['observationComplete'] = (receipt['exitCode'] is not None
        and receipt['ownedProcessGroupAbsent'] is True and observation_error is None
        and all(row['eof'] and row['observedBytes'] == row['retainedBytes'] for row in streams.values()))
    receipt['rootEmergencyReconciliationRequired'] = timed_out or not receipt['observationComplete']
    write(output / 'receipt.json', receipt)
    print(json.dumps({key: receipt[key] for key in ['runID','exitCode','outerTimeout','observationComplete','rootEmergencyReconciliationRequired']}, sort_keys=True))
    return 0 if receipt['observationComplete'] and not timed_out and receipt['exitCode'] == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
