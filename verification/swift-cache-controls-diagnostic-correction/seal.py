#!/usr/bin/env python3
"""Bind reviewed sources, scoped read-only Git checks, and mocked-only evidence."""
import hashlib
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PATHS = ['verification/swift-cache-state-ci/check_cache_state.py',
         'verification/swift-cache-state-ci/test_runner.py']

def run(args):
    result = subprocess.run(['git', '-c', 'gc.auto=0', *args], cwd=ROOT,
                            capture_output=True, timeout=10, check=True)
    return result.stdout

receipt = json.loads((BASE / 'mocked-controls.json').read_bytes())
if not (receipt['status'] == 'passed-three-mocked-diagnostic-controls'
        and receipt['tests_run'] == 3 and not receipt['denied_process_or_socket_events']
        and receipt['source_before'] == receipt['source_after']):
    raise RuntimeError('Mocked-only evidence does not qualify')
snapshot = BASE / 'source-after'
snapshot.mkdir()
for row in receipt['source_after']:
    path = pathlib.Path(row['path'])
    data = path.read_bytes()
    if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
        raise RuntimeError('Source changed after mocked controls')
    (snapshot / path.name).write_bytes(data)
check = run(['diff', '--check', '--', *PATHS])
(BASE / 'diff-check.stdout').write_bytes(check)
(BASE / 'correction.patch').write_bytes(run(['diff', '--', *PATHS]))
context = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
           'python': sys.version, 'git_version': run(['--version']).decode().strip(),
           'observed_head': run(['rev-parse', 'HEAD']).decode().strip(),
           'observed_head_tree': run(['rev-parse', 'HEAD^{tree}']).decode().strip(),
           'failed_attempt_commit': '0b99469dfbeb06ac53ad0223bd070a35f2a6a700',
           'source_after': receipt['source_after'],
           'git_diff_check': {'command': ['git', '-c', 'gc.auto=0', 'diff', '--check', '--', *PATHS],
                              'exit': 0, 'stdout_bytes': len(check)},
           'no_full_suite_compiler_real_process_control_or_custody_probe': True,
           'original_CI_primary_cause_fixed': False,
           'root_review_and_remote_CI_pending': True}
with (BASE / 'receipt.json').open('x') as stream:
    stream.write(json.dumps(context, sort_keys=True, indent=2) + '\n')
rows = []
for path in sorted(BASE.rglob('*')):
    if path.is_file() and path.name != 'packet-manifest.json':
        if path.is_symlink():
            raise RuntimeError('Symlink in correction packet')
        data = path.read_bytes()
        rows.append({'path': path.relative_to(BASE).as_posix(), 'bytes': len(data),
                     'sha256': hashlib.sha256(data).hexdigest()})
tree = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
with (BASE / 'packet-manifest.json').open('x') as stream:
    stream.write(json.dumps({'schema': 1, 'sealed_at': datetime.now(timezone.utc).isoformat(),
                             'files': rows, 'tree_sha256': tree,
                             'scope': 'Diagnostic source correction with three mocked-only controls'},
                            sort_keys=True, indent=2) + '\n')
print(json.dumps({'sealed': True, 'files': len(rows), 'tree_sha256': tree,
                  'source_after': receipt['source_after'], 'diff_check_exit': 0}))
