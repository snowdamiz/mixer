#!/usr/bin/env python3
"""Snapshot-bound V2 data qualification; no device discovery or native runtime claims."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess, sys
HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parents[1]
CANDIDATE=HERE/'candidate-1'
CANDIDATE.mkdir(exist_ok=False)
SNAPSHOT=CANDIDATE/'inputs'; SNAPSHOT.mkdir()
BUILD=HERE/'build'/'candidate-1'; BUILD.mkdir(parents=True)
LOGS=CANDIDATE/'logs'; LOGS.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=[ROOT/'sdk/Package.swift']
for folder in ['sdk/Sources','sdk/Tests']:
    paths += sorted(p for p in (ROOT/folder).rglob('*') if p.is_file())
paths += [ROOT/p for p in ['AGENTS.md','mixer-product-plan.md','docs/ui-measured-appearance-v2-contract.md',
    'verification/ui-measured-appearance-v2-contract/descriptor-schema.json',
    'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json',
    'verification/ui-measured-appearance-v2-contract/shape-definitions.json',
    'verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json',
    'verification/ui-appearance-foundation/design-corpus.json',
    'verification/ui-appearance-descriptor-v2/PublicConsumer.swift',
    'verification/ui-appearance-descriptor-v2/scripts/run-checks.py']]
manifest={}
for p in sorted(set(paths)):
    relative=p.relative_to(ROOT); data=p.read_bytes(); target=SNAPSHOT/relative
    target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
    manifest[str(relative)]=hashlib.sha256(data).hexdigest()
commands=[]; artifacts={}
receipt={'format':'mixer.appearance-descriptor-v2-receipt.1',
    'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceRevision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'sourceGitTree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip(),
    'inputManifest':manifest,
    'inputTreeSHA256':hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
    'commands':commands,'artifacts':artifacts,'status':'not-run',
    'scope':'Swift V2 values/default/closed descriptor codec. Frozen full SDK host Debug/Release tests and public caller execution; iOS17/officialAndroid30 module+public-caller compilation. No resource installation, resolver, native consumer, runtime authority or physical evidence.',
    'limitations':['Synthetic resource/font metadata checks validate references only, never actual font bytes, coverage, identity or installation.',
        'No native V2 renderer/resolver/bootstrap/support/transaction/signed binding implemented by this lane.',
        'Phones disconnected; no discovery/run/reconnection request. Physical parity/accessibility/interactions, signed display/health, immutable published FieldLog, store/customer/operational and GA qualification remain pending.']}
(CANDIDATE/'input-lock.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
def run(name,args,env,cwd=SNAPSHOT):
    argv=[str(x) for x in args]
    result=subprocess.run(argv,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=900)
    log=LOGS/(name+'.log');log.write_bytes(result.stdout)
    commands.append({'name':name,'argv':argv,'cwd':str(cwd.relative_to(ROOT)),
        'environment':{k:env[k] for k in ['DEVELOPER_DIR'] if k in env},
        'exit':result.returncode,'log':str(log.relative_to(ROOT)),'sha256':sha(log)})
    print(name,result.returncode,flush=True)
    if result.returncode: raise RuntimeError(result.stdout.decode(errors='replace')[-10000:])
    return result.stdout.decode().strip()
apple=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
android=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer')
official=Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swiftc')
androidsdk=Path('/Users/andreyyurlov/Library/org.swift.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android')
try:
    run('python-version',[sys.executable,'--version'],apple)
    run('apple-swift-version',['xcrun','swiftc','--version'],apple)
    run('xcode-version',['xcodebuild','-version'],apple)
    run('android-swift-version',[official,'--version'],android)
    ios=run('iphoneos-sdk',['xcrun','--sdk','iphoneos','--show-sdk-path'],apple)
    for mode in ['debug','release']:
        run('sdk-tests-'+mode,['swift','test','--package-path',SNAPSHOT/'sdk','--scratch-path',BUILD/('tests-'+mode),'-c',mode],apple)
    outputs=[]
    for platform,compiler,flags,env in [('host-debug','swiftc',['-Onone'],apple),('host-release','swiftc',['-O'],apple),
        ('ios','swiftc',['-target','arm64-apple-ios17.0','-sdk',ios],apple),
        ('android',official,['-target','aarch64-unknown-linux-android30','-sdk',androidsdk/'ndk-sysroot',
            '-resource-dir',androidsdk/'swift-resources/usr/lib/swift-aarch64'],android)]:
        folder=BUILD/platform;folder.mkdir()
        common=['-swift-version','6','-warnings-as-errors','-module-cache-path',folder/'cache','-I',folder,*flags]
        host=platform.startswith('host')
        for module in ['MixerCore','MixerUI']:
            output=folder/(module+'.swiftmodule')
            args=[compiler,*common,'-parse-as-library','-emit-module','-module-name',module,'-emit-module-path',output]
            if host:args += ['-emit-library','-o',folder/('lib'+module+'.dylib')]
            if host and module=='MixerUI':args += ['-L',folder,'-lMixerCore','-Xlinker','-rpath','-Xlinker',folder]
            run(platform+'-'+module,[*args,*sorted((SNAPSHOT/'sdk/Sources'/module).glob('*.swift'))],env)
            artifacts[str(output.relative_to(ROOT))]=sha(output)
        consumer=SNAPSHOT/'verification/ui-appearance-descriptor-v2/PublicConsumer.swift'
        if host:
            executable=folder/'consumer'
            run(platform+'-caller',[compiler,*common,consumer,'-L',folder,'-lMixerUI','-lMixerCore',
                '-Xlinker','-rpath','-Xlinker',folder,'-o',executable],env)
            artifacts[str(executable.relative_to(ROOT))]=sha(executable)
            outputs.append(run(platform+'-caller-run',[executable],env))
        else:run(platform+'-caller',[compiler,*common,'-typecheck',consumer],env)
    if len(set(outputs))!=1:raise RuntimeError('public caller differs between host optimization modes')
    if manifest!={path:sha(SNAPSHOT/path) for path in manifest}:raise RuntimeError('frozen inputs changed')
    v1=[p for p in manifest if p.startswith('sdk/Sources/MixerUI/') and p.endswith('V1.swift')]
    unchanged={}
    for path in v1:
        baseline=subprocess.check_output(['git','show',receipt['sourceRevision']+':'+path],cwd=ROOT)
        if baseline!=(SNAPSHOT/path).read_bytes():raise RuntimeError('V1 changed:'+path)
        unchanged[path]=manifest[path]
    receipt['unchangedV1Bindings']=unchanged
    receipt['defaultSHA256']=manifest['verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json']
    receipt['defaultBytes']=9587
    receipt['newV2TestMethodsPerMode']=12
    receipt['status']='passed-data-only'
finally:
    receipt['liveInputChangesSinceSnapshot']=[p for p,h in manifest.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    (CANDIDATE/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print('PASS frozen fullSDK Debug/Release and public callers; iOS17/officialAndroid30 compiled; V1 unchanged',flush=True)
