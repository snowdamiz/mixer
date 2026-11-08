"""One authorized <=20s client-only refusal; never starts a server or releases the port."""
import os
from pathlib import Path
import signal
import socket
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_api28 as r

started = time.monotonic()
signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(RuntimeError('20s refusal probe bound')))
signal.alarm(20)
out = Path(__file__).resolve().parent / 'inherited-client-refusal'
out.mkdir(exist_ok=False)
work = out / 'scratch'
work.mkdir(mode=0o700)
r.require(r.identity(r.ADB)['sha256'] == r.ADB_SHA, 'selected installed binary drift')
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
for name in ('ADB_SERVER_SOCKET', 'ANDROID_ADB_SERVER_ADDRESS', 'ANDROID_ADB_SERVER_PORT',
             'ADB_SERVER_PORT', 'ANDROID_SERIAL', 'ADB_VENDOR_KEYS'):
    env.pop(name, None)
env['ANDROID_USER_HOME'] = str(work)
c = r.lifecycle().Commands(out, env, deadline=started + 19, output_bytes=4*1024*1024, total_output_bytes=32*1024*1024)
receipt = {'status': 'failed', 'maximumSeconds': 20, 'python': sys.version,
           'adbIdentity': r.identity(r.ADB), 'metadataVersion': '37.0.1',
           'sourceProof': 'official-sources.json; numeric remote host returns before launch_server on fd=-2',
           'realServerStarts': 0, 'emulators': 0, 'deviceCommandsDelivered': 0,
           'keysRequested': 0, 'portReleasedBeforeClientExit': False}
with socket.socket() as reservation:
    reservation.bind(('127.0.0.1', 0))
    port = reservation.getsockname()[1]
    c.env.update(ADB_SERVER_SOCKET='tcp:127.0.0.1:' + str(port),
                 ANDROID_ADB_SERVER_ADDRESS='127.0.0.1',
                 ANDROID_ADB_SERVER_PORT=str(port), ADB_SERVER_PORT=str(port))
    receipt['inheritedClientEnvironment'] = {key:c.env[key] for key in ('ADB_SERVER_SOCKET','ANDROID_ADB_SERVER_ADDRESS','ANDROID_ADB_SERVER_PORT','ADB_SERVER_PORT')}
    receipt['reservedAddress'] = ['127.0.0.1', port]
    receipt['reservationListening'] = False  # construction: bind only; no listen call
    receipt['unsupportedSocketQueryRemoved'] = 'macOS SO_ACCEPTCONN Errno42; no production edit'
    try:
        output = c.run('no-autostart-refusal', [r.ADB, '-s', 'emulator-5678', 'get-state'], work, 10, (1,))
        r.require('cannot start server on remote host' in output, 'remote refusal absent')
        r.require('daemon started' not in output and 'starting now' not in output, 'unexpected daemon path')
        receipt.update(status='passed', output=output)
    except BaseException as error:
        receipt['error'] = repr(error)
    finally:
        receipt['cleanup'] = r.cleanup(c, work)
        receipt['commands'] = c.records
        if not receipt['cleanup'].get('allTerminalCustody') or not receipt['cleanup'].get('scratchRemoved'):
            receipt['status'] = 'failed'
        receipt['elapsedSeconds'] = time.monotonic() - started
        receipt['command'] = [sys.executable, '-B', str(Path(__file__).resolve())]
        r.save(out / 'receipt.json', receipt)
signal.alarm(0)
print(receipt['status'], receipt['elapsedSeconds'], receipt.get('output', receipt.get('error')))
sys.exit(0 if receipt['status'] == 'passed' else 1)
