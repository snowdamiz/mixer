"""Root custody release of the finite IR01 correction; no semantic acceptance."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
PACKET=ROOT/'verification/swift-guarded-snapshot-actual-owner-rust-retirement-correction'
DEST=OUT/'guarded-snapshot-actual-owner-Rust-retirement-correction-release.json'
def row(path):
    assert path.is_file() and not path.is_symlink()
    data=path.read_bytes()
    return {'path':str(path.relative_to(ROOT)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
assert not DEST.exists(), 'One-shot; do not replay'
assert row(PACKET/'seal.json')['sha256']=='46d811b1264770604106b061386e6eba01ea07e55590240eff722c36af4bcaa0'
seal=json.loads((PACKET/'seal.json').read_bytes())
assert len(seal['members'])==seal['member_count']==1487
assert sum(item['bytes'] for item in seal['members'])==seal['member_bytes']==154102793
names={'seal.json'}
for item in seal['members']:
    name=PurePosixPath(item['path'])
    assert not name.is_absolute() and '..' not in name.parts and str(name) not in names
    actual=row(PACKET/name)
    assert actual['bytes']==item['bytes'] and actual['sha256']==item['sha256']
    names.add(str(name))
assert {str(path.relative_to(PACKET)) for path in PACKET.rglob('*') if path.is_file()}==names
summary=json.loads((PACKET/'command-summary.json').read_bytes())
assert summary['compiler_invocations']==9 and summary['filtered_host_runs']==2 and summary['version_queries']==1
assert summary['methods_per_mode']==25 and summary['all_exact_owned_groups_absent'] and summary['all_owned_children_reaped']
assert all(item['source_unchanged'] and item['input_unchanged'] and item['tool_unchanged'] and item['exact_owned_group_absent'] for item in summary['commands'])
for item in summary['commands']:
    if item['kind']=='compiler-negative':
        assert item['exit']==1 and item['intended_diagnostics_found'] and not item['negative_rmeta_created']
    else: assert item['exit']==0
assert not (PACKET/'build').exists()
value={'schema':1,'at':datetime.now(timezone.utc).isoformat(),
    'command':[sys.executable,'-B',str(Path(__file__).relative_to(ROOT))],
    'status':'frozen-IR01-correction-released-for-independent-review-only','accepted':False,
    'seal':row(PACKET/'seal.json'),'members_verified':1487,'member_bytes':154102793,
    'source146_tree':seal['source146_tree'],'source_delta':row(PACKET/'source-delta.patch'),
    'producer_result':row(PACKET/'result.json'),'command_summary':row(PACKET/'command-summary.json'),
    'producer_compiler_invocations':9,'producer_host_runs':2,'producer_methods_per_mode':25,
    'root_review':'Sticky obligation is initialized only at construction, set before expected/attempt publication and checked before any retirement cleanup. No reset/discharge route exists. Original witness now takes Retained; matched/refused/extracted/forgotten carriers remain charged.',
    'independent_next':'Review exact source/MIR and compiler claims; fresh unchanged producer methods and independent host controls, including frozen binary/provenance/read vectors. Compiler lane waits for console independent review.',
    'permanent_retention_not_useful_joint_retirement':True,'new_layouts_and_prices_unqualified':True,
    'native_funding_OTA_or_GA_accepted':False}
with DEST.open('x') as stream:
    json.dump(value,stream,indent=2);stream.write('\n')
w=json.loads((ROOT/'work-graph.json').read_bytes());g=json.loads((ROOT/'gates/ga.json').read_bytes())
c=w['packages'][7]['fixtureCacheStateContractCandidate'];assert c==g['gates'][1]['fixtureCacheStateContractCandidate']
b=c['scalar_cursor_host_acceptance']['real_profile_adapter_preparation']['next_header_preparation']['retained_profile_composition_preparation']['real_binding_preparation']['real_profile_loader_binding']['next_adoption_lane']['guarded_snapshot_export_contract_review']['composition_source_preparation']['bootstrap_host_boundary']
correction=b['actual_owner_Rust_selection']['correction']
correction.update({'status':'producer-frozen-released-for-independent-review','root_release':row(DEST),
    'source146_tree':seal['source146_tree'],'producer_methods_per_mode':25,'producer_compiler_invocations':9,
    'producer_host_runs':2,'implementation_accepted':False})
correction['queued_command_budget']['lane_released']=True
correction['queued_command_budget']['execution']='completed-within-selected-budget; lane released after terminal cleanup'
g['gates'][1]['fixtureCacheStateContractCandidate']=copy.deepcopy(c)
for name,data in [('work-graph.json',w),('gates/ga.json',g)]: (ROOT/name).write_text(json.dumps(data,indent=2)+'\n')
for name in ['PLAN.md','STATUS.md']:
    path=ROOT/name;text=path.read_text()
    old='source work is active and validation remains pending.'
    new='the correction is frozen after 25 passing host methods in each mode and six intended negative compiler probes within the selected nine compiler/two host commands. Root verifies all 1,487 frozen members and releases independent review; implementation acceptance remains pending.'
    assert text.count(old)==1
    path.write_text(text.replace(old,new))
subprocess.run(['git','diff','--check','--','PLAN.md','STATUS.md','work-graph.json','gates/ga.json'],cwd=ROOT,timeout=10,check=True)
print(json.dumps({'correction_members_verified':1487,'producer_methods_per_mode':25,'released_for_independent_review':True,'accepted':False}))
