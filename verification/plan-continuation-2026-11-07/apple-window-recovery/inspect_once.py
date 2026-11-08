"""Root-selected read-only reconciliation after the new AXWindows failure.

No old held process is inspected. This does not reset the failed controller or
authorize a device/window mutation, another frontend, or native dispatch.
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
ATTEMPT = BASE / 'apple-safe-keyboard-fix-r3/native-attempt-1'
sys.path.insert(0, str(BASE / 'native-custody-premise'))
from cleanup_control import Commands

def require(value, message):
    if not value:
        raise RuntimeError(message)

def devices(raw):
    fields = ['name', 'state', 'deviceTypeIdentifier', 'dataPath', 'logPath']
    return {row['udid']: {**{key: row.get(key) for key in fields}, 'runtime': rt}
            for rt, rows in raw['devices'].items() for row in rows}

def main():
    out = HERE / 'inspection-1'
    out.mkdir(exist_ok=False)
    logs = out / 'commands'
    logs.mkdir()
    scratch = out / 'scratch'
    scratch.mkdir()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
               DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer')
    commands = Commands(logs, env, deadline=time.monotonic()+90,
                        output_bytes=1024*1024, total_output_bytes=4*1024*1024)
    result = {'startedAt': datetime.now(timezone.utc).isoformat(),
              'scope': 'One root-owned read-only reconciliation of newly created resources',
              'historicalHoldsReleased': False, 'mutationsAuthorized': False,
              'failedControllerResumed': False, 'nativeAttempts': 0}
    try:
        owned = json.loads((ATTEMPT / 'owned-device.json').read_text())
        require(owned['uuid']=='4CE0ECC9-1EDA-4543-80FF-9B011DF9044F', 'owned identity changed')
        expected = (ATTEMPT / 'commands/013-frontend-identity.stdout').read_text().strip()
        actual = commands.run('exact-frontend-identity',
            ['/bin/ps', '-p', '75452', '-o', 'pid=,lstart=,comm='], ROOT, 15)
        require(actual.strip()==expected, 'exact frontend identity changed; stop')
        result['frontendIdentity'] = actual
        baseline = devices(json.loads((ATTEMPT / 'commands/004-devices.stdout').read_text()))
        raw = commands.run('device-reconciliation',
            ['/usr/bin/xcrun', 'simctl', 'list', 'devices', '--json'], ROOT, 20)
        current = devices(json.loads(raw))
        require({k:v for k,v in current.items() if k!=owned['uuid']}==baseline,
                'external device baseline changed; stop without further observation')
        result['externalBaselineUnchanged'] = True
        row = current.get(owned['uuid'])
        require(row and row['name']==owned['name'] and row['runtime']==owned['runtime'] and
                row['deviceTypeIdentifier']==owned['device_type'], 'owned device mismatch')
        result['ownedDevice'] = row
        result['ax'] = json.loads(commands.run('exact-frontend-public-ax',
            ['/opt/homebrew/opt/python@3.14/bin/python3.14', '-B', str(HERE/'inspect_ax.py')], ROOT, 20))
        result['status'] = 'OBSERVED; NO MUTATION OR NATIVE DISPATCH AUTHORIZED'
    except BaseException as error:
        result['status'] = 'STOPPED'
        result['error'] = repr(error)
    finally:
        result['cleanup'] = commands.cleanup(scratch)
        result['finishedAt'] = datetime.now(timezone.utc).isoformat()
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))

if __name__ == '__main__':
    main()
