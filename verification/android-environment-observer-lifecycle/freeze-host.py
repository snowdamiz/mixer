from pathlib import Path
import ast,hashlib,json
r=Path(__file__).resolve().parents[2]
p=r/'native/android/tests/run-environment-observer-host.py'
vals={}
for n in ast.parse(p.read_text()).body:
    if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('BASE','LEAVES','SELF'):
        vals[n.targets[0].id]=ast.literal_eval(n.value)
paths=['native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java','native/android/tests/NativeEnvironmentV2ObserverHostTests.java',vals['SELF']]+[vals['BASE']+s for s in vals['LEAVES']]
files={s:{'bytes':len((r/s).read_bytes()),'sha256':hashlib.sha256((r/s).read_bytes()).hexdigest()} for s in sorted(paths)}
value={'schema':1,'context_revision':'4e48ac1a3c1593d46c0dcbaf207053ff5e1b6d5d','leaf_count':len(vals['LEAVES']),'scope':'Exact independently authored leaf list frozen before host execution; production Observer compiled directly','files':files}
p=r/'verification/android-environment-observer-lifecycle/host-source-freeze.json';p.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
print(p,hashlib.sha256(p.read_bytes()).hexdigest())
