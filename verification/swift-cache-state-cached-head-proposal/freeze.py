#!/usr/bin/env python3
import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
assert json.loads((HERE / 'verify.stdout.json').read_text())['checks_passed']
members = []
for path in sorted(HERE.rglob('*')):
    if path.is_file() and path.name != 'seal.json':
        data = path.read_bytes()
        members.append({'path': str(path.relative_to(ROOT)), 'bytes': len(data),
                        'sha256': hashlib.sha256(data).hexdigest()})
seal = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command': [sys.executable, '-B', str(HERE / 'freeze.py')], 'python': sys.version,
        'status': 'sealed failed finite cached-head source candidate; independent review pending',
        'owned_scope': ['verification/swift-cache-state-cached-head-proposal/**'],
        'members': members, 'member_count': len(members), 'member_bytes': sum(x['bytes'] for x in members),
        'source_revision': '0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8',
        'necessary_G3_groups': 2653, 'G3_cap': 2568, 'necessary_G4_groups': 778, 'G4_cap': 768,
        'G2_G5_complete_component_recount_built': False,
        'complete_new_path_or_lifetime_accepted': False,
        'product_or_prior_packet_mutated': False,
        'compiler_runtime_native_UI_capture_or_process_inventory_executed': False,
        'numeric_caps_or_selected_grammar_changed': False, 'implementation_or_GA_accepted': False}
(HERE / 'seal.json').write_text(json.dumps(seal, indent=2, sort_keys=True) + '\n')
data = (HERE / 'seal.json').read_bytes()
print(json.dumps({'path': str((HERE / 'seal.json').relative_to(ROOT)), 'sha256': hashlib.sha256(data).hexdigest(),
                  'seal_bytes': len(data), 'members': len(members), 'member_bytes': seal['member_bytes']}, indent=2))
