#!/usr/bin/env python3
"""Freeze this independent baseline review without modifying earlier sealed members."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ACTUAL=HERE/'actual-review'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(directory,name,expected):
    path=directory/name;data=path.read_bytes();assert sha(data)==expected
    seal=json.loads(data);total=0
    for row in seal['members']:
        p=directory/row['path'];assert not p.is_symlink()
        b=p.read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256'],str(p)
        total+=len(b)
    return {'path':str(path.relative_to(ROOT)),'sha256':expected,
            'members':len(seal['members']),'bytes':total}


def main():
    verified=[
        verify(HERE,'preaccess-seal.json','60305ff555f5a0c26f87b2f57ca9ffa5e2a771a0f67a0f7e9f74787d0d65681f'),
        verify(HERE/'replacement-preaccess','seal.json','89fef50e796ef1e1952301be04554e09404f2d00a3d6926a73dacfed0554728a'),
        verify(ACTUAL/'findings-1','seal.json','f6d6c1be1278a8e40d4bedd8bfc55d64d32ce002b53e745fa099b0322268fbf2'),
        verify(ROOT/'verification/android-editor-implementation','seal.json','99ee53d6cf73cc062d5f39f7caa743dfed68f0f22522788adabe83159cacc9cd'),
    ]
    admission=json.loads((ACTUAL/'admission-receipt.json').read_text())
    for row in admission['copied_current_members']:
        b=(ACTUAL/'frozen'/row['path']).read_bytes()
        assert len(b)==row['bytes'] and sha(b)==row['sha256']
    ownership=json.loads((ACTUAL/'source-ownership-review.json').read_text())
    product=[row for row in ownership['rows'] if row['path'].startswith('source/')]
    changed=[row['path'] for row in product if not row['unchanged']]
    assert sorted(changed)==['source/NativeAppearanceViewsV2.java','source/NativeCoordinatorV2.java','source/NativeRenderer.java']
    host=json.loads((ACTUAL/'frozen/runs/host-1/receipt.json').read_text())
    cross=json.loads((ACTUAL/'frozen/runs/cross-1/receipt.json').read_text())
    assert host['status']=='passed-host-only' and cross['status']=='passed-cross-only'
    assert host['cleanup']['children_reaped'] and host['cleanup']['scratch_removed']
    assert cross['cleanup']['children_reaped'] and cross['cleanup']['scratch_removed']
    commands=json.loads((ACTUAL/'independent-controls-1/commands.json').read_text())
    corrected=json.loads((ACTUAL/'metadata-controls-2/commands.json').read_text())
    assert next(row for row in commands if row['label']=='compiled-adapter-shape')['exit']==0
    for row in commands:
        if row['label'] in ('mutation-getter-reentry','close-roster-reentry','close-target-reentry'):
            assert row['exit']==1
    for row in corrected:
        assert row['exit']==(0 if row['label']=='compile' else 1)
    official=json.loads((HERE/'inputs/verification/android-editor-api-boundary-proposal/official-inputs.json').read_text())
    tools=[]
    for row in official['installed']:
        if row['path'].endswith(('/android.jar','/d8','/d8.jar','/bin/java','/bin/javac','/bin/javap')):
            b=Path(row['path']).read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256']
            tools.append(row)
    amendment=ACTUAL/'root-replacement-amendment-at-review.md'
    assert sha(amendment.read_bytes())=='b386f832479884f2487df114fb080f14ebac99c747208bffd0428477c32d844b'
    receipt={
        'schema':1,'at':datetime.datetime.now(datetime.UTC).isoformat(),'argv':sys.argv,'python':sys.version,
        'script_sha256':sha(Path(__file__).read_bytes()),
        'scope':'Independent review of exact frozen Android editor baseline only',
        'decision':'changes_required_no_integration_or_native_acceptance',
        'verified_immutable_packets':verified,'copied_current_members_reverified':len(admission['copied_current_members']),
        'product_baseline_files':len(product),'changed_existing_product_files':changed,
        'new_product_source':'source/NativeEditorConnectionV2.java',
        'host_replay':{'groups':38,'assertions':505,'status':'passed','includes_expected_witnesses_of_two_real_compatibility_failures':True},
        'cross_replay':{'status':'passed','scope':'SDK37 javac and unsigned D8 min-api28 only'},
        'independent_compiled_adapter_descriptors':38,
        'independent_findings':5,'getter_tuple_reflective_host_invariant_findings':3,
        'corrected_supported_SelectGesture_control':'failed_as_documented',
        'failed_creator_payload_control':'failed_as_documented',
        'original_base_gesture_token_control':'preserved_but_superseded_due_permissive_host_leaf',
        'known_ACTION_SET_TEXT_product_failures':2,
        'pinned_external_tools_reverified':tools,
        'prospective_root_amendments':{
            'initial_replacement_sha256':'da69185315f2952248596ddd4566a1041bacff73003feff7d38ba48aa0707f92',
            'reviewed_root_amendment_snapshot_sha256':'b386f832479884f2487df114fb080f14ebac99c747208bffd0428477c32d844b',
            'replacement_source_preparation_consistent':True,
            'exact_EditorInfo_class_admission':'explicit later root direction; derivative guard review pending',
            'active_derivative_reads_or_executions':0},
        'cleanup':{'all_recorded_finite_children_exited_and_reaped':True,
                   'replay_scratch_removed':True,'compiled_evidence_retained':True,
                   'native_capture_ui_device_or_process_inventory':False},
        'git_canonical_root_metadata_credentials_customer_or_production_mutation':False,
        'pending':['root-released derivative actual-source review and positive replacement/class-guard controls',
                   'Android/ART/IME/lifecycle/EditorInfo runtime when resumed','physical final matrix','TalkBack',
                   'API28-35 admission','immutable separate-repository FieldLog','store/signing/OTA/operations/accountable GA'],
    }
    (ACTUAL/'audit-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    rows=[]
    sealpath=HERE/'audit-seal.json'
    for path in sorted(HERE.rglob('*')):
        if not path.is_file() or path==sealpath:continue
        assert not path.is_symlink();b=path.read_bytes()
        rows.append({'path':path.relative_to(HERE).as_posix(),'bytes':len(b),'sha256':sha(b)})
    seal={'schema':1,'at':datetime.datetime.now(datetime.UTC).isoformat(),
          'scope':'Independent exact baseline source review, complete-source host/SDK replay, sealed replacement preparation and five findings; no derivative/native/integration acceptance',
          'members':rows,'decision':receipt['decision'],'native_or_GA_accepted':False}
    sealpath.write_text(json.dumps(seal,indent=2)+'\n')
    print(json.dumps({'members':len(rows),'bytes':sum(row['bytes'] for row in rows),
                      'seal_sha256':sha(sealpath.read_bytes()),'decision':receipt['decision'],
                      'findings':5,'known_compatibility_failures':2}))


if __name__=='__main__':main()
