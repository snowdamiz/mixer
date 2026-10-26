#!/usr/bin/env python3
"""Freeze only this independent evidence directory."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
rows = []
for p in sorted(HERE.rglob('*')):
    if p.is_file() and p.name != 'seal.json':
        data = p.read_bytes()
        rows.append({'path':str(p.relative_to(ROOT)), 'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest()})
seal = {'schema':1, 'at':datetime.now(timezone.utc).isoformat(),
        'status':'independent finite receiver correction required; corrected scoped source bound512/514 within640; root selection pending',
        'command':[sys.executable,'-B',str(Path(__file__).resolve())], 'python':sys.version,
        'source_sha256':'0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8',
        'producer_seal_sha256':'c806b2967e37978403641c0172f3d70013b1e74c0d28128236f26fb618812597',
        'owned_scope':['verification/swift-cache-state-g6-complete-independent/**'],
        'members':rows, 'member_count':len(rows), 'member_bytes':sum(row['bytes'] for row in rows),
        'root_addendum_selection_required':True,'implementation_or_whole_lifetime_accepted':False,
        'frozen_packet_mutation':False,'product_compiler_runtime_native_UI_capture_or_process_inventory_executed':False}
(HERE/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
print(json.dumps({'seal_sha256':hashlib.sha256((HERE/'seal.json').read_bytes()).hexdigest(), 'members':len(rows), 'bytes':seal['member_bytes']}))
