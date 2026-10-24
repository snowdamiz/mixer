//! Private borrowed types and static frozen numeric primitive dispatch.

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
/// remain on each owner path; the primitive algorithm has one shared body.
#[cfg(any(
    feature = "experimental-span-execution",
    feature = "experimental-swift-reactor"
))]
pub(crate) trait NumericMode: ExecutionMode + Sized {
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

#[cfg(any(
    feature = "experimental-span-execution",
    feature = "experimental-swift-reactor"
))]
pub(crate) fn numeric<M: NumericMode>(
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

// Private literal control methods, emitted on the original frozen owner.
#[cfg(feature = "experimental-span-execution")]
macro_rules! frozen_control_methods {
    () => {
        fn pop32(&mut self) -> Result<i32, ExecutionFailure> {
            match self.pop()? {
                Value::I32(value) => Ok(value),
                _ => Err(self.invariant()),
            }
        }
        fn close_control(&mut self, control: Control) -> Result<(), ExecutionFailure> {
            let value = if control.result {
                Some(self.pop()?)
            } else {
                None
            };
            if control.height > self.values.len() {
                return Err(self.invariant());
            }
            self.work(self.values.len() - control.height + 1)?;
            self.values.truncate(control.height);
            self.observe();
            if let Some(value) = value {
                self.push(value)?;
            }
            Ok(())
        }
        fn branch(&mut self, depth: u32) -> Result<bool, ExecutionFailure> {
            let frame = self.frames.last().ok_or_else(|| self.invariant())?;
            let index = self
                .controls
                .len()
                .checked_sub(depth as usize + 1)
                .filter(|i| *i >= frame.controls)
                .ok_or_else(|| self.invariant())?;
            let mut control = self.controls[index];
            self.work(self.controls.len() - index)?;
            if control.kind == Kind::Loop {
                control.result = false;
            }
            self.close_control(control)?;
            self.controls.truncate(if control.kind == Kind::Loop {
                index + 1
            } else {
                index
            });
            let pc = if control.kind == Kind::Loop {
                control.start
            } else {
                control.end + 1
            };
            self.frames.last_mut().ok_or_else(unreachable_failure)?.pc = pc;
            self.observe();
            Ok(control.kind == Kind::Function)
        }
    };
}

#[cfg(feature = "experimental-span-execution")]
pub(super) use frozen_control_methods;
