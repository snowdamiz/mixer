#!/usr/bin/env python3
"""Record only the bounded Python ledger/source check and owned-path whitespace check."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import platform
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

def sha(data):
    return hashlib.sha256(data).hexdigest()

def command(args, name):
    started = datetime.now(timezone.utc).isoformat()
    start = time.monotonic()
    result = subprocess.run(args, cwd=ROOT, capture_output=True, timeout=30)
    (HERE/(name+'.stdout')).write_bytes(result.stdout)
    (HERE/(name+'.stderr')).write_bytes(result.stderr)
    return {'argv': args, 'cwd': str(ROOT), 'started_utc': started,
            'elapsed_seconds': time.monotonic()-start, 'exit_code': result.returncode,
            'stdout': name+'.stdout', 'stdout_sha256': sha(result.stdout),
            'stderr': name+'.stderr', 'stderr_sha256': sha(result.stderr)}

def main():
    ledger = json.loads((HERE/'ledger.json').read_text())
    steps = [command([sys.executable, str(HERE/'check.py')], 'check'),
             command(['git','diff','--check','--', str(HERE)], 'diff-check'),
             command(['git','rev-parse','HEAD'], 'source-revision'),
             command(['git','--version'], 'git-version')]
    receipt = {'schema': 1, 'status': 'passed' if all(s['exit_code']==0 for s in steps) else 'failed',
               'python_version': sys.version, 'python_executable': sys.executable,
               'platform': platform.platform(), 'source_members': 144,
               'source_tree_sha256': ledger['source_tree_sha256'],
               'source_seal_sha256': ledger['source_seal_sha256'],
               'script_sha256': sha((HERE/'check.py').read_bytes()),
               'ledger_sha256': sha((HERE/'ledger.json').read_bytes()),
               'steps': steps, 'scope': 'Finite source custody and source-action arithmetic only; owned-path whitespace; read-only git revision attribution.',
               'runtime_or_native_executed': False, 'capture_or_UI_used': False,
               'new_native_checks': 'pending under explicit pause',
               'cleanup': 'Only bounded Python/git child commands; each returned. No simulator/emulator or capture process started. No other-project processes inspected or altered.',
               'operational_work_selected': False}
    (HERE/'command-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    assert receipt['status'] == 'passed'
    print(json.dumps({'status': receipt['status'], 'commands': len(steps),
                      'source_tree_sha256': ledger['source_tree_sha256'], **ledger['exports']}))

if __name__ == '__main__':
    main()
