"""Read trust for the same helpers after the user showed Acid enabled."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('trust_commands', ROOT / 'scripts/ci/check-android-generated-java.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
out = HERE / 'commands'
out.mkdir()
commands = runner.Commands(out, dict(os.environ), seconds=90, command_seconds=20,
                           output_bytes=1024*1024, total_output_bytes=4*1024*1024)
receipt = {'schema': 1, 'observedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'userScreenshot': 'Acid enabled in Device Control and Data Access',
           'permissionMutation': False, 'simulatorOrNativeAttempt': False}
try:
    probe = HERE.parent / 'apple-safe-keyboard-controller/ax_probe.js'
    receipt['osascript'] = json.loads(commands.run('osascript-trust', ['/usr/bin/osascript', '-l', 'JavaScript', str(probe)]))
    receipt['python'] = json.loads(commands.run('python-trust', [sys.executable, '-B', str(HERE / 'python_probe.py')]))
    ids = [receipt['osascript']['pid'], receipt['python']['pid']]
    predicate = 'subsystem == "com.apple.TCC" AND (' + ' OR '.join('eventMessage CONTAINS "' + str(pid) + '"' for pid in ids) + ')'
    try:
        log = commands.run('own-request-attribution-log', ['/usr/bin/log', 'show', '--last', '2m', '--style', 'json', '--info', '--debug', '--predicate', predicate])
        (HERE / 'attribution.json').write_text(log)
        receipt['attributionLogBytes'] = len(log.encode())
        receipt['attributionLogSHA256'] = hashlib.sha256(log.encode()).hexdigest()
    except RuntimeError as error:
        receipt['attributionUnavailable'] = str(error)
finally:
    receipt['terminalCustody'] = commands.custody_terminal()
    (HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
