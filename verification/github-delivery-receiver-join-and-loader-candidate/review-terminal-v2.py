"""Root custody and source/phase review of frozen terminal CI audit v2."""
from pathlib import Path
import datetime
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
DATA = HERE / 'terminal-artifact-audit-v2'
OUT = HERE / 'terminal-v2-root-custody.json'
assert __debug__ and not OUT.exists()

def identity(path):
    b = path.read_bytes()
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

def load(path):
    return json.loads(path.read_bytes())

seal_hash = '7d9b6268b00927352e806f9958447d4e47fa61d8a99a0c1461af99ee0226ac3f'
assert identity(DATA / 'seal.json')['sha256'] == seal_hash
seal = load(DATA / 'seal.json')
names = set()
for row in seal['members']:
    p = Path(row['path'])
    assert not p.is_absolute() and '..' not in p.parts and row['path'] not in names
    names.add(row['path'])
    assert identity(DATA / p) == {k: row[k] for k in ('bytes', 'sha256')}
actual = set()
for p in DATA.rglob('*'):
    assert not p.is_symlink()
    if p.is_file() and p.name != 'seal.json':
        actual.add(str(p.relative_to(DATA)))
assert actual == names and len(names) == 74
assert sum(r['bytes'] for r in seal['members']) == 8384560
acceptance = load(DATA / 'acceptance.json')
assert identity(DATA / 'acceptance.json')['sha256'] == '09f3587e768b81c4587db2f1ed892bc009d7f94563603a205443cdba0b0493ce'
assert acceptance['source_revision'] == '3e105c206c88e18461feb66bdecc0ddb1f2b0f0a'
assert acceptance['source_tree'] == 'd23017135c7b34cb030c5b515f7da1bd4b870bb8'
assert acceptance['run_id'] == 40437321290 and acceptance['run_attempt'] == 1
assert acceptance['successful_jobs'] == 6 and acceptance['successful_steps'] == 64
assert acceptance['retries_executed'] == 0
terminal = load(DATA / 'ci-terminal.stdout')
assert terminal['headSha'] == acceptance['source_revision']
assert terminal['status'] == 'completed' and terminal['conclusion'] == 'success'
assert len(terminal['jobs']) == 6 and sum(len(j['steps']) for j in terminal['jobs']) == 64
assert all(j['conclusion'] == 'success' and all(s['conclusion'] == 'success' for s in j['steps']) for j in terminal['jobs'])
preparation = load(DATA / 'preparation.json')
for row in preparation['execution_scripts']:
    assert identity(DATA / row['path']) == row['digest']
for name in ('audit.py', 'capability_review.py'):
    assert (DATA / name).read_bytes() == (HERE / 'terminal-artifact-audit' / name).read_bytes()
commands = []
for p in sorted(DATA.rglob('*.command.json')):
    c = load(p)
    assert c['exit_code'] == 0 and not c.get('timed_out', False)
    stem = p.name.removesuffix('.command.json')
    assert identity(p.parent / c.get('stdout_file', stem + '.stdout')) == c['stdout']
    assert identity(p.parent / (stem + '.stderr')) == c['stderr']
    commands.append(str(p.relative_to(DATA)))
assert len(commands) == 18
phases = []
for name in ('terminal-collection', 'core-jvm-audit', 'capability-collection', 'capability-audit', 'acceptance'):
    c = load(DATA / (name + '.command.json'))
    assert c['direct_child_reaped'] and c['owned_process_group_absent_after_reaping']
    assert c['elapsed_seconds'] < 60 and c['child_timeout_seconds'] == 60
    assert c['auditor_sources_verified_before_child'] == preparation['execution_scripts']
    assert not c['cleanup_signals'] and not c['process_inventory_queried']
    phases.append({'name': name, 'elapsed_seconds': c['elapsed_seconds'], 'exit_code': c['exit_code']})
capability = load(DATA / 'capability/audit.json')
assert capability['status'] == 'passed-retained-host-artifact-audit'
assert [(m['mode'], m['cases_verified'], m['command_log_digests_verified']) for m in capability['modes']] == [('debug', 39, 51), ('release', 39, 51), ('tsan', 39, 51)]
assert acceptance['JVM_exact_committed_source_counts'] == [39, 90, 93]
assert acceptance['JVM_retained_class_counts'] == [0, 270, 311]
prior = acceptance['prior_failed_collection']
assert prior['timed_out'] and not prior['descendant_reaping_verified']
assert identity(HERE / 'terminal-artifact-audit/collection.command.json') == prior['command_record']
assert not (HERE / 'terminal-artifact-audit/acceptance.json').exists()
assert not (HERE / 'terminal-artifact-audit/seal.json').exists()
receipt = {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'argv': sys.argv, 'python': sys.version, 'reviewer': identity(Path(__file__)),
    'status': 'accepted-terminal-CI-and-data-only-host-artifact-scope',
    'source_revision': acceptance['source_revision'], 'source_tree': acceptance['source_tree'],
    'run_id': acceptance['run_id'], 'seal': identity(DATA / 'seal.json'),
    'closed_members_verified': 74, 'closed_member_bytes': 8384560,
    'acceptance': identity(DATA / 'acceptance.json'), 'command_output_pairs_verified': 18,
    'immutable_auditor_preexecution_and_final_hashes_equal': True,
    'base_data_auditors_equal_root_reviewed_code': True, 'phases': phases,
    'successful_jobs': 6, 'successful_steps': 64, 'run_attempt': 1,
    'original_failed_collector_remains_unaccepted': True,
    'prior_descendant_reaping_verified': False,
    'scope_limits': acceptance['limits'],
    'root_execution': 'Read-only frozen source/data/custody review only; no product, artifact, native, capture or process inventory execution',
}
OUT.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'path': str(OUT), **identity(OUT), 'members_verified': 74}))
