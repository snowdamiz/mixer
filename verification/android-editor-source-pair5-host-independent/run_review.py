#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,json,os,shutil,signal,subprocess,sys,time
O=Path(__file__).resolve().parent;R=O.parents[1];P=R/'verification/android-editor-source-pair5-host-integration';C=O/'candidate'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
if not C.exists():shutil.copytree(P/'candidate',C)
expected=json.loads((P/'final-candidate-bindings.json').read_text());actual={str(p.relative_to(C)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(C.rglob('*')) if p.is_file()}
assert set(actual)==set(expected) and all(all(expected[n].get(k)==v for k,v in x.items()) for n,x in actual.items())
save(O/'copied-source-map.json',actual)
commands=[];env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
for label,flags,expected_exit in [('A',['--closure','A'],0),('B-default',['--closure','B'],1),('B',['--closure','B','--skip-matrix','--preservation'],0)]:
 evidence=O/'runs'/label;evidence.parent.mkdir(exist_ok=True)
 argv=[sys.executable,str(C/'native/android/tests/run-private-owner-host.py'),'--evidence',str(evidence),*flags]
 start=time.monotonic();stdout=O/(label+'.stdout');stderr=O/(label+'.stderr')
 with stdout.open('wb') as out,stderr.open('wb') as err:
  p=subprocess.Popen(argv,cwd=R,env=env,stdout=out,stderr=err,start_new_session=True)
  try:code=p.wait(timeout=300)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);code=p.wait()
 commands.append({'argv':argv,'label':label,'exit':code,'expected_exit':expected_exit,'passed':code==expected_exit,'elapsed_seconds':time.monotonic()-start,'stdout_sha256':sha(stdout),'stderr_sha256':sha(stderr),'reaped':True})
 save(O/'review-commands.json',commands);print(label,code,'expected',expected_exit,flush=True)
 if code!=expected_exit:raise SystemExit(1)
assert all(sha(C/n)==x['sha256'] for n,x in actual.items())
print('PASS fresh independent exact-copy A/B/default controls',flush=True)
