#!/usr/bin/env python3
"""Seal exact source, borrowed dependencies, executables and observed receipts."""
import datetime,hashlib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def need(ok,message):
    if not ok:raise RuntimeError(message)
def main():
    names=['2026-10-23-candidate-1','2026-10-23-derived-final','2026-10-23-supplemental-final']
    receipts={n:json.loads((HERE/n/'receipt.json').read_text()) for n in names}
    primary=receipts[names[0]];source=Path(primary['export'])
    source_checks=0;log_checks=0;artifact_checks=0;dependency_checks=0
    for name,r in receipts.items():
        need(r['status'].startswith(('scoped tests passed','scoped consumer/opacity/cross checks passed')),'successful '+name)
        for item,digest in r['source_files'].items():
            path=Path(r.get('export',str(source)))/item;need(sha(path)==digest,'export '+item);source_checks+=1
        for command in r['commands']:
            need(sha(HERE/name/command['log'])==command['log_sha256'],'log '+name+'/'+command['log']);log_checks+=1
            need(command['exit_code']==command.get('expected_exit',0),'observed exit '+command['name'])
            if 'expected_tests' in command:need(command['observed_test_counts'][-1]==command['expected_tests'],'test count')
        for mode,value in r.get('artifacts',{}).items():
            if 'path' in value:need(sha(Path(value['path']))==value['sha256'],'artifact '+mode);artifact_checks+=1
            else:
                for kind,item in value.items():
                    if isinstance(item,dict) and 'path' in item:need(sha(Path(item['path']))==item['sha256'],'artifact '+kind);artifact_checks+=1
                    elif isinstance(item,str):need(sha(HERE/'.build'/name/mode/kind)==item,'cross artifact '+kind);artifact_checks+=1
        for path,digest in r.get('dependency_inputs',{}).items():need(sha(Path(path))==digest,'cross dependency '+path);dependency_checks+=1
    for name in primary['own_files']:need(sha(ROOT/name)==primary['source_files'][name],'live owned source '+name)
    revision=primary['baseline_revision']
    for name,digest in primary['source_files'].items():
        if name in primary['own_files']:continue
        raw=subprocess.check_output(['git','show',revision+':'+name],cwd=ROOT)
        need(hashlib.sha256(raw).hexdigest()==digest,'exact committed baseline '+name)
    depfile=Path(primary['dependency_receipt']['path']);need(sha(depfile)==primary['dependency_receipt']['sha256'],'retained receipt')
    dependency=json.loads(depfile.read_text())
    for mode,retained in dependency['retained_products'].items():
        for path,digest in retained['files'].items():need(sha(Path(retained['directory'])/path)==digest,'retained '+mode+'/'+path);dependency_checks+=1
    for path,digest in primary['native_files'].items():need(sha(Path(primary['native_directory'])/path)==digest,'native '+path);dependency_checks+=1
    derived=receipts[names[1]]
    for name,digest in derived['original_source_files'].items():
        if name in primary['source_files']:need(digest==primary['source_files'][name],'same original derived source '+name)
    need(sha(HERE/names[1]/'test-only.patch')==derived['test_only_patch_sha256'],'derived patch')
    supplemental=receipts[names[2]]
    for path,digest in supplemental['supplemental_files'].items():need(sha(HERE/path)==digest,'final supplemental tool '+path)
    files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and not any(part in ['.build','__pycache__'] for part in p.relative_to(HERE).parts) and p.name not in ['final-receipt.json','file-manifest.sha256']}
    manifest=''.join(d+'  '+n+'\n' for n,d in sorted(files.items()));(HERE/'file-manifest.sha256').write_text(manifest)
    record={'status':'owner scoped qualification and exact-input audit passed; independent review pending','completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline_revision':revision,'source_manifest_sha256':primary['source_manifest_sha256'],'source_count':len(primary['source_files']),'new_production_files':{n:primary['source_files'][n] for n in primary['own_files'] if 'Sources/MixerCapabilityActivation/CapabilityColdStart' in n},'new_tests':{'file':'capability-activation/Tests/MixerCapabilityActivationTests/CapabilityColdStartRuntimeTests.swift','sha256':primary['source_files']['capability-activation/Tests/MixerCapabilityActivationTests/CapabilityColdStartRuntimeTests.swift'],'functions':8},'receipts':{n:sha(HERE/n/'receipt.json') for n in names},'unmodified_tests_per_mode':dict(debug=95,release=95,tsan=95),'derived_tests_per_mode':dict(debug=13,release=13,tsan=13),'derived_only_new_functions':5,'ordinary_public_consumer_runs':2,'ordinary_import_opacity_rejections':6,'official_cross_module_and_object':['arm64-apple-ios17.0','aarch64-unknown-linux-android28'],'binding_counts':dict(source=source_checks,logs=log_checks,artifacts=artifact_checks,borrowed_dependencies=dependency_checks),'evidence_files':len(files),'file_manifest_sha256':hashlib.sha256(manifest.encode()).hexdigest(),'native_revision':'b25e3b7de2391a80d12e7fd75e60903495bec120','native_archive_sha256':primary['native_files']['lib/libmixer_vm_capability_experimental.a'],'compiled_one_native_registry_per_mode':True,'frozen_concrete_owner_receipt':{'path':'verification/capability-concrete-attempt/final-receipt.json','sha256':sha(ROOT/'verification/capability-concrete-attempt/final-receipt.json')},'independent_review_qualified':False,'committed':False,'pushed':False,'limitations':primary['limitations']+['Derived export driver is absent from production; public event delivery/full guest UI remain separate','Adapter-retirement barrier pauses publication after real bridge/KV close; not a hung native-I/O reproduction','Source checks and test evidence do not themselves authorize release/selection outside the private coordinator','Initial failed fixture/tool experiments preserved in file manifest; no production source fix between preliminary link and final candidate']}
    (HERE/'final-receipt.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'receipt_sha256':sha(HERE/'final-receipt.json'),'counts':record['binding_counts'],'evidence_files':len(files)},indent=2))
if __name__=='__main__':main()
