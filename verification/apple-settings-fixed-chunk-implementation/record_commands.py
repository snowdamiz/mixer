"""Bounded host command runner; retain failed outputs and reap owned children."""
import datetime,hashlib,json,os,pathlib,subprocess,sys,time
B=pathlib.Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def main():
 entries=[]
 commands=[([sys.executable,'--version'],'python-version',10),([sys.executable,str(B/'prepare.py')],'prepare',15),([sys.executable,str(B/'derive_tests.py')],'derive-tests',10),([sys.executable,str(B/'run_controls.py')],'controls',55),([sys.executable,str(B/'run_host.py')],'host',70)]
 directory=B/'commands';directory.mkdir(exist_ok=True)
 for argv,name,timeout in commands:
  begin=time.monotonic();env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
  p=subprocess.Popen(argv,cwd=B,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
  try:out,err=p.communicate(timeout=timeout)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,15)
   try:out,err=p.communicate(timeout=3)
   except subprocess.TimeoutExpired:os.killpg(p.pid,9);out,err=p.communicate(timeout=3)
  (directory/(name+'.stdout')).write_bytes(out);(directory/(name+'.stderr')).write_bytes(err)
  entries.append(dict(argv=argv,pid=p.pid,processGroup=p.pid,sourceRevisionLabel='ee390cbf56ba388a21c7d28c884dbed5fd7282fe',sourceBindingsSHA256=sha((B/'source-bindings.json').read_bytes()),exitCode=p.returncode,elapsedSeconds=time.monotonic()-begin,stdoutEOF=True,stderrEOF=True,ownedChildReaped=p.poll() is not None,stdoutSHA256=sha(out),stderrSHA256=sha(err)))
  (B/'command-receipt.json').write_text(json.dumps(dict(schema=1,python=sys.version,runnerSHA256=sha(pathlib.Path(__file__).read_bytes()),observedUTC=datetime.datetime.now(datetime.UTC).isoformat(),commands=entries,scope='host-only bounded controls; no listener, native/simulator/emulator/phone/UI/screenshot, build-for-testing, full-runtime or Git operation'),indent=2)+'\n')
  print(json.dumps(dict(command=name,exitCode=p.returncode,elapsedSeconds=entries[-1]['elapsedSeconds'])),flush=True)
  if p.returncode:raise SystemExit(p.returncode)
if __name__=='__main__':main()
