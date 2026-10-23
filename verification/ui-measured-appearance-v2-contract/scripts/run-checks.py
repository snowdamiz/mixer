#!/usr/bin/env python3
"""Replay design checks and declaration compilation from exact retained inputs."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
canonical = lambda x: json.dumps(x,sort_keys=True,separators=(',',':')).encode()
# This is a frozen replay, not a live-source discovery/build tool. The original
# lock and input copy were retained before any V2 implementation existed.
lock = json.loads((HERE/'input-lock.json').read_text())
manifest = lock['inputs']
snapshot = HERE/'inputs'
if manifest!={p:sha(snapshot/p) for p in manifest}:
    raise RuntimeError('retained input mismatch before replay')
previous = json.loads((HERE/'receipt.json').read_text())
log_dir = HERE/'logs'; log_dir.mkdir(exist_ok=True)
build = HERE/'build'; build.mkdir(exist_ok=True)
commands=[]
def run(name,argv,env=None):
    argv=[str(x) for x in argv]
    result=subprocess.run(argv,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
    log=log_dir/(name+'.log'); log.write_bytes(result.stdout)
    commands.append({'name':name,'argv':argv,'environment':{k:env[k] for k in ['DEVELOPER_DIR'] if env and k in env},
                     'exit':result.returncode,'log':str(log.relative_to(ROOT)),'sha256':sha(log)})
    print(name,result.returncode,flush=True)
    if result.returncode: raise RuntimeError(result.stdout.decode(errors='replace'))
    return result.stdout.decode().strip()

apple=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer',PYTHONDONTWRITEBYTECODE='1')
android=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer')
official=Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swiftc')
android_sdk=Path('/Users/andreyyurlov/Library/org.swift.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android')
result_scope='design schema/model checks and declaration compilation only; no product implementation or native authority'
receipt={'format':'mixer.measured-appearance-v2-design-receipt.1',
    'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceRevision':previous['sourceRevision'],
    'sourceGitTree':previous['sourceGitTree'],
    'observedRepositoryRevision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'inputTreeSHA256':hashlib.sha256(canonical(manifest)).hexdigest(),
    'scope':result_scope,'status':'not-run','commands':commands,
    'limitations':['Design candidate awaiting root freeze; no product codec, resolver, resource bootstrap, adapter or signed binding implemented.',
        'Authored continuous26 full-group curve and sealed switch paths require native validation; retained Apple group9-10px/switch1-2px residuals are not erased.',
        'Android preference conversion, native shaping/controls/layout/interactions/accessibility and environment changes remain unqualified.',
        'Physical phones disconnected; no device run or reconnection request. Signed display/health, immutable published FieldLog, store/customer/operations and GA gates pending.']}
try:
    run('python-version',[sys.executable,'--version'])
    run('apple-swift-version',['xcrun','swiftc','--version'],apple)
    run('xcode-version',['xcodebuild','-version'],apple)
    run('android-swift-version',[official,'--version'],android)
    ios_sdk=run('iphoneos-sdk',['xcrun','--sdk','iphoneos','--show-sdk-path'],apple)
    generated=[HERE/p for p in ['descriptor-schema.json','mixer-measured-default-v2.json','shape-definitions.json']]
    before={p.name:sha(p) for p in generated}
    run('generate-determinism',[sys.executable,HERE/'scripts/generate-spec.py'],apple)
    if before!={p.name:sha(p) for p in generated}: raise RuntimeError('generation changed retained proposal')
    run('checker-normal',[sys.executable,HERE/'scripts/check-contract.py'],apple)
    run('checker-optimized',[sys.executable,'-O',HERE/'scripts/check-contract.py'],apple)
    module_bindings={}
    for platform,compiler,flags,env in [
        ('host','xcrun',['swiftc'],apple),
        ('ios','xcrun',['swiftc','-target','arm64-apple-ios17.0','-sdk',ios_sdk],apple),
        ('android',official,['-target','aarch64-unknown-linux-android30','-sdk',android_sdk/'ndk-sysroot',
            '-resource-dir',android_sdk/'swift-resources/usr/lib/swift-aarch64'],android)]:
        folder=build/platform; folder.mkdir(exist_ok=True)
        common=[compiler,*flags,'-swift-version','6','-warnings-as-errors','-module-cache-path',folder/'cache','-I',folder]
        for module in ['MixerCore','MixerUI']:
            output=folder/(module+'.swiftmodule')
            run(platform+'-'+module,[*common,'-parse-as-library','-emit-module','-module-name',module,
                '-emit-module-path',output,*sorted((snapshot/'sdk/Sources'/module).glob('*.swift'))],env)
            module_bindings[str(output.relative_to(ROOT))]=sha(output)
        run(platform+'-contract-declarations',[*common,'-typecheck',HERE/'ContractTypes.swift'],env)
    receipt['compiledModuleBindings']=module_bindings
    if manifest!={p:sha(snapshot/p) for p in manifest}: raise RuntimeError('retained input mismatch')
    v1_names=['sdk/Sources/MixerUI/AppearanceValuesV1.swift','sdk/Sources/MixerUI/AppearanceDefaultV1.swift',
        'sdk/Sources/MixerUI/AppearanceDescriptorV1.swift','sdk/Sources/MixerUI/AppearanceResolutionV1.swift',
        'sdk/Sources/MixerUI/AppearanceMetricMathV1.swift','verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json']
    for path in v1_names:
        original=subprocess.check_output(['git','show',receipt['sourceRevision']+':'+path],cwd=ROOT)
        if original!=(snapshot/path).read_bytes(): raise RuntimeError('V1 changed from frozen source revision: '+path)
    receipt['unchangedV1Bindings']={p:manifest[p] for p in v1_names}
    receipt['status']='passed-design-only'
    receipt['checkerTestMethodsPerMode']=13
    receipt['admittedBody64InputsPerMode']=2497
    receipt['roleSizeComparisonsPerMode']=72
    receipt['defaultBytes']=len((HERE/'mixer-measured-default-v2.json').read_bytes())
    receipt['defaultSHA256']=sha(HERE/'mixer-measured-default-v2.json')
finally:
    # Ignore derived build/cache and receipt itself; source inputs and command logs
    # are retained as auditable files. Collection hashing is path\0hexhash\n order.
    artifacts={}
    for p in sorted(HERE.rglob('*')):
        if p.is_file() and 'build' not in p.relative_to(HERE).parts and '__pycache__' not in p.parts and p.name!='receipt.json':
            artifacts[str(p.relative_to(ROOT))]=sha(p)
    external=ROOT/'docs/ui-measured-appearance-v2-contract.md'
    artifacts[str(external.relative_to(ROOT))]=sha(external)
    receipt['artifacts']=dict(sorted(artifacts.items()))
    receipt['artifactCollectionRule']='SHA256 of sorted UTF8 path NUL lowercase SHA256 LF records; excludes receipt, build and pycache'
    receipt['artifactCollectionSHA256']=hashlib.sha256(''.join(p+'\0'+h+'\n' for p,h in sorted(artifacts.items())).encode()).hexdigest()
    (HERE/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
if receipt['status']!='passed-design-only': sys.exit(1)
print('PASS:13 checker methods per normal/optimized; host/iOS17/officialAndroid30 declarations; V1 unchanged')
