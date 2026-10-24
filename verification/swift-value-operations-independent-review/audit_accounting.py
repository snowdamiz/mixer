#!/usr/bin/env python3
"""Materialize the independently reviewed path/position association for a seal."""
from pathlib import Path
import hashlib, json, sys, tarfile

HERE=Path(__file__).resolve().parent
OUT=Path(sys.argv[1]).resolve()
encode=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
binding=json.loads((OUT/'inputs/producer-binding-map.json').read_text())
with tarfile.open(OUT/'candidate-source.tar.gz') as tf:
    source={name:tf.extractfile('vm/'+name).read().decode() for name in [
        'src/experimental_swift_reactor/value_operations.rs',
        'src/experimental_swift_reactor/execution.rs',
        'src/experimental/execution/borrowed.rs',
        'src/execute.rs','src/float.rs',
        'src/experimental_swift_reactor/cache.rs',
        'src/experimental_swift_reactor/control.rs','src/experimental/swift.rs']}
def anchor(path,needle):
    text=source[path];assert needle in text
    return dict(file='vm/'+path,line=text[:text.index(needle)].count('\n')+1,source=needle)
op='src/experimental_swift_reactor/value_operations.rs'
groups={
 'prepare':dict(meaning='New original-owner arguments/reborrows, provenance calls, usage checks, ticket loop and pre-enlargement failure/return window. Actual unchanged called-helper internals retain their previously accepted owner reservation.',
                anchors=[anchor(op,'pub(crate) fn prepare_value_operation('),anchor('src/experimental_swift_reactor/cache.rs','pub(crate) fn check_owner(')]),
 'prepare_bound':dict(meaning='Constant lookup, checked addition and exact previous-bound retention; no named-row traversal runs before admission. Full phase Result/Option source, return, caller and match objects remain positively charged.',
                      anchors=[anchor(op,'const VALUE_OPERATION_BYTES:'),anchor(op,'let previous_bound = control')]),
 'complete':dict(meaning='Consumed actual phase, destructured parts/operation, fixed actual supplied return storage and complete clear/restore results. Supplied parts/storage are destroyed before restoration; returned results remain covered after restoration.',
                 anchors=[anchor(op,'pub(crate) fn complete_values('),anchor('src/experimental_swift_reactor/control.rs','pub(crate) fn end_construction_phase_with_wasi<T>(')]),
 'caller_retention':dict(meaning='Actual caller preparation/outcome slots and retained copied failure/value/usage/WASI diagnostics remain in the permanent header until final consuming cleanup. This covers the bounded caller contract, not arbitrary external collections.',
                         anchors=[anchor(op,'pub(crate) struct ValueOperationStorage'),anchor('src/experimental_swift_reactor/execution.rs','fn drop_cleanup_return_storage<T>(')]),
 'operation_common':dict(meaning='Additional phase/parts/operation/arena reborrows, helper result transfers, actual WASI/fault/failure objects and new work/live caller positions. No existing owner payload, Frozen row or interior padding is used as credit.',
                         anchors=[anchor(op,'fn primitive_values_match('),anchor(op,'fn primitive_invariant('),anchor(op,'fn primitive_clear(')]),
 'push_pop':dict(meaning='Frame operand-base selection, push input and real popped result/Option transfers, work and admission arguments, capacity and limit faults. All new source/return/caller wrappers are counted as their complete actual types.',
                 anchors=[anchor(op,'pub(crate) fn push_value('),anchor(op,'fn primitive_push('),anchor(op,'fn primitive_pop(')]),
 'policy':dict(meaning='Distinct original-cache, adopted-proof, validated-proof and policy receiver/return chains for the sealed 128 operand limit; none is a replacement owner or ticket.',
               anchors=[anchor(op,'let operand_limit = self.parts.cache.proof()'),anchor('src/experimental_swift_reactor/cache.rs','pub(crate) fn proof(&self)'),anchor('src/experimental_swift_reactor/control.rs','impl AdoptedProof'),anchor('src/experimental/swift.rs','pub(crate) fn decode_policy')]),
 'numeric_owner':dict(meaning='Opcode admission precedes partial shape helpers; shape/type/count/bounds, actual-before/after reduction, raw helper Result and trap diagnostics coexist through live reconciliation. Work is count+1; no primitive instruction-fuel debit.',
                      anchors=[anchor(op,'fn primitive_numeric(')]),
 'primitive':dict(meaning='New Swift call windows for the literal shared arithmetic body: helper/arena arguments and returns, actual integer and floating shapes/scalars/pop/conversion/push wrappers. All nested roles add positive typed fields; no Frozen 512-byte component is borrowed.',
                 anchors=[anchor('src/experimental/execution/borrowed.rs','pub(crate) fn numeric<M:'),anchor('src/execute.rs','pub(crate) fn numeric(o:'),anchor('src/float.rs','pub(crate) fn numeric(op:')]),
 'primitive_nan':dict(meaning='Separate seven-element bit windows for a/b/bits plus arithmetic_nan source/argument/return/caller, retained in addition to the non-NaN primitive scalar fields.',
                     anchors=[anchor('src/float.rs','fn arithmetic_nan32('),anchor('src/float.rs','fn arithmetic_nan64(')]),
 'truncated':dict(meaning='Actual Result<Value,&str>/Try/residual and Value transfers, x/n/bits/signed/saturating parameters, four concrete Range<f64> branches with distinct range/item references and contains/negation results. i128/u128 proxy shapes were removed.',
                 anchors=[anchor('src/float.rs','fn truncated('),anchor('src/float.rs','pub(crate) fn saturating(')]),
 'try':dict(meaning='Actual compiler Try ControlFlow success/residual wrappers at new call sites; these do not alias a Result<(),Failure>, raw failure, or a different numeric success payload.',
           anchors=[anchor(op,'fn primitive_push('),anchor(op,'fn primitive_pop('),anchor(op,'fn primitive_numeric(')]),
}

def category(inventory,name):
    if inventory=='PermanentPositions':
        if name.startswith('completion_'):return 'complete'
        if name.startswith(('caller_','retained_')):return 'caller_retention'
        if name.startswith(('previous_','bound_','phase_constant_','enlarged_','enlargement_','preparation_')):return 'prepare_bound'
        return 'prepare'
    if name.startswith('truncated_'):return 'truncated'
    if name.startswith('primitive_nan'):return 'primitive_nan'
    if name.startswith(('unit_try_','unit_residual_')):return 'try'
    if name.startswith(('primitive_results_','work_results_','live_results_')):return 'operation_common'
    if name.startswith('primitive_'):return 'primitive'
    if name.startswith(('proof_','policy_')):return 'policy'
    if name.startswith(('frame_option','operand_base','operand_limit','input_value','pop_value','push_','pop_','scalar_capacity','checked_operand')):return 'push_pop'
    if name.startswith(('shape_','saturating_','opcode_','before','removed_','work_credits','available_','count_','type_','unsupported_','operand_type','numeric_','range_')):return 'numeric_owner'
    return 'operation_common'

site_maps={
 'preflight_unit_try_source_return_caller':(['cache-owner','header-owner','buffer-ticket-owner','enlarge-construction'],['source','return','caller']),
 'preflight_unit_residual_source_argument_parameter':(['cache-owner','header-owner','buffer-ticket-owner','enlarge-construction'],['source','argument','parameter']),
 'unit_try_source_return_caller':(['push.work','push.values-match','push.add-live','pop.work','pop.values-match','pop.remove-live','numeric.values-match','numeric.work','numeric.remove-live'],['source','return','caller']),
 'unit_residual_source_argument_parameter':(['push.work','push.values-match','push.add-live','pop.work','pop.values-match','pop.remove-live','numeric.values-match','numeric.work','numeric.remove-live'],['source','argument','parameter']),
 'work_component_source_argument_parameter':(['push.work','pop.work','numeric.work'],['source','argument','parameter']),
 'live_resource_source_argument_parameter':(['push.add-live','pop.remove-live','numeric.remove-live','clear.remove-live'],['source','argument','parameter']),
 'primitive_div_residual_source_argument_parameter':(['i32-checked-div','i64-checked-div'],['source','argument','parameter']),
 'truncated_range_source_argument_parameter':(['i32-signed','i32-unsigned','i64-signed','i64-unsigned'],['source','argument','parameter']),
 'truncated_n_source_argument_parameter':(['i32-signed','i32-unsigned','i64-signed','i64-unsigned'],['source','argument','parameter']),
 'truncated_contains_return_caller_negation':(['i32-signed','i32-unsigned','i64-signed','i64-unsigned'],['return','caller','negation']),
 'primitive_nan32_bits':(['a','b','bits','nan-source','nan-argument','nan-return','nan-caller'],['position']),
 'primitive_nan64_bits':(['a','b','bits','nan-source','nan-argument','nan-return','nan-caller'],['position']),
}
positions=[]
for row in binding['positions']:
    group=category(row['inventory'],row['name'])
    actual=[dict(x) for x in row['typedPositions']]
    if row['name'] in site_maps:
        sites,roles=site_maps[row['name']]
        assert len(actual)==len(sites)*len(roles)
        for index,item in enumerate(actual):
            item['actualCallSite']=sites[index//len(roles)]
            item['transferRole']=roles[index%len(roles)]
    positions.append(dict(inventory=row['inventory'],field=row['name'],shape=row['declaredShape'],bytes=row['bytes'],offset=row['offset'],
                          reviewedPath=group,declarationFile=row['declarationFile'],declarationLine=row['declarationLine'],positions=actual))
assert len(positions)==binding['fields'] and sum(len(x['positions']) for x in positions)==binding['typedPositions']
assert not any('i128' in x['shape'] or 'u128' in x['shape'] for x in positions)
required=['Result<Value,', 'Result<i32,', 'Result<i64,','Range<f64>','Option<(Type, usize, Type)>','ControlFlow','Option<&\'static SwiftFrame>','ValidatedSwiftReactor','CacheControl']
for shape in required:assert any(shape in x['shape'] for x in positions),shape
result=dict(schema=1,status='source-path-association-reviewed-pending-final-evidence-decision',sourceTreeSHA256=binding['sourceTreeSHA256'],
            fields=binding['fields'],typedPositions=binding['typedPositions'],groups=groups,positions=positions,
            invariant='All new positions are positive complete typed fields and disjoint compiled offsets; no aliases, containing/interior padding credit, old failure slots or arbitrary residual subtraction.',
            existingCallees='Unchanged internal helper windows remain covered by their still-charged original control/cache/WASI owners. This new route separately covers its arguments, receivers, returned values, Try wrappers and retained caller diagnostics. It adds no recursive or overlapping helper depth beyond accepted existing routes.',
            scope='Named authored/requested storage association; not physical stack, RSS, arbitrary external caller storage, a native-device run or OTA authorization.')
(OUT/'accounting-audit.json').write_bytes(encode(result))
print(json.dumps({k:result[k] for k in ['status','sourceTreeSHA256','fields','typedPositions']},indent=2))
