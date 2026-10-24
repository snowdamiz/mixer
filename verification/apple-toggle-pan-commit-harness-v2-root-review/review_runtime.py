"""Independent offline replay of the selected native interaction attempt."""
import collections,datetime,hashlib,importlib.util,json,math,pathlib,re,sys
ROOT=pathlib.Path(__file__).resolve().parents[2];OUT=pathlib.Path(__file__).resolve().parent
PRODUCER=ROOT/'verification/apple-toggle-pan-commit-harness-v2';RUN=PRODUCER/'runtime';ORACLE=PRODUCER/'commit_oracle.py'
read=lambda p:json.loads(p.read_bytes());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
selection=read(OUT/'selection.json')
for name,digest in selection['bindings'].items():assert sha(ROOT/name)==digest,name
seal=read(PRODUCER/'packet-seal.json')
for name,digest in seal['files'].items():assert sha(ROOT/name)==digest,name
life=read(RUN/'lifecycle.json');summary=read(RUN/'runtime-verdict.json');bridge=read(RUN/'captures/bridge-summary.json')
assert life['verifiedHandoff']['sealSHA256']==selection['reviewedSealSHA256']
assert life['runtime']['buildversion']=='23F77'
assert life['cleanedUp'] and life['ownedDeviceAbsent'] and life['baselineStatesPreserved'] and life['ephemeralWorkspaceAbsent']
assert all(v['passed'] for v in life['cleanupResults']) and not pathlib.Path(life['ephemeralWorkspace']['path']).exists()
assert life['beforeFrontends']==life['afterFrontends']
module=importlib.util.spec_from_file_location('root_pan_origin_oracle',ORACLE);oracle=importlib.util.module_from_spec(module);module.loader.exec_module(oracle)
actions=[];native_verdicts=[]
for p in sorted((RUN/'captures').glob('*-after-*.json')):
 after=read(p);actual=after['verdict'];before=read(p.with_name(p.name.replace('-after-','-before-')))
 replay=oracle.verdict(actual['candidate'],actual['case'],actual['action'],before['observation'],after['observation'],before['signature']!=after['signature'])
 assert all(actual[k]==v for k,v in replay.items()),p.name
 assert actual['ownedSimulatorIdentity']['udid']==life['ownedSimulator']
 previous=max((x['sequence'] for x in before['observation'].get('diagnosticTrace',[])),default=0)
 delta=[x for x in after['observation'].get('diagnosticTrace',[]) if x['sequence']>previous]
 decisions=[x for x in delta if x['kind']=='shouldBeginDecision'];origin_proofs=[]
 if actual['action'] in {'authored-pan','native-pan-interruption','native-pan-commit'}:
  for d in decisions:
   c=[x for x in delta if x['kind']=='panOriginCapture' and x['attempt']==d.get('admissionAttempt') and x['sequence']<d['sequence']]
   t=[x for x in delta if x['kind']=='recognizerShouldReceiveTouch' and x['touchIdentity']==d.get('admissionTouchIdentity') and x['sequence']<d['sequence']]
   displacement=d.get('admissionDisplacementInWindow');origin=d.get('admissionOriginInWindow');current=d.get('admissionCurrentInWindow')
   point_valid=all(isinstance(v,dict) and set(v)=={'x','y'} and all(type(x) in (int,float) and math.isfinite(x) for x in v.values()) for v in [displacement,origin,current])
   predicates={
    'nativeAdmissionAccepted':d.get('result') is True and d.get('admissionReason')=='accepted',
    'oneOriginCapture':len(c)==1 and c[0]['invalidated'] is False,
    'originalNativeTouchMatched':len(t)==1 and t[0]['phase']==0 and t[0]['locationInWindow']==origin and t[0]['timestamp']==d.get('admissionOriginTimestamp'),
    'windowBindingAttemptMatched':len(c)==1 and c[0]['origin']==origin and c[0]['touchIdentity']==d.get('admissionTouchIdentity') and c[0]['windowIdentity']==d.get('admissionWindowIdentity') and c[0]['bindingGeneration']==d.get('admissionBindingGeneration') and d.get('admissionAttempt')==d.get('admissionOriginAttempt'),
    'finiteExactDisplacement':point_valid and all(math.isclose(displacement[k],current[k]-origin[k],abs_tol=1e-9) for k in ['x','y']),
    'frozen6Point1_2Policy':point_valid and abs(displacement['x'])>=6 and abs(displacement['x'])>abs(displacement['y'])*1.2,
    'currentFencesValid':d.get('admissionContextMatches') is True and d.get('admissionOriginGeometry')==d.get('admissionCurrentGeometry') and d.get('enabled') is True and d.get('inputAllowed') is True and d.get('gesture',{}).get('touchCount')==1 and d.get('admissionTouchPhase') in [0,1,2] and d.get('admissionTouchTimestamp',-1)>=d.get('admissionOriginTimestamp',0),
    'noInterveningReset':len(c)==1 and not any(x['kind']=='panOriginReset' and c[0]['sequence']<x['sequence']<d['sequence'] for x in delta),
    'nativeTerminalReset':any(x['kind']=='panOriginReset' and x['reason'] in ({'interaction-invalidated','native-pan-cancelled-or-failed'} if actual['action']=='native-pan-interruption' and oracle.interruption.SPECS[actual['case']]['mode']!='nochange' else {'native-pan-ended'}) and x['sequence']>d['sequence'] for x in delta),
   }
   origin_proofs.append({'predicates':predicates,'passed':all(predicates.values()),'decision':d})
 native_verdicts.append(actual)
 actions.append({'case':actual['case'],'action':actual['action'],'actionIndex':actual['actionIndex'],'passed':actual['passed'],'predicateCount':len(actual['predicates']),'failedPredicates':[k for k,v in actual['predicates'].items() if not v],'originProofs':origin_proofs,'nativeTraceCounts':dict(collections.Counter(x['kind'] for x in delta))})
assert bridge['verdicts']==native_verdicts
assert bridge['failures']==summary['bridgeFailures']
expected={k:2 if k.endswith('taps') else 1 for k in oracle.CASES}
counts=dict(collections.Counter(x['case'] for x in actions));complete=counts==expected
pan_proofs=[p for a in actions if a['action'] in {'authored-pan','native-pan-interruption','native-pan-commit'} for p in a['originProofs']]
origin_accepted=all(a['originProofs'] and all(p['passed'] for p in a['originProofs']) for a in actions if a['action'] in {'authored-pan','native-pan-interruption','native-pan-commit'}) and len([a for a in actions if a['action'] in {'authored-pan','native-pan-interruption','native-pan-commit'}])==36
commands=read(RUN/'commands.json');text='\n'.join(x.get('stdout','') for x in commands)
methods=[{'method':n,'status':s,'seconds':float(t)} for n,s,t in re.findall(r"Test Case '-\[MixerToggleUITests.ToggleUITests (\w+)\]' (passed|failed) \(([0-9.]+) seconds\)\.",text)]
interrupted=[x for x in commands if x['kind']=='command-interrupted'];official=read(RUN/'xctest-summary.json') if (RUN/'xctest-summary.json').exists() else None
accepted=complete and all(x['passed'] for x in actions) and origin_accepted and summary['runPassed'] is True and len(methods)==43 and {x['method'] for x in methods}==set(re.findall(r'^    func (test\w+)\(', (PRODUCER/'harness/UITests/ToggleUITests.swift').read_text(), re.M)) and official is not None and official['totalTestCount']==43 and official['passedTests']==43 and official['failedTests']==0 and official['skippedTests']==0 and all(x['status']=='passed' for x in methods)
result={'schema':1,'status':'accepted-private-native-pan-commit-and-regression-components' if accepted else 'reviewed-native-attempt-not-accepted','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(pathlib.Path(__file__).resolve())],'pythonVersion':sys.version,'sourceRevisionContext':{'baseRevision':selection['sourceRevisionContext'],'candidateSourceClosureSHA256':life['verifiedHandoff']['candidateSourceClosureSHA256'],'candidateArchiveSHA256':life['verifiedHandoff']['candidateArchiveSHA256']},'environment':'iPhone17Pro iOS26.5(23F77) simulator; SDK26.5/minimum26.0 candidate','actionEvaluations':len(actions),'passingActionEvaluations':sum(a['passed'] for a in actions),'originalPredicateAssertions':sum(a['predicateCount'] for a in actions),'originProofAssertions':sum(len(p['predicates']) for p in pan_proofs),'originProofPassed':origin_accepted,'completeCaseSet':complete,'actions':actions,'xcodebuildExitCode':summary['xcodebuildExitCode'],'interruptedExitCodes':[x['exitCode'] for x in interrupted],'xctestMethodsReported':methods,'officialSummary':official,'bridgeFailures':summary['bridgeFailures'],'sessionFailure':summary['sessionFailure'],'ownedSimulator':life['ownedSimulator'],'cleanup':'All independent cleanup passed; owned device absent; capability workspace removed; baseline states and frontends preserved.','acceptedPrivateInteractionSlice':accepted,'productionIntegrated':False,'fullCarrierAccepted':False,'gaAccepted':False,'pending':['Physical VoiceOver delivery is not established by direct accessibility callbacks', 'Other lifecycle retirements, including native window detach','Full native focus and keyboard delivery','Compositor parity','Live adapter integration','Physical final matrix including VoiceOver','Immutable external FieldLog consumption','GA'],'bindings':{str(p.relative_to(ROOT)):sha(p) for p in sorted(RUN.rglob('*')) if p.is_file()}}
for p in [pathlib.Path(__file__),OUT/'selection.json',PRODUCER/'host-controls.json']:result['bindings'][str(p.relative_to(ROOT))]=sha(p)
native_actions=[a for a in actions if a['action']!='direct-suite']
direct=[v for v in native_verdicts if v['action']=='direct-suite']
result.update(nativeActions=len(native_actions),directComponentResults=len(direct),semanticCallbackRows=sum(v['semanticComponents']['cases'] for v in direct),originalStrictDiagnosticPassed=[v['originalStrictVerdict']['passed'] for v in direct],originalReferenceFailures=[v['originalFailures'] for v in direct])
assert len(direct)==1 and direct[0]['originalStrictVerdict']['passed'] is False and len(direct[0]['originalFailures'])==4
if accepted: assert len(native_actions)==45 and result['semanticCallbackRows']==36
(OUT/'runtime-review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['actions','bindings','officialSummary']},indent=2))
