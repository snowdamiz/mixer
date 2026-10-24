"""Seal immutable review inputs after all observed compiler work has completed."""
import sys
sys.dont_write_bytecode=True
import collect as c
from pathlib import Path
import shutil,datetime

ALLOWED=['src/experimental/execution/mod.rs','src/experimental/execution/borrowed.rs','src/experimental_swift_reactor/execution.rs','src/experimental_swift_reactor/frame_operations.rs','src/experimental_swift_reactor/memory_growth_operations.rs','src/experimental_swift_reactor/call_dispatch.rs','src/experimental_swift_reactor/call_dispatch_tests.rs','src/experimental_swift_reactor/memory_growth_operations_tests.rs']
assert not (c.HERE/'review-seal.json').exists(),'existing seal must never be overwritten'
cleanup=c.read_json(c.HERE/'tool-preparation/20261024T160529443594Z/final-cleanup.json');assert cleanup['removed']and not Path(cleanup['scratch']).exists()
attempts=[]
for p in sorted((c.HERE/'attempts').glob('*/command.json')):
 row=c.read_json(p);assert 'exitCode'in row and row['sourceUnchanged']and not row['remainingGroup'],p
 clean=c.read_json(p.parent/'cleanup.json');assert clean['removed']and clean['holderCheckEmpty']and not Path(clean['scratch']).exists()and clean['nativeInstancesCreated']==0,p
 attempts.append({'attempt':str(p.parent.relative_to(c.HERE)),'label':row['label'],'exitCode':row['exitCode'],'sourceClosure':row['sourceClosure'],'commandSHA256':c.sha(p.read_bytes()),'cleanupSHA256':c.sha((p.parent/'cleanup.json').read_bytes())})
for p in (c.HERE/'attempts').glob('*/overlay-cleanup.json'):
 x=c.read_json(p);assert x['removed']and x['holderCheckEmpty']and not Path(x['scratch']).exists()
c.save(c.HERE/'captured-attempt-index.json',attempts)
cache=c.HERE/'__pycache__';cached=[{'path':str(p.relative_to(c.HERE)),'sha256':c.sha(p.read_bytes()),'bytes':p.stat().st_size}for p in cache.rglob('*')if p.is_file()]if cache.exists()else[]
if cache.exists():shutil.rmtree(cache)
c.save(c.HERE/'owned-python-cache-cleanup.json',{'removed':not cache.exists(),'files':cached,'proofSourceAndRawAttemptsPreserved':True})
for rel in ['AGENTS.md','mixer-product-plan.md','docs/swift-calls-dispatch-contract.md','docs/swift-optimized-accounting-contract-audit.md','docs/swift-calls-dispatch-implementation.md']:
 c.save(c.HERE/'review-inputs'/rel,(c.ROOT/rel).read_bytes())
for p in sorted((c.ROOT/'verification/swift-calls-dispatch-root-review').glob('*.json')):c.save(c.HERE/'review-inputs/authority'/p.name,p.read_bytes())
c.save(c.HERE/'review-seal-command.json',{'argv':[sys.executable,'-B',str(c.HERE/'seal_review.py')],'pythonVersion':sys.version,'pythonSHA256':c.sha(Path(sys.executable).read_bytes()),'sourceSHA256':c.sha(Path(__file__).read_bytes()),'scope':'Read-only source/artifact capture plus owned seal/cache cleanup; no compiler, interpreter or native execution','createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat()})
bindings={}
for p in sorted(c.HERE.rglob('*')):
 if not p.is_file()or '__pycache__'in p.relative_to(c.HERE).parts or p.name in ['review-seal.json','review-seal.sha256']:continue
 raw=p.read_bytes();bindings[str(p.relative_to(c.HERE))]={'sha256':c.sha(raw),'bytes':len(raw)}
final=c.read_json(c.HERE/'candidate-final-source.json');baseline=c.sha(c.enc(c.manifest(c.HERE/'baseline')));assert baseline=='1e89853d56f0ae46720cb0e9d72a4a2a13003f777e1d01f65db154f30782ed9c'
seal={'version':5,'candidateSourceClosure':final['sourceClosure'],'baselineSourceClosure':baseline,'allowedChangedCandidateFiles':sorted(ALLOWED),'bindings':bindings,'capturedAttempts':len(attempts),'allOwnedCompilerGroupsAndScratchCleaned':True,'runtimeQualified':False,'independentAccountingAccepted':False,'rootSelectionPending':True,'readOnlyVerifier':{'argv':['python3','-B','verification/swift-calls-dispatch/read_only_verify.py'],'performsCompilation':False,'performsVMExecution':False,'writesFiles':False},'scope':'Private full-dispatch/compiler accounting review input; not runtime, full Swift, Ready, native, FieldLog, OTA or GA acceptance'}
c.save(c.HERE/'review-seal.json',seal);digest=c.sha((c.HERE/'review-seal.json').read_bytes());c.save(c.HERE/'review-seal.sha256',(digest+'  review-seal.json\n').encode());print(digest,len(bindings),'bound files',len(attempts),'captured attempts')
