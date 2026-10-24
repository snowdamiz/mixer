//! Private type/lifetime prerequisite. No interpreter algorithm is selected here.

use super::*;

#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) mod sealed {
    pub trait Mode {}
}

/// Closed static association; an operation lifetime cannot outlive its owners.
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) trait ExecutionMode: sealed::Mode {
    type Cache;
    type Pin;
    type Frame;
    type Operation<'a>;
    type Failure;
}

#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct ExecutionParts<'a, M: ExecutionMode> {
    pub cache: &'a mut M::Cache,
    pub memory: &'a mut Vec<u8>,
    pub table: &'a mut Vec<Option<u32>>,
    pub globals: &'a mut Vec<Value>,
    pub values: &'a mut Vec<Value>,
    pub controls: &'a mut Vec<Control>,
    pub frames: &'a mut Vec<M::Frame>,
}

#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct FrozenMode;
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) struct FrozenOperation<'a> {
    pub budget: &'a ExecutionBudget,
    pub cancellation: &'a Cancellation,
    pub usage: &'a mut ExecutionUsage,
    pub failure: &'a mut Option<ExecutionFailure>,
    pub function: &'a mut Option<u32>,
    pub offset: &'a mut usize,
}
impl sealed::Mode for FrozenMode {}
impl ExecutionMode for FrozenMode {
    type Cache = FunctionCache;
    type Pin = FunctionPin;
    type Frame = Frame;
    type Operation<'a> = FrozenOperation<'a>;
    type Failure = ExecutionFailure;
}

/// Only borrows the original frozen fields; it neither constructs an owner nor
/// changes a field, counter, failure order, allocation, or instruction path.
#[allow(dead_code)] // Chosen private type/layout prerequisite; no executable owner route yet.
pub(crate) fn frozen_parts(
    instance: &mut SpanInstance,
) -> (ExecutionParts<'_, FrozenMode>, FrozenOperation<'_>) {
    (
        ExecutionParts {
            cache: &mut instance.cache,
            memory: &mut instance.memory,
            table: &mut instance.table,
            globals: &mut instance.globals,
            values: &mut instance.values,
            controls: &mut instance.controls,
            frames: &mut instance.frames,
        },
        FrozenOperation {
            budget: &instance.budget,
            cancellation: &instance.cancellation,
            usage: &mut instance.usage,
            failure: &mut instance.failure,
            function: &mut instance.function,
            offset: &mut instance.offset,
        },
    )
}

#[cfg(all(test, feature = "experimental-swift-reactor"))]
#[path = "tests.rs"]
mod tests;

/// Static primitive dispatch only. Owner validation/metering/observation/errors
/// remain on the existing frozen path; Swift has no numeric mode adapter.
#[cfg(feature = "experimental-span-execution")]
pub(super) trait NumericMode: ExecutionMode + Sized {
    type NumericState<'a>;
    fn values_mut<'short>(state: &'short mut Self::NumericState<'_>) -> &'short mut Vec<Value>;
}

#[cfg(feature = "experimental-span-execution")]
impl NumericMode for FrozenMode {
    type NumericState<'a> = SpanInstance;
    fn values_mut<'short>(state: &'short mut Self::NumericState<'_>) -> &'short mut Vec<Value> {
        &mut state.values
    }
}

#[cfg(feature = "experimental-span-execution")]
pub(super) fn numeric<M: NumericMode>(
    state: &mut M::NumericState<'_>,
    opcode: u8,
    saturating: bool,
) -> Result<(), &'static str> {
    if saturating {
        crate::float::saturating(opcode, M::values_mut(state));
        Ok(())
    } else if crate::float::shape(opcode).is_some() {
        crate::float::numeric(opcode, M::values_mut(state))
    } else {
        crate::execute::numeric(opcode, M::values_mut(state))
    }
}

#[cfg(test)]
#[path = "numeric_layout_probe.rs"]
mod numeric_layout_probe;
