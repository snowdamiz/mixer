#!/usr/bin/env python3
"""Resolve W04 from official output and seal retained evidence; no native calls."""
import collections
import datetime
import hashlib
import json
from pathlib import Path
import stat
import sys

BASE = Path(__file__).resolve().parent

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def stable(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()

def read(path):
    return json.loads(path.read_bytes())

def inventory():
    rows = {}
    for path in sorted(BASE.rglob('*')):
        assert not path.is_symlink(), str(path)
        if path.is_file() and path != BASE/'handoff.json':
            raw = path.read_bytes()
            rows[str(path.relative_to(BASE))] = dict(bytes=len(raw), sha256=sha(raw),
                    mode=stat.S_IMODE(path.stat().st_mode))
    return rows

def seal():
    run = next((BASE/'sealed-inputs/verification/apple-passive-lifecycle-runtime-preparation').glob('native-run-v9-*'))
    runtime = run/'runtime'
    official = read(runtime/'xctest-tests.json')
    nodes = []
    def walk(value):
        if isinstance(value, dict):
            if value.get('nodeType') == 'Test Case': nodes.append(value)
            for child in value.values(): walk(child)
        elif isinstance(value, list):
            for child in value: walk(child)
    walk(official)
    methods = {node['name']:node['result'] for node in nodes}
    assert methods == {'test000PublicSettingsFullKeyboardAccess()':'Failed',
                       'test010ReferenceFirstTab()':'Skipped'}
    observer = read(runtime/'session/command-observer/observer.json')
    lifecycle = read(runtime/'lifecycle.json')
    scratch = read(run/'scratch-cleanup.json')
    outer = read(BASE/'attempt-result.json')
    assert observer['exitCode']==65 and observer['ownedProcessGroup']['state']=='absent'
    assert all(row['eof'] and not row['readerFailed'] for row in observer['streams'].values())
    assert all(row['passed'] for row in lifecycle['cleanupResults'])
    assert lifecycle['ownedDeviceAbsent'] and lifecycle['baselineStatesPreserved']
    assert scratch['scratchAbsent'] and scratch['verifiedBeforeRemoval']
    assert outer['ownedDeviceAbsent'] and outer['baselineStatesPreserved']
    records=[read(path) for path in (runtime/'captures').glob('0000-settings-*.json')]
    start=next(row for row in records if row['record']['kind']=='start')
    observations={row['record']['stage']:row for row in records if row['record']['kind']=='observe' and row['record']['stage'] in ['before-switch','after-switch','terminal']}
    terminal=observations['terminal']['record']
    slot='settings-'+str(terminal['sequence']).zfill(4)+'-png'
    chunks=[row for row in records if row['record']['kind']=='chunk' and row['record']['slot']==slot]
    assert len(chunks)==23 and {row['record']['count'] for row in chunks}=={44}
    bridge=read(runtime/'captures/bridge-summary.json')
    assert bridge['generation']==0 and bridge['currentCase'] is None and bridge['verdicts']==[]
    # Resolve the supervisor's initial placeholders from official method results.
    outer['nativeMethodResults']={'Settings':'Failed','Tab':'Skipped'}
    outer['methodResultsResolvedFrom']=str((runtime/'xctest-tests.json').relative_to(BASE))
    (BASE/'attempt-result.json').write_bytes(stable(outer))
    command_rows=read(runtime/'commands.json')
    own=outer['ownedDevice']
    cleanup_commands=[row for row in command_rows if row.get('argv') in [
        ['/usr/bin/xcrun','simctl','shutdown',own],['/usr/bin/xcrun','simctl','delete',own]]]
    assert len(cleanup_commands)==2 and all(row['exitCode']==0 for row in cleanup_commands)
    drift=read(BASE/'preflight.json')['originalMetadataDrift']
    repo=BASE.parents[2]
    for row in drift:
        original=repo/row['path']
        assert stat.S_IMODE(original.stat().st_mode)==row['observedMode']
        staged=BASE/'sealed-inputs'/row['path']
        assert original.read_bytes()==staged.read_bytes()
    tools={}
    for path in ['/usr/bin/xcrun','/Applications/Xcode_26.6.app/Contents/Developer/usr/bin/xcodebuild',
                 '/Applications/Xcode_26.6.app/Contents/Developer/usr/bin/simctl']:
        p=Path(path)
        if p.is_file(): tools[path]=dict(resolvedPath=str(p.resolve()),sha256=sha(p.read_bytes()))
    result=dict(schema='mixer.w04.apple-v9-native-attempt.1',
      observedAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
      runID=read(BASE/'root-selection.json')['runID'],
      sourceRevision=read(BASE/'environment.json')['source-revision'].strip(),
      identities=read(BASE/'root-selection.json'),
      sourceIdentityAuthority='Exact accepted archive/manifest bytes; current checkout revision is context only',
      sourceMembers=42, productMembers=55, productRebuildRequired=False,
      execution='One fresh native simulator run using unchanged accepted V9 composition and retained products',
      methodResults=methods, xcodebuildExitCode=65,
      nativeFocusOracleResult='Not evaluated: Settings failed and first Tab was skipped',
      passiveAppLifecycleResult='Not collected: dependent application case never began',
      officialImportAccepted=False,
      officialImportFailure=read(runtime/'runtime-verdict.json')['sessionFailure'],
      primaryNativeFailure='Settings diagnostic deadline exhausted',
      settingsEvidence=dict(diagnosticBudgetSeconds=29, chunkBytes=4992,
        receiverStartUptime=start['receivedUptime'],deadlineUptime=start['diagnosticDeadlineUptime'],
        observedSwitchValues={stage:row['record']['snapshot']['value'] for stage,row in observations.items()},
        terminalObservationUptime=terminal['uptime'], terminalPNGBytes=terminal['files']['png']['bytes'],
        terminalPNGExpectedChunks=44,terminalPNGReceivedChunks=23,
        terminalPNGAvailableAsCompleteCapture=(runtime/'captures'/(slot+'.png')).exists(),
        terminationMarkersCompleted=False, durableSetupCompleted=False),
      cleanup=dict(allFiveSelectedOperationsPassed=True, selectedOperations=lifecycle['cleanupResults'],
        shutdownAndDeleteCommands=cleanup_commands, ownedDeviceAbsent=True,
        baselineStatesPreserved=True, otherBootedDevicesPreserved=outer['otherBootedDevicesPreserved'],
        selectedProcessGroupAbsent=True, selectedProcessGroup=observer['ownedProcessGroup'],
        selectedStreamsReachedEOF=True,outerDispatchGroupAbsent=read(BASE/'commands/dispatch/receipt.json')['ownedGroupAbsent'],
        sourceAndProductScratchAbsent=True,sessionConfigurationRetired=not (runtime/'session/session.xctestrun').exists()),
      originalCheckoutModeDrift=drift,originalInputsModified=False, tools=tools,
      frozenV7JoinUsed=False, heldV5StartupRetried=False, heldHistoricalProcessesTargeted=False,
      physicalPhones='Disconnected; no discovery or runs', productionPublication=False,
      runPassed=False,nativeKeyboardQualified=False,gaAccepted=False,
      elapsedSeconds=outer['elapsedSeconds'],
      nextConcreteCorrection='Correct Settings evidence collection to finish terminal PNG delivery and durable completion within the existing 29-second budget. This run received only 23/44 terminal PNG chunks although the switch was observed enabled. Preserve raw captures, 4992-byte chunks, 8 KiB guards, first-Tab gate and original focus oracle; obtain review of the harness correction before a newly selected attempt.',
      artifacts=dict(runtimeDirectory=str(runtime.relative_to(BASE)),
        officialTests=str((runtime/'xctest-tests.json').relative_to(BASE)),
        officialSummary=str((runtime/'xctest-summary.json').relative_to(BASE)),
        xcresult=str((runtime/'session/session.xcresult').relative_to(BASE)),
        rawCaptures=str((runtime/'captures').relative_to(BASE)),
        supervision=str((runtime/'session/command-observer').relative_to(BASE))))
    with (BASE/'result.json').open('xb') as f:f.write(stable(result))
    rows=inventory()
    with (BASE/'handoff.json').open('xb') as f:
        f.write(stable(dict(schema=1,members=rows,memberTreeSHA256=sha(stable(rows)),
                           officialMethods=methods,runPassed=False,gaAccepted=False)))
    print(json.dumps(dict(methods=methods,evidenceFiles=len(rows),nativeRunPassed=False,cleanupPassed=True)))

def verify():
    handoff=read(BASE/'handoff.json')
    assert sha(stable(handoff['members']))==handoff['memberTreeSHA256']
    assert inventory()==handoff['members']
    result=read(BASE/'result.json')
    assert result['cleanup']['ownedDeviceAbsent'] and result['cleanup']['baselineStatesPreserved']
    assert not result['runPassed'] and not result['officialImportAccepted']
    print(json.dumps(dict(verified=True,evidenceFiles=len(handoff['members']),
                         handoffSHA256=sha((BASE/'handoff.json').read_bytes()),
                         methodResults=result['methodResults'])))

if __name__=='__main__':
    if sys.argv[1:] == ['seal']: seal()
    elif sys.argv[1:] == ['verify']: verify()
    else: raise SystemExit('Use seal once, or verify (read-only)')
