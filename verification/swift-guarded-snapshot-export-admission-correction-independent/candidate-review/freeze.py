"""Freeze exact independent findings after validating fresh command evidence."""
import datetime
import hashlib
import json
import pathlib
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
assert not (HERE/'seal.json').exists()
receipt=json.loads((HERE/'execution-receipt.json').read_text())
assert len(receipt['commands'])==13
for command in receipt['commands']:
    folder=HERE/'commands'/command['name']
    assert sha(folder/'receipt.json')==command['receipt_sha256']
    result=json.loads((folder/'receipt.json').read_text())
    assert result['expectation_met'] and result['exit_code']==result['expected_exit_code']
    for stream in ['stdout','stderr']:assert sha(folder/stream)==result[stream+'_sha256']
assert len(json.loads((HERE/'fresh-layout-comparison.json').read_text())['configurations'])==4
assert json.loads((HERE/'fresh-layout-comparison.json').read_text())['all_eight_constants_match']
assert len(json.loads((HERE/'criteria-disposition.json').read_text())['criteria'])==10
findings=json.loads((HERE/'findings.json').read_text())
assert findings['new_blocking_findings']==[]
assert not findings['complete_floor_or_operational_grant_accepted']
cleanup=json.loads((HERE/'cleanup.json').read_text())
assert cleanup['scratch_removed'] and cleanup['all_subprocesses_completed']
assert not cleanup['native_ui_capture_process_inventory_started']
custody=json.loads((HERE/'input-custody-after.json').read_text())
verified=[]
for item in custody['inputs']:
    base=ROOT/item['path']
    if 'seal_sha256' in item:
        assert sha(base/'seal.json')==item['seal_sha256']
        manifest=json.loads((base/'seal.json').read_text())
    else:
        manifest_path=base.parents[1]/'source-manifest.json'
        assert sha(manifest_path)==item['manifest_sha256']
        manifest=json.loads(manifest_path.read_text())
    for member in manifest['members']:
        path=base/member['path']
        assert not path.is_symlink() and path.stat().st_size==member['bytes'] and sha(path)==member['sha256']
    assert len(manifest['members'])==item['members_verified']
    verified.append({'path':item['path'],'members':len(manifest['members']),'bytes':sum(m['bytes'] for m in manifest['members'])})
dump(HERE/'final-verification.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'inputs_reverified':verified,'fresh_commands_verified':13,'complete_floor_or_grant':False,
    'pending_scope':'Healthy selected cleanup, authentic shared admission/scope/finalizer and actual wrapper/writer remain pending',
    'scratch_removed':True,'candidate_preaccess_original_accepted_unchanged':True})
members=[]
for path in sorted(HERE.rglob('*')):
    assert not path.is_symlink()
    if path.is_file() and path.name!='seal.json':members.append({'path':str(path.relative_to(HERE)),'bytes':path.stat().st_size,'sha256':sha(path)})
tree=hashlib.sha256(''.join(f"{m['path']}\0{m['bytes']}\0{m['sha256']}\n" for m in members).encode()).hexdigest()
dump(HERE/'seal.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'member_count':len(members),'bytes':sum(m['bytes'] for m in members),'members':members,'tree_sha256':tree,
    'scope':'Independent exact correction63 F1 conservative branch and F2 actual-type lifetime review; no integrated admission, healthy selected cleanup, floor or grant acceptance'})
print(json.dumps({'seal_sha256':sha(HERE/'seal.json'),'members':len(members),'bytes':sum(m['bytes'] for m in members),'tree_sha256':tree},indent=2))
