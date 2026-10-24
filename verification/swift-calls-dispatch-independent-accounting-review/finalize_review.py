#!/usr/bin/env python3
"""Bind the completed, independent host review; performs no compiler/VM execution."""
from pathlib import Path
import datetime,hashlib,json,shutil,sys
from review import BASE,PACKET,read,require,sha
HERE=Path(__file__).resolve().parent
SOURCE='ba9231499244692bbed61f0566ec72864a979df9e3fc71511560ec66a2e00c70'
SEAL='7d5a043e7c982a84d5fe1a85444a6a492a40ebddf87a36e95ebdedde02593b15'
def bind(p):return {'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
def main():
 statuses={'final-seal-replay.json':'sealed-producer-bindings-passed','final-method-replay.json':'method-replay-passed-additional-review-pending','final-artifact-replay.json':'artifact-replay-passed-additional-review-pending','selected-authority-review.json':'finite-selected-authority-reconciliation-passed','source-owner-temporal-review.json':'source-owner-review-passed-final-packet-pending','source-revision-review.json':'rejected-to-repaired-position-delta-passed'}
 receipts={n:read(HERE/n)for n in statuses}
 for n,expected in statuses.items():require(receipts[n]['status']==expected,'component review did not pass '+n)
 require(sha((PACKET/'review-seal.json').read_bytes())==SEAL,'immutable producer seal changed')
 require(receipts['final-seal-replay.json']['producerSealSHA256']==SEAL,'reviewed seal mismatch')
 require(all(r['sourceClosure']==SOURCE for r in [receipts['final-seal-replay.json'],receipts['final-method-replay.json'],receipts['source-owner-temporal-review.json']]),'reviewed source mismatch')
 for receipt,script in [('final-seal-replay.json','seal_review.py'),('final-method-replay.json','review.py'),('final-artifact-replay.json','artifact_review.py'),('source-revision-review.json','revision_review.py')]:require(receipts[receipt]['verifierSHA256']==sha((HERE/script).read_bytes()),'verifier changed after final replay '+script)
 method=receipts['final-method-replay.json'];artifacts=receipts['final-artifact-replay.json'];authority=receipts['selected-authority-review.json']
 require(method['inventoryRows']==89124 and method['numericPositions']==1032 and authority['positions']==1032,'final complete field extent')
 require(method['phases']=={'active':82768,'permanent':6356},'final temporal partition')
 controls=method['mutationControls']|method['witnessLayouts']['sameSizeMutationControls'];require(len(controls)==13 and all(v=='rejected'for v in controls.values()),'mutation controls incomplete')
 comparisons=sum(sum(d.values())for d in method['witnessLayouts']['originToCompiledFieldComparisons'].values());require(comparisons==524224,'compiled field bridge extent')
 require(len(artifacts['frozenMethods'])==39 and len(artifacts['pairedLayouts'])==8,'paired baseline/candidate or Frozen extent')
 cleanup=[]
 cache=HERE/'__pycache__'
 if cache.exists():
  cleanup=[str(p.relative_to(HERE))for p in sorted(cache.rglob('*'))if p.is_file()];shutil.rmtree(cache)
 commands=[['python3','-B',*r['command']]for r in receipts.values()]
 result={'schema':1,'status':'independent-accounting-review-passed','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'accountableReviewer':'/root/swift_calls_dispatch_independent_accounting_review','modelScope':'Fresh bounded Sol 6.1 xhigh lane under AGENTS.md parallel review authorization','independentAccountingAccepted':True,'sourceClosure':SOURCE,'baselineSourceClosure':'1e89853d56f0ae46720cb0e9d72a4a2a13003f777e1d01f65db154f30782ed9c','producerSeal':{'path':'verification/swift-calls-dispatch/review-seal.json','sha256':SEAL},'reviewScope':'Complete logical source/argument/returned/caller accounting, selected finite exceptions, actual compiler identity/full layout/offsets, temporal admission and original owner/Frozen preservation on the immutable private source closure only.','pendingScopes':['Root V5 selection','Qualified four-configuration CD01–24 runtime','Live source integration','Native simulator/emulator and physical phone evidence','Ready/full Swift acceptance','Immutable published-package FieldLog dogfood','OTA release','GA'],'rootSelectionAccepted':False,'qualifiedRuntimeExecuted':False,'runtimeQualified':False,'gaAccepted':False,'compilerExecutedByReviewer':False,'nativeInstancesCreated':0,'gitOperationsPerformed':False,'producerOrLiveFilesMutated':False,'findings':{'R1':'Resolved: 64 successful param checkpoint precedes optional result; old source remains rejected, final runtime pending.','R2':'Resolved: actual recursive type/definition graphs and complete field/variant layouts bridged in every destination compiler context.','R3':'Resolved: fresh baseline/candidate receipts bind actual compiler and complete official sysroot.'},'openSourceOrMethodFindings':[],'roles':89124,'phaseCounts':method['phases'],'finiteNumericRoles':1032,'methodCounts':method['methods'],'selectedCounts':authority['selectedCounts'],'compiledFieldBindings':comparisons+288,'originRowFieldComparisons':comparisons,'retainedWholeCarrierComparisons':288,'independentMutationControls':controls,'compilerContexts':8,'pairedLayouts':16,'frozenMethodsPreserved':39,'frozenBoundBytes':2912,'stateCeilingBytes':128*1024**2,'combinedCeilingBytes':256*1024**2,'ticketMaximum':86,'python':{'version':sys.version,'executable':str(Path(sys.executable).resolve()),'sha256':sha(Path(sys.executable).resolve().read_bytes())},'commands':commands+[['python3','-B',str(Path(__file__).relative_to(BASE))]],'receipts':{n:bind(HERE/n)for n in statuses},'verifiers':{p.name:bind(p)for p in sorted(HERE.glob('*.py'))},'cleanup':{'ownedCompilerScratchCreated':False,'ownedNativeInstancesCreated':0,'persistentOwnedProcessesCreated':0,'ownedPythonCacheFilesRemoved':cleanup,'producerScratchCleanup':'Sealed tool-preparation final-cleanup.json and per-attempt cleanup receipts verified; no mutation by this reviewer.'}}
 (HERE/'review.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
 bindings={str(p.relative_to(HERE)):bind(p)for p in sorted(HERE.rglob('*'))if p.is_file()and p.name!='review-seal.json'}
 ownseal={'schema':1,'scope':'Independent accounting review only; root-qualified runtime remains pending.','sourceClosure':SOURCE,'producerSealSHA256':SEAL,'bindings':bindings,'documents':{'docs/swift-calls-dispatch-independent-accounting-review.md':bind(BASE/'docs/swift-calls-dispatch-independent-accounting-review.md')}}
 (HERE/'review-seal.json').write_text(json.dumps(ownseal,sort_keys=True,indent=2)+'\n')
 print(json.dumps({'status':result['status'],'reviewPath':str(HERE/'review.json'),'reviewSHA256':sha((HERE/'review.json').read_bytes()),'independentSealSHA256':sha((HERE/'review-seal.json').read_bytes()),'producerSealSHA256':SEAL,'sourceClosure':SOURCE,'roles':result['roles'],'finiteNumericRoles':result['finiteNumericRoles'],'runtimeQualified':False},indent=2))
if __name__=='__main__':main()
