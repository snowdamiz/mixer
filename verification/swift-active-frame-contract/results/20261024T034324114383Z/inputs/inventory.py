"""Concrete additive contract inventory. No accepted scratch/padding supplies credit.

Each family expands source/argument/return/caller/branch/residual positions into
separate real Rust fields. Fields across ALL windows are reserved simultaneously;
no lifetime exclusivity is used to reduce the total. This is a proposal inventory
for the specified future code, not proof of yet absent runtime bindings.
"""
def rows():
    result = []
    def add(envelope, window, binding, rust_type, positions):
        for position in positions.split():
            result.append(dict(envelope=envelope, window=window,
                binding=binding, position=position, rustType=rust_type,
                field=f'{window}_{binding}_{position}'))
    p = 'permanent'
    a = 'active'
    for binding, ty in [
        ('instance','SwiftReactorInstance'), ('state','SwiftExecutionState'),
        ('cleanup_state','FrameCleanupState'), ('cleanup_option','Option<EntryGuard>'),
        ('bound','Option<FrameBound>'), ('nested_bound','Option<usize>'),
    ]:
        add(p,'owner',binding,ty,'source argument return caller')
    for binding,ty in [
        ('owner','&\'static mut SwiftReactorInstance'),
        ('control','&\'static mut RuntimeControl'), ('cache','&\'static mut SwiftFunctionCache'),
        ('wasi','&\'static mut AccountedWasi'), ('state','&\'static mut SwiftExecutionState'),
        ('lifecycle','&\'static mut Lifecycle'), ('cleanup','&\'static mut FrameCleanupState'),
        ('ticket','&\'static ReservationTicket'), ('cursor','Cursor'),
        ('usage','SwiftRunUsage'), ('cache_usage','super::super::cache::SwiftCacheUsage'),
        ('wasi_usage','WasiUsage'), ('live','SwiftLiveUsage'), ('budget','SwiftRunBudget'),
        ('previous','usize'), ('admitted','usize'), ('byte_option','Option<usize>'),
        ('check','Result<(), SwiftRunFailure>'), ('fault','Fault'), ('failure','SwiftRunFailure'),
        ('ticket_option','Option<&\'static ReservationTicket>'),
        ('tickets_iterator','std::slice::Iter<\'static, Option<ReservationTicket>>'),
        ('ticket_option_borrow','&\'static Option<ReservationTicket>'),
        ('gate','bool'), ('disposition','FrameDisposition'),
    ]:
        add(p,'prepare',binding,ty,'source argument return caller')
    for binding,ty in [
        ('phase','FrameOperationPhase<\'static>'),
        ('phase_return','Result<FrameOperationPhase<\'static>, SwiftRunFailure>'),
        ('phase_option','Option<Result<FrameOperationPhase<\'static>, SwiftRunFailure>>'),
        ('storage','FrameOperationStorage<\'static>'),
        ('completion','FrameCompletion'), ('report','FrameDrainReport'),
        ('report_option','Option<FrameDrainReport>'), ('bound','FrameBound'),
        ('parts','ExecutionParts<\'static, SwiftMode>'),
        ('operation','SwiftExecutionOperation<\'static>'),
        ('first_failure','Option<SwiftRunFailure>'), ('usage','SwiftRunUsage'),
        ('wasi','Option<WasiUsage>'), ('restore','Result<(), SwiftRunFailure>'),
        ('empty','bool'), ('previous','usize'), ('remaining','usize'),
    ]:
        add(p,'completion',binding,ty,'source argument return caller')
    for binding,ty in [
        ('step_entry','Option<Result<(), SwiftRunFailure>>'),
        ('step_return','Option<Result<FrameReturn, SwiftRunFailure>>'),
        ('completion_option','Option<FrameCompletion>'),
        ('final_failure','Option<SwiftRunFailure>'), ('final_usage','Option<SwiftRunUsage>'),
        ('cleanup_tail','ExecutionCleanupTail'),
        ('cleanup_result','Option<Result<ExecutionCleanupTail, SwiftRunFailure>>'),
    ]:
        add(p,'after',binding,ty,'source argument return caller')
    for window in ['prepare','completion']:
        for binding,ty in [
            ('try_branch','ControlFlow<Result<Infallible, SwiftRunFailure>, ()>'),
            ('try_residual','Result<Infallible, SwiftRunFailure>'),
        ]:
            add(p,window,binding,ty,'source return caller')
    # Active caller/callee windows are distinct even where the underlying cache
    # already has its own separately admitted internal implementation inventory.
    for binding,ty in [
        ('phase','&\'static mut FrameOperationPhase<\'static>'),
        ('parts','ExecutionParts<\'static, SwiftMode>'),
        ('parts_borrow','&\'static mut ExecutionParts<\'static, SwiftMode>'),
        ('operation','SwiftExecutionOperation<\'static>'),
        ('operation_borrow','&\'static mut SwiftExecutionOperation<\'static>'),
        ('control','&\'static mut RuntimeControl'), ('wasi','&\'static AccountedWasi'),
        ('values','&\'static mut Vec<Value>'), ('controls','&\'static mut Vec<Control>'),
        ('frames','&\'static mut Vec<SwiftFrame>'), ('cache','&\'static mut SwiftFunctionCache'),
        ('usage','SwiftRunUsage'), ('observation','Option<WasiUsage>'), ('cursor','Cursor'),
        ('live','SwiftLiveUsage'), ('fault','Fault'), ('failure','SwiftRunFailure'),
        ('unit_result','Result<(), SwiftRunFailure>'), ('gate','bool'),
    ]:
        add(a,'common',binding,ty,'source argument return caller')
    for binding,ty in [
        ('phase','CacheOperationPhase<\'static>'),
        ('prepare_result','Result<CacheOperationPhase<\'static>, SwiftRunFailure>'),
        ('prepare_option','Option<Result<CacheOperationPhase<\'static>, SwiftRunFailure>>'),
        ('pin','SwiftFunctionPin'), ('pin_option','Option<SwiftFunctionPin>'),
        ('pin_result','Result<SwiftFunctionPin, SwiftRunFailure>'),
        ('pin_return_slot','Option<Result<SwiftFunctionPin, SwiftRunFailure>>'),
        ('attempt','PinAttempt'), ('first','Option<SwiftRunFailure>'),
        ('nested_restore','Option<usize>'), ('frame_bound','usize'),
        ('completion','Result<(), SwiftRunFailure>'), ('function','u32'),
        ('empty_pair','(Option<Result<CacheOperationPhase<\'static>, SwiftRunFailure>>, Option<Result<SwiftFunctionPin, SwiftRunFailure>>)'),
    ]:
        add(a,'acquire',binding,ty,'source argument return caller')
    for binding,ty in [
        ('guard','EntryGuard'), ('guard_option','Option<EntryGuard>'),
        ('guard_borrow','&\'static mut EntryGuard'), ('signature','SignatureView<\'static>'),
        ('signature_option','Option<SignatureView<\'static>>'), ('view','FunctionView<\'static>'),
        ('view_result','Result<FunctionView<\'static>, SwiftRunFailure>'),
        ('params','usize'), ('locals','usize'), ('total_locals','Option<usize>'),
        ('base','usize'), ('base_option','Option<usize>'), ('end','usize'),
        ('end_option','Option<usize>'), ('operands','usize'), ('control_base','usize'),
        ('frame_count','usize'), ('frame_limit','usize'), ('control_limit','usize'),
        ('value_capacity','usize'), ('control_capacity','usize'), ('frame_capacity','usize'),
        ('local_index','usize'), ('type_borrow','Option<&\'static Type>'),
        ('ty','Type'), ('value','Value'), ('function_control','Control'),
        ('frame','SwiftFrame'), ('scalars','FrameScalars'), ('debit','Live'),
        ('work','usize'), ('work_option','Option<usize>'), ('work_u64','u64'),
        ('debit_result','Result<(), SwiftRunFailure>'), ('checked_result','Result<(), SwiftRunFailure>'),
        ('pin','Option<SwiftFunctionPin>'), ('result','Result<(), SwiftRunFailure>'),
    ]:
        add(a,'entry',binding,ty,'source argument return caller')
    for binding,ty in [
        ('frame_borrow','Option<&\'static SwiftFrame>'), ('scalars','FrameScalars'),
        ('saved','Option<Value>'), ('saved_value','Value'), ('pop','Result<Value, SwiftRunFailure>'),
        ('value_len','usize'), ('control_len','usize'), ('base','usize'), ('control_base','usize'),
        ('work','Option<usize>'), ('value_delta','usize'), ('control_delta','usize'),
        ('frame','SwiftFrame'), ('frame_option','Option<SwiftFrame>'),
        ('pin','SwiftFunctionPin'), ('release','Result<(), SwiftReleaseFailure>'),
        ('rejected','SwiftReleaseFailure'), ('restored_frame','SwiftFrame'),
        ('push','Result<(), SwiftRunFailure>'), ('result','Result<FrameReturn, SwiftRunFailure>'),
        ('returned','FrameReturn'),
    ]:
        add(a,'finish',binding,ty,'source argument return caller')
    for binding,ty in [
        ('guard','EntryGuard'), ('guard_option','Option<EntryGuard>'),
        ('guard_pin','Option<SwiftFunctionPin>'), ('release','Result<(), SwiftReleaseFailure>'),
        ('rejected','SwiftReleaseFailure'), ('rejected_pin','SwiftFunctionPin'),
        ('values_actual','usize'), ('controls_actual','usize'), ('value_debit','usize'),
        ('control_debit','usize'), ('frame_debit','bool'), ('removal','Result<(), SwiftRunFailure>'),
    ]:
        add(a,'rejection',binding,ty,'source argument return caller')
    for binding,ty in [
        ('cleanup','&\'static mut FrameCleanupState'), ('unvisited','&\'static mut usize'),
        ('index','usize'), ('frame','SwiftFrame'), ('scalars','FrameScalars'),
        ('pin','SwiftFunctionPin'), ('release','Result<(), SwiftReleaseFailure>'),
        ('rejected','SwiftReleaseFailure'), ('restored_pin','SwiftFunctionPin'),
        ('restored_frame','SwiftFrame'), ('first','Option<SwiftRunFailure>'),
        ('value_len','usize'), ('control_len','usize'), ('live_before','SwiftLiveUsage'),
        ('live_after','SwiftLiveUsage'), ('cache_before','super::super::cache::SwiftCacheUsage'),
        ('cache_after','super::super::cache::SwiftCacheUsage'), ('report','FrameDrainReport'),
        ('remaining','usize'), ('removed','Result<(), SwiftRunFailure>'),
    ]:
        add(a,'drain',binding,ty,'source argument return caller')
    for window in ['entry','finish','rejection','drain']:
        for binding,ty in [
            ('try_branch_unit','ControlFlow<Result<Infallible, SwiftRunFailure>, ()>'),
            ('try_branch_value','ControlFlow<Result<Infallible, SwiftRunFailure>, Value>'),
            ('try_branch_usize','ControlFlow<Result<Infallible, SwiftRunFailure>, usize>'),
            ('try_residual','Result<Infallible, SwiftRunFailure>'),
            ('closure_capture','(&\'static mut RuntimeControl, &\'static AccountedWasi, Cursor)'),
            ('closure_failure','SwiftRunFailure'),
        ]:
            add(a,window,binding,ty,'source argument return caller')
    return result

def render():
    output=[]
    for envelope,name in [('permanent','PermanentPositions'),('active','ActivePositions')]:
        output.append(f'struct {name} {{')
        output += [f'    {r["field"]}: {r["rustType"]},' for r in rows() if r['envelope']==envelope]
        output.append('}')
    output += ['pub(super) const PERMANENT_BYTES: usize = size_of::<PermanentPositions>();',
               'pub(super) const ACTIVE_BYTES: usize = size_of::<ActivePositions>();']
    return '\n'.join(output)

def print_fields():
    output=[]
    for r in rows():
        owner='PermanentPositions' if r['envelope']=='permanent' else 'ActivePositions'
        output.append('println!("AF_FIELD '+r['field']+' {} {} {}", std::mem::offset_of!('+owner+', '+r['field']+'), size_of::<'+r['rustType']+'>(), std::mem::align_of::<'+r['rustType']+'>());')
    return '\n'.join(output)
