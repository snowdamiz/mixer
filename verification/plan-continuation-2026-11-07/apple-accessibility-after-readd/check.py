import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import time

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
ROOT = BASE.parent.parent
sys.path.insert(0, str(BASE / 'native-custody-premise'))
from cleanup_control import Commands

logs = OUT / 'commands'
logs.mkdir(exist_ok=False)
scratch = OUT / 'scratch'
scratch.mkdir(exist_ok=False)
commands = Commands(logs, dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                    deadline=time.monotonic() + 90, output_bytes=1024*1024,
                    total_output_bytes=4*1024*1024)
receipt = {'schema': 1, 'startedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'scope': 'Nonprompting public trust checks after observed current Acid launch',
           'noUIOrPermissionMutation': True, 'nativeAttempts': 0}
try:
    probes = {
        'osascript': ['/usr/bin/osascript', '-l', 'JavaScript', str(BASE / 'apple-safe-keyboard-controller/ax_probe.js')],
        'python': ['/opt/homebrew/opt/python@3.14/bin/python3.14', '-B', str(BASE / 'apple-accessibility-after-screenshot/python_probe.py')],
    }
    for name, argv in probes.items():
        receipt[name] = json.loads(commands.run(name + '-trust', argv, ROOT, 20))
    receipt['bothTrusted'] = all(receipt[name]['trusted'] for name in probes)
    pids = [str(receipt[name]['pid']) for name in probes]
    predicate = 'subsystem=="com.apple.TCC" AND (' + ' OR '.join('eventMessage CONTAINS "' + pid + '"' for pid in pids) + ')'
    attribution = commands.run('request-attribution', ['/usr/bin/log', 'show', '--last', '2m', '--style', 'json', '--info', '--debug', '--predicate', predicate], ROOT, 20)
    (OUT / 'attribution.json').write_text(attribution + '\n')
    receipt['attributionSHA256'] = hashlib.sha256((attribution + '\n').encode()).hexdigest()
except BaseException as error:
    receipt['error'] = repr(error)
finally:
    receipt['cleanup'] = commands.cleanup(scratch)
    receipt['finishedAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k: v for k, v in receipt.items() if k != 'attributionSHA256'}))
