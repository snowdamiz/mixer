import hashlib,importlib.util,json,os,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CTL=HERE.parent/'native-custody-premise/cleanup_control.py'
PYTHON='/opt/homebrew/opt/python@3.14/bin/python3.14'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
mode=sys.argv[1]
if mode not in ['normal','optimized']:raise RuntimeError('Two fixed modes only')
if (HERE/'HOLD.json').exists():raise RuntimeError('Sticky hold')
if sha(CTL)!='8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df':raise RuntimeError('Controller drift')
if Path(sys.executable).resolve()!=Path(PYTHON).resolve():raise RuntimeError('Python drift')
prior_bytes=0
if mode=='optimized':
 prior=json.loads((HERE/'normal-supervisor/result.json').read_bytes())
 if not prior['cleanup']['allTerminalCustody'] or prior['testExit']!=0:raise RuntimeError('Prior mode did not pass')
 prior_bytes=prior['cleanup']['aggregateBytes']
protected=json.loads((HERE/'protected-inputs.json').read_bytes())
for row in protected:
 if sha(row['path'])!=row['sha256']:raise RuntimeError('Protected input drift: '+row['path'])
for row in json.loads((HERE/'control-seal.json').read_bytes()):
 if sha(HERE/row['path'])!=row['sha256']:raise RuntimeError('Control drift: '+row['path'])
compile((HERE/'verify_controls.py').read_bytes(),str(HERE/'verify_controls.py'),'exec')
source=json.loads((HERE/'sources.json').read_bytes())
for row in source['members']:
 if sha(HERE/row['path'])!=row['sha256']:raise RuntimeError('Source drift: '+row['path'])
spec=importlib.util.spec_from_file_location('custody',CTL);custody=importlib.util.module_from_spec(spec);spec.loader.exec_module(custody)
out=HERE/(mode+'-supervisor');out.mkdir(exist_ok=False)
scratch=out/'scratch';scratch.mkdir()
start=time.monotonic()
c=custody.Commands(out,dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(scratch),TMP=str(scratch),TEMP=str(scratch)),deadline=start+60,cleanup_seconds=5,output_bytes=8388608,total_output_bytes=67108864-prior_bytes)
argv=[PYTHON,'-B']+(['-O'] if mode=='optimized' else [])+[str(HERE/'verify_controls.py'),mode,sha(HERE/'sources.json'),source['tree_sha256']]
r={'mode':mode,'status':'pending','argv':argv,'python':sys.version,'pythonSHA256':sha(Path(sys.executable).resolve()),'controllerSHA256':sha(CTL),'sourceSealSHA256':sha(HERE/'sources.json'),'controlSHA256':sha(HERE/'verify_controls.py'),'maximumCampaigns':2,'maximumSecondsPerCampaign':60,'aggregateSecondsBudget':120,'realInnerChildren':0,'actualOriginal36Rerun':False}
try:c.run('controls-'+mode,argv,ROOT,timeout=55,allowed=(0,1))
except BaseException as error:r['error']=repr(error)
if c.hold:
 save(HERE/'HOLD.json',{'hold':c.hold,'commands':c.records,'scratch':str(scratch),'noFurtherProcessOperations':True})
 r.update(status='UNKNOWN',cleanup={'allTerminalCustody':False,'scratchRemoved':False});save(out/'result.json',r);raise SystemExit(2)
r['cleanup']=c.cleanup(scratch)
if c.hold:save(HERE/'HOLD.json',{'hold':c.hold,'commands':c.records,'scratch':str(scratch),'noFurtherProcessOperations':True})
r['commands']=c.records
r['elapsedSeconds']=time.monotonic()-start
r['protectedInputsUnchanged']=all(sha(x['path'])==x['sha256'] for x in protected)
r['sourcePostflight']=all(sha(HERE/x['path'])==x['sha256'] for x in source['members'])
r['testExit']=c.records[-1]['exit_code'] if c.records else None
r['status']='PASS' if r['testExit']==0 and r['cleanup']['allTerminalCustody'] and r['protectedInputsUnchanged'] and r['sourcePostflight'] and not c.limit and not c.hold and 'error' not in r else 'FAIL'
save(out/'result.json',r)
print(json.dumps({k:v for k,v in r.items() if k!='commands'}))
raise SystemExit(0 if r['status']=='PASS' else 1)
