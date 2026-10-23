from pathlib import Path
import hashlib,json,os,subprocess,datetime
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
out=HERE/'build'/'module-check';out.mkdir(exist_ok=False)
snapshot=HERE/'inputs';snapshot.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=[p for name in ['MixerCore','MixerUI'] for p in (ROOT/'sdk/Sources'/name).glob('*.swift')]
paths += [HERE/'PublicConsumer.swift',HERE/'compile.py',ROOT/'verification/apple-appearance-font-profile/type-profiles.json',ROOT/'sdk/Tests/MixerUITests/SharedTextProfilesV1Tests.swift']
manifest={str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}
for p in paths:
    target=snapshot/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
commands=[];artifacts={}
def run(name,argv,env=None):
    p=subprocess.run([str(x) for x in argv],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
    log=HERE/(name+'.log');log.write_bytes(p.stdout)
    commands.append({'name':name,'command':[str(x) for x in argv],'environment':{k:env[k] for k in ['DEVELOPER_DIR'] if env and k in env},'exit':p.returncode,'log':str(log.relative_to(ROOT)),'sha256':sha(log)})
    print(name,p.returncode,flush=True);assert p.returncode==0,p.stdout.decode()
    return p.stdout.decode()
apple=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
android=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer')
official=Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swiftc')
sdk=Path('/Users/andreyyurlov/Library/org.swift.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android')
outputs=[]
try:
    run('apple-swift-version',['xcrun','swiftc','--version'],apple)
    run('android-swift-version',[official,'--version'],android)
    ios=run('iphoneos-sdk',['xcrun','--sdk','iphoneos','--show-sdk-path'],apple).strip()
    for platform,compiler,flags,env in [('host-debug','swiftc',['-Onone'],apple),('host-release','swiftc',['-O'],apple),('ios','swiftc',['-target','arm64-apple-ios17.0','-sdk',ios],apple),('android',official,['-target','aarch64-unknown-linux-android30','-sdk',sdk/'ndk-sysroot','-resource-dir',sdk/'swift-resources/usr/lib/swift-aarch64'],android)]:
        folder=out/platform;folder.mkdir();host=platform.startswith('host')
        common=['-swift-version','6','-warnings-as-errors','-module-cache-path',folder/'cache','-I',folder,*flags]
        for module in ['MixerCore','MixerUI']:
            output=folder/(module+'.swiftmodule')
            args=[compiler,*common,'-parse-as-library','-emit-module','-module-name',module,'-emit-module-path',output]
            if host:args += ['-emit-library','-o',folder/('lib'+module+'.dylib')]
            run(platform+'-'+module,args+sorted((snapshot/'sdk/Sources'/module).glob('*.swift')),env)
            artifacts[str(output.relative_to(ROOT))]=sha(output)
        consumer=snapshot/'verification/ui-shared-text-profiles/PublicConsumer.swift'
        if host:
            exe=folder/'consumer'
            run(platform+'-consumer',[compiler,*common,consumer,'-L',folder,'-lMixerUI','-lMixerCore','-Xlinker','-rpath','-Xlinker',folder,'-o',exe],env)
            artifacts[str(exe.relative_to(ROOT))]=sha(exe)
            outputs.append(run(platform+'-run',[exe],env))
        else:run(platform+'-consumer',[compiler,*common,'-typecheck',consumer],env)
    assert outputs[0]==outputs[1]
    profiles=json.loads((snapshot/'verification/apple-appearance-font-profile/type-profiles.json').read_text())['profiles']
    rows={p['normalizedProfileID']:p for p in profiles};anchors=[int(p['fonts']['body']['size']*64) for p in profiles]
    metric_count=selection_count=0
    for line in outputs[0].splitlines():
        v=line.split()
        if v[0]=='METRIC':
            role=v[2];p=rows[v[1]];observed=p['actualExpandedNavigationUIFont'] if role=='navigationExpanded' else p['fonts']['sectionHeaderCandidate' if role=='sectionHeader' else role]
            assert int(v[3])==round(observed['pointSize']*64)
            expected_weight=700 if role=='navigationExpanded' else 600 if role in ['headline','sectionHeader'] else 400
            assert int(v[4])==expected_weight;metric_count+=1
        else:
            assert v[0]=='SELECT';n=int(v[1])
            best='unsupported' if n<anchors[0] or n>anchors[-1] else profiles[min(range(12),key=lambda i:(abs(n-anchors[i]),-i))]['normalizedProfileID']
            assert v[2]==best;selection_count+=1
    assert metric_count==72 and selection_count==3502
    assert manifest=={p:sha(ROOT/p) for p in manifest}=={p:sha(snapshot/p) for p in manifest}
finally:
    (HERE/'module-receipt.json').write_text(json.dumps({'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_manifest':manifest,'source_tree_sha256':hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest(),'commands':commands,'artifacts':artifacts,'scope':'Public caller module compilation on iOS17 target and official Android30 toolchain; host Debug/Release outputs compared directly with accepted native reference tables and independent distance selector. No native renderer/preference/device or signed qualification.'},indent=2)+'\n')
print('PASS72actual measured metrics +3502selection outcomes perhostmode;public iOS/Android compilation')
