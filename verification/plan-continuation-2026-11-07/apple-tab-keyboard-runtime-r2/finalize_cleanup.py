#!/usr/bin/env python3
"""Finish owned-device cleanup, retaining the failed external-state reconciliation."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode=True
import outer

HERE=outer.HERE
device=outer.read('owned-device.json')
frontend=outer.read('owned-frontend.json')
baseline=outer.read('external-baseline-normalized.json')
assert not (HERE/'dispatch-invocation.json').exists()
assert not (HERE/'root-selection.json').exists()
assert device['udid'] not in ['CE7E80FC-64BF-41A0-B07B-60F4D8711808','D55C87E9-F349-49AC-BCD3-3B4B5BE9E010']
def flat(snapshot):
    return {r['udid']:{**r,'runtimeIdentifier':runtime} for runtime,rows in snapshot['devices'].items() for r in rows}
now=outer.devices('devices-cleanup-reconciliation')
rows=flat(now)
if device['udid'] in rows:
    owned=rows[device['udid']]
    assert owned['name']==device['name'] and owned['runtimeIdentifier']==device['runtime']
    assert owned['deviceTypeIdentifier']=='com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro'
    assert owned['state']=='Shutdown','No second shutdown command or runtime retry'
    outer.command('delete-owned-device-final',['/usr/bin/xcrun','simctl','delete',device['udid']])
after=outer.devices('devices-final')
before_rows,after_rows=flat(baseline['devices']),flat(after)
fields=['name','state','runtimeIdentifier','deviceTypeIdentifier']
differences={k:{f:dict(before=before_rows[k].get(f),after=after_rows.get(k,{}).get(f)) for f in fields if before_rows[k].get(f)!=after_rows.get(k,{}).get(f)} for k in before_rows if any(before_rows[k].get(f)!=after_rows.get(k,{}).get(f) for f in fields)}
final_frontends=outer.frontends('frontends-final')
assert final_frontends==baseline['frontends']
assert device['udid'] not in after_rows
watched=outer.read('input-identities.json')
changed=[]
for path,expected in watched.items():
    p=Path(path)
    actual=dict(bytes=p.stat().st_size,mode=p.stat().st_mode & 0o7777,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    if actual!=expected:changed.append(path)
assert changed==[],changed
scratch=outer.SCRATCH
assert scratch.parent==Path('/private/tmp') and scratch.name.startswith('mixer-20261107-apple-tab-keyboard-r2-')
assert scratch.stat().st_ino==outer.read('scratch-custody.json')['inode']
shutil.rmtree(scratch)
result=dict(ownedDevice=device,ownedFrontend=frontend,ownedFrontendAbsent=True,ownedWindowAbsentWithFrontend=True,ownedSimulatorAbsent=True,allExternalDeviceIdentitiesAndStatesPreserved=not bool(differences),externalStateDifferences=differences,unexpectedNewDevices=sorted(set(after_rows)-set(before_rows)),externalFrontendIdentitiesPreserved=final_frontends==baseline['frontends'],externalBaselineFrontends=baseline['frontends'],finalFrontends=final_frontends,protectedSimulators={k:after_rows[k]['state'] for k in ['CE7E80FC-64BF-41A0-B07B-60F4D8711808','D55C87E9-F349-49AC-BCD3-3B4B5BE9E010']},cleanupPassed=False,incident='Graceful termination of the uniquely owned Simulator frontend also shut down both protected booted simulators. Baseline preservation failed. No recovery commands sent to protected devices.',failedShutdownCommand='Only owned UUID was sent simctl shutdown, but Simulator quit had already shut it down; exit 149 / CoreSimulator 405 retained. No shutdown command was repeated.',inputFilesRechecked=len(watched),allWatchedInputsUnchanged=True,innerFiveRuntimeCleanupChecks='Not entered: unchanged dispatcher and XCTest were never invoked; no new inner pass claimed.',scratch=str(scratch),scratchAbsent=not scratch.exists(),noListenerOpened=True,noDirectProtectedDeviceCommands=True,heldProcessProbesOrSignals=False,phones='Disconnected; no discovery',children=0,builds=0,nativeAttempts=0,automaticRetries=0,commits=0,pushes=0)
outer.put('cleanup.json',result)
print(json.dumps(dict(cleanup='external-baseline-reconciliation-failed',ownedDeviceAbsent=True,protectedStates=result['protectedSimulators'],scratchAbsent=result['scratchAbsent'])))
