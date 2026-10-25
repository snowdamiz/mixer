#!/usr/bin/env python3
"""Independent narrow macOS controls; no generic build or native commands."""
import datetime
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUT = BASE / 'controls'
SCRATCH = OUT / 'owned-host'
PRODUCER = ROOT / 'verification/apple-passive-lifecycle-sendable-correction'
ARCHIVE = PRODUCER / 'review-source-package.tar.gz'
ORIGINAL = ROOT / 'verification/apple-passive-lifecycle-observer/review-source-package.tar.gz'
SWIFT = Path('/Applications/Xcode_26.6.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc')
SDK = Path('/Applications/Xcode_26.6.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
COMMANDS = []
ENV = {'TMPDIR': str(SCRATCH / 'tmp') + '/', 'CLANG_MODULE_CACHE_PATH': str(SCRATCH / 'cache'),
       'SWIFT_MODULECACHE_PATH': str(SCRATCH / 'cache'), 'LC_ALL': 'C'}

def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(x): return (json.dumps(x, indent=2, sort_keys=True) + '\n').encode()
def binding(p):
    s=p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
    b=p.read_bytes()
    return {'kind':'file','mode':stat.S_IMODE(s.st_mode),'bytes':len(b),'sha256':sha(b)}
def save(n,x): (OUT/n).write_bytes(canonical(x))
def archive(p):
    result={}
    with tarfile.open(fileobj=io.BytesIO(p.read_bytes()), mode='r:gz') as t:
        for m in t:
            n=PurePosixPath(m.name)
            assert m.name and not n.is_absolute() and '..' not in n.parts and str(n)==m.name
            assert m.name not in result and m.isfile()
            result[m.name]=(t.extractfile(m).read(),m.mode)
    return result
def members(group):
    r=subprocess.run(['/bin/ps','-axo','pid=,pgid='],capture_output=True,timeout=10,check=True)
    return [int(s.split()[0]) for s in r.stdout.decode().splitlines() if int(s.split()[1])==group]
def command(name,argv,seconds=60):
    argv=[str(x) for x in argv]; start=time.monotonic()
    env=os.environ.copy(); env.update(ENV)
    p=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    timeout=False; signals=[]
    try: out,err=p.communicate(timeout=seconds)
    except subprocess.TimeoutExpired:
        timeout=True
        if members(p.pid): os.killpg(p.pid,signal.SIGTERM); signals.append('SIGTERM')
        try: out,err=p.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            if members(p.pid): os.killpg(p.pid,signal.SIGKILL); signals.append('SIGKILL')
            out,err=p.communicate(timeout=5)
    for suffix,raw in [('stdout',out),('stderr',err)]: (OUT/(name+'.'+suffix)).write_bytes(raw)
    COMMANDS.append({'name':name,'argv':argv,'cwd':str(ROOT),'explicitEnvironment':ENV,'timeoutSeconds':seconds,
                     'elapsedSeconds':time.monotonic()-start,'exitCode':p.returncode,'timedOut':timeout,
                     'signalsSent':signals,'ownedPID':p.pid,'ownedPGID':p.pid,'processGroupAbsent':not members(p.pid),
                     'stdoutEOF':True,'stderrEOF':True,**{s:binding(OUT/(name+'.'+s)) for s in ['stdout','stderr']}})
    save('commands.json',COMMANDS)
    print(name+': exit '+str(p.returncode),flush=True)
    assert p.returncode==0 and not timeout and not signals and COMMANDS[-1]['processGroupAbsent'],err.decode(errors='replace')
    return out
def main():
    assert not OUT.exists(),'Preserve prior review controls'
    OUT.mkdir(); SCRATCH.mkdir(); (SCRATCH/'cache').mkdir(); (SCRATCH/'tmp').mkdir()
    expected='bf31888a14490e83e2424f458eac0cf8f56258d581ff2fc4034840b0d1783663'
    assert binding(ARCHIVE)['sha256']==expected
    corrected=archive(ARCHIVE); original=archive(ORIGINAL)
    observer='accepted/source/Prototype/PassiveLifecycleObserver.swift'
    data='accepted/source/Prototype/PassiveLifecycleData.swift'
    assert set(corrected)==set(original) and [n for n in corrected if corrected[n]!=original[n]]==[observer]
    files={'corrected.swift':corrected[observer], 'original.swift':original[observer], 'Data.swift':corrected[data],
           'UIKitDouble.swift':((PRODUCER/'UIKitDouble.swift').read_bytes(),0o444),
           'BoundaryControls.swift':((BASE/'BoundaryControls.swift').read_bytes(),0o444)}
    before={'candidateArchive':binding(ARCHIVE),'originalArchive':binding(ORIGINAL),
            'sources':{n:{'sha256':sha(b),'bytes':len(b),'mode':m} for n,(b,m) in files.items()},
            'swiftRequested':str(SWIFT),'swiftResolved':str(SWIFT.resolve()),'swift':binding(SWIFT.resolve()),
            'sdkRequested':str(SDK),'sdkResolved':str(SDK.resolve()),'sdkSettings':binding(SDK.resolve()/'SDKSettings.json'),
            'sourceRevisionReportedByRoot':'6b8aba350224ed19f678669bdbea6b359d8de68b','gitQueried':False}
    save('driver-command.json',{'argv':[sys.executable,'-B',str(BASE/'run_controls.py')],
                                'cwd':str(ROOT),'driver':binding(BASE/'run_controls.py'),'python':sys.version})
    save('bindings-before.json',before)
    for n,(b,m) in files.items(): (SCRATCH/n).write_bytes(b); (SCRATCH/n).chmod(m)
    passed=False; results={}
    try:
        command('python-version',[sys.executable,'--version'])
        command('swift-version',[SWIFT,'--version'])
        prefix=[SWIFT,'-sdk',SDK,'-target','arm64-apple-macosx26.0','-module-cache-path',SCRATCH/'cache','-parse-as-library']
        command('compile-double',[*prefix,'-swift-version','6','-module-name','UIKit','-emit-module','-emit-module-path',SCRATCH/'UIKit.swiftmodule','-emit-library',SCRATCH/'UIKitDouble.swift','-o',SCRATCH/'libUIKit.dylib'])
        for label,version in [('corrected','6'),('original','5')]:
            command('compile-'+label,[*prefix,'-swift-version',version,'-I',SCRATCH,'-L',SCRATCH,'-lUIKit','-Xlinker','-rpath','-Xlinker','@executable_path',SCRATCH/'Data.swift',SCRATCH/(label+'.swift'),SCRATCH/'BoundaryControls.swift','-o',SCRATCH/(label+'-controls')])
            results[label]=json.loads(command('execute-'+label,[SCRATCH/(label+'-controls')],30).decode().splitlines()[-1])
        assert results['corrected']==results['original']
        assert binding(ARCHIVE)==before['candidateArchive'] and binding(ORIGINAL)==before['originalArchive']
        assert binding(SWIFT.resolve())==before['swift'] and binding(SDK.resolve()/'SDKSettings.json')==before['sdkSettings']
        save('bindings-after.json',before)
        passed=True
    finally:
        assert all(not members(c['ownedPGID']) for c in COMMANDS)
        first=SCRATCH.lstat()
        r=subprocess.run(['/usr/sbin/lsof','-nP','+D',str(SCRATCH)],capture_output=True,timeout=30)
        for s,b in [('stdout',r.stdout),('stderr',r.stderr)]: (OUT/('holders.'+s)).write_bytes(b)
        assert r.returncode==1 and not r.stdout and not r.stderr
        entries={str(p.relative_to(SCRATCH)):binding(p) for p in sorted(SCRATCH.rglob('*')) if p.is_file()}
        assert all((SCRATCH/n).lstat().st_nlink==1 for n in entries)
        save('scratch-manifest.json',entries)
        second=SCRATCH.lstat(); assert (first.st_dev,first.st_ino)==(second.st_dev,second.st_ino)
        assert all(not members(c['ownedPGID']) for c in COMMANDS)
        shutil.rmtree(SCRATCH)
        save('cleanup.json',{'ownedScratchPath':str(SCRATCH),'inodeStable':True,'processGroupsAbsent':True,
                             'stdoutStderrEOF':True,'regularFilesSingleLink':True,'holdersAbsent':True,
                             'holderCommand':['/usr/sbin/lsof','-nP','+D',str(SCRATCH)],'holderExitCode':r.returncode,
                             'ownedScratchRemoved':not SCRATCH.exists(),'nativeInstancesTouched':0,'otherProjectsTouched':False})
        save('receipt.json',{'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                             'passed':passed,'results':results,'normalizedResultsEqual':passed and results.get('corrected')==results.get('original'),
                             'sourcesAndTools':before,'ownedScratchRemoved':not SCRATCH.exists(),
                             'genericBuilds':0,'nativeQueries':0,'nativeExecutions':0,'realUIKitExecuted':False,
                             'scope':'Independent narrow finite macOS controls; exact archived adapter and Foundation data, explicit UIKit double',
                             'physicalPhones':'disconnected-deferred'})
    print(json.dumps({'passed':passed,'results':results}),flush=True)

if __name__=='__main__': main()
