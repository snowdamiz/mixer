"""Fresh finite terminal/artifact data audit; no artifact code execution."""
import datetime
import json
import pathlib
import subprocess
import sys

import audit

HERE = pathlib.Path(__file__).resolve().parent
EXPECTED_TREE = '52e887a6a99623b6a2f6f2c5e9788147e0fb91fd'
assert __debug__, 'Assertions must remain enabled'
assert not (HERE / 'acceptance.json').exists(), 'Accepted audit is one-shot'


def capture(name, argv, stdout_file=None):
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=audit.REPO, capture_output=True, timeout=60)
    stdout_file = stdout_file or (name + '.stdout')
    (HERE / stdout_file).write_bytes(result.stdout)
    (HERE / (name + '.stderr')).write_bytes(result.stderr)
    (HERE / (name + '.command.json')).write_text(json.dumps({
        'started_utc': start, 'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'argv': argv, 'cwd': str(audit.REPO), 'exit_code': result.returncode,
        'stdout_file': stdout_file, 'stdout': audit.digest(result.stdout), 'stderr': audit.digest(result.stderr),
        'scope': 'Read-only terminal CI, artifact download or exact committed source inspection',
    }, indent=2) + '\n')
    assert result.returncode == 0, (name, result.returncode)
    return result.stdout


assert audit.digest((audit.REPO / 'verification/github-delivery-ci-framing-readiness-repair/fixture-artifact-audit/acceptance.json').read_bytes())['sha256'] == 'f8a67c214a903018dba3acb99cb88f0885895ebdaa6fd96032978311df31b0cd'
capture('gh-version', ['gh', '--version'])
capture('git-version', ['git', '--version'])
run = json.loads(capture('ci-run-api', ['gh', 'api', f'repos/snowdamiz/mixer/actions/runs/{audit.RUN}']))
assert run['id'] == audit.RUN and run['head_sha'] == audit.SHA
assert run['status'] == 'completed' and run['conclusion'] == 'success'
assert run['run_attempt'] == 1
assert run['event'] == 'push' and run['head_branch'] == 'main'
assert run['head_repository']['full_name'] == 'snowdamiz/mixer'
terminal = json.loads(capture('ci-terminal', ['gh', 'run', 'view', str(audit.RUN), '--repo', 'snowdamiz/mixer', '--json', 'status,conclusion,headSha,jobs,url']))
assert terminal['status'] == 'completed' and terminal['conclusion'] == 'success' and terminal['headSha'] == audit.SHA
expected_names = {'swift', 'swift-capability-native', 'vm', 'services', 'android-owner-host', 'swift-cache-state-fixture'}
assert {j['name'] for j in terminal['jobs']} == expected_names
assert len(terminal['jobs']) == 6 and sum(len(j['steps']) for j in terminal['jobs']) == 64
assert all(j['status'] == 'completed' and j['conclusion'] == 'success' and all(s['conclusion'] == 'success' for s in j['steps']) for j in terminal['jobs'])
jobs = json.loads(capture('ci-jobs-api', ['gh', 'api', f'repos/snowdamiz/mixer/actions/runs/{audit.RUN}/jobs?per_page=100']))
assert jobs['total_count'] == len(jobs['jobs']) == 6
assert {j['name'] for j in jobs['jobs']} == expected_names
assert {j['id'] for j in jobs['jobs']} == {j['databaseId'] for j in terminal['jobs']}
assert sum(len(j['steps']) for j in jobs['jobs']) == 64
assert all(j['status'] == 'completed' and j['conclusion'] == 'success' and j['head_sha'] == audit.SHA and j['run_attempt'] == 1 and all(s['status'] == 'completed' and s['conclusion'] == 'success' for s in j['steps']) for j in jobs['jobs'])
logs = capture('ci-full-log', ['gh', 'run', 'view', str(audit.RUN), '--repo', 'snowdamiz/mixer', '--log'])
assert audit.SHA.encode() in logs
source_tree = capture('source-tree', ['git', 'rev-parse', audit.SHA + '^{tree}']).decode().strip()
assert source_tree == EXPECTED_TREE
workflow = capture('workflow-source', ['git', 'show', audit.SHA + ':.github/workflows/verify.yml'])
assert audit.digest(workflow)['sha256'] == audit.WORKFLOW_HASH
metadata = json.loads(capture('artifact-metadata', ['gh', 'api', f'repos/snowdamiz/mixer/actions/runs/{audit.RUN}/artifacts?per_page=100']))
assert metadata['total_count'] == len(metadata['artifacts'])
for name in ('swift-core-toolchain-host', 'android-owner-host'):
    artifact, = [a for a in metadata['artifacts'] if a['name'] == name + '-' + audit.SHA]
    capture(name, ['gh', 'api', f"repos/snowdamiz/mixer/actions/artifacts/{artifact['id']}/zip"], name + '.zip')
core = audit.audit_core()
jvm = audit.audit_jvm()
audit.write_json('source-blobs.json', audit.SOURCE_RECORDS)
audit.write_json('core-jvm-audit.json', {'core': core, 'jvm': jvm, 'source_revision': audit.SHA, 'source_tree': source_tree, 'run': audit.RUN, 'source_blobs': audit.digest((HERE / 'source-blobs.json').read_bytes()), 'source_commands': audit.digest((HERE / 'source-commands.json').read_bytes())})
# A separate audit process owns capability-specific globals and retained custody.
capture('capability-collection', [sys.executable, '-B', str(HERE / 'capability_review.py'), 'collect'])
capture('capability-audit', [sys.executable, '-B', str(HERE / 'capability_review.py'), 'audit'])
capability = json.loads((HERE / 'capability/audit.json').read_text())
assert capability['status'] == 'passed-retained-host-artifact-audit'
receipt = {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'argv': sys.argv, 'python': sys.version, 'source_revision': audit.SHA,
    'source_tree': source_tree, 'workflow_sha256': audit.WORKFLOW_HASH,
    'run_id': audit.RUN, 'run_url': terminal['url'], 'run_attempt': run['run_attempt'],
    'status': 'all-six-jobs-and-retained-host-artifacts-pass',
    'scope': 'Terminal CI status and data-only retained core/JVM/capability host artifacts against exact committed source bytes',
    'successful_jobs': len(terminal['jobs']), 'successful_steps': sum(len(j['steps']) for j in terminal['jobs']),
    'retries_executed': 0, 'job_statuses': [{'name':j['name'], 'id':j['id'], 'status':j['status'], 'conclusion':j['conclusion'], 'steps':len(j['steps'])} for j in jobs['jobs']],
    'full_ci_log': {**audit.digest(logs), 'path':'ci-full-log.stdout', 'qualification':'Retained terminal CI context; passing steps are GitHub statuses, not independent reexecution'},
    'core': {k: core[k] for k in ('id', 'sha256', 'members', 'member_bytes')},
    'JVM': {k: jvm[k] for k in ('id', 'sha256', 'members', 'member_bytes')},
    'capability': {k: capability[k] for k in ('id', 'sha256', 'members', 'member_bytes')},
    'binding_cases_per_mode': 39, 'binding_command_logs_per_mode': 51,
    'separate_fixture_artifact_acceptance': {'path': 'verification/github-delivery-ci-framing-readiness-repair/fixture-artifact-audit/acceptance.json', 'sha256': 'f8a67c214a903018dba3acb99cb88f0885895ebdaa6fd96032978311df31b0cd', 'scope':'Actual Rust1.98.1 closed host fixture separately audited'},
    'limits': [
        'Core library/build-log and capability native-library/tool/9 native command logs are receipt-only hashes',
        'JVM environment class hashes only; other two closures retain 581 class members',
        'TSAN covers the Swift host harness, not Rust archive',
        'Other workflow artifact families were not downloaded or audited; this acceptance covers the three selected core/JVM/capability archives',
        'No new native runtime, UI, screen capture, physical device, simulator/emulator, public V2, signed package, FieldLog or GA qualification',
    ],
    'cleanup': {'artifacts_extracted_or_executed': False, 'native_or_capture_processes_started_or_queried': False, 'children_reaped': True, 'git_mutations': False, 'network_mutations': False},
}
(HERE / 'acceptance.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
