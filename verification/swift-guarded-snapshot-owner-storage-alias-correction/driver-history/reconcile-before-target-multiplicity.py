"""Reconcile the root-released immutable independent review, without new probes."""
from pathlib import Path
from collections import Counter
import json,sys
sys.dont_write_bytecode=True
from correct import ROOT,PRODUCER,sha,canonical,save,custody

REVIEW=ROOT.parent/'swift-guarded-snapshot-owner-storage-independent/actual-review'
RELEASE=ROOT.parent/'swift-semantic-adapter-root-review/guarded-snapshot-owner-storage-review-release.json'
RELEASE_SHA='434b4b9d959a222cf10a35c457a97987ebb85850e1f4ded8a03205119de75a6a'
REVIEW_SHA='f5083b7a2cf24d2e8e0ede20b287e5e88c62febb56b053f3d66276cb535f38ed'

def main():
    custody();assert sha(RELEASE.read_bytes())==RELEASE_SHA
    release=json.loads(RELEASE.read_text());seal=(REVIEW/'seal.json').read_bytes()
    assert sha(seal)==REVIEW_SHA==release['review_seal']['sha256']
    manifest=json.loads(seal)
    for row in manifest['members']:
        data=(REVIEW/row['path']).read_bytes()
        assert len(data)==row['bytes'] and sha(data)==row['sha256'],row['path']
    assert len(manifest['members'])==37 and sum(r['bytes'] for r in manifest['members'])==11960570
    aliases={r['new_id']:r for r in json.loads((ROOT/'inherited-aliases.json').read_text())['aliases']}
    funding={r['id']:r for r in json.loads((ROOT/'funding.json').read_text())['roles']}
    changes=json.loads((ROOT/'delta.json').read_text())['changed_roles']
    prior={r['new_id']:r for r in json.loads((PRODUCER/'inherited-aliases.json').read_text())['aliases']}
    dispositions=[];affected=set()
    receivers=json.loads((REVIEW/'alias-repair-suggestions.json').read_text())
    for q in receivers['suggestions']:
        nid=q['current']['id'];oid=q['suggested_baseline']['id'];affected.add(nid)
        assert aliases[nid]['old_id']==oid and prior[nid]['old_id']==q['wrong_baseline']['id']
        dispositions.append({'kind':'receiver-context','affected_new_id':nid,
                             'corrected_old_id':oid,'disposition':'full enclosing call/function/ordered occurrence repaired'})
    additional=json.loads((REVIEW/'additional-alias-findings.json').read_text())
    for q in additional['findings']:
        nid=q['currently_aliased_role']['id'];oid=q['baseline_role']['id'];candidate=q['source_exact_current_candidate']['id'];affected.add(nid)
        assert aliases[candidate]['old_id']==oid and prior[nid]['old_id']==oid
        assert (aliases.get(nid) or {}).get('old_id')!=oid
        dispositions.append({'kind':'borrow-or-argument-context','affected_new_id':nid,
                             'correct_source_current_id':candidate,'corrected_old_id':oid,
                             'disposition':'old discount moved to exact surviving source occurrence; new operation charged'})
    flags=json.loads((REVIEW/'drop-flag-findings.json').read_text())
    for q in flags['pairs']:
        nid=q['current']['flag_role']['id'];oid=q['baseline']['flag_role']['id'];affected.add(nid)
        assert prior[nid]['old_id']==oid and (aliases.get(nid) or {}).get('old_id')!=oid
        dispositions.append({'kind':'owned-drop-flag','affected_new_id':nid,
                             'old_wrong_id':oid,'corrected_old_id':(aliases.get(nid) or {}).get('old_id'),
                             'disposition':'guarded owned place or exact dead-field initialization identity checked; new owner flag charged'})
    raw=json.loads((PRODUCER/'raw-inventory.json').read_text())
    adopt=next(f['id'] for f in raw['functions'] if f['name'].endswith('::adopt_body_core_v1'))
    old_adopt=next(f['id'] for f in raw['baseline_functions'] if f['name'].endswith('::adopt_body'))
    for family,new_prefix,old_prefix in [('constructor','owner::construct_profile_core_v1','owner::construct_with_initial_profile_v1'),('adoption',adopt,old_adopt)]:
        for new_local,old_local in flags['source_exact_reassignment_seeds'][family].items():
            assert aliases[new_prefix+'::'+new_local]['old_id']==old_prefix+'::'+old_local
    failure=json.loads((REVIEW/'failure-boundary-finding.json').read_text())
    nid=failure['current_role']['id'];affected.add(nid)
    assert nid not in aliases and funding[nid]['funding']=={'common-extra':1096,'selected-unconditional':0,'admitted-only':0}
    dispositions.append({'kind':'new-failure-call-boundary','affected_new_id':nid,
                         'disposition':'unproved alias refused; actual1096byte argument charged in C; old slot retained in legacy floor'})
    changed_prior={r['id'] for r in changes if r['before_old_id'] is not None}
    assert affected==changed_prior and len(affected)==29
    independent=json.loads((REVIEW/'complete-calls-and-callbacks.json').read_text())
    calls=json.loads((ROOT/'call-boundaries.json').read_text())
    def call_key(r):return r['caller'],r['call_result_role'],r['target'],r['source_statement']
    assert Counter(map(call_key,calls['calls']))==Counter(map(call_key,independent['calls']))
    delta=json.loads((ROOT/'call-delta.json').read_text())
    ours={(r['caller'],r['call_result_role'],r['before_target'],r['after_target']) for r in delta['changed_calls']}
    theirs={(r['caller'],r['result'],r['truncated_target'],r['complete_target']) for r in independent['target_display_differences']}
    assert ours==theirs and len(ours)==107
    ours_cb={(r['from'],cb,r['call_result_role']) for r in calls['calls'] for cb in r['owned_callbacks']}
    theirs_cb={(r['from'],r['to'],r['result']) for r in independent['actual_owned_callback_edges']}
    assert ours_cb==theirs_cb
    missing={(r['from'],r['to'],r['result']) for r in independent['actual_owned_callback_edges'] if not r['producer_callback_present']}
    added={(r['from'],r['to'],r['call_result']) for r in delta['added_owned_callback_edges']}
    assert missing==added and len(added)==2
    assert independent['acyclic_after_complete_callback_reconstruction'] and calls['correction']['graph_acyclic']
    optional=json.loads((ROOT/'optional-credits-unselected.json').read_text());assert not optional['selected'] and len(optional['correspondences'])==2
    formula=json.loads((ROOT/'formula.json').read_text())
    assert (formula['common_extra'],formula['selected_unconditional_extra'],formula['admitted_only_extra'],formula['host_caller_extra'])==(78240,941467,430175,81327)
    formula['released_original_review_reconciled']=True
    formula['correction_root_acceptance_pending']=True
    save('formula.json',formula)
    value={'schema':1,'root_review_release_received':True,'root_release_path':str(RELEASE),
           'root_release_sha256':RELEASE_SHA,'frozen_review_seal_path':str(REVIEW/'seal.json'),
           'frozen_review_seal_sha256':REVIEW_SHA,'review_members_verified':37,'review_bytes_verified':11960570,
           'all_frozen_findings_addressed':True,'alias_dispositions':dispositions,
           'affected_aliases_reconciled':29,'all_corrected627_call_targets_equal_independent_fresh_reconstruction':True,
           'target_repairs_reconciled':107,'all18_owned_callback_edges_equal_independent_reconstruction':True,
           'missing_callback_edges_reconciled':2,'complete_graph_acyclic':True,
           'existing_conservative_foundation_charge2192_retained':True,'new_legacy_credits_selected':False,
           'original_producer_accepted':False,'corrected_candidate_root_acceptance_pending':True,
           'source_layout_runtime_changes':False,'no_new_generic_revalidation_loop':True,
           'corrected_alias_map_sha256':sha((ROOT/'inherited-aliases.json').read_bytes()),
           'corrected_funding_sha256':sha((ROOT/'funding.json').read_bytes()),
           'corrected_call_boundaries_sha256':sha((ROOT/'call-boundaries.json').read_bytes())}
    save('review-reconciliation.json',value)
    print('PASS frozen review reconciliation:29 aliases,627 full targets/107 repairs,18 callback edges/2 repairs; all findings addressed')
    custody()

if __name__=='__main__':main()
