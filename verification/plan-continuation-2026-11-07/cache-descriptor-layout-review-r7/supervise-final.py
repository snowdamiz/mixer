import hashlib, importlib.util, json, os, sys, time
from pathlib import Path
START=time.monotonic()
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CAND=HERE.parent/'cache-descriptor-layout-fix-r7'
CTL=HERE.parent/'native-custody-premise/cleanup_control.py'
PYTHON='/opt/homebrew/opt/python@3.14/bin/python3.14'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x): p.write_text(json.dumps(x,indent=2)+chr(10))
if (HERE/'HOLD.json').exists(): raise RuntimeError('Sticky UNKNOWN')
if sha(CTL)!='8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df': raise RuntimeError('Controller drift')
if Path(sys.executable).resolve()!=Path(PYTHON).resolve() or sha(Path(PYTHON).resolve())!='e401ac7a95cda75dee34a0cfe1e4faf0a6df1a501cf67887f177fb78cd4eb60a': raise RuntimeError('Python drift')
prior=json.loads((HERE/'normal-supervisor/result.json').read_bytes())
if not prior['custodyComplete'] or not prior['protectedInputsUnchanged']: raise RuntimeError('First campaign not safely complete')
protected=json.loads((HERE/'protected-inputs.json').read_bytes())
for row in protected:
    if sha(row['path'])!=row['sha256']: raise RuntimeError('Protected input drift: '+row['path'])
for row in json.loads((HERE/'control-seal.json').read_bytes()):
    if sha(HERE/row['path'])!=row['sha256']: raise RuntimeError('Control drift: '+row['path'])
compile((HERE/'review.py').read_bytes(),str(HERE/'review.py'),'exec')
source=json.loads((CAND/'sources.json').read_bytes());seal=sha(CAND/'sources.json')
spec=importlib.util.spec_from_file_location('accepted_custody',CTL)
custody=importlib.util.module_from_spec(spec);spec.loader.exec_module(custody)
out=HERE/'final-supervisor';out.mkdir()
scratch=out/'scratch';scratch.mkdir()
c=custody.Commands(out,dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(scratch),TMP=str(scratch),TEMP=str(scratch)),deadline=START+60,cleanup_seconds=5,output_bytes=8388608,total_output_bytes=67108864-prior['cleanup']['aggregateBytes'])
commands=[(mode,[PYTHON,'-B']+(['-O'] if mode=='optimized' else [])+[str(HERE/'review.py'),mode,seal,source['tree_sha256']]) for mode in ['normal','optimized']]
r={'campaign':2,'commandsPreparedBeforeLaunch':commands,'python':sys.version,'pythonSHA256':sha(Path(PYTHON).resolve()),'host':list(os.uname()),'controllerSHA256':sha(CTL),'sourceSealSHA256':seal,'treeSHA256':source['tree_sha256'],'reviewSHA256':sha(HERE/'review.py'),'limits':{'campaigns':2,'secondsPerCampaign':60,'totalSeconds':120,'commandBytes':8388608,'aggregateBytes':67108864},'realInnerChildren':0,'actualOriginal36Rerun':False}
for mode,argv in commands:
    try: c.run('review-'+mode,argv,ROOT,timeout=55,allowed=(0,1))
    except BaseException as error: r.setdefault('executionErrors',[]).append(repr(error))
    if c.hold:
        save(HERE/'HOLD.json',{'hold':c.hold,'commands':c.records,'scratch':str(scratch),'noFurtherProcessOperations':True})
        r.update(custodyComplete=False,commands=c.records,cleanup={'allTerminalCustody':False,'scratchRemoved':False})
        save(out/'result.json',r);raise SystemExit(2)
    if c.limit or r.get('executionErrors'):break
r['cleanup']=c.cleanup(scratch)
if c.hold:save(HERE/'HOLD.json',{'hold':c.hold,'commands':c.records,'scratch':str(scratch),'noFurtherProcessOperations':True})
r['commands']=c.records
r['elapsedSeconds']=time.monotonic()-START
r['protectedInputsUnchanged']=all(sha(x['path'])==x['sha256'] for x in protected)
r['sourcePostflight']=all(sha(CAND/x['path'])==x['sha256'] and sha(HERE/'executed-sources'/x['path'])==x['sha256'] for x in source['members'])
r['testExits']=[x['exit_code'] for x in c.records]
r['custodyComplete']=r['cleanup']['allTerminalCustody'] and r['cleanup']['scratchRemoved'] and not c.limit and not c.hold and not r.get('executionErrors')
save(out/'result.json',r)
print(json.dumps({k:v for k,v in r.items() if k!='commands'}))
raise SystemExit(0 if r['custodyComplete'] and r['protectedInputsUnchanged'] and r['sourcePostflight'] else 2)
