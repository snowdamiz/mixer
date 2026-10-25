#!/usr/bin/env python3
"""Copy the selected VM closure, never execute any prior preparation or target."""
from pathlib import Path
import datetime, hashlib, json, subprocess
HERE=Path(__file__).resolve().parent; ROOT=HERE.parent.parent

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value): (HERE/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
paths=[ROOT/'vm/Cargo.toml',ROOT/'vm/Cargo.lock']
paths += [p for top in ('include','src','tests') for p in (ROOT/'vm'/top).rglob('*') if p.is_file()]
manifest={str(p.relative_to(ROOT/'vm')):sha(p) for p in sorted(paths)}
closure=hashlib.sha256((json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()).hexdigest()
assert len(manifest)==132 and closure=='b28da766c84b6353a4511e2fc3fbcb0d4302d5b8a5a74da1ee3d7fb776ca2c11'
assert not (HERE/'source').exists() and not (HERE/'baseline').exists()
for name in manifest:
    for copy in ('baseline','source'):
        dest=HERE/copy/name; dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/'vm'/name).read_bytes())
save('baseline-manifest.json',manifest)
save('preparation.json',{'schema':1,'sourceRevision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'sourceClosure':closure,'sourceMembers':len(manifest),'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'selection':'Root selected fixed128-head64-link192-byte private Swift resident index through collaboration before implementation','scope':'finite host tests only; no full target/native/device/publication','dependenciesAdded':False,'priorPreparationScriptsExecuted':False})
print(json.dumps({'copiedMembers':len(manifest),'sourceClosure':closure}))
