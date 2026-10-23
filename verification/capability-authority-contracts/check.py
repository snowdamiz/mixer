#!/usr/bin/env python3
"""Original static contract audit; not a runtime validator or authorization tool."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
BASELINE='1ab4d4ee76a5d4ba206bd370cbeeeb73a7c6c636'
FROZEN={
 'contracts/capability-execution-v1.json':'898ea22b93a5b0dcd94c3b54f7cc97c41a259cd2285cbacd54bf0bd52ba48c97',
 'contracts/runtime-identity-v2.json':'d66c44d49f79325a643516f33bd19ba882ef711a5139afb54499b39931ba48b8',
 'contracts/release-v3.json':'935c2311fb32a72d4b1e49ce55fd1c63f9f8448386a7076db48550767f6212f0',
 'contracts/activation-v2.json':'e72c75d69e089cc3a23e09cc2f65e1902d9fc8f0bee401555507ec36d5e224d4',
 'docs/capability-authorized-execution-design.md':'13b047877dd1ff842b4e8984335680805709ff7b6e5a7e2e7a9e033d46a136d9',
}
OLD={
 'contracts/activation-v1.json':'a0816bddd38afdfedb4fc2d50e522b0c808e64b640fb91d7991f895dc405989c',
 'contracts/guest-capability-transport-v1.json':'052ebe9fbdc20a41307332086767e7903680bc83ba273c696edf9187be6b6439',
 'contracts/release-v1.json':'ff899af876c1bb28b0c65c913702b22af9e7031537f5d37ff36f41bf88e12769',
 'contracts/release-v2.json':'ab4f5d881b1fd0cb91d01bd1da25a0b864690d29936063e0144304bfd275ba4b',
 'contracts/runtime-identity-v1.json':'454daf6fdc16955b32a725fd5fa230a4f7cc0c1f3327223bf73d8e6331fcf30c',
 'contracts/ui-v1.json':'e9983da1c8f5b79dcead9fc7c99172be374ddeba319308615108651cb3931ac5',
 'contracts/vm-profile-v1.json':'813a54a4e198a73d49afffe7c8d9cf54f6e76bfca80dd6556a439a4bdf1bdf4c',
 'contracts/vm-session-v1.json':'6921f707b943ab76cdc3dae996ac7448d3c720676f290e259c892afcab1bf41a',
}
AUX={
 'vm/include/mixer_vm.h':'18c2498d0d1deae2c998ef9f4b3f811b2184c45e8169610012b05e99342385fd',
 'vm/include/mixer_vm_capability.h':'9213c34ebf0f14d14f3319172e83647f704f3a02a60d413b4de990884357b4a6',
 'vm/profiles/numeric-v2.json':'4eb10d61ddc0092bec5f40b40cc3473ae3443491e7bdfe49b9cae80b58e09d57',
 'vm/profiles/table-memory-v3.json':'c46d5527aa1d4ed1e4b282269546a132d75f8f1895640978165db68ec9ed028d',
 'capabilities/schema/v1.json':'2b7519e0daea5a1dd25f8d2f93d2dc25c32caa376b8cf21a15e69505c621d77e',
 'capabilities/schema/hashes.json':'5407bea4cbb2a43be1a2bd8faa9983b06fe158ecc1bca99b2123e7f0869bc185',
 'experimental-capability-runtime/build-vm.py':'e7e34079d7af7d26162ccfc0c43cc6d269fb500ed42bd5e1aef91765e2fee076',
 'experimental-capability-runtime/build-tests/test_builder.py':'541169114d62b237844cf815b1b5495c540d59c3ff293533eec32f6ccfe51138',
}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def pairs(items):
    result={}
    for key,value in items:
        if key in result:raise ValueError('duplicate JSON key '+key)
        result[key]=value
    return result

def read(path):return json.loads(Path(path).read_bytes(),object_pairs_hook=pairs)
def head(major,value):
    if value<24:return bytes([major*32+value])
    for code,size in [(24,1),(25,2),(26,4),(27,8)]:
        if value<1<<(8*size):return bytes([major*32+code])+value.to_bytes(size,'big')
    raise ValueError('uint64 overflow')

def cbor(value):
    """Small original encoder for the grant descriptor's restricted data types."""
    if isinstance(value,bool):return bytes([245 if value else 244])
    if isinstance(value,int) and value>=0:return head(0,value)
    if isinstance(value,str):
        raw=value.encode();return head(3,len(raw))+raw
    if isinstance(value,list):return head(4,len(value))+b''.join(map(cbor,value))
    if isinstance(value,dict):
        entries=sorted((cbor(key),cbor(child)) for key,child in value.items())
        return head(5,len(entries))+b''.join(key+child for key,child in entries)
    raise ValueError('unsupported canonical type')

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.absolute();output.mkdir(parents=True,exist_ok=False)
    inputs={**FROZEN,**OLD,**AUX,str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))}
    receipt={'schema_version':1,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'baseline_revision':BASELINE,'source_files':inputs,'argv':[sys.executable,*sys.argv],'cwd':str(ROOT),
        'python':sys.version,'commands':[],'checks':[],'model':'gpt-6.1-sol','reasoning_effort':'xhigh',
        'scope':'Static JSON/closed-schema/policy/digest audit only; proposed/implementation status lives in design. This checker never authorizes a release or qualifies a parser/runtime/native effect/device.',
        'runtime_or_device_commands':False,'independent_review':False}
    def test(label,value):
        if not value:raise ValueError(label)
        receipt['checks'].append(label)
    def git(*arguments):
        command=['git','--no-replace-objects',*arguments]
        result=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
        receipt['commands'].append({'argv':command,'exit_code':result.returncode,
            'stdout_bytes':len(result.stdout),'stdout_sha256':hashlib.sha256(result.stdout).hexdigest(),
            'stderr':result.stderr[:1024].decode(errors='replace')})
        if result.returncode:raise ValueError('Git baseline read failed')
        return result.stdout
    def frozen():
        for path,expected in inputs.items():
            if sha(ROOT/path)!=expected:raise ValueError('source freeze mismatch: '+path)
    try:
        frozen();receipt['head_at_start']=git('rev-parse','HEAD').decode().strip();receipt['git_version']=git('--version').decode().strip()
        names=list(FROZEN)[:4];e,i,r,a=[read(ROOT/name) for name in names];eh=sha(ROOT/names[0])
        for name,document in zip(names,[e,i,r,a]):
            label=Path(name).name
            test(label+' immutable definition',document['kind']=='immutable_contract_definition' and 'status' not in document and 'implementation_status' not in document)
            def closed(value):
                if isinstance(value,dict):
                    test(label+' no mutable implementation marker','implemented' not in value)
                    if value.get('type')=='object':test(label+' closed schema',value['additionalProperties'] is False and set(value['required'])==set(value['properties']) and len(value['required'])==len(set(value['required'])))
                    for child in value.values():closed(child)
                elif isinstance(value,list):
                    for child in value:closed(child)
            closed(document)
        test('identity references',i['execution_contract']['sha256']==eh==i['descriptor_schema']['properties']['capability_execution']['properties']['contract_sha256']['const'])
        test('release reference',r['execution_binding']['execution_contract_sha256']==eh);test('activation reference',a['execution_contract']['sha256']==eh)
        for key in ['wire','native_header','legacy_header','base_profile','capability_schema_file']:
            ref=e['references'][key];test('file reference '+key,sha(ROOT/ref['path'])==ref['sha256'])
        wire=read(ROOT/'contracts/guest-capability-transport-v1.json')
        test('six imports exact',len(e['imports']['additional_capability_functions'])==6 and {x['name']:([p['type'] for p in x['params']],x['results'],x.get('operation_tag')) for x in wire['imports']['functions']}=={x['name']:(x['parameters'],x['results'],x.get('operation_tag')) for x in e['imports']['additional_capability_functions']})
        test('two legacy imports',e['imports']['unchanged_legacy_functions']==[{'module':'mixer','name':'checkpoint','parameters':[],'results':[]},{'module':'mixer','name':'abort','parameters':['i32'],'results':[]}])
        v2=read(ROOT/'contracts/release-v2.json')
        test('manifest closed keys preserved',set(r['manifest_fields'])==set(v2['manifest_fields'])==set(r['wire_types']['manifest_required']))
        test('assignment closed keys preserved',set(r['assignment_fields'])==set(v2['assignment_fields'])==set(r['wire_types']['assignment_required']))
        test('grant definition preserved',r['capability_grant_descriptor']==v2['capability_grant_descriptor'])
        grant=hashlib.sha256(cbor(r['capability_grant_descriptor'])).hexdigest()
        test('original grant CBOR encoder hash',grant==r['capability_grant_descriptor_sha256']==e['references']['grant_descriptor_sha256']==a['execution_contract']['grant_descriptor_sha256'])
        receipt['grant_descriptor_sha256']=grant
        profile=read(ROOT/'vm/profiles/table-memory-v3.json')
        for key in ['module_bytes','types','functions_including_imports','instructions','parameters_plus_locals_per_function','globals','exports','operand_values_per_frame','call_depth','control_depth_including_function','memory_pages','name_utf8_bytes']:
            test('fixed ceiling '+key,e['ceilings'][key]==profile['unchanged_ceilings'][key])
        test('fuel ceiling',e['ceilings']['fuel_per_turn']==profile['unchanged_ceilings']['fuel_per_invocation'])
        test('hostcall ceiling',e['ceilings']['host_calls_per_turn']==profile['unchanged_ceilings']['host_calls_per_invocation'])
        test('native pool/request ceilings',(e['ceilings']['shared_native_sessions_including_reserved_closing_reclaiming'],e['ceilings']['maximum_requests'],e['ceilings']['native_reservation_bytes'])==(16,8,8388608))
        test('separate close work',e['scheduler']['host_close_tasks']==e['scheduler']['native_close_dispatch_jobs']==1 and 'close_tasks' not in e['scheduler'])
        test('zero page exact','exact0..64' in e['effective_memory'] and 'never round' in r['execution_binding']['zero_page_effective_limit'])
        test('effects gate',a['lifecycle']['effects_gate']==e['selection']['effects_gate']=='after-verified-startup-v1')
        test('material budget',e['installed_material']['input']['maximum_file_bytes']*e['installed_material']['input']['maximum_material_files']==e['installed_material']['input']['maximum_total_material_bytes'])
        if e['preservation']!=OLD:raise ValueError('old baseline set differs')
        for path,expected in OLD.items():
            test('old hash '+path,sha(ROOT/path)==expected)
            raw=git('show',BASELINE+':'+path)
            test('old bytes '+path,raw==(ROOT/path).read_bytes())
        if len(receipt['checks'])!=241:raise ValueError('unexpected static assertion count')
        frozen();receipt['source_unchanged_during_checks']=True;receipt['static_assertions_passed']=len(receipt['checks'])
        receipt['old_contracts_byte_preserved']=len(OLD);receipt['auxiliary_frozen_inputs_preserved']=len(AUX)
        receipt['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();receipt['result']='241 static assertions pass;8 old contracts byte-equal committed baseline;8 auxiliary frozen inputs unchanged; not execution authorization'
        log='\n'.join(f'PASS {n+1}: {label}' for n,label in enumerate(receipt['checks']))+'\n'+receipt['result']+'\n'
        (output/'checks.log').write_text(log);receipt['checks_log_sha256']=sha(output/'checks.log')
        (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'receipt':str(output/'receipt.json'),'sha256':sha(output/'receipt.json'),'static_assertions':len(receipt['checks'])},indent=2))
    except BaseException as error:
        receipt['error']=str(error);(output/'failure.json').write_text(json.dumps(receipt,indent=2)+'\n');raise
if __name__=='__main__':main()
