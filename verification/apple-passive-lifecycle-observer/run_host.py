#!/usr/bin/env python3
"""Finite macOS Foundation tests only. No UIKit compilation or native query."""
import datetime, hashlib, json, os, pathlib, shutil, subprocess, tarfile, time
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SWIFT=pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc')
SDK=pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
sha=lambda b:hashlib.sha256(b).hexdigest()
def stable(v):return (json.dumps(v,indent=2,sort_keys=True)+'\n').encode()
scratch=HERE/'.host-work';assert not scratch.exists();scratch.mkdir();(scratch/'cache').mkdir();(scratch/'tmp').mkdir()
attempt=HERE/'host-tests';assert not attempt.exists();attempt.mkdir()
env=os.environ.copy();explicit={'TMPDIR':str(scratch/'tmp')+'/', 'CLANG_MODULE_CACHE_PATH':str(scratch/'cache'), 'SWIFT_MODULECACHE_PATH':str(scratch/'cache'), 'LC_ALL':'C'};env.update(explicit)
source_name='accepted/source/Prototype/PassiveLifecycleData.swift'
with tarfile.open(HERE/'review-source-package.tar.gz') as t:data=t.extractfile(source_name).read()
(scratch/'PassiveLifecycleData.swift').write_bytes(data)
sources={source_name:{'bytes':len(data),'sha256':sha(data)},'HostTests.swift':{'bytes':(HERE/'HostTests.swift').stat().st_size,'sha256':sha((HERE/'HostTests.swift').read_bytes())}}
commands=[]
def run(name,argv,timeout=55):
    started=datetime.datetime.now(datetime.timezone.utc).isoformat();start=time.monotonic();timedout=False
    try:
        p=subprocess.run([str(x) for x in argv],cwd=HERE,env=env,capture_output=True,timeout=timeout);out,err,code=p.stdout,p.stderr,p.returncode
    except subprocess.TimeoutExpired as e:out,err,code=e.stdout or b'',e.stderr or b'',None;timedout=True
    (attempt/(name+'.stdout')).write_bytes(out);(attempt/(name+'.stderr')).write_bytes(err)
    commands.append({'name':name,'argv':[str(x) for x in argv],'cwd':str(HERE),'explicitEnvironment':explicit,'startedUTC':started,'elapsedSeconds':time.monotonic()-start,'timeoutSeconds':timeout,'timedOut':timedout,'exitCode':code,'stdoutSHA256':sha(out),'stderrSHA256':sha(err),'sourceArchiveSHA256':sha((HERE/'review-source-package.tar.gz').read_bytes()),'sourceTreeSHA256':sha(stable(sources))})
    (attempt/'commands.json').write_bytes(stable(commands))
    print(json.dumps({'command':name,'exitCode':code,'stderrBytes':len(err),'stdoutBytes':len(out)}),flush=True)
    assert code==0,err.decode(errors='replace')
    return out
passed=False;summary=None
try:
    version=run('swift-version',[SWIFT,'--version'])
    run('compile-foundation-host',[SWIFT,'-swift-version','6','-sdk',SDK,'-target','arm64-apple-macosx26.0','-module-cache-path',scratch/'cache','-parse-as-library',scratch/'PassiveLifecycleData.swift',HERE/'HostTests.swift','-o',scratch/'host-tests'])
    original=ROOT/'verification/apple-focus-system-runtime-preparation/native-run-v8-d9a1ae2b-ef02-4db2-b2ff-4979213c8236/runtime/captures/0001-after-1.json'
    output=run('execute-foundation-host',[scratch/'host-tests',original])
    summary=json.loads(output.decode().splitlines()[-1]);passed=summary['passed']
finally:
    shutil.rmtree(scratch)
    receipt={'schema':1,'passed':passed,'summary':summary,'sourceContextRevision':'6b8aba350224ed19f678669bdbea6b359d8de68b','sourceArchiveSHA256':sha((HERE/'review-source-package.tar.gz').read_bytes()),'testedSources':sources,'scope':'macOS Foundation serialization, finite data/filter/ownership/token tests only','uikitCompiled':False,'genericSimulatorBuilds':0,'nativeExecutions':0,'nativeQueries':0,'phones':'disconnected-deferred','ownedHostScratchRemoved':not scratch.exists()}
    (attempt/'receipt.json').write_bytes(stable(receipt));print(json.dumps(receipt,sort_keys=True),flush=True)
