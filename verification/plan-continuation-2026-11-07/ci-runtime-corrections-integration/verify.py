import importlib.util,json,os,sys,time,hashlib
from pathlib import Path
ROOT=Path("/Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4")
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
CTL=BASE/'native-custody-premise/cleanup_control.py'
if hashlib.sha256(CTL.read_bytes()).hexdigest()!='8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df':raise RuntimeError('controller drift')
s=importlib.util.spec_from_file_location('c',CTL);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
out=HERE/'commands';out.mkdir();scratch=HERE/'scratch';scratch.mkdir()
c=m.Commands(out,dict(os.environ,PYTHONDONTWRITEBYTECODE='1',GIT_TERMINAL_PROMPT='0'),deadline=time.monotonic()+180)
r={'status':'pending','scope':'Installed source/job preflights only; no compiler/native qualification'}
try:
 for label,relative in [('envelope','envelope-output-ownership-fix-r2'),('cache','cache-custody-fix-r3')]:
  script=BASE/relative/('adopt_envelope.py' if label=='envelope' else 'adopt_fixture.py')
  r[label]=json.loads(c.run(label,[sys.executable,'-B',script,'verify','--workflow-installed'],ROOT,60))
 c.run('whitespace',['git','diff','--check'],ROOT,30)
 sp=importlib.util.spec_from_file_location('inventory',ROOT/'scripts/ci/check-android-generated-java.py');i=importlib.util.module_from_spec(sp);sys.modules[sp.name]=i;sp.loader.exec_module(i)
 inputs=i.source_inputs(i.load_profile());r['sourceCount']=len(inputs);r['sourceDigest']=i.source_digest(inputs)
 if r['sourceCount']!=103 or r['sourceDigest']!='eda43c6bb96bfeb15ab31731858c7388a7ba52329c8ba8e48ed52505bfe86158':raise RuntimeError('source103 drift')
 r['status']='passed'
except BaseException as e:r['status']='failed';r['error']=repr(e)
finally:
 r['cleanup']=c.cleanup(scratch);r['commands']=c.records
 if c.hold or c.limit or not r['cleanup']['allTerminalCustody']:r['status']='failed'
 (HERE/'verification.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps({k:v for k,v in r.items() if k not in ('commands','envelope','cache')},indent=2))
sys.exit(0 if r['status']=='passed' else 1)
