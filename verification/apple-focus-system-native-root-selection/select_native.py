#!/usr/bin/env python3
"""Verify accepted inputs and select exactly one owned V8 simulator attempt."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
DEV = '/Applications/Xcode_26.6.app/Contents/Developer'
PYTHON = '/opt/homebrew/opt/python@3.14/bin/python3.14'
PACKET = '70dcc748cf67ce6573215b3815736aca4689707cc081d34c8069f9b5f13c3a82'
PRODUCER = ROOT / 'verification/apple-focus-system-runtime-preparation'
REVIEW = ROOT / 'verification/apple-focus-system-runtime-review'
RUNTIME = 'com.apple.CoreSimulator.SimRuntime.iOS-26-5'
COMMANDS = []

def sha(raw): return hashlib.sha256(raw).hexdigest()
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(name, value):
    with (BASE / name).open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')

def command(name, argv, filter_frontends=False):
    start=time.monotonic()
    row=dict(name=name,argv=argv,startedUTC=utc(),cwd=str(ROOT),developerDirectory=DEV)
    p=subprocess.Popen(argv,cwd=ROOT,env={**os.environ,'DEVELOPER_DIR':DEV,'PYTHONDONTWRITEBYTECODE':'1'},
                       stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    row.update(PID=p.pid,processGroup=p.pid)
    try: out,err=p.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid,signal.SIGKILL)
        out,err=p.communicate(timeout=10)
        row['timedOut']=True
    if filter_frontends:
        out=('\n'.join(l for l in out.decode().splitlines() if '/Simulator.app/Contents/MacOS/Simulator' in l)+'\n').encode()
    (BASE/(name+'.stdout')).write_bytes(out)
    (BASE/(name+'.stderr')).write_bytes(err)
    try: os.killpg(p.pid,0); absent=False
    except ProcessLookupError: absent=True
    row.update(exitCode=p.returncode,bothEOF=True,ownedProcessGroupAbsent=absent,
               stdoutFilteredToSimulatorFrontends=filter_frontends,stdoutSHA256=sha(out),stderrSHA256=sha(err),
               elapsedSeconds=time.monotonic()-start)
    COMMANDS.append(row)
    (BASE/'commands.json').write_text(json.dumps(COMMANDS,indent=2,sort_keys=True)+'\n')
    assert p.returncode==0 and absent and not row.get('timedOut'), row
    return out

def main():
    assert not (BASE/'selection.json').exists() and not (BASE/'creation-intent.json').exists()
    for path,digest in [(PRODUCER/'packet.json',PACKET),
            (PRODUCER/'handoff.json','20dd17885f3c9b923465299da1cff9044ae178cb448b026c531552be87f332c5'),
            (REVIEW/'handoff.json','874ce792b4353f5b8ae21a5e08ea655c7909ba5111a104a28708caed600c8d89')]:
        assert sha(path.read_bytes())==digest
    command('prepare-verify',[PYTHON,'-B',str(PRODUCER/'prepare.py'),'verify'])
    command('handoff-verify',[PYTHON,'-B',str(PRODUCER/'seal.py'),'verify'])
    command('review-verify',[PYTHON,'-B',str(REVIEW/'seal.py'),'verify'])
    devices=json.loads(command('precreation-devices',['/usr/bin/xcrun','simctl','list','devices','--json']))
    runtimes=json.loads(command('precreation-runtimes',['/usr/bin/xcrun','simctl','list','runtimes','--json']))
    frontends=command('precreation-frontends',['/bin/ps','-axo','pid=,lstart=,comm='],True).decode().splitlines()
    frontends=[l for l in frontends if l.strip()]
    # A shared foreground Simulator needs separate coordination; this attempt owns its own frontend.
    assert not frontends, 'Existing Simulator frontend must be preserved'
    assert not any(d['state']=='Booted' for rows in devices['devices'].values() for d in rows), 'Preserve active native work'
    assert not any(d['name'].startswith('MixerFocusReferenceV') for rows in devices['devices'].values() for d in rows), 'Retire obsolete owned instance before replacement'
    runtime=next(r for r in runtimes['runtimes'] if r['identifier']==RUNTIME)
    assert runtime['isAvailable'] and runtime['buildversion']=='23F77'
    run=str(uuid.uuid4()); name='MixerFocusReferenceV8-'+run[:8]
    write('creation-intent.json',dict(runID=run,name=name,runtime=RUNTIME,build='23F77',createdUTC=utc(),phones='disconnected-deferred'))
    udid=command('create',['/usr/bin/xcrun','simctl','create',name,'com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro',RUNTIME]).decode().strip()
    assert str(uuid.UUID(udid)).upper()==udid
    identity=dict(udid=udid,name=name,runtime=RUNTIME,build='23F77')
    write('created-identity.json',identity)
    after=json.loads(command('postcreation-devices',['/usr/bin/xcrun','simctl','list','devices','--json']))
    created=next(d for d in after['devices'][RUNTIME] if d['udid']==udid)
    assert created['name']==name and created['state']=='Shutdown' and created['isAvailable']
    before_by_id={d['udid']:d for rows in devices['devices'].values() for d in rows}
    after_by_id={d['udid']:d for rows in after['devices'].values() for d in rows}
    assert set(after_by_id)==set(before_by_id)|{udid}
    assert all(after_by_id[k]['state']==v['state'] and after_by_id[k]['name']==v['name'] for k,v in before_by_id.items())
    packet=json.loads((PRODUCER/'packet.json').read_bytes())
    selection=dict(schema='mixer.apple-focus-reference-root-selection.8',runID=run,packetSHA256=PACKET,
        selectedAtUTC=utc(),ownedSimulatorIdentity=identity,sourceTreeSHA256=packet['sourceTreeSHA256'],
        productArchiveSHA256=packet['nativeProductArchiveSHA256'],developerDirectory=DEV,
        baselineDevices=devices,baselineFrontends=[])
    write('selection.json',selection)
    digest=sha((BASE/'selection.json').read_bytes())
    driver=ROOT/'verification/apple-focus-system-native/observe_dispatch.py'
    assert sha(driver.read_bytes())=='95b8170c71375abc929ae21177b94a1ce7b0145cab8e0fa83cf553cdbfc68e7c'
    argv=[PYTHON,'-B',str(driver),'--root-selection',str(BASE/'selection.json'),'--root-selection-sha256',digest]
    write('execution-selection.json',dict(schema=1,attemptsAuthorized=1,selectedCommand=argv,
        rootSelectionSHA256=digest,driverSHA256=sha(driver.read_bytes()),selectionDriverSHA256=sha(Path(__file__).read_bytes()),
        sourceRevision='6403eea98031207f6e40a72b55dfd3bd4e7e6ec2',selectedUTC=selection['selectedAtUTC'],
        independentReviewHandoffSHA256='874ce792b4353f5b8ae21a5e08ea655c7909ba5111a104a28708caed600c8d89',
        cleanupOwner='selected runner; root emergency reconciliation',phones='disconnected-deferred',gaAccepted=False))
    print(json.dumps(dict(runID=run,udid=udid,rootSelectionSHA256=digest,selectedCommand=argv)))

if __name__=='__main__': main()
