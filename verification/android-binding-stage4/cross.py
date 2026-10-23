#!/usr/bin/env python3
"""Official API30 compile of frozen full product source plus fixed host fixture."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,shutil,subprocess,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
p=argparse.ArgumentParser();p.add_argument('--reference',required=True);p.add_argument('--name',required=True);a=p.parse_args()
refpath=ROOT/a.reference;ref=json.loads(refpath.read_text());refsource=Path(ref['commands'][0]['cwd'])
out=HERE/'.build'/('android-'+a.name);out.mkdir(parents=True,exist_ok=False)
logs=HERE/'runs'/('android-'+a.name);logs.mkdir(parents=True,exist_ok=False)
source=out/'source';source.mkdir();products=out/'products';products.mkdir()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
receipt={'reference':a.reference,'reference_sha256':sha(refpath),'commands':[],'source_files':{},'artifacts':{},'scope':'Official Swift 6.3.3 / Android NDK r27d API30 full-module and actual fixed host C compile/link. Host fixture ABI only; no JNI, Looper, device, profile enablement, signed core integration or GA authority. Crypto retained actual API28 third-party objects are explicitly hashed dependencies.'}
def copy(path,base=ROOT):
    relative=str(path.relative_to(base));target=source/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target);target.chmod(0o444);receipt['source_files'][relative]=sha(target)
for relative,digest in ref['source_files'].items():
    path=refsource/relative;assert sha(path)==digest;copy(path,refsource)
for group in ['sdk/Sources/MixerCore','sdk/Sources/MixerUI','sdk/Sources/MixerGuest','sdk/Sources/MixerCapabilities','updates/Sources/MixerUpdates','updates/Sources/MixerDurableIO','runtime-identity/Sources/MixerRuntimeIdentity','experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime','experimental-capability-runtime/Sources/CMixerVMCapability','capability-activation/Sources/MixerCapabilityDurableIO','native/include']:
    for path in (ROOT/group).rglob('*'):
        if path.is_file():copy(path)
copy(HERE/'SymbolEntry.swift');copy(Path(__file__))
vmreceipt_path=HERE/'.build/android-vm-3a1bb5a/receipt.json'
vmreceipt=json.loads(vmreceipt_path.read_text())
receipt['vm_receipt']=str(vmreceipt_path.relative_to(ROOT));receipt['vm_receipt_sha256']=sha(vmreceipt_path)
for path in vmreceipt_path.parent.joinpath('include').glob('*.h'):
    target=source/'vm-native-include'/path.name;target.parent.mkdir(exist_ok=True);shutil.copy2(path,target);target.chmod(0o444);receipt['source_files'][str(target.relative_to(source))]=sha(target)
vmarchive=Path(vmreceipt['library']['path']);receipt['vm_archive_sha256']=sha(vmarchive)

receipt['source_tree_sha256']=hashlib.sha256(json.dumps(receipt['source_files'],sort_keys=True).encode()).hexdigest()
toolchain=Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin')
sdk=Path('/Users/andreyyurlov/.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android').resolve()
ndk=sdk/'android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64/bin'
swift=toolchain/'swiftc';clang=ndk/'aarch64-linux-android30-clang'
crypto=ROOT/'verification/local/runtime-identity-2026-10-22-final/android-compile'
crypto_products=crypto/'aarch64-unknown-linux-android28/release'
crypto_cmap=crypto/'checkouts/swift-crypto/Sources/CCryptoBoringSSL/include/module.modulemap'
cmaps={
'MixerCapabilityIO':'sdk/Sources/MixerCapabilities/NativeIO/include/MixerCapabilityIO.h',
'MixerDurableIO':'updates/Sources/MixerDurableIO/include/MixerDurableIO.h',
'MixerCapabilityDurableIO':'capability-activation/Sources/MixerCapabilityDurableIO/include/MixerCapabilityDurableIO.h',
'CMixerVMCapability':'experimental-capability-runtime/Sources/CMixerVMCapability/include/MixerVMCapability.h'}
module_flags=['-I',products,'-I',crypto_products/'Modules','-Xcc','-fmodule-map-file='+str(crypto_cmap),'-Xcc','-I'+str(source/'vm-native-include'),'-I',source/'native/android/signed-guest-ui/binding/include','-I',source/'verification/android-binding-stage4/host-bridge']
for name,relative in cmaps.items():
    folder=out/'cmaps'/name;folder.mkdir(parents=True);(folder/'module.modulemap').write_text('module '+name+' { header "'+str(source/relative)+'" export * }\n');module_flags+=['-I',folder]
flags=['-swift-version','6','-warnings-as-errors','-enable-testing','-parse-as-library','-O','-g','-target','aarch64-unknown-linux-android30','-sdk',sdk/'ndk-sysroot','-resource-dir',sdk/'swift-resources/usr/lib/swift-aarch64','-module-cache-path',out/'cache']+module_flags
env=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer')
def save():(logs/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
def run(name,argv,expected=0):
    start=time.monotonic()
    try:r=subprocess.run([str(x) for x in argv],cwd=source,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240);data,code=r.stdout,r.returncode
    except subprocess.TimeoutExpired as e:data,code=(e.stdout or b'')+b'\nTIMEOUT\n',124
    log=logs/(name+'.log');log.write_bytes(data);receipt['commands'].append({'name':name,'argv':[str(x) for x in argv],'cwd':str(source),'environment':{'DEVELOPER_DIR':env['DEVELOPER_DIR']},'exit':code,'expected_exit':expected,'seconds':time.monotonic()-start,'log':str(log.relative_to(ROOT)),'sha256':sha(log)});save();print(name,code,flush=True)
    if code!=expected:print(data.decode(errors='replace'));raise RuntimeError(name)
    return data.decode(errors='replace')
try:
    run('official-swift-version',[swift,'--version']);run('official-clang-version',[clang,'--version']);run('platform',['uname','-a'])
    for module,group in [('MixerCore','sdk/Sources/MixerCore'),('MixerUI','sdk/Sources/MixerUI'),('MixerGuest','sdk/Sources/MixerGuest'),('MixerCapabilities','sdk/Sources/MixerCapabilities'),('MixerUpdates','updates/Sources/MixerUpdates'),('MixerRuntimeIdentity','runtime-identity/Sources/MixerRuntimeIdentity'),('MixerExperimentalCapabilityRuntime','experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime'),('MixerCapabilityActivation','capability-activation/Sources/MixerCapabilityActivation')]:
        files=sorted((source/group).glob('*.swift'))
        run(module,[swift]+flags+['-whole-module-optimization','-emit-object','-emit-module','-module-name',module,'-emit-module-path',products/(module+'.swiftmodule')]+files+['-o',products/(module+'.o')])
    cfiles=[source/'native/android/signed-guest-ui/transport/transport.c',source/'verification/android-binding-stage4/host-bridge/host_bridge.c',source/'sdk/Sources/MixerCapabilities/NativeIO/lock.c',source/'updates/Sources/MixerDurableIO/lock.c',source/'capability-activation/Sources/MixerCapabilityDurableIO/lock.c']
    for index,path in enumerate(cfiles):run('C-'+str(index),[clang,'-std=c11','-Wall','-Wextra','-Werror','-O2','-g','-fPIC','-DMIXER_UI_TRANSPORT_TESTING','-I',path.parent/'include','-c',path,'-o',products/('C'+str(index)+'.o')])
    run('verification-edge',[swift]+flags+['-emit-object','-module-name','Stage4AndroidEdge',source/'verification/android-binding-stage4/SymbolEntry.swift','-o',products/'edge.o'])
    receipt['artifacts']={str(path.relative_to(ROOT)):sha(path) for path in products.glob('*') if path.is_file()}
    receipt['third_party_inputs']={str(path.relative_to(ROOT)):sha(path) for path in [crypto_products/'Modules/Crypto.swiftmodule',crypto_products/'Modules/CryptoBoringWrapper.swiftmodule',crypto_cmap]}
    crypto_objects=[]
    for name in ['Crypto.build','CryptoBoringWrapper.build','CCryptoBoringSSL.build','CXKCP.build','CXKCPShims.build']:
        crypto_objects+=sorted((crypto_products/name).rglob('*.o'))
    receipt['third_party_objects']={str(path.relative_to(ROOT)):sha(path) for path in crypto_objects}
    # The retained earlier module-only build never emitted bcm.cc.o. Compile
    # that real vendored translation unit with its canonical SwiftPM flags.
    vendored=crypto/'checkouts/swift-crypto/Sources/CCryptoBoringSSL'
    vendor_copy=source/'third-party/CCryptoBoringSSL';shutil.copytree(vendored,vendor_copy)
    receipt['crypto_bcm_sources']={str(path.relative_to(vendor_copy)):sha(path) for path in vendor_copy.rglob('*') if path.is_file()}
    run('actual-Crypto-bcm',[toolchain/'clang','-target','aarch64-unknown-linux-android30','-O2','-DSWIFT_PACKAGE=1','-fblocks','-I',vendor_copy/'include','--sysroot',sdk/'ndk-sysroot','-fPIC','-g','-fno-omit-frame-pointer','-w','-std=c++17','-c',vendor_copy/'crypto/fipsmodule/bcm.cc','-o',products/'crypto-bcm.o'])

    library=products/'libMixerStage4AndroidHost.so'
    run('actual-strict-link',[swift]+flags+['-emit-library','-tools-directory',ndk]+sorted(products.glob('*.o'))+crypto_objects+[vmarchive,'-Xlinker','-z','-Xlinker','defs','-Xlinker','-z','-Xlinker','max-page-size=16384','-o',library])
    run('linked-ELF',[ndk/'llvm-readelf','-h','-d','-s',library])
    receipt['artifacts'][str(library.relative_to(ROOT))]=sha(library)
    receipt['status']='official API30 full Swift module/object, actual fixed C host fixture and strict no-undefined native link passed'

except BaseException as e:receipt['status']='failed verification retained';receipt['error']=str(e);raise
finally:receipt['completed_utc']=datetime.now(timezone.utc).isoformat();save()
