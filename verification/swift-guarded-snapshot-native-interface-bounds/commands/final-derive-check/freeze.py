"""Freeze or verify this packet, preserving every failed pure-host attempt."""
import hashlib,json,sys,datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(j):return json.dumps(j,sort_keys=True,separators=(',',':')).encode()
def roster():
    rows=[]
    for p in sorted(HERE.rglob('*')):
        if p.is_file() and p.name!='seal.json':
            assert not p.is_symlink() and '__pycache__' not in p.parts
            d=p.read_bytes();rows.append({'path':str(p.relative_to(HERE)),'bytes':len(d),'sha256':sha(d)})
    return rows
def main():
    check='--check-only' in sys.argv
    if not check:
        assert not (HERE/'seal.json').exists()
        attempts=[]
        for p in sorted((HERE/'commands').glob('*/receipt.json')):
            r=json.loads(p.read_text());assert r['waited'] and r['owned_process_group_absent']
            attempts.append({'path':str(p.parent.relative_to(HERE)),'exit_code':r['exit_code'],'elapsed_seconds':r['elapsed_seconds']})
        (HERE/'attempt-history.json').write_text(json.dumps({'schema':1,'attempts':attempts,
          'failures_preserved':sum(r['exit_code']!=0 for r in attempts)},indent=2,sort_keys=True)+'\n')
        (HERE/'cleanup.json').write_text(json.dumps({'schema':1,'all_owned_children_waited':True,'owned_process_groups_absent':True,
          'other_projects_processes_touched':False,'compiler_product_native_UI_capture_started':False,'global_process_inventory':False,
          'installed_toolchain_mutations':False,'native_runtime':'paused'},indent=2,sort_keys=True)+'\n')
        (HERE/'freeze-command.json').write_text(json.dumps({'schema':1,'argv':[sys.executable,'-B',str(HERE/'freeze.py')],
          'python':sys.version,'source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
          'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'output':'seal.json','pure_host_only':True},indent=2,sort_keys=True)+'\n')
        rows=roster();seal={'schema':1,'status':'frozen-source-native-interface-candidate-pending-independent-review-selection-and-binary-correspondence',
          'member_count':len(rows),'member_bytes':sum(r['bytes'] for r in rows),'members':rows,'tree_sha256':sha(canonical(rows)),
          'source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
          'whole_host_grant':False,'native_runtime':'paused','GA_verified':False}
        (HERE/'seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
    else:
        seal=json.loads((HERE/'seal.json').read_text());rows=roster()
        assert rows==seal['members'] and len(rows)==seal['member_count']
        assert sum(r['bytes'] for r in rows)==seal['member_bytes'] and sha(canonical(rows))==seal['tree_sha256']
    print(json.dumps({'status':'verified' if check else 'sealed','member_count':seal['member_count'],'member_bytes':seal['member_bytes'],
      'seal_sha256':sha((HERE/'seal.json').read_bytes())},sort_keys=True))
if __name__=='__main__':main()
