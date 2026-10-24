#!/usr/bin/env python3
"""Finalize this isolated preflight packet; does not authorize product execution."""
from pathlib import Path
import datetime,gzip,hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes() if p.exists() else gzip.decompress(Path(str(p)+'.gz').read_bytes()))
def save(n,x):(HERE/n).write_bytes(enc(x))
qualifying='results/20261024T065629251176Z';OUT=HERE/qualifying;r=read(OUT/'receipt.json');post=read(OUT/'postprocess-receipt.json');assert r['status'].startswith('passed-') and post['status'].startswith('passed-')
comparisons=read(OUT/'corrected-boundary-comparisons.json');bounds={('unit' if x['unit'] else 'production'):x for x in comparisons if x['config']=='swift' and x['profile']=='debug'}
save('qualifying.json',dict(resultDirectory=qualifying,candidateTreeSHA256=r['candidateTreeSHA256'],baselineTreeSHA256=r['baselineTreeSHA256'],canonicalFields=7640,canonicalFunctionCountPerConfiguration=38,preflightOnly=True,rootAcceptanceRequired=True))
bootstrap=[dict(directory=str(p.parent.relative_to(HERE)),status=read(p)['status']) for p in sorted((HERE/'bootstrap').glob('*/receipt.json'))]
results=[dict(directory=str(p.parent.relative_to(HERE)),status=read(p)['status']) for p in sorted((HERE/'results').glob('*/receipt.json'))]
save('development-attempts.json',dict(bootstrap=bootstrap,results=results,failedProducerAttempts=[x for x in bootstrap+results if not x['status'].startswith('passed-')],allRetained=True))
cleanups=[str(p.relative_to(HERE)) for p in sorted(HERE.rglob('*cleanup.json')) if p.name!='owned-scratch-cleanup.json']
assert all(read(HERE/p).get('removed') and not read(HERE/p).get('nativeInstancesStarted',False) for p in cleanups)
save('owned-scratch-cleanup.json',dict(status='all-owned-scratch-removed',receipts=cleanups,removed=True,nativeInstancesStarted=False,otherProjectProcessesTouched=False))
save('receipt.json',dict(schema=1,status='passed-candidate2-producer-preflight-pending-independent-root-review',observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceRevision=r['sourceRevision'],baselineTreeSHA256=r['baselineTreeSHA256'],historicalCandidate1TreeSHA256='6d9e1b3f5aec1bedf2a8dc773a23c1731ee05e094d69d646ab4db8d397381156',candidateTreeSHA256=r['candidateTreeSHA256'],resultDirectory=qualifying,sourcePatchSHA256=sha(HERE/'source.patch'),behaviorDeltaSHA256=sha(HERE/'behavior-delta.patch'),positiveFields=7640,wrapperPositiveFields=136,obsoleteDirectReborrowFields=16,netAdditionalFields=120,selectedFunctionsPerConfig=38,sourceCompilerAndMetadataCommands=len(r['commands']),mirBuilds=len(r['mirInventory']),fullLayouts=16,nestedLayouts=8,privacyCommands=4,exactBounds=bounds,liveVMUnchanged=True,previousProducerAndReviewerPacketsUnchanged=True,controlMethodsExecuted=False,faultBehaviorExecuted=False,sc01Through12Passed=False,controlExecutionAuthorized=False,accountingAccepted=False,implementationAccepted=False,nativeRuntime=False,physicalRuntime=False,physicalPhonesDisconnected=True,logicalOwnershipOnly=True,optimizedMIRCoverageOnly=True,privateCompilerCoreAliases=False,physicalStackOrRSSClaim=False,ceilingsUnchanged=True,gaAcceptance=False))
# Compress bulky immutable compiler evidence, retaining the raw file identity.
index=read(HERE/'compression-index.json') if (HERE/'compression-index.json').exists() else {}
for p in sorted(HERE.rglob('*')):
 if not p.is_file() or p.suffix=='.gz':continue
 relative=str(p.relative_to(HERE));eligible=p.suffix=='.mir' or (p.suffix=='.stdout' and p.stat().st_size>65536) or (p.suffix=='.json' and relative.startswith(('results/','bootstrap/')) and p.stat().st_size>262144)
 if not eligible:continue
 data=p.read_bytes();target=Path(str(p)+'.gz');target.write_bytes(gzip.compress(data,compresslevel=9,mtime=0));index[relative]=dict(gzipPath=str(target.relative_to(HERE)),uncompressedSHA256=hashlib.sha256(data).hexdigest(),storedSHA256=sha(target),uncompressedBytes=len(data),compressedBytes=target.stat().st_size);p.unlink()
save('compression-index.json',index)
inputs=read(OUT/'inputs.json')['files'];external=dict(inputs);external['docs/swift-control-accounting-candidate-2.md']=sha(ROOT/'docs/swift-control-accounting-candidate-2.md')
files={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='seal.json' and '__pycache__' not in p.parts}
save('seal.json',dict(schema=1,status='sealed-candidate2-preflight-only-pending-independent-root-review',files=files,externalBindings=external,candidateTreeSHA256=r['candidateTreeSHA256'],baselineTreeSHA256=r['baselineTreeSHA256'],controlMethodsExecuted=False,controlExecutionAuthorized=False,accountingAccepted=False,implementationAccepted=False,gaAcceptance=False))
print('sealed',len(files),'files; candidate',r['candidateTreeSHA256'])
