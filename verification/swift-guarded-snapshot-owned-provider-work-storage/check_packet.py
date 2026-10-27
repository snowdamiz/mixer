#!/usr/bin/env python3
"""Read-only packet/source custody and deterministic reconstruction check."""
from pathlib import Path
import hashlib, json, sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def canon(obj):return json.dumps(obj,sort_keys=True,separators=(',',':')).encode()
def members():
    out=[]
    for path in sorted(HERE.rglob('*')):
        if path.is_dir():continue
        assert not path.is_symlink(),'no symlink members'
        name=path.relative_to(HERE).as_posix()
        if name=='seal.json':continue
        assert '__pycache__' not in name and not name.startswith('owned-work/'),'no transient members'
        data=path.read_bytes();out.append({'path':name,'bytes':len(data),'sha256':sha(data)})
    return out
def validate(*,sealed):
    if sealed:
        seal=json.loads((HERE/'seal.json').read_bytes());actual=members()
        assert seal['members']==actual and seal['member_count']==len(actual) and seal['total_bytes']==sum(r['bytes'] for r in actual)
        assert seal['member_table_sha256']==sha(canon(actual))
    for member in json.loads((HERE/'input-custody.json').read_bytes())['members']:
        data=(ROOT/member['path']).read_bytes();assert (len(data),sha(data))==(member['bytes'],member['sha256']),member['path']
    latest=json.loads((HERE/'latest-checks.json').read_bytes());receipt_data=(HERE/latest['path']).read_bytes();assert sha(receipt_data)==latest['sha256']
    receipt=json.loads(receipt_data);assert latest['success'] and receipt['success'] and receipt['scripts_unchanged'] and len(receipt['commands'])==3 and all(c['exit_code']==0 for c in receipt['commands'])
    for name,binding in receipt['scripts'].items():
        data=(HERE/name).read_bytes();assert (len(data),sha(data))==(binding['bytes'],binding['sha256'])
    import derive
    derived=derive.derive()
    for name,value in derived.items():assert json.loads((HERE/name).read_bytes())==value,'stale:'+name
    candidate=derived['candidate.json'];assert candidate['all_six_upstream_requirements']=='Pending' and candidate['all_three_selectors']=='Pending'
    assert not any(candidate[name] for name in ('new_callee_contracts_selected','actual_acquisition_or_authenticated_owner','L_str_selected','whole_quote_or_root_funding_or_operational_grant','native_runtime_FieldLog_OTA_GA'))
    assert candidate['fresh_independent_review_required']
    return {'success':True,'scope':'immutable packet, exact frozen/current inputs, completed pure-host commands, deterministic derivation; no new compiler or runtime','roles':candidate['roles'],'operations':candidate['written_operations'],'typed_inline_slots':candidate['typed_inline_slots'],'provider_inline_addition':candidate['provider_inline_addition'],'source_work':candidate['provider_source_work']}
if __name__=='__main__':print(json.dumps(validate(sealed=True),sort_keys=True))
