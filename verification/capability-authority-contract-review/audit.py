#!/usr/bin/env python3
"""Bounded read-only consistency checks; never an execution/OTA authorization gate."""
from pathlib import Path
import datetime
import hashlib
import json
import platform
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PINS = {
    'contracts/capability-execution-v1.json':'898ea22b93a5b0dcd94c3b54f7cc97c41a259cd2285cbacd54bf0bd52ba48c97',
    'contracts/runtime-identity-v2.json':'d66c44d49f79325a643516f33bd19ba882ef711a5139afb54499b39931ba48b8',
    'contracts/release-v3.json':'935c2311fb32a72d4b1e49ce55fd1c63f9f8448386a7076db48550767f6212f0',
    'contracts/activation-v2.json':'e72c75d69e089cc3a23e09cc2f65e1902d9fc8f0bee401555507ec36d5e224d4',
    'docs/capability-authorized-execution-design.md':'13b047877dd1ff842b4e8984335680805709ff7b6e5a7e2e7a9e033d46a136d9',
}
BASELINE = '1ab4d4ee76a5d4ba206bd370cbeeeb73a7c6c636'
INSPECTED = [
    'runtime-identity/Package.swift','runtime-identity/Sources/MixerRuntimeIdentity/RuntimeIdentity.swift',
    'runtime-identity/build-tools/capture.py','runtime-identity/build-tools/embed.py',
    'updates/Sources/MixerUpdates/Verifier.swift','updates/Sources/MixerUpdates/ColdStartModels.swift',
    'updates/Sources/MixerUpdates/ColdStartUpdater.swift','activation/Package.swift',
    'activation/Sources/MixerActivation/InstalledExecution.swift','activation/Sources/MixerActivation/StartupWork.swift',
    'activation/Sources/MixerActivation/ColdStartRuntime.swift','experimental-capability-runtime/Package.swift',
    'experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/Types.swift',
    'experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/Native.swift',
    'experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/Session.swift',
    'experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/Ownership.swift',
    'sdk/Sources/MixerCapabilities/Host.swift','sdk/Sources/MixerCapabilities/InstalledCapabilityAdapters.swift',
    'sdk/Sources/MixerCapabilities/AppPrivateKeyValueStore.swift','sdk/Sources/MixerCapabilities/GeneratedIdentity.swift',
    'vm/src/lib.rs','vm/src/decode.rs','vm/src/execute.rs','vm/src/ffi.rs','vm/src/session.rs',
    'vm/src/capability_ffi/api.rs','vm/src/capability_ffi/error.rs','vm/src/capability_ffi/session.rs',
    'vm/src/experimental_capability_guest/mod.rs','services/protocol/protocol.go','services/protocol/v2.go',
    'services/release/versioned.go','services/release/storage.go','services/release/store.go','services/release/postgres.go',
]


def sha(data): return hashlib.sha256(data).hexdigest()
def unique(pairs):
    result = {}
    for key,value in pairs:
        if key in result: raise RuntimeError('duplicate decoded JSON key '+key)
        result[key] = value
    return result

def main():
    target = HERE / 'receipt.json'
    if target.exists(): raise RuntimeError('preserve prior receipt')
    checks = []
    def require(value, name):
        if not value: raise RuntimeError(name)
        checks.append(name)
    def load(relative): return json.loads((ROOT / relative).read_text(), object_pairs_hook=unique)
    for path,digest in PINS.items(): require(sha((ROOT/path).read_bytes()) == digest,'frozen input '+path)
    execution,identity,release,activation = [load(p) for p in list(PINS)[:4]]
    old_identity=load('contracts/runtime-identity-v1.json'); old_release=load('contracts/release-v2.json')
    old = {}
    for path,digest in execution['preservation'].items():
        baseline = subprocess.check_output(['git','show',BASELINE+':'+path],cwd=ROOT)
        actual = (ROOT/path).read_bytes()
        require(actual == baseline and sha(actual) == digest,'unchanged legacy bytes '+path)
        old[path] = digest
    require(len(old)==8,'eight old contract inputs')
    for label,reference in execution['references'].items():
        if isinstance(reference,dict) and set(reference).issuperset({'path','sha256'}):
            require(sha((ROOT/reference['path']).read_bytes())==reference['sha256'],'exact external reference '+label)
    execution_hash=PINS['contracts/capability-execution-v1.json']
    for name,obj in [('identity',identity),('activation',activation)]:
        require(obj['execution_contract']['sha256']==execution_hash and obj['execution_contract']['path']=='contracts/capability-execution-v1.json','execution reference '+name)
    require(release['execution_binding']['execution_contract_sha256']==execution_hash,'execution reference release')
    schema=identity['descriptor_schema'];props=schema['properties'];caps=props['capability_execution']['properties']
    require(caps['contract_sha256']['const']==execution_hash,'identity bound execution digest')
    require(set(schema['required'])==set(old_identity['fields'])|{'capability_execution'},'identity root fields additive only')
    for name in ['application','platform','engine','toolchain','build','execution']:
        require(set(props[name]['required'])==set(old_identity['fields'][name]),'identity existing field set '+name)
    require(props['schema']['const']==2 and props['engine']['properties']['guest_abi']['const']==2 and props['engine']['properties']['ui_schema']['const']==1,'identity2 ABI2 UI1')
    require(props['execution']['properties']['protocol']['const']==3 and caps['route']['const']=='capability-guest-v1','identity explicit route3')
    require(props['engine']['properties']['profile']['const']=='mixer-table-memory-v3','fixed unchanged base grammar')
    require(execution['selection']['identity_schema']==2 and execution['selection']['release_schema']==3 and execution['selection']['guest_abi']==2,'execution tuple')
    require(activation['installed_policy']['tuple']=={'identity_schema':2,'release_protocol':3,'guest_abi':2,'ui_schema':1,'base_profile':'mixer-table-memory-v3','route':'capability-guest-v1'},'activation closed tuple')
    require(identity['domain']!=old_identity['domain'] and 'v2' in identity['domain'],'identity domain separation')
    require(set(release['manifest_fields'])==set(old_release['manifest_fields']),'release manifest field set unchanged')
    require(set(release['assignment_fields'])==set(old_release['assignment_fields']),'release assignment field set unchanged')
    for key,value in [('schema',3),('protocol',3),('guest_abi',2),('ui_schema',1)]: require(release['manifest_fields'][key]==value,'release fixed '+key)
    require(release['assignment_fields']['schema']==3,'assignment fixed3')
    for key in ['artifact_signature','assignment_signature']:
        require(release['canonicalization'][key]!=old_release['canonicalization'][key] and '.v3' in release['canonicalization'][key],'signature domain '+key)
    for key in ['capability_grant_descriptor','capability_grant_descriptor_sha256','capability_grant_descriptor_hash','capability_grant_entry_fields']:
        require(release[key]==old_release[key],'exact existing grant definition '+key)
    for label in ['manifest','assignment']:
        require(set(release['wire_types'][label+'_required'])==set(release[label+'_fields']),'all required '+label+' fields')
    wire=load('contracts/guest-capability-transport-v1.json')
    functions=[]
    for item in wire['imports']['functions']:
        record={'name':item['name'],'parameters':[p['type'] for p in item['params']],'results':item['results']}
        if 'operation_tag' in item: record['operation_tag']=item['operation_tag']
        functions.append(record)
    require(execution['imports']['additional_capability_functions']==functions and len(functions)==6,'exact six existing capability signatures/tags')
    require(execution['imports']['unchanged_legacy_functions']==[{'module':'mixer','name':'checkpoint','parameters':[],'results':[]},{'module':'mixer','name':'abort','parameters':['i32'],'results':[]}],'two unchanged legacy signatures')
    object_schemas=0
    def closed_schema(node):
        nonlocal object_schemas
        if isinstance(node,dict):
            if node.get('type')=='object':
                require(node.get('additionalProperties') is False and set(node.get('required',[]))==set(node.get('properties',{})),'closed mandatory object schema '+str(object_schemas))
                object_schemas+=1
            for child in node.values(): closed_schema(child)
        elif isinstance(node,list):
            for child in node: closed_schema(child)
    closed_schema(schema)
    material=execution['installed_material']
    for name in ['http_configuration_schema','storage_configuration_schema','bridge_policy_schema']: closed_schema(material[name])
    require(material['input']['maximum_file_bytes']==65536 and material['input']['maximum_material_files']==5 and material['input']['maximum_total_material_bytes']==327680,'bounded five-role immutable materials')
    require(execution['scheduler']['host_close_tasks']==1 and execution['scheduler']['native_close_dispatch_jobs']==1,'separate coalesced close job bounds')
    require(execution['ceilings']['maximum_requests']==8 and execution['ceilings']['swift_pending_live_draining_owners']==16 and execution['ceilings']['shared_native_sessions_including_reserved_closing_reclaiming']==16,'consistent eight request and shared16 ceilings')
    for name,obj in [('execution',execution),('identity',identity),('release',release),('activation',activation)]:
        require(obj['kind']=='immutable_contract_definition' and not {'status','implementation_status','protocol_status','missing_primitives'}&set(obj),'stable definition-only top-level '+name)
    require(all('implemented' not in item for item in execution['required_primitives']+activation['api_prerequisites']),'requirements omit mutable implementation flags')
    inspected={p:sha((ROOT/p).read_bytes()) for p in INSPECTED}
    for path,digest in PINS.items(): require(sha((ROOT/path).read_bytes())==digest,'frozen unchanged after checks '+path)
    report={'status':'bounded independent design consistency review passed; no actionable contradiction found',
            'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':['python3',str(Path(__file__).relative_to(ROOT))],
            'versions':{'python':platform.python_version(),'git':subprocess.check_output(['git','--version'],text=True).strip()},
            'head_at_review':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'frozen_proposed_inputs':PINS,'legacy_baseline_revision':BASELINE,'preserved_old_contracts':old,
            'inspected_implementation_sha256':inspected,'consistency_checks':checks,'check_count':len(checks),'closed_object_schemas':object_schemas,
            'manual_findings':[],'manual_review':'See README.md for semantic boundary analysis; static checks alone do not establish runtime correctness or authorize execution.',
            'limitations':['Read-only contract/design review, no new parser/verifier/factory/activation implementation or execution test',
                           'Additive bounded validation, typed error classification and zero-page same-config parity remain explicit prerequisites',
                           'No OTA/identity/build provenance/permission/health/recovery/data compatibility/publication/device/GA qualification',
                           'No production, old contract, frozen bridge review, device, trust, credential, commit or push mutation'],
            'script_sha256':sha(Path(__file__).read_bytes()),'readme_sha256':sha((HERE/'README.md').read_bytes())}
    target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'checks':len(checks),'inspected_implementation_files':len(inspected),'receipt_sha256':sha(target.read_bytes())}))

if __name__=='__main__': main()
