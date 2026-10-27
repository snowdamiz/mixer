#!/usr/bin/env python3
"""Frozen accepted source146 preaccess only. Active work packet is never read."""
from pathlib import Path
import hashlib,json,sys,difflib
ROOT=Path(__file__).resolve().parents[3];D=Path(__file__).resolve().parent
V=ROOT/'verification';COMP=V/'swift-guarded-snapshot-host-composition'
IND=V/'swift-guarded-snapshot-host-composition-independent'
DESC=V/'swift-guarded-snapshot-descriptor-rebinding'
BASE=V/'swift-guarded-snapshot-funding-implementation/source/vm'
WORK=V/'swift-guarded-snapshot-loader-work'
checks=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def check(label,yes):
    if not yes:raise AssertionError(label)
    checks.append(label)
for name,expected in [('guarded-snapshot-host-composition-host-acceptance.json','c176aa3802d267d1e5bac6c5c281b1122058d81c4fbc5fa3eff49a05ca404ee8'),('guarded-snapshot-loader-work-host-acceptance.json','e819f93e5219c631255c4322f291539c72b2660f8b7cb593a51cb4beb78742c7')]:
    check('root-acceptance:'+name,sha((V/'swift-semantic-adapter-root-review'/name).read_bytes())==expected)
for p,expected in [(COMP,'2fc002b2598effdc70a74ecfa3da775b4aa82f2572cbbb93650207925238dc2e'),(IND,'c9ccf4649a4dd5c11ac62d403e6443f58dd018562d667f76d16dc422354f3e63')]:
    check('accepted-seal:'+p.name,sha((p/'seal.json').read_bytes())==expected)
    for member in json.loads((p/'seal.json').read_text())['members']:
        b=(p/member['path']).read_bytes();check('frozen-member:'+p.name+':'+member['path'],len(b)==member['bytes'] and sha(b)==member['sha256'])
old=json.loads((DESC/'source-manifest.json').read_text());new=json.loads((COMP/'source-manifest.json').read_text())
A={r['path']:r for r in old['members']};B={r['path']:r for r in new['members']}
check('source145-exact',old['tree_sha256']=='450b6d9b3a05d160e19fa888b68173286b8f6af20ecc7216fdf86283f09b308a' and len(A)==145)
check('source146-exact',new['tree_sha256']=='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185' and len(B)==146)
def bytes145(path):
    p=DESC/'overlay/vm'/path
    return (p if p.exists() else BASE/path).read_bytes()
def bytes146(path):
    p=COMP/'overlay/vm'/path
    return p.read_bytes() if p.exists() else bytes145(path)
for p,row in B.items():
    b=bytes146(p);check('reconstructed146:'+p,len(b)==row['bytes'] and sha(b)==row['sha256'])
added=sorted(B.keys()-A.keys());removed=sorted(A.keys()-B.keys())
changed=sorted(p for p in A.keys()&B.keys() if A[p]['sha256']!=B[p]['sha256'])
loader='src/experimental_swift_reactor/retained_profile_loader_v1.rs'
check('one-new-account-member',added==['src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'] and not removed)
check('exact-three-modified-members',changed==['src/experimental_swift_reactor/cache/initial_profile_v1.rs','src/experimental_swift_reactor/control.rs',loader])
check('loader-count-only',bytes145(loader).replace(b'word(b, 32) != 145',b'word(b, 32) != 146')==bytes146(loader))
check('literal-count-single-site',bytes145(loader).count(b'word(b, 32) != 145')==1)
owners=json.loads((WORK/'source-body-ledger.json').read_text())['nodes']
owner_deltas=[]
for name,row in owners.items():
    s=row['source'];relative=s['path'].split('/source/vm/',1)[-1]
    if relative==s['path']:relative=s['path'].split('/overlay/vm/',1)[-1]
    a=b''.join(bytes145(relative).splitlines(keepends=True)[s['line']-1:s['end_line']]).strip()
    b=b''.join(bytes146(relative).splitlines(keepends=True)[s['line']-1:s['end_line']]).strip()
    check('source-owner-original-fingerprint:'+name,len(a)==s['bytes'] and sha(a)==s['sha256'])
    if a!=b:
        owner_deltas.append(dict(owner=name,path=relative,line=s['line'],end_line=s['end_line'],old_sha256=sha(a),new_sha256=sha(b)))
        check('only-build-body-changes',name=='build' and a.replace(b'word(b, 32) != 145',b'word(b, 32) != 146')==b)
check('all129-body-owners',len(owners)==129 and len(owner_deltas)==1)
X=json.loads((WORK/'mir-extraction.json').read_text())
selected_paths=sorted({r['source_path'] for r in X['functions'].values() if r['source_path']!='compiler-generated-from-source-derive'})
check('sole-selected-changed-file',set(selected_paths)&set(changed)=={loader})
prior_checks=[]
for name,expected in [('preaccess','37aaa40dcfa3cf599d35f3466d12dffc7431c5c53d689ebe7e4f388958834fa2'),('review','28d14ca65eed39ac22b01f562ccc74178f3ee361c2c0a73d16e0da9b122f4be5'),('correction-review','5b15b973477808ff0aeafb00b53006b763d71f5b30d71de5995854aa5193e876')]:
    p=D.parent/name;check('prior-seal-immutable:'+name,sha((p/'seal.json').read_bytes())==expected)
    for member in json.loads((p/'seal.json').read_text())['members']:
        check('prior-member-immutable:'+name+':'+member['path'],sha((p/member['path']).read_bytes())==member['sha256'])
    prior_checks.append(dict(path=str(p.relative_to(ROOT)),seal_sha256=expected))
delta=dict(schema=1,old_tree=old['tree_sha256'],new_tree=new['tree_sha256'],added=added,removed=removed,changed=changed,selected_source_paths=selected_paths,selected_body_owner_count=129,changed_selected_body=owner_deltas,loader_diff='\n'.join(difflib.unified_diff(bytes145(loader).decode().splitlines(),bytes146(loader).decode().splitlines(),fromfile='accepted source145',tofile='accepted source146',n=3)),scope='source facts only; source146 MIR/work rebind is not yet accepted')
(D/'source-diff.json').write_text(json.dumps(delta,indent=2,sort_keys=True)+'\n')
receipt=dict(schema=1,command='python3 verification/swift-guarded-snapshot-loader-work-independent/source146-preaccess/audit.py',python=sys.version,checks_passed=len(checks),source_tree=new['tree_sha256'],prior_packets_unchanged=prior_checks,accepted_composition_members=152,accepted_composition_independent_members=96,source_members=146,host_members=11,selected_owner_changes=['parse_build count145→146'],active_loader_work_source146_read=False,compiler_execution=False,product_execution=False,native_UI_capture='paused and not used',global_process_inventory=False,scope='short exact-source preaccess and pending MIR criteria only',source146_work_quote_accepted=False,operational_grant=False,cleanup='Only owned pure Python process; no compiler/native/runtime child or duplicate source tree created.')
(D/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(checks=len(checks),source_members=146,selected_body_owners=129,selected_body_changes=1,active_source146_read=False,work_quote_accepted=False)))
