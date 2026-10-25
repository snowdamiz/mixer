#!/usr/bin/env python3
"""Independent bounded review driver. No network or native runtime commands."""
import datetime,hashlib,json,os,pathlib,shutil,signal,subprocess,sys,time,tarfile,stat,plistlib
B=pathlib.Path(__file__).resolve().parent
ROOT=B.parents[1]
DEV=pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer')
SWIFT=DEV/'Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc'
sha=lambda data:hashlib.sha256(data).hexdigest()
def save(name,value):(B/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def run(argv,label,timeout=55):
    began=time.monotonic();started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    p=subprocess.Popen([str(x) for x in argv],cwd=B,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    signals=[];timedout=False
    try: out,err=p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timedout=True;os.killpg(p.pid,signal.SIGTERM);signals.append('SIGTERM')
        try:out,err=p.communicate(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);signals.append('SIGKILL');out,err=p.communicate(timeout=5)
    try:os.killpg(p.pid,0);empty=False
    except ProcessLookupError:empty=True
    folder=B/'commands';folder.mkdir(exist_ok=True)
    (folder/(label+'.stdout')).write_bytes(out);(folder/(label+'.stderr')).write_bytes(err)
    row=dict(argv=[str(x) for x in argv],cwd=str(B),startedUTC=started,exitCode=p.returncode,elapsedSeconds=time.monotonic()-began,timeoutSeconds=timeout,timedOut=timedout,ownedPID=p.pid,ownedPGID=p.pid,signals=signals,ownedGroupEmpty=empty,stdoutEOF=True,stderrEOF=True,stdoutSHA256=sha(out),stderrSHA256=sha(err))
    save('commands/'+label+'.json',row)
    assert p.returncode==0 and not timedout and empty,(label,row,err.decode()[:3000])
    return out
def main():
    action=sys.argv[1]
    if action=='audit':run([sys.executable,'-B',B/'audit.py'],'audit')
    elif action=='receiver':run([sys.executable,'-B',B/'controls.py'],'receiver')
    elif action=='foundation':
        scratch=B/'owned-host';scratch.mkdir(exist_ok=False)
        try:
            run([sys.executable,'-B',B/'generate_probe.py'],'generate-probe')
            shutil.copyfile(B/'independent-probe.swift',scratch/'main.swift')
            run([SWIFT,'--version'],'swift-version',15)
            argv=[SWIFT,'-sdk',DEV/'Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk','-target','arm64-apple-macosx26.0','-module-cache-path',scratch/'module-cache',scratch/'main.swift']
            argv += [B/'sources/accepted/harness/UITests'/n for n in ['DiagnosticTransport.swift','SettingsFailureDiagnostic.swift']]
            argv += ['-o',scratch/'probe']
            run(argv,'foundation-compile');run([scratch/'probe'],'foundation-execute',20)
        finally:
            shutil.rmtree(scratch)
            save('foundation-cleanup.json',{'ownedScratch':str(scratch),'removed':not scratch.exists(),'compilerSHA256':sha(SWIFT.read_bytes())})
    elif action=='typecheck':
        scratch=B/'owned-typecheck';scratch.mkdir(exist_ok=False)
        names=['DiagnosticTransport.swift','SettingsFailureDiagnostic.swift','ToggleUITests.swift','PublicSwitchSelection.swift']
        rows={}
        for n in names:
            source=B/'sources/accepted/harness/UITests'/n
            shutil.copyfile(source,scratch/n);rows[n]=sha(source.read_bytes())
        previous=ROOT/'verification/apple-settings-failure-instrumentation-root-review/attempts/typecheck-2/typecheck-receipt.json'
        sdk=DEV/'Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator.sdk'
        argv=[SWIFT,'-typecheck','-target','arm64-apple-ios26.0-simulator','-sdk',sdk,'-F',DEV/'Platforms/iPhoneSimulator.platform/Developer/Library/Frameworks','-I',DEV/'Platforms/iPhoneSimulator.platform/Developer/usr/lib','-module-cache-path',scratch/'module-cache','-module-name','MixerSettingsDiagnostic']+[scratch/n for n in names]
        try:
            run(argv,'typecheck')
            assert all(sha((scratch/n).read_bytes())==v for n,v in rows.items())
            save('typecheck.json',dict(passed=True,exactSourceHashes=rows,compilerSHA256=sha(SWIFT.read_bytes()),sdkResolved=str(sdk.resolve()),sdkSettingsSHA256=sha((sdk/'SDKSettings.json').read_bytes()),priorFlagsReceiptSHA256=sha(previous.read_bytes()),minimumTarget='iOS 26.0 simulator arm64',nativeProductBuild=False,nativeExecuted=False,deviceQuery=False))
        finally:shutil.rmtree(scratch);save('typecheck-cleanup.json',{'ownedScratchAbsent':not scratch.exists()})
    elif action=='cleanup':
        scratch=B/'synthetic-attempts'
        manifest={}
        for path in sorted(scratch.rglob('*')):
            mode=path.lstat().st_mode;row={'kind':'symlink' if stat.S_ISLNK(mode) else 'directory' if stat.S_ISDIR(mode) else 'file','mode':stat.S_IMODE(mode)}
            if row['kind']=='file':raw=path.read_bytes();row.update(bytes=len(raw),sha256=sha(raw))
            if row['kind']=='symlink':row['target']=os.readlink(path)
            manifest[str(path.relative_to(B))]=row
        save('synthetic-evidence-manifest.json',manifest)
        with tarfile.open(B/'independent-synthetic-evidence.tar.gz','w:gz',dereference=False) as tf:tf.add(scratch,arcname='synthetic-attempts',recursive=True)
        count=sum(1 for x in scratch.rglob('*') if x.is_file())
        shutil.rmtree(scratch)
        save('cleanup.json',dict(ownedStoresArchived=True,archiveSHA256=sha((B/'independent-synthetic-evidence.tar.gz').read_bytes()),files=count,ownedScratchAbsent=not scratch.exists(),otherProjectsChanged=False,listeners=0,nativeRuntimeCommands=0,physicalPhones='disconnected-deferred'))
    elif action=='environment':
        run([sys.executable,'--version'],'python-version',10)
        run(['/usr/bin/sw_vers'],'os-version',10)
        run([SWIFT,'--version'],'swift-version-final',15)
        sdk=DEV/'Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator.sdk'
        mac=DEV/'Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
        save('environment.json',dict(python=sys.version,pythonExecutable=sys.executable,pythonExecutableSHA256=sha(pathlib.Path(sys.executable).read_bytes()),swiftCompilerSHA256=sha(SWIFT.read_bytes()),xcode=plistlib.loads((DEV.parent/'version.plist').read_bytes()),iOSSDK=json.loads((sdk/'SDKSettings.json').read_bytes()),macOSSDK=json.loads((mac/'SDKSettings.json').read_bytes()),rootRevisionSuppliedByController='be472ce6424a691de5673e3438d2768264827d23',gitOperations=False))
    else:raise ValueError(action)
if __name__=='__main__':main()
