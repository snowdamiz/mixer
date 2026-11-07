from pathlib import Path
import hashlib,json,os,shutil,signal,subprocess,sys,time
D=Path(__file__).resolve().parent
R=D/'replay-copy'
assert not R.exists()
shutil.copytree(D/'input',R)
commands=[]
def identity(p):
 b=Path(p).read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(): (D/'supplied-controls-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
def run(label,argv,timeout):
 start=time.monotonic();out=D/(label+'.stdout');err=D/(label+'.stderr')
 with out.open('wb') as stdout,err.open('wb') as stderr:
  p=subprocess.Popen([str(x) for x in argv],cwd=R,env={'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8','LC_ALL':'en_US.UTF-8','TZ':'UTC'},stdout=stdout,stderr=stderr,start_new_session=True)
  timed=False
  try:p.wait(timeout=timeout)
  except subprocess.TimeoutExpired:timed=True;os.killpg(p.pid,signal.SIGKILL);p.wait()
  except BaseException:os.killpg(p.pid,signal.SIGKILL);p.wait();raise
 record={'label':label,'argv':[str(x) for x in argv],'cwd':str(R),'timeout_seconds':timeout,'elapsed_seconds':time.monotonic()-start,'exit':p.returncode,'timed_out':timed,'reaped':True,'stdout':identity(out),'stderr':identity(err)};commands.append(record);save();print(label,p.returncode,flush=True)
 assert not timed and p.returncode==0,record
run('python-context',[sys.executable,'-I','-B','-S','-c','import sys,json;print(json.dumps({"version":sys.version,"executable":sys.executable,"base_executable":sys._base_executable,"prefix":sys.prefix,"base_prefix":sys.base_prefix,"exec_prefix":sys.exec_prefix,"base_exec_prefix":sys.base_exec_prefix,"sys_path":sys.path,"flags":str(sys.flags)},indent=2))'],60)
run('bootstrap-integrity-controls',[sys.executable,'-I','-B','-S',R/'test_bootstrap_integrity.py'],1200)
run('python-admission-controls',[sys.executable,'-I','-B','-S',R/'test_python_admission.py'],900)
(D/'supplied-controls-result.json').write_text(json.dumps({'status':'passed-supplied-controls-independent-owned-copy','commands':len(commands),'bootstrap_controls':json.loads((R/'integrity-controls-4/controls.json').read_bytes()),'admission_controls':json.loads((R/'python-admission-controls-4/controls.json').read_bytes()),'all_children_reaped':True,'input_untouched':True,'product_authority':False},indent=2)+'\n')
