"""Seal or read-only check of the local CI input-selection evidence."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sha = lambda data: hashlib.sha256(data).hexdigest()
def members():
    result = []
    for path in sorted(ROOT.rglob('*')):
        assert not path.is_symlink()
        if not path.is_file() or path == ROOT / 'seal.json': continue
        data = path.read_bytes()
        result.append({'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)})
    return result

seal_path = ROOT / 'seal.json'
if sys.argv[1:] == ['--check']:
    value = json.loads(seal_path.read_text())
    assert value['members'] == members()
else:
    assert sys.argv[1:] == [] and not seal_path.exists()
    audit = json.loads((ROOT / 'receipt.json').read_text())
    assert audit['result'] == 'local-sparse-materialization-and-offline-generators-pass'
    assert audit['inputs_and_workflow_unchanged'] and audit['owned_scratch_removed']
    assert all(c['exit'] == 0 and not c['timed_out'] and c['owned_group_absent'] for c in audit['commands'])
    workflow = ROOT.parents[1] / '.github/workflows/verify.yml'
    body = workflow.read_bytes()
    assert sha(body) == audit['workflow_before_sha256']
    with (ROOT / 'workflow-candidate.yml').open('xb') as stream: stream.write(body)
    rows = members()
    value = {'schema': 1, 'members': rows, 'member_count': len(rows), 'member_bytes': sum(r['bytes'] for r in rows),
        'tree_sha256': sha(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()),
        'scope': 'local actual Git sparse materialization and offline generators; remote CI pending',
        'workflow_sha256': sha(body), 'product_changed': False, 'remote_CI_passed': False}
    with seal_path.open('x') as stream: json.dump(value, stream, indent=2); stream.write('\n')
assert value['member_count'] == len(value['members'])
assert value['member_bytes'] == sum(r['bytes'] for r in value['members'])
print(json.dumps({'seal_sha256': sha(seal_path.read_bytes()), 'members': value['member_count'], 'bytes': value['member_bytes']}))
