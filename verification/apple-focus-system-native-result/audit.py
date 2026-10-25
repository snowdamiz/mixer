#!/usr/bin/env python3
"""Read recorded V8 evidence; never import a runner, oracle, or supplemental join."""
import datetime
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tarfile
import time
import traceback

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
RUN_ID = 'd9a1ae2b-ef02-4db2-b2ff-4979213c8236'
PREP = ROOT / 'verification/apple-focus-system-runtime-preparation'
RUN = PREP / ('native-run-v8-' + RUN_ID)
RUNTIME = RUN / 'runtime'
SELECT = ROOT / 'verification/apple-focus-system-native-root-selection'
OUTER = ROOT / ('verification/apple-focus-system-native/outer-run-' + RUN_ID)
BUILD = ROOT / 'verification/apple-focus-system-native-build/attempt-1'
REPORT = ROOT / 'docs/apple-focus-system-native-result.md'
PACKET = '70dcc748cf67ce6573215b3815736aca4689707cc081d34c8069f9b5f13c3a82'
SOURCE = 'ddd4036d785c1c5f0161f8146ee7295b8df8dcd2bd615b45eebefc4112fcfb0d'
PRODUCT = '681059d32edbd63128c8f4552af2ed161d6dce05847397ffa6ce57b5402364d9'
ROOT_SELECTION = '9351a5263c9280cb790ec2fed613db03f1c1fec449a1bf1583bc6f8be9863276'
ORIGINAL_SELECTION = '1cee9899bcbd1739787a6ba991a82e6e1fb924f3225420640a82f2d4040ae8f3'
METHODS = ['test000PublicSettingsFullKeyboardAccess', 'test010ReferenceFirstTab']
RESOURCES = ['loopback-server-shutdown','loopback-server-close','loopback-thread-join',
             'ephemeral-capability-workspace-removal','owned-simulator-and-baseline-reconciliation']
INPUTS = {}


def stable(value): return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def require(value, message):
    if not value: raise ValueError(message)


def audit_boundary(event, args):
    if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.exec','os.posix_spawn','os.fork','os.forkpty','pty.spawn'}:
        raise PermissionError('Native-result audit cannot launch a process or use sockets')
    if event == 'open' and args and isinstance(args[0],(str,bytes)):
        path = Path(os.fsdecode(args[0])).resolve()
        require(not any(s in str(path).lower() for s in ['catalog-inspector','authority-driver','worker-transport']), 'Excluded lane')
        writing = (isinstance(args[1],str) and any(c in args[1] for c in 'wax+')) or len(args)>2 and isinstance(args[2],int) and bool(args[2] & (os.O_WRONLY|os.O_RDWR))
        if writing and not (path.is_relative_to(BASE) or path == REPORT):
            raise PermissionError('Cannot alter recorded native evidence or another lane')


def row(path):
    require(not any(s in str(path).lower() for s in ['catalog-inspector','authority-driver','worker-transport']), 'Excluded lane')
    info = path.lstat()
    require(path.resolve()==path and stat.S_ISREG(info.st_mode), 'Canonical regular evidence required: '+str(path))
    hasher=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''): hasher.update(block)
    return {'kind':'file','mode':stat.S_IMODE(info.st_mode),'bytes':info.st_size,
            'sha256':hasher.hexdigest(),'linkCount':info.st_nlink}


def bind(path, expected=None):
    observed=row(path)
    if isinstance(expected,str): require(observed['sha256']==expected,'Pinned SHA256 differs: '+str(path))
    elif expected is not None:
        require(all(observed[k]==v for k,v in expected.items()),'Pinned metadata differs: '+str(path))
    INPUTS[str(path.relative_to(ROOT))]=observed
    return observed


def read(path, expected=None):
    bind(path,expected)
    raw=path.read_bytes()
    require(len(raw)<=2_000_000,'Bounded JSON evidence required')
    def pairs(items):
        value={}
        for k,v in items:
            require(k not in value,'Duplicate JSON field')
            value[k]=v
        return value
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:require(False,'Nonfinite JSON'))


def tree(path):
    files={}; directories={}
    require(path.resolve()==path and path.is_dir() and not path.is_symlink(),'Canonical retained tree required')
    for item in sorted(path.rglob('*')):
        info=item.lstat();name=str(item.relative_to(path))
        require(item.resolve()==item and not item.is_symlink(),'Retained tree redirect')
        if stat.S_ISREG(info.st_mode): files[name]=row(item)
        else:
            require(stat.S_ISDIR(info.st_mode),'Unexpected retained tree member type')
            directories[name]={'mode':stat.S_IMODE(info.st_mode)}
    require(len(files)<5000 and sum(r['bytes'] for r in files.values())<256_000_000,'Bounded retained evidence tree')
    return {'root':str(path.relative_to(ROOT)),'files':files,'directories':directories,
            'fileTreeSHA256':sha(stable(files)),'filesCount':len(files),'totalBytes':sum(r['bytes'] for r in files.values())}


def command_argv(root):
    session=RUNTIME/'session'
    return [root['developerDirectory']+'/usr/bin/xcodebuild','test-without-building','-xctestrun',str(session/'session.xctestrun'),
            '-destination','platform=iOS Simulator,id='+root['ownedSimulatorIdentity']['udid'],
            '-parallel-testing-enabled','NO','-maximum-concurrent-test-simulator-destinations','1',
            '-resultBundlePath',str(session/'session.xcresult')]+['-only-testing:MixerToggleUITests/ToggleUITests/'+m for m in METHODS]


def states(devices):
    return {v['udid']:v['state'] for rows in devices['devices'].values() for v in rows}


def observed_methods(tests):
    found=[]
    def visit(v):
        if isinstance(v,dict):
            if v.get('nodeType')=='Test Case': found.append(v)
            for x in v.values(): visit(x)
        elif isinstance(v,list):
            for x in v:visit(x)
    visit(tests)
    require(len(found)==2,'Exactly two actual test executions, no retries')
    result={}
    for node in found:
        method=next((m for m in METHODS if node.get('name')==m+'()' and node.get('nodeIdentifier')=='ToggleUITests/'+m+'()'
                     and node.get('nodeIdentifierURL')=='test://com.apple.xcode/MixerToggleUITests/MixerToggleUITests/ToggleUITests/'+m),None)
        require(method and method not in result,'Foreign or duplicate method')
        result[method]=node['result']
    require(result==dict(zip(METHODS,['Passed','Failed'])),'Recorded official outcome differs')
    return result


def source_slices():
    manifest=read(BUILD/'source-manifest.json')
    require(len(manifest['sources'])==40 and sha(stable(manifest['sources']))==SOURCE,'Compile source closure differs')
    bind(BUILD/'sources.tar.gz',manifest['archive']['sha256'])
    product=read(BUILD/'product-manifest.json')
    require(product['archive']['sha256']==PRODUCT and len(product['products'])==55
            and sha(stable(product['products']))==product['productTreeSHA256']=='6966d9d0e83fb4552a9b5b6611cea897a9402bb048dc1bdb45562cbd5bedf3f1',
            'Fresh product identity differs')
    bind(BUILD/'products.tar.gz',PRODUCT)
    bind(ROOT/'verification/apple-focus-system-observation/review-source-package.tar.gz',
         'd1262c1e16a4decdca0ecbfdc278b7eaa1282f47d68776bfdede235157019cda')
    slices=[]
    with tarfile.open(BUILD/'sources.tar.gz','r:gz') as stream:
        for name,ranges in [('source/Prototype/main.swift',[(48,52),(285,296)]),
                            ('harness/UITests/ToggleUITests.swift',[(333,341),(409,423),(471,474)])]:
            member=stream.getmember(name);raw=stream.extractfile(member).read();expected=manifest['sources'][name]
            require(member.isfile() and member.mode==expected['mode']==0o444
                    and len(raw)==expected['bytes'] and sha(raw)==expected['sha256'],'Selected source member differs')
            lines=raw.decode().splitlines()
            for start,end in ranges:
                slices.append({'archive':str((BUILD/'sources.tar.gz').relative_to(ROOT)),
                               'archiveSHA256':manifest['archive']['sha256'],'member':name,'memberSHA256':sha(raw),
                               'lineStart':start,'lineEnd':end,'lines':lines[start-1:end]})
    return {'schema':1,'scope':'Exact selected source excerpts read as data only; no compilation or execution','slices':slices}


def inspect():
    originals=read(SELECT/'original-selection.json',ORIGINAL_SELECTION)
    root=read(SELECT/'selection.json',ROOT_SELECTION)
    require((RUN/'root-selection.json').read_bytes()==(SELECT/'selection.json').read_bytes(),'Dispatch root selection bytes differ')
    bind(RUN/'root-selection.json',ROOT_SELECTION)
    require(root['runID']==RUN_ID and root['schema']=='mixer.apple-focus-reference-root-selection.8'
            and root['packetSHA256']==PACKET and root['sourceTreeSHA256']==SOURCE and root['productArchiveSHA256']==PRODUCT,
            'Root source/product/run selection differs')
    identity=root['ownedSimulatorIdentity'];argv=command_argv(root)
    require(identity=={'udid':'9CDA64A8-4057-4327-99B1-2ECE73C07EC2','name':'MixerFocusReferenceV8-d9a1ae2b',
                       'runtime':'com.apple.CoreSimulator.SimRuntime.iOS-26-5','build':'23F77'},'Native environment differs')
    require(originals['runID']==RUN_ID and originals['rootSelectionSHA256']==ROOT_SELECTION
            and originals['rawOriginalModeAfterSelection']==0o444,'Immutable original selection differs')
    expected_roles={'before':'0001-before-1.json','after':'0001-after-1.json','witness':'0001-keyboard-witness-1.json'}
    data={}
    require(set(originals['originals'])==set(expected_roles),'Exact separately selected original roles required')
    for role,name in expected_roles.items():
        selected=originals['originals'][role];path=RUNTIME/'captures'/name
        require(selected['path']==str(path.relative_to(ROOT)) and selected['mode']==0o644,'Original collection path/mode differs')
        observed=bind(path,{'bytes':selected['bytes'],'sha256':selected['sha256'],'mode':0o444,'linkCount':1})
        data[role]=read(path)
    packet=read(PREP/'packet.json',PACKET)
    require(packet['runtimeSourceTreeSHA256']=='4ed156befa6fd0d74c57a72b7be5a2181f763dab4c30851578a50d8a49a13a9b','Runtime closure differs')
    bind(PREP/'runtime-sources.tar.gz','d21f0fa805d33648c43ed094f304c82896a34e67b754aa96711c0ca85c563e92')
    for name,digest in [('verification/apple-focus-system-runtime-preparation/handoff.json','20dd17885f3c9b923465299da1cff9044ae178cb448b026c531552be87f332c5'),
                        ('verification/apple-focus-system-runtime-review/handoff.json','874ce792b4353f5b8ae21a5e08ea655c7909ba5111a104a28708caed600c8d89')]:
        handoff=read(ROOT/name,digest)
        for member,expected in handoff['members'].items():bind(ROOT/member,expected)
    selection=read(SELECT/'execution-selection.json')
    require(selection['attemptsAuthorized']==1 and selection['rootSelectionSHA256']==ROOT_SELECTION,'Single native attempt selection differs')
    bind(SELECT/'select_native.py',selection['selectionDriverSHA256'])
    bind(ROOT/'verification/apple-focus-system-native/observe_dispatch.py',selection['driverSHA256'])
    outer=read(OUTER/'receipt.json')
    require(outer['runID']==RUN_ID and outer['rootSelectionSHA256']==ROOT_SELECTION and outer['exitCode']==0
            and outer['observationComplete'] is True and outer['outerTimeout'] is False and outer['observationError'] is None
            and outer['ownedProcessGroupAbsent'] is True and outer['retryAttempted'] is False
            and outer['sourceTreeSHA256']==SOURCE and outer['productArchiveSHA256']==PRODUCT
            and outer['driverSHA256']==selection['driverSHA256'],'Outer observed execution differs')
    for stream,expected in outer['streams'].items():
        bind(OUTER/(stream+'.log'),{'bytes':expected['retainedBytes'],'sha256':expected['retainedSHA256']})
        require(expected['eof'] is True and expected['observedBytes']==expected['retainedBytes'],'Outer stream incomplete')
    marker=read(PREP/('dispatch-attempts/'+RUN_ID+'.json'))
    require(marker['runID']==RUN_ID and marker['packetSHA256']==PACKET and marker['rootSelectionSHA256']==ROOT_SELECTION
            and marker['oneAttemptOnly'] is True,'Durable attempt marker differs')
    observer=read(RUNTIME/'session/command-observer/observer.json')
    require(observer['argv']==argv and observer['exitCode']==65 and observer['startNewSession'] is True
            and observer['successInferredFromConsoleOrMarkers'] is False and observer['timeoutSeconds']==600
            and observer['ownedProcessGroup']['state']=='absent','Selected native command terminal outcome differs')
    require(observer['PID']==observer['processGroup']==observer['ownedProcessGroup']['targetProcessGroup'],'Native owned group differs')
    for stream,expected in observer['streams'].items():
        bind(RUNTIME/('session/command-observer/'+stream+'.log'),{'bytes':expected['retainedBytes'],'sha256':expected['retainedSHA256']})
        require(expected['observedBytes']==expected['retainedBytes'] and expected['eof'] is True
                and expected['readerFailed'] is False and expected['readerErrors']==[],'Native observer stream incomplete')
    official=read(RUNTIME/'official-capture.json')
    require(official['runID']==RUN_ID and official['rootSelectionSHA256']==ROOT_SELECTION and official['argv']==argv,'Official capture selection differs')
    session=RUNTIME/'session';result_path=session/'session.xcresult'
    for path,key in [(session,'sessionIdentity'),(result_path,'resultIdentity')]:
        info=path.lstat();require(path.resolve()==path and path.is_dir() and [info.st_dev,info.st_ino,info.st_uid]==official[key],'Retained native directory identity differs')
    official_data={}
    for role,name in [('summary','xctest-summary.json'),('tests','xctest-tests.json'),('manifest','attachments/manifest.json')]:
        official_data[role]=read(RUNTIME/name,official['officialSHA256'][role])
    summary=official_data['summary'];methods=observed_methods(official_data['tests'])
    require({k:summary[k] for k in ['totalTestCount','passedTests','failedTests','skippedTests','expectedFailures']}==
            {'totalTestCount':2,'passedTests':1,'failedTests':1,'skippedTests':0,'expectedFailures':0}
            and summary['result']=='Failed','Official totals differ')
    for device in official_data['tests']['devices']:
        require(device['deviceId']==identity['udid'] and device['deviceName']==identity['name']
                and device['osVersion']=='26.5' and device['osBuildNumber']=='23F77' and device['architecture']=='arm64','Official selected device differs')
    require(len(official_data['tests']['devices'])==1,'One actual device required')
    exact=json.loads((RUNTIME/'xctest-summary.json').read_bytes(),parse_float=Decimal,parse_int=Decimal)
    stamp=datetime.datetime.fromisoformat(root['selectedAtUTC']);delta=stamp-datetime.datetime(1970,1,1,tzinfo=datetime.timezone.utc)
    start=Decimal(delta.days*86400+delta.seconds)+Decimal(delta.microseconds)/1_000_000
    require(start<=exact['startTime']<exact['finishTime']<=start+660,'Official selected run wall ordering differs')
    export=read(RUNTIME/'attachment-export.json')
    require(export['passed'] is True and export['exitCode']==0 and export['ownedResultPath']==str(result_path),'Official export failed')
    require(set(export['files'])=={p.name for p in (RUNTIME/'attachments').iterdir()},'Official export inventory differs')
    for name,digest in official['payloadSHA256'].items():bind(RUNTIME/'attachments'/name,digest)
    for name,expected in export['files'].items():bind(RUNTIME/'attachments'/name,expected)
    for role,name in {'begin':'0001-begin.json',**expected_roles}.items():bind(RUNTIME/'captures'/name,official['applicationCaptureSHA256'][role])
    verdict=read(RUNTIME/'runtime-verdict.json')
    require(verdict['runID']==RUN_ID and verdict['sourceTreeSHA256']==SOURCE and verdict['productArchiveSHA256']==PRODUCT
            and verdict['officialMethodResults']==methods and verdict['xcodebuildExitCode']==65 and verdict['provenanceAccepted'] is True
            and verdict['diagnosticOutcome']=='one-strict-original-verdict-failed' and verdict['actualNativeInputActions']==verdict['keyInjectionCount']==1
            and verdict['sessionFailure'] is None and verdict['bridgeFailures']==[] and verdict['reportingFailures']==[], 'Recorded strict import differs')
    for flag in ['runPassed','strictNativeVerdictsPassed','singleTabDiagnosticEvidencePassed','carrierAccepted','gaAccepted',
                 'completeCaseSet','cursorCompletionCredit','fullSixCaseQualification','nativeKeyboardQualification']:
        require(verdict[flag] is False,'Failed diagnostic cannot grant completion: '+flag)
    original=data['after']['verdict'];witness=data['witness']['witness']
    require(stable(original)==stable(verdict['classification']['originalOracleResults'][0]),'Retained original verdict differs from imported original')
    require(stable(original['keyboardWitness'])==stable(witness) and stable(original['keyboardBinding'])==stable(data['witness']['binding']),'Original witness/binding differs')
    for role,detail in verdict['authoritativeAttachments'].items():
        path=RUNTIME/'attachments'/detail['file'];bind(path,detail['sha256'])
        if role=='verdict':require(stable(read(path))==stable(original),'Official original verdict differs')
        if role=='witness':require(stable(read(path))==stable(witness),'Official key witness differs')
    failed=[k for k,v in original['predicates'].items() if v is False]
    require(failed==['actualNativeFocusTraversal'] and all(type(v) is bool for v in original['predicates'].values())
            and original['passed'] is False and original['originalOraclePassed'] is False,'Strict failure category differs')
    require(witness['returned'] is True and witness['key']=='tab' and witness['publicAPI']=='XCUIElement.typeKey(_:modifierFlags:)'
            and witness['generation']==witness['actionIndex']==1 and witness['phase']=='acquire','One returned public acquisition Tab required')
    require(witness['before']['elements']['plain-uibutton-reference']['hasFocus'] is True
            and all(v['hasFocus'] is False for v in witness['after']['elements'].values()),'Reference-to-no-fixed-target observation differs')
    require(original['pairedFocusDisagreement'] is False and original['missingAppFocusUpdateSignal'] is False,'Focus-pairing/signal category differs')
    lifecycle=read(RUNTIME/'lifecycle.json');cleanup=[{'resource':x,'passed':True} for x in RESOURCES]
    require(lifecycle['cleanupResults']==verdict['cleanupResults']==cleanup and lifecycle['cleanedUp'] is True
            and lifecycle['ownedSimulator']==identity['udid'] and lifecycle['ownedDeviceAbsent'] is True
            and lifecycle['baselineStatesPreserved'] is True and lifecycle['nativeDeviceCleanupPassed'] is True,'Five native cleanup checks differ')
    require(states(lifecycle['before'])==states(root['baselineDevices'])==states(lifecycle['after'])
            and identity['udid'] not in states(lifecycle['after'])
            and lifecycle['beforeFrontends']==root['baselineFrontends']==lifecycle['afterFrontends'],'Recorded baseline preservation differs')
    commands=read(RUNTIME/'commands.json')
    selected_commands=[x for x in commands if x.get('argv')==argv]
    require(len(selected_commands)==1 and selected_commands[0]['exitCode']==65,'Exactly one selected XCTest command required')
    final_list=[x for x in commands if x.get('argv')==['/usr/bin/xcrun','simctl','list','devices','--json']][-1]
    require(final_list['exitCode']==0 and states(json.loads(final_list['stdout']))==states(lifecycle['after']),'Recorded final native inventory differs')
    for action in ['shutdown','delete']:
        recorded=[x for x in commands if x.get('argv')==['/usr/bin/xcrun','simctl',action,identity['udid']]]
        require(len(recorded)==1 and recorded[0]['exitCode']==0,'Recorded owned cleanup command differs')
    retirement=read(RUNTIME/'session/configuration-derivation.json')
    require(retirement['retired'] is True and retirement['secretConfigurationAbsent'] is True
            and retirement['compiledProductsUnchanged'] is True and not (session/'session.xctestrun').exists(),'Capability configuration retirement differs')
    scratch=read(RUN/'scratch-cleanup.json')
    require(scratch['scratchAbsent'] is True and scratch['verifiedBeforeRemoval'] is True
            and scratch['paths']==[str(RUN/'products'),str(RUN/'selected')]
            and not (RUN/'products').exists() and not (RUN/'selected').exists(),'Recorded source/product retirement differs')
    settings=verdict['settingsDiagnostic']
    require(settings['setupObservationSatisfied'] is True and settings['settingsEvidenceComplete'] is True
            and settings['persistenceUncertain'] is False and settings['persistenceRetirementPending'] is False
            and settings['terminationMarkers']==['terminate-before','terminate-after']
            and settings['completionMarkers']==['test-case-finished'],'Durable Settings completion differs')
    before=data['before']['observation'];after=data['after']['observation']
    b=before['focusSystemDiagnostic'];a=after['focusSystemDiagnostic']
    for value,count in [(b,27),(a,32)]:
        require(value['schema']=='mixer.apple-toggle.focus-system.1' and value['authoritative'] is False and value['atomic'] is False
                and value['captureStatus']=='complete' and value['dropped']==0 and value['revision']==count
                and len(value['entries'])==count and [r['sequence'] for r in value['entries']]==list(range(1,count+1)),
                'Bounded supplemental focus packet shape differs')
    require(stable(a['entries'][:27])==stable(b['entries']),'Supplemental prefix differs')
    selected_rows=[]
    for role,indices in [('before',[26]),('after',list(range(27,32)))]:
        observation=before if role=='before' else after
        for index in indices:
            entry=observation['focusSystemDiagnostic']['entries'][index]
            require([r['slot'] for r in entry['controls']]==['authored-toggle','plain-uibutton-reference','next-focus'], 'Supplemental fixed-slot order differs')
            selected_rows.append({'originalRole':role,'sourcePath':originals['originals'][role]['path'],
                                  'sourceSHA256':originals['originals'][role]['sha256'],
                                  'pointer':'/observation/focusSystemDiagnostic/entries/'+str(index),'value':entry})
    require([r['value']['system']['item']['state'] for r in selected_rows]==['fixed','null','unavailable','fixed','null','unavailable'],
            'Supplemental focus transitions differ')
    contexts=[]
    require(len(after['focusContexts'])==4 and len(before['focusContexts'])==1,'Supplemental callback counts differ')
    for index in [1,2,3]:
        context=after['focusContexts'][index]
        require(context['sequence']==index+1 and context['source']=='controller' and context['heading']==0,'Supplemental callback identity differs')
        contexts.append({'originalRole':'after','sourcePath':originals['originals']['after']['path'],
                         'sourceSHA256':originals['originals']['after']['sha256'],
                         'pointer':'/observation/focusContexts/'+str(index),'value':context})
    supplemental={'schema':1,'scope':'Bounded literal extraction from separately selected immutable V8 originals; no frozen V7 join, anchor or oracle execution',
                  'authoritative':False,'atomic':False,'nativeSuccessInferred':False,'originalSelectionSHA256':ORIGINAL_SELECTION,
                  'keyIntervalPointer':'/witness','keySourcePath':originals['originals']['witness']['path'],
                  'keySourceSHA256':originals['originals']['witness']['sha256'],
                  'keyStartedUptime':witness['startedUptime'],'keyFinishedUptime':witness['finishedUptime'],
                  'beforeEntries':27,'afterEntries':32,'focusSystemRows':selected_rows,'controllerContextRows':contexts,
                  'interpretation':'Samples record loss of the plain reference, brief reacquisition of the same reference with a different system identity, then loss again. They do not establish the cause or a successful traversal.'}
    result={'schema':1,'status':'completed-native-attempt-with-failed-original-verdict','runID':RUN_ID,
            'auditPassed':True,'nativePassed':False,'officialMethods':methods,'officialTotals':{k:summary[k] for k in ['totalTestCount','passedTests','failedTests','skippedTests','expectedFailures']},
            'outerDispatchExitCode':0,'xcodebuildExitCode':65,'failureCategory':'actual-native-focus-traversal-failed-from-plain-reference',
            'failedOriginalPredicates':failed,'otherOriginalPredicatesPassed':len(original['predicates'])-1,
            'pairedFocusDisagreement':False,'missingAppFocusUpdateSignal':False,'actualNativeInputActions':1,
            'observedFocusBefore':'plain-uibutton-reference','observedFocusAfter':None,
            'settings':{'requests':settings['requests'],'uploads':len(settings['uploads']),'decodedBytesDeclared':settings['decodedBytesDeclared'],
                        'setupObservationSatisfied':True,'settingsEvidenceComplete':True,'persistenceUncertain':False},
            'cleanupResults':cleanup,'ownedDeviceAbsentInRecordedFinalInventory':True,'baselineStatesPreserved':True,
            'preservedBaselineDeviceCount':len(states(lifecycle['before'])),'baselineFrontendsPreserved':True,
            'capabilityConfigurationAbsent':True,'sourceAndProductScratchAbsent':True,
            'packetSHA256':PACKET,'sourceTreeSHA256':SOURCE,'productArchiveSHA256':PRODUCT,
            'rootSelectionSHA256':ROOT_SELECTION,'originalSelectionSHA256':ORIGINAL_SELECTION,
            'originalCollectionMode':0o644,'originalCurrentMode':0o444,'sourceRevisionReportedByRoot':'6403eea98031207f6e40a72b55dfd3bd4e7e6ec2',
            'nativeEnvironment':identity,'architecture':'arm64','xcode':'26.6 (17F113)','SDK':'26.5','minimumIOS':'26.0',
            'frozenV7JoinImportedOrExecuted':False,'newSupplementalAnchorCreated':False,'nativeQueriesDuringAudit':0,
            'nativeExecutionDuringAudit':False,'networkOrChildProcessDuringAudit':False,'physicalPhones':'disconnected-deferred',
            'carrierAccepted':False,'nativeKeyboardQualification':False,'gaAccepted':False,
            'nextAction':'Investigate the unchanged plain-reference app/window and public-key delivery contract: PrototypeDelegate UIWindow creation/key-window and scene association, PrototypeController.preferredFocusEnvironments/controller callbacks, and launchCase -> XCUIApplication.typeKey. The recorded system-identity turnover around the plain UIButton reference precedes any supported claim of an authored-component defect. Cause remains unproven; preserve the original oracle/actions/budgets.'}
    return result,supplemental,source_slices()


def inventory():
    return {str(REPORT.relative_to(ROOT)):row(REPORT),**{str(p.relative_to(ROOT)):row(p) for p in sorted(BASE.rglob('*'))
            if p.is_file() and p.name not in {'handoff.json','handoff.sha256'} and not p.is_relative_to(BASE/'commands/seal')
            and not p.is_relative_to(BASE/'commands/verify')}}


def main(action):
    if action=='build':
        require(not (BASE/'result.json').exists(),'Preserve first audited result')
        result,supplemental,slices=inspect()
        snapshots={'nativeAttempt':tree(RUN),'rootSelectionEvidence':tree(SELECT),'outerObservation':tree(OUTER)}
        # Re-read every retained tree before publishing the audit; no raw evidence is copied.
        require(snapshots=={'nativeAttempt':tree(RUN),'rootSelectionEvidence':tree(SELECT),'outerObservation':tree(OUTER)},'Evidence changed during audit')
        for name,expected in INPUTS.items(): require(row(ROOT/name)==expected,'Bound evidence changed during audit')
        for name,value in [('result.json',result),('supplemental-extract.json',supplemental),('source-slices.json',slices),
                           ('input-bindings.json',INPUTS),('native-evidence-manifest.json',snapshots)]:
            (BASE/name).write_bytes(stable(value))
        return {'auditPassed':True,'nativePassed':False,'nativeFiles':snapshots['nativeAttempt']['filesCount'],
                'failureCategory':result['failureCategory'],'nativeExecutionDuringAudit':False}
    result,supplemental,slices=inspect()
    require(stable(result)==(BASE/'result.json').read_bytes() and stable(supplemental)==(BASE/'supplemental-extract.json').read_bytes()
            and stable(slices)==(BASE/'source-slices.json').read_bytes(),'Audited result/extraction differs')
    bindings=json.loads((BASE/'input-bindings.json').read_bytes())
    for name,expected in bindings.items():require(row(ROOT/name)==expected,'Bound input differs: '+name)
    snapshots=json.loads((BASE/'native-evidence-manifest.json').read_bytes())
    require(snapshots=={'nativeAttempt':tree(RUN),'rootSelectionEvidence':tree(SELECT),'outerObservation':tree(OUTER)},'Complete recorded native inventory differs')
    if action=='seal':
        require(not (BASE/'handoff.json').exists(),'Preserve first native-result seal')
        members=inventory();handoff={'schema':1,'status':result['status'],'members':members,'memberTreeSHA256':sha(stable(members)),
                                  'runID':RUN_ID,'originalSelectionSHA256':ORIGINAL_SELECTION,'auditPassed':True,'nativePassed':False,
                                  'nativeExecutionDuringAudit':False,'physicalPhones':'disconnected-deferred','gaAccepted':False}
        (BASE/'handoff.json').write_bytes(stable(handoff));(BASE/'handoff.sha256').write_text(sha(stable(handoff))+'  handoff.json\n')
    else:
        handoff=json.loads((BASE/'handoff.json').read_bytes())
        require(handoff['memberTreeSHA256']==sha(stable(handoff['members'])) and handoff['members']==inventory(),'Sealed report inventory differs')
    return {'auditPassed':True,'nativePassed':False,'handoffSHA256':sha((BASE/'handoff.json').read_bytes()),
            'members':len(handoff['members']),'recordedNativeFiles':snapshots['nativeAttempt']['filesCount'],'nativeExecutionDuringAudit':False}


if __name__=='__main__':
    sys.addaudithook(audit_boundary)
    action=sys.argv[1];require(action in {'build','seal','verify'},'Bound audit action')
    started=time.monotonic();code=0;error='';output=''
    try:output=json.dumps(main(action),sort_keys=True)+'\n'
    except BaseException:
        code=1;error=traceback.format_exc()
    # Read-only verification makes no receipt writes. Build/seal retain their
    # exact streams and source/tool identities, outside seal circularity.
    if action!='verify':
        folder=BASE/'commands'/action;folder.mkdir(parents=True,exist_ok=False)
        (folder/'stdout.log').write_text(output);(folder/'stderr.log').write_text(error)
        receipt={'schema':1,'argv':[sys.executable,'-B',str(Path(__file__).resolve()),action],'cwd':str(Path.cwd()),
                 'python':sys.version,'pythonExecutable':str(Path(sys.executable).resolve()),
                 'pythonExecutableSHA256':sha(Path(sys.executable).resolve().read_bytes()),'sourceSHA256':sha(Path(__file__).read_bytes()),
                 'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsedSeconds':time.monotonic()-started,
                 'exitCode':code,'streams':{n:{'bytes':len(v.encode()),'sha256':sha(v.encode()),'eof':True} for n,v in [('stdout',output),('stderr',error)]},
                 'scope':'One host Python evidence audit; no child, native tool, device query, network or selected-module import',
                 'nativeExecutionDuringAudit':False}
        (folder/'receipt.json').write_bytes(stable(receipt))
    sys.stdout.write(output);sys.stderr.write(error)
    raise SystemExit(code)
