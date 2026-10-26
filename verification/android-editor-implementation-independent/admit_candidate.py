#!/usr/bin/env python3
"""Admit only the exact root-released frozen packet; operate only on owned copies."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / 'verification/android-editor-implementation'
OUT = HERE / 'actual-review'
EXPECTED_SEAL = '99ee53d6cf73cc062d5f39f7caa743dfed68f0f22522788adabe83159cacc9cd'
EXPECTED_CUSTODY = '9c8f82dba143eb8360b9b89ff68b00ecf25095828dc13769f18170458559f2ea'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    custody_path = ROOT / 'verification/android-editor-boundary-root-review/implementation-review-custody.json'
    custody_bytes = custody_path.read_bytes()
    assert sha(custody_bytes) == EXPECTED_CUSTODY
    custody = json.loads(custody_bytes)
    assert custody['seal_sha256'] == EXPECTED_SEAL
    seal_bytes = (SOURCE / 'seal.json').read_bytes()
    assert sha(seal_bytes) == EXPECTED_SEAL
    seal = json.loads(seal_bytes)
    assert len(seal['members']) == 6149
    OUT.mkdir(exist_ok=True)
    copied = []
    count = size = 0
    for row in seal['members']:
        path = Path(row['path'])
        assert not path.is_absolute() and '..' not in path.parts
        absolute = SOURCE / path
        assert not absolute.is_symlink() and absolute.resolve().is_relative_to(SOURCE.resolve())
        data = absolute.read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256'], row['path']
        count += 1; size += len(data)
        if path.parts[0] in ('source', 'host-leaves', 'tests', 'cross-source', 'scripts', 'inputs') or len(path.parts) == 1:
            target = OUT / 'frozen' / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            copied.append(row)
    assert count == 6149 and size == 24007562
    (OUT / 'producer-seal.json').write_bytes(seal_bytes)
    (OUT / 'root-custody.json').write_bytes(custody_bytes)
    receipt = {
        'schema': 1, 'at': datetime.datetime.now(datetime.UTC).isoformat(),
        'argv': sys.argv, 'python': sys.version, 'script_sha256': sha(Path(__file__).read_bytes()),
        'release': 'Root message explicitly released exact frozen candidate after replacement preaccess seal',
        'producer_seal_sha256': EXPECTED_SEAL, 'root_custody_sha256': EXPECTED_CUSTODY,
        'verified_members': count, 'verified_bytes': size, 'copied_current_members': copied,
        'producer_product_tree': seal['product_source_tree_digest'],
        'producer_host_tree': seal['complete_host_closure_tree_digest'],
        'candidate_executions_at_admission': 0,
        'scope': 'Custody of complete actual-source candidate for independent review only',
        'historical_runs_hashed_not_imported_or_executed': True,
        'canonical_native_capture_ui_process_inventory_git_or_root_metadata_mutations': False,
    }
    (OUT / 'admission-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'members_verified': count, 'bytes_verified': size,
                      'current_members_copied': len(copied), 'candidate_executions': 0}))


if __name__ == '__main__':
    main()
