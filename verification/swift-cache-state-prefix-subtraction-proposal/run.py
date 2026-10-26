#!/usr/bin/env python3
"""Retain two bounded sequential Python-only checker commands and outputs."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
logs = HERE / 'commands' / stamp
logs.mkdir(parents=True)
checker = (HERE / 'check.py').read_bytes()
(logs / 'checker-source.py').write_bytes(checker)
receipt = {
    'schema': 1, 'at': stamp, 'cwd': str(ROOT), 'python': sys.version, 'executable': sys.executable,
    'scope': 'source-only structural, finite mathematical and necessary G3 obstruction checks',
    'checker_sha256': hashlib.sha256(checker).hexdigest(),
    'input_tree_digest': json.loads((HERE / 'input-bindings.json').read_text())['input_tree_digest'],
    'proposed_source_sha256': json.loads((HERE / 'source-assembly.json').read_text())['proposed_sha256'],
    'host_child_limit': 1, 'per_child_timeout_seconds': 60, 'commands': [],
    'compiler_product_native_UI_capture_process_inventory': False,
    'cleanup': 'No native instances, capture helpers, compiler products or external scratch created. Sequential owned checker children reaped. Retained only this packet.',
}
for label, flags in [('normal', []), ('optimized', ['-O'])]:
    argv = [sys.executable, '-B', *flags, str(HERE / 'check.py')]
    began = datetime.datetime.now(datetime.timezone.utc)
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
    elapsed = (datetime.datetime.now(datetime.timezone.utc)-began).total_seconds()
    (logs / f'{label}.stdout').write_bytes(result.stdout)
    (logs / f'{label}.stderr').write_bytes(result.stderr)
    receipt['commands'].append({'label': label, 'argv': argv, 'returncode': result.returncode,
                                'elapsed_seconds': elapsed,
                                'stdout_sha256': hashlib.sha256(result.stdout).hexdigest(),
                                'stderr_sha256': hashlib.sha256(result.stderr).hexdigest()})
(logs / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
passed = all(c['returncode'] == 0 for c in receipt['commands'])
(HERE / 'latest-run.json').write_text(json.dumps({'receipt': str((logs/'receipt.json').relative_to(ROOT)),
                                                 'checker_sha256': receipt['checker_sha256'],
                                                 'all_passed': passed}, indent=2, sort_keys=True)+'\n')
print(json.dumps(receipt, sort_keys=True))
sys.exit(0 if passed else 1)
