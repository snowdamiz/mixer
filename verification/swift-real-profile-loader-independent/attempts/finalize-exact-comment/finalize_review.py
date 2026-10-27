from pathlib import Path
import datetime,hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def ident(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def read(p):return json.loads(Path(p).read_bytes())
def write(n,obj):(HERE/n).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
def closed(p,expected):
 seal=p/'seal.json';assert sha(seal.read_bytes())==expected;rows=[]
 for f in sorted(p.rglob('*')):
  assert not f.is_symlink(),str(f)
  if f.is_file()and f!=seal:
   b=f.read_bytes();rows.append({'path':str(f.relative_to(p)),'bytes':len(b),'sha256':sha(b)})
 assert rows==read(seal)['members'];return {'path':str(p.relative_to(ROOT)),'seal_sha256':expected,'members':len(rows),'member_bytes':sum(m['bytes']for m in rows),'exact_closed_file_set':True,'all_member_identities_match':True}
producer=ROOT/'verification/swift-real-profile-loader-binding';baseline=ROOT/'verification/swift-typed-result-codec-implementation'
packets=[closed(producer,'e1701fb93056b763a06164d7ccf0cae3112f2e27baaa3f4a35aedd8e747665a2'),closed(baseline,'4f5e0ffd63c343511948d1bacc933698cd36369f94b3b96f3047ff325cd94b86'),closed(ROOT/'verification/swift-typed-result-codec-independent','8f22a9842cb609027d6f6cbe808eefb13d56cd52b68ef6cddec9a9926f5fc16b')]
a=read(baseline/'source-manifest.json');b=read(producer/'source-manifest.json');old={m['path']:m for m in a['members']};new={m['path']:m for m in b['members']};assert len(old)==142 and len(new)==144
added=sorted(set(new)-set(old));changed=sorted(p for p in old if old[p]!=new[p]);assert added==['src/experimental_swift_reactor/retained_profile_loader_v1.rs','src/experimental_swift_reactor/retained_profile_loader_v1_tests.rs'];assert changed==['src/experimental_swift_reactor/mod.rs']
mod='src/experimental_swift_reactor/mod.rs';before=(baseline/'source/vm'/mod).read_bytes();after=(producer/'source/vm'/mod).read_bytes();assert after.startswith(before);delta=after[len(before):];assert delta==b'\n// Actual safe-File loader; private, host-selected and not a runtime route.\nmod retained_profile_loader_v1;\n'
for name,m in old.items():
 if name!=mod:assert (baseline/'source/vm'/name).read_bytes()==(producer/'source/vm'/name).read_bytes()
oldhost={str(p.relative_to(baseline/'host')):p.read_bytes()for p in(baseline/'host').rglob('*')if p.is_file()};newhost={str(p.relative_to(producer/'host')):p.read_bytes()for p in(producer/'host').rglob('*')if p.is_file()};assert oldhost==newhost and len(oldhost)==11
verified=[]
for folder,filename in [(HERE,'baseline-command-receipts.json'),(HERE,'independent-command-receipts.json'),(HERE/'replay','command-receipts.json')]:
 commands=read(folder/filename)
 for c in commands:
  assert c['terminally_waited'] and c['killed_for']is None
  assert c.get('expectation_met',c['exit_code']==0)
  for stream in['stdout','stderr']:
   original=Path(c[stream]['path']);p=original if original.is_file()else folder/'logs'/original.name
   assert p.is_file(),str(p);r=ident(p);assert r['bytes']==c[stream]['bytes']and r['sha256']==c[stream]['sha256']
 verified.append({'path':str((folder/filename).relative_to(HERE)),'commands':len(commands),'all_expectations_and_output_identities_match':True,'direct_owned_children_terminally_waited':True})
assert [v['commands']for v in verified]==[9,43,105]
replay=read(HERE/'replay/receipt.json');fresh=read(HERE/'independent-receipt.json');assert replay['source_tree_sha256']==b['tree_sha256']=='3d7776d8ca3dc10894522079b49e0e8602b567c2e3926f9438b51c843fd6af13';assert replay['runner']['sha256']==ident(HERE/'replayed_run_checks.py')['sha256'];assert fresh['runner_hashed_before_compile']==ident(HERE/'run_independent.py')
closure=read(HERE/'independent-build-input-manifest.json')
for item in closure['independent_inputs']:assert ident(item['path'])==item
assert (HERE/'original_fixture.rs').read_text()==(baseline/'source/vm/tests/swift_reactor_validation_fixture.rs').read_text().replace('use mixer_vm::','use crate::')
for filename in ['baseline-cleanup.json','independent-cleanup.json','replay-cleanup.json']:
 c=read(HERE/filename);assert c['scratch_removed'];path=c.get('scratch_path',c.get('owned_scratch_path'));assert not Path(path).exists()
assert read(HERE/'replay/cleanup.json')['scratch_removed']
# The failed non-UTF8 argv0 session is retained under its first-failure attempt.
stale=HERE/'independent-preimages/debug-raw-argv.bin'
if stale.exists():assert (HERE/'attempts/independent-nonutf8-argv-harness'/stale.name).read_bytes()==stale.read_bytes();stale.unlink()
write('input-custody-after.json',{'schema':1,'packets':packets,'accepted_old_distribution_members':142,'candidate_distribution_members':144,'unchanged_old_source_files':141,'only_changed_existing_source':changed,'exact_private_module_append':delta.decode(),'added_distribution_sources':added,'unchanged_host_members':11,'command_output_sets_verified':verified,'total_successful_bounded_commands':157,'frozen_producer_or_prior_packets_written':False,'source_and_external_control_identities_unchanged_after':True})
write('review-result.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'independent-host-review-complete-with-one-nonblocking-diagnostic-finding','producer':packets[0],'source_tree_sha256':b['tree_sha256'],'scope':'Private selected macOS loader/carrier host correlation under trusted launcher and quiescent local host','authority_blocking_findings':[],'nonblocking_findings':[{'id':'R1','severity':'low','file':'source/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs','line':1105,'issue':'Final post-validation identity checks pass Role::Source for every File; slots1..3 therefore mislabel final recheck metadata/OS errors as Source, with array index as offset.','effect':'Guard still fails closed; original OS error and all File owners remain retained. No authority bypass observed in selected quiescent scope.','required_followup':'Correct all4 roles and add focused final-recheck role controls in next selected integration before claiming exact final-recheck role semantics. Frozen candidate was not edited.'}],'fresh_successful_bounded_commands':157,'producer_replay':{'commands':105,'genuine_loader_cases_each_mode':37,'helper_filter_methods_each_mode':13,'behavior_helpers_each_mode':12,'helper_filter_includes_no_context_emitter_method':True,'genuine_fixture_emissions_each_mode':1,'positive_compile_controls_each_mode':1,'negative_compile_controls_each_mode':8,'ordinary_production_layout_comparisons_each_mode':23},'independent_extra':{'commands':43,'helpers_each_mode':6,'genuine_loader_cases_each_mode':16,'original_late_failure_function':62,'original_late_failure_offset':8390447,'original_late_source_bytes':8390448,'original_late_failure_total_peak':8393796,'five_additional_File_alias_pairs':True,'full_entry_allocation_failpoints':[0,1,2,3,4],'actual_duplicate_ordinary_session_nonce_keys_refused':True,'actual_65_environment_entries_refused':True,'actual_empty_argv0_selected':True,'original_failure_payload_compared_directly_except_elapsed':True,'source_build_session_preimages_and_runner_binding_retained':True},'baseline_late_probe_commands':9,'modes':['debug','optimized'],'fixed_named_storage_bytes':197656,'conservative_union_bytes':152437784,'old165_layouts_cover_new_storage':False,'operational_storage_or_runtime_adoption_accepted':False,'unsupported':['Producer2 invalid-UTF8 filesystem path cases per mode refused by APFS EILSEQ92 before loader execution','Independent actual non-UTF8 argv0 refused by libtest main before loader execution; not candidate refusal/pass'],'all_owned_scratch_removed':True,'direct_owned_children_terminally_waited':True,'descendant_process_group_cleanup_claimed':False,'File_drop_is_proven_close':False,'native_simulator_emulator_device_UI_capture_process_inventory':'paused-unused-pending','authenticated_build_package_hostile_launcher_protection':False,'canonical_native_OTA_FieldLog_store_customer_operational_GA_accepted':False,'recommendation':'Root may accept selected isolated private loader/carrier host-correlation scope with R1 retained; wider integration and all gates remain pending'})
print(json.dumps({'status':'review-data-checks-pass','successful_commands':157,'nonblocking_findings':1}))
