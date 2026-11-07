#!/usr/bin/env python3
"""Seal observed R2 results and retain bulky evidence outside Git. No native calls."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import stat
import sys

HERE = Path(__file__).resolve().parent
RESOURCES = ['loopback-server-shutdown','loopback-server-close','loopback-thread-join',
             'ephemeral-capability-workspace-removal','owned-simulator-and-baseline-reconciliation']

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def stable(value):
    return (json.dumps(value,indent=2,sort_keys=True)+'\n').encode()

def read(path):
    return json.loads(path.read_bytes())

def write(path,value):
    with path.open('xb') as stream:
        stream.write(stable(value))

def row(path):
    assert not path.is_symlink() and path.is_file(), str(path)
    raw=path.read_bytes()
    return dict(bytes=len(raw),sha256=sha(raw),mode=stat.S_IMODE(path.stat().st_mode))

def inventory(base):
    result={}
    for path in sorted(base.rglob('*')):
        assert not path.is_symlink(),str(path)
        if path.is_file():result[str(path.relative_to(base))]=row(path)
    return result

def seal():
    materialized=read(HERE/'materialization.json')
    scratch=Path(materialized['scratch'])
    assert scratch.resolve()==scratch and scratch.name.startswith('mixer-20261107-apple-settings-runtime-')
    outer=read(HERE/'attempt-result.json')
    selected=read(HERE/'root-selection.json')
    run=scratch/('native-run-v9-'+selected['runID'])
    runtime=run/'runtime'
    methods={}
    def walk(value):
        if isinstance(value,dict):
            if value.get('nodeType')=='Test Case':
                assert value['name'] not in methods
                methods[value['name']]=value['result']
            for child in value.values():walk(child)
        elif isinstance(value,list):
            for child in value:walk(child)
    tests=runtime/'xctest-tests.json'
    if tests.exists():walk(read(tests))
    lifecycle=read(runtime/'lifecycle.json') if (runtime/'lifecycle.json').exists() else {}
    verdict=read(runtime/'runtime-verdict.json') if (runtime/'runtime-verdict.json').exists() else {}
    observer_path=runtime/'session/command-observer/observer.json'
    observer=read(observer_path) if observer_path.exists() else {}
    scratch_cleanup=read(run/'scratch-cleanup.json') if (run/'scratch-cleanup.json').exists() else {}
    clean={r['resource']:r for r in lifecycle.get('cleanupResults',[])}
    cleanup=[clean.get(n,dict(resource=n,passed=False,status='Not recorded; no pass inferred')) for n in RESOURCES]
    captures=runtime/'captures'
    records=[read(p) for p in sorted(captures.glob('0000-settings-*.json'))]
    start=next((r for r in records if r['record']['kind']=='start'),None)
    observations={r['record']['stage']:r for r in records if r['record']['kind']=='observe'}
    terminal=observations.get('terminal')
    bridge=read(captures/'bridge-summary.json') if (captures/'bridge-summary.json').exists() else {}
    final_settings=verdict.get('settingsDiagnostic') or bridge.get('settingsDiagnostic') or bridge.get('settings')
    settings=dict(diagnosticBudgetSeconds=29,enablementObservationWindowSeconds=3,
                  journalRecords=len(records),
                  observations={stage:dict(sequence=r['record']['sequence'],uptime=r['record'].get('uptime'),
                        value=r['record'].get('snapshot',{}).get('value')) for stage,r in observations.items()},
                  bridgeSettings=final_settings)
    if start:
        settings.update(receiverStartUptime=start['receivedUptime'],deadlineUptime=start['diagnosticDeadlineUptime'])
    if terminal:
        record=terminal['record'];slot='settings-'+str(record['sequence']).zfill(4)+'-png';png=captures/(slot+'.png')
        settings.update(terminalDescriptor=record['files'].get('png'),terminalPNGPath=str(png),
                        terminalPNGComplete=png.exists(),terminalPNG=row(png) if png.exists() else None,
                        terminalRecordPath=str(next(p for p in captures.glob('0000-settings-*.json') if read(p)==terminal)))
        settings['terminalPNGChunkRequests']=sum(r['record'].get('kind')=='chunk' and r['record'].get('slot')==slot for r in records)
        prior_equal=[]
        if png.exists():
            for stage,prior in observations.items():
                if stage=='terminal' or prior['record']['sequence']>=record['sequence']:continue
                prior_slot='settings-'+str(prior['record']['sequence']).zfill(4)+'-png'
                prior_png=captures/(prior_slot+'.png')
                if prior_png.exists() and prior_png.read_bytes()==png.read_bytes():
                    prior_equal.append(dict(stage=stage,path=str(prior_png),sha256=sha(prior_png.read_bytes())))
        settings['earlierCompletedPNGsWithExactTerminalBytes']=prior_equal
    outer['nativeMethodResults']={'Settings':methods.get('test000PublicSettingsFullKeyboardAccess()','Not observed'),
                                  'Tab':methods.get('test010ReferenceFirstTab()','Not observed')}
    outer['methodResultsResolvedFrom']=str(tests)
    (HERE/'attempt-result.json').write_bytes(stable(outer))
    # Re-run only source/archive checks before relocating bulky historical copies.
    import importlib.util
    spec=importlib.util.spec_from_file_location('_successor_final_guard',HERE/'dispatch_successor.py')
    dispatcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(dispatcher)
    reverified=dispatcher.verify()
    assert reverified['packetSHA256']==materialized['packetSHA256']==selected['packetSHA256']
    relocated=[]
    stage=HERE/'sealed-inputs'
    if stage.exists():
        before=inventory(stage);destination=scratch/'sealed-baseline'
        assert not destination.exists()
        shutil.move(str(stage),destination)
        assert inventory(destination)==before and not stage.exists()
        relocated.append(dict(originalPath=str(stage),retainedPath=str(destination),
                              files=len(before),bytes=sum(r['bytes'] for r in before.values()),
                              memberTreeSHA256=sha(stable(before)),members=before))
    write(HERE/'relocated-source-custody.json',relocated)
    compact=HERE/'observed';compact.mkdir()
    for rel in ['runtime/lifecycle.json','runtime/runtime-verdict.json','runtime/xctest-tests.json',
                'runtime/xctest-summary.json','runtime/official-capture.json','runtime/attachment-export.json',
                'runtime/session/command-observer/observer.json','runtime/session/local-settings-first-failure.json',
                'runtime/captures/bridge-summary.json','scratch-cleanup.json']:
        source=run/rel
        if source.exists():
            assert source.stat().st_size<2_000_000
            target=compact/rel.replace('/','__')
            with target.open('xb') as stream:stream.write(source.read_bytes())
    raw=inventory(run)
    write(HERE/'raw-artifacts.json',dict(root=str(run),members=raw,memberTreeSHA256=sha(stable(raw))))
    tools={}
    for name in ['/usr/bin/xcrun','/Applications/Xcode_26.6.app/Contents/Developer/usr/bin/xcodebuild',
                 '/Applications/Xcode_26.6.app/Contents/Developer/usr/bin/simctl']:
        p=Path(name)
        if p.is_file():tools[name]=dict(resolvedPath=str(p.resolve()),**row(p))
    command=read(HERE/'commands/dispatch/receipt.json')
    original_results=verdict.get('classification',{}).get('originalOracleResults',[])
    failed_predicates=sorted({name for r in original_results for name,passed in r.get('predicates',{}).items() if not passed})
    passed_predicates=sorted({name for r in original_results for name,passed in r.get('predicates',{}).items() if passed})
    results=dict(schema='mixer.apple-settings-runtime-r2.1',observedAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        runID=selected['runID'],methodResults=methods,
        Settings=methods.get('test000PublicSettingsFullKeyboardAccess()','Not observed'),
        Tab=methods.get('test010ReferenceFirstTab()','Not observed'),
        nativeAttempts=1 if observer else 0,builds=0,automaticRetry=False,
        sourceIdentityAuthority='Exact accepted runtime/compile archives and manifests. Checkout revision is context only.',
        sourceRevision=read(HERE/'environment.json')['source-revision'].strip(),
        sourceTreeSHA256=selected['sourceTreeSHA256'],runtimeSourceTreeSHA256=materialized['runtimeSourceTreeSHA256'],
        productArchiveSHA256=selected['productArchiveSHA256'],sourceMembers=42,runtimeMembers=32,productMembers=55,
        candidatePacketSHA256=read(HERE/'packet.json')['acceptedBindings']['candidatePacket']['sha256'],
        dispatchPacketSHA256=selected['packetSHA256'],rootSelectionSHA256=sha((HERE/'root-selection.json').read_bytes()),
        originalRootSelectionSHA256=materialized['rootSelectionSHA256'],environment=read(HERE/'environment.json'),
        toolFiles=tools,settings=settings,officialImportAccepted=(runtime/'official-capture.json').exists(),
        failedOriginalPredicates=failed_predicates,passedOriginalPredicates=passed_predicates,
        nativeVerdict=verdict,xcodebuildExitCode=observer.get('exitCode'),dispatchExitCode=command['exitCode'],
        cleanup=dict(checks=cleanup,allFivePassed=all(r['passed'] for r in cleanup),
            ownedDeviceAbsent=outer.get('ownedDeviceAbsent'),baselineStatesPreserved=outer.get('baselineStatesPreserved'),
            otherBootedDevicesPreserved=outer.get('otherBootedDevicesPreserved'),
            processGroup=observer.get('ownedProcessGroup'),streams=observer.get('streams'),
            outerDispatchGroupAbsent=command['ownedGroupAbsent'],sourceProductScratch=scratch_cleanup,
            sessionConfigurationAbsent=not (runtime/'session/session.xctestrun').exists()),
        selectedSimulator=selected['ownedSimulatorIdentity'],baselineFrontends=selected['baselineFrontends'],
        outerFailure=outer.get('failure'),elapsedNativeSupervisorSeconds=outer['elapsedSeconds'],
        heldHistoricalProcessesTargeted=False,heldV5Retried=False,physicalPhones='Disconnected; no discovery or runs',
        runPassed=verdict.get('runPassed',False),GAQualified=False,
        custody=dict(rawRun=str(run),rawManifest='raw-artifacts.json',relocatedHistoricalInputs='relocated-source-custody.json',
            immutableHistoryModified=False,appOrRunnerProductChanges=0,rawMediaAndXCResultRetainedOutsideGit=True),
        commands=dict(supervisor='TMPDIR='+str(scratch/'tmp')+' PYTHONDONTWRITEBYTECODE=1 python3 -B '+str(HERE/'run_r2.py'),
                      actualXCTest=observer.get('argv'),outerCommands='commands/',nativeCommands=str(runtime/'commands.json')))
    write(HERE/'result.json',results)
    label=lambda value: value if value is not None else 'unobserved'
    report=f'''One fresh accepted Settings then reference-first Tab diagnostic; zero builds, zero retries.
Settings: {results['Settings']}
Tab: {results['Tab']}
XCTest exit: {label(results['xcodebuildExitCode'])}
Official import accepted: {results['officialImportAccepted']}
Native run passed: {results['runPassed']}
Failed original predicates: {json.dumps(failed_predicates)}; other predicates passed: {len(passed_predicates)}
All five cleanup checks passed: {results['cleanup']['allFivePassed']}
Owned simulator absent: {results['cleanup']['ownedDeviceAbsent']}
Baseline simulator states preserved: {results['cleanup']['baselineStatesPreserved']}
Unrelated booted simulators: {json.dumps(results['cleanup']['otherBootedDevicesPreserved'])}
Raw trace, media and xcresult: {run}
Raw artifact identities: raw-artifacts.json
Dispatch packet SHA256: {selected['packetSHA256']}
Accepted candidate SHA256: {results['candidatePacketSHA256']}
Compile source SHA256: {selected['sourceTreeSHA256']}
Retained products SHA256: {selected['productArchiveSHA256']}
Environment, commands, detailed Settings evidence, source bindings and cleanup: result.json
Sealed baseline copies moved unchanged outside Git: relocated-source-custody.json
No physical phones, historical held-process probes/signals, V5 retry, product changes, commits, pushes, or children.
Simulator diagnostic only; no physical-device, full matrix, package, FieldLog, publication or GA qualification.
'''
    (HERE/'REPORT.txt').write_text(report)
    members=inventory(HERE)
    write(HERE/'handoff.json',dict(schema=1,members=members,memberTreeSHA256=sha(stable(members)),
        methodResults=methods,runPassed=results['runPassed'],gaAccepted=False,rawRoot=str(run)))
    print(json.dumps(dict(methodResults=methods,allFiveCleanupPassed=results['cleanup']['allFivePassed'],
                         rawRoot=str(run),handoffSHA256=sha((HERE/'handoff.json').read_bytes()))))

def verify():
    sealed=read(HERE/'handoff.json')
    actual=inventory(HERE);actual.pop('handoff.json')
    assert actual==sealed['members'] and sha(stable(actual))==sealed['memberTreeSHA256']
    raw=read(HERE/'raw-artifacts.json');assert inventory(Path(raw['root']))==raw['members']
    for moved in read(HERE/'relocated-source-custody.json'):
        assert not Path(moved['originalPath']).exists()
        assert inventory(Path(moved['retainedPath']))==moved['members']
    print(json.dumps(dict(verified=True,methodResults=sealed['methodResults'],
                         handoffSHA256=sha((HERE/'handoff.json').read_bytes()))))

if __name__=='__main__':
    if sys.argv[1:]==['seal']:seal()
    elif sys.argv[1:]==['verify']:verify()
    else:raise SystemExit('Use seal once, or verify')
