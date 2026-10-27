#!/usr/bin/env python3
"""Seal only this owned candidate after exact data replay; never run compiler."""
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
import derive
HERE=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def snapshot():
    assert not (HERE/'owned-work').exists()
    assert not list(HERE.rglob('__pycache__'))
    for name,value in derive.derive().items():assert json.loads((HERE/name).read_bytes())==value,name
    latest=json.loads((HERE/'latest-checks.json').read_bytes());receipt=HERE/latest['path']
    assert sha(receipt.read_bytes())==latest['sha256'] and latest['passed']
    checks=json.loads(receipt.read_bytes());assert checks['passed'] and all(c['exit_code']==0 for c in checks['commands'])
    for r in checks['source_snapshots']:
        b=(HERE/r['path']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256']
    members=[]
    for p in sorted(HERE.rglob('*')):
        assert not p.is_symlink(),'packet contains symlink'
        if p.is_file() and p!=HERE/'seal.json':
            b=p.read_bytes();members.append({'path':p.relative_to(HERE).as_posix(),'bytes':len(b),'sha256':sha(b)})
    return {'schema':1,'members':members,'member_count':len(members),'member_bytes':sum(r['bytes'] for r in members),'manifest_sha256':sha(derive.canon(members)),
        'candidate_source_tree_sha256':derive.NEW_TREE,'old_source_tree_sha256':derive.OLD_TREE,'source_members':146,'new_outer_work':2706170,'new_outer_roles':130,'new_written_operations':386,
        'new_outer_inline_bytes':56414,'P0_fixed_inline_bytes_before_actual_external_inputs':292037,'Python_test_methods':32,'exact_replay_passed':True,
        'compiler_queries':1,'query_observations':2,'query_expected_diagnostic_exit':1,'query_child_group_and_scratch_cleanup_confirmed':True,
        'actual_identity_or_path_inputs_selected':False,'all_three_selectors_pending':True,'source_binding_candidate_only':True,'independent_review':False,
        'root_policy_or_operational_grant':False,'complete_compiled_or_healthy_runtime_qualification':False,'native_FieldLog_OTA_GA':False}
def main():
    a=snapshot();b=(json.dumps(a,sort_keys=True,indent=2)+'\n').encode();p=HERE/'seal.json'
    if sys.argv[1:]==['--check-only']:assert p.read_bytes()==b,'frozen packet changed'
    else:assert not p.exists(),'refuse to replace seal';p.write_bytes(b)
    print(json.dumps({'passed':True,'seal_sha256':sha(b),'members':a['member_count'],'member_bytes':a['member_bytes'],'compiler_or_runtime_started':False}))
if __name__=='__main__':main()
