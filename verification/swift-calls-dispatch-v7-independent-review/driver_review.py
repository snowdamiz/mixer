#!/usr/bin/env python3
"""Pure plan and immutable tooling-control review, with no process execution."""
from pathlib import Path
import ast, collections, datetime, hashlib, json, sys
HERE=Path(__file__).resolve().parent
PACKET=HERE.parent/'swift-calls-dispatch/v7-fixture-expectations'
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda b:hashlib.sha256(b).hexdigest()
def main():
 source=(PACKET/'qualified_runtime.py').read_bytes()
 assert sha(source)=='86595d8e18360fec5101a90feef7744c2f2a32d0482f88a6003ff1b7dfd4d2fb'
 tree=ast.parse(source);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='plan')
 frozen=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(x,ast.Name)and x.id=='FROZEN'for x in n.targets))
 scope={'FROZEN':frozen,'PREFIXES':[f'swift_dispatch_cd{i:02}_'for i in range(1,25)]}
 # Evaluate only the reviewed pure plan function. No import/main/facade executes.
 exec(compile(ast.Module(body=[fn],type_ignores=[]),str(PACKET/'qualified_runtime.py'),'exec'),scope)
 rows=scope['plan']();assert len(rows)==27 and len({r['id']for r in rows})==27
 digest=sha(enc(rows));assert digest=='ec311b9d62cf95d605889707058e3c38c5624a2f980e12c3eb7d173df2a9a44d'
 plan=json.loads((PACKET/'qualification-plan.json').read_bytes());assert rows==plan['commands']
 for row in rows:
  if row['id'].startswith('library-'):
   assert row['post']['prefixes']==scope['PREFIXES']and row['post']['args']==['--nocapture','--test-threads=1']
  if row['id'].startswith('frozen-'):
   assert row['post']['target']in frozen and row['post']['args']==['--nocapture','--test-threads=1']
 collector=(PACKET/'collect.py').read_bytes();old=(PACKET.parent/'collect.py').read_bytes()
 assert old.replace(b'ROOT=HERE.parents[1]',b'ROOT=HERE.parents[2]')==collector
 controls=[]
 for path in sorted((PACKET/'tooling-tests').glob('*/controls.json')):
  data=json.loads(path.read_bytes());clean=json.loads((path.parent/'test-final-cleanup.json').read_bytes())
  assert all(v is True for k,v in data.items()if k not in ['mixerVMExecuted','compilerExecuted','nativeExecuted'])
  assert data['mixerVMExecuted']is False and data['compilerExecuted']is False and data['nativeExecuted']is False
  assert clean['allOwnedChildrenStopped']and clean['allOwnedTargetsRemoved']and clean['nativeInstancesCreated']==0
  controls.append({'path':str(path.relative_to(PACKET)),'sha256':sha(path.read_bytes()),'cleanupSHA256':sha((path.parent/'test-final-cleanup.json').read_bytes()),'controls':data})
 assert any(x['controls'].get('lsofLaunchExceptionLatchesPreservation')for x in controls)
 result={'schema':1,'status':'sealed-driver-plan-and-scoped-controls-reviewed','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':sys.argv,'pythonVersion':sys.version,'verifierSHA256':sha(Path(__file__).read_bytes()),'driverSHA256':sha(source),'planSHA256':digest,'commands':len(rows),'families':dict(collections.Counter(r['id'].split('-')[0]for r in rows)),'controls':controls,'sourceReview':{'perLaunchCandidateAndActualCompilerSysrootPins':True,'requiresExplicitRootSelectionSourceSealDriverPlanHashes':True,'rawPipeRetentionBeforeCollectorValidation':True,'unreapedOwnedChildAndOriginalNewSessionPGIDRequiredForEveryCollectorKill':True,'completedNumericPGIDCannotAuthorizeKill':True,'independentProcessAndTargetCleanupAttempts':True,'actualFinalPSRequeryRequiredEmpty':True,'strictLsofRC1AndNoOutputOrDiagnosticsRequired':True,'scanHolderErrorAndLaunchExceptionStickyTargetPreservation':True,'commandSuccessAndCleanupSuccessSeparateAndBothRequired':True,'fullLibraryCDPrefixesAndIndependentTracesRequired':True,'freshOwnedTargetPerPlanCommand':True,'compileAndExecutableTimeoutSeconds':900},'compilerExecutedByReviewer':False,'VMExecutedByReviewer':False,'processesCreatedByReviewer':0,'runtimeQualified':False,'rootSelectionPending':True}
 (HERE/'driver-review.json').write_bytes(enc(result));(HERE/'reviewed-plan.json').write_bytes(enc(rows));print(result['status'],digest)
if __name__=='__main__':main()
