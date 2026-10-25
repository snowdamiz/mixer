#!/usr/bin/env python3
"""Bounded offline explanation and compact hash binding of one finished run."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PRODUCER = ROOT / 'verification/apple-focus-reference-runtime-v5-namespace-correction'
RUN_ID = 'e7108fc8-281b-4c59-831a-f3697609017d'
NATIVE = PRODUCER / ('native-run-v5-' + RUN_ID)
RUNTIME = NATIVE / 'runtime'


def stable(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def row(path, single_link=True):
    info = path.lstat()
    assert path.resolve() == path and stat.S_ISREG(info.st_mode) and (not single_link or info.st_nlink == 1)
    raw = path.read_bytes()
    result=dict(kind='file', mode=stat.S_IMODE(info.st_mode), bytes=len(raw), sha256=sha(raw))
    if not single_link:result['links']=info.st_nlink
    return result


def read(path):
    return json.loads(path.read_bytes())


def write(name, value):
    if (BASE/name).exists():
        assert (BASE/name).read_bytes()==stable(value), 'Preserve existing collection bytes: '+name
        return
    with (BASE/name).open('xb') as stream:
        stream.write(stable(value))


def main():
    handoff = PRODUCER/'handoff.json'
    assert row(handoff)['sha256'] == 'bfc528c7786e681f964e93e9f022bae13dc9dd0ebd8b9f343f44f1834004d631'
    frozen = read(handoff)
    assert len(frozen['members']) == 36
    assert sha(stable(frozen['members'])) == frozen['memberTreeSHA256']
    comparisons = {name: dict(expected=expected, actual=row(ROOT/name), passed=row(ROOT/name)==expected)
                   for name,expected in frozen['members'].items()}
    assert all(value['passed'] for value in comparisons.values())
    write('frozen-members-verification.json',dict(schema=1, handoff=row(handoff), members=comparisons,
          all36OriginalMembersUnchanged=True, aggregateFreezeVerifierNotRun=True,
          reason='New designed native output is outside the original frozen member inventory; no re-freeze'))
    importer_path = PRODUCER/'importer.py'
    assert row(importer_path)['sha256'] == '592a5063cbdac739a9ca09df4cf4b8e89469e3b370b14920e95ae4074159aae3'
    spec=importlib.util.spec_from_file_location('collected_official_importer',importer_path)
    importer=importlib.util.module_from_spec(spec);spec.loader.exec_module(importer)
    selection_path=ROOT/'verification/apple-focus-reference-v5-root-selection/selection.json'
    root=read(selection_path)
    summary=read(RUNTIME/'xctest-summary.json');tests=read(RUNTIME/'xctest-tests.json')
    observer=read(RUNTIME/'session/command-observer/observer.json')
    nodes=[]
    def visit(value):
        if isinstance(value,dict):
            if value.get('nodeType')=='Test Case':nodes.append(value)
            for item in value.values():visit(item)
        elif isinstance(value,list):
            for item in value:visit(item)
    visit(tests)
    predicates=[]
    def check(name,actual,expected):
        predicates.append(dict(predicate=name,actual=actual,expected=expected,
                               passed=type(actual) is type(expected) and actual==expected))
    identity=root['ownedSimulatorIdentity']
    check('exactly one official device',len(tests.get('devices',[])),1)
    check('exactly one official configuration',len(summary.get('devicesAndConfigurations',[])),1)
    configs=summary['devicesAndConfigurations']
    for label,device in [('tests',tests['devices'][0]),('summary',configs[0]['device'])]:
        for key,value in dict(deviceId=identity['udid'],deviceName=identity['name'],platform='iOS Simulator',
                              osVersion='26.5',osBuildNumber=identity['build'],architecture='arm64').items():
            check(label+'.device.'+key,device.get(key),value)
    check('official configuration identity',configs[0].get('testPlanConfiguration'),
          dict(configurationId='1',configurationName='Test Scheme Action'))
    check('exactly two official test nodes',len(nodes),2)
    seen=[];method_rows=[]
    for index,node in enumerate(nodes):
        method=next((method for method in importer.METHODS
                     if node.get('nodeIdentifier')=='ToggleUITests/'+method+'()'
                     and node.get('nodeIdentifierURL')==importer.PREFIX+method
                     and node.get('name')==method+'()'),None)
        check('node '+str(index)+' exact selected name/identifier/URL',method is not None,True)
        check('node '+str(index)+' nonduplicate',method not in seen,True)
        check('node '+str(index)+' result belongs to Passed/Failed',node.get('result') in ('Passed','Failed'),True)
        check('node '+str(index)+' closed failure children',type(node.get('children',[])) is list and all(
            type(child) is dict and set(child)=={'name','nodeType'} and child['nodeType']=='Failure Message'
            and type(child['name']) is str for child in node.get('children',[])),True)
        seen.append(method);method_rows.append(dict(method=method,node=node))
    check('exact selected method set',set(seen)==set(importer.METHODS),True)
    check('Settings must pass',nodes[0]['result'],'Passed')
    passed=sum(node.get('result')=='Passed' for node in nodes)
    for key,expected in [('totalTestCount',2),('passedTests',passed),('failedTests',2-passed),('skippedTests',0),('expectedFailures',0)]:
        check('summary.'+key,summary.get(key),expected)
        if key!='totalTestCount':check('configuration.'+key,configs[0].get(key),expected)
    check('summary result consistent with passed count',summary.get('result'),'Passed' if passed==2 else 'Failed')
    check('exit code consistent with passed count',observer['exitCode'],0 if passed==2 else 65)
    check('summary start numeric/nonnegative',importer.number(summary.get('startTime')),True)
    check('summary finish numeric/nonnegative',importer.number(summary.get('finishTime')),True)
    exact=importer.decimal_document((RUNTIME/'xctest-summary.json').read_bytes())
    start=importer.datetime_ns(root['selectedAtUTC'])
    check('exact official times within selected 660 second window',start<=importer.decimal_timestamp_ns(exact['startTime'])
          <importer.decimal_timestamp_ns(exact['finishTime'])<=start+660_000_000_000,True)
    try:
        importer.official_methods(summary,tests,root,observer['exitCode'],exact_summary=exact)
        replay=dict(raised=False)
    except ValueError as error:
        replay=dict(raised=True,type=type(error).__name__,message=str(error))
    owners=[]
    for group in read(RUNTIME/'attachments/manifest.json'):
        matches=[method for method in importer.METHODS if group.get('testIdentifier')=='ToggleUITests/'+method+'()'
                 and group.get('testIdentifierURL')==importer.PREFIX+method]
        owners.append(dict(testIdentifier=group.get('testIdentifier'),testIdentifierURL=group.get('testIdentifierURL'),
                           exactSelectedMethod=matches[0] if len(matches)==1 else None,attachmentCount=len(group.get('attachments',[]))))
    outcomes=[]
    for attempt in sorted((RUNTIME/'captures/.settings-attempts').iterdir()):
        outcome=read(attempt/'outcome.json')
        outcomes.append(dict(attemptID=attempt.name,outcome=outcome.get('outcome')))
    last=read(RUNTIME/'captures/0000-settings-0220.json')
    last['record'].pop('data',None)
    explanation=dict(schema=1,scope='Offline collection only; existing importer and exact raw official JSON; no parser correction',
        primaryFailure='Public Settings setup failed with bridge transport request timeout within existing 2 second budget',
        dependentInput='Skipped because Public Settings setup did not pass; reference Tab input remains unrun',
        selectedMethods=method_rows,officialMethodsPredicateComparisons=predicates,actualImporterReplay=replay,
        firstRejectedPredicate='second selected node result Skipped is outside Passed/Failed',
        additionalFailingPredicates=[p['predicate'] for p in predicates if not p['passed']],rawAttachmentOwners=owners,
        officialRunRawTimes={key:str(exact[key]) for key in ['startTime','finishTime']},
        officialRunUTCTimes={key:datetime.datetime.fromtimestamp(summary[key],datetime.timezone.utc).isoformat() for key in ['startTime','finishTime']},
        timedOutRequestID=None,timedOutRequestReason='Not explicitly identified by retained terminal logs; no inference from last commit',
        durableSettingsAttemptCount=len(outcomes),allDurableSettingsOutcomesCommitted=all(x['outcome']=='committed' for x in outcomes),
        lastCommittedSettingsRecord=last,diagnosticPassCredited=False,correctionStarted=False,nativeRetry=False)
    write('official-failure-explanation.json',explanation)
    all_rows={}
    for path in sorted(NATIVE.rglob('*')):
        info=path.lstat();name=str(path.relative_to(NATIVE))
        if stat.S_ISDIR(info.st_mode):all_rows[name]=dict(kind='directory',mode=stat.S_IMODE(info.st_mode))
        elif stat.S_ISLNK(info.st_mode):all_rows[name]=dict(kind='symlink',mode=stat.S_IMODE(info.st_mode),target=path.readlink().as_posix())
        else:all_rows[name]=row(path,single_link=False)
    selected=['root-selection.json','scratch-cleanup.json','runtime/runtime-verdict.json','runtime/lifecycle.json',
              'runtime/commands.json','runtime/xctest-summary.json','runtime/xctest-tests.json','runtime/attachments/manifest.json',
              'runtime/attachment-export.json','runtime/session/command-observer/observer.json',
              'runtime/session/command-observer/stdout.log','runtime/session/command-observer/stderr.log',
              'runtime/session/configuration-derivation.json','runtime/captures/bridge-summary.json','runtime/captures/0000-settings-0220.json']
    write('native-output-manifest.json',dict(schema=1,root=str(NATIVE),selectedFiles={name:all_rows[name] for name in selected},
        fullTreeSHA256=sha(stable(all_rows)),entryCount=len(all_rows),fileCount=sum(v['kind']=='file' for v in all_rows.values()),
        totalFileBytes=sum(v.get('bytes',0) for v in all_rows.values()),
        treeAlgorithm='SHA256 of UTF-8 json.dumps(rows,indent=2,sort_keys=True,allow_nan=False)+newline; rows contain every relative entry kind/mode and file bytes/sha256/link-count or symlink target',
        archivesCreated=0,productCopiesCreated=0))
    outer=read(BASE/('outer-run-'+RUN_ID)/'receipt.json');life=read(RUNTIME/'lifecycle.json')
    final=read(BASE/'final-inventory.json');config=read(RUNTIME/'session/configuration-derivation.json')
    assert outer['observationComplete'] and not outer['outerTimeout'] and outer['exitCode']==1
    assert life['cleanedUp'] and life['ownedDeviceAbsent'] and life['baselineStatesPreserved']
    assert final['ownedSimulatorAbsent'] and final['baselineStatesPreserved'] and final['unexpectedDevices']==[]
    assert config['retired'] and config['secretConfigurationAbsent']
    write('result.json',dict(schema=1,observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        command=[sys.executable,'-B',str(Path(__file__).resolve())],python=sys.version,runID=RUN_ID,
        status='Settings-precondition-failed; dependent reference input skipped; diagnostic outcome unknown',
        dispatcherExitCode=1,xcodebuildExitCode=65,outerSeconds=outer['elapsedSeconds'],nativeCommandSeconds=observer['ownedProcessGroup']['elapsedSeconds'],
        original36FrozenMembersUnchanged=True,cleanupResources=life['cleanupResults'],ownedSimulatorAbsent=True,
        baselinePreserved=True,secretConfigurationAbsent=True,sourceProductScratchAbsent=read(NATIVE/'scratch-cleanup.json')['scratchAbsent'],
        outerObservationComplete=True,outerTimeout=False,retryAttempted=False,diagnosticPassCredited=False,
        keyboardQualification=False,carrierAccepted=False,gaAccepted=False,physicalPhones='disconnected-deferred'))
    packet=read(PRODUCER/'packet.json')
    bindings={str(path.relative_to(ROOT)):row(path) for path in [PRODUCER/'packet.json',PRODUCER/'handoff.json',
        PRODUCER/'runtime-sources.tar.gz',PRODUCER/'runtime-source-manifest.json',importer_path,
        ROOT/'verification/apple-focus-reference-runtime-v5/packet.json',selection_path,
        ROOT/'verification/apple-focus-reference-v5-root-selection/execution-selection.json']}
    members={str(p.relative_to(ROOT)):row(p) for p in sorted(BASE.rglob('*')) if p.is_file() and p.name!='handoff.json'}
    document=ROOT/'docs/apple-focus-reference-v5-native.md';members[str(document.relative_to(ROOT))]=row(document)
    write('handoff.json',dict(schema=1,scope='One failed native Settings diagnostic and offline collection; no new packet/version/archive',
        members=members,memberTreeSHA256=sha(stable(members)),inputBindings=bindings,
        sourceRevisionLabel=packet['sourceRevisionLabel'],sourceRevisionMeaning=packet['sourceRevisionMeaning'],
        compileSourceTreeSHA256=root['sourceTreeSHA256'],selectedSourceTreeSHA256=packet['selectedSourceTreeSHA256'],
        nativeProductArchiveSHA256=root['productArchiveSHA256'],nativeProductManifestSHA256=packet['nativeProductManifestSHA256'],
        toolIdentityReceipt='verification/apple-focus-reference-v5-native/preparation-baseline/receipt.json',
        nativeOutputManifest='verification/apple-focus-reference-v5-native/native-output-manifest.json',
        diagnosticPassed=False,cleanupPassed=True,physicalPhones='disconnected-deferred',gaAccepted=False))
    print(json.dumps(dict(frozenMembersVerified=36,predicates=len(predicates),failedPredicates=explanation['additionalFailingPredicates'],
        nativeOutputFiles=sum(v['kind']=='file' for v in all_rows.values()),handoffSHA256=row(BASE/'handoff.json')['sha256']),indent=2))


if __name__=='__main__':
    main()
