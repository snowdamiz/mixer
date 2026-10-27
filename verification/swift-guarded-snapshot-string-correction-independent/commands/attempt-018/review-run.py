#!/usr/bin/env python3
"""Owned bounded Python-only recorder. Never dispatches frozen writers."""
import datetime,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent; R=D.parents[1]; V=R/'verification'
C=V/'swift-guarded-snapshot-string-provenance-correction'
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,j):p.write_text(json.dumps(j,indent=2,sort_keys=True)+'\n')
def inventory(p):
 return {str(x.relative_to(p)):{'bytes':x.stat().st_size,'sha256':sha(x.read_bytes())} for x in sorted(p.rglob('*')) if x.is_file()}
def main():
 if (D/'seal.json').exists():raise SystemExit('frozen review: recorder disabled')
 target=(R/sys.argv[1]).resolve(); args=sys.argv[2:]
 allowed=(target.parent==D and target.name in ('custody.py','audit.py','adverse.py','report.py','check.py')) or (target.parent==C and (target.name,args) in [('test_provenance.py',[]),('test_correction.py',[]),('prepare_contracts.py',['--check']),('derive.py',['--check']),('check.py',[]),('custody.py',['--check'])])
 if not allowed:raise SystemExit('not an authorized read-only target')
 attempts=D/'commands';attempts.mkdir(exist_ok=True)
 n=1
 while (attempts/f'attempt-{n:03d}').exists():n+=1
 out=attempts/f'attempt-{n:03d}';out.mkdir()
 for f in sorted(D.glob('*.py')):(out/('review-'+f.name)).write_bytes(f.read_bytes())
 if target.parent==C:
  for f in sorted(C.glob('*.py')):(out/('target-'+f.name)).write_bytes(f.read_bytes())
 packets=[C,V/'swift-guarded-snapshot-string-provenance-independent',V/'swift-guarded-snapshot-string-provenance']
 before={p.name:inventory(p) for p in packets};cmd=[sys.executable,'-B',str(target),*args]
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');start=time.monotonic();at=datetime.datetime.now(datetime.timezone.utc).isoformat()
 child=subprocess.Popen(cmd,cwd=R,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 timeout=False
 try:stdout,stderr=child.communicate(timeout=55)
 except subprocess.TimeoutExpired:
  timeout=True;os.killpg(child.pid,signal.SIGKILL);stdout,stderr=child.communicate(timeout=3)
 (out/'stdout').write_bytes(stdout);(out/'stderr').write_bytes(stderr)
 after={p.name:inventory(p) for p in packets}
 receipt={'schema':1,'at':at,'argv':cmd,'cwd':str(R),'seconds':time.monotonic()-start,'exit_code':child.returncode,'timed_out':timeout,'owned_child_pid':child.pid,'owned_child_waited':child.poll() is not None,'owned_group_cleanup':'owned group killed and child waited' if timeout else 'child completed and waited; no other children started', 'python':sys.version,'python_executable':sys.executable,'python_executable_sha256':sha(Path(sys.executable).resolve().read_bytes()),'source_revision':'frozen-source146-exacttree-690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185','host_tree_sha256':'027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2','frozen_packets_unchanged':before==after,'frozen_inventory_before':before,'frozen_inventory_after':after,'stdout_sha256':sha(stdout),'stderr_sha256':sha(stderr),'scope':'pure host offline Python; no compiler/runtime/native/UI/capture/Git/global process inventory'}
 write(out/'receipt.json',receipt)
 print(json.dumps({'attempt':out.name,'exit_code':child.returncode,'seconds':receipt['seconds'],'frozen_packets_unchanged':before==after,'owned_child_waited':receipt['owned_child_waited']}));sys.stdout.buffer.write(stdout);sys.stderr.buffer.write(stderr)
 if before!=after:raise SystemExit('frozen packet changed')
 raise SystemExit(child.returncode)
if __name__=='__main__':main()
