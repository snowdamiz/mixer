#!/usr/bin/env python3
"""Validate the closed owned packet and seal retained evidence without touching inputs."""
from pathlib import Path
import datetime
import hashlib
import json
D=Path(__file__).resolve().parent

def identity(path):
    b=path.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}

def main():
    assert not (D/'seal.json').exists(),'closed packets are immutable'
    current=identity(D/'FiniteMembershipControls.java')
    assert current==identity(D/'run-3/FiniteMembershipControls.java')==json.loads((D/'run-3/receipt.json').read_bytes())['control']
    assert identity(D/'run_controls.py')==identity(D/'run-3/run_controls.py')
    validation=json.loads((D/'validation.json').read_bytes())
    assert all(validation[key] is True for key in ['original_six_ids_preserved','original_categories_and_semantic_case_lists_preserved','all_outcomes_equal_independent_literal_expected','all_counts_unchanged','all_snapshot_digests_unchanged','all_zero_native_effects','all_enclosing_execution_joins_null'])
    assert validation['actual_result_row_count']==validation['unique_control_cases']==142
    assert json.loads((D/'run-1/failure.json').read_bytes())['status']=='failed-authoring-attempt-no-pass-credit'
    for name in ('run-1','run-2','run-3'):
        cleanup=json.loads((D/name/'cleanup.json').read_bytes());assert cleanup['all_started_children_reaped'] and cleanup['owned_scratch_removed']
        assert not (D/name/'scratch').exists()
        commands=json.loads((D/name/'commands.json').read_bytes())
        for command in commands:
            assert command['reaped'] and not command['timeout']
            for stream in ('stdout','stderr'):
                recorded=command[stream];assert identity(D/name/recorded['path'])=={k:recorded[k] for k in ('bytes','sha256')}
    manifest=json.loads((D/'manifest.json').read_bytes())
    assert manifest['invocations']==142 and manifest['actual_counts']['after_original_edit']==[0,0,0]
    assert json.loads((D/'run-3/compile-identity.json').read_bytes())['all_209_exact_matches']
    members=[]
    for path in sorted(D.rglob('*')):
        if path.is_file():members.append({'path':path.relative_to(D).as_posix(),**identity(path)})
    seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'closed-six-exact-finite-host-controls-root-review-pending','selected_run':'run-3','source_revision_context':'6450104dc3b02d0f4d4e572c6b05ad7fdc6657b2',
          'source_context':manifest['source_context'],'member_count':len(members),'member_bytes':sum(m['bytes'] for m in members),'members':members,
          'scope':'Only owned ordinary finite host controls of exact six original NativeRenderer membership/capture/provenance/identity/cohort/funding methods; original IDs/categories/cases retained and enclosing obligations pending',
          'complete_matrix_policy_canonical_native_OTA_GA_accepted':False,'physical_native_cleanup_credit':False}
    (D/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
    print(json.dumps({'seal':identity(D/'seal.json'),'member_count':len(members),'member_bytes':seal['member_bytes']}))
if __name__=='__main__':main()
