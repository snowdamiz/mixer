#!/usr/bin/env python3
"""Archive exact tested bytes, verify evidence, consume owned products and seal."""
import sys
sys.dont_write_bytecode=True
import datetime,difflib,hashlib,json,os,pathlib,subprocess,tarfile,time
import run

OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
began=now();assert not (OUT/'seal.json').exists()
python=pathlib.Path(sys.executable).resolve()
tool={'path':str(python),'version':sys.version,'sha256':sha(python.read_bytes())}
environment={'system':os.uname()._asdict() if hasattr(os.uname(),'_asdict') else list(os.uname()),'python':tool}
write(OUT/'environment.json',environment)
live=run.live();seals=run.verify_seals()
initial=json.loads((OUT/'inputs.json').read_text());current=run.inputs()
metadata={p:{'before':h,'after':current[p]} for p,h in initial['metadata'].items() if h!=current[p]}
assert all(p=='PLAN.md' for p in metadata),metadata
commands={}
expected_failures={'candidate-original-swift','candidate-original-swift-2','baseline-expanded'}
for directory in sorted((OUT/'commands').iterdir()):
    result=json.loads((directory/'result.json').read_text());command=json.loads((directory/'command.json').read_text())
    for stream in ['stdout','stderr']:assert sha((directory/stream).read_bytes())==result[stream+'SHA256']
    assert result['exitCode']==(101 if directory.name in expected_failures else 0),directory
    assert result['error'] is None and result['sourceUnchanged']
    assert command['liveClosureBefore']==result['liveClosureAfter']==run.EXPECTED
    source=(directory/'source-manifest.json').read_bytes();assert sha(source)==command['sourceManifestSHA256']
    assert len(json.loads(source))==132
    commands[directory.name]={'exitCode':result['exitCode'],'resultSHA256':sha((directory/'result.json').read_bytes()),'sourceManifestSHA256':sha(source)}
assert len(commands)==14,len(commands)
for mode,label in [('baseline','tested-baseline'),('candidate','candidate')]:
    manifest=run.closure(run.SCRATCH/mode)
    write(OUT/(label+'-source-manifest.json'),manifest)
    with tarfile.open(OUT/(label+'-source.tar.gz'),'w:gz') as archive:
        for relative in sorted(manifest):archive.add(run.SCRATCH/mode/relative,arcname=relative,recursive=False)
    with tarfile.open(OUT/(label+'-source.tar.gz'),'r:gz') as archive:
        assert set(archive.getnames())==set(manifest)
        for member in archive.getmembers():assert sha(archive.extractfile(member).read())==manifest[member.name]
for base,label in [(ROOT/'vm','candidate-vs-pristine.patch'),(run.SCRATCH/'baseline','candidate-vs-tested-baseline.patch')]:
    chunks=[]
    for relative in sorted(live):
        a=(base/relative).read_bytes();b=(run.SCRATCH/'candidate'/relative).read_bytes()
        if a!=b:
            chunks.extend(difflib.unified_diff(a.decode().splitlines(True),b.decode().splitlines(True),fromfile='a/'+relative,tofile='b/'+relative))
    (OUT/label).write_text(''.join(chunks))
audit=OUT/'assessment-reproduction';assert not audit.exists();audit.mkdir()
argv=[sys.executable,str(OUT/'assess.py')]
write(audit/'command.json',{'at':now(),'argv':argv,'cwd':str(ROOT),'python':tool,
  'scriptSHA256':sha((OUT/'assess.py').read_bytes()),'scope':'Derive exact differentials and rejection from retained finite Rust outputs; no engine rerun'})
start=time.monotonic();process=subprocess.run(argv,cwd=ROOT,env=os.environ|{'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,timeout=60)
(audit/'stdout').write_bytes(process.stdout);(audit/'stderr').write_bytes(process.stderr)
write(audit/'result.json',{'exitCode':process.returncode,'seconds':time.monotonic()-start,'stdoutSHA256':sha(process.stdout),'stderrSHA256':sha(process.stderr)})
assert process.returncode==0,process.stderr.decode()
comparison=json.loads((OUT/'comparison.json').read_text());assert comparison['status']=='rejected-for-integration-and-full-target'
run.cleanup();assert not run.SCRATCH.exists()
assert not (OUT/'__pycache__').exists()
assert run.live()==live
write(OUT/'receipt.json',{'schema':1,'at':now(),'began':began,'revisionBefore':initial['revision'],
  'revisionAfter':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
  'status':comparison['status'],'rootDecision':'Root agreed to preserve and reject after three measured work regressions plus memory admission regressions. No retuning, live integration or full-target run.',
  'liveSourceFiles':132,'liveClosure':run.EXPECTED,'frozenPackets':seals,'metadataOnlyDrift':metadata,
  'commands':commands,'allSynchronousChildrenCompleted':True,'ownedScratchAbsent':True,
  'completeInventoryBytes':20472,'DeltaExisting':0,'workBlocks':[41,16], 'hitWorkParity':True,'hitAllocationParity':True,'hitByteParity':False,
  'newHostMethods':{'baseline':8,'candidate':9},'originalSwift':{'baselinePassed':39,'candidatePassed':37,'candidateFailed':2},
  'fullTarget':'not run','nativeUIAndCapture':'not used; paused','scope':'finite host feasibility, rejected; independent result audit pending'})
final=OUT/'finalization';final.mkdir()
write(final/'command.json',{'at':began,'argv':[sys.executable,str(pathlib.Path(__file__).resolve())],'cwd':str(ROOT),'python':tool,
  'scriptSHA256':sha(pathlib.Path(__file__).read_bytes()),'scope':'Archive exact finite source/evidence, verify observed results, remove only identity-bound owned scratch, seal'})
message='Finite Rust candidate rejected; archives verified; 132 live files unchanged; owned scratch/compiler products removed.\n'
(final/'stdout').write_text(message);(final/'stderr').write_text('')
write(final/'result.json',{'at':now(),'exitCode':0,'stdoutSHA256':sha(message.encode()),'stderrSHA256':sha(b''),'ownedScratchAbsent':True})
members=[]
paths=sorted([ROOT/'docs/swift-count-plan-retention-candidate.md']+[p for p in OUT.rglob('*') if p.is_file()])
for p in paths:
    b=p.read_bytes();members.append({'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':sha(b)})
seal={'schema':1,'sourceRevision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 'liveSourceFiles':132,'liveClosure':run.EXPECTED,'selection':'rejected-no-live-integration-no-full-target','ownedScratchAbsent':True,
 'scope':'Actual finite isolated Rust feasibility result, original failures preserved; independent review pending','members':members}
write(OUT/'seal.json',seal)
print(message,end='');print('sealSHA256='+sha((OUT/'seal.json').read_bytes()),'members='+str(len(members)))
