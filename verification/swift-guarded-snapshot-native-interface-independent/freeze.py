"""Freeze/verify only this independent source review, without execution grants."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
def sha(d):return hashlib.sha256(d).hexdigest()
def enc(j):return (json.dumps(j,indent=2,sort_keys=True)+'\n').encode()
def roster():
    out=[]
    for p in sorted(HERE.rglob('*')):
        if p.is_file() and p.name!='seal.json':
            assert not p.is_symlink() and '__pycache__' not in p.parts
            d=p.read_bytes();out.append({'path':str(p.relative_to(HERE)),'bytes':len(d),'sha256':sha(d)})
    return out
check='--check-only' in sys.argv
if not check:
    assert not (HERE/'seal.json').exists()
    attempts=[]
    for p in sorted((HERE/'commands').glob('attempt*/receipt.json')):
        r=json.loads(p.read_text())
        assert r['waited'] and r['owned_process_group_absent']
        attempts.append({'path':str(p.parent.relative_to(HERE)),'exit_code':r['exit_code'],'receipt_sha256':sha(p.read_bytes())})
    failure_log={'schema':1,'validation_attempts':attempts,'checker_failures_preserved':sum(r['exit_code']!=0 for r in attempts),
        'failure_causes':['attempt01: frozen Path sorting differs from sorted relative string ordering; identical member sets',
            'attempt02: inherited declaration hashes intentionally elide comments; full raw source separately hashed',
            'attempt03: accepted graph disambiguates Span/Resource as MetaSpan/WasiSpan/ValidatorResource'],
        'non_validation_exploration_failures':[
            {'command':'rg -n loader_inline|validator_inline|caller_inline|Error|uniform|temporary|requested verification/swift-guarded-snapshot-host-storage-composition/{model.py,derive.py,README.md,contract.json} verification/swift-guarded-snapshot-native-interface-bounds/test_interfaces.py','exit_code':2,'output':'rg: verification/swift-guarded-snapshot-host-storage-composition/contract.json: No such file or directory (os error 2); other requested files returned matches','effect':'read-only nonexistent-file exploratory query; no validation pass claimed'},
            {'command':"rg -n -C 2 MetaSpan verification/swift-guarded-snapshot-funding-implementation/source/vm/src/experimental/metadata.rs",'exit_code':1,'output':'','effect':'accepted graph alias is source Span; reviewed exact mapping and corrected independent checker'}],
        'candidate_failures_preserved':4,'immutable_inputs_changed':False}
    (HERE/'attempt-history.json').write_bytes(enc(failure_log))
    (HERE/'cleanup.json').write_bytes(enc({'schema':1,'all_owned_children_waited':True,'all_owned_process_groups_absent':True,'no_other_projects_processes_touched':True,'compiler_product_fixture_native_UI_capture_started':False,'simulator_emulator_started':False,'global_process_inventory':False,'live_source_Git_toolchain_mutations':False,'other_active_lane_read':False,'native_runtime':'paused'}))
    (HERE/'freeze-command.json').write_bytes(enc({'schema':1,'argv':[sys.executable,'-B',str(HERE/'freeze.py')],'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python_version':sys.version,'source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185','scope':'freeze independent offline review only; no policy amendment selection or execution grant','output':'seal.json'}))
    rows=roster()
    seal={'schema':1,'status':'frozen-independent-source-interface-review-conditional-amendment-proposed-not-selected','source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185','candidate_seal_sha256':'d02b6602bc7c4419d908db90a8e67d24b1dd3a46f9c9d2c2bb9158c70229b60f','member_count':len(rows),'member_bytes':sum(r['bytes'] for r in rows),'members':rows,'tree_sha256':sha(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()),'root_amendment_selected':False,'whole_root_quote_policy_grant':False,'native_runtime':'paused','GA_verified':False}
    (HERE/'seal.json').write_bytes(enc(seal))
else:
    seal=json.loads((HERE/'seal.json').read_text());rows=roster()
    assert rows==seal['members'] and len(rows)==seal['member_count']
    assert sum(r['bytes'] for r in rows)==seal['member_bytes']
    assert sha(json.dumps(rows,sort_keys=True,separators=(',',':')).encode())==seal['tree_sha256']
print(json.dumps({'status':'verified' if check else 'frozen','members':seal['member_count'],'bytes':seal['member_bytes'],'seal_sha256':sha((HERE/'seal.json').read_bytes()),'native_runtime':'paused','root_amendment_selected':False},sort_keys=True))
