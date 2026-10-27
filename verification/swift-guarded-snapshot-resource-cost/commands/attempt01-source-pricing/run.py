"""Bounded pure-Python child; retain failed attempts and exact tool/source data."""
import datetime,hashlib,json,os,signal,subprocess,sys,time,shutil
from pathlib import Path
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent;R=D.parents[1]
name=sys.argv[1];script=sys.argv[2];extra=sys.argv[3:]
assert name.replace('-','').isalnum() and script in ('derive.py','controls.py')
A=D/'commands'/name;A.mkdir(parents=True,exist_ok=False)
for f in ('run.py',script,'model.py'):shutil.copy2(D/f,A/f)
argv=[sys.executable,'-B',str(D/script)]+extra
env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0'}
started=datetime.datetime.now(datetime.timezone.utc).isoformat();then=time.monotonic()
p=subprocess.Popen(argv,cwd=R,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
timed_out=False
try:out,err=p.communicate(timeout=50)
except subprocess.TimeoutExpired:
    timed_out=True;os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate()
try:os.killpg(p.pid,0);absent=False
except ProcessLookupError:absent=True
(A/'stdout').write_bytes(out);(A/'stderr').write_bytes(err)
def sha(raw):return hashlib.sha256(raw).hexdigest()
receipt={'schema':1,'at':started,'argv':argv,'cwd':str(R),'environment':env,
    'python_version':sys.version,'python_executable_sha256':sha(Path(sys.executable).read_bytes()),
    'source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
    'script_sha256':sha((D/script).read_bytes()),'model_sha256':sha((D/'model.py').read_bytes()),
    'exit_code':p.returncode,'timed_out':timed_out,'elapsed_seconds':time.monotonic()-then,
    'direct_child_pid':p.pid,'direct_child_waited':True,'owned_group_absent':absent,
    'compiler_or_product_executed':False,'native_UI_capture_started':False,'global_process_inventory':False,
    'outputs':{k:{'bytes':len(v),'sha256':sha(v)} for k,v in [('stdout',out),('stderr',err)]}}
(A/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps(receipt,sort_keys=True));print(out.decode());print(err.decode(),file=sys.stderr)
assert absent and not timed_out
sys.exit(p.returncode)
