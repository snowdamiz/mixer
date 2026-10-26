#!/usr/bin/env python3
from pathlib import Path
import json

OUT=Path(__file__).resolve().parent
def write(name,j):(OUT/name).write_text(json.dumps(j,indent=2,sort_keys=True)+'\n')
def main():
    selected=json.loads((OUT/'inputs/root/selected-host-budget.json').read_text())
    budget=selected['budget'];order=selected['field_order'];records=[]
    def add(name,changes,expect):
        record=dict(budget);record.update(changes)
        records.append({'id':name,'budget':record,'expected_scope':expect,'altered_fields':list(changes)})
    add('selected-complete17',{},'Exact root-selected component record; no historical full-target replay')
    for field in order:add('drift-'+field,{field:budget[field]-1},'Actual budget differs from selected record; wrapper SelectionRefused before prepare')
    add('test-selected-zero-slots',{'cache_entries':0},'Separate explicit test selection; VM construction may succeed, profile slots unsupported; no clamping')
    add('test-selected-zero-pins',{'active_pins':0},'Separate explicit test selection; VM construction may succeed, profile pins unsupported; no clamping')
    add('test-selected-entry-zero',{'cache_entry_bytes':0},'Separate explicit test selection; header meaningful if constructor succeeds and B<=capacity')
    add('test-selected-entry-above-capacity',{'cache_bytes':1048576,'cache_entry_bytes':2097152},'Separate explicit test selection; header meaningful if constructor succeeds and B<=capacity; entry limit exceeds cache capacity')
    add('test-selected-cache-below-fixed-B',{'cache_bytes':1},'Separate explicit test selection; preserve actual constructor capacity failure; no header success')
    add('test-selected-zero-source',{'source_bytes':0},'Separate explicit test selection; actual validation/adoption may fail earlier; no universal nonzero-budget rule')
    write('test-budget-records.json',{'schema':1,'field_order':order,'records':records,
      'scope':'Complete proposed records for finite future Rust tests only; only selected-complete17 is root-selected production-component input',
      'all_values_to_be_explicit_in_future_named_Rust_test_source':True,'executed_as_runtime_tests':False})
    variants=[
      (1,'SlotOccupied',{'adopted':'AdoptedProof'},'not-attempted','not-attempted','not-attempted','not-attempted','preexisting slot untouched; adopted returned'),
      (2,'SelectionRefused',{'error':'ProfileHeaderErrorV1','adopted':'AdoptedProof'},'not-attempted','not-attempted','not-attempted','not-attempted','adopted returned'),
      (3,'PreparationFailed',{'failure':'SwiftRunFailure','adopted':'AdoptedProof'},'not-attempted-prepare-failed','not-attempted','not-attempted','not-attempted','adopted returned'),
      (4,'ConstructionFailed',{'failure':'CacheConstructionFailure','completion':'Result<(),SwiftRunFailure>'},'failed','original-result','not-attempted','not-attempted','original optional rejected_adopted retained'),
      (5,'PhaseCompletionFailed',{'failure':'SwiftRunFailure'},'succeeded','failed','not-attempted','not-attempted','cache_out Some'),
      (6,'HeaderRefused',{'error':'ProfileHeaderErrorV1'},'succeeded','succeeded','failed-profile','not-attempted','cache_out Some'),
      (7,'HeaderOwnerCheckFailed',{'failure':'SwiftRunFailure'},'succeeded','succeeded','failed-original-runtime','not-attempted','cache_out Some'),
      (8,'HeaderEncoded',{'header':'UnverifiedProfileHeaderV1','rows':'Result<ProfileRowsObservationV1,ProfileAdapterErrorV1>'},'succeeded','succeeded','succeeded','original-result','cache_out Some')]
    write('protocol.json',{'schema':1,'status':'proposed-for-root-and-independent-review','product_implementation_selected':False,
      'guard_constructor':'sole private struct literal in construct_with_initial_profile_v1 success branch after exact construction and completion',
      'wrapper_cursor':{'stage':'Initialization','function':None,'offset':None},'outcome_representation':'repr(u32), inline owned fields, no Clone/Copy',
      'variants':[{'tag':t,'name':n,'fields':f,'construction':c,'completion':p,'header':h,'rows':r,'ownership':o} for t,n,f,c,p,h,r,o in variants],
      'original_construction_return_slot':'Option<Result<SwiftFunctionCache,CacheConstructionFailure>>',
      'original_completion_storage':'(Option<Result<CacheConstructionPhase,SwiftRunFailure>>,ConstructionReturnSlot), both None after take',
      'runtime_failure_reclassification':False,'positive_cache_bytes_excluded':True,'zero_byte_cache_ticket_exclusivity':False,
      'wasi':'Optional supplied authentic common RuntimeControl owner; no historical instance identity',
      'row_owner':'initial.cache.proof() internally; no independent owner argument',
      'local_layout_comparison_executed':False,'external_build_attestation_inside_helper':False,
      'next_distribution_paths':140,'next_new_Rust_files':[
        'src/experimental_swift_reactor/cache/initial_profile_v1.rs',
        'src/experimental_swift_reactor/cache/initial_profile_v1/header.rs',
        'src/experimental_swift_reactor/cache/initial_profile_v1/selected.rs',
        'src/experimental_swift_reactor/cache/initial_profile_v1/local_structure.rs',
        'src/experimental_swift_reactor/cache/initial_profile_v1/tests.rs',
        'src/experimental_swift_reactor/cache/initial_profile_v1/compile_contracts.rs'],
      'future_host_runner':'verification/swift-initial-profile-construction-host/run_component.py',
      'future_fixed_compile_case_sources':['verification/swift-initial-profile-construction-host/compile_cases/'+n+'.rs' for n in ['positive_contract','guard_literal_from_sibling','guard_escape','proof_escape','cache_move','cache_mutation','control_mutation','row_foreign_snapshot','callback_reentry','external_selection_literal']],
      'future_distribution_plus_named_host_support_sources':151,
      'new_140_count_schema_or_product_or_runtime_or_GA_accepted':False})
    print(f'wrote 8 exact outcome variants and {len(records)} complete17-field proposed test records')
if __name__=='__main__':main()
