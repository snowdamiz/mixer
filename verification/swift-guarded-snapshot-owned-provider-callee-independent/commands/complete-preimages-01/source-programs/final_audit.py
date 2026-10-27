import json
from pathlib import Path
import hashlib

OWN=Path(__file__).resolve().parent

def main():
    receipts=[]
    for path in sorted((OWN/'commands').glob('*/receipt.json')):
        r=json.loads(path.read_text())
        receipts.append({'command':path.parent.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                         'child_spawned':r['child_spawned'],'exit_code':r.get('exit_code'),
                         'postflight_ok':r.get('postflight_ok'),
                         'owned_process_group_absent_after_reap':r.get('owned_process_group_absent_after_reap')})
        for s in r['source_files']:
            saved=path.parent/'source-programs'/Path(s['path']).name
            assert saved.is_file(), (path,s['path'])
            assert (saved.stat().st_size,hashlib.sha256(saved.read_bytes()).hexdigest())==(s['bytes'],s['sha256'])
        if r['child_spawned']:
            assert r['exit_code']==0 and r['postflight_ok'] and r['same_custody_before_after'] and r['owned_process_group_absent_after_reap']
        else:
            assert path.parent.name=='source-trace-01' and not r['preflight_ok']
    assert len(receipts)>=6
    report=json.loads((OWN/'review.json').read_text())
    contract=json.loads((OWN/'correction-contract.json').read_text())
    assert len(contract['findings'])==3
    assert report['fresh_checks']['component_equalities']==5344
    assert report['retained_compiler_correspondence']['functions_checked']==23
    assert report['status']=='focused-source-closure-correction-required'
    result={'schema':1,'status':'independent-focused-correction-packet-ready-to-freeze','receipt_history':receipts,
            'review_sha256':hashlib.sha256((OWN/'review.json').read_bytes()).hexdigest(),
            'correction_contract_sha256':hashlib.sha256((OWN/'correction-contract.json').read_bytes()).hexdigest(),
            'producer_and_review_preflight_failures_preserved':True,
            'all_previous_successful_children_reaped_and_groups_absent':True,
            'new_compiler_product_native_UI_capture_or_global_inventory':False,
            'price_root_funding_OTA_or_GA_acceptance':False}
    (OWN/'final-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'prior_commands':len(receipts),'all_prior_receipt_source_snapshots_match':True}))

if __name__=='__main__':main()
