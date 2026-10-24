"""Seal V7 source/proof/driver, binding unchanged V5 and preserved V6 history."""
import sys,os,datetime,shutil
from pathlib import Path
import collect as c
assert not (c.HERE/'review-seal.json').exists()
parent=c.read_json(c.HERE.parent/'review-seal.json');assert c.sha((c.HERE.parent/'review-seal.json').read_bytes())=='7d5a043e7c982a84d5fe1a85444a6a492a40ebddf87a36e95ebdedde02593b15'
selected=['src/experimental_swift_reactor/frame_operations_tests.rs','src/experimental_swift_reactor/memory_operations_tests.rs','src/experimental_swift_reactor/bulk_memory_operations_tests.rs'];allowed=set(parent['allowedChangedCandidateFiles'])|set(selected)
source=c.sha(c.enc(c.manifest(c.HERE/'candidate')));assert source=='78e2586b41f698c60e1bcd4cdd4abb33fbf98d747d1ee183a793988dea7b5237';assert c.read_json(c.HERE/'final-accounting-report.json')['sourceClosure']==source and c.read_json(c.HERE/'v5-to-v7-summary.json')['allSelectedRuntimeMIRByteEqual']
old=(c.HERE.parent/'collect.py').read_bytes();new=(c.HERE/'collect.py').read_bytes();assert old.replace(b'ROOT=HERE.parents[1]',b'ROOT=HERE.parents[2]')==new
c.save(c.HERE/'collector-reuse.json',{'parentSHA256':c.sha(old),'currentSHA256':c.sha(new),'soleDelta':'Nested packet ROOT lookup parents[1]→parents[2]; execution/collection/archive algorithms byte-identical','runtimeAdapters':'Only reviewed qualified_runtime.py facades; no collector source mutation'})
s=c.read_json(c.HERE/'layout-tool-session.json');cleanup=c.read_json(c.HERE/s['preparation']/'final-cleanup.json');assert cleanup['removed']and not Path(cleanup['scratch']).exists()
links=[];attempts=[]
for a in sorted((c.HERE/'attempts').iterdir()):
 if a.is_symlink():links.append({'path':str(a.relative_to(c.HERE)),'target':os.readlink(a),'resolvedRelativePath':os.path.relpath(a.resolve(),c.HERE)});continue
 row=c.read_json(a/'command.json');clean=c.read_json(a/'cleanup.json');assert row['sourceUnchanged']and not row['remainingGroup']and clean['removed']and not Path(clean['scratch']).exists()
 attempts.append({'path':str(a.relative_to(c.HERE)),'commandSHA256':c.sha((a/'command.json').read_bytes()),'exitCode':row['exitCode'],'sourceClosure':row['sourceClosure'],'cleanupSHA256':c.sha((a/'cleanup.json').read_bytes())})
for p in (c.HERE/'attempts').glob('*/overlay-cleanup.json'):
 row=c.read_json(p);assert row['removed']and not Path(row['scratch']).exists()
c.save(c.HERE/'shared-evidence-links.json',links);c.save(c.HERE/'captured-attempt-index.json',attempts)
cache=c.HERE/'__pycache__';cached=[{'path':str(p.relative_to(c.HERE)),'sha256':c.sha(p.read_bytes())}for p in cache.rglob('*')if p.is_file()]if cache.exists()else[]
if cache.exists():shutil.rmtree(cache)
c.save(c.HERE/'owned-python-cache-cleanup.json',{'removed':not cache.exists(),'files':cached,'sourceAndRawAttemptsPreserved':True})
for rel in ['AGENTS.md','mixer-product-plan.md','docs/swift-calls-dispatch-contract.md','docs/swift-optimized-accounting-contract-audit.md','docs/swift-calls-dispatch-implementation.md']:c.save(c.HERE/'review-inputs'/rel,(c.ROOT/rel).read_bytes())
for p in sorted((c.ROOT/'verification/swift-calls-dispatch-root-review').glob('*.json')):c.save(c.HERE/'review-inputs/authority'/p.name,p.read_bytes())
c.save(c.HERE/'review-seal-command.json',{'argv':[sys.executable,'-B',str(Path(__file__))],'sourceSHA256':c.sha(Path(__file__).read_bytes()),'pythonVersion':sys.version,'pythonSHA256':c.sha(Path(sys.executable).read_bytes()),'createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Seal capture and owned cache cleanup only; no compiler/VM/native execution'})
bindings={}
for p in sorted(c.HERE.rglob('*')):
 if not p.is_file()or '__pycache__'in p.relative_to(c.HERE).parts or p.name in ['review-seal.json','review-seal.sha256']:continue
 raw=p.read_bytes();bindings[str(p.relative_to(c.HERE))]={'sha256':c.sha(raw),'bytes':len(raw)}
seal={'version':7,'candidateSourceClosure':source,'baselineSourceClosure':parent['baselineSourceClosure'],'parentSealSHA256':c.sha((c.HERE.parent/'review-seal.json').read_bytes()),'allowedChangedCandidateFiles':sorted(allowed),'selectedFixtureOnlyFiles':selected,'originalEightImplementationFilesByteIdenticalToV5':True,'bindings':bindings,'capturedNewAttempts':len(attempts),'sharedHistoricalAttemptLinks':len(links),'allOwnedCompilerGroupsAndScratchCleaned':True,'qualificationDriverSHA256':c.sha((c.HERE/'qualified_runtime.py').read_bytes()),'qualificationPlanSHA256':c.sha(c.enc(c.read_json(c.HERE/'qualification-plan.json')['commands'])),'runtimeQualified':False,'independentAccountingAccepted':False,'rootSelectionPending':True,'readOnlyVerifier':{'argv':['python3','-B','verification/swift-calls-dispatch/v7-fixture-expectations/read_only_verify.py'],'performsCompilation':False,'performsVMExecution':False,'writesFiles':False},'scope':'Exact three selected original fixture expectation additions over accepted V5; full refreshed V7 logical proof and qualification driver. No runtime/public/Ready/fullSwift/native/FieldLog/OTA/GA acceptance.'}
c.save(c.HERE/'review-seal.json',seal);digest=c.sha((c.HERE/'review-seal.json').read_bytes());c.save(c.HERE/'review-seal.sha256',(digest+'  review-seal.json\n').encode());print(digest,len(bindings),'bound V7 files',len(attempts),'new attempts')
