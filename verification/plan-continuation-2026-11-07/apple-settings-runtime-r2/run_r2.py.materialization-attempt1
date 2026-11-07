#!/usr/bin/env python3
"""One owned V9 run; sealed code/products stay byte-identical."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import time
import traceback
import uuid

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DEV = '/Applications/Xcode_26.6.app/Contents/Developer'
ENV = {**os.environ, 'DEVELOPER_DIR': DEV, 'PYTHONDONTWRITEBYTECODE': '1'}
START = time.monotonic()
COMMANDS = []
HELD = {20745, 20770, 20780, 20817, 20842, 20851, 20866, 2424, 2621}

def stable(v):
    return (json.dumps(v, indent=2, sort_keys=True) + '\n').encode()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def write(path, value):
    with path.open('xb') as f:
        f.write(stable(value))

def command(name, argv, timeout=60, check=True, stdout_filter=None):
    folder = HERE / 'commands' / name
    folder.mkdir(parents=True)
    began = time.monotonic()
    p = subprocess.Popen(argv, cwd=REPO, env=ENV, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, start_new_session=True)
    signals = []
    try:
        out, err = p.communicate(timeout=min(timeout, max(1, 1150-(time.monotonic()-START))))
        timedout = False
    except subprocess.TimeoutExpired:
        timedout = True
        assert p.pid not in HELD
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try: os.killpg(p.pid, sig); signals.append(int(sig))
            except ProcessLookupError: pass
            try: out, err = p.communicate(timeout=5); break
            except subprocess.TimeoutExpired: continue
        else: raise RuntimeError('Owned command failed to close pipes')
    if stdout_filter is not None:
        out = stdout_filter(out)
    (folder / 'stdout.log').write_bytes(out)
    (folder / 'stderr.log').write_bytes(err)
    try: os.killpg(p.pid, 0); absent = False
    except ProcessLookupError: absent = True
    item = dict(argv=argv, cwd=str(REPO), developerDirectory=DEV,
                exitCode=p.returncode, timedOut=timedout, elapsedSeconds=time.monotonic()-began,
                pid=p.pid, processGroup=p.pid, signals=signals, ownedGroupAbsent=absent,
                stdout=dict(bytes=len(out), sha256=sha(out), eof=True),
                stderr=dict(bytes=len(err), sha256=sha(err), eof=True))
    item['stdoutScope'] = 'filtered pinned Simulator executable only' if stdout_filter else 'complete'
    write(folder/'receipt.json', item); COMMANDS.append(item)
    if check and (p.returncode or timedout):
        raise RuntimeError(name+': '+err.decode(errors='replace')[-2000:])
    return out

def load(path):
    spec = importlib.util.spec_from_file_location('w04_packet', path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

def prepare_baseline():
    original = REPO/'verification/apple-passive-lifecycle-runtime-preparation'
    p = load(original/'prepare.py')
    try: result = p.verify(); original_error = None
    except Exception as e: result = None; original_error = repr(e)
    write(HERE/'original-preflight.json', dict(verified=result, failure=original_error,
          noNativeCommandDispatched=True))
    packet = json.loads((original/'packet.json').read_bytes())
    rows = dict(packet['references'])
    for name, row in packet['references'].items():
        path = REPO/name
        assert sha(path.read_bytes()) == row['sha256'], name
        if path.name == 'handoff.json':
            for n, r in json.loads(path.read_bytes())['members'].items(): rows[n] = r
    for name, row in packet['files'].items():
        rows[str((original/name).relative_to(REPO))] = row
    for n in ['packet.json', 'handoff.json']:
        f = original/n
        rows[str(f.relative_to(REPO))] = dict(kind='file',mode=stat.S_IMODE(f.stat().st_mode),
              bytes=f.stat().st_size,sha256=sha(f.read_bytes()))
    acceptance = json.loads((REPO/'verification/current-diagnostic-corrections-root-review/apple-runtime-preparation-acceptance.json').read_bytes())
    for binding in acceptance['bindings'].values():
        f = REPO/binding['path']; assert sha(f.read_bytes()) == binding['sha256']
        if f.name == 'handoff.json':
            for n,r in json.loads(f.read_bytes())['members'].items(): rows[n]=r
    stage = HERE/'sealed-inputs'
    stage.mkdir(mode=0o755)
    drift = []
    for name, row in sorted(rows.items()):
        f = REPO/name; raw=f.read_bytes(); info=f.lstat()
        assert f.resolve()==f and stat.S_ISREG(info.st_mode) and info.st_nlink==1, name
        assert len(raw)==row['bytes'] and sha(raw)==row['sha256'], name
        if stat.S_IMODE(info.st_mode)!=row['mode']:
            drift.append(dict(path=name,observedMode=stat.S_IMODE(info.st_mode),sealedMode=row['mode'],bytesUnchanged=True))
        target = stage/name; target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as out: out.write(raw)
        target.chmod(row['mode'])
    cloned = stage/'verification/apple-passive-lifecycle-runtime-preparation'
    p = load(cloned/'prepare.py')
    # The sealed template embeds this archival path. Keep it literally; its
    # actual archives are rechecked by unchanged p.verify()/p.dispatch().
    archival = Path(json.loads((cloned/'selection-template.json').read_bytes())['productArchive']).parent
    p.BUILD_ATTEMPT = archival
    verified = p.verify()
    write(HERE/'preflight.json',dict(verified=verified, checkedFiles=len(rows),
         originalMetadataDrift=drift, originalsModified=False,
         staging='Independent byte-identical copies with sealed member modes; original files untouched',
         runtimeModulesModified=False, sourceOrProductModified=False,
         relocation=dict(repositoryRoot=str(stage),packetBase=str(cloned),
                         retainedLiteralBuildArchiveRoot=str(archival))))
    return cloned


def prepare():
    cloned = prepare_baseline()
    p = load(HERE/'dispatch_successor.py')
    result = p.verify()
    write(HERE/'successor-preflight.json', result)
    return p.BASE

def child():
    cloned = Path(sys.argv[2]); selection = Path(sys.argv[3])
    p = load(HERE/'dispatch_successor.py')
    assert cloned == p.BASE
    root = json.loads(selection.read_bytes())
    print(json.dumps(p.dispatch(root['packetSHA256'],str(selection),sha(selection.read_bytes()))),flush=True)

def main():
    if (HERE/'one-attempt-marker.json').exists(): raise RuntimeError('Never retry accepted Settings R2')
    write(HERE/'one-attempt-marker.json',dict(startedAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),oneAttemptOnly=True))
    device = None; name=None; baseline=None; failure=None; final=None; cleanup=[]
    try:
        identity = {}
        for name_,argv in [
            ('source-revision',['git','rev-parse','HEAD']),
            ('os',['/usr/bin/sw_vers']),
            ('kernel',['/usr/bin/uname','-a']),
            ('xcode',[DEV+'/usr/bin/xcodebuild','-version']),
            ('swift',['/usr/bin/xcrun','swiftc','--version']),
            ('sdk',['/usr/bin/xcrun','--sdk','iphonesimulator','--show-sdk-version']),
            ('python',[sys.executable,'--version'])]:
            identity[name_]=command(name_,argv).decode()
        identity['pythonExecutable']=str(Path(sys.executable).resolve())
        identity['pythonExecutableSHA256']=sha(Path(sys.executable).resolve().read_bytes())
        write(HERE/'environment.json',identity)
        cloned=prepare()
        runtimes=json.loads(command('runtimes',['/usr/bin/xcrun','simctl','list','runtimes','--json']))
        runtime=next(r for r in runtimes['runtimes'] if r['identifier']=='com.apple.CoreSimulator.SimRuntime.iOS-26-5')
        assert runtime['isAvailable'] and runtime['buildversion']=='23F77'
        baseline=json.loads(command('baseline-simulators',['/usr/bin/xcrun','simctl','list','devices','--json']))
        # Filter the one pinned frontend executable; never target historical held PIDs.
        def pinned_only(raw):
            return ('\n'.join(line.strip() for line in raw.decode().splitlines()
                    if line.strip().endswith(DEV+'/Applications/Simulator.app/Contents/MacOS/Simulator'))+'\n').encode()
        raw=command('baseline-frontends',['/bin/ps','-axo','pid=,lstart=,comm='],stdout_filter=pinned_only)
        frontends=[line.strip() for line in raw.decode().splitlines() if line.strip().endswith(DEV+'/Applications/Simulator.app/Contents/MacOS/Simulator')]
        runid=str(uuid.uuid4()); name='MixerFocusReferenceV9-'+runid
        write(HERE/'creation-intent.json',dict(name=name,runtime=runtime['identifier'],
              deviceType='com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro',baseline=baseline,
              maxNewDevices=1,phonesQueried=False))
        device=command('create',['/usr/bin/xcrun','simctl','create',name,
                     'com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro',runtime['identifier']]).decode().strip()
        assert str(uuid.UUID(device)).upper()==device
        selected=dict(schema='mixer.apple-focus-reference-root-selection.9',runID=runid,
          packetSHA256=sha((cloned/'packet.json').read_bytes()),
          selectedAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
          ownedSimulatorIdentity=dict(udid=device,name=name,runtime=runtime['identifier'],build='23F77'),
          sourceTreeSHA256='f402eba7b6fa8abf2671e3a95441351dace37f291a9d55024232c9112b2720fb',
          productArchiveSHA256='495f83c4702f7b229be495756f0a524c700f07159c5e21975dea471d118a8904',
          developerDirectory=DEV,baselineDevices=baseline,baselineFrontends=frontends)
        selection=HERE/'root-selection.json';write(selection,selected)
        command('dispatch',[sys.executable,'-B',str(Path(__file__).resolve()),'child',str(cloned),str(selection)],timeout=950)
    except BaseException as e:
        failure=dict(type=type(e).__name__,message=str(e),traceback=traceback.format_exc())
    finally:
        if baseline is not None:
            try:
                current=json.loads(command('cleanup-inventory',['/usr/bin/xcrun','simctl','list','devices','--json']))
                allrows=[r for v in current['devices'].values() for r in v]
                if device is None and name:
                    matches=[r for r in allrows if r['name']==name]
                    assert len(matches)<=1
                    if matches: device=matches[0]['udid']
                owned=next((r for r in allrows if r['udid']==device),None)
                if owned:
                    assert owned['name']==name
                    assert device not in {r['udid'] for v in baseline['devices'].values() for r in v}
                    if owned['state']!='Shutdown':
                        command('shutdown-owned',['/usr/bin/xcrun','simctl','shutdown',device]);cleanup.append('shutdown-owned')
                    command('delete-owned',['/usr/bin/xcrun','simctl','delete',device]);cleanup.append('delete-owned')
                final=json.loads(command('final-simulators',['/usr/bin/xcrun','simctl','list','devices','--json']))
            except BaseException as e: cleanup.append(dict(failure=repr(e)))
        results=dict(schema=1,failure=failure,ownedDevice=device,ownedName=name,
                     nativeMethodResults={'Settings':'Not run','Tab':'Not run'},
                     cleanupFallbackActions=cleanup,elapsedSeconds=time.monotonic()-START,
                     physicalPhones='disconnected; no discovery',gaAccepted=False)
        if final:
            after={r['udid']:r for v in final['devices'].values() for r in v}
            before={r['udid']:r for v in baseline['devices'].values() for r in v}
            results['ownedDeviceAbsent']=device not in after
            results['baselineStatesPreserved']=all(k in after and all(after[k].get(f)==r.get(f) for f in ['name','state','deviceTypeIdentifier']) for k,r in before.items())
            results['otherBootedDevicesPreserved']={k:after.get(k,{}).get('state') for k in ['CE7E80FC-64BF-41A0-B07B-60F4D8711808','D55C87E9-F349-49AC-BCD3-3B4B5BE9E010']}
        write(HERE/'attempt-result.json',results)
        print(json.dumps(results),flush=True)

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='child': child()
    else: main()
