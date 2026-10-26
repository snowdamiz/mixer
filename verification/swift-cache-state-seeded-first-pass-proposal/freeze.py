#!/usr/bin/env python3
"""Seal this failed finite source packet; execute no other packet code."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(b): return hashlib.sha256(b).hexdigest()
def dump(n,v): (HERE/n).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def info(p):
    b=p.read_bytes()
    return {'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':sha(b)}

def main():
    assert not (HERE/'seal.json').exists(), 'No overwrite of a sealed packet'
    build=json.loads((HERE/'build.stdout.txt').read_text())
    verify=json.loads((HERE/'verify.stdout.txt').read_text())
    assert (HERE/'build.stderr.txt').read_bytes()==(HERE/'verify.stderr.txt').read_bytes()==b''
    assert build['totals']['G2']['groups']==verify['G2_necessary_groups']==2660
    assert verify['G2_over_cap']==100 and verify['mathematical_cases']==422
    assert not verify['complete_source_upper_layout_lifetime_implementation_or_GA_accepted']
    bindings=json.loads((HERE/'input-bindings.json').read_text())
    for item in bindings['inputs']: assert info(ROOT/item['path'])==item
    dump('freeze-result.json',{'schema':1,'command':[sys.executable,'-B',str(HERE/'freeze.py')],
        'python':sys.version,'result':'sealed failed source-only G2 necessary-bound proposal',
        'exit_code':0,'failed_tool_or_check_attempts':[],
        'cleanup':'No compiler/runtime/native/capture instance or build directory started; only new owned source packet exists.',
        'compiler_runtime_native_UI_capture_process_inventory_Git_hosted':False})
    members=[info(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='seal.json']
    seal={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'status':'sealed failed source-only seeded first-pass proposal; independent root review pending',
        'command':[sys.executable,'-B',str(HERE/'freeze.py')],'python':sys.version,
        'member_count':len(members),'member_bytes':sum(m['bytes'] for m in members),'members':members,
        'input_tree_digest':bindings['input_tree_digest'],
        'source_revision':'0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8',
        'owned_scope':['verification/swift-cache-state-seeded-first-pass-proposal/**'],
        'necessary_G2_groups':2660,'G2_cap':2560,'G2_over_cap':100,
        'G3_finite_subtrace_groups':2443,'G4_finite_subtrace_groups':543,
        'G2_G3_G4_G5_complete_upper_or_role_ledger_built':False,
        'complete_new_path_layout_lifetime_implementation_or_GA_accepted':False,
        'numeric_caps_or_selected_grammar_changed':False,
        'product_old_packet_or_root_metadata_mutated':False,
        'compiler_Rust_runtime_native_UI_capture_process_inventory_Git_or_hosted':False,
        'failed_tool_or_check_attempts':[]}
    dump('seal.json',seal)
    print(json.dumps({'status':seal['status'],'seal_sha256':sha((HERE/'seal.json').read_bytes()),
        'member_count':seal['member_count'],'member_bytes':seal['member_bytes'],
        'G2_necessary_groups':2660,'G2_over_cap':100},indent=2))

if __name__=='__main__': main()
