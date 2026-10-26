"""Bounded reviewer-only runner with retained raw output and source identities."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d): p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def main():
 attempt=HERE/'commands'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
 attempt.mkdir(parents=True)
 sources={p.name:sha(p) for p in sorted(HERE.glob('*.py'))}
 commands=[('proof-obligations',[sys.executable,'-B',str(HERE/'write_obligations.py')]),
  ('fixture-encoding',[sys.executable,'-B',str(HERE/'build_fixtures.py')]),
  ('normal',[sys.executable,'-B',str(HERE/'test_controls.py')]),
  ('optimized',[sys.executable,'-B','-O',str(HERE/'test_controls.py')])]
 results=[]
 for name,argv in commands:
  start=time.monotonic(); before=datetime.now(timezone.utc).isoformat()
  try:
   r=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=60,check=False)
   stdout,stderr,code,timed=r.stdout,r.stderr,r.returncode,False
  except subprocess.TimeoutExpired as e:
   stdout,stderr,code,timed=e.stdout or b'',e.stderr or b'',None,True
  if len(stdout)>1048576 or len(stderr)>1048576: raise RuntimeError('owned command exceeded output bound')
  (attempt/(name+'.stdout')).write_bytes(stdout); (attempt/(name+'.stderr')).write_bytes(stderr)
  receipt={'argv':argv,'cwd':str(ROOT),'at':before,'duration_seconds':time.monotonic()-start,
   'timeout_seconds':60,'exit_code':code,'timed_out':timed,'stdout_sha256':hashlib.sha256(stdout).hexdigest(),
   'stderr_sha256':hashlib.sha256(stderr).hexdigest(),'source_sha256':sources,
   'scope':'reviewer raw fixture encoder / finite oracle consistency; zero Rust/product semantic tests',
   'python':sys.version,'platform':platform.platform(),'machine':platform.machine()}
  write(attempt/(name+'.json'),receipt); results.append({'name':name,'exit_code':code,'timed_out':timed})
  print(name,code,stdout.decode()[-500:],stderr.decode()[-500:])
  if code!=0:
   write(attempt/'summary.json',{'results':results,'status':'failed-preserved','Rust_product_tests':0}); return 1
 write(attempt/'summary.json',{'results':results,'status':'reviewer-controls-passed','Rust_product_tests':0})
 write(HERE/'latest-controls.json',{'attempt':str(attempt.relative_to(HERE)),'results':results,'source_sha256':sources,
  'Rust_product_tests':0,'candidate_accessed':False})
 return 0
if __name__=='__main__': raise SystemExit(main())
