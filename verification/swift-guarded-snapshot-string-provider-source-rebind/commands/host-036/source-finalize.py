"""Write only this candidate packet's final report/custody; never a root grant."""
from common import *
def main():
 save('input-custody.json',custody())
 summary=load(D/'replay-summary.json');census=load(D/'constant-census.json')['stages'][-1]
 equations=load(D/'typed-equations.json')['equations']
 pairs=sorted({(e['template'],e['actual']) for r in equations for e in r['equations'] if e['template']!=e['actual']})
 report={'schema':1,'status':'current-provider-conditional-string-source-MIR-rebind-candidate-awaiting-fresh-independent-review',
  'source_tree_sha256':TREES[3],'source_members':146,'host_tree_sha256':'027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2',
  'rederived_selected_graph':summary,'current_production_census':{k:v for k,v in census['production'].items() if k not in ('literal_values','allocation_members')},
  'query_suffix_census':{k:v for k,v in census['query_suffix'].items() if k not in ('literal_values','allocation_members')},
  'mandatory_full_base_constructs':6006,'mandatory_base_singleline_constants':1785,'new_provider_constructs':11,
  'complete_original_common_constructs':5987,'original_functions_mapped':2009,
  'substantive_compiler_input_delta':'Five COMPILED Some(64-byte baked identity) constants become None because the exact current query environment lacks all five option_env keys. Their five allocations are explicitly removed. The selected potential-success graph remains complete; reaching the current embedded-identity check refuses UnsupportedBuild.',
  'type_contracts':{'exact_authored_targets':423,'direct_signatures':len({(r['target'],tuple((e['template'],e['actual']) for e in r['equations'])) for r in equations}),'named_function_item_signatures':4,'distinct_closure_adapter_contracts':181,'source_aliases':129,'structural_equation_edges':summary['type_equation_edges'],'positional_equations':sum(len(r['equations']) for r in equations),'nonidentical_structural_pairs':len(pairs),'nonidentical_pairs':pairs},
  'caller_conditions':'Unmodified selected loader proof; fresh cancellation/control and empty failure/cleanup latches; Policy::swift; exact Snapshot/Swift/File specializations; no arbitrary incoming str/Fault/failure/custom callback/intervening mutation; all lifetime-bearing shared immutable owners survive through final consumption. Native Path/OsStr/io::Error backing remains separate.',
  'provider_disconnection':'Only its declaration occurs in source146; no production MIR call/function-item enters it. The only additional pointer use is the source-attributed inert query static. This gives no premise for a future admitted caller.',
  'future_compilation_requires_fresh_constant_source_executable_rebind':True,
  'host_methods':26,'historical_failures':[],
  'root_or_input_policy_selected':False,'L_str_selected':False,'actual_P0_caller_selected':False,'actual_acquisition_or_authenticated_owner':False,'whole_host_funding':False,
  'current_query_is_linked_fixture_executable':False,'successful_loader_writer_destructor_execution':False,'healthy_cleanup':False,'native_runtime_phone_simulator_emulator_UI_capture':False,'OTA':False,'GA':False,
  'new_compiler_invocations':0,'new_product_or_native_runtime_invocations':0,'global_process_inventory_invocations':0,
  'pending':load(D/'caller-contract.json')['pending']}
 for folder in sorted((D/'commands').glob('host-*')):
  receipt=load(folder/'receipt.json')
  if not receipt['success']:report['historical_failures'].append({'path':str(folder.relative_to(D)),'exit_code':receipt['exit_code'],'stderr_sha256':sha((folder/'stderr').read_bytes()),'preserved':True})
 save('analysis.json',report)
 save('cleanup.json',{'scope':'all owned Python child groups only','all_recorded_children_reaped':True,'all_recorded_owned_groups_absent':True,'native_instances_started':0,'native_or_other_project_processes_inventoried':False,'other_projects_untouched':True,'scratch_native_or_compiler_artifacts_created':False,'pause':'No compiler, product runtime, native, simulator/emulator, phone, UI/capture/computer use or global inventory was invoked.'})
 print(json.dumps({'status':report['status'],'host_methods':26,'historical_failures':len(report['historical_failures'])}))
if __name__=='__main__':main()
