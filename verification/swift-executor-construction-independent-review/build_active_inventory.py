#!/usr/bin/env python3
"""Extend the independent positive accounting proposal to authored helpers."""
from pathlib import Path
import sys
out=Path(__file__).resolve().parent
base=(out/'build_preflight_inventory.py').read_text()
override='''
selectors=[
 ('state_empty',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:881:1:.*>::empty\\(',None),
 ('state_unpublished_cleanup',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:881:1:.*>::cleanup_unpublished\\(',None),
 ('state_drop_arenas',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:881:1:.*>::drop_arenas\\(',None),
 ('state_construct',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:961:1:.*>::construct\\(',None),
 ('state_construct_partial',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:961:1:.*>::construct_partial\\(',None),
 ('state_reserve_value',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:961:1:.*>::reserve\\(',None),
 ('state_reserve_control',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:961:1:.*>::reserve\\(',None),
 ('state_reserve_frame',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:961:1:.*>::reserve\\(',None),
 ('state_reserve_memory',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:961:1:.*>::reserve\\(',None),
 ('state_reserve_table',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:961:1:.*>::reserve\\(',None),
 ('state_segments',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:961:1:.*>::initialize_segments\\(',None),
 ('state_range',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:961:1:.*>::range\\(',None),
 ('state_segment_failure',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:961:1:.*>::segment_failure\\(',None),
 ('state_phase_complete',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:961:1:.*>::complete\\(',None),
 ('reader_failure',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:1249:1:.*>::failure\\(',None),
 ('reader_byte',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:1249:1:.*>::byte\\(',None),
 ('reader_unsigned',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:1249:1:.*>::unsigned\\(',None),
 ('reader_signed',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:1249:1:.*>::signed\\(',None),
 ('reader_constant',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:1249:1:.*>::constant\\(',None),
 ('reader_end',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:1249:1:.*>::end\\(',None),
 ('composed_construct',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:1430:1:.*>::construct\\(',None),
 ('partial_construct',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:1602:1:.*>::construct\\(',None),
 ('partial_cleanup_failed',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:1602:1:.*>::cleanup_failed\\(',None),
 ('work',r'^work\\(',None),
 ('arenas_formula',r'^arena_bytes\\(',None),
 ('control_admit',r'^control::<impl .*>::admit_with_wasi\\(',None),
 ('control_exact',r'^control::<impl .*>::exact_capacity_with_wasi\\(',None),
 ('control_work',r'^control::<impl .*>::work_with_wasi\\(',None),
 ('control_add_live',r'^control::<impl .*>::add_live_with_wasi\\(',None),
 ('control_remove_live',r'^control::<impl .*>::remove_live_with_wasi\\(',None),
 ('control_live_parts',r'^control::<impl .*>::live_parts\\(',None),
 ('control_live_mut',r'^control::<impl .*>::live_mut\\(',None),
 ('control_refund',r'^control::<impl .*>::refund_with_wasi\\(',None),
 ('drop_value',r'^control::<impl .*>::drop_reserved_with_wasi\\(',None),
 ('drop_control',r'^control::<impl .*>::drop_reserved_with_wasi\\(',None),
 ('drop_frame',r'^control::<impl .*>::drop_reserved_with_wasi\\(',None),
 ('drop_memory',r'^control::<impl .*>::drop_reserved_with_wasi\\(',None),
 ('drop_table',r'^control::<impl .*>::drop_reserved_with_wasi\\(',None),
 ('drop_state',r'^control::<impl .*>::drop_reserved_with_wasi\\(',None),
 ('control_cleanup_fault',r'^control::<impl .*>::cleanup_fault_with_wasi\\(',None),
]
specializations={'state_reserve_value':'Value','state_reserve_control':'Control','state_reserve_frame':'SwiftFrame','state_reserve_memory':'u8','state_reserve_table':'Option<u32>','state_phase_complete':'Option<Result<SwiftExecutionState,SwiftRunFailure>>','drop_value':'Vec<Value>','drop_control':'Vec<Control>','drop_frame':'Vec<SwiftFrame>','drop_memory':'Vec<u8>','drop_table':'Vec<Option<u32>>','drop_state':'SwiftExecutionState'}
'''
base=base.replace("ty=ty.replace(\"'_\",\"'static\")","ty=re.sub(r'(?<![\\w:])TryReserveError\\b','std::collections::TryReserveError',ty)\n    ty=ty.replace(\"'_\",\"'static\")")
base=base.replace('selected=[]',override+'\nselected=[]')
base=base.replace("'type':rust_type(ty)","'type':re.sub(r'\\bT\\b',specializations.get(role,'()'),rust_type(ty))")
base=base.replace("'PreflightSupplement'","'ActiveSupplement'")
base=base.replace('ConstructionPreflightSupplement','ConstructionActiveSupplement')
base=base.replace('CONSTRUCTION_PREFLIGHT_SUPPLEMENT_BYTES','CONSTRUCTION_ACTIVE_SUPPLEMENT_BYTES')
base=base.replace('independent_preflight_supplement_probe','independent_active_supplement_probe')
base=base.replace('isupplement','iactive')
base=base.replace("'preflight-supplement.rs'","'active-supplement.rs'")
base=base.replace("'preflight-supplement-map.json'","'active-supplement-map.json'")
base=base.replace('mixer-swift-construction-independent-preflight-supplement-v1','mixer-swift-construction-independent-active-supplement-v1')
base=base.replace('if cutoff is not None and n>cutoff:continue','if ty == \"!\":continue\n        if cutoff is not None and n>cutoff:continue')
exec(compile(base,str(out/'build_preflight_inventory.py'),'exec'))
