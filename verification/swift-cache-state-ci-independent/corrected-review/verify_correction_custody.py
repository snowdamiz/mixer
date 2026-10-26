#!/usr/bin/env python3
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import stat
import sys

HERE = Path(__file__).absolute().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / 'verification/swift-cache-state-ci-root-correction'
SEAL = '9704bd9de71610ca480a392a3e30fb3c46dd6136ce6e490218b676262da0a0d6'
RUNNER = 'd30871f94721fff10a3b508670cc9520fc021812b1d39c4655a17420308635a7'
MANIFEST = '6c52eb0ed737530d92011ce63e1eda593159c670b262a5f7bcf8b54b5338d857'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    assert sha(SOURCE / 'source-seal.json') == SEAL
    seal = json.loads((SOURCE / 'source-seal.json').read_bytes())
    rows = seal['members']
    assert len(rows) == 96
    for row in rows:
        p = SOURCE / row['path']
        assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size == row['bytes'] and sha(p) == row['sha256']
    assert sha(SOURCE / 'check_cache_state.py') == RUNNER
    assert sha(SOURCE / 'pack/manifest.json') == MANIFEST
    original = ROOT / 'verification/swift-cache-state-ci-preparation/pack'
    for row in json.loads((original / 'manifest.json').read_bytes())['members']:
        assert (SOURCE / 'pack' / row['path']).read_bytes() == (original / row['path']).read_bytes()
    copy = HERE / 'candidate-copy'
    copy.mkdir(exist_ok=False)
    shutil.copy2(SOURCE / 'check_cache_state.py', copy / 'check_cache_state.py')
    shutil.copytree(SOURCE / 'pack', copy / 'pack')
    (copy / 'runs').mkdir()
    receipt = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
        'script_sha256': sha(Path(__file__)), 'source_seal_sha256': SEAL,
        'members_verified': len(rows), 'bytes_verified': sum(r['bytes'] for r in rows),
        'runner_sha256': RUNNER, 'pack_manifest_sha256': MANIFEST,
        'pack_source_and_expected_inventory_unchanged': True, 'owned_copy': str(copy)}
    (HERE / 'custody.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print('PASS correction custody96members; unchanged exact pack; owned copy ready')

if __name__ == '__main__':
    main()
