#!/usr/bin/env python3
"""Check this checkout-only edit against its canonical workflow base."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REVISION = '114a2632fd58076574bd5b2444c511861c3b30d4'
env = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')
base = subprocess.check_output(['git', 'show', REVISION + ':.github/workflows/verify.yml'],
                               cwd=ROOT, text=True, env=env, timeout=15)
current = (ROOT / '.github/workflows/verify.yml').read_text()
start = current.index('  swift:\n')
end = current.index('  swift-capability-native:\n', start)
job = current[start:end]
begin = job.index('          # Retain source and every policy manifest; omit unrelated old receipts.\n')
finish = job.index('      - name: Verify and record pinned Apple toolchain', begin)
inserted = job[begin:finish]
expected = (HERE / 'patterns.txt').read_text().splitlines()
actual = inserted.split('          sparse-checkout: |\n')[1].splitlines()
if actual != ['            ' + line for line in expected]:
    raise RuntimeError('Workflow patterns differ from observed offline rules')
if current[:start] + job[:begin] + job[finish:] + current[end:] != base:
    raise RuntimeError('Unexpected change outside the Swift checkout insertion')
materialization = json.loads((HERE / 'materialization-2/receipt.json').read_text())
if materialization['status'] != 'passed-offline-materialization' or not materialization['cleanup']['removed']:
    raise RuntimeError('Passing materialization/cleanup receipt required')
if not all(row['owned_group_gone'] and row['child_reaped'] for row in materialization['commands']):
    raise RuntimeError('An owned materialization child/group was not reaped')
sha = lambda raw: hashlib.sha256(raw).hexdigest()
result = {'schema': 1, 'status': 'passed-workflow-only-delta-check',
          'scope': 'Workflow byte delta and retained offline materialization receipts only',
          'command': [sys.executable, '-B', str(Path(__file__).resolve())],
          'python': platform.python_version(), 'git': materialization['git'], 'revision': REVISION,
          'collector_sha256': sha(Path(__file__).read_bytes()),
          'canonical_workflow_sha256': sha(base.encode()), 'current_workflow_sha256': sha(current.encode()),
          'patterns_sha256': sha((HERE / 'patterns.txt').read_bytes()),
          'only_swift_checkout_with_block_changed': True,
          'job_commands_toolchain_timeouts_triggers_other_jobs_equal': True,
          'all_owned_materialization_groups_gone': True, 'runtime_ci_acceptance': 'pending'}
(HERE / 'workflow-delta-2.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
print(json.dumps(result, sort_keys=True))
