#!/usr/bin/env python3
"""Seal scoped v3 evidence without rebuilding or changing production inputs."""
from pathlib import Path
import datetime
import hashlib
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
HOST='253bf3912fe52262b5e837f2c3a51ea656b13eafe32dd59f991ccf53748484ff'
CROSS='08a62b5a808adb31befefea9e608833d7900cfaef963d7de6ecd7795d871777d'

def sha(data):return hashlib.sha256(data).hexdigest()
def require(value,message):
    if not value:raise RuntimeError(message)

def main():
    require(not(HERE/'final-receipt.json').exists(),'preserve prior final receipt')
    paths=[HERE/'2026-10-23-candidate-1/receipt.json',HERE/'2026-10-23-candidate-1-cross/receipt.json']
    receipts=[]
    for path,pin in zip(paths,[HOST,CROSS]):
        raw=path.read_bytes();require(sha(raw)==pin,'exact command receipt');receipts.append(json.loads(raw))
    host,cross=receipts;require(host['source_manifest_sha256']==cross['source_manifest_sha256'],'one source freeze')
    require(host['status'].startswith('scoped checks passed') and cross['status']=='official SDK module/object compile checks passed','green command matrices')
    source=Path(host['immutable_source_export'])
    for relative,digest in host['source_files'].items():
        require(sha((ROOT/relative).read_bytes())==digest,'current source unchanged '+relative)
        require(sha((source/relative).read_bytes())==digest,'export source unchanged '+relative)
    for receipt in receipts:
        for command in receipt['commands']:
            require(command['exit_code']==command.get('expected_exit',0),'command exit')
            require(sha((ROOT/command['log']).read_bytes())==command['sha256'],'raw command log')
    for target,artifacts in cross['artifacts'].items():
        for artifact in artifacts:require(sha(Path(artifact['path']).read_bytes())==artifact['sha256'],'actual '+target+' artifact')
    require(sha(Path(host['public_client']['path']).read_bytes())==host['public_client']['sha256'],'actual public consumer')
    for name,digest in host['shared_fixture_sha256'].items():
        require(sha((ROOT/'services/protocol/testdata'/name).read_bytes())==digest,'shared fixture')
        require(sha((ROOT/'updates/Tests/MixerUpdatesTests/Fixtures'/name).read_bytes())==digest,'copied fixture')
    extra={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in [HERE/'README.md',HERE/'cross-compile.py',Path(__file__).resolve()]}
    source_map=dict(host['source_files'],**extra)
    manifest=''.join(d+'  '+p+'\n' for p,d in sorted(source_map.items())).encode()
    (HERE/'qualification-source.sha256').write_bytes(manifest)
    excluded={'.build','.swiftpm','__pycache__'}
    evidence=sorted(p for p in HERE.rglob('*') if p.is_file() and not excluded.intersection(p.relative_to(HERE).parts) and p.name not in ['evidence-manifest.sha256','final-receipt.json'])
    inventory=''.join(sha(p.read_bytes())+'  '+str(p.relative_to(HERE))+'\n' for p in evidence).encode()
    (HERE/'evidence-manifest.sha256').write_bytes(inventory)
    result={'status':'scoped Swift release-v3 verifier/proof qualification passed; integration remains root-owned',
            'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_manifest_sha256':host['source_manifest_sha256'],
            'host_receipt_sha256':HOST,'official_sdk_receipt_sha256':CROSS,'qualification_source_files':len(source_map),
            'qualification_source_manifest_sha256':sha(manifest),'evidence_files':len(evidence),'evidence_manifest_sha256':sha(inventory),
            'source_files':source_map,'preserved_old_source_test_files':host['preserved_old_source_test_files'],
            'legacy_verifier_sha256':host['legacy_verifier_sha256'],'shared_fixture_sha256':host['shared_fixture_sha256'],
            'actual_public_consumer':host['public_client'],'cross_compile_artifacts':cross['artifacts'],
            'counts':{'all_debug':55,'all_release':55,'new_v3_tsan':15,'public_client_runs':1,'positive_external_typechecks':1,'intentional_negative_compiles':8,
                      'shared_manifest_cases':154,'shared_assignment_cases':36,'shared_origin_cases':39,'shared_namespace_cases':14},
            'independent_review':'Separate root-owned verification/release-v3-root-review/; not included as owner-generated proof',
            'limitations':host['limitations']+[cross['scope'],'No new durable updater, factory, coordinator, hosted route or retained-health exception'],
            'production_ownership':'Only approved additive v3 verifier/tests, updates README, API design and this evidence lane; old Verifier.swift byte-exact',
            'commits_pushes_devices_trust_or_credentials_changed':False}
    (HERE/'final-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'final_receipt_sha256':sha((HERE/'final-receipt.json').read_bytes()),'qualification_source_manifest_sha256':sha(manifest),'evidence_manifest_sha256':sha(inventory)}))

if __name__=='__main__':main()
