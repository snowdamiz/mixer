#!/usr/bin/env python3
"""Finite host controls; exact observer with explicit UIKit double, no native UI."""
import datetime
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from common import BASE, ROOT, SOURCE, PRODUCER_SOURCE, SWIFT, DEV, REVISION
from common import binding, canonical, sha, payload, rows, materialize, archive_tree, tree, verify_inputs

OUT = BASE / 'finite'
SCRATCH = OUT / 'owned-host'
SDK = DEV / 'Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
COMMANDS = []
EXPLICIT = {'TMPDIR': str(SCRATCH / 'tmp') + '/', 'CLANG_MODULE_CACHE_PATH': str(SCRATCH / 'cache'),
            'SWIFT_MODULECACHE_PATH': str(SCRATCH / 'cache'), 'LC_ALL': 'C'}

def save(name, value): (OUT / name).write_bytes(canonical(value))

def members(group):
    r = subprocess.run(['/bin/ps', '-axo', 'pid=,pgid='], capture_output=True, timeout=10, check=True)
    assert not r.stderr
    return [int(s.split()[0]) for s in r.stdout.decode().splitlines() if int(s.split()[1]) == group]

def command(name, argv, seconds=60):
    argv = [str(x) for x in argv]
    stamp = time.monotonic()
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    env = os.environ.copy(); env.update(EXPLICIT)
    p = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timedout, signals = False, []
    try: out, err = p.communicate(timeout=seconds)
    except subprocess.TimeoutExpired:
        timedout = True
        if members(p.pid): os.killpg(p.pid, signal.SIGTERM); signals.append('SIGTERM')
        try: out, err = p.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            if members(p.pid): os.killpg(p.pid, signal.SIGKILL); signals.append('SIGKILL')
            out, err = p.communicate(timeout=5)
    for s, raw in [('stdout', out), ('stderr', err)]: (OUT / (name + '.' + s)).write_bytes(raw)
    COMMANDS.append({'name': name, 'argv': argv, 'cwd': str(ROOT), 'explicitEnvironment': EXPLICIT,
                     'startedUTC': started, 'elapsedSeconds': time.monotonic()-stamp, 'timeoutSeconds': seconds,
                     'exitCode': p.returncode, 'timedOut': timedout, 'signalsSent': signals,
                     'ownedPID': p.pid, 'ownedPGID': p.pid, 'processGroupAbsent': not members(p.pid),
                     'stdoutEOF': True, 'stderrEOF': True,
                     **{s: binding(OUT / (name+'.'+s)) for s in ['stdout','stderr']}})
    save('commands.json', COMMANDS)
    print(name + ': exit ' + str(p.returncode), flush=True)
    assert COMMANDS[-1]['processGroupAbsent']
    assert p.returncode == 0 and not timedout and not signals, err.decode(errors='replace')
    return out

def cleanup():
    before = SCRATCH.lstat()
    assert SCRATCH.is_dir() and not SCRATCH.is_symlink()
    assert all(not members(c['ownedPGID']) for c in COMMANDS)
    current = tree(SCRATCH)
    assert all((SCRATCH/n).lstat().st_nlink == 1 for n in current)
    r = subprocess.run(['/usr/sbin/lsof','-nP','+D',str(SCRATCH)],capture_output=True,timeout=30)
    for s, raw in [('stdout',r.stdout),('stderr',r.stderr)]: (OUT/('holders.'+s)).write_bytes(raw)
    assert r.returncode == 1 and not r.stdout and not r.stderr
    archive_rows = archive_tree(OUT/'host-scratch.tar.gz',SCRATCH)
    assert archive_rows == current
    after=SCRATCH.lstat()
    assert (before.st_dev,before.st_ino)==(after.st_dev,after.st_ino)
    assert all(not members(c['ownedPGID']) for c in COMMANDS)
    shutil.rmtree(SCRATCH)
    save('cleanup.json',{'ownedScratchPath':str(SCRATCH),'inodeStable':True,'regularFilesSingleLink':True,
                         'preservedScratchArchive':binding(OUT/'host-scratch.tar.gz'),
                         'preservedMembers':len(current),'preservedTreeSHA256':sha(canonical(current)),
                         'processGroupsAbsent':True,'stdoutStderrEOF':True,
                         'holderCommand':['/usr/sbin/lsof','-nP','+D',str(SCRATCH)],'holderExitCode':r.returncode,
                         'holdersAbsent':True,'ownedScratchRemoved':not SCRATCH.exists(),
                         'nativeInstancesTouched':0,'otherProjectsTouched':False})

def main():
    assert not OUT.exists(), 'Preserve all earlier finite evidence'
    OUT.mkdir(); SCRATCH.mkdir(); (SCRATCH/'cache').mkdir(); (SCRATCH/'tmp').mkdir()
    passed = False
    result = {}
    inputs = verify_inputs(); save('input-bindings-before.json',inputs)
    source = payload((ROOT/SOURCE).read_bytes()); producer = payload((ROOT/PRODUCER_SOURCE).read_bytes())
    member = 'accepted/source/Prototype/PassiveLifecycleObserver.swift'
    helper = 'accepted/source/Prototype/PassiveLifecycleData.swift'
    host_files = {
        'corrected-observer.swift': source[member], 'producer-observer.swift': producer[member],
        'PassiveLifecycleData.swift': source[helper],
        'UIKitDouble.swift':((BASE/'UIKitDouble.swift').read_bytes(),0o444),
        'SemanticTests.swift':((BASE/'SemanticTests.swift').read_bytes(),0o444),
        'HostTests.swift':((ROOT/'verification/apple-passive-lifecycle-observer/HostTests.swift').read_bytes(),0o444),
        'HostReview.swift':((ROOT/'verification/apple-passive-lifecycle-review/HostReview.swift').read_bytes(),0o444)
    }
    original = ROOT/'verification/apple-focus-system-runtime-preparation/native-run-v8-d9a1ae2b-ef02-4db2-b2ff-4979213c8236/runtime/captures/0001-after-1.json'
    for n,(raw,mode) in host_files.items(): (SCRATCH/n).write_bytes(raw); (SCRATCH/n).chmod(mode)
    bindings = {'inputs':rows(host_files),'historicalOriginalCapture':binding(original),'swift':binding(SWIFT.resolve()),
                'sdkRequested':str(SDK),'sdkResolved':str(SDK.resolve()),'sdkSettings':binding(SDK.resolve()/'SDKSettings.json')}
    save('source-tool-bindings.json',bindings)
    try:
        command('swift-version',[SWIFT,'--version'])
        prefix=[SWIFT,'-sdk',SDK,'-target','arm64-apple-macosx26.0','-module-cache-path',SCRATCH/'cache','-parse-as-library']
        command('compile-UIKit-double',[*prefix,'-swift-version','6','-module-name','UIKit','-emit-module','-emit-module-path',SCRATCH/'UIKit.swiftmodule','-emit-library',SCRATCH/'UIKitDouble.swift','-o',SCRATCH/'libUIKit.dylib'])
        for label,version,observer in [('corrected','6','corrected-observer.swift'),('producer-baseline','5','producer-observer.swift')]:
            command('compile-'+label,[*prefix,'-swift-version',version,'-I',SCRATCH,'-L',SCRATCH,'-lUIKit','-Xlinker','-rpath','-Xlinker','@executable_path',SCRATCH/'PassiveLifecycleData.swift',SCRATCH/observer,SCRATCH/'SemanticTests.swift','-o',SCRATCH/(label+'-tests')])
            raw=command('execute-'+label,[SCRATCH/(label+'-tests')],30)
            result[label]=json.loads(raw.decode().splitlines()[-1])
        assert result['corrected']==result['producer-baseline'], 'Observable semantic transcript differs from original'
        for label,filename in [('producer-Foundation','HostTests.swift'),('independent-Foundation','HostReview.swift')]:
            command('compile-'+label,[*prefix,'-swift-version','6',SCRATCH/'PassiveLifecycleData.swift',SCRATCH/filename,'-o',SCRATCH/(label+'-tests')])
            raw=command('execute-'+label,[SCRATCH/(label+'-tests'),original],30)
            result[label]=json.loads(raw.decode().splitlines()[-1])
        assert all(v['passed'] for v in result.values())
        assert verify_inputs()==inputs
        assert binding(SWIFT.resolve())==bindings['swift']
        assert binding(SDK.resolve()/'SDKSettings.json')==bindings['sdkSettings']
        save('input-bindings-after.json',inputs)
        save('semantic-results.json',result)
        passed=True
    finally:
        cleanup()
        save('receipt.json',{'schema':1,'passed':passed,'sourceContextRevisionReportedByRoot':REVISION,
                             'correctedSourceArchive':binding(ROOT/SOURCE),'testedSources':bindings,
                             'results':result,'differentialSemanticOutputsEqual':passed and result.get('corrected')==result.get('producer-baseline'),
                             'scope':'Finite macOS exact adapter plus UIKit double, original Swift 5 comparison, unchanged Foundation controls',
                             'realUIKitCompiled':False,'realUIKitExecuted':False,'genericBuildsDuringFiniteControls':0,
                             'nativeExecutions':0,'nativeQueries':0,'physicalPhones':'disconnected-deferred',
                             'ownedHostScratchRemoved':not SCRATCH.exists()})
    print(json.dumps({'passed':passed,'semanticChecksPerAdapter':result['corrected']['checks'],
                      'FoundationChecks':[result['producer-Foundation']['checks'],result['independent-Foundation']['checks']],
                      'differentialSemanticOutputsEqual':True}),flush=True)

if __name__=='__main__': main()
