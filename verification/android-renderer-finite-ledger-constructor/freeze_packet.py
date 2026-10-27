#!/usr/bin/env python3
"""Close this lane only, after executable controls, audit and explicit cleanup."""
from pathlib import Path
import datetime
import hashlib
import json
import os

D = Path(__file__).resolve().parent


def main():
    assert not (D / 'seal.json').exists(), 'one-shot closed packet; no reseal'
    receipt = json.loads((D / 'run-1/receipt.json').read_bytes())
    validation = json.loads((D / 'validation.json').read_bytes())
    manifest = json.loads((D / 'manifest.json').read_bytes())
    cleanup = json.loads((D / 'run-1/cleanup.json').read_bytes())
    assert receipt['invocations'] == 41 and validation['status'] == 'passed-retained-artifact-audit'
    assert manifest['selected_exact_control_copy_matches']
    assert cleanup['all_started_children_bounded_and_reaped'] and cleanup['owned_compile_scratch_removed'] and cleanup['leased_JDK_preserved']
    members = []
    for base, dirs, files in os.walk(D, followlinks=False):
        for name in dirs + files:
            assert not (Path(base) / name).is_symlink()
        for name in sorted(files):
            path = Path(base) / name
            assert '__pycache__' not in path.parts and 'owned-scratch' not in path.parts
            raw = path.read_bytes()
            members.append({'path': path.relative_to(D).as_posix(), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    members.sort(key=lambda item: item['path'])
    seal = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'closed-two-finite-host-Java-controls-root-policy-selection-pending',
        'source_revision_context': '6450104dc3b02d0f4d4e572c6b05ad7fdc6657b2',
        'source_context': receipt['source_context'], 'selected_run': 'run-1',
        'receipt_sha256': hashlib.sha256((D / 'run-1/receipt.json').read_bytes()).hexdigest(),
        'member_count': len(members), 'member_bytes': sum(item['bytes'] for item in members), 'members': members,
        'scope': 'Only two exact finite Java bodies; all original enclosing/count/cleanup/authority/allocation-failure cases pending; no canonical/index/commit/push/native/process inventory operation',
        'complete_matrix_policy_native_OTA_GA_accepted': False}
    (D / 'seal.json').write_text(json.dumps(seal, indent=2) + '\n')
    print(json.dumps({'seal_sha256': hashlib.sha256((D / 'seal.json').read_bytes()).hexdigest(), 'member_count': len(members), 'member_bytes': seal['member_bytes']}))


if __name__ == '__main__':
    main()
