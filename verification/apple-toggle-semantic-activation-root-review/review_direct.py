"""Preserve complete original direct API failures separately from native input."""
import datetime,hashlib,importlib.util,json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parents[2];OUT=pathlib.Path(__file__).resolve().parent;PRODUCER=ROOT/'verification/apple-toggle-semantic-activation';RUN=PRODUCER/'runtime-direct'
read=lambda p:json.loads(p.read_bytes());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
selection=read(OUT/'direct-selection.json')
for n,d in selection['bindings'].items():assert sha(ROOT/n)==d,n
for n,d in read(PRODUCER/'packet-seal.json')['files'].items():assert sha(ROOT/n)==d,n
life=read(RUN/'lifecycle.json');summary=read(RUN/'runtime-verdict.json');bridge=read(RUN/'captures/bridge-summary.json');official=read(RUN/'xctest-summary.json') if (RUN/'xctest-summary.json').exists() else None
assert life['verifiedHandoff']['sealSHA256']==selection['sealSHA256']
assert life['cleanedUp'] and life['ownedDeviceAbsent'] and life['baselineStatesPreserved'] and life['ephemeralWorkspaceAbsent']
assert all(v['passed'] for v in life['cleanupResults']) and not pathlib.Path(life['ephemeralWorkspace']['path']).exists()
assert life['beforeFrontends']==life['afterFrontends'] and summary['scope']=='direct'
spec=importlib.util.spec_from_file_location('root_direct_oracle',ROOT/'verification/apple-toggle-pan-origin-correction/oracle.py');oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
actions=[];operations=[];native=[]
for path in sorted((RUN/'captures').glob('*-after-*.json')):
 after=read(path);before=read(path.with_name(path.name.replace('-after-','-before-')));actual=after['verdict'];native.append(actual)
 replay=oracle.verdict(actual['candidate'],actual['case'],actual['action'],before['observation'],after['observation'],before['signature']!=after['signature'])
 assert all(actual[k]==v for k,v in replay.items()) and actual['ownedSimulatorIdentity']['udid']==life['ownedSimulator']
 checks=actual['originalChecks'];actions.append({'case':actual['case'],'passed':actual['passed'],'originalCheckCount':len(checks),'originalChecksPassed':sum(x['pass'] for x in checks),'originalChecks':checks,'predicates':actual['predicates'],'diagnosticSuiteState':after['observation'].get('diagnosticSuiteState')})
 for op in after['observation'].get('diagnosticOperations',[]):
  phases=['before','immediate','nextMainQueueTurn','settledAfter250ms'];fields=['identity','class','selected','primaryCount','valueCount','enabled','allowed','attachedToWindow']
  operations.append({'name':op['name'],'action':op['action'],'reference':op['reference'],'directReturn':op['directReturn'],'settledRequirementSatisfied':op['settledRequirementSatisfied'],'observations':{phase:{k:op[phase][k] for k in fields} for phase in phases}})
assert native==bridge['verdicts'];assert len(actions)==2 and {a['case']:a['originalCheckCount'] for a in actions}=={'diagnostic-direct':19,'comparator-direct':12}
assert summary['completeCaseSet'] and summary['bridgeFailures']==bridge['failures']==[]
assert not summary['runPassed']
if official is not None: assert official['totalTestCount']==2 and official['failedTests']==2 and official['skippedTests']==0
for op in operations:
 b=op['observations']['before'];a=op['observations']['settledAfter250ms']
 if op['name'] in ['carrier-primary-off-to-on','carrier-primary-on-to-off','carrier-accessibility-off-to-on','carrier-accessibility-on-to-off']:
  assert b['selected'] is not a['selected'] and a['primaryCount']==b['primaryCount']+1 and a['valueCount']==b['valueCount']+1
  if 'accessibility' in op['name']:assert op['directReturn'] is True
 if op['name'] in ['reference-primary-off-to-on','reference-primary-on-to-off']:
  assert b['selected']==a['selected'] and a['primaryCount']==b['primaryCount']+1
 if op['name'] in ['reference-accessibility-off-to-on','reference-accessibility-on-to-off']:
  assert op['directReturn'] is False and b['selected']==a['selected'] and b['primaryCount']==a['primaryCount'] and b['valueCount']==a['valueCount']
spec=importlib.util.spec_from_file_location('semantic_component_oracle',PRODUCER/'semantic_oracle.py');semantic=importlib.util.module_from_spec(spec);spec.loader.exec_module(semantic)
observed=[read(p) for p in sorted((RUN/'captures').glob('*-after-*.json')) if read(p)['verdict']['candidate']=='diagnostic'];assert len(observed)==1
semantic_result=semantic.verify(observed[0]['observation']['semanticOperations'])
assert {a['case']:a['originalChecksPassed'] for a in actions}=={'diagnostic-direct':15,'comparator-direct':10}
commands=read(RUN/'commands.json');text='\n'.join(x.get('stdout','') for x in commands)
methods=[{'method':n,'status':s,'seconds':float(t)} for n,s,t in re.findall(r"Test Case '-\[MixerToggleUITests.ToggleUITests (\w+)\]' (passed|failed) \(([0-9.]+) seconds\)\.",text)]
result={'schema':1,'status':'semantic36callback-components-pass-original-reference-suites-still-fail','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'environment':'iPhone17Pro iOS26.5(23F77) simulator; same sealed candidate as13passing interactions','actions':actions,'operations':operations,'xcodebuildExitCode':summary['xcodebuildExitCode'],'sessionFailure':summary['sessionFailure'],'interruptedCommands':[{'argv':x['argv'],'exitCode':x['exitCode'],'failureType':x['failureType']} for x in commands if x['kind']=='command-interrupted'],'semanticComponents':semantic_result,'xctestMethodsReported':methods,'officialSummary':official,'bridgeFailures':[],'completeCaseSet':True,'finding':'Authored carrier now commits exactly one value for primary/accessibility activation, and all36finite callback cases pass. Unchanged plain UIKit reference keeps its direct-call failures. Strict original suites and the overall XCTest run remain failed. Direct callbacks do not qualify physical VoiceOver.','cleanup':'All five cleanup operations pass, exact owned simulator deleted, capability workspace removed, baseline identities/states and frontends preserved.','ownedSimulator':life['ownedSimulator'],'originalSuiteAccepted':False,'semanticCallbackComponentsAccepted':True,'nativeInteractionRegressionReview':'runtime-review.json','fullCarrierAccepted':False,'gaAccepted':False,'bindings':{str(p.relative_to(ROOT)):sha(p) for p in sorted(RUN.rglob('*')) if p.is_file()}}
for p in [pathlib.Path(__file__),OUT/'direct-selection.json',PRODUCER/'semantic_oracle.py']:result['bindings'][str(p.relative_to(ROOT))]=sha(p)
(OUT/'direct-review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'checks':[{k:a[k] for k in ['case','originalCheckCount','originalChecksPassed','passed']} for a in actions],'semanticComponents':semantic_result,'xcodebuildExitCode':summary['xcodebuildExitCode'],'sessionFailure':summary['sessionFailure'],'cleanup':result['cleanup']}))
