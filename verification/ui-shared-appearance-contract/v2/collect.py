#!/usr/bin/env python3
"""Seal v2 design artifacts and exact archived sources; no product qualification."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parent.parent

def sha(data): return hashlib.sha256(data).hexdigest()
def record(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)}
def run(argv):
    completed = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, check=False)
    return {'argv': argv, 'cwd': str(ROOT), 'exit_code': completed.returncode,
            'stdout': completed.stdout, 'stderr': completed.stderr}
def require(condition, message):
    if not condition: raise SystemExit(message)

def main():
    old = json.loads((BASE / 'receipt.json').read_text())
    recovery = json.loads((BASE / 'v1/recovery.json').read_text())
    require(sha((BASE/'receipt.json').read_bytes()) == recovery['original_receipt_sha256'], 'original receipt changed')
    for artifact in old['proposal_files']:
        path = ROOT / artifact['path']
        if artifact['path'] == 'docs/ui-shared-appearance-contract.md':
            path = BASE / 'v1/ui-shared-appearance-contract.md'
        require(sha(path.read_bytes()) == artifact['sha256'], 'original artifact changed: '+artifact['path'])
    require(len(recovery['recovered']) == 17 and recovery['missing'] == ['PLAN.md','STATUS.md'], 'historical recovery accounting changed')
    for item in recovery['recovered']:
        require(sha((ROOT/item['snapshot_path']).read_bytes()) == item['sha256'], 'historical input corruption')
    lock = json.loads((HERE / 'input-lock.json').read_text())
    live = []
    for item in lock['inputs']:
        snapshot = HERE / item['snapshot']
        require(len(snapshot.read_bytes()) == item['bytes'] and sha(snapshot.read_bytes()) == item['sha256'], 'v2 snapshot corruption: '+item['path'])
        path = ROOT / item['path']
        live_sha = sha(path.read_bytes()) if path.is_file() else None
        live.append({'path':item['path'], 'captured_sha256':item['sha256'],
                     'live_sha256_observation':live_sha, 'equal_at_collection':live_sha == item['sha256']})
    default = HERE / 'mixer-default-appearance-v1.json'
    require(sha(default.read_bytes()) == 'e94f6988744bde16b83001db8e5047aeac4f15f6b045f99a4660445e7e2062d2', 'candidate default changed')
    commands = [run(['git','rev-parse','HEAD']), run(['git','status','--short']),
        run(['swift','--version']), run([sys.executable,'--version']),
        run([sys.executable,'-B',str(HERE/'validate_descriptor.py')]),
        run([sys.executable,'-B','-m','unittest','discover','-s',str(HERE),'-p','test_*.py','-v']),
        run([sys.executable,'-B','-O','-m','unittest','discover','-s',str(HERE),'-p','test_*.py','-v']),
        run(['swiftc','-swift-version','6','-warnings-as-errors','-typecheck',str(HERE/'AppearanceV1Declarations.swift')])]
    owned = [ROOT/'docs/ui-shared-appearance-contract.md'] + [p for p in sorted(HERE.iterdir()) if p.is_file() and p.name != 'receipt.json']
    primary = record(owned[0])
    passed = all(c['exit_code'] == 0 for c in commands)
    receipt = {'schema':2,'recorded_at':datetime.now(timezone.utc).isoformat(),
        'scope':'design-only closed descriptor shape, concrete declarations, default data and historical source binding',
        'collector_argv':[sys.executable,*sys.argv], 'collector_optimize':sys.flags.optimize,
        'interpreter_sha256':sha(pathlib.Path(sys.executable).read_bytes()),
        'source_head_observation':commands[0]['stdout'].strip(),
        'bounded_archived_source_tree_sha256':sha(json.dumps(lock['inputs'],sort_keys=True,separators=(',',':')).encode()),
        'source_inputs':lock['inputs'], 'live_source_observations':live,
        'live_observation_scope':'Concurrent live edits do not replace archived source bytes or establish runtime/build authority.',
        'original_receipt_sha256':recovery['original_receipt_sha256'],
        'original_primary_sha256':next(x['sha256'] for x in old['proposal_files'] if x['path']=='docs/ui-shared-appearance-contract.md'),
        'original_source_bytes_recovered':17, 'original_hash_bound_only_status_observations':['PLAN.md','STATUS.md'],
        'original_recovery_manifest':record(BASE/'v1/recovery.json'),
        'revised_primary_proposal':primary, 'artifacts':[record(p) for p in owned],
        'commands':commands, 'passed':passed,
        'qualification':'No production Swift/Java codec, resolver, renderer, native capture, build consumption or signed authority was implemented or tested.',
        'pending':['root v2 contract acceptance','production foundation implementation and independent review',
                   'Swift/Java decoded-value and integer-math equivalence','native resource/index capture contract and real packaging',
                   'ordinary/signed native consumption','Apple reference and native four-state screenshots',
                   'physical iOS/Android parity/accessibility','full GA UI inventory','separate immutable published FieldLog','compatibility and GA acceptance'],
        'physical_devices':'disconnected; no discovery, runs or reconnect requests'}
    (HERE/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'passed':passed,'scope':receipt['scope'],'primary_sha256':primary['sha256'],
                      'source_files':len(lock['inputs']),'default_bytes':len(default.read_bytes()),
                      'default_sha256':sha(default.read_bytes()),'receipt':str(HERE/'receipt.json')}))
    if not passed: raise SystemExit(1)

if __name__ == '__main__': main()
