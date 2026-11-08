"""Request the standard OS Accessibility notice once; never change TCC state."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('request_commands', ROOT / 'scripts/ci/check-android-generated-java.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
out = HERE / 'commands'
out.mkdir()
commands = runner.Commands(out, dict(os.environ), seconds=30, command_seconds=15,
                           output_bytes=1024*1024, total_output_bytes=2*1024*1024)
receipt = {'schema': 1, 'requestedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'scope': 'One standard OS permission notice; no simulator, frontend or test attempt',
           'requestSHA256': hashlib.sha256((HERE / 'request.js').read_bytes()).hexdigest()}
try:
    receipt['response'] = json.loads(commands.run('request-accessibility-notice',
        ['/usr/bin/osascript', '-l', 'JavaScript', str(HERE / 'request.js')], ROOT))
    receipt['status'] = 'trusted' if receipt['response']['trusted'] else 'OS_PERMISSION_REQUIRED'
except BaseException as error:
    receipt.update(status='request-failed', error=repr(error))
    raise
finally:
    receipt['terminalCustody'] = commands.custody_terminal()
    (HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
