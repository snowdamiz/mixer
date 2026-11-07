#!/usr/bin/env python3
"""Freeze this source-only packet. Does not import or execute source snippets."""
import datetime,hashlib,json,pathlib,sys
root=pathlib.Path(__file__).resolve().parent
repo=root.parents[1]
seal=root/'seal.json'
assert not seal.exists(),'never replace a frozen seal'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
bindings=json.loads((root/'input-bindings.json').read_text())
assert digest(root/'build_proof.py')==bindings['builder_sha256']
for old in bindings['baselines_verified']+[bindings['review']]:
 p=repo/old['path'];assert digest(p)==old['sha256']
 j=json.loads(p.read_text())
 for m in j['members']:
  q=repo/m['path'];assert q.stat().st_size==m['bytes']and digest(q)==m['sha256']
members=[]
for p in sorted(root.rglob('*')):
 if p.is_file():
  assert not p.is_symlink() and '__pycache__'not in p.parts
  members.append({'path':str(p.relative_to(repo)),'bytes':p.stat().st_size,'sha256':digest(p)})
j={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'command':[sys.executable,str(pathlib.Path(__file__).resolve())],'python':sys.version,
 'builder_sha256':digest(pathlib.Path(__file__)),
 'status':'frozen source-only rejected per-comparison fragment and separate unselected next option',
 'member_path_base':'repository-root','owned_scope':str(root.relative_to(repo))+'/**',
 'excluded':['seal.json (self)'],'members':members,'member_count':len(members),
 'member_bytes':sum(m['bytes']for m in members),
 'target_source':bindings['target_source'],
 'source_accounting_accepted':False,'lifetime_proof_accepted':False,
 'implementation_selected':False,'runtime_qualification':False,
 'old_packets_unchanged_verified':True,
 'no_product_compiler_native_capture_UI_hosted_or_Git_execution':True}
seal.write_text(json.dumps(j,indent=2)+'\n')
print(json.dumps({'seal':str(seal.relative_to(repo)),'sha256':digest(seal),
 'members':len(members),'bytes':j['member_bytes']},indent=2))
