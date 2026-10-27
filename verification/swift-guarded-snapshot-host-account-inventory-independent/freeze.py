#!/usr/bin/env python3
"""Freeze only this independent packet; no source or Git mutations."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    assert not (HERE / 'seal.json').exists(), 'already frozen'
    results = json.loads((HERE / 'results.json').read_text())
    assert results['checks_passed'] == 2004
    listing = []
    for path in sorted(HERE.rglob('*')):
        if path.is_file():
            data = path.read_bytes()
            listing.append({'path': path.relative_to(HERE).as_posix(), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    seal = {'schema': 1, 'status': 'frozen-independent-bounded-source-object-inventory-review', 'members': listing, 'member_count': len(listing), 'member_bytes': sum(i['bytes'] for i in listing), 'source_tree_sha256': results['source_tree_sha256'], 'checks_passed': results['checks_passed'], 'whole_quote_P0_fixture_operational_native_OTA_GA_authority': False}
    (HERE / 'seal.json').write_text(json.dumps(seal, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'member_count': seal['member_count'], 'member_bytes': seal['member_bytes'], 'seal_sha256': hashlib.sha256((HERE / 'seal.json').read_bytes()).hexdigest()}, sort_keys=True))


if __name__ == '__main__':
    main()
