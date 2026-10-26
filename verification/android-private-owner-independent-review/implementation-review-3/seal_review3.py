#!/usr/bin/env python3
"""Seal rejected candidate4 review and verify all protected historical packets."""
from pathlib import Path
import hashlib
import json
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DOC=ROOT/'docs/android-private-owner-candidate4-review.md'
EXCLUDED={HERE/'manifest.json',HERE/'manifest.sha256',HERE/'seal-result.json'}
PROTECTED={
 'preaccess/manifest.json':'3d9100d342756d902152a6e786ec0e2a8ae1cd63d3ca79dde68f56ce3c7a390b',
 'leaf-review-1/manifest.json':'a553307572c2a7384a2a9129016a629fc8dd572f451da87c6c2714ce6be34ec7',
 'implementation-review-1/manifest.json':'e59aed63978371a1bb946b77b3e07ef0fce0fd9bd39a14d1c5c3f45aa2dd4742',
 'implementation-review-2/manifest.json':'f9f1b610a6a7bfb7918be64f27b19b95a44682348168407c5af079405ca289ab',
 'implementation-review-3/checkpoint-first10/manifest.json':'d12dd7f879ab399900d26f5fbd559254ac495d4c4f6fe94b6430ab0ca6945087',
 'implementation-review-3/jdi-helper/seal-manifest.json':'e417e1588c8c9ebd062d047ba88f3d2f180fbbcb9bbe101361b0dbb8c46df83a',
 'implementation-review-3/disposal-priority-finding/manifest.json':'397397444b68a6dccdbd6c5b52536e756b87467fc8d5e46771b5caf44a776a74',
}
def record(p):
    b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def read(p):return json.loads(p.read_text())
def dependencies():
    rows=[];external=set()
    for name,expected in PROTECTED.items():
        p=HERE.parent/name;assert record(p)['sha256']==expected,name
        m=read(p)
        for path,value in m['files'].items():assert record(ROOT/path)==value,(name,path)
        assert len(m['files'])==m['members'] and sum(x['bytes'] for x in m['files'].values())==m['bytes']
        rows.append({'path':str(p.relative_to(ROOT)),'manifest_sha256':expected,'members':m['members'],'bytes':m['bytes'],'all_members_verified':True})
        external.add(p)
        if name.startswith(('preaccess/','leaf-review-1/')):external.update(ROOT/path for path in m['files'])
    migration=read(HERE/'final-evidence/historical-migration.json')
    external.update(ROOT/r['path'] for r in migration['sources'])
    external.add(HERE.parent/'implementation-review-2/historical-vector-obligation-index.json')
    return rows,external
def main():
    mode=sys.argv[1:];assert mode in [['--seal'],['--check']]
    rows,external=dependencies()
    status={'scope':'Rejected candidate4 source/host review; no implementation/native/publicV2/GA acceptance',
        'candidate_manifest_sha256':'69fcd445119c0ea311c11cf97587d591d87ba1c5bd2d5b3c0a722116f66231c5',
        'candidate_disposition':'REJECTED_F09','direct_matrix_rows':1316,'required_matrix_rows':1323,'pending_measure_helper_rows':7,
        'actual_owner_core_observer_cases':129,'actual_owner_core_observer_assertions':1787,
        'separate_V1_positive_sites':5,'historical_full_dynamic_vector_expansion':'pending',
        'protected_packets':rows,'prior_failed_evidence_preserved':True,'product_sources_changed':False,
        'native_capture_UI_started':False,'all_recorded_owned_children_reaped':True,'all_exclusive_scratch_removed':True}
    if mode==['--seal']:
        assert not any(p.exists() for p in EXCLUDED)
        (HERE/'final-evidence/dependency-validation.json').write_text(json.dumps(status,indent=2)+'\n')
    else:assert read(HERE/'final-evidence/dependency-validation.json')==status
    paths={p for p in HERE.rglob('*') if p.is_file() and p not in EXCLUDED}|external|{DOC}
    assert not any(p.is_symlink() for p in paths)
    assert not any('scratch' in p.name for p in HERE.rglob('*') if p.is_dir())
    files={str(p.relative_to(ROOT)):record(p) for p in sorted(paths)}
    manifest={'schema':1,'scope':status['scope'],'command':['python3','-B',str(Path(__file__).relative_to(ROOT)),'--seal'],
        'python':sys.version,'source_revision':'Exact frozen candidate4 manifest; repository HEAD drift supplies no input authority',
        'excluded_metadata':['manifest.json','manifest.sha256','seal-result.json'],'members':len(files),'bytes':sum(v['bytes'] for v in files.values()),
        'external_owned_document':str(DOC.relative_to(ROOT)),'files':files}
    if mode==['--seal']:
        (HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        (HERE/'manifest.sha256').write_text(record(HERE/'manifest.json')['sha256']+'  manifest.json\n')
    assert read(HERE/'manifest.json')==manifest
    assert (HERE/'manifest.sha256').read_text()==record(HERE/'manifest.json')['sha256']+'  manifest.json\n'
    result={k:v for k,v in status.items() if k!='protected_packets'}
    result.update(manifest_sha256=record(HERE/'manifest.json')['sha256'],members=len(files),bytes=manifest['bytes'])
    if mode==['--seal']:(HERE/'seal-result.json').write_text(json.dumps(result,indent=2)+'\n')
    else:assert read(HERE/'seal-result.json')==result
    print(json.dumps(result))

if __name__=='__main__':main()
