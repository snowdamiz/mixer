// Appended only to isolated Swift execution module. Never activates its owner.
use crate::experimental::execution::borrowed::algorithm_contract_probe::{AlgorithmMode,
    FrameScalars, PinAttempt};
pub(crate) struct SwiftGrowthContext<'a> {
    pub memory_ticket: &'a mut Option<ReservationTicket>,
}
impl AlgorithmMode for SwiftMode {
    type ReleaseFailure = SwiftReleaseFailure;
    type Growth<'a> = SwiftGrowthContext<'a>;
    fn frame(frame: &SwiftFrame) -> FrameScalars {
        FrameScalars { function: frame.function, pc: frame.pc, base: frame.base,
            operands: frame.operands, controls: frame.controls, result: frame.result }
    }
    fn frame_pin(frame: &SwiftFrame) -> &SwiftFunctionPin { &frame.pin }
    fn set_pc(frame: &mut SwiftFrame, pc: usize) { frame.pc = pc; }
    fn view<'cache>(cache: &'cache SwiftFunctionCache, pin: &SwiftFunctionPin,
        operation: &mut SwiftExecutionOperation<'_>) -> Result<FunctionView<'cache>, SwiftRunFailure> {
        cache.view(pin, &mut *operation.control, Some(&*operation.wasi))
    }
    fn check(operation: &mut SwiftExecutionOperation<'_>) -> Result<(), SwiftRunFailure> {
        let observed = Some(operation.wasi.checked_usage(operation.control, operation.cursor)?);
        operation.control.check_with_wasi(operation.cursor, observed)
    }
    fn work(operation: &mut SwiftExecutionOperation<'_>, credits: usize) -> Result<(), SwiftRunFailure> {
        let observed = Some(operation.wasi.checked_usage(operation.control, operation.cursor)?);
        operation.control.work_with_wasi(Work::Execution, credits as u64, operation.cursor, observed)
    }
    fn invariant(operation: &mut SwiftExecutionOperation<'_>) -> SwiftRunFailure {
        let observed = match operation.wasi.checked_usage(operation.control, operation.cursor) {
            Ok(observed) => Some(observed), Err(failure) => return failure,
        };
        operation.control.fail(operation.cursor,
            Fault::new(SwiftRunFailureKind::Invariant, "shared_type_probe_invariant"), observed)
    }
    fn release(cache: &mut SwiftFunctionCache, pin: SwiftFunctionPin,
        operation: &mut SwiftExecutionOperation<'_>) -> Result<(), SwiftReleaseFailure> {
        cache.release(pin, &mut *operation.control, Some(&*operation.wasi))
    }
    fn split_release(error: SwiftReleaseFailure, _: &mut SwiftExecutionOperation<'_>) -> (SwiftRunFailure, SwiftFunctionPin) {
        let failure = error.failure;
        (failure, error.into_pin())
    }
}
/// Shows the six vectors and memory ticket have independent mutable borrows.
fn shared_growth_split<'a>(cache: &'a mut SwiftFunctionCache,
    state: &'a mut SwiftExecutionState) ->
    (ExecutionParts<'a, SwiftMode>, SwiftGrowthContext<'a>) {
    let SwiftExecutionState {memory,table,globals,values,controls,frames,buffers,..} = state;
    (ExecutionParts {cache,memory,table,globals,values,controls,frames},
        SwiftGrowthContext { memory_ticket: &mut buffers[3] })
}
/// Exact nested completion: move pin out, consume returned Option<Result>, then
/// return BOTH retained pin and completion failure. No pin is lost on `?`.
fn shared_pin_phase_borrow(cache: &mut SwiftFunctionCache,
    operation: &mut SwiftExecutionOperation<'_>, function: u32) -> PinAttempt<SwiftMode> {
    let mut phase = match cache.prepare_operation(&mut *operation.control,
        Some(&*operation.wasi), operation.cursor) {
        Ok(phase) => phase,
        Err(failure) => return PinAttempt { pin: None, failure: Some(failure) },
    };
    let mut returned = Some(phase.pin(cache, function));
    let attempt: PinAttempt<SwiftMode> = match returned.take().expect("just populated") {
        Ok(pin) => PinAttempt { pin: Some(pin), failure: None },
        Err(failure) => PinAttempt { pin: None, failure: Some(failure) },
    };
    let completed = phase.complete(returned);
    let failure = attempt.failure.or_else(|| completed.err());
    PinAttempt { pin: attempt.pin, failure }
}
/// Typed argument slice and guest memory are disjoint; cache phase has ended.
fn shared_host_split(parts: &mut ExecutionParts<'_, SwiftMode>,
    operation: &mut SwiftExecutionOperation<'_>, function: u32, base: usize)
    -> Result<Option<Value>, SwiftRunFailure> {
    let wasi_function = *parts.cache.proof().execution_imports().get(function as usize)
        .ok_or_else(|| SwiftMode::invariant(operation))?;
    let arguments = &parts.values[base..];
    let errno = operation.wasi.dispatch(operation.control, wasi_function, arguments,
        parts.memory, operation.cursor)?;
    Ok(Some(Value::I32(errno as u16 as i32)))
}
fn shared_phase_reborrow(phase: &mut ExecutionOperationPhase<'_>) {
    with_cache_operation(phase, |parts, operation| {
        let _ = crate::experimental::execution::borrowed::algorithm_contract_probe::numeric_signature::<SwiftMode>(parts, operation, 0, false);
    });
}
#[cfg(test)]
mod shared_algorithm_contract_swift_tests {
    use super::*;
    use crate::experimental::execution::borrowed::algorithm_contract_probe::*;
    #[test]
    fn shared_algorithm_contract_swift_bindings() {
        let _ = numeric_signature::<SwiftMode>;
        let _ = selected_view_borrow::<SwiftMode>;
        let _ = enter_signature::<SwiftMode>;
        let _ = run_signature::<SwiftMode>;
        let _ = finish_signature::<SwiftMode>;
        let _ = unwind_signature::<SwiftMode>;
        let _ = shared_growth_split;
        let _ = shared_pin_phase_borrow;
        let _ = shared_host_split;
        let _ = shared_phase_reborrow;
        assert_eq!(std::mem::size_of::<SwiftMode>(), 0);
    }
    #[test]
    fn shared_algorithm_contract_swift_layouts() {
        println!("SwiftGrowthContext size={} align={}", size_of::<SwiftGrowthContext<'_>>(), std::mem::align_of::<SwiftGrowthContext<'_>>());
        println!("PinAttempt<SwiftMode> size={} align={}", size_of::<PinAttempt<SwiftMode>>(), std::mem::align_of::<PinAttempt<SwiftMode>>());
        println!("Result<(),SwiftReleaseFailure> size={} align={}", size_of::<Result<(),SwiftReleaseFailure>>(), std::mem::align_of::<Result<(),SwiftReleaseFailure>>());
        assert_eq!(size_of::<SwiftGrowthContext<'_>>(), size_of::<&mut Option<ReservationTicket>>());
    }
}
