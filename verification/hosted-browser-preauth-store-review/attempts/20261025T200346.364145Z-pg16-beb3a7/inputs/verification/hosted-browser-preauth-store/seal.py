#!/usr/bin/env python3
"""Seal one exact successful runtime attempt and preserved failure cleanup."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    attempt = ROOT / sys.argv[1]
    receipt = json.loads((attempt / 'receipt.json').read_text())
    assert receipt['success'] and len(receipt['checks']) == 30
    assert all(receipt['cleanup'].values())
    assert not receipt['source_changes'] and not receipt['dependency_changes']
    assert all(sha(ROOT / p) == h and sha(attempt / 'inputs' / p) == h for p, h in receipt['sources'].items())
    assert all(sha(ROOT / p) == h for p, h in receipt['dependencies'].items())
    assert all(sha(attempt / p) == h for p, h in receipt['outputs'].items())
    historical = {}
    for path in sorted((BASE / 'attempts').glob('*/receipt.json')):
        item = json.loads(path.read_text())
        assert all(item['cleanup'].values())
        assert not Path(item['owned_scratch']).exists()
        historical[str(path.relative_to(ROOT))] = sha(path)
    baseline = {str(p.relative_to(ROOT)): sha(p) for p in sorted((BASE / 'baseline').rglob('*')) if p.is_file()}
    payload = {
        'schema': 1,
        'recorded_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'scope': receipt['scope'],
        'review_status': 'producer_passed_independent_review_and_root_acceptance_pending',
        'selected_attempt': str(attempt.relative_to(ROOT)),
        'selected_receipt_sha256': sha(attempt / 'receipt.json'),
        'checks': 30,
        'source_revision': receipt['revision'],
        'source_tree_sha256': receipt['source_tree_sha256'],
        'sources': receipt['sources'],
        'dependency_tree_sha256': receipt['dependency_tree_sha256'],
        'output_sha256': receipt['outputs'],
        'historical_receipts': historical,
        'archived_baseline_files': baseline,
        'cleanup': receipt['cleanup'],
        'pending': [
            'independent exact-source runtime review and root acceptance',
            'full owner/lifecycle adversity matrices and all per-field mutation cases',
            'valid durable active-snapshot rejection as an independent runtime case',
            'definite response loss after successful COMMIT acknowledgement',
            'shared Application startup provenance and live supervision/re-admission',
            'production Neon TLS/5432 and external custody source qualification',
            'current verifier/provider/OIDC/claims/HTTP/console active authentication',
            'cross-replica operations, operational recovery, immutable FieldLog and GA',
            'native runtime paused and physical phones disconnected',
        ],
    }
    (BASE / 'handoff.json').write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')
    files = dict(receipt['sources'])
    files.update({str(attempt.relative_to(ROOT) / p): h for p, h in receipt['outputs'].items()})
    files[str((attempt / 'receipt.json').relative_to(ROOT))] = sha(attempt / 'receipt.json')
    files[str((BASE / 'handoff.json').relative_to(ROOT))] = sha(BASE / 'handoff.json')
    files.update(historical)
    files.update(baseline)
    (BASE / 'handoff.sha256').write_text(''.join(h + '  ' + p + '\n' for p, h in sorted(files.items())))
    print(json.dumps({'sealed': True, 'checks': 30, 'historical_receipts': len(historical),
                      'sha256_entries': len(files), 'handoff_sha256': sha(BASE / 'handoff.json')}))


if __name__ == '__main__':
    main()
