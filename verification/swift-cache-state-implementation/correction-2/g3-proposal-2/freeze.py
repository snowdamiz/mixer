#!/usr/bin/env python3
import datetime,hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent;REPO=ROOT.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=ROOT/'seal.json';assert not out.exists()
b=json.loads((ROOT/'input-bindings.json').read_text());assert sha(REPO/b['target']['path'])==b['target']['sha256']
ms=[{'path':str(p.relative_to(REPO)),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(ROOT.rglob('*'))if p.is_file()]
s={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'frozen source-only unselected G3 expression-inlining proposal','member_path_base':'repository-root','command':[sys.executable,str(pathlib.Path(__file__).resolve())],'python':sys.version,'members':ms,'member_count':len(ms),'member_bytes':sum(m['bytes']for m in ms),'excluded':[str(out.relative_to(REPO))],'target_source_sha256':b['target']['sha256'],'product_source_unchanged_during_proposal':True,'proposed_fragment_implemented_or_executed':False,'cost_model_or_bound_accepted':False,'lifetime_proof_accepted':False,'native_capture_or_process_inventory':False}
out.write_text(json.dumps(s,indent=2)+'\n')
for m in ms:
 p=REPO/m['path'];assert p.stat().st_size==m['bytes']and sha(p)==m['sha256']
print(json.dumps({'seal':str(out.relative_to(REPO)),'sha256':sha(out),'members':len(ms),'bytes':s['member_bytes']},indent=2))
