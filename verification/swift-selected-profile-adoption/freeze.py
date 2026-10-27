#!/usr/bin/env python3
"""Verify final-byte coverage/custody, clean only owned scratch, then seal once."""
from pathlib import Path
import datetime,hashlib,json,re,shutil,sys
sys.dont_write_bytecode=True
import evidence as E
import contracts as C
R=E.HERE
INITIAL=['selected_layout_and_places','fresh_header_rows_and_cleanup','same_control_wasi_and_unrelated_owners','complete17_drift_precedes_prepare','explicit_narrowed_budgets','header_retained_when_actual_row_file_refuses','all64_slot_pin_pairs_checked','local_structure_refusals','original_prepare_construct_completion_outcomes','occupancy_foreign_proof_and_prepare_failures','authentic_owner_and_every_initial_field','post_acquire_chronology_cannot_reenter','canonical_ceilings_and_prepare_capacity','foreign_wasi_prepare_owned_cleanup','control_live_counts_and_peaks','all17_explicit_exhaustions','supported_count_boundary']
LOADER=['success','narrowed','raw-environment','source-substitute','source-extent','build-tail','build-identity','binary-substitute','session-digest','nonce','argv','environment','cwd','offset','alias','nonregular','unreadable','zero-source','zero-metadata','zero-scratch','zero-work','zero-deadline','cancelled','malformed','large-malformed','build-overcap','session-overcap']+[prefix+'-'+field for prefix in ['drift','widen']for field in ['source','metadata','scratch','work','deadline']]
SELECTED=['occupied','selection','preparation','construction','completion','header','owner','encoded','foreign-control','admission-source','admission-metadata','admission-combined','admission-deadline','admission-cancelled','admission-invalid']
OLD=['original-'+name for name in ['positive','clone','private_proof','private_provenance','literal','source_escape','source_mutation','raw_proof_mint','deserialize']]
GUARD=['guard-'+placement+'-'+name for name,placement in [('positive_contract','descendant'),('positive_contract','cache-sibling'),('guard_literal_from_sibling','cache-sibling'),('external_selection_literal','cache-sibling'),('guard_escape','descendant'),('proof_escape','descendant'),('cache_move','descendant'),('cache_mutation','descendant'),('control_mutation','descendant'),('row_foreign_snapshot','descendant'),('callback_reentry','descendant')]]
ALLOWED={
 'src/experimental_swift_reactor/'+name for name in ['retained_profile_loader_v1.rs','retained_profile_loader_v1_tests.rs','control.rs','cache.rs','execution.rs','cache/initial_profile_v1.rs','cache/initial_profile_v1/local_structure.rs','cache/initial_profile_v1/selected.rs','cache/initial_profile_v1/tests.rs','cache/initial_profile_v1/compile_contracts.rs','cache_tests.rs','mod.rs']}
def verify_packet(name,seal_sha):
 root=R.parent/name;seal=root/'seal.json';assert E.sha(seal.read_bytes())==seal_sha
 data=json.loads(seal.read_text());declared={x['path']:x for x in data['members']}
 actual={str(p.relative_to(root))for p in root.rglob('*')if p.is_file()and p!=seal}
 assert actual==set(declared)
 for name,member in declared.items():
  p=root/name;assert not p.is_symlink();b=p.read_bytes();assert len(b)==member['bytes']and E.sha(b)==member['sha256']
 return {'seal_sha256':seal_sha,'member_count':len(declared),'member_bytes':sum(x['bytes']for x in declared.values())}
def main():
 assert not (R/'seal.json').exists(),'frozen packet must not be changed or rerun in place'
 source=E.manifest(E.SOURCE);assert source['member_count']==144
 base=json.loads((R.parent/'swift-real-profile-loader-binding/source-manifest.json').read_text())
 old={m['path']:m for m in base['members']};new={m['path']:m for m in source['members']};assert set(old)==set(new)
 changed={p for p in old if old[p]!=new[p]};assert changed==ALLOWED,(changed^ALLOWED)
 support=json.loads((R.parent/'swift-real-profile-loader-binding/baseline-host-support-manifest.json').read_text());assert len(list((R/'host').rglob('*.py')))+len(list((R/'host').rglob('*.rs')))==11
 for member in support['members']:assert E.ident(R/member['retained_path'])['sha256']==member['sha256']
 public=json.loads((R/'public-compiler-source-mapping.json').read_text());assert len(public)==13
 records=[];pending=[]
 for folder in sorted((R/'commands').iterdir()):
  p=folder/'receipt.json'
  if not p.exists():pending.append(str(folder.relative_to(R)));continue
  row=json.loads(p.read_text());row['receipt_path']=str(p.relative_to(R));assert row['terminally_waited']
  for stream in ['stdout','stderr']:
   b=(folder/stream).read_bytes();assert len(b)==row[stream]['bytes']and E.sha(b)==row[stream]['sha256']
  records.append(row)
 assert not pending,('owned command not terminally recorded',pending)
 final={row['label']:row for row in records if row['source_tree_sha256']==source['tree_sha256']and row['expectation_met']and(row.get('compiled_context')is None or row['compiled_context']['context']['distribution']['tree_sha256']==source['tree_sha256'])}
 expected=[]
 for mode in ['debug','optimized']:
  expected += ['compile-unit-'+mode,'compile-host-'+mode,'host-layout-'+mode,'ordinary-production-layout-'+mode,mode+'-complete_adoption_layout_inventory_v1',mode+'-loader-helpers',mode+'-emit_genuine_validator_fixture',mode+'-suite-experimental_swift_reactor::cache_tests::',mode+'-suite-experimental_swift_reactor::execution_tests::','public-library-'+mode]
  expected += [mode+'-'+name for name in INITIAL+LOADER]
  expected += [mode+'-adopt-'+name for name in SELECTED]
  expected += [f'host-{mode}-method-{i}'for i in range(1,9)]
  expected += ['contract-'+mode+'-'+name for name in list(C.NEW)+OLD+GUARD]
  expected += ['public-contract-'+mode+'-'+row['case']for row in public]
 missing=sorted(set(expected)-set(final))
 if '--check' in sys.argv:
  print(json.dumps({'source_tree_sha256':source['tree_sha256'],'expected_final_labels':len(set(expected)),'complete_final_labels':len(set(expected)&set(final)),'missing':missing},indent=2));return
 assert not missing,missing
 for mode in ['debug','optimized']:
  for suffix,count in [('loader-helpers',17),('suite-experimental_swift_reactor::cache_tests::',38),('suite-experimental_swift_reactor::execution_tests::',22)]:
   row=final[mode+'-'+suffix];stdout=(R/row['receipt_path']).parent.joinpath('stdout').read_text()
   assert f'test result: ok. {count} passed; 0 failed;' in stdout,(mode,suffix)
  for name in INITIAL+LOADER+['adopt-'+x for x in SELECTED]:
   row=final[mode+'-'+name];stdout=(R/row['receipt_path']).parent.joinpath('stdout').read_text()
   assert 'test result: ok. 1 passed; 0 failed;' in stdout,(mode,name)
 # The two actual production cap declarations remain byte-identical.
 control_path='src/experimental_swift_reactor/control.rs'
 old_control=(R.parent/'swift-real-profile-loader-binding/source/vm'/control_path).read_text();new_control=(E.SOURCE/control_path).read_text()
 def defaults(text):
  start=text.index('impl Default for SwiftRunBudget');return text[start:text.index('\n#[derive',start)]
 assert defaults(old_control)==defaults(new_control)
 selection_path='src/experimental_swift_reactor/cache/initial_profile_v1/selected.rs'
 def selected_budget(text):return text[text.index(' budget:SwiftRunBudget {'):text.index(' local:SelectedLocalStructureV1')]
 assert selected_budget((R.parent/'swift-real-profile-loader-binding/source/vm'/selection_path).read_text())==selected_budget((E.SOURCE/selection_path).read_text())
 for config in ['production','unit']:
  a=json.loads((R/f'layouts/{config}-debug.json').read_text());b=json.loads((R/f'layouts/{config}-optimized.json').read_text())
  assert a['source_tree_sha256']==b['source_tree_sha256']==source['tree_sha256']
  assert a['rows']==b['rows']and a['values']==b['values']and len(a['rows'])==201
  assert [x['id']for x in a['rows']]==list(range(1,202))
 for mode in ['debug','optimized']:
  context=json.loads((R/f'compiled-{mode}.json').read_text());assert context['context']['distribution']==source
  assert E.ident(E.WORK/f'unit-{mode}')==context['binary']
  for item in context['context']['orchestration']:assert E.ident(item['path'])==item
  for key in ['rustc','python']:assert E.ident(context['context']['tools'][key]['path'])==context['context']['tools'][key]
  for header in context['context']['tools']['SDK_headers']:assert E.ident(header['path'])==header
  assert context['context']['tools']['rustc']==E.ident(E.RUSTC)
 # Exact old165 identities remain; new36 measurements were appended.
 base_compare=(R.parent/'swift-real-profile-loader-binding/source/vm/src/experimental_swift_reactor/cache/initial_profile_v1/local_structure.rs').read_text()
 new_compare=(E.SOURCE/'src/experimental_swift_reactor/cache/initial_profile_v1/local_structure.rs').read_text()
 assert re.findall(r'compare!\((\d+),(.*?)\);',base_compare,re.S)==re.findall(r'compare!\((\d+),(.*?)\);',new_compare,re.S)
 inputs={'loader':verify_packet('swift-real-profile-loader-binding','e1701fb93056b763a06164d7ccf0cae3112f2e27baaa3f4a35aedd8e747665a2'),'independent':verify_packet('swift-real-profile-loader-independent','20841ffd95685e0a65d926c747dfd2c7394341663593cca7c6c01d2c2f329c3f')}
 # Verify every retained historical source snapshot independently.
 custody=json.loads((R/'historical-source-custody.json').read_text())
 for item in custody['exact_tree_digests_checked']:assert E.manifest(R/item['path'])['tree_sha256']==item['tree_sha256']
 artifacts=[E.ident(p)for p in sorted(E.WORK.iterdir())if p.is_file()]
 E.write(R/'artifacts-measured-before-owned-removal.json',artifacts)
 shutil.rmtree(E.WORK);assert not E.WORK.exists()
 cleanup={'schema':1,'owned_scratch_removed':True,'all_recorded_direct_children_terminally_waited':True,'native_simulator_emulator_UI_capture_or_process_inventory_used':False,'File_drop_or_process_exit_is_close_success':False,'owned_names_removed_after_terminal_children':True,'other_projects_processes_or_files_touched':False}
 E.write(R/'cleanup.json',cleanup)
 failed=[{'receipt':r['receipt_path'],'label':r['label'],'exit_code':r['exit_code'],'source_tree_sha256':r['source_tree_sha256']}for r in records if not r['expectation_met']]
 E.write(R/'source-manifest.json',source);E.write(R/'source-change-roster.json',{'schema':1,'baseline_tree_sha256':base['tree_sha256'],'final_tree_sha256':source['tree_sha256'],'changed_existing_paths':sorted(changed),'unchanged_existing_files':144-len(changed),'added_distribution_files':0,'root_comment_amendment':E.ident(R/'root-comment-amendment.json'),'conditional_cache_test_change':'only expected foundation sum now includes the exact new source-backed floors; original tests retained'})
 E.write(R/'final-required-command-matrix.json',{'schema':1,'source_tree_sha256':source['tree_sha256'],'required_commands':len(set(expected)),'by_label':{label:final[label]['receipt_path']for label in sorted(set(expected))}})
 E.write(R/'command-receipts.json',records)
 scope={'schema':1,'status':'private-selected-profile-adoption-host-candidate-pass-awaiting-independent-review-and-root-acceptance','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_tree_sha256':source['tree_sha256'],'source_members':144,'unchanged_source_members':144-len(changed),'unchanged_host_support_members':11,'all_original165_type_identities_preserved':True,'appended_types':36,'layouts_each_configuration':201,'configurations':['aarch64-apple-darwin Debug unit','aarch64-apple-darwin optimized unit','Debug production host','optimized production host','Debug ordinary production metadata','optimized ordinary production metadata'],'genuine_loader_cases_each_mode':37,'genuine_selected_cases_each_mode':15,'selected_cases_include':'all8constructor outcomes, actual foreign control,6admission refusal/destruction cases','original_initial_methods_each_mode':17,'production_host_methods_each_mode':8,'cache_behavior_methods_each_mode':38,'execution_behavior_methods_each_mode':22,'compiler_controls_each_mode':46,'compiler_control_positive_each_mode':5,'compiler_control_negative_each_mode':41,'public_original_exact_source_controls_each_mode':13,'original_external_cargo_wrapper_run':False,'actual_Final_File_mismatch_roles_each_mode':4,'synthetic_helper_IO_roles_each_mode':4,'final_required_commands':len(set(expected)),'total_historical_and_final_commands':len(records),'retained_first_command_failures':failed,'historical_source_custody':'historical-source-custody.json','inputs':inputs,'root_selection':E.ident(R/'selection.json'),'root_comment_amendment':E.ident(R/'root-comment-amendment.json'),'entry_context':'preparation/input-custody.json','actual_compiler_contexts':['compiled-debug.json','compiled-optimized.json'],'cleanup':cleanup,'original_validation_runtime_caps_raised':False,'full_runtime_provenance_implemented_in_isolated_source':True,'operational_loader_storage_admitted':False,'canonical_export_context_native_FieldLog_OTA_store_customer_operations_GA_accepted':False,'trusted_scope':'trusted launcher/compiler, quiescent local macOS correlation only','unrun':['raw cwd/executable APFS pathname cases','raw nonUTF8 argv0 full-entry case','original nested-Cargo external_surface_and_borrow_privacy wrapper','native/simulator/emulator/UI/capture/process inventory','exporter/context/canonical integration','operational loader storage and descriptor close/name-custody admission','FieldLog immutable published packages,OTA/store/customer/operations and GA']}
 E.write(R/'receipt.json',scope)
 scope['additional_retained_tooling_failures']=['preparation/first-inspection-failure.json','preparation/first-prepare-failure.json','preparation/diagnostic-search-missing-file.json','runner-failures/001-layout-values-parser.json']
 scope['loader_helper_filter_methods_each_mode']=17
 scope['loader_helper_behavior_methods_each_mode']=16
 scope['loader_helper_filter_includes_noop_fixture_emitter']=True
 scope['genuine_fixture_emission_is_separately_required_each_mode']=True
 E.write(R/'receipt.json',scope)
 assert E.manifest(E.SOURCE)==source
 members=[]
 for p in sorted(R.rglob('*')):
  assert not p.is_symlink()
  if p.is_file():members.append({'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':E.sha(p.read_bytes())})
 seal={'schema':1,'scope':'frozen private selected-profile adoption host candidate; no root/canonical/GA acceptance','member_count':len(members),'member_bytes':sum(x['bytes']for x in members),'members':members}
 E.write(R/'seal.json',seal)
 print(json.dumps({'status':scope['status'],'source_tree_sha256':source['tree_sha256'],'seal_sha256':E.sha((R/'seal.json').read_bytes()),'member_count':len(members),'member_bytes':seal['member_bytes'],'final_required_commands':len(set(expected)),'historical_commands':len(records),'retained_first_failures':len(failed),'cleanup':cleanup},indent=2))
if __name__=='__main__':main()
