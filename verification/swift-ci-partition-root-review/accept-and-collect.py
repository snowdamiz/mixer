"""One-shot root custody/structural review and exact workflow application."""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PACKET = ROOT / 'verification/swift-ci-partition-review'
BASE = '5583fb2c61e2c12acb5f0120a9a072e05cdb5ac1'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def write(name, data):
    path = OUT / name
    with path.open('x') as f:
        json.dump(data, f, indent=2)
        f.write('\n')

def run(label, argv, allowed=(0,)):
    receipt_path = OUT / (label + '.command.json')
    if receipt_path.exists():
        prior = json.loads(receipt_path.read_bytes())
        assert prior['argv'] == argv and prior['exit'] in allowed
        stdout = (OUT / (label + '.stdout')).read_bytes()
        stderr = (OUT / (label + '.stderr')).read_bytes()
        assert sha(stdout) == prior['stdout_sha256'] and sha(stderr) == prior['stderr_sha256']
        return stdout  # Immutable already completed observation, never overwritten.
    before = datetime.datetime.now(datetime.UTC).isoformat()
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
    for suffix, value in [('stdout', result.stdout), ('stderr', result.stderr)]:
        with (OUT / (label + '.' + suffix)).open('xb') as f:
            f.write(value)
    write(label + '.command.json', {'argv': argv, 'at': before,
          'exit': result.returncode, 'stdout_sha256': sha(result.stdout),
          'stderr_sha256': sha(result.stderr), 'timeout_seconds': 60})
    if result.returncode not in allowed:
        raise RuntimeError(label + ' failed')
    return result.stdout

if (OUT / 'acceptance.json').exists():
    raise SystemExit('one-shot receipt already exists')
assert run('source-revision', ['git', 'rev-parse', 'HEAD']).decode().strip() == BASE
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip() == BASE
run('gh-version', ['gh', '--version'])
run('ruby-version', ['ruby', '-rpsych', '-e', 'puts RUBY_DESCRIPTION; puts Psych::VERSION'])
terminal = json.loads(run('terminal-run', ['gh', 'run', 'view', '40347513075',
    '--repo', 'snowdamiz/mixer', '--json',
    'attempt,status,conclusion,headSha,createdAt,updatedAt,jobs,url']))
assert terminal['status'] == 'completed' and terminal['headSha'] == BASE
assert terminal['conclusion'] == 'cancelled' and terminal['attempt'] == 1
swift = next(j for j in terminal['jobs'] if j['name'] == 'swift')
assert swift['databaseId'] == 121658283739 and swift['conclusion'] == 'cancelled'
assert all(j['conclusion'] == 'success' for j in terminal['jobs'] if j['name'] != 'swift')
job = json.loads(run('swift-job', ['gh', 'api',
    'repos/snowdamiz/mixer/actions/jobs/121658283739']))
check = json.loads(run('swift-check', ['gh', 'api', job['check_run_url']]))
annotations = json.loads(run('swift-annotations', ['gh', 'api', check['url'] + '/annotations']))
assert any('exceeded the maximum execution time of 30m' in a['message'] for a in annotations)
run('swift-logs-safe-capture', ['gh', 'api', 'repos/snowdamiz/mixer/actions/jobs/121658283739/logs',
    '--allow-escape-sequences'])  # Retain raw bytes as data; never display them as terminal control.
run('branch-protection', ['gh', 'api', 'repos/snowdamiz/mixer/branches/main/protection'], (0, 1))
rules = json.loads(run('branch-rules', ['gh', 'api', 'repos/snowdamiz/mixer/rules/branches/main']))
assert rules == []

manifest_bytes = (PACKET / 'packet-manifest.json').read_bytes()
assert sha(manifest_bytes) == 'a30c660e9ca4a5bab3cbdf5279792e2deee216783dcf1ab091fd8ad5187a732d'
manifest = json.loads(manifest_bytes)
total = 0
for row in manifest['members']:
    rel = Path(row['path'])
    assert not rel.is_absolute() and '..' not in rel.parts
    p = PACKET / rel
    assert not p.is_symlink()
    b = p.read_bytes()
    assert len(b) == row['bytes'] and sha(b) == row['sha256'], str(p)
    total += len(b)
assert len(manifest['members']) == 30
sources = json.loads((PACKET / 'source-evidence.json').read_bytes())['files']
for row in sources:
    b = (ROOT / row['path']).read_bytes()
    assert len(b) == row['bytes'] and sha(b) == row['sha256'], row['path']
workflow = ROOT / '.github/workflows/verify.yml'
old = workflow.read_bytes()
proposed = (PACKET / 'proposed-verify.yml').read_bytes()
assert old == (PACKET / 'original-verify.yml').read_bytes()
assert sha(proposed) == '0afea45a4545c40d11096db2cb6030674f9eb8631ec4b90cbeb030271382512b'
parsed = run('root-yaml-parse', ['ruby', '-rpsych', '-rjson', '-e',
    'ARGV.each { |p| puts JSON.generate(Psych.safe_load_file(p, aliases:false)) }',
    str(PACKET / 'original-verify.yml'), str(PACKET / 'proposed-verify.yml')])
a, b = [json.loads(line) for line in parsed.splitlines()]
assert {k:v for k,v in a.items() if k != 'jobs'} == {k:v for k,v in b.items() if k != 'jobs'}
assert set(b['jobs']) - set(a['jobs']) == {'swift-capability-native'}
for name in ('android-owner-host', 'vm', 'services'):
    assert a['jobs'][name] == b['jobs'][name]
old_job = a['jobs']['swift']
new_jobs = [b['jobs'][n] for n in ('swift', 'swift-capability-native')]
metadata = {k:v for k,v in old_job.items() if k != 'steps'}
assert all({k:v for k,v in j.items() if k != 'steps'} == metadata for j in new_jobs)
assert new_jobs[0]['steps'][:-1] == old_job['steps'][:13] + [old_job['steps'][-1]]
assert new_jobs[1]['steps'] == old_job['steps'][:2] + old_job['steps'][13:18]
extra = new_jobs[0]['steps'][-1]
assert extra['if'] == 'always()' and extra['uses'] == 'actions/upload-artifact@v4'
assert extra['with']['retention-days'] == 14
assert sum(len(j['steps']) for j in a['jobs'].values()) == 37
assert sum(len(j['steps']) for j in b['jobs'].values()) == 40
workflow.write_bytes(proposed)
write('acceptance.json', {
    'schema': 1, 'at': datetime.datetime.now(datetime.UTC).isoformat(),
    'command': 'python3 -B verification/swift-ci-partition-root-review/accept-and-collect.py',
    'python': sys.version, 'source_revision': BASE,
    'review_manifest_sha256': sha(manifest_bytes), 'members_verified': 30,
    'member_bytes': total, 'reviewed_live_sources_verified': len(sources),
    'old_workflow_sha256': sha(old), 'new_workflow_sha256': sha(proposed),
    'old_source_steps': 37, 'new_source_steps': 40,
    'exact_old_step_objects_preserved': True,
    'added_work': 'Duplicate exact checkout/toolchain probe, core receipt upload',
    'all_five_terminal_jobs_required_for_root_acceptance': True,
    'branch_rules_observed': rules,
    'previous_run': 40347513075, 'previous_run_conclusion': terminal['conclusion'],
    'previous_swift_job': swift['databaseId'],
    'timeout_annotation_verified': True,
    'previous_generated_consumer_skipped': True,
    'retained_collection_failure': 'swift-logs.command.json: gh declined terminal escape sequences; safe retry captures bytes as data without rendering',
    'decision': 'Apply exact independently reviewed job partition; actual CI execution pending',
    'product_or_runtime_limits_changed': False,
    'runtime_device_capture_or_GA_qualified': False,
    'cleanup': 'Read-only command children returned; no native/capture process started'
})
print('Root verified 30 review members, retained terminal cancellation, and applied exact two-job partition.')
