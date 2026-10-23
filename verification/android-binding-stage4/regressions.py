#!/usr/bin/env python3
"""Execute frozen common/Apple/core plus actual portable rejection regressions."""
from pathlib import Path
from datetime import datetime,timezone
import argparse, hashlib,json,os,plistlib,shutil,subprocess,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
p=argparse.ArgumentParser();p.add_argument('--reference',required=True);p.add_argument('--name',required=True);a=p.parse_args()
refpath=ROOT/a.reference;ref=json.loads(refpath.read_text());mode=ref['mode']
out=HERE/'.build'/('regression-'+a.name);out.mkdir(parents=True,exist_ok=False)
logs=HERE/'runs'/('regression-'+a.name);logs.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
receipt={'reference':a.reference,'reference_sha256':sha(refpath),'mode':mode,'source_files':{},'commands':[],'artifacts':{},'scope':'Existing unchanged common Task/lifetime/core/Apple-model regressions compiled against actual full host-enabled module. Portable rejection rebuild removes MixerApple and both host C modules; no Android state or Task is admitted. Retained SDK dependencies are not TSan-instrumented.'}
base=json.loads((ROOT/ref['dependency_receipt']).read_text());original=next(x['argv'] for x in base['commands'] if x['name']=='link-current-runtime')
ref_source=Path(next(x['cwd'] for x in ref['commands']));products=ref_source.parent
for relative,digest in ref['source_files'].items():assert sha(ref_source/relative)==digest
src=out/'test-source';src.mkdir()
checks=ROOT/'capability-activation/Tests/MixerCapabilityActivationTests'
testpaths=[checks/n for n in ['GuestUIPresentationLifetimeTests.swift','CapabilityColdStartRuntimeTests.swift','GuestUIPresentationModelTests.swift','GuestUIPresentationWindowTests.swift']]
testpaths+=list((checks/'Fixtures').glob('*'))
testpaths+=[ROOT/'verification/common-presentation-lifetime'/n for n in ['TestResources.swift','TestMain.swift','PortableTests.swift']]
for path in testpaths:
    relative=str(path.relative_to(ROOT));target=src/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target);target.chmod(0o444);receipt['source_files'][relative]=sha(target)
env=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer');env.pop('MIXER_GUEST_UI_VISIBLE_WINDOW',None)
flags=['-O'] if mode=='release' else ['-sanitize=thread'] if mode=='tsan' else []
frameworks=Path(env['DEVELOPER_DIR'])/'Platforms/MacOSX.platform/Developer/Library/Frameworks';overlays=frameworks.parents[1]/'usr/lib'
tsan=Path(env['DEVELOPER_DIR'])/'Toolchains/XcodeDefault.xctoolchain/usr/lib/clang/21/lib/darwin/libclang_rt.tsan_osx_dynamic.dylib'
macros=Path(env['DEVELOPER_DIR'])/'Toolchains/XcodeDefault.xctoolchain/usr/lib/swift/host/plugins/testing/libTestingMacros.dylib'
def save():(logs/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
def run(name,argv,expected=0,extra=None):
    start=time.monotonic();r=subprocess.run([str(x) for x in argv],cwd=src,env=env|(extra or {}),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
    log=logs/(name+'.log');log.write_bytes(r.stdout);receipt['commands'].append({'name':name,'argv':[str(x) for x in argv],'exit':r.returncode,'expected_exit':expected,'seconds':time.monotonic()-start,'log':str(log.relative_to(ROOT)),'sha256':sha(log)})
    save();print(name,r.returncode,flush=True)
    if r.returncode!=expected or b'WARNING: ThreadSanitizer' in r.stdout:print(r.stdout.decode(errors='replace'));raise RuntimeError(name)
    return r.stdout.decode(errors='replace')
def bundle(name):
    b=out/(name+'.xctest');exe=b/'Contents/MacOS'/name;exe.parent.mkdir(parents=True)
    (b/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable':name,'CFBundleIdentifier':'dev.mixer.stage4.'+name,'CFBundlePackageType':'BNDL','CFBundleVersion':'1'}));return b,exe
try:
    prefix=original[:original.index('-emit-library')];prefix=prefix[:2]+['-I',products]+prefix[2:]
    module_flags=['-I',ref_source/'native/android/signed-guest-ui/binding/include','-I',ref_source/'verification/android-binding-stage4/host-bridge']
    link=['-L',products,'-lMixerAndroidStage4','-L',overlays,'-Xlinker','-rpath','-Xlinker',products,'-Xlinker','-rpath','-Xlinker',frameworks,'-Xlinker','-rpath','-Xlinker',overlays]
    test_src=src/'capability-activation/Tests/MixerCapabilityActivationTests';helper=src/'verification/common-presentation-lifetime'
    b,exe=bundle('MixerStage4CommonTests');shutil.copytree(test_src/'Fixtures',b/'Contents/Resources/Fixtures')
    run('common-xctest-link',prefix+flags+module_flags+['-I',overlays,'-F',frameworks,'-emit-library','-module-name','MixerStage4CommonTests',test_src/'GuestUIPresentationLifetimeTests.swift',test_src/'CapabilityColdStartRuntimeTests.swift',helper/'TestResources.swift']+link+['-o',exe])
    output=run('common-xctests',[Path(env['DEVELOPER_DIR'])/'usr/bin/xctest',b],extra={'DYLD_INSERT_LIBRARIES':str(tsan)} if mode=='tsan' else None);assert 'with 0 failures' in output
    models=out/'AppleModels'
    run('apple-model-link',prefix+flags+module_flags+['-I',overlays,'-F',frameworks,'-load-plugin-library',macros,'-module-name','MixerStage4Models',test_src/'GuestUIPresentationModelTests.swift',test_src/'GuestUIPresentationWindowTests.swift',helper/'TestMain.swift']+link+['-o',models])
    output=run('apple-models',[models],extra={'DYLD_INSERT_LIBRARIES':str(tsan)} if mode=='tsan' else None);assert 'passed' in output and 'skipped' in output
    portable=out/'portable';portable.mkdir();modules=portable/'dependencies';modules.mkdir()
    base_products=Path(base['dylib']).parent
    for path in base_products.glob('*.swiftmodule'):
        if path.stem not in ['MixerApple','MixerCapabilityActivation']:shutil.copy2(path,modules/path.name)
    library=portable/'libMixerPortableStage4.dylib';argv=[]
    for arg in original:
        if arg.startswith(str(Path(base['source'])/'capability-activation/Sources/MixerCapabilityActivation')):continue
        if arg==str(base_products):arg=str(modules)
        elif arg==base['dylib']:arg=str(library)
        elif arg.endswith('/products/MixerCapabilityActivation.swiftmodule'):arg=str(portable/'MixerCapabilityActivation.swiftmodule')
        elif arg=='@rpath/libMixerGuestUITeardownRuntime.dylib':arg='@rpath/'+library.name
        argv.append(arg)
    insertion=argv.index('-emit-library');argv[insertion:insertion]=flags+sorted((ref_source/'capability-activation/Sources/MixerCapabilityActivation').glob('*.swift'))
    run('portable-module-link',argv)
    portable_prefix=original[:original.index('-emit-library')];portable_prefix=[str(modules) if x==str(base_products) else x for x in portable_prefix]
    b,exe=bundle('MixerStage4PortableTests')
    portable_link=['-L',portable,'-lMixerPortableStage4','-L',overlays,'-Xlinker','-rpath','-Xlinker',portable,'-Xlinker','-rpath','-Xlinker',frameworks,'-Xlinker','-rpath','-Xlinker',overlays]
    run('portable-tests-link',portable_prefix[:2]+['-I',portable]+portable_prefix[2:]+flags+['-I',overlays,'-F',frameworks,'-emit-library','-module-name','MixerStage4PortableTests',helper/'PortableTests.swift']+portable_link+['-o',exe])
    output=run('portable-tests',[Path(env['DEVELOPER_DIR'])/'usr/bin/xctest',b],extra={'DYLD_INSERT_LIBRARIES':str(tsan)} if mode=='tsan' else None);assert 'Executed 1 test, with 0 failures' in output
    receipt['artifacts']={str(path.relative_to(ROOT)):sha(path) for path in [library,exe,models]};receipt['result']='common/core Apple-model and portable regressions passed; visible positive window remains skipped'
except BaseException as error:receipt['result']='failed regression retained';receipt['error']=str(error);raise
finally:receipt['completed_utc']=datetime.now(timezone.utc).isoformat();save()
