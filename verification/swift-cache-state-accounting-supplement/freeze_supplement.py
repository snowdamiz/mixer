#!/usr/bin/env python3
"""Freeze repo-relative proof-only closure without running product/test tools."""
import datetime,hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent;REPO=ROOT.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=ROOT/'seal.json';assert not out.exists(),'immutable supplement cannot be overwritten'
bindings=json.loads((ROOT/'input-bindings.json').read_text())
for path,h in bindings['source'].items():assert sha(REPO/path)==h
for r in bindings['immutable_seals']:
 p=REPO/r['path'];assert sha(p)==r['sha256']
 for m in json.loads(p.read_text())['members']:
  q=REPO/m['path'];assert q.stat().st_size==m['bytes']and sha(q)==m['sha256']
assert not list(ROOT.rglob('*.pyc'))and not list(ROOT.rglob('__pycache__'))
members=[{'path':str(p.relative_to(REPO)),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(ROOT.rglob('*'))if p.is_file()]
seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'frozen source-only G6 blocker and unselected literal repair proposal; independent review pending','member_path_base':'repository-root','command':[sys.executable,str(pathlib.Path(__file__).resolve())],'python':sys.version,'builder_sha256':sha(pathlib.Path(__file__)),'owned_scope':['verification/swift-cache-state-accounting-supplement/**'],'excluded':[str(out.relative_to(REPO))],'members':members,'member_count':len(members),'member_bytes':sum(m['bytes']for m in members),'target_source_sha256':bindings['source'],'lower_bound_qualification':'explicit source-site scalar-block model; not a measured runtime overrun','source_accounting_acceptance':False,'repair_selected':False,'product_or_test_changed_or_executed':False,'native_capture_or_process_inventory':False}
out.write_text(json.dumps(seal,indent=2)+'\n')
for m in members:
 p=REPO/m['path'];assert p.stat().st_size==m['bytes']and sha(p)==m['sha256']
print(json.dumps({'seal':str(out.relative_to(REPO)),'sha256':sha(out),'member_count':len(members),'member_bytes':seal['member_bytes'],'source_accounting_acceptance':False},indent=2))
