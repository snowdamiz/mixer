"""Exact owned ordinary-Python child commands, each bounded to60seconds."""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def ident(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def main():
    destination = HERE / 'run1'
    destination.mkdir(exist_ok=False)
    commands = [
        ('tests', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(HERE), '-p', 'test_descriptor_joins.py', '-v']),
        ('descriptor-pass', [sys.executable, '-B', str(HERE / 'check_descriptor_joins.py'), '--output', str(HERE / 'facets-run1')]),
    ]
    results = []
    for label, argv in commands:
        started = time.monotonic()
        timeout = False
        try:
            child = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=False)
            code, stdout, stderr = child.returncode, child.stdout, child.stderr
        except subprocess.TimeoutExpired as failure:
            # subprocess.run kills and waits for its direct child on timeout.
            timeout = True
            code, stdout, stderr = None, failure.stdout or b'', failure.stderr or b''
        (destination / (label + '.stdout')).write_bytes(stdout)
        (destination / (label + '.stderr')).write_bytes(stderr)
        results.append({'label': label, 'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': 60, 'timeout': timeout, 'exit': code, 'elapsed_seconds': time.monotonic() - started, 'direct_child_reaped': True, 'stdout': ident(destination / (label + '.stdout')), 'stderr': ident(destination / (label + '.stderr'))})
        if timeout or code != 0:
            break
    acceptance = json.loads((ROOT / 'verification/android-editor-boundary-root-review/finite-observation-consistency-acceptance.json').read_text())
    receipt = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'passed-bounded-host-descriptor-consistency-only' if len(results) == 2 and all(x['exit'] == 0 and not x['timeout'] for x in results) else 'findings-or-failed-bounded-host-command', 'commands': results, 'tool': {'python': sys.version, 'python_executable': sys.executable, 'platform': sys.platform}, 'source_revision_context_from_pinned_acceptance': acceptance['source_revision_context'], 'source_seal': ident(HERE / 'source-seal.json'), 'prepared_input_manifest': ident(HERE / 'prepared-input-manifest.json'), 'process_boundary': 'Only these ordinary Python direct children were launched; no product/native execution, process inventories or environment-wide process scans.', 'cleanup': {'all_direct_children_reaped': True, 'scratch_created': False, 'native_or_capture_processes_started': False, 'owned_simulator_emulator_instances_started': False}, 'qualification': False, 'independent_review': 'pending'}
    (destination / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'status': receipt['status'], 'commands': [{'label': x['label'], 'exit': x['exit'], 'timeout': x['timeout'], 'seconds': x['elapsed_seconds']} for x in results]}))
    return 0 if receipt['status'].startswith('passed-') else 1


if __name__ == '__main__':
    sys.exit(main())
