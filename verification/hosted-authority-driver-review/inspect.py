#!/usr/bin/env python3
"""Independent source and retained-evidence comparisons; no service mutation."""
import pathlib,json,hashlib,subprocess
h=pathlib.Path(__file__).resolve().parent;r=h.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
f=h/'frozen-run';b=f/'inputs/hosted';diff=[];count=0
for p in sorted(b.rglob('*')):
 if p.is_file():
  count+=1;live=r/'hosted'/p.relative_to(b)
  if not live.is_file() or p.read_bytes()!=live.read_bytes():diff.append(str(p.relative_to(b)))
core={n:sha((f/'source/probe/lib'/n).read_bytes()) for n in ['coordinator.ex','transport.ex']}
runs={}
for p in sorted(h.glob('run-*/receipt.json')):
 receipt=json.loads(p.read_text());out=p.parent
 runs[out.name]={'actual_revision':receipt['revision'],'actual_tree':receipt['tree'],'success':receipt['success'],'core_unchanged':{n:sha((out/'source/probe/lib'/n).read_bytes())==digest for n,digest in core.items()},'schema_unchanged':sha((out/'source/schema.sql').read_bytes())==sha((f/'source/schema.sql').read_bytes()),'functions_unchanged':sha((out/'source/functions.sql').read_bytes())==sha((f/'source/functions.sql').read_bytes()),'cleanup':receipt['cleanup']}
print(json.dumps({'review_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip(),'frozen_hosted_files':count,'frozen_hosted_differs_from_current':diff,'core_sha256':core,'runs':runs},indent=2))
