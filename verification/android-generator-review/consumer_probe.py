#!/usr/bin/env python3
"""Create and test an app from the frozen CLI; avoid any Android build/device access."""
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
OUT=pathlib.Path(__file__).resolve().parent
SOURCE=OUT/'.local/source'
APP=OUT/'.local/independent-consumer'
CLI=SOURCE/'cli/.build/debug/mixer'
commands=[]
def run(name,args,expected=0,contains=None):
    p=subprocess.run(list(map(str,args)),cwd=SOURCE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log=OUT/('consumer-'+name+'.log');log.write_bytes(p.stdout)
    commands.append({'name':name,'command':list(map(str,args)),'exit_code':p.returncode,'output':log.name,'output_sha256':hashlib.sha256(p.stdout).hexdigest()})
    assert (p.returncode==0)==(expected==0),(name,p.stdout[-5000:])
    assert contains is None or contains.encode() in p.stdout,(name,p.stdout[-5000:])
    return p.stdout
run('create',[CLI,'create','IndependentConsumer','--platform','android','--directory',APP,'--application','dev.mixer.independentreview','--sdk-path',SOURCE/'sdk','--android-adapter-path',SOURCE/'native/android'])
# Byte equality binds the app export to committed reusable adapter sources.
for relative in ['bridge/jni.c','bridge/mixer_android.h','contracts/android-profile-v1.json','app/src/dev/mixer/android/Json.java','app/src/dev/mixer/android/UiPacket.java','app/src/dev/mixer/android/NativeBridge.java','app/src/dev/mixer/android/NativeRenderer.java','app/src/dev/mixer/android/MixerActivity.java']:
    assert (APP/'Generated/MixerAndroid'/relative).read_bytes()==(SOURCE/'native/android'/relative).read_bytes(),relative
run('host-tests',['/usr/bin/swift','test','--package-path',APP],contains='4 tests')
shutil.copyfile(OUT/'ConsumerProbe.swift',APP/'Platforms/Android/Tests/AppAndroidTests/ConsumerProbe.swift')
run('actual-abi-probe',['/usr/bin/swift','test','--package-path',APP/'Platforms/Android','--filter','IndependentConsumerProbe'],contains='1 test')
for name,relative,marker in [('sdk-drift','Generated/MixerSDK/Package.swift','lock.sdk-drift'),('adapter-drift','Generated/MixerAndroid/bridge/jni.c','lock.android-drift')]:
    path=APP/relative;original=path.read_bytes()
    try:
        path.write_bytes(original+b'\n// independent drift probe\n')
        run(name,[CLI,'build','--platform','android','--directory',APP],expected=1,contains=marker)
    finally:path.write_bytes(original)
config=APP/'mixer.yml';original=config.read_bytes()
try:
    changed=json.loads(original);changed['capabilities']=['storage.files'];config.write_text(json.dumps(changed))
    run('unsupported-capability',[CLI,'build','--platform','android','--directory',APP],expected=1,contains='android.unsupported-capability')
finally:config.write_bytes(original)
resource=APP/'Resources/required.txt';resource.write_text('A required resource must not disappear.')
try:run('unsupported-resource',[CLI,'build','--platform','android','--directory',APP],expected=1,contains='android.unsupported-resources')
finally:resource.unlink()
(OUT/'consumer-probe-results.json').write_text(json.dumps({'revision':json.loads((OUT/'freeze.json').read_text())['revision'],'commands':commands,'scope':'Independent app creation and host tests of actual shared AppFeatures/AppModels/C ABI; no Android/device qualification.'},indent=2)+'\n')
print('Independent consumer creation, shared host tests, bounded actual C ABI reducer and fail-closed negatives passed.')
