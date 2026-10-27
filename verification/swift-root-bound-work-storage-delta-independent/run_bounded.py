#!/usr/bin/env python3
import sys,subprocess,time,datetime,json,hashlib,platform
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
label=sys.argv[1]
cmd=[sys.executable,'-B',*sys.argv[2:]]
out=HERE/'commands'/label
out.mkdir(parents=True,exist_ok=False)
def ref(p):
 b=Path(p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
started=time.monotonic();at=datetime.datetime.now(datetime.timezone.utc).isoformat()
timed_out=False
with (out/'stdout').open('wb') as stdout,(out/'stderr').open('wb') as stderr:
 try:r=subprocess.run(cmd,cwd=ROOT,stdout=stdout,stderr=stderr,timeout=50,check=False);code=r.returncode
 except subprocess.TimeoutExpired:timed_out=True;code=None
receipt={'schema':1,'at':at,'command':cmd,'cwd':str(ROOT),'python':sys.version,'platform':platform.platform(),'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'tool':ref(sys.executable),'script':ref(ROOT/sys.argv[2]),'wall_bound_seconds':50,'elapsed_seconds':time.monotonic()-started,'exit_code':code,'timed_out':timed_out,'retries':0,'stdout':ref(out/'stdout'),'stderr':ref(out/'stderr'),'scope':'offline Python only; no compiler, native/runtime/UI/capture/network/process inventories'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
raise SystemExit(0 if code==0 else 1)
