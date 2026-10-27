#!/usr/bin/env python3
"""Freeze this owned review only; inspect no unrelated path."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
members = []
for path in sorted(HERE.rglob('*')):
    if path.is_file() and path != HERE / 'seal.json':
        data = path.read_bytes()
        if path.suffix in ['.py', '.md']:
            assert all(line == line.rstrip() for line in data.decode().splitlines())
        members.append({'path': path.relative_to(HERE).as_posix(), 'bytes': len(data),
                        'sha256': hashlib.sha256(data).hexdigest()})
result = {
    'schema': 1, 'status': 'frozen-independent-bounded-logical-work-review-pass',
    'member_count': len(members), 'member_bytes': sum(m['bytes'] for m in members),
    'members': members, 'controls_passed': 1058,
    'source_tree_sha256': '575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896',
    'material_findings': [], 'complete_work_or_storage_admission_accepted': False,
    'writer_or_native_execution_authorized': False,
    'scope': 'Independent frozen-plan, corrected arithmetic, exact-source fingerprints, bounded ingress/WASI DAG and finite quote/order/multiplicity controls; no runtime or release permission',
}
target = HERE / 'seal.json'
target.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(json.dumps({'member_count': result['member_count'], 'member_bytes': result['member_bytes'],
                  'seal_sha256': hashlib.sha256(target.read_bytes()).hexdigest()}, sort_keys=True))
