"""Freeze the current terminal CI artifact audit without executing artifacts."""
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
assert __debug__ and not (ROOT / 'seal.json').exists()
def digest(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

acceptance = json.loads((ROOT / 'acceptance.json').read_bytes())
assert acceptance['source_revision'] == 'a9ea84aa33320cadaed2340fe637324b694a917f'
assert acceptance['source_tree'] == '52e887a6a99623b6a2f6f2c5e9788147e0fb91fd'
assert acceptance['successful_jobs'] == 6 and acceptance['successful_steps'] == 64
assert acceptance['retries_executed'] == 0 and acceptance['run_attempt'] == 1
commands = []
for path in sorted(ROOT.rglob('*.command.json')):
    row = json.loads(path.read_bytes())
    assert row['exit_code'] == 0, str(path)
    name = path.name.removesuffix('.command.json')
    stdout = path.parent / row.get('stdout_file', name + '.stdout')
    stderr = path.parent / (name + '.stderr')
    assert digest(stdout.read_bytes()) == row['stdout'], str(stdout)
    assert digest(stderr.read_bytes()) == row['stderr'], str(stderr)
    commands.append(str(path.relative_to(ROOT)))
members = []
for path in sorted(ROOT.rglob('*')):
    assert not path.is_symlink()
    if path.is_file():
        members.append({'path': str(path.relative_to(ROOT)), **digest(path.read_bytes())})
seal = {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'scope': 'Frozen exact-source terminal six-job CI and retained core/JVM/capability artifact audit; separate fixture audit remains separately sealed',
    'source_revision': acceptance['source_revision'], 'source_tree': acceptance['source_tree'],
    'run_id': acceptance['run_id'], 'acceptance_sha256': digest((ROOT / 'acceptance.json').read_bytes())['sha256'],
    'command_records_verified': commands, 'members': members, 'member_count': len(members),
    'total_bytes': sum(m['bytes'] for m in members),
}
(ROOT / 'seal.json').write_text(json.dumps(seal, indent=2) + '\n')
print(json.dumps({'status': 'sealed', 'acceptance_sha256': seal['acceptance_sha256'], 'seal_sha256': digest((ROOT / 'seal.json').read_bytes())['sha256'], 'members': len(members), 'bytes': seal['total_bytes']}))
