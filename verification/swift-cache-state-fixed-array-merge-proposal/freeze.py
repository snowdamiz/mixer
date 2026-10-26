#!/usr/bin/env python3
"""Freeze only this new source-only rejected packet."""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    members = []
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and path.name != 'seal.json':
            assert '__pycache__' not in path.parts
            data = path.read_bytes()
            members.append({'path': str(path.relative_to(ROOT)), 'bytes': len(data),
                            'sha256': hashlib.sha256(data).hexdigest()})
    bound = json.loads((HERE / 'necessary-bound.json').read_text())
    run = json.loads((HERE / 'run.json').read_text())
    verified = json.loads((HERE / 'verify.stdout.json').read_text())
    assert bound['necessary_groups'] == 2605 > bound['cap'] == 2568
    assert verified['G3_floor'] == 2605 and verified['all_counted_events_grouped_once'] is True
    packet = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'status': 'sealed failed fixed-array/source-expanded necessary-bound proposal; independent root review pending',
              'command': [sys.executable, '-B', str(HERE / 'freeze.py')], 'python': sys.version,
              'source_revision': run['source_revision'],
              'owned_scope': ['verification/swift-cache-state-fixed-array-merge-proposal/**'],
              'member_count': len(members), 'member_bytes': sum(row['bytes'] for row in members), 'members': members,
              'necessary_G3_groups': 2605, 'G3_cap': 2568, 'G3_over_cap': 37,
              'G2_G5_complete_component_recount_built': False,
              'numeric_caps_or_selected_grammar_changed': False,
              'compiler_runtime_native_UI_capture_or_process_inventory_executed': False,
              'Git_or_hosted_access': False, 'product_old_packet_or_root_metadata_mutated': False,
              'complete_new_path_or_lifetime_accepted': False, 'implementation_or_GA_accepted': False}
    (HERE / 'seal.json').write_text(json.dumps(packet, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'member_count': packet['member_count'], 'member_bytes': packet['member_bytes'],
                      'seal_sha256': hashlib.sha256((HERE / 'seal.json').read_bytes()).hexdigest(),
                      'necessary_G3_groups': 2605, 'status': packet['status']}, indent=2))


if __name__ == '__main__':
    main()
