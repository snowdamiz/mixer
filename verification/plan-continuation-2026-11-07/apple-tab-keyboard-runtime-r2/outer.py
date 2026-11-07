#!/usr/bin/env python3
"""Owned environment operations around the unchanged accepted dispatcher.

No packet-local runtime module or compiled product is changed by this controller.
Dispatch is a separate explicit phase after public UI eligibility is recorded.
"""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OLD = HERE.parent / 'apple-settings-runtime-r2'
DEV = '/Applications/Xcode_26.6.app/Contents/Developer'
EXE = DEV + '/Applications/Simulator.app/Contents/MacOS/Simulator'
SCRATCH = Path(json.loads((HERE/'scratch-custody.json').read_text())['path'])
ENV = {**os.environ,'DEVELOPER_DIR':DEV,'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(SCRATCH)}

def stable(value):
    return (json.dumps(value,indent=2,sort_keys=True)+'\n').encode()

def put(name,value):
    with (HERE/name).open('xb') as f:
        f.write(stable(value))

def read(name):
    return json.loads((HERE/name).read_bytes())

def command(label,argv,timeout=45,frontends=False):
    start=time.monotonic()
    p=subprocess.run(argv,cwd=REPO,env=ENV,capture_output=True,timeout=timeout)
    out=p.stdout
    if frontends:
        out=('\n'.join(line.strip() for line in out.decode().splitlines() if line.strip().endswith(EXE))).encode()
    with (HERE/(label+'.stdout')).open('xb') as f:f.write(out)
    with (HERE/(label+'.stderr')).open('xb') as f:f.write(p.stderr)
    put(label+'.command.json',dict(argv=argv,atUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),cwd=str(REPO),developerDirectory=DEV,exitCode=p.returncode,seconds=time.monotonic()-start,stdoutSHA256=hashlib.sha256(out).hexdigest(),stderrSHA256=hashlib.sha256(p.stderr).hexdigest(),scope='Only pinned Simulator frontend identities retained' if frontends else 'Complete command output'))
    if p.returncode:raise RuntimeError(label+': '+p.stderr.decode())
    return out.decode()

def frontends(label):
    return command(label,['/bin/ps','-axo','pid=,lstart=,comm='],frontends=True).strip().splitlines()

def devices(label):
    return json.loads(command(label,['/usr/bin/xcrun','simctl','list','devices','--json']))

def setup():
    assert read('preflight.json')['verified']['nativeExecuted'] is False
    before=read('external-baseline.json')
    # The raw empty frontend output is a newline; normalize it to the exact []
    # contract, without changing the raw observation or claiming another run.
    external_frontends=(HERE/'frontends-before.stdout').read_text().strip().splitlines()
    put('external-baseline-normalized.json',dict(devices=before['devices'],frontends=external_frontends,normalization='Whitespace-only raw frontend output is zero identities'))
    run_id=str(uuid.uuid4())
    name='MixerFocusReferenceV9-'+run_id
    put('creation-intent.json',dict(runID=run_id,name=name,deviceType='com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro',runtime='com.apple.CoreSimulator.SimRuntime.iOS-26-5',build='23F77',maximumNativeAttempts=1,builds=0,automaticRetries=0))
    owned=command('create',['/usr/bin/xcrun','simctl','create',name,'com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro','com.apple.CoreSimulator.SimRuntime.iOS-26-5']).strip()
    assert str(uuid.UUID(owned)).upper()==owned
    assert owned not in {r['udid'] for rows in before['devices']['devices'].values() for r in rows}
    put('owned-device.json',dict(runID=run_id,udid=owned,name=name,runtime='com.apple.CoreSimulator.SimRuntime.iOS-26-5',build='23F77'))
    command('boot',['/usr/bin/xcrun','simctl','boot',owned])
    command('bootstatus',['/usr/bin/xcrun','simctl','bootstatus',owned,'-b'],timeout=180)
    rows=frontends('frontends-before-open')
    assert rows==external_frontends,'External frontend baseline changed before open'
    command('open-owned-window',['/usr/bin/open','-n','-a',DEV+'/Applications/Simulator.app','--args','-CurrentDeviceUDID',owned])
    time.sleep(2)
    after=frontends('frontends-after-open')
    new=[r for r in after if r not in external_frontends]
    assert len(new)==1 and all(r in after for r in external_frontends),'Exactly one new frontend required'
    pid=int(new[0].split()[0])
    assert pid not in [2621,20745,20770,20780,20817,20842,20851,20866,2424]
    put('owned-frontend.json',dict(pid=pid,identity=new[0],allInnerBaselineFrontends=after,externalBaselineFrontends=external_frontends))
    print(json.dumps(dict(owned=owned,pid=pid,name=name)))

def inspect_ui(label):
    owned=read('owned-device.json');pid=read('owned-frontend.json')['pid']
    # Read only the exact new frontend's public accessibility tree.
    script='''function run(args) {
      var se=Application('System Events');
      var found=se.applicationProcesses.whose({unixId:Number(args[0])})();
      if(found.length!==1)throw Error('Exact owned frontend unavailable');
      var p=found[0];
      function safe(f){try{return f()}catch(e){return String(e)}}
      function item(x,depth){
        var o={name:safe(()=>x.name()),role:safe(()=>x.role()),enabled:safe(()=>x.enabled())};
        o.attributes=safe(()=>x.attributes().map(a=>({name:a.name(),value:safe(()=>a.value())})));
        if(depth>0)o.menus=safe(()=>x.menus().map(m=>({name:safe(()=>m.name()),items:m.menuItems().map(y=>item(y,depth-1))})));
        return o;
      }
      return JSON.stringify({pid:p.unixId(),name:p.name(),frontmost:p.frontmost(),windows:p.windows().map(w=>({name:w.name(),role:w.role(),attributes:safe(()=>w.attributes().map(a=>({name:a.name(),value:safe(()=>a.value())})))})),menuBar:p.menuBars[0].menuBarItems().map(x=>item(x,3))});
    }'''
    raw=command(label,['/usr/bin/osascript','-l','JavaScript','-e',script,str(pid)],timeout=45)
    obj=json.loads(raw)
    put(label+'.json',obj)
    print(json.dumps(dict(pid=obj['pid'],windows=[x['name'] for x in obj['windows']],menus=[x['name'] for x in obj['menuBar']])))

def dispatch():
    eligibility=read('keyboard-eligibility.json')
    assert eligibility['eligible'] is True and eligibility['hardwareKeyboardConnected'] is True
    assert eligibility['globalPreferencesChanged'] is False
    assert not (HERE/'dispatch-invocation.json').exists(),'Outer one-attempt marker exists'
    device=read('owned-device.json');frontend=read('owned-frontend.json')
    assert frontends('frontends-at-dispatch')==frontend['allInnerBaselineFrontends']
    old=json.loads((OLD/'root-selection.json').read_bytes())
    root={**old,'runID':device['runID'],'selectedAtUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'ownedSimulatorIdentity':{k:device[k] for k in ['udid','name','runtime','build']},'baselineDevices':read('external-baseline-normalized.json')['devices'],'baselineFrontends':frontend['allInnerBaselineFrontends']}
    put('root-selection.json',root)
    selected_sha=hashlib.sha256((HERE/'root-selection.json').read_bytes()).hexdigest()
    packet=read('preflight.json')['verified']['packetSHA256']
    put('dispatch-invocation.json',dict(acceptedDispatcher=str(OLD/'dispatch_successor.py'),function='dispatch(reviewed_packet, selection_path, selected_sha)',reviewed_packet=packet,selection_path=str(HERE/'root-selection.json'),selected_sha=selected_sha,runID=device['runID'],builds=0,maximumNativeAttempts=1,automaticRetries=0,outerOnly=True,packetChanges=0))
    spec=importlib.util.spec_from_file_location('_unchanged_accepted_dispatcher',OLD/'dispatch_successor.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    os.environ.update(ENV)
    try:
        result=module.dispatch(packet,HERE/'root-selection.json',selected_sha)
        put('dispatch-result.json',result)
        print(json.dumps(dict(returned=True,runPassed=result.get('runPassed'),diagnosticOutcome=result.get('diagnosticOutcome'),xcodebuildExitCode=result.get('xcodebuildExitCode'))))
    except BaseException as error:
        import traceback
        put('dispatch-error.json',dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
        raise

if __name__=='__main__':
    if sys.argv[1]=='setup':setup()
    elif sys.argv[1]=='inspect-ui':inspect_ui(sys.argv[2])
    elif sys.argv[1]=='dispatch':dispatch()
    else:raise ValueError('Unknown explicit phase')
