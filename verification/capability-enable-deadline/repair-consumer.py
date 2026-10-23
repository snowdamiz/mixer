#!/usr/bin/env python3
"""Repair only the standalone consumer fixture; reuse unchanged runtime test evidence."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib, json, os, shutil, subprocess, time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'experimental-capability-runtime/verification/2026-10-23-enable-deadline-candidate-1/receipt.json'
OUT = HERE / 'consumer-repair-1'
WORK = ROOT / 'experimental-capability-runtime/.build/enable-deadline-consumer-repair-1'
OUT.mkdir(exist_ok=False); WORK.mkdir(exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
base = json.loads(BASE.read_text())
assert base['status'] == 'failed_check_preserved'
failed = [c['name'] for c in base['commands'] if c['exitCode'] != 0]
assert failed == ['host-lifecycle-consumer-run']
for c in base['commands']:
    assert sha(BASE.parent / c['log']) == c['logSHA256']
    if c['name'].startswith('bridge-'): assert c['passedTests'] == [35] and c['testCountsMatch']
source = WORK / 'source'
fixture = 'experimental-capability-runtime/verification/CrossProbe/Sources/bridge-lifecycle-probe/main.swift'
inputs = {}
for name, digest in base['source'].items():
    old = Path(base['frozenSourceExport']) / name
    assert sha(old) == digest
    if name != fixture: assert sha(ROOT / name) == digest, name
    destination = source / name; destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes((ROOT / name).read_bytes()); destination.chmod(0o444)
    inputs[name] = sha(destination)
manifest = ''.join(d+'  '+n+'\n' for n,d in inputs.items())
(OUT / 'source-manifest.sha256').write_text(manifest)
stage = Path(base['stageRoot'])
for artifacts in base['nativeArtifacts'].values():
    for name,digest in artifacts.items(): assert sha(stage / name) == digest
r = {'status':'running','base_receipt':str(BASE.relative_to(ROOT)),'base_sha256':sha(BASE),
     'source':inputs,'source_export':str(source),'source_manifest_sha256':hashlib.sha256(manifest.encode()).hexdigest(),
     'changed_fixture':fixture,'driver_sha256':sha(Path(__file__)),'commands':[],'binaries':{},
     'scope':'Unchanged35-test debug/release/TSan matrix reused from frozen base; standalone consumer fixture corrected and all4platform links rebuilt.',
     'limitations':['Original malformed no-memory/no-wake fixture failure preserved.','No device/platform execution beyond macOS host; no hard real-time or signed execution authority claim.']}
def save(): (OUT / 'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
def run(name, command, env):
    began=time.monotonic(); p=subprocess.run(command,cwd=source,env=os.environ|env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=900)
    (OUT/(name+'.log')).write_bytes(p.stdout)
    print(name+': '+str(p.returncode),flush=True)
    return {'name':name,'command':command,'cwd':str(source),'environment':env,'exit_code':p.returncode,'seconds':time.monotonic()-began,'log':name+'.log','log_sha256':hashlib.sha256(p.stdout).hexdigest()}
def flags(target): return ['-Xcc','-I'+str(stage/target/'include'),'-Xlinker','-L'+str(stage/target/'lib'),'-Xswiftc','-warnings-as-errors']
apple={'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'}
android={'DEVELOPER_DIR':'/Applications/Xcode_26.6.app/Contents/Developer'}
probe=str(source/'experimental-capability-runtime/verification/CrossProbe')
jobs=[('host',['swift','build','--package-path',probe,'--scratch-path',str(WORK/'host')]+flags('host'),apple)]
for target,triple,sdk in [('ios','arm64-apple-ios17.0','iphoneos'),('ios-simulator','arm64-apple-ios17.0-simulator','iphonesimulator')]:
    sdkpath=subprocess.check_output(['xcrun','--sdk',sdk,'--show-sdk-path'],env=os.environ|apple,text=True).strip()
    jobs.append((target,['swift','build','--package-path',probe,'--scratch-path',str(WORK/target),'--triple',triple,'--sdk',sdkpath]+flags(target),apple))
swift='/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift'
jobs.append(('android',[swift,'build','--package-path',probe,'--scratch-path',str(WORK/'android'),'--swift-sdks-path','/Users/andreyyurlov/.swiftpm/swift-sdks','--swift-sdk','aarch64-unknown-linux-android28','--static-swift-stdlib','-c','release']+flags('android')+['-Xlinker','-lssl','-Xlinker','-lcrypto','-Xlinker','-lz'],android))
save()
with ThreadPoolExecutor(max_workers=2) as pool:
    for row in pool.map(lambda job: run(*job),jobs): r['commands'].append(row); save()
for target,_,env in jobs:
    for product in ['bridge-cross-probe','bridge-lifecycle-probe']:
        paths=sorted({p.resolve() for p in (WORK/target).rglob(product) if p.is_file()})
        assert len(paths)==1,(target,product,paths)
        p=paths[0];key=target+'-'+product
        r['binaries'][key]={'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
        if target=='host': r['commands'].append(run(key,[str(p)],env));save()
r['unchanged_export']=all(sha(source/n)==d for n,d in inputs.items())
r['unchanged_native']=all(sha(stage/n)==d for files in base['nativeArtifacts'].values() for n,d in files.items())
r['status']='scoped consumer repair passed' if all(c['exit_code']==0 for c in r['commands']) and r['unchanged_export'] and r['unchanged_native'] else 'failed check preserved'
save()
raise SystemExit(0 if r['status']=='scoped consumer repair passed' else 1)
