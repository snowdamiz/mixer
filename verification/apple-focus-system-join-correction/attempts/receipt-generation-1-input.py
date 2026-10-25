#!/usr/bin/env python3
"""Finalize host-only evidence metadata without changing any executed input."""
import datetime
import hashlib
import json
import pathlib
import sys

sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def read(name):return json.loads((H/name).read_bytes())
def write(name,value):(H/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
command=read('attempts/attempt-2/command.json');validation=read('attempts/attempt-2/validation.json')
assert command['exitCode']==0 and validation['passed'] is True
for name,binding in command['executionInputs'].items():
 raw=(H/name).read_bytes();assert len(raw)==binding['bytes'] and sha(raw)==binding['sha256'],name
controls=read('attempts/attempt-2/focused-controls.json')['controls']
positive=next(row['result'] for row in controls if row['name']=='exact original positive join')
write('action-selection.json',{'schema':1,'selection':'v7-first-tab','scope':'Only frozen V7 host replay; future runtime originals need separate selection and immutable binding','case':'keyboard-enabled-off','generation':1,'actionIndex':1,'baselineDecimal':'948787.116983291','evaluatedDecimal':'948794.231054541','rawPackets':{name:binding for name,binding in read('input-bindings.json')['files'].items() if name.startswith('inputs/v7/')},'joinedOriginalFingerprints':{key:positive[key] for key in ['beforeObservationSHA256','afterObservationSHA256','witnessSHA256','bindingSHA256','originalVerdictSHA256']},'expectedFingerprintsDerivedFromCandidate':False})
write('cleanup.json',{'schema':1,'ownedScratchCreated':False,'ownedScratchRemaining':False,'ownedPythonCachesAbsent':not list(H.rglob('__pycache__')),'nativeInstancesCreated':0,'nativeInstancesCleaned':0,'nativeQueries':0,'nativeAttempts':0,'otherProjectProcessesOrDataTouched':False,'parentArtifactsWritten':False,'scope':'No compiler or native scratch/instances created; host bytecode disabled; no external cleanup claim'})
write('receipt.json',{'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'pending-independent-host-review','scope':'Host adapter correction of F1/F2 only; frozen V7 originals plus synthetic supplemental rows','sourceRevision':command['sourceRevision'],'sourceExecutionInputTreeSHA256':command['executionInputTreeSHA256'],'adapterSHA256':sha((H/'observation.py').read_bytes()),'producerHandoffSHA256':'5d88cd0069f7e83e73b95903ecf0e9e6b721a73328193653e8e1da8903c81427','producerMembers':177,'reviewHandoffSHA256':'e66d1f5710d5614fc668bec3fc6759fb6080a91002516f13d43994dca2ab35a4','reviewMembers':51,'sourceArchiveSHA256':validation['candidateArchiveSHA256'],'sourceMembers':40,'changedSwiftMembers':[],'commands':['attempts/attempt-1/command.json','attempts/attempt-2/command.json'],'successfulAttempt':2,'retainedFailedAttempts':[{'attempt':1,'reason':'Wrong raw digest fixture mutation was absent from the before packet; mutation assertion failed; corrected fixture only','evidence':'attempts/attempt-1/failure.json'}],'tools':command['tool'],'hostTestMethodsPassed':validation['hostTestMethods'],'originalHostTestMethods':26,'correctionHostTestMethods':12,'focusedResultControls':validation['focusedControls'],'auditChecksPassed':validation['checksPassed'],'auditCheckScope':'Includes repeated parent seal and copied input accounting; not independent behavior tests','originalVerdictObjectAndBytesUnchanged':True,'originalOraclePassed':False,'originalFailingPredicates':['actualNativeFocusTraversal'],'settingsEvidence':'Historical prior passed result; no new run or acceptance','nativePass':False,'sourceHostAccepted':False,'needsFreshIndependentNarrowReview':True,'nativeAccepted':False,'gaAccepted':False,'compilerInvocations':0,'typecheckInvocations':0,'links':0,'appProducts':0,'nativeQueries':0,'nativeAttempts':0,'uiOperations':0,'screenCaptures':0,'physicalPhones':'disconnected-deferred','networkOperations':0,'gitOperations':0,'rootTrackerEdits':0,'parentSealsExactBeforeAndAfter':True,'prohibitedUnrelatedLanesRead':False,'cleanup':'cleanup.json','receiptGeneration':{'argv':[sys.executable,'-B',str(H/'write_receipt.py')],'toolVersion':sys.version,'scriptSHA256':sha(pathlib.Path(__file__).read_bytes())},'sealCommand':[sys.executable,'-B',str(H/'seal.py')],'verifyCommand':[sys.executable,'-B',str(H/'verify_seal.py')]})
print(json.dumps({'receiptWritten':True,'executionInputsUnchanged':True,'hostTestMethodsPassed':validation['hostTestMethods'],'nativePass':False},sort_keys=True))
