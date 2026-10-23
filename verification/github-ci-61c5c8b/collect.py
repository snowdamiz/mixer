#!/usr/bin/env python3
"""Verify downloaded immutable host CI receipts against their exact Git inputs."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
ARTIFACT = ROOT / 'android-host'
REVISION = '61c5c8b2e0af59ea98d3ff85f208ad97df069411'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

runner = subprocess.check_output(['git', 'show', REVISION + ':scripts/ci/check-android-binding.py'])
assignment = next(n for n in ast.parse(runner).body if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == 'SCENARIOS' for t in n.targets))
require(isinstance(assignment.value, ast.Call) and isinstance(assignment.value.func, ast.Attribute)
        and assignment.value.func.attr == 'split' and not assignment.value.args
        and not assignment.value.keywords, 'Scenario source shape changed')
scenarios = ast.literal_eval(assignment.value.func.value).split()
checks = 0
modes = []
for mode in ['debug', 'release', 'tsan']:
    directory = ARTIFACT / f'android-binding-{mode}'
    receipt = json.loads((directory / 'receipt.json').read_text())
    require(receipt['status'] == 'passed' and receipt['mode'] == mode
            and receipt['revision'] == REVISION and receipt['native_source_revision'] == REVISION
            and receipt['cases_executed'] == scenarios and receipt['runner_sha256'] == sha(runner),
            'Receipt mismatch ' + mode)
    for path, expected in receipt['input_files'].items():
        require(sha(subprocess.check_output(['git', 'show', REVISION + ':' + path])) == expected,
                'Git source mismatch ' + path)
        checks += 1
    for command in receipt['commands']:
        path = directory / 'logs' / Path(command['log']).name
        require(command['exit'] == 0 and sha(path.read_bytes()) == command['sha256'],
                'Command mismatch ' + str(path))
        if command['name'] in scenarios:
            require(('HOST_PASS ' + command['name']) in path.read_text().splitlines(),
                    'Missing exact scenario marker')
        checks += 1
    require(sha((ARTIFACT / 'capability-vm/receipt.json').read_bytes()) == receipt['native_receipt_sha256'],
            'Native receipt mismatch')
    require(all(not value['status'] for value in receipt['dependency_checkouts'].values()),
            'Dirty dependency checkout')
    modes.append({'mode': mode, 'cases': len(scenarios), 'commands': len(receipt['commands']),
                  'input_files': len(receipt['input_files']),
                  'source_tree_sha256': receipt['source_tree_sha256']})
toolchain = json.loads((ARTIFACT / 'apple-toolchain.json').read_text())
require(toolchain['swiftVersion'] == [6, 2, 4] and toolchain['sourceRevision'] == REVISION,
        'Toolchain mismatch')
jobs = json.loads((ROOT / 'jobs.json').read_text())['jobs']
require(all(job['status'] == 'completed' for job in jobs), 'Jobs incomplete')
require({j['name']: j['conclusion'] for j in jobs} == {'vm': 'failure', 'swift': 'success', 'services': 'success'},
        'Unexpected job conclusion')
receipt = {
    'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'revision': REVISION, 'run': 40016654693,
    'url': 'https://github.com/snowdamiz/mixer/actions/runs/40016654693',
    'conclusion': 'failure',
    'jobs': [{key: job[key] for key in ['id', 'name', 'status', 'conclusion']} for job in jobs],
    'android_host': {'status': 'passed', 'modes': modes,
                     'git_input_and_command_hash_checks': checks, 'swift_version': toolchain['swiftVersion'],
                     'artifact_id': 12529138272,
                     'artifact_zip_sha256': '2c4eb865ebc0c852999faf5e570d6aa95b26e039d776b3e74220476c14f86b70',
                     'artifact_download_digest_matched': True},
    'failure': 'Minimal Swift reactor tests passed; Clippy rejected unused GlobalView fields. Descriptor-only repair is checkpoint d6c41a06f9b787250a2ef3c30e51014f0b72b043; its VM job passes, full run pending at collection.',
    'scope': 'First hosted pinned Swift6.2.4 fresh private Android host runner:39 ordinary scenarios each Debug/Release/TSan with actual source/dependency checks and native archive rebuilt at same revision. Services and all Swift steps passed. Overall checkpoint failed VM lint.',
    'limits': 'Host evidence only. No JNI/Android native authority, S4-21 native delivery, S4-29 optimized Release counter injection, full Swift target, physical visual parity, published FieldLog, store or GA qualification. Rust archive TSan instrumentation is not claimed.',
    'files': {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in sorted(ROOT.rglob('*'))
              if path.is_file() and path.name != 'receipt.json' or path.is_file() and path.parent != ROOT},
}
destination = ROOT / 'receipt.json'
require(not destination.exists(), 'Do not overwrite immutable collection')
destination.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'checks': checks, 'modes': modes}, indent=2))
