#!/usr/bin/env python3
"""Freeze the private slice with reviewed transition inputs; reuse dependencies."""
import argparse,datetime,hashlib,json,os,plistlib,re,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def require(value,message):
    if not value:raise RuntimeError(message)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',required=True);parser.add_argument('--modes',default='debug,release,tsan');args=parser.parse_args()
    require(re.fullmatch('[a-z0-9-]{1,64}',args.name) is not None,'bounded evidence name')
    out=HERE/args.name;out.mkdir(exist_ok=False)
    work=ROOT/'capability-activation/.build'/('concrete-'+args.name);source=work/'source';source.mkdir(parents=True,exist_ok=False)
    dependency=ROOT/'verification/capability-recovery-transitions/2026-10-23-candidate-2/receipt.json';base=json.loads(dependency.read_text());base_source=Path(base['export'])
    require(base['source_manifest_sha256']=='eca159ee0c07066a5f6bccb3ef8e02396a6489cb6f392c9bf2f8d4cb8c04ff62','reviewed transition freeze')
    inputs=dict(base['source_files'])
    own=['capability-activation/Sources/MixerCapabilityActivation/CapabilityConcreteAttempt.swift','capability-activation/Sources/MixerCapabilityActivation/CapabilityConcreteRetirement.swift','capability-activation/Tests/MixerCapabilityActivationTests/ConcreteAttemptTests.swift','verification/capability-concrete-attempt/Bundle.swift','verification/capability-concrete-attempt/run.py']
    for name in own:inputs[name]=sha(ROOT/name)
    require(len(inputs)==127,'closed combined input count')
    for name,digest in inputs.items():
        original=ROOT/name if name in own else base_source/name
        require(sha(original)==digest,'source '+name);target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(original.read_bytes())
    manifest=''.join(d+'  '+n+'\n' for n,d in sorted(inputs.items()));(out/'source-manifest.sha256').write_text(manifest)
    native=Path(base['native_copy']);frameworks=Path('/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/Library/Frameworks')
    receipt=dict(status='running',started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),dependency_revision=base['dependency_revision'],
        dependency_receipt=dict(path=str(dependency.relative_to(ROOT)),sha256=sha(dependency)),dependency_manifest_sha256=base['source_manifest_sha256'],
        source_files=inputs,own_files={n:inputs[n] for n in own},source_manifest_sha256=hashlib.sha256(manifest.encode()).hexdigest(),export=str(source),
        native_directory=str(native),native_files=base['native_files'],retained_products={},commands=[],artifacts={},scope='Private concrete adapter attempt and retirement join; real signed/store selection, native VM and KV, direct module/test-bundle compilation with retained dependencies; no new package/Rust graph.',
        limitations=['Root coordinator/terminal consumer are excluded and separately owned','Immutable candidate2 Store/old Signals are the explicit dependency; live shared-owner revisions and final composition are separately qualified','Store retained-source authority is not independent final review approval','Direct Swift TSan instruments activation sources/test bundle and uses retained TSan dependencies; native/system dependencies are not Swift TSan instrumented','Sampled startup cutoff, no atomic hard real-time guarantee','No devices, signed execution/public facade/real health, final publication or GA qualification'])
    def save():(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    def unchanged():
        for name,digest in inputs.items():
            require(sha(source/name)==digest,'immutable export '+name)
            if name in own:require(sha(ROOT/name)==digest,'current owned source '+name)
        for name,digest in base['native_files'].items():require(sha(native/name)==digest,'native artifact '+name)
    unchanged();save();print('SOURCE FROZEN '+receipt['source_manifest_sha256'],flush=True)
    def run(name,command,env=None,timeout=180,expected_tests=None):
        unchanged();began=time.monotonic();environment=os.environ|{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'}|(env or {})
        try:r=subprocess.run(command,cwd=source,env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);raw,code=r.stdout,r.returncode
        except subprocess.TimeoutExpired as error:raw,code=(error.stdout or b'')+b'\nconcrete qualification timeout\n',124
        log=out/(name+'.log');log.write_bytes(raw);row=dict(name=name,command=command,cwd=str(source),environment={k:environment[k] for k in ['DEVELOPER_DIR']+list((env or {}).keys())},exit_code=code,seconds=time.monotonic()-began,timeout_seconds=timeout,log=log.name,log_sha256=sha(log))
        if expected_tests is not None:
            counts=[int(n) for n in re.findall(rb'Executed (\d+) tests?, with 0 failures',raw)];row.update(expected_tests=expected_tests,observed_test_counts=counts)
        receipt['commands'].append(row);save();require(code==0,name+' unexpected exit '+str(code))
        if expected_tests is not None:require(row['observed_test_counts'] and row['observed_test_counts'][-1]==expected_tests,'observed XCTest count')
        require(b'WARNING: ThreadSanitizer' not in raw,'no TSan warning');unchanged();print(name+': '+str(code),flush=True)
    try:
        run('swift-version',['swift','--version']);run('xcode-version',['xcodebuild','-version'])
        activation=source/'capability-activation/Sources/MixerCapabilityActivation';sources=sorted(str(p) for p in activation.glob('*.swift'))
        require(len(sources)==11,'nine frozen existing activation files plus two owned additions')
        tests=source/'capability-activation/Tests/MixerCapabilityActivationTests/ConcreteAttemptTests.swift'
        for mode in args.modes.split(','):
            retained=base['retained_products'][mode];retained_path=Path(retained['directory']);products=retained_path/'products';maps=retained_path/'modulemaps'
            library=products/'libMixerCapabilityActivation.a';require(sha(library)==retained['files']['products/libMixerCapabilityActivation.a'],'retained dependency product')
            receipt['retained_products'][mode]=dict(directory=str(retained_path),library_sha256=sha(library));save()
            target=work/mode;target.mkdir();current_products=target/'products';current_products.mkdir()
            flags=['swiftc','-parse-as-library','-swift-version','6','-warnings-as-errors','-I',str(products),'-F',str(frameworks)]
            for name in ['CMixerVMCapability','MixerCapabilityDurableIO','MixerCapabilityIO','MixerDurableIO']:flags+=['-Xcc','-fmodule-map-file='+str(maps/(name+'.modulemap'))]
            flags+=['-Xcc','-I'+str(native/'include')]
            if mode=='release':flags+=['-O']
            if mode=='tsan':flags+=['-sanitize=thread']
            dylib=current_products/'libMixerCapabilityActivationConcrete.dylib'
            run(mode+'-module',flags+['-emit-library','-emit-module','-enable-testing','-module-name','MixerCapabilityActivation','-emit-module-path',str(current_products/'MixerCapabilityActivation.swiftmodule')]+sources+['-L',str(products),'-lMixerCapabilityActivation','-L',str(native/'lib'),'-lmixer_vm_capability_experimental','-Xlinker','-install_name','-Xlinker','@rpath/'+dylib.name,'-o',str(dylib)])
            bundle=target/'MixerConcreteTests.xctest';executable=bundle/'Contents/MacOS/MixerConcreteTests';executable.parent.mkdir(parents=True)
            (bundle/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable':'MixerConcreteTests','CFBundleIdentifier':'org.mixer.test.concrete','CFBundlePackageType':'BNDL','CFBundleVersion':'1'}))
            overlays=frameworks.parents[1]/'usr/lib';require((overlays/'XCTest.swiftmodule').exists(),'official XCTest Swift overlay')
            run(mode+'-tests-link',flags[:1]+['-I',str(current_products),'-I',str(overlays)]+flags[1:]+['-emit-library','-module-name','MixerConcreteAttemptTests',str(tests),str(source/'verification/capability-concrete-attempt/Bundle.swift'),'-L',str(current_products),'-lMixerCapabilityActivationConcrete','-L',str(products),'-lMixerCapabilityActivation','-L',str(overlays),'-Xlinker','-rpath','-Xlinker',str(current_products),'-Xlinker','-rpath','-Xlinker',str(frameworks),'-Xlinker','-rpath','-Xlinker',str(overlays),'-o',str(executable)])
            env={'MIXER_CONCRETE_TEST_BUNDLE':str(products/'MixerCapabilityActivation_MixerCapabilityActivationTests.bundle')}
            if mode=='tsan':
                resource=subprocess.check_output(['clang','-print-resource-dir'],env=os.environ|{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'},text=True).strip()
                runtime=Path(resource)/'lib/darwin/libclang_rt.tsan_osx_dynamic.dylib';require(runtime.exists(),'official TSan runtime');env['DYLD_INSERT_LIBRARIES']=str(runtime)
            # /usr/bin/xcrun strips DYLD_* at its protected launcher boundary.
            # Resolve first, then execute XCTest directly so TSan loads at launch.
            xctest=subprocess.check_output(['xcrun','--find','xctest'],env=os.environ|{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'},text=True).strip()
            run(mode+'-tests',[xctest,str(bundle)],env=env,expected_tests=6)
            run(mode+'-native-symbols',['nm','-gU',str(dylib)])
            run(mode+'-test-native-symbols',['nm','-gU',str(executable)])
            defined=(out/(mode+'-native-symbols.log')).read_text();test_defined=(out/(mode+'-test-native-symbols.log')).read_text()
            require(len(re.findall(r'\b_mixer_vm_capability_session_enable_v1$',defined,re.M))==1,'one linked native enable definition')
            require(re.search(r'\b_mixer_vm_\w+$',test_defined,re.M) is None,'test bundle defines no second native registry')
            receipt['artifacts'][mode]=dict(module=dict(path=str(dylib),sha256=sha(dylib)),test_bundle_executable=dict(path=str(executable),sha256=sha(executable)));save()
            require(sha(library)==receipt['retained_products'][mode]['library_sha256'],'retained library unchanged')
        unchanged();receipt.update(status='scoped concrete attempt tests passed; independent review pending',source_unchanged=True,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    except Exception as error:receipt.update(status='failed check preserved',problem=str(error));save();raise
    save();print('receipt_sha256 '+sha(out/'receipt.json'))
if __name__=='__main__':main()
