#!/usr/bin/env python3
"""Seal a terminal selected roster; never runs a compiler or test."""
from pathlib import Path
import datetime,hashlib,json,sys
HERE=Path(__file__).resolve().parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def digest(value):return sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())
def row(path,base=HERE):
    raw=path.read_bytes();return {'path':str(path.relative_to(base)),'bytes':len(raw),'sha256':sha(raw)}
def write(name,value):(HERE/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
assert not (HERE/'seal.json').exists(),'No frozen packet edits.'
roster=json.loads((HERE/'proposed-command-roster.json').read_text());summary=[]
for command in roster['commands']:
    receipt=json.loads((HERE/'commands'/command['id']/'receipt.json').read_text())
    assert receipt['id']==command['id'] and receipt['kind']==command['kind']
    assert receipt['reason'] is None and receipt['exact_owned_group_absent'] and receipt['child_reaped']
    assert receipt['source_unchanged'] and receipt['input_unchanged'] and receipt['tool_unchanged'] and receipt['output_within_caps'] and receipt['seconds']<=55
    assert receipt['exit']!=0 if receipt['kind']=='compiler-negative' else receipt['exit']==0
    summary.append(receipt)
assert sum(r['kind'] in ('compiler','compiler-negative') for r in summary)==9
assert sum(r['kind']=='host' for r in summary)==2
assert sum(r['kind']=='version' for r in summary)==1
for mode in ['debug','opt2']:
    output=(HERE/'commands'/('run-'+mode)/'stdout').read_text()
    assert 'running 25 tests' in output and '25 passed; 0 failed' in output
    assert 'independent_result_live_acquisition_retirement_v1 ... ok' in output
    assert 'h14_live_matched_carrier_cannot_coexist_with_complete_acquisition ... ok' in output
    assert 'h22_positive_move_and_borrowed_return_controls ... ok' in output
source=json.loads((HERE/'source-manifest.json').read_text())
actual=[row(p,HERE/'source/vm') for p in sorted((HERE/'source/vm').rglob('*')) if p.is_file()]
assert actual==source['members'] and digest(actual)==source['tree_sha256']
historical=HERE/'historical-independent';old=json.loads((historical/'seal.json').read_text())
assert sha((historical/'seal.json').read_bytes())=='e9d55089795d317048040be973e518ff9ce841d7f39cb1449b930d7ae066990c'
for member in old['members']:assert row(historical/member['path'],historical)==member
write('command-summary.json',{'schema':1,'commands':summary,'compiler_invocations':9,'filtered_host_runs':2,'methods_per_mode':25,'version_queries':1,'each_seconds_max':55,'layout_queries':0,'all_owned_children_reaped':True,'all_exact_owned_groups_absent':True,'native_fixture_UI_capture':False,'independent_acceptance':False})
write('cleanup.json',{'schema':1,'owned_commands_terminal':True,'owned_children_reaped':True,'exact_owned_groups_absent':True,'instances_started':0,'native_fixture_or_capture_processes_started':0,'other_projects_processes_touched':False,'scope':'Owned subprocess identities only; no global process/OS inventory.'})
write('result.json',{'schema':1,'status':'corrected-producer-source-and-selected-host-evidence-frozen-awaiting-independent-review','source146_tree':source['tree_sha256'],'host11_tree':json.loads((HERE/'host-manifest.json').read_text())['tree_sha256'],'protocol':'Every issued correlation scope permanently blocks Complete/refund; no reset/discharge route.','methods_per_mode':25,'Debug':'passed','opt_level2':'passed','unchanged_original_IR01_witness':'passes through Retained; H14 verifies same real proof pointer/1947 bytes/guards20..23/charge after owner Drop.','historical_IR01_failure_preserved':True,'compiler_missing_subcases_selected':list(k['id'] for k in roster['commands'] if k['kind']=='compiler-negative'),'compiler_claim_limits':'Only explicit Clone requirements at both types, correspondence live-borrow, proof-source/root-reservation static escapes, and two separate sibling privacy operations. Prior Copy/replay/caller-map/cfg(test) evidence is historical; external metadata privacy consumer is unrun.','native_policy_funding_layouts_prices_FieldLog_OTA_GA':'Pending','new_unpriced_obligations':'Added Cell<bool> changes owner/call/capture/move/return shapes; no inherited layout/MIR price authority.','frozen_vector_replay':'Additional full frozen51/230/12 replay not selected or executed in this correction.','production_loader_or_fixture_execution':False,'independent_acceptance':False})
# Preserve the historical seal too; exclude only this packet's own seal.
members=[row(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p!=HERE/'seal.json' and '__pycache__' not in p.parts]
seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'frozen-correction-awaiting-root-custody-release-and-independent-review','member_count':len(members),'member_bytes':sum(r['bytes'] for r in members),'tree_sha256':digest(members),'members':members,'source146_tree':source['tree_sha256'],'compiler_lane_released':True,'independent_acceptance':False,'native_or_GA_acceptance':False,'python':sys.version}
write('seal.json',seal)
print(json.dumps({'seal_sha256':sha((HERE/'seal.json').read_bytes()),'members':len(members),'bytes':seal['member_bytes'],'tree_sha256':seal['tree_sha256'],'source146_tree':source['tree_sha256']}))
