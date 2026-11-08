"""One bounded campaign; both Python modes through the accepted custody controller."""
import hashlib, importlib.util, json, os, sys, time
from pathlib import Path
START=time.monotonic()
OWN=Path(__file__).resolve().parent
ROOT=OWN.parents[2]
CAND=OWN.parent/'cache-refusal-cleanup-r8'
CTL=OWN.parent/'native-custody-premise/cleanup_control.py'
PYTHON='/opt/homebrew/opt/python@3.14/bin/python3.14'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def need(v,m):
    if not v:raise RuntimeError(m)
def checked(rows):return all(Path(r['path']).stat().st_size==r['bytes'] and sha(r['path'])==r['sha256'] for r in rows)
need(not (OWN/'HOLD.json').exists(),'Sticky hold')
need(Path(sys.executable).resolve()==Path(PYTHON).resolve(),'Pinned interpreter required')
need(sha(CTL)=='8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df','Controller drift')
protected=json.loads((OWN/'protected-inputs.json').read_bytes())
controls=json.loads((OWN/'review-control-seal.json').read_bytes())
need(checked(protected) and checked(controls),'Input drift')
need(sha(CAND/'sources.json')=='19af15d0fcb485957e2cb459c2a654e07f34f71ee52163f01a5336b17b09ec9b','Source seal drift')
need(sha(CAND/'control-seal.json')=='1422fc0b994415ae4e87d39360dd3a0472c053f1438ac6d3907d294cec615814','Candidate control drift')
for name in ['driver.py','review.py','focused_controls.py','fresh_probes.py']:compile((OWN/name).read_bytes(),str(OWN/name),'exec')
for p in [CAND/'descriptor_preflight.py',CAND/'test_scope.py',CAND/'stdin_guard.py',OWN/'stdin_guard.py',OWN/'focused_controls.py']:
    need(p.is_absolute() and p.is_file(),'Absolute import path absent: '+str(p))
spec=importlib.util.spec_from_file_location('accepted_custody',CTL)
custody=importlib.util.module_from_spec(spec);spec.loader.exec_module(custody)
logs=OWN/'campaign';logs.mkdir()
scratch=OWN/'scratch';scratch.mkdir()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(scratch),TMP=str(scratch),TEMP=str(scratch),PYTHONPATH=str(OWN)+os.pathsep+str(CAND))
c=custody.Commands(logs,env,deadline=START+60,cleanup_seconds=5,output_bytes=8388608,total_output_bytes=67108864)
r={'status':'pending','bootstrap_argv':sys.argv,'python':sys.version,'executable':sys.executable,'executableSHA256':sha(Path(sys.executable).resolve()),'host':list(os.uname()),'controllerSHA256':sha(CTL),'sourceSealSHA':sha(CAND/'sources.json'),'treeSHA':json.loads((CAND/'sources.json').read_bytes())['tree_sha256'],'controlSealSHA':sha(CAND/'control-seal.json'),'reviewControlSealSHA':sha(OWN/'review-control-seal.json'),'revision':json.loads((OWN/'revision.json').read_bytes()),'campaigns':1,'maximumCampaigns':2,'maximumSecondsPerCampaign':60,'totalSecondsBudget':120,'perCommandOutputCap':8388608,'aggregateOutputCap':67108864,'realInnerChildren':0,'actualOriginal36Rerun':False,'modes':{}}
def hold_exit():
    save(OWN/'HOLD.json',{'hold':c.hold,'commands':c.records,'scratch':str(scratch),'noFurtherProcessOperations':True})
    r.update(status='UNKNOWN',commands=c.records,elapsedSeconds=time.monotonic()-START,cleanup={'allTerminalCustody':False,'scratchRemoved':False})
    save(logs/'result.json',r)
    raise SystemExit(2)
try:
    for mode in ['normal','optimized']:
        argv=[PYTHON,'-B']+(['-O'] if mode=='optimized' else [])+[str(OWN/'driver.py'),mode,r['sourceSealSHA'],r['treeSHA']]
        c.run('review-'+mode,argv,ROOT,timeout=24,allowed=(0,1))
        retained=json.loads((OWN/('evidence-'+mode)/'result.json').read_bytes())
        fresh=json.loads((OWN/('evidence-'+mode)/'fresh-result.json').read_bytes())
        r['modes'][mode]={'retained':retained,'fresh':fresh}
except BaseException as error:r['error']=repr(error)
if c.hold:hold_exit()
r['cleanup']=c.cleanup(scratch)
if c.hold:hold_exit()
r.update(commands=c.records,elapsedSeconds=time.monotonic()-START,protectedInputsUnchanged=checked(protected),reviewControlsUnchanged=checked(controls))
r['status']='PASS' if ('error' not in r and len(r['modes'])==2 and all(v['retained']['tests']==70 and v['retained']['expected']==70 and v['retained']['successful'] and v['fresh']['tests']==4 and v['fresh']['successful'] for v in r['modes'].values()) and all(x['exit_code']==0 for x in c.records) and r['cleanup']['allTerminalCustody'] and r['cleanup']['scratchRemoved'] and r['protectedInputsUnchanged'] and r['reviewControlsUnchanged'] and r['elapsedSeconds']<=60 and not c.limit and not c.hold) else 'FAIL'
save(logs/'result.json',r)
print(json.dumps({k:v for k,v in r.items() if k not in ['commands','host','modes']}))
sys.exit(0 if r['status']=='PASS' else 1)
