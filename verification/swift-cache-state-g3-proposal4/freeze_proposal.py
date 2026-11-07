#!/usr/bin/env python3
"""Freeze only this source-only packet, never overwrite its seal."""
import datetime,hashlib,json,pathlib,sys
root=pathlib.Path(__file__).resolve().parent;repo=root.parents[1]
seal=root/'seal.json';assert not seal.exists()
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
b=json.loads((root/'custody.json').read_text())
assert digest(root/'build_proof.py')==b['builder_sha256']
assert digest(repo/b['target_source']['path'])==b['target_source']['sha256']
for old in b['verified_old_packets']:
 p=repo/old['path'];assert digest(p)==old['sha256']
 for m in json.loads(p.read_text())['members']:
  q=repo/m['path'];assert q.stat().st_size==m['bytes']and digest(q)==m['sha256']
members=[]
for p in sorted(root.rglob('*')):
 if p.is_file():
  assert not p.is_symlink()and '__pycache__'not in p.parts
  members.append({'path':str(p.relative_to(repo)),'bytes':p.stat().st_size,'sha256':digest(p)})
j={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'command':[sys.executable,str(pathlib.Path(__file__).resolve())],'python':sys.version,
 'builder_sha256':digest(pathlib.Path(__file__)),
 'status':'frozen source-only whole-sort-view exploration stopped at qualified G4 obstacle',
 'member_path_base':'repository-root','owned_scope':str(root.relative_to(repo))+'/**',
 'excluded':['seal.json (self)'],'members':members,'member_count':len(members),
 'member_bytes':sum(m['bytes']for m in members),'target_source':b['target_source'],
 'explored_source':b['explored_source'],'source_accounting_accepted':False,
 'lifetime_proof_accepted':False,'product_implementation_selected':False,
 'runtime_qualification':False,'old_packets_unchanged_verified':True,
 'native_UI_capture_process_inventory_hosted_Git_mutation':False}
seal.write_text(json.dumps(j,indent=2)+'\n')
print(json.dumps({'seal':str(seal.relative_to(repo)),'sha256':digest(seal),
 'members':len(members),'bytes':j['member_bytes']},indent=2))
