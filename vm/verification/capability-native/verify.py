#!/usr/bin/env python3
"""Original source-bound host/C/cross-build verifier; never operates a device."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
FREEZE='76372fd254e646141e991b3289b14c8380f13ea68602b21d4aa746080fddc8cf'
REFERENCE='cc0ac37abf45c59df7c85f59ebbb038af7c0a251'
FROZEN=['vm/include/mixer_vm.h','runtime/Sources/CMixerVM/include/mixer_vm.h',
    'contracts/vm-profile-v1.json','contracts/vm-session-v1.json','vm/profiles/numeric-v2.json',
    'vm/profiles/table-memory-v3.json','vm/src/ffi.rs','vm/src/float.rs','vm/src/decode.rs',
    'vm/src/validate.rs','vm/src/execute.rs','vm/src/experimental/mod.rs',
    'vm/src/experimental_capability/mod.rs','vm/src/experimental_capability/guest.rs']
NDK=Path('/Users/andreyyurlov/.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android/android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64')
ROOT_PINS={'vm/src/session.rs':'ce446d2bb18a0aabe9750707901a4f6eb5e6dbfeb9494ce955ce2f3e44b591b8',
    'vm/tests/capability_registry.rs':'edaad6e2f097eb14d732754afaefc1a8ed6351ec2715196db4b6adf75102c7c4',
    'vm/src/capability_ffi/ranges.rs':'1f4adbef4dc181cf60eeffe8f041c508b361154cb4a4f3c1c61dddae706e20be'}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def counts(output):return {'passed':sum(map(int,re.findall(r'test result: ok\. (\d+) passed;',output))),
    'ignored':sum(map(int,re.findall(r'test result: ok\..*? (\d+) ignored;',output)))}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--name',required=True);a=p.parse_args()
    if not re.fullmatch('[A-Za-z0-9_-]+',a.name):p.error('invalid fresh receipt directory name')
    out=ROOT/'vm/verification/capability-native'/a.name;out.mkdir(exist_ok=False)
    target=ROOT/'vm/target/capability-native-verification'
    env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ.get('PATH',''),CARGO_TARGET_DIR=str(target))
    manifest=(ROOT/'vm/verification/capability-native/source-freeze.sha256').read_bytes()
    if sha(manifest)!=FREEZE:raise RuntimeError('freeze manifest differs')
    entries=[line.split('  ',1) for line in manifest.decode().splitlines()]
    def check():
        for digest,name in entries:
            if sha((ROOT/name).read_bytes())!=digest:raise RuntimeError('source drift: '+name)
        for name,digest in ROOT_PINS.items():
            if sha((ROOT/name).read_bytes())!=digest:raise RuntimeError('root input differs: '+name)
    check();(out/'source-manifest.sha256').write_bytes(manifest)
    receipt={'schema_version':1,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_manifest_sha256':FREEZE,'source_files':len(entries),'source_manifest':str((out/'source-manifest.sha256').relative_to(ROOT)),
        'head_at_start':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'source_is_uncommitted_freeze_before_integration':True,'implementation_selection':{'model':'gpt-6.1-sol','reasoning_effort':'xhigh'},
        'independent_review':False,'root_owned_inputs':ROOT_PINS,
        'environment':{'PATH_prefix':'/opt/homebrew/opt/rustup/bin','CARGO_TARGET_DIR':str(target),'DEVELOPER_DIR':env.get('DEVELOPER_DIR')},
        'scope':'host only actual C/Rust/Wasm plus official iOS/Android compile/link; no device execution',
        'SDK_native_identity_and_Swift_bridge_are_excluded':True,
        'verification_driver_sha256':sha(Path(__file__).read_bytes()),'commands':[]}
    def save(): (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    def run(name,argv,overrides=None):
        before=time.monotonic();current=env|dict(overrides or {})
        r=subprocess.run(argv,cwd=ROOT,env=current,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        log=out/(name+'.log');log.write_text(r.stdout)
        receipt['commands'].append({'name':name,'argv':argv,'environment_overrides':overrides or {},'exit_code':r.returncode,
            'elapsed_host_development_seconds':round(time.monotonic()-before,6),'log':str(log.relative_to(ROOT)),'sha256':sha(log.read_bytes())})
        save();print(f'{name}: exit={r.returncode}',flush=True)
        if r.returncode:print(r.stdout[-14000:]);raise RuntimeError(name+' failed')
        check();return r.stdout
    receipt['unchanged_legacy_inputs']={}
    for path in FROZEN:
        old=subprocess.check_output(['git','show',REFERENCE+':'+path],cwd=ROOT)
        if old!=(ROOT/path).read_bytes():raise RuntimeError('unexpected old input change: '+path)
        receipt['unchanged_legacy_inputs'][path]=sha(old)
    receipt['versions']={key:run('version-'+key,cmd).strip() for key,cmd in {
        'rustc':['rustc','-Vv'],'cargo':['cargo','-V'],'clippy':['cargo','clippy','--version'],
        'targets':['rustup','target','list','--installed'],'python':[sys.executable,'--version'],
        'node':['node','--version'],'apple_clang':['clang','--version'],'android_clang':[str(NDK/'bin/aarch64-linux-android28-clang'),'--version'],
        'macos':['sw_vers'],'host':['uname','-a'],'xcode':['xcodebuild','-version']}.items()}
    macsdk=run('macos-sdk',['xcrun','--sdk','macosx','--show-sdk-path']).strip()
    iossdk=run('ios-sdk',['xcrun','--sdk','iphoneos','--show-sdk-path']).strip()
    run('format',['cargo','fmt','--manifest-path','vm/Cargo.toml','--check'])
    run('fixed-payload-parity',[sys.executable,'-B','vm/tools/generate-capability-terminals.py'])
    for label,flags in [('default',[]),('all',['--all-features'])]:
        run('clippy-'+label,['cargo','clippy','--locked','--manifest-path','vm/Cargo.toml','--all-targets',*flags,'--','-D','warnings'])
    base=['cargo','test','--locked','--manifest-path','vm/Cargo.toml'];receipt['test_counts']={}
    for label,flags in [('default',[]),('all',['--all-features'])]:
        for build,mode in [('debug',[]),('release',['--release'])]:
            name=label+'-'+build;receipt['test_counts'][name]=counts(run(name,base+mode+flags+['--','--nocapture']))
    for build,mode in [('debug',[]),('release',['--release'])]:
        for test in ['review_session_lifetime','capability_registry','capability_ffi_public','capability_ffi_allocations']:
            name=test+'-'+build;receipt['test_counts'][name]=counts(run(name,base+mode+['--all-features','--test',test,'--','--nocapture','--test-threads=1']))
        name='oracles-'+build;receipt['test_counts'][name]=counts(run(name,base+mode+['--all-features','--','--ignored','--nocapture']))
    receipt['artifacts']={};receipt['symbols']={};receipt['c_smokes']={}
    for label,flags in [('default',[]),('guest',['--features','experimental-capability-guest']),('native',['--features','experimental-capability-native']),('all',['--all-features'])]:
        run(label+'-release-build',['cargo','build','--locked','--manifest-path','vm/Cargo.toml','--release',*flags])
        archive=target/'release/libmixer_vm.a';dynamic=target/'release/libmixer_vm.dylib'
        receipt['artifacts'][label]={'archive_sha256':sha(archive.read_bytes()),'dynamic_sha256':sha(dynamic.read_bytes())}
        output=run(label+'-symbols',['nm','-gU',str(dynamic)])
        receipt['symbols'][label]=sorted(set(re.findall(r'\b_mixer_vm_\w+',output)))
        expected=12 if label in ('default','guest') else 27
        if len(receipt['symbols'][label])!=expected:raise RuntimeError('unexpected public symbols: '+label)
        if label=='guest':continue
        tests=['ffi_smoke','ffi_numeric_smoke','ffi_table_memory_smoke','ffi_session_smoke']
        if label!='default':tests+=['capability_ffi_smoke']
        for test in tests:
            client=target/(label+'-'+test)
            run(label+'-'+test+'-compile',['clang','-std=c11','-Wall','-Wextra','-Werror','-isysroot',macsdk,'-I','vm/include','vm/tests/'+test+'.c',str(archive),'-o',str(client)])
            receipt['c_smokes'][label+'-'+test]=run(label+'-'+test+'-run',[str(client)]).strip()
    if receipt['symbols']['default']!=receipt['symbols']['guest']:raise RuntimeError('guest-only public symbols changed')
    if receipt['symbols']['native']!=receipt['symbols']['all']:raise RuntimeError('native symbols differ under combined features')
    # Compile the real client, including every C layout assertion, for other
    # proposed LP64 layouts. Objects and cross-linked programs are never executed.
    receipt['cross_builds']={}
    common=['-std=c11','-Wall','-Wextra','-Werror','-I','vm/include']
    run('macos-x86_64-c-layout',['clang',*common,'-target','x86_64-apple-macos14','-isysroot',macsdk,'-c','vm/tests/capability_ffi_smoke.c','-o',str(target/'client-x86_64.o')])
    for label,rust_target,compiler,cflags,overrides in [
        ('ios-arm64','aarch64-apple-ios','clang',['-target','arm64-apple-ios17.0','-isysroot',iossdk],{'IPHONEOS_DEPLOYMENT_TARGET':'17.0'}),
        ('android-arm64','aarch64-linux-android',str(NDK/'bin/aarch64-linux-android28-clang'),[],{'CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER':str(NDK/'bin/aarch64-linux-android28-clang'),'RUSTFLAGS':'-C link-arg=-Wl,-z,max-page-size=16384'})]:
        run(label+'-c-layout',[compiler,*common,*cflags,'-c','vm/tests/capability_ffi_smoke.c','-o',str(target/(label+'.o'))])
        run(label+'-rust-archive',['cargo','build','--locked','--manifest-path','vm/Cargo.toml','--release','--features','experimental-capability-native','--target',rust_target],overrides)
        archive=target/rust_target/'release/libmixer_vm.a';binary=target/(label+'-linked-client')
        extra=[] if label=='ios-arm64' else ['-ldl','-llog','-lm']
        run(label+'-c-link',[compiler,*common,*cflags,'vm/tests/capability_ffi_smoke.c',str(archive),*extra,'-o',str(binary)])
        run(label+'-file',['file',str(binary)])
        receipt['cross_builds'][label]={'archive_sha256':sha(archive.read_bytes()),'object_sha256':sha((target/(label+'.o')).read_bytes()),'linked_client_sha256':sha(binary.read_bytes()),'executed':False,'rust_compile_time_layout_assertions':True}
    check();receipt['source_unchanged_during_checks']=True
    receipt['known_limits']=['existing core/Error String/Arc/standard mutex OOM abort boundaries remain; negative children retained by old suites',
        'quarantine monotonic and capacity-pinning; poison ack failure is not recovery/reclamation',
        'native C takes count exit obligations independently of temporary Rust objects; trusted caller must ack actual exit',
        'dynamic post is trusted opaque bytes; no JSON/grants/I/O/Swift bridge/scheduler/release profile or identity qualification',
        'raw tuple is scoped to supplied valid session; equal token bits in two valid contexts cannot reveal caller intent',
        'iOS/Android cross-build/link only; phones disconnected, no physical run or mobile lifecycle claim',
        'full Swift/FieldLog owned-VM execution, package dogfood, stores/operations/GA remain open']
    receipt['allocation_method']='System GlobalAlloc requested Layout sizes; realloc postreturn logical live accounting excludes allocator internal overlap/RSS; no constructor or process-wide OOM guarantee'
    receipt['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();receipt['result']='scoped host+C+cross-build checks passed; independent integrated review pending';save()

if __name__=='__main__':main()
