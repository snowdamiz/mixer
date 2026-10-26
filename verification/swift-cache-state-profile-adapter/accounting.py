#!/usr/bin/env python3
"""Exact-source logical-place inventory, conservative whole-union/source-work proof.
This is not a compiler stack-frame, machine-instruction, RSS or debit receipt.
"""
from pathlib import Path
import hashlib,json,re
P=Path(__file__).resolve().parent

def build():
    layouts={}
    for mode in ['debug','optimized']:
        text=(P/'logs'/f'{mode}-units.stdout').read_text()
        values={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)', '\n'.join(x for x in text.splitlines() if 'LAYOUT ' in x))}
        assert values;layouts[mode]=values
    assert layouts['debug']==layouts['optimized']
    # Sizes below are measured above; place multiplicities deliberately overcount
    # mutually-exclusive branches/temporaries to avoid an optimistic reuse claim.
    groups={
      'external_caller': [('writer_caller_tuple',152,1),('row_caller_tuple_for_independent_helper',88,1)],
      'safe_File_wrapper': [('argument_pair',16,1),('complete_admit_Result',40,2),('complete_writer_Result',72,1),('File_borrow_closure',8,1)],
      'write_body': [('argument_reference_and_closure',8,2),('block',4096,1),('global_counters',8,2),('step_iterator',24,1),('row_range',8,1),('first_and_local_u32',4,2),('row_start_usize',8,1),('complete_row_Result',40,1),('row_value',32,1),('done_calls_remaining',8,3),('write_slice_borrow',16,1),('complete_write_Result',16,1),('returned_count',8,1),('io_error',8,1),('io_error_kind_rounded',8,1),('finish_observations',136,1),('constructed_observation',64,1),('complete_return_Result',72,1),('all_four_conversion_Results',16,4),('all_four_finish_errors',32,4),('forwarded_row_error',32,1),('error_return_value',32,1),('bounded_scalar_comparison_padding',8,16)],
      'profile_row_v1': [('argument_tuple_rounded',16,1),('coordinate',8,1),('complete_admit_Result',40,1),('observations',136,1),('all_checked_Option_usize',16,2),('end_and_body_end',8,2),('optional_descriptor',32,1),('descriptor',32,1),('source_and_body_borrows',16,2),('complete_row_return_Result',40,1),('constructed_row',32,1),('both_conversion_Results',16,2),('all_lexical_error_constructions',32,9),('bounded_scalar_comparison_padding',8,16)],
      'admit': [('snapshot_argument',8,1),('observations',136,1),('policy_str_borrow',16,1),('checked_Option',16,1),('total',8,1),('complete_return_Result',40,1),('all_lexical_errors',32,3),('bounded_scalar_comparison_padding',8,8)],
      'encode': [('row_and_output_arguments',48,1),('all_LE_array_values',32,1),('all_five_destination_slice_places',16,5),('all_five_source_array_borrows',8,5)],
      'admit_output': [('File_argument',8,1),('complete_metadata_Result',152,1),('metadata',144,1),('complete_position_Result',16,1),('position',8,1),('complete_return_Result',40,1),('all_four_errors',32,4),('bounded_scalar_comparison_padding',8,4)],
      'error': [('argument_tuple',16,1),('constructed_return_error',32,1)],
      'with_progress': [('complete_argument_tuple',48,1),('complete_return_error',32,1)]}
    inventory=[]
    for name,cells in groups.items():
      inventory.append({'function_or_owner':name,'places':[{'name':n,'bytes':b,'count':c,'reserved_bytes':b*c} for n,b,c in cells],'bytes':sum(b*c for n,b,c in cells)})
    union=sum(g['bytes'] for g in inventory)
    source=P/'source/vm/src/experimental_swift_reactor/diagnostic_profile.rs';lines=source.read_text().splitlines()
    starts=[(i+1,re.match(r'(?:pub\(crate\) )?fn (\w+)',l).group(1)) for i,l in enumerate(lines) if re.match(r'(?:pub\(crate\) )?fn (\w+)',l)]
    spans=[{'function':name,'start':line,'end':starts[i+1][0]-1 if i+1<len(starts) else len(lines)-3} for i,(line,name) in enumerate(starts)]
    work=[{'item':'snapshot_admission_and_row_derivation_including_two_observation_copies_lookup_checked_fields_all_branches_and_error_construction','per_unit_bound':1024,'units':80000}, {'item':'five_explicit_LE_serializations_and_32_wire_byte_transfers','per_unit_bound':128,'units':80000},{'item':'row_loop_induction_index_and_bounded_slice_construction','per_unit_bound':32,'units':80000},{'item':'block_loop_induction_and_reset','per_unit_bound':32,'units':625},{'item':'write_result_classification_counter_updates_error_and_progress_transfers','per_unit_bound':128,'units':20000},{'item':'top_level_admission_File_metadata_position_and_finish_caller_Result_transfers','per_unit_bound':1024,'units':1}]
    record={'schema':1,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'candidate_tree_sha256':json.loads((P/'logs/sealed-compile-debug.json').read_text())['candidate_source_tree_sha256'],'measured_layouts':layouts,'logical_place_inventory':inventory,'conservative_whole_union_bytes':union,'all_mutually_exclusive_phases_summed':True,'maximum_alignment':8,'separate_snapshot_fixed_bytes':664,'separate_snapshot_retained_limits':{'source_bytes':64*1024*1024,'metadata_bytes':16*1024*1024,'validation_scratch_bytes':1024*1024,'validation_work':512000000,'validation_deadline_ms':120000},'source_spans':spans,'source_work_model':work,'source_work_upper_bound':sum(x['per_unit_bound']*x['units'] for x in work),'source_work_model_unit':'one scalar/byte-transfer/comparison/counter/Result-transfer source action; conservative structured-source accounting, not CPU instructions or borrowed G totals','max_rows':80000,'row_wire_bytes':32,'block_bytes':4096,'blocks':625,'max_calls_per_block':32,'max_calls_per_file':20000,'max_cumulative_requested_write_bytes':4096*20000,'max_acknowledged_bytes':2560000,'new_heap_allocations_observed':0,'new_reservation_or_debit_cap_increased':False,'existing_analyzer_or_VM_budget_debit_or_integration_claimed':False,'proof_requires_independent_actual_source_review':True}
    assert union<65536
    (P/'accounting.json').write_text(json.dumps(record,indent=2)+'\n');return record
if __name__=='__main__':r=build();print(r['conservative_whole_union_bytes'],r['source_work_upper_bound'])
