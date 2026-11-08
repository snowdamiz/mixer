"""Bounded single command; imports only the reviewed inert Commands runner."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUNNER = ROOT / 'scripts/ci/check-android-generated-java.py'
spec = importlib.util.spec_from_file_location('identity_commands', RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
out = HERE / 'commands'
out.mkdir()
commands = runner.Commands(out, dict(os.environ), seconds=35, command_seconds=20,
                           output_bytes=65536, total_output_bytes=131072, cleanup_seconds=5)
receipt = {'schema': 1, 'observedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'sourceRevision': '96f03ab65966a6374e958e780fa09a3eed814c0b',
           'committedTree': '6dacea5d2f5cd55d6934142cce556a4bd0fcd1c0',
           'scope': 'One read-only AppKit/Security identity probe; no product/native build or AX/UI test',
           'preferredRunner': 'native-custody-premise/bounded_lifecycle.py not present in this checkout',
           'runner': str(RUNNER),
           'sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (RUNNER, HERE / 'probe.py', HERE / 'run.py')}}
try:
    receipt['probe'] = json.loads(commands.run('public-acid-identity', [sys.executable, '-B', str(HERE / 'probe.py')]))
except Exception as error:
    receipt['error'] = {'type': type(error).__name__, 'message': str(error)}
finally:
    receipt['terminalCustody'] = commands.custody_terminal()
    (HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))
