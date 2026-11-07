#!/usr/bin/env python3
"""Retire only the new owned environment after the pre-XCTest UI refusal."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time

sys.dont_write_bytecode = True
import outer

HERE = outer.HERE
device = outer.read('owned-device.json')
frontend = outer.read('owned-frontend.json')
baseline = outer.read('external-baseline-normalized.json')
assert not (HERE/'dispatch-invocation.json').exists(), 'This cleanup is for an ineligible pre-dispatch setup only'
assert not (HERE/'root-selection.json').exists()
assert not (HERE/'cleanup.json').exists()
assert device['udid'] not in ['CE7E80FC-64BF-41A0-B07B-60F4D8711808','D55C87E9-F349-49AC-BCD3-3B4B5BE9E010']
pid = frontend['pid']
assert pid not in [2621,2424,20745,20770,20780,20817,20842,20851,20866]
current = outer.frontends('frontends-pre-cleanup')
assert current == frontend['allInnerBaselineFrontends']
assert frontend['identity'] in current and frontend['identity'] not in baseline['frontends']
# NSRunningApplication targets the exact new app instance. This does not rely on
# Accessibility, a generic bundle-ID quit, or signalling any external process.
script = '''ObjC.import('AppKit');
function run(args) {
 var a=$.NSRunningApplication.runningApplicationWithProcessIdentifier(Number(args[0]));
 if(!a)throw Error('Owned app instance missing before termination');
 if(ObjC.unwrap(a.executableURL.path)!==args[1])throw Error('Owned executable differs');
 return JSON.stringify({pid:Number(a.processIdentifier),executable:ObjC.unwrap(a.executableURL.path),terminationRequested:Boolean(a.terminate)});
}'''
requested = json.loads(outer.command('terminate-owned-frontend',['/usr/bin/osascript','-l','JavaScript','-e',script,str(pid),outer.EXE]))
assert requested['terminationRequested'] is True
for i in range(10):
    rows = outer.frontends('frontends-retirement-'+str(i))
    if rows == baseline['frontends']:
        break
    time.sleep(0.5)
else:
    raise RuntimeError('Owned frontend did not retire; no broad signal attempted')
now = outer.devices('devices-pre-cleanup')
def flat(snapshot):
    return {r['udid']:{**r,'runtimeIdentifier':runtime} for runtime,rows in snapshot['devices'].items() for r in rows}
row = flat(now)[device['udid']]
assert row['name'] == device['name'] and row['runtimeIdentifier'] == device['runtime']
assert row['deviceTypeIdentifier'] == 'com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro'
if row['state'] != 'Shutdown':
    outer.command('shutdown-owned-device',['/usr/bin/xcrun','simctl','shutdown',device['udid']])
outer.command('delete-owned-device',['/usr/bin/xcrun','simctl','delete',device['udid']])
after = outer.devices('devices-after-cleanup')
before_rows,after_rows = flat(baseline['devices']),flat(after)
fields = ['name','state','runtimeIdentifier','deviceTypeIdentifier']
assert set(before_rows) == set(after_rows)
assert all(all(before_rows[k].get(f) == after_rows[k].get(f) for f in fields) for k in before_rows)
assert device['udid'] not in after_rows
final_frontends = outer.frontends('frontends-after-cleanup')
assert final_frontends == baseline['frontends']
watched = outer.read('input-identities.json')
changed=[]
for path,expected in watched.items():
    p=Path(path)
    actual=dict(bytes=p.stat().st_size,mode=p.stat().st_mode & 0o7777,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    if actual != expected:changed.append(path)
assert changed == [], changed
scratch = outer.SCRATCH
assert scratch.parent == Path('/private/tmp') and scratch.name.startswith('mixer-20261107-apple-tab-keyboard-r2-')
assert scratch.stat().st_ino == outer.read('scratch-custody.json')['inode']
shutil.rmtree(scratch)
result=dict(ownedDevice=device,ownedFrontend=frontend,ownedFrontendAbsent=True,ownedWindowAbsentWithFrontend=True,ownedSimulatorAbsent=True,allExternalDeviceIdentitiesAndStatesPreserved=True,externalFrontendIdentitiesPreserved=True,externalBaselineFrontends=baseline['frontends'],finalFrontends=final_frontends,protectedSimulators={k:after_rows[k]['state'] for k in ['CE7E80FC-64BF-41A0-B07B-60F4D8711808','D55C87E9-F349-49AC-BCD3-3B4B5BE9E010']},inputFilesRechecked=len(watched),allWatchedInputsUnchanged=True,innerFiveRuntimeCleanupChecks='Not entered: unchanged dispatcher and XCTest were never invoked; no new inner pass claimed.',scratch=str(scratch),scratchAbsent=not scratch.exists(),noListenerOpened=True,heldProcessProbesOrSignals=False,phones='Disconnected; no discovery',children=0,builds=0,nativeAttempts=0,automaticRetries=0,commits=0,pushes=0)
outer.put('cleanup.json',result)
print(json.dumps(dict(cleanup='passed',ownedDeviceAbsent=True,externalBaselinePreserved=True,scratchAbsent=result['scratchAbsent'])))
