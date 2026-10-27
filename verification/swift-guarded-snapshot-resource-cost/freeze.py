"""Freeze this candidate once, or verify every member without mutation."""
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':')).encode()
def roster():
    result=[]
    for p in sorted(D.rglob('*')):
        if p.is_file() and p.name!='seal.json':
            assert not p.is_symlink();raw=p.read_bytes()
            result.append({'path':str(p.relative_to(D)),'bytes':len(raw),'sha256':sha(raw)})
    return result
if '--check-only' not in sys.argv:
    assert not (D/'seal.json').exists()
    attempts=[]
    for p in sorted((D/'commands').glob('*/receipt.json')):
        r=json.loads(p.read_text());assert r['direct_child_waited'] and r['owned_group_absent'] and not r['timed_out']
        attempts.append({'path':str(p.parent.relative_to(D)),'exit_code':r['exit_code'],
                         'script_sha256':r['script_sha256'],'elapsed_seconds':r['elapsed_seconds']})
    (D/'attempt-history.json').write_text(json.dumps({'schema':1,'attempts':attempts,
        'checker_failures_retained':sum(r['exit_code']!=0 for r in attempts),
        'frozen_source_input_or_product_mutations':0},indent=2,sort_keys=True)+'\n')
    (D/'cleanup.json').write_text(json.dumps({'schema':1,'all_direct_python_children_waited':True,
        'owned_child_process_groups_absent':True,'compiler_product_native_UI_capture_started':False,
        'global_process_inventory':False,'native_runtime':'paused','owned_runtime_scratch_created':0,
        'other_projects_processes_or_data_touched':False},indent=2,sort_keys=True)+'\n')
    (D/'freeze-command.json').write_text(json.dumps({'schema':1,'argv':['python3','-B',str(D/'freeze.py')],
        'cwd':str(D.parents[1]),'python_version':sys.version,'script_sha256':sha(Path(__file__).read_bytes()),
        'source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
        'compiler_product_runtime_executed':False,'output':'seal.json'},indent=2,sort_keys=True)+'\n')
    members=roster();seal={'schema':1,'status':'frozen-source-resource-interface-candidate-pending-independent-review-and-compiled-stdlib-correspondence',
        'members':members,'member_count':len(members),'member_bytes':sum(m['bytes'] for m in members),'tree_sha256':sha(canonical(members)),
        'whole_host_quote_or_grant':False,'native_runtime':'paused','healthy_cleanup_OTA_GA':False}
    (D/'seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
else:
    seal=json.loads((D/'seal.json').read_text());members=roster()
    assert members==seal['members'] and len(members)==seal['member_count']
    assert sum(m['bytes'] for m in members)==seal['member_bytes'] and sha(canonical(members))==seal['tree_sha256']
print(json.dumps({'status':'verified' if '--check-only' in sys.argv else 'sealed','members':seal['member_count'],
    'bytes':seal['member_bytes'],'seal_sha256':sha((D/'seal.json').read_bytes())},sort_keys=True))
