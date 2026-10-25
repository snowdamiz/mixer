#!/usr/bin/env python3
import datetime,hashlib,json,stat
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1]
RUNID="4c0ed51e-8060-4646-83a5-873b875d4d30"
RUN=ROOT/"verification/apple-settings-instrumented-runtime-preparation"/("native-run-v6-"+RUNID)
SELECT=ROOT/"verification/apple-settings-instrumented-native-root-selection"
OUT=BASE/"result";OUT.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def row(p):
 s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink(),p
 return {'bytes':s.st_size,'sha256':sha(p),'mode':stat.S_IMODE(s.st_mode),'kind':'file'}
def load(p):return json.loads(p.read_text())
def save(n,v):
 with (OUT/n).open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write("\n")
selection=load(SELECT/'selection.json');assert selection['runID']==RUNID
life=load(RUN/'runtime/lifecycle.json');assert life['cleanedUp'] and life['ownedDeviceAbsent'] and life['baselineStatesPreserved'] and life['secretConfigurationAbsent'] and len(life['cleanupResults'])==5 and all(r['passed'] for r in life['cleanupResults'])
assert life['ownedSimulator']==selection['ownedSimulatorIdentity']['udid']
assert not (Path('/Users/andreyyurlov/Library/Developer/CoreSimulator/Devices')/life['ownedSimulator']).exists()
scratch=load(RUN/'scratch-cleanup.json');assert scratch['verifiedBeforeRemoval'] and scratch['scratchAbsent'] and all(not Path(p).exists() for p in scratch['paths'])
outer=load(BASE/('outer-run-'+RUNID)/'receipt.json');assert outer['observationComplete'] and outer['ownedProcessGroupAbsent'] and not outer['outerTimeout'] and not outer['signals'] and outer['exitCode']==1
for n,r in outer['streams'].items():
 assert r['eof'] and r['observedBytes']==r['retainedBytes'];p=BASE/('outer-run-'+RUNID)/(n+'.log');assert p.stat().st_size==r['retainedBytes'] and sha(p)==r['retainedSHA256']
observer=load(RUN/'runtime/session/command-observer/observer.json');assert observer['exitCode']==65 and observer['ownedProcessGroup']['state']=='absent' and observer['outcome']=='command-exited-and-streams-EOF' and not observer['cleanup']['signals']
for n,r in observer['streams'].items():
 assert r['eof'] and not r['readerFailed'] and r['observedBytes']==r['retainedBytes'];p=RUN/'runtime/session/command-observer'/(n+'.log');assert p.stat().st_size==r['retainedBytes'] and sha(p)==r['retainedSHA256']
summary=load(RUN/'runtime/xctest-summary.json');assert summary['failedTests']==1 and summary['passedTests']==0 and summary['skippedTests']==1
local=load(RUN/'runtime/session/local-settings-first-failure.json');assert local['status']=='captured-safe-local-record' and local['rootSelectionSHA256']==sha(SELECT/'selection.json') and local['sourceObserverSHA256']==sha(RUN/'runtime/session/command-observer/observer.json') and local['supplementalOnly'] and not local['runPassed']
record=local['diagnostic']['record'];assert record['kind']=='chunk' and record['chunkIndex']==42 and record['chunkCount']==71 and record['requestOrdinal']==166 and record['overallDeadlineClipped'] and record['branch']=='semaphore-expiration' and 0<record['actualAllowanceSeconds']<0.009
files={str(p.relative_to(ROOT)):row(p) for p in sorted(RUN.rglob('*')) if p.is_file()}
save('native-files.json',files)
compact=['runtime/lifecycle.json','runtime/commands.json','runtime/xctest-summary.json','runtime/xctest-tests.json','runtime/runtime-verdict.json','runtime/session/local-settings-first-failure.json','runtime/session/command-observer/observer.json','runtime/session/command-observer/stdout.log','runtime/session/command-observer/stderr.log','runtime/session/configuration-derivation.json','runtime/captures/bridge-summary.json','runtime/attachment-export.json','scratch-cleanup.json','root-selection.json']
for n in compact:
 target=OUT/'retained'/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((RUN/n).read_bytes());assert sha(target)==sha(RUN/n)
verified={}
for n,expected in [('verification/apple-settings-instrumented-runtime-preparation/handoff.json','ca361bde1632c4ad4bbaf517817b9d8a5a9426a25d462738a9e03eeeb1786a3c'),('verification/apple-settings-instrumented-runtime-review/handoff.json','dbfcd7c074acbe63b27bd26a94d77f72c494fa4fdc8b0f9b6792aa2d83da049f')]:
 p=ROOT/n;assert sha(p)==expected;h=load(p)
 for member,binding in h['members'].items():assert row(ROOT/member)==binding,member
 verified[n]={'sha256':expected,'members':len(h['members'])}
verdict=load(RUN/'runtime/runtime-verdict.json')
save('receipt.json',{'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runID':RUNID,'rootSelectionSHA256':sha(SELECT/'selection.json'),'sourceRevisionLabel':'4a4d8b7301351247318424ed71a89ab41f0db2ca','sourceTreeSHA256':selection['sourceTreeSHA256'],'productArchiveSHA256':selection['productArchiveSHA256'],'environment':selection['ownedSimulatorIdentity'],'nativeFiles':len(files),'nativeFileBytes':sum(v['bytes'] for v in files.values()),'nativeManifestSHA256':sha(OUT/'native-files.json'),'frozenInputsUnchanged':verified,'outerExitCode':1,'xcodeExitCode':65,'outerElapsedSeconds':outer['elapsedSeconds'],'xcodeElapsedSeconds':observer['elapsedSeconds'],'bothCommandGroupsCompleteAndAbsent':True,'hostTimeout':False,'signals':[],'officialSummary':{'failed':1,'passed':0,'skipped':1},'supplementalFirstFailure':record,'nativeVerdictAccepted':False,'strictImporterReportingFailures':verdict['reportingFailures'],'cleanupOperationsPassed':5,'ownedSimulatorAbsent':True,'baselineDevicesPreserved':sum(map(len,selection['baselineDevices']['devices'].values())),'preparedScratchAbsent':True,'physicalPhones':'disconnected-deferred','gaAccepted':False,'limitations':['Settings failed; dependent Tab skipped.','Supplemental first-failure data identifies request and actual allowance; it does not prove causal server phase or native acceptance.','Raw xcresult/media/restored application retained locally with complete hashes; compact evidence copied.']})
print(json.dumps({'nativeFiles':len(files),'cleanupPassed':5,'ownedSimulatorAbsent':True,'firstFailureAllowanceMs':record['actualAllowanceSeconds']*1000,'status':'failed-native-evidence-collected'}))
