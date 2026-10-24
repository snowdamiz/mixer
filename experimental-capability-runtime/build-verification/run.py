#!/usr/bin/env python3
"""Qualify the frozen archive builder on host/cross tools; never operate devices."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time

BASE=Path(__file__).resolve().parent
PACKAGE=BASE.parent
ROOT=PACKAGE.parent
PIN='1adb25c48a8723f56ed2649712fe5e357920c53e'
PREVIOUS_PIN='b25e3b7de2391a80d12e7fd75e60903495bec120'
LIBRARY='libmixer_vm_capability_experimental.a'
spec=importlib.util.spec_from_file_location('builder',PACKAGE/'build-vm.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--artifacts',type=Path,required=True)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--rustc',type=Path,required=True)
    parser.add_argument('--ndk',type=Path,required=True)
    args=parser.parse_args()
    evidence=args.output.absolute();artifacts=args.artifacts.absolute()
    evidence.mkdir(parents=True,exist_ok=False);artifacts.mkdir(parents=True,exist_ok=False)
    inputs=[PACKAGE/'build-vm.py',PACKAGE/'build-tests/test_builder.py',PACKAGE/'build-tests/mixed_registry.c',PACKAGE/'build-tests/guest_ui.c',BASE/'README.md',Path(__file__)]
    manifest={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    receipt={'schema_version':1,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_revision':PIN,
        'head_at_start':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'implementation_selection':{'model':'gpt-6.1-sol','reasoning_effort':'xhigh'},'source_files':manifest,
        'source_manifest_sha256':hashlib.sha256(''.join(f'{h}  {p}\n' for p,h in sorted(manifest.items())).encode()).hexdigest(),
        'commands':[],'targets':{},'host_tests':{},'actual_native_revision_frozen':True,'device_commands':False,
        'qualification':'local immutable native-only source builder and host public C/UI consumers; cross compile/link only; no release/identity/device/bit-reproducibility claim',
        'native_feature_selection':['experimental-capability-mailbox','experimental-capability-guest','experimental-capability-native'],
        'stream_cache_features_enabled':False,'previous_qualified_artifacts_modified':False}
    def save(name='progress.json'):(evidence/name).write_text(json.dumps(receipt,indent=2)+'\n')
    def run(name,argv,maximum=8*1024*1024):
        start=time.monotonic();code,raw,problem=b.capture([str(a) for a in argv],cwd=ROOT,maximum=maximum)
        path=evidence/(name+'.log');path.write_bytes(raw)
        entry={'name':name,'argv':[str(a) for a in argv],'cwd':str(ROOT),'exit_code':code,'problem':problem,
            'elapsed_host_development_seconds':round(time.monotonic()-start,6),'log':path.name,'sha256':sha(path)}
        receipt['commands'].append(entry);save()
        if code or problem:raise RuntimeError(name+' failed: '+str(path))
        return raw.decode().strip()
    try:
        run('python-version',[sys.executable,'--version'])
        normal=run('tests-normal',[sys.executable,PACKAGE/'build-tests/test_builder.py'])
        optimized=run('tests-optimized',[sys.executable,'-O',PACKAGE/'build-tests/test_builder.py'])
        counts=[int(re.search(r'Ran (\d+) tests',text).group(1)) for text in (normal,optimized)]
        if counts!=[24,24]:raise RuntimeError('unexpected boundary test function count')
        receipt['host_tests']={'normal_functions':counts[0],'optimized_functions':counts[1],'fixture_scope':'original temporary Git/filesystem/process cases; not VM semantic qualification'}
        receipt['unchanged_headers']={}
        for name in ('mixer_vm.h','mixer_vm_capability.h'):
            path='vm/include/'+name
            run('previous-'+name,['git','show',PREVIOUS_PIN+':'+path])
            old=(evidence/('previous-'+name+'.log')).read_bytes()
            current=b.frozen_inputs(PIN)[path]['bytes']
            if old!=current:raise RuntimeError('previous public header bytes changed: '+name)
            receipt['unchanged_headers'][name]={'previous_source_revision':PREVIOUS_PIN,'source_revision':PIN,'sha256':hashlib.sha256(current).hexdigest()}
        for target in ('host','ios','ios-simulator','android'):
            output=artifacts/target
            command=[sys.executable,PACKAGE/'build-vm.py','--revision',PIN,'--target',target,'--output',output,'--cache',args.cache,'--rustc',args.rustc]
            if target=='android':command+=['--ndk',args.ndk]
            run('build-'+target,command)
            build=json.loads((output/'receipt.json').read_text())
            if build['builder_sha256']!=manifest['experimental-capability-runtime/build-vm.py']:raise RuntimeError('builder bytes changed')
            if build['source_revision']!=PIN or build['feature']!='experimental-capability-native' or build['features']!=receipt['native_feature_selection']:raise RuntimeError('source/feature mismatch')
            if sorted(p.name for p in (output/'lib').iterdir())!=[LIBRARY]:raise RuntimeError('staged library directory is not static-only distinct archive')
            if sorted(p.name for p in (output/'include').iterdir())!=['mixer_vm.h','mixer_vm_capability.h','mixer_vm_guest_ui.h']:raise RuntimeError('staged header inventory mismatch')
            if build['public_C_symbols']!=sorted(b.PUBLIC_C_SYMBOLS):raise RuntimeError('public C symbol inventory mismatch')
            for name,data in build['source_blobs'].items():
                if sha(output/'source'/name)!=data['sha256']:raise RuntimeError('source changed after builder: '+name)
            for name,data in build['headers'].items():
                if sha(output/'include'/name)!=data['sha256']:raise RuntimeError('staged header drift')
            if sha(output/'lib'/LIBRARY)!=build['library']['sha256']:raise RuntimeError('staged archive drift')
            shutil.copyfile(output/'receipt.json',evidence/(target+'-builder-receipt.json'))
            for log in output.glob('*.log'):shutil.copyfile(log,evidence/(target+'-'+log.name))
            receipt['targets'][target]={'builder_receipt':target+'-builder-receipt.json','builder_receipt_sha256':sha(output/'receipt.json'),
                'library':build['library'],'headers':build['headers'],'source_manifest_sha256':build['source_manifest_sha256'],
                'source_archive_sha256':build['source_archive_sha256'],'source_files':build['source_file_count'],
                'public_C_symbol_count':len(build['public_C_symbols']),'public_C_symbols':build['public_C_symbols'],
                'features':build['features'],'rust_target':build['rust_target'],'executed':target=='host'}
            clang=build['tools']['linker']['path'];flags=[];libraries=[]
            if target=='host':
                flags=['-isysroot',build['environment']['SDKROOT'],'-mmacosx-version-min=14.0']
            elif target in ('ios','ios-simulator'):
                triple='arm64-apple-ios26.0' if target=='ios' else 'arm64-apple-ios26.0-simulator'
                flags=['-target',triple,'-isysroot',build['environment']['SDKROOT']]
            else:libraries=['-ldl','-llog','-lm','-Wl,-z,max-page-size=16384']
            common=[clang,'-std=c11','-Wall','-Wextra','-Werror',*flags,'-I',output/'include']
            fixture=output/'source/vm/tests/capability_ffi_smoke.c';client=output/'capability-smoke'
            run(target+'-c-layout',[*common,'-c',fixture,'-o',output/'capability-layout.o'])
            run(target+'-c-link',[*common,fixture,output/'lib'/LIBRARY,*libraries,'-o',client])
            run(target+'-client-file',['/usr/bin/file',client])
            receipt['targets'][target]['client_sha256']=sha(client)
            receipt['targets'][target]['layout_object_sha256']=sha(output/'capability-layout.o')
            ui=output/'guest-ui-smoke'
            run(target+'-ui-c-link',[*common,PACKAGE/'build-tests/guest_ui.c',output/'lib'/LIBRARY,*libraries,'-o',ui])
            run(target+'-ui-client-file',['/usr/bin/file',ui])
            receipt['targets'][target]['ui_client_sha256']=sha(ui)
            if target=='host':
                result=run('host-c-smoke',[client])
                if 'passed27 ' not in result:raise RuntimeError('unexpected C smoke count')
                receipt['host_tests']['native_C_status_alias_checks']=27
                mixed=output/'mixed-registry'
                run('mixed-registry-compile',[*common,PACKAGE/'build-tests/mixed_registry.c',output/'lib'/LIBRARY,'-o',mixed])
                result=run('mixed-registry-run',[mixed])
                if 'passed52 ' not in result:raise RuntimeError('unexpected mixed registry count')
                receipt['host_tests']['one_archive_mixed_registry_checks']=52
                receipt['host_tests']['mixed_client_sha256']=sha(mixed)
                result=run('host-ui-c-smoke',[ui])
                if 'passed42 ' not in result:raise RuntimeError('unexpected UI public C smoke count')
                receipt['host_tests']['guest_ui_public_C_checks']=42
            save()
        if len({v['source_manifest_sha256'] for v in receipt['targets'].values()})!=1 or len({v['source_archive_sha256'] for v in receipt['targets'].values()})!=1:raise RuntimeError('source export differs by target')
        for path,expected in manifest.items():
            if sha(ROOT/path)!=expected:raise RuntimeError('qualification input changed: '+path)
        receipt['qualification_source_unchanged']=True
        receipt['known_limits']=['trusted installed official tools and coordinated owned cache; no hostile same-user/tool sandbox',
            'no bit-for-bit binary reproducibility, SDK consumer identity, signed attestation, release authorization or published packaging',
            'iOS/simulator/Android compile and C link only; no simulator launch or physical device command',
            'existing bounded VM/native/Swift-full-runtime limitations unchanged; no full Swift/FieldLog execution claim',
            'source-only export excludes SDK Swift source and all mutable working-tree inputs',
            'native-only package is distinct from earlier locally combined stream/cache/native bridge tests; downstream Swift bridge/activation must be retested against this exact new archive',
            'OS process-group probe denial is conservative cleanup failure/quarantine; hostile session escape and kernel uninterruptible termination are not bounded']
        receipt['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();receipt['result']='scoped frozen builder,24 normal+24 optimized host tests,27 native C,52 mixed registry and42 guest UI C checks plus3 cross C/UI links passed'
        receipt['evidence_files']={p.name:sha(p) for p in sorted(evidence.iterdir()) if p.is_file() and p.name not in ('receipt.json','progress.json','failure.json')}
        save('receipt.json');print(evidence/'receipt.json')
    except BaseException as error:
        receipt['failure']=str(error);save('failure.json');raise
if __name__=='__main__':main()
