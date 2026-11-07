"""One bounded read of an existing immutable CI artifact; no compiler execution."""
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
OUTPUT = Path('/tmp/mixer-20261107-ci-df7-envelope-bounded.zip')
EXPECTED = '9a837ebd67d865b2bc4f5cc7e53f6e245ecdd1b49731f2be49e68279384890af'
ARGV = ['gh', 'api', 'repos/snowdamiz/mixer/actions/artifacts/13592908052/zip']
if OUTPUT.exists() or (HERE / 'bounded-acquisition.json').exists():
    raise RuntimeError('one selected acquisition already has output')
record = {'argv': ARGV, 'artifact': 13592908052, 'expectedSHA256': EXPECTED,
          'limits': {'seconds': 15, 'stdoutBytes': 2000000, 'stderrBytes': 65536,
                     'cleanupSeconds': 5}, 'signals': [], 'cleanupErrors': [],
          'status': 'failed', 'scope': 'new bounded acquisition of existing ordinary CI artifact'}
buffers = {'stdout': bytearray(), 'stderr': bytearray()}
eof = {'stdout': False, 'stderr': False}
child = None
selector = selectors.DefaultSelector()
started = time.monotonic()
try:
    child = subprocess.Popen(ARGV, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, start_new_session=True)
    record.update(pid=child.pid, ownedPGID=child.pid)
    for stream in buffers:
        pipe = getattr(child, stream)
        os.set_blocking(pipe.fileno(), False)
        selector.register(pipe, selectors.EVENT_READ, stream)
    while selector.get_map():
        if time.monotonic() - started > 15:
            raise RuntimeError('acquisition deadline')
        for key, _ in selector.select(0.05):
            block = os.read(key.fileobj.fileno(), 65536)
            if not block:
                eof[key.data] = True
                selector.unregister(key.fileobj)
            else:
                cap = 2000000 if key.data == 'stdout' else 65536
                if len(buffers[key.data]) + len(block) > cap:
                    raise RuntimeError('acquisition output cap: ' + key.data)
                buffers[key.data].extend(block)
    record['exit'] = child.wait(timeout=max(0.01, 15 - (time.monotonic() - started)))
    record['directChildReaped'] = True
    if record['exit'] != 0:
        raise RuntimeError('gh acquisition failed')
    body = bytes(buffers['stdout'])
    if len(body) != 770713 or hashlib.sha256(body).hexdigest() != EXPECTED:
        raise RuntimeError('provider archive identity mismatch')
    record['bodyCompleted'] = True
except BaseException as failure:
    record['failure'] = {'type': type(failure).__name__, 'message': str(failure)}
finally:
    if child is not None:
        try:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                record['signals'].append('SIGKILL')
            record['exit'] = child.wait(timeout=5)
            record['directChildReaped'] = True
        except BaseException as failure:
            record['cleanupErrors'].append(type(failure).__name__ + ': ' + str(failure))
        try:
            os.killpg(child.pid, 0)
            record['ownedGroupAbsent'] = False
        except ProcessLookupError:
            record['ownedGroupAbsent'] = True
        except BaseException as failure:
            record['cleanupErrors'].append(type(failure).__name__ + ': ' + str(failure))
        for stream in buffers:
            getattr(child, stream).close()
        record['pipeReadersClosed'] = all(getattr(child, stream).closed for stream in buffers)
    selector.close()
    record['streamEOF'] = eof
    record['elapsedSeconds'] = time.monotonic() - started
    record['streams'] = {k: {'bytes': len(v), 'sha256': hashlib.sha256(v).hexdigest()}
                         for k, v in buffers.items()}
    record['scriptSHA256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    record['limitations'] = ['gh internal HTTP events and provider disposal are not separately instrumented']
    if (record.get('bodyCompleted') and record.get('directChildReaped')
            and record.get('ownedGroupAbsent') and record.get('pipeReadersClosed')
            and all(eof.values()) and not record['cleanupErrors'] and not record['signals']):
        OUTPUT.write_bytes(buffers['stdout'])
        record['archive'] = str(OUTPUT)
        record['status'] = 'passed-complete-bounded-acquisition'
    (HERE / 'bounded-acquisition.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))
if record['status'] != 'passed-complete-bounded-acquisition':
    raise SystemExit(1)
