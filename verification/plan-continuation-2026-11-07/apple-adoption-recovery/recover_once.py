"""Root-selected exact-device cleanup after asynchronous window-close shutdown.

This does not resume the failed adoption reservation or perform UI/native work.
Delete only the previously owned disposable device after positive Shutdown and
unchanged external baseline. Any other state stops without a further command.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parent.parent
ATTEMPT = BASE / 'apple-window-identity-campaign/adoption-attempt-1'
UID = '4CE0ECC9-1EDA-4543-80FF-9B011DF9044F'
LIFECYCLE = BASE / 'native-custody-premise/cleanup_control.py'
if hashlib.sha256(LIFECYCLE.read_bytes()).hexdigest() != '8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df':
    raise RuntimeError('Lifecycle drift')
sys.path.insert(0, str(LIFECYCLE.parent))
from cleanup_control import Commands


def require(value, message):
    if not value:
        raise RuntimeError(message)


def devices(raw):
    return {row['udid']: dict(name=row['name'], state=row['state'], runtime=runtime,
            deviceType=row.get('deviceTypeIdentifier'),
            deviceTypeIdentifier=row.get('deviceTypeIdentifier'),
            dataPath=row.get('dataPath'), logPath=row.get('logPath'))
            for runtime, rows in raw['devices'].items() for row in rows}


def main():
    out = HERE / 'attempt-1'
    out.mkdir(exist_ok=False)
    scratch = out / 'scratch'
    scratch.mkdir()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
               DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer')
    c = Commands(out, env, deadline=time.monotonic()+75,
                 output_bytes=1024*1024, total_output_bytes=4*1024*1024)
    result = dict(startedAt=datetime.now(timezone.utc).isoformat(),
                  status='failed', scope='exact owned Shutdown-device deletion only',
                  failedControllerResumed=False, frontendQuit=False, nativeAttempts=0,
                  sourceSHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    try:
        adoption = json.loads((ATTEMPT/'adoption.json').read_text())
        baseline, owned = adoption['externalBaseline'], adoption['owned']
        require(owned['uuid'] == UID and UID not in baseline, 'Owned selection mismatch')
        def observe(label):
            current = devices(json.loads(c.run(label,
                ['/usr/bin/xcrun', 'simctl', 'list', 'devices', '--json'], ROOT, 20)))
            require({key:value for key,value in current.items() if key != UID} == baseline,
                    'External baseline changed; stop')
            return current
        current = observe('preflight')
        row = current.get(UID)
        result['ownedPreflight'] = row
        if row is not None:
            require(row['name'] == owned['name'] and row['runtime'] == owned['runtime'] and
                    row['deviceType'] == owned['device_type'] and
                    row['dataPath'] == '/Users/andreyyurlov/Library/Developer/CoreSimulator/Devices/'+UID+'/data',
                    'Owned identity changed; stop')
            require(row['state'] == 'Shutdown', 'Owned device not positively Shutdown; no mutation')
            c.run('delete-exact-owned', ['/usr/bin/xcrun','simctl','delete',UID], ROOT, 20)
            current = observe('postflight')
        require(UID not in current, 'Owned device remains')
        result.update(status='passed', ownedDeviceAbsent=True, externalBaselineUnchanged=True,
                      protectedDevices={key:current[key]['state'] for key in
                        ('CE7E80FC-64BF-41A0-B07B-60F4D8711808','D55C87E9-F349-49AC-BCD3-3B4B5BE9E010')})
    except BaseException as error:
        result['error'] = repr(error)
    finally:
        result['cleanup'] = c.cleanup(scratch)
        result['commands'] = c.records
        if not result['cleanup']['allTerminalCustody']:
            result['status'] = 'failed'
        result['finishedAt'] = datetime.now(timezone.utc).isoformat()
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key != 'commands'}))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
