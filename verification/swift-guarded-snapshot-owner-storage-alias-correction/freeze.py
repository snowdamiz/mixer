"""Seal only after the root releases and this packet reconciles the final review."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
assert not (ROOT/'seal.json').exists(),'frozen correction is immutable'
review=json.loads((ROOT/'review-reconciliation.json').read_text())
assert review['all_frozen_findings_addressed'] and review['root_review_release_received']
assert sha(Path(review['frozen_review_seal_path']).read_bytes())==review['frozen_review_seal_sha256']
cleanup=json.loads((ROOT/'cleanup.json').read_text());assert cleanup['all_owned_groups_absent_and_reaped'] and cleanup['compiler_scratch_removed']
checks=json.loads((ROOT/'producer-control-replay.json').read_text());assert checks['all_pass'] and checks['count']==17
controls=json.loads((ROOT/'adversarial-controls.json').read_text());assert controls['all_pass'] and controls['count']==60
recipe=json.loads((ROOT/'recipe-control-results.json').read_text());assert recipe['all_owned_groups_absent_and_reaped'] and recipe['owned_scratch_removed']
formula=json.loads((ROOT/'formula.json').read_text())
assert [formula[k] for k in ['common_extra','selected_unconditional_extra','admitted_only_extra','host_caller_extra']]==[78240,941467,430175,81327]
value={'schema':1,'status':'complete-separate-source-alias-and-call-correction-awaiting-root-acceptance',
       'producer_seal_sha256':'afd33c1df35e4072e582789a38c14372f9a8efc4c6243301df4399e4899f2e4b',
       'source_tree_sha256':'575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896',
       'roles':3115,'templates':81,'aliases':356,'retained_unused_legacy_roles':65,
       'formula':formula,'host_admitted_increment_from_legacy':1531209,
       'prior_wrong_alias_claims_repaired':28,'additional_unproved_failure_argument_charged':1096,
       'changed_current_role_assignments':40,'new_legacy_credits_selected':False,
       'unselected_conservative_foundation_charge_retained':2192,
       'complete_calls':627,'target_displays_repaired':107,'owned_callback_edges_added':2,
       'complete_owned_graph_acyclic':True,'call_correction_storage_delta':0,
       'producer_controls_replayed':17,'targeted_controls':60,'metadata_positive_contexts':['production','cfg(test)'],
       'overflow_refusal':'expected E0080','runtime_executions':0,'source_or_layout_changes':False,
       'operational_floor_selected':False,'budget_changes':False,'writer_dispatch':False,
       'native_UI_capture_and_process_inventory':'paused/not performed',
       'root_acceptance_pending':True,'GA_or_production_claim':False}
(ROOT/'result.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
members=[]
for path in sorted(ROOT.rglob('*')):
    if path.is_file() and '__pycache__' not in path.parts and path.name!='seal.json':
        data=path.read_bytes();members.append({'path':str(path.relative_to(ROOT)),'bytes':len(data),'sha256':sha(data)})
seal={'schema':1,'scope':'separate corrected source-role aliases, funding and complete compiler call evidence; no operational selection',
      'members':members,'member_count':len(members),'total_bytes':sum(r['bytes'] for r in members),
      'members_tree_sha256':sha(canonical(members)),
      'producer_seal_sha256':value['producer_seal_sha256'],'source_tree_sha256':value['source_tree_sha256']}
(ROOT/'seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
print(json.dumps({'members':len(members),'bytes':seal['total_bytes'],'tree_sha256':seal['members_tree_sha256'],
                  'seal_sha256':sha((ROOT/'seal.json').read_bytes())}))
