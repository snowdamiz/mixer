"""Two finite campaigns; every child uses the pinned accepted custody controller."""
import hashlib, importlib.util, json, os, sys, time
from pathlib import Path
START=time.monotonic()
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CTL=HERE.parent/'native-custody-premise/cleanup_control.py'
PYTHON='/opt/homebrew/opt/python@3.14/bin/python3.14'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def require(value,message):
    if not value:raise RuntimeError(message)
def checked(rows,base=None):
    return all(sha((base/r['path']) if base else r['path'])==r['sha256'] for r in rows)
def source_check():
    seal=json.loads((HERE/'sources.json').read_bytes())
    require(seal['member_count']==20 and len(seal['members'])==20,'20 shipping files required')
    require(checked(seal['members'],HERE),'Shipping drift')
    tree=hashlib.sha256(json.dumps(seal['members'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    require(tree==seal['tree_sha256'],'Canonical tree drift')
    return seal
mode=sys.argv[1]
require(mode in ['normal','optimized'],'Two fixed modes only')
require(not (HERE/'HOLD.json').exists(),'Sticky hold')
require(sha(CTL)=='8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df','Controller drift')
require(Path(sys.executable).resolve()==Path(PYTHON).resolve(),'Python drift')
prior_bytes=0;prior_seconds=0
if mode=='optimized':
    prior=json.loads((HERE/'normal-supervisor/result.json').read_bytes())
    require(prior['status']=='PASS' and prior['cleanup']['allTerminalCustody'],'First campaign incomplete')
    require(prior['sourceSealSHA256']==sha(HERE/'sources.json'),'Final modes require same source bytes')
    require(prior['controlSealSHA256']==sha(HERE/'control-seal.json'),'Final modes require same control bytes')
    prior_bytes=prior['cleanup']['aggregateBytes'];prior_seconds=prior['elapsedSeconds']
protected=json.loads((HERE/'protected-inputs.json').read_bytes())
controls=json.loads((HERE/'control-seal.json').read_bytes())
require(checked(protected),'Protected input drift')
require(checked(controls,HERE),'Control drift')
source=source_check()
for name in ['reproduce_r7.py','verify_controls.py','focused_controls.py']:
    compile((HERE/name).read_bytes(),str(HERE/name),'exec')
if mode=='normal':
    require(sha(HERE/'sources.json')=='224abe485fcf30cf0dd7a1e1747c3c122511d497fd1a39499738b767c2e07402','Baseline copy must still be exact R7')
    require(source['tree_sha256']=='8361cc10d0026c1bb832f5cde012aa8cedc5baf48d4c26105e1845c63be549d3','R7 tree drift')
spec=importlib.util.spec_from_file_location('accepted_custody',CTL)
custody=importlib.util.module_from_spec(spec);spec.loader.exec_module(custody)
out=HERE/(mode+'-supervisor');out.mkdir()
scratch=HERE/'scratch'/mode;scratch.mkdir()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(scratch),TMP=str(scratch),TEMP=str(scratch),PYTHONPATH=str(HERE))
c=custody.Commands(out,env,deadline=min(START+60,START+120-prior_seconds),cleanup_seconds=5,output_bytes=8388608,total_output_bytes=67108864-prior_bytes)
r={'mode':mode,'status':'pending','bootstrap_argv':sys.argv,'python':sys.version,'pythonSHA256':sha(Path(sys.executable).resolve()),
   'host':list(os.uname()),'controllerSHA256':sha(CTL),'controlSealSHA256':sha(HERE/'control-seal.json'),
   'maximumCampaigns':2,'maximumSecondsPerCampaign':60,'aggregateSecondsBudget':120,
   'perCommandOutputCap':8388608,'aggregateOutputCap':67108864,'realInnerChildren':0,'actualOriginal36Rerun':False,
   'sourceRevision':json.loads((HERE/'r8-revision.json').read_bytes()),'preflightSourceSealSHA256':sha(HERE/'sources.json')}
def hold_exit():
    save(HERE/'HOLD.json',{'hold':c.hold,'commands':c.records,'scratch':str(scratch),'noFurtherProcessOperations':True})
    r.update(status='UNKNOWN',cleanup={'allTerminalCustody':False,'scratchRemoved':False},elapsedSeconds=time.monotonic()-START)
    save(out/'result.json',r)
    raise SystemExit(2)
try:
    if mode=='normal':
        for baseline_mode in ['normal','optimized']:
            argv=[PYTHON,'-B']+(['-O'] if baseline_mode=='optimized' else [])+[str(HERE/'reproduce_r7.py')]
            c.run('r7-baseline-'+baseline_mode,argv,ROOT,timeout=12)
            proof=json.loads((HERE/('baseline-'+baseline_mode)/'result.json').read_bytes())
            require(proof['expected_R7_failures_reproduced'],'Exact R7 refusal failures not reproduced')
        c.admissible()
        require(checked(protected),'Protected drift before correction')
        patches=json.loads((HERE/'patch.json').read_bytes())
        changes=[]
        for patch in patches:
            path=HERE/patch['path'];before=path.read_bytes()
            require(sha(path)==patch['before'],'Patch preimage drift')
            text=before.decode();require(patch['old'] in text,'Patch anchor absent')
            if not patch.get('all'):require(text.count(patch['old'])==1,'Patch anchor not unique')
            after=text.replace(patch['old'],patch['new'])
            path.write_text(after)
            changes.append({'path':patch['path'],'beforeSHA256':patch['before'],'afterSHA256':sha(path)})
        members=[{'path':row['path'],'bytes':(HERE/row['path']).stat().st_size,'sha256':sha(HERE/row['path'])} for row in source['members']]
        tree=hashlib.sha256(json.dumps(members,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        source={'member_count':20,'members':members,'tree_sha256':tree}
        save(HERE/'sources.json',source)
        save(HERE/'applied-change.json',{'baselineModes':['normal','optimized'],'expectedFailuresPerMode':2,'baselineCompletedBeforePatch':True,'changes':changes,'sourceSealSHA256':sha(HERE/'sources.json'),'treeSHA256':tree})
        snapshots=HERE/'executed-sources';snapshots.mkdir()
        for row in members:(snapshots/row['path']).write_bytes((HERE/row['path']).read_bytes())
        (snapshots/'sources.json').write_bytes((HERE/'sources.json').read_bytes())
    source=source_check()
    argv=[PYTHON,'-B']+(['-O'] if mode=='optimized' else [])+[str(HERE/'verify_controls.py'),mode,sha(HERE/'sources.json'),source['tree_sha256']]
    r.update(argv=argv,sourceSealSHA256=sha(HERE/'sources.json'),treeSHA256=source['tree_sha256'])
    c.run('final-controls-'+mode,argv,ROOT,timeout=40,allowed=(0,1))
    result=json.loads((HERE/('evidence-'+mode)/'result.json').read_bytes())
    r.update(tests=result['tests'],expected=result['expected'],testSuccessful=result['successful'])
except BaseException as error:r['error']=repr(error)
if c.hold:hold_exit()
r['cleanup']=c.cleanup(scratch)
if c.hold:hold_exit()
r['commands']=c.records
r['elapsedSeconds']=time.monotonic()-START
r['aggregateSeconds']=prior_seconds+r['elapsedSeconds']
r['protectedInputsUnchanged']=checked(protected)
r['controlPostflight']=checked(controls,HERE)
r['sourcePostflight']=checked(source['members'],HERE)
r['testExit']=c.records[-1]['exit_code'] if c.records else None
r['status']='PASS' if (r.get('testSuccessful') and r.get('tests')==70 and r.get('expected')==70 and r['testExit']==0
    and r['cleanup']['allTerminalCustody'] and r['cleanup']['scratchRemoved'] and r['protectedInputsUnchanged']
    and r['sourcePostflight'] and r['controlPostflight'] and not c.limit and not c.hold and 'error' not in r
    and r['elapsedSeconds']<=60 and r['aggregateSeconds']<=120) else 'FAIL'
save(out/'result.json',r)
print(json.dumps({k:v for k,v in r.items() if k not in ['commands','host']}))
sys.exit(0 if r['status']=='PASS' else 1)
