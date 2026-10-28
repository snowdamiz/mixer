#!/usr/bin/env python3
"""Final in-process source/offline checks and packet freeze. No child processes."""
from pathlib import Path
import contextlib
import datetime
import hashlib
import io
import json
import sys
import time

import check
import controls

D = Path(__file__).resolve().parent
def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(obj): return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()
def row(path, base=D):
    raw = path.read_bytes(); return {'path': str(path.relative_to(base)), 'bytes': len(raw), 'sha256': sha(raw)}
def put(path, obj):
    with path.open('x') as handle: json.dump(obj, handle, indent=2, sort_keys=True); handle.write('\n')
def main():
    started = time.monotonic(); now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    assert not (D / 'seal.json').exists() and not (D / 'command').exists() and not (D / 'build').exists()
    output = D / 'commands/final-offline'; output.mkdir(parents=True)
    transcript = io.StringIO(); error = None; plan = None
    try:
        with contextlib.redirect_stdout(transcript):
            plan = check.check(deadline=started + 15)
            print(json.dumps({'status': 'frozen-preparation-custody-passed', 'original146': True, 'diagnostic146': True,
                              'exact_edit_replay': 3, 'plan_sha256': sha((D/'plan.json').read_bytes()), 'compiler_or_children_started': 0}))
            controls.main()
    except BaseException as failure: error = {'type': type(failure).__name__, 'message': str(failure)}
    stdout = transcript.getvalue().encode(); assert len(stdout) <= 65536
    (output/'stdout').write_bytes(stdout); (output/'stderr').write_bytes(b'')
    command = [str(Path(sys.executable).resolve()), '-B', str(D/'verify_and_seal.py')]
    receipt = {'schema': 1, 'at': now, 'command': command, 'cwd': str(D.parents[1]), 'python': sys.version,
        'python_tool': {'path': str(Path(sys.executable).resolve()), **check.hash_file(Path(sys.executable).resolve())},
        'script': row(Path(__file__).resolve()), 'plan_sha256': sha((D/'plan.json').read_bytes()),
        'original_source146_tree': None if plan is None else plan['original_source']['tree_sha256'],
        'diagnostic_source146_tree': None if plan is None else plan['diagnostic_source']['tree_sha256'],
        'elapsed_seconds': time.monotonic()-started, 'exit': 0 if error is None else 1, 'error': error,
        'in_process_calls': ['check.check(deadline=start+15)', 'controls.main()'],
        'outputs': [row(output/'stdout'), row(output/'stderr')], 'compiler_runtime_or_child_processes_started': 0,
        'cleanup': 'No compiler/native/build process or generated build artifacts started. Frozen source scratch retained.'}
    put(output/'receipt.json', receipt)
    if error is not None: raise SystemExit(json.dumps(error))
    result = json.loads((D/'controls-result.json').read_text())
    assert len(result['controls']) == 28 and result['actual_layout_strategy_qualified'] is False
    members = [row(path) for path in sorted(D.rglob('*')) if path.is_file() and path.name != 'seal.json']
    assert all(not (D/member['path']).is_symlink() for member in members)
    seal = {'schema': 1, 'status': 'FROZEN_SOURCE_OFFLINE_PREPARATION_AWAITING_ROOT_COMPILER_RELEASE',
        'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'members': members,
        'tree_sha256': sha(canonical(members)), 'member_count': len(members), 'member_bytes': sum(row['bytes'] for row in members),
        'plan_sha256': sha((D/'plan.json').read_bytes()), 'source146_original_tree': plan['original_source']['tree_sha256'],
        'source146_diagnostic_tree': plan['diagnostic_source']['tree_sha256'], 'exact_edits': 3,
        'offline_controls': 28, 'compiler_released': False, 'compiler_executed': False, 'layout_strategy_qualified': False,
        'all_actual_layouts_prices_backing_peak_funding_full_ownership_GA_pending': True}
    put(D/'seal.json', seal)
    print(json.dumps({'status': seal['status'], 'plan_sha256': seal['plan_sha256'], 'seal_sha256': sha((D/'seal.json').read_bytes()),
                      'members': len(members), 'compiler_started': False}))
if __name__ == '__main__': main()
