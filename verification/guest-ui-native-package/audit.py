#!/usr/bin/env python3
"""Read-only binding audit of the exact native package; never run device tools."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
PIN='1adb25c48a8723f56ed2649712fe5e357920c53e'
OLD_PIN='b25e3b7de2391a80d12e7fd75e60903495bec120'
PACKAGE=ROOT/'experimental-capability-runtime'
LIBRARY='libmixer_vm_capability_experimental.a'
HEADERS={'mixer_vm.h':'18c2498d0d1deae2c998ef9f4b3f811b2184c45e8169610012b05e99342385fd',
         'mixer_vm_capability.h':'9213c34ebf0f14d14f3319172e83647f704f3a02a60d413b4de990884357b4a6',
         'mixer_vm_guest_ui.h':'d8d8217b900662e77787a8729f5c1cfe096b0df25ffe39e289f89d69fc156ab5'}
FEATURES=['experimental-capability-mailbox','experimental-capability-guest','experimental-capability-native']
def sha(raw):return hashlib.sha256(raw).hexdigest()
def file_sha(path):return sha(path.read_bytes())
def need(ok,message):
    if not ok:raise RuntimeError(message)
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qualification',type=Path,required=True)
    parser.add_argument('--stage',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();evidence=args.qualification.resolve();stage=args.stage.resolve();out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=False)
    receipt=json.loads((evidence/'receipt.json').read_bytes())
    result={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_revision':PIN,
            'argv':[sys.executable,*sys.argv],'cwd':str(Path.cwd()),'python_version':platform.python_version(),
            'driver_sha256':file_sha(Path(__file__)),'qualification_receipt_sha256':file_sha(evidence/'receipt.json'),
            'checks':0,'commands':[],'targets':{},'device_commands':False,
            'scope':'Post-build immutable source, header, archive, symbol, C consumer and retained prior-artifact binding audit; no Swift/device/release qualification'}
    def check(ok,message):need(ok,message);result['checks']+=1
    def run(name,argv):
        command=[str(a) for a in argv];p=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
        log=out/(name+'.log');log.write_bytes(p.stdout)
        result['commands'].append({'argv':command,'cwd':str(ROOT),'exit_code':p.returncode,'log':log.name,'sha256':sha(p.stdout)})
        check(p.returncode==0,name);return p.stdout
    try:
        check(receipt['source_revision']==PIN,'immutable qualification revision')
        check(receipt['qualification_source_unchanged'] is True,'qualification source unchanged')
        check(receipt['native_feature_selection']==FEATURES and receipt['stream_cache_features_enabled'] is False,'native-only feature selection')
        check(len(receipt['commands'])==33 and all(c['exit_code']==0 and c['problem'] is None for c in receipt['commands']),'all33 qualification commands passed')
        for command in receipt['commands']:check(file_sha(evidence/command['log'])==command['sha256'],'qualification log '+command['name'])
        for name,digest in receipt['evidence_files'].items():check(file_sha(evidence/name)==digest,'qualification evidence '+name)
        for name,digest in receipt['source_files'].items():check(file_sha(ROOT/name)==digest,'current qualification tooling '+name)
        check(receipt['host_tests']['normal_functions']==24 and receipt['host_tests']['optimized_functions']==24,'normal and optimized boundary counts')
        for key,count in [('native_C_status_alias_checks',27),('one_archive_mixed_registry_checks',52),('guest_ui_public_C_checks',42)]:
            check(receipt['host_tests'][key]==count,key)
        old_qualification=json.loads((PACKAGE/'build-verification/2026-10-23-final-v3/receipt.json').read_bytes())
        old_stage=PACKAGE/'build-verification/local/qualified-final-v3'
        for target in ('host','ios','ios-simulator','android'):
            selected=stage/target;build=json.loads((selected/'receipt.json').read_bytes());entry=receipt['targets'][target]
            check(file_sha(selected/'receipt.json')==entry['builder_receipt_sha256'],'selected builder receipt '+target)
            check(build['source_revision']==PIN and build['features']==FEATURES,'selected source/feature '+target)
            check(build['builder_sha256']==file_sha(PACKAGE/'build-vm.py'),'selected builder bytes '+target)
            check(sorted(p.name for p in (selected/'lib').iterdir())==[LIBRARY],'one static archive '+target)
            check(sorted(p.name for p in (selected/'include').iterdir())==sorted(HEADERS),'three headers '+target)
            for name,digest in HEADERS.items():
                raw=(selected/'include'/name).read_bytes()
                check(sha(raw)==digest and raw==subprocess.check_output(['git','show',PIN+':vm/include/'+name],cwd=ROOT),'frozen header '+target+'/'+name)
                if name!='mixer_vm_guest_ui.h':
                    check(raw==subprocess.check_output(['git','show',OLD_PIN+':vm/include/'+name],cwd=ROOT),'unchanged old header '+target+'/'+name)
            source_manifest=''
            for name,blob in sorted(build['source_blobs'].items()):
                raw=subprocess.check_output(['git','show',PIN+':'+name],cwd=ROOT)
                check(sha(raw)==blob['sha256'] and (selected/'source'/name).read_bytes()==raw,'immutable exported blob '+target+'/'+name)
                source_manifest+=blob['sha256']+'  '+name+'\n'
            check(sha(source_manifest.encode())==build['source_manifest_sha256']==entry['source_manifest_sha256'],'source manifest '+target)
            check(file_sha(selected/'source.tar')==build['source_archive_sha256']==entry['source_archive_sha256'],'source tar '+target)
            library=selected/'lib'/LIBRARY
            check(library.read_bytes()[:8]==b'!<arch>\n' and file_sha(library)==build['library']['sha256']==entry['library']['sha256'],'staged archive '+target)
            nm=Path(build['tools']['llvm_nm']['path'])
            check(file_sha(nm.resolve())==build['tools']['llvm_nm']['sha256'],'matching inspected LLVM tool '+target)
            raw=run(target+'-symbols',[nm,'--extern-only','--defined-only',library]).decode()
            names=[row.split()[-1].removeprefix('_') for row in raw.splitlines() if row.split() and row.split()[-1].removeprefix('_').startswith('mixer_vm_')]
            check(len(names)==28 and len(set(names))==28 and sorted(names)==build['public_C_symbols']==entry['public_C_symbols'],'exactly one each28 public APIs '+target)
            check(names.count('mixer_vm_capability_guest_ui_validate_v1')==1,'one UI validator '+target)
            check(file_sha(selected/'capability-smoke')==entry['client_sha256'] and file_sha(selected/'guest-ui-smoke')==entry['ui_client_sha256'],'C consumer products '+target)
            previous=json.loads((old_stage/target/'receipt.json').read_bytes())
            check(previous['source_revision']==OLD_PIN and file_sha(old_stage/target/'receipt.json')==old_qualification['targets'][target]['builder_receipt_sha256'],'prior receipt preserved '+target)
            check(file_sha(old_stage/target/'lib'/LIBRARY)==previous['library']['sha256']==old_qualification['targets'][target]['library']['sha256'],'prior archive preserved '+target)
            result['targets'][target]={'library_sha256':entry['library']['sha256'],'source_manifest_sha256':build['source_manifest_sha256'],'public_C_symbol_count':len(names),'prior_qualified_archive_unchanged':True}
        check(len({v['source_manifest_sha256'] for v in result['targets'].values()})==1,'identical frozen source manifest across all targets')
        result['status']='scoped_binding_audit_passed'
    except BaseException as error:
        result['status']='failed';result['failure']=str(error);raise
    finally:
        result['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(out/'receipt.json')
if __name__=='__main__':main()
