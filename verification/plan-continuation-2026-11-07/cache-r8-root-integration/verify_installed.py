import hashlib,importlib.util,json,os,sys,time
from pathlib import Path
ROOT=Path("/Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4")
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
CTL=BASE/'native-custody-premise/cleanup_control.py'
def need(value,message):
 if not value:raise RuntimeError(message)
def identity(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
need(identity(CTL)['sha256']=='8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df','custody drift')
prep=json.loads((HERE/'preparation.json').read_bytes())
need(identity(ROOT/'.github/workflows/verify.yml')=={'bytes':len((HERE/'verify.proposed.yml').read_bytes()),'sha256':prep['workflowProposalSHA256']},'exact installed proposal required')
need(identity(BASE/'cache-refusal-cleanup-r8/sources.json')['sha256']=='19af15d0fcb485957e2cb459c2a654e07f34f71ee52163f01a5336b17b09ec9b','R8 source seal')
compile((BASE/'cache-r8-delivery/deliver.py').read_bytes(),str(BASE/'cache-r8-delivery/deliver.py'),'exec')
spec=importlib.util.spec_from_file_location('custody',CTL);custody=importlib.util.module_from_spec(spec);spec.loader.exec_module(custody)
out=HERE/'installed-commands';out.mkdir(exist_ok=False)
scratch=HERE/'installed-scratch';scratch.mkdir(exist_ok=False)
c=custody.Commands(out,dict(os.environ,PYTHONDONTWRITEBYTECODE='1',GIT_TERMINAL_PROMPT='0'),deadline=time.monotonic()+150)
r={'status':'pending','scope':'Exact installed R7 cache workflow and source103; no compiler/native/hosted qualification'}
try:
 r['cache']=json.loads(c.run('cache-installed',[sys.executable,'-B',str(BASE/'cache-refusal-cleanup-r8/adopt_fixture.py'),'verify','--workflow-installed'],ROOT,60))
 r['envelope']=json.loads(c.run('envelope-installed',[sys.executable,'-B',str(BASE/'envelope-output-ownership-fix-r2/adopt_envelope.py'),'verify','--workflow-installed'],ROOT,60))
 c.run('whitespace',['git','diff','--check'],ROOT,30)
 s=importlib.util.spec_from_file_location('inventory',ROOT/'scripts/ci/check-android-generated-java.py');i=importlib.util.module_from_spec(s);sys.modules[s.name]=i;s.loader.exec_module(i)
 inputs=i.source_inputs(i.load_profile());r['sourceCount']=len(inputs);r['sourceDigest']=i.source_digest(inputs)
 need(r['sourceCount']==103 and r['sourceDigest']=='eda43c6bb96bfeb15ab31731858c7388a7ba52329c8ba8e48ed52505bfe86158','source103 drift')
 need(identity(ROOT/'.github/workflows/verify.yml')=={'bytes':len((HERE/'verify.proposed.yml').read_bytes()),'sha256':prep['workflowProposalSHA256']},'installed workflow postflight drift')
 r['status']='passed'
except BaseException as e:r.update(status='failed',error=repr(e))
finally:
 r['cleanup']=c.cleanup(scratch);r['commands']=c.records
 if c.hold or c.limit or not r['cleanup']['allTerminalCustody']:r['status']='failed'
 (HERE/'installed-verification.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps({k:v for k,v in r.items() if k not in ['commands','cache','envelope']}))
raise SystemExit(0 if r['status']=='passed' else 1)
