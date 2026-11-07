#!/opt/homebrew/Cellar/python@3.14/3.14.8/Frameworks/Python.framework/Versions/3.14/bin/python3.14 -B
"""Record only this fixture's pinned OpenSSL argv and capped output."""
from pathlib import Path
import json
import os
import selectors
import subprocess
import sys
import time

started = time.monotonic()
deadline = started + 5
directory = Path(os.environ['MIXER_KEY_OWNER_FIXTURE_EVIDENCE'])
command = ['/opt/homebrew/Cellar/openssl@3/3.6.5/bin/openssl', *sys.argv[1:]]
child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
output = bytearray()
error = None
selector = selectors.DefaultSelector()
try:
    selector.register(child.stdout, selectors.EVENT_READ)
    eof = False
    while not eof:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('OpenSSL five-second deadline exceeded')
        for key, _ in selector.select(min(0.05, remaining)):
            block = os.read(key.fileobj.fileno(), 4096)
            if not block:
                eof = True
                break
            output.extend(block)
            if len(output) > 8192:
                raise ValueError('OpenSSL output exceeded 8192 bytes')
    child.wait(timeout=max(0.001, deadline - time.monotonic()))
except BaseException as exc:
    error = type(exc).__name__ + ': ' + str(exc)
finally:
    selector.close()
    if child.poll() is None:
        child.kill()
    child.wait(timeout=1)
    child.stdout.close()

count = len(list(directory.glob('openssl-*.json'))) + 1
record = {'argv': command, 'exit_code': child.returncode, 'output': bytes(output).decode('utf-8'),
          'output_bytes': len(output), 'pid': child.pid, 'child_reaped': True,
          'elapsed_seconds': round(time.monotonic() - started, 6), 'error': error}
with (directory / ('openssl-%02d.json' % count)).open('x') as stream:
    json.dump(record, stream, allow_nan=False)
    stream.write('\n')
sys.stdout.buffer.write(output)
sys.exit(1 if error else child.returncode)
