//! Isolated compilation probe. None of its algorithm callsites are executed.
#![allow(dead_code, clippy::result_large_err)]
use super::*;
use crate::experimental::cache::FunctionView;

#[derive(Clone, Copy)]
pub(crate) struct FrameScalars {
    pub function: u32,
    pub pc: usize,
    pub base: usize,
    pub operands: usize,
    pub controls: usize,
    pub result: bool,
}
/// Both fields are owned. Completion failure may coexist with a successful pin.
pub(crate) struct PinAttempt<M: AlgorithmMode> {
    pub pin: Option<M::Pin>,
    pub failure: Option<M::Failure>,
}
/// This inherits the existing private sealing; no trait object is constructed.
pub(crate) trait AlgorithmMode: ExecutionMode + Sized {
    type ReleaseFailure;
    type Growth<'a>;
    fn frame(frame: &Self::Frame) -> FrameScalars;
    fn frame_pin(frame: &Self::Frame) -> &Self::Pin;
    fn set_pc(frame: &mut Self::Frame, pc: usize);
    fn view<'cache>(cache: &'cache Self::Cache, pin: &Self::Pin,
        operation: &mut Self::Operation<'_>) -> Result<FunctionView<'cache>, Self::Failure>;
    fn check(operation: &mut Self::Operation<'_>) -> Result<(), Self::Failure>;
    fn work(operation: &mut Self::Operation<'_>, credits: usize) -> Result<(), Self::Failure>;
    fn invariant(operation: &mut Self::Operation<'_>) -> Self::Failure;
    fn release(cache: &mut Self::Cache, pin: Self::Pin,
        operation: &mut Self::Operation<'_>) -> Result<(), Self::ReleaseFailure>;
    fn split_release(error: Self::ReleaseFailure, operation: &mut Self::Operation<'_>) -> (Self::Failure, Self::Pin);
}

/// Compile a view reborrow, copy selected data, then mutate both cache and pc.
/// This is a borrow-topology witness, not the run/selection algorithm.
pub(crate) fn selected_view_borrow<M: AlgorithmMode>(
    parts: &mut ExecutionParts<'_, M>, operation: &mut M::Operation<'_>,
    replacement_pin: M::Pin,
) -> Result<(Option<super::super::super::cache::DecodedInstruction>,
             Option<u32>, Option<M::ReleaseFailure>), M::Failure> {
    let selected = {
        let frame = parts.frames.last().ok_or_else(|| M::invariant(operation))?;
        let scalars = M::frame(frame);
        let view = M::view(parts.cache, M::frame_pin(frame), operation)?;
        // Crucially Operation's mutable borrow has ended while the cache view lives.
        M::check(operation)?;
        let instruction = view.instructions.get(scalars.pc).copied();
        let selected_target = view.branch_targets.first().copied();
        (instruction, selected_target)
    };
    let release_error = M::release(parts.cache, replacement_pin, operation).err();
    if let Some(frame) = parts.frames.last_mut() { M::set_pc(frame, 0); }
    Ok((selected.0, selected.1, release_error))
}

/// Compilation only: these bind the common helper signature, with separate
/// owner and temporary-borrow lifetimes. The algorithm bodies remain pending.
pub(crate) fn numeric_signature<M: AlgorithmMode>(
    parts: &mut ExecutionParts<'_, M>, operation: &mut M::Operation<'_>,
    opcode: u8, saturating: bool,
) -> Result<(), M::Failure> {
    let frame = parts.frames.last().ok_or_else(|| M::invariant(operation))?;
    let scalars = M::frame(frame);
    let _disjoint_values = &mut *parts.values;
    M::work(operation, 0)?;
    let _ = (scalars, opcode, saturating);
    Ok(())
}
// These bodies intentionally diverge. No interpreter or target entry is added.
pub(crate) fn enter_signature<M: AlgorithmMode>(
    _: &mut ExecutionParts<'_, M>, _: u32, _: &mut M::Operation<'_>,
) -> Result<(), M::Failure> { unimplemented!("type-only signature") }
pub(crate) fn run_signature<M: AlgorithmMode>(
    _: &mut ExecutionParts<'_, M>, _: &mut M::Operation<'_>, _: &mut M::Growth<'_>,
) -> Result<Option<Value>, M::Failure> { unimplemented!("type-only signature") }
pub(crate) fn finish_signature<M: AlgorithmMode>(
    _: &mut ExecutionParts<'_, M>, _: &mut M::Operation<'_>,
) -> Result<Option<Value>, M::Failure> { unimplemented!("type-only signature") }
pub(crate) fn unwind_signature<M: AlgorithmMode>(
    _: &mut ExecutionParts<'_, M>, _: &mut M::Operation<'_>, _: &mut Option<M::Pin>,
) { unimplemented!("type-only signature") }

#[cfg(feature = "experimental-span-execution")]
impl AlgorithmMode for FrozenMode {
    type ReleaseFailure = super::super::super::cache::ReleaseFailure;
    type Growth<'a> = ();
    fn frame(frame: &Frame) -> FrameScalars {
        FrameScalars { function: frame.function, pc: frame.pc, base: frame.base,
            operands: frame.operands, controls: frame.controls, result: frame.result }
    }
    fn frame_pin(frame: &Frame) -> &FunctionPin { &frame.pin }
    fn set_pc(frame: &mut Frame, pc: usize) { frame.pc = pc; }
    fn view<'cache>(cache: &'cache FunctionCache, pin: &FunctionPin,
        operation: &mut FrozenOperation<'_>) -> Result<FunctionView<'cache>, ExecutionFailure> {
        cache.view(pin).map_err(|error| frozen_cache_failure(operation, error))
    }
    fn check(operation: &mut FrozenOperation<'_>) -> Result<(), ExecutionFailure> {
        if operation.cancellation.is_cancelled() { Err(frozen_failure(operation,
            ExecutionFailureKind::Cancelled, "cancelled", 0, 0)) } else { Ok(()) }
    }
    fn work(operation: &mut FrozenOperation<'_>, credits: usize) -> Result<(), ExecutionFailure> {
        Self::check(operation)?;
        let next = operation.usage.work_used.checked_add(credits as u64).ok_or_else(||
            frozen_failure(operation, ExecutionFailureKind::WorkExhausted, "work_overflow",
                u64::MAX, operation.budget.work_credits))?;
        if next > operation.budget.work_credits { return Err(frozen_failure(operation,
            ExecutionFailureKind::WorkExhausted, "execution_work", next,
            operation.budget.work_credits)); }
        operation.usage.work_used = next;
        Ok(())
    }
    fn invariant(operation: &mut FrozenOperation<'_>) -> ExecutionFailure {
        frozen_failure(operation, ExecutionFailureKind::Invariant, "execution_invariant", 0, 0)
    }
    fn release(cache: &mut FunctionCache, pin: FunctionPin,
        _: &mut FrozenOperation<'_>) -> Result<(), Self::ReleaseFailure> { cache.release(pin) }
    fn split_release(error: Self::ReleaseFailure, operation: &mut FrozenOperation<'_>) -> (ExecutionFailure, FunctionPin) {
        let failure = frozen_cache_failure(operation, error.failure);
        (failure, error.into_pin())
    }
}
#[cfg(feature = "experimental-span-execution")]
fn frozen_failure(operation: &FrozenOperation<'_>, kind: ExecutionFailureKind,
    code: &'static str, attempted: u64, limit: u64) -> ExecutionFailure {
    ExecutionFailure { kind, code, function: *operation.function, offset: *operation.offset,
        attempted, limit, usage: *operation.usage, cache_failure: None }
}
#[cfg(feature = "experimental-span-execution")]
fn frozen_cache_failure(operation: &FrozenOperation<'_>, error: CacheFailure) -> ExecutionFailure {
    let mut failure = frozen_failure(operation, ExecutionFailureKind::Cache, error.code,
        error.attempted, error.limit);
    if operation.function.is_none() { failure.function = error.function; failure.offset = error.offset; }
    failure.cache_failure = Some(error);
    failure
}
#[cfg(test)]
mod shared_algorithm_contract_tests {
    use super::*;
    #[cfg(feature = "experimental-span-execution")]
    #[test]
    fn shared_algorithm_contract_frozen_bindings() {
        let _ = numeric_signature::<FrozenMode>;
        let _ = selected_view_borrow::<FrozenMode>;
        let _ = enter_signature::<FrozenMode>;
        let _ = run_signature::<FrozenMode>;
        let _ = finish_signature::<FrozenMode>;
        let _ = unwind_signature::<FrozenMode>;
        let _: for<'a> fn(&'a mut SpanInstance) ->
            (ExecutionParts<'a, FrozenMode>, FrozenOperation<'a>) = frozen_parts;
        assert_eq!(std::mem::size_of::<FrozenMode>(), 0);
    }
    #[test]
    fn shared_algorithm_contract_scalar_layouts() {
        println!("FrameScalars size={} align={}", std::mem::size_of::<FrameScalars>(), std::mem::align_of::<FrameScalars>());
        #[cfg(feature = "experimental-span-execution")]
        println!("PinAttempt<FrozenMode> size={} align={}", std::mem::size_of::<PinAttempt<FrozenMode>>(), std::mem::align_of::<PinAttempt<FrozenMode>>());
        assert_eq!(std::mem::size_of::<FrameScalars>(), std::mem::size_of_val(&FrameScalars {function:0,pc:0,base:0,operands:0,controls:0,result:false}));
    }
}
