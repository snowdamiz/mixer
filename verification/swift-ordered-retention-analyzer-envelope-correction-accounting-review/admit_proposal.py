#!/usr/bin/env python3
"""Admit only root-selected immutable proposal; execute no producer code."""
import hashlib
import json
from pathlib import Path
import sys
from datetime import datetime, timezone
from prepare_baseline import verify_old_seals

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
PROPOSAL = ROOT/'verification/swift-ordered-retention-analyzer-envelope-correction/commands/operation-ledger-proposal-1'
MANIFEST = 'f3567bdae0835d7f024fcf7e759e197c44a7b4571204b37c80fb6c596e5bc23d'
def sha(data): return hashlib.sha256(data).hexdigest()
def write_json(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
def verify_proposal():
    raw = (PROPOSAL/'manifest.json').read_bytes()
    assert sha(raw) == MANIFEST
    manifest = json.loads(raw)
    total = 0
    for item in manifest['members']:
        path = PROPOSAL/item['path']; assert path.resolve().is_relative_to(PROPOSAL.resolve())
        data = path.read_bytes(); assert len(data) == item['bytes'] and sha(data) == item['sha256'], item['path']
        total += len(data)
    assert len(manifest['members']) == 15 and total == 321919
    return {'manifest_sha256': MANIFEST, 'members': 15, 'bytes': total}
def main():
    run = OWN/'commands/proposal-admission-1'; run.mkdir(parents=True, exist_ok=False)
    before = verify_proposal(); old_before = verify_old_seals()
    dest = run/'inputs'; dest.mkdir()
    manifest = json.loads((PROPOSAL/'manifest.json').read_bytes())
    copies = []
    for name in [item['path'] for item in manifest['members']] + ['manifest.json']:
        data = (PROPOSAL/name).read_bytes(); target = dest/name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        copies.append({'source': str((PROPOSAL/name).relative_to(ROOT)), 'copy': str(target.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)})
    after = verify_proposal(); old_after = verify_old_seals(); assert before == after and old_before == old_after
    receipt = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'invocation': sys.orig_argv,
               'status': 'immutable-operation-proposal-admitted-for-review-no-numeric-selection',
               'before': before, 'after': after, 'old_before': old_before, 'old_after': old_after,
               'copies': copies, 'independent_copy_tree_sha256': sha(json.dumps(copies, sort_keys=True, separators=(',', ':')).encode()),
               'runtime_probes_executed': False, 'producer_code_executed': False, 'numeric_values_selected': False,
               'native_capture_process_or_device_discovery': False,
               'review_script_sha256': sha(Path(__file__).read_bytes()),
               'cleanup': 'No child, executable or disposable scratch created; exact immutable proposal copies and custody receipt retained.'}
    write_json(run/'receipt.json', receipt)
    output = json.dumps({'status': receipt['status'], 'members': 15, 'bytes': 321919, 'old_members_unchanged': 860}, sort_keys=True)+'\n'
    (run/'stdout.txt').write_text(output); (run/'stderr.txt').write_text(''); print(output, end='')
if __name__ == '__main__': main()
