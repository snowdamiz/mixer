"""Freeze the fresh data-only fixture audit and its retained command outputs."""
import datetime
import json
import pathlib
import sys
import zipfile
from capture import digest, ROOT

assert __debug__ and not (ROOT / 'seal.json').exists()
def read(name):
    return json.loads((ROOT / name).read_bytes())
def save(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2) + '\n')

commands = []
resolution = read('audit-failure-resolution.json')
assert digest((ROOT / resolution['failed_script']).read_bytes())['sha256'] == resolution['failed_auditor_sha256']
assert digest((ROOT / 'audit-content.py').read_bytes())['sha256'] == resolution['corrected_auditor_sha256']
assert resolution['CI_retries_executed'] == 0 and not resolution['artifact_or_CI_retried'] and not resolution['source_fixture_changed']
failures = []
for path in sorted(ROOT.glob('*.command.json')):
    command = read(path.name)
    name = path.name.removesuffix('.command.json')
    assert not command['timed_out']
    assert command['exit_code'] == (1 if path.name in resolution['failed_command_records'] else 0)
    if command['exit_code'] != 0:
        failures.append(path.name)
    assert digest((ROOT / command['stdout_file']).read_bytes()) == command['stdout']
    assert digest((ROOT / (name + '.stderr')).read_bytes()) == command['stderr']
    commands.append(path.name)
assert set(failures) == set(resolution['failed_command_records'])
assert read('content-audit-corrected.command.json')['exit_code'] == 0
report = read('full-audit.json')
with zipfile.ZipFile(ROOT / 'fixture-artifact.zip') as archive:
    runner_receipt = json.loads(archive.read('runs/ci-40387011950-1/receipt.json'))
authority_flags = {k: runner_receipt[k] for k in ('storedPrefixValidated', 'fullReplayAccepted', 'semanticMetricsValid', 'GA_qualified', 'model_imported_or_evaluated')}
assert all(v is False for v in authority_flags.values())
assert max(c['elapsed_seconds'] for c in runner_receipt['commands']) <= 60
run = read('run-at-fixture-audit.stdout')
fixture, = [j for j in read('jobs-at-fixture-audit.stdout')['jobs'] if j['name'] == 'swift-cache-state-fixture']
assert report['passed'] and report['actual_compiler_release'] == '1.98.1'
assert report['source_revision'] == run['head_sha'] == fixture['head_sha']
assert run['run_attempt'] == fixture['run_attempt'] == 1
assert fixture['conclusion'] == 'success' and len(fixture['steps']) == 8
assert all(s['status'] == 'completed' and s['conclusion'] == 'success' for s in fixture['steps'])
receipt = {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'argv': sys.argv, 'python': sys.version,
    'status': 'accepted-exact-Rust1.98.1-Actions-closed-host-fixture-only',
    'source_revision': report['source_revision'], 'source_tree': report['source_tree'],
    'run_id': run['id'], 'run_url': run['html_url'], 'run_attempt': run['run_attempt'],
    'fixture_job': {'id': fixture['id'], 'name': fixture['name'], 'conclusion': fixture['conclusion'], 'steps': 8},
    'global_status_at_snapshot': run['status'], 'global_conclusion_at_snapshot': run['conclusion'], 'global_CI_qualified': False,
    'fixture_component_accepted': True, 'artifact': report['artifact'],
    'actual_compiler': report['compiler'],
    'source_bindings': {'canonical_paths': 91, 'runner_sha256': report['runner_sha256'], 'pack_manifest_sha256': digest((ROOT / 'sources/verification/swift-cache-state-ci/pack/manifest.json').read_bytes())['sha256'], 'workflow_sha256': digest((ROOT / 'source-workflow.stdout').read_bytes())['sha256']},
    'normal_full_invocations': 1, 'commands': 103, 'focused_controls': report['focused_controls'],
    'modes': report['modes'],
    'active_elapsed_seconds': report['active_elapsed_seconds'], 'cleanup_elapsed_seconds': report['cleanup_elapsed_seconds'],
    'elapsed_seconds': report['elapsed_seconds'], 'max_child_seconds': report['max_child_seconds'],
    'deadlines': {'active_seconds': 600, 'cleanup_seconds': 60, 'child_seconds': 60, 'unchanged': True},
    'retained_logical_files_verified': report['retained_files_verified'], 'retained_logical_bytes_verified': report['retained_logical_bytes_verified'],
    'unique_content_members_verified': report['unique_content_members_verified'], 'derived_source_files_verified': report['derived_source_files_verified'],
    'compiler_products_hashed_removed_per_receipt': report['compiler_products_hashed_removed'], 'postflight_checks_passed': report['postflight_checks_passed'],
    'full_raw_audit_sha256': digest((ROOT / 'full-audit.json').read_bytes())['sha256'],
    'command_records_digest_verified': len(commands), 'command_records': commands,
    'CI_retries_executed': 0, 'limits': report['limits'],
    'retained_local_auditor_failures': failures,
    'retained_local_auditor_failure_scope': 'Local additional selection-cardinality assertion and its containing collector failed; no fixture CI failure is claimed. Exact first auditor script, stdout, stderr and command records are retained.',
    'audit_failure_resolution': resolution,
    'cleanup': {'artifact_code_extracted_or_executed': False, 'native_runtime_or_capture_or_process_inventory': False, 'new_Rust_invocations': 0, 'children_reaped': True},
    'new_profile_adapter_or_full_runtime_or_GA_qualified': False,
    'isolated_profile_row_adapter_in_canonical_fixture': False,
    'isolated_profile_row_adapter_CI_qualified': False,
    'all_authority_flags_false': True,
    'authority_flags': authority_flags,
}
save('acceptance.json', receipt)
members = []
for path in sorted(ROOT.rglob('*')):
    assert not path.is_symlink()
    if path.is_file():
        members.append({'path': str(path.relative_to(ROOT)), **digest(path.read_bytes())})
seal = {'schema': 1, 'at': receipt['at'], 'source_revision': report['source_revision'], 'source_tree': report['source_tree'], 'run_id': run['id'], 'acceptance_sha256': digest((ROOT / 'acceptance.json').read_bytes())['sha256'], 'members': members, 'member_count': len(members), 'total_bytes': sum(m['bytes'] for m in members)}
save('seal.json', seal)
print(json.dumps({'status': 'sealed', 'seal_sha256': digest((ROOT / 'seal.json').read_bytes())['sha256'], 'acceptance_sha256': seal['acceptance_sha256'], 'members': len(members), 'bytes': seal['total_bytes']}))
