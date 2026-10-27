#!/usr/bin/env python3
"""Bounded dispatch of owned read-only review validators, with exact raw output."""
from pathlib import Path
import hashlib,json,os,platform,signal,subprocess,sys,time
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent
def identity(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def main():
 commands=[]
 for name in ('review_packet','review_recovery'):
  script=D/(name+'.py');out=D/(name+'.stdout');err=D/(name+'.stderr');argv=[sys.executable,'-B',str(script)];started=time.monotonic();timed_out=False
  with out.open('wb') as stdout,err.open('wb') as stderr:
   child=subprocess.Popen(argv,cwd=D,stdout=stdout,stderr=stderr,start_new_session=True)
   try:child.wait(timeout=60)
   except subprocess.TimeoutExpired:timed_out=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
   except BaseException:os.killpg(child.pid,signal.SIGKILL);child.wait();raise
  row={'argv':argv,'cwd':str(D),'script':identity(script),'exit':child.returncode,'timeout':timed_out,'reaped':True,'elapsed_seconds':time.monotonic()-started,'stdout':{'path':out.name,**identity(out)},'stderr':{'path':err.name,**identity(err)}};commands.append(row)
  (D/'review-commands.json').write_text(json.dumps({'schema':1,'commands':commands,'maximum_concurrent_children':1,'deadline_seconds_per_child':60,'python':sys.version,'python_executable':{'path':sys.executable,**identity(Path(sys.executable))},'platform':platform.platform(),'runner':identity(Path(__file__))},indent=2)+'\n')
  print(name,child.returncode,flush=True);assert child.returncode==0 and not timed_out
if __name__=='__main__':main()
