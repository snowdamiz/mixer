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

// Literal helpers and inline arms are shared at compile time; no runtime adapter.
#[cfg(feature = "experimental-span-execution")]
macro_rules! frozen_control_methods {
    () => {
        shared_control_methods!(self, ExecutionFailure, frozen_control_leaf, control, {});
    };
}

#[allow(unused_macros)]
macro_rules! shared_control_methods {
    ($this:ident, $failure:ty, $leaf:ident, $control:ident, {$($close_prelude:tt)*}) => {
        fn pop32(&mut $this) -> Result<i32, $failure> {
            match $leaf!(pop $this)? {
                Value::I32(value) => Ok(value),
                _ => Err($leaf!(invariant $this)),
            }
        }
        fn close_control(&mut $this, $control: Control) -> Result<(), $failure> {
            $($close_prelude)*
            let value = if $leaf!(result $control) {
                Some($leaf!(pop $this)?)
            } else {
                None
            };
            if $leaf!(height $control) > $leaf!(values $this).len() {
                return Err($leaf!(invariant $this));
            }
            $this.work($leaf!(values $this).len() - $leaf!(height $control) + 1)?;
            $leaf!(truncate_values $this, $leaf!(height $control));
            $leaf!(observe $this);
            if let Some(value) = value {
                $leaf!(push $this, value)?;
            }
            Ok(())
        }
        fn branch(&mut $this, depth: u32) -> Result<bool, $failure> {
            $leaf!(frame $this, frame);
            let index = $leaf!(controls $this)
                .len()
                .checked_sub($leaf!(depth_offset $this, depth))
                .filter(|i| *i >= $leaf!(floor frame))
                .ok_or_else(|| $leaf!(invariant $this))?;
            let mut $control = $leaf!(copy_control $this, index);
            $this.work($leaf!(controls $this).len() - index)?;
            if $leaf!(loop $control) {
                $leaf!(clear $control);
            }
            $this.close_control($control)?;
            $leaf!(truncate_controls $this, if $leaf!(loop $control) {
                index + 1
            } else {
                index
            });
            let pc = if $leaf!(loop $control) {
                $leaf!(start $control)
            } else {
                $leaf!(after_end $this, $control)
            };
            $leaf!(set_pc $this, pc);
            $leaf!(observe $this);
            Ok($leaf!(function $control))
        }
    };
}

#[allow(unused_macros)]
macro_rules! frozen_control_leaf {
    (pop $s:ident) => {
        $s.pop()
    };
    (push $s:ident, $v:expr) => {
        $s.push($v)
    };
    (invariant $s:ident) => {
        $s.invariant()
    };
    (values $s:ident) => {
        $s.values
    };
    (controls $s:ident) => {
        $s.controls
    };
    (frame $s:ident, $f:ident) => {
        let $f = $s.frames.last().ok_or_else(|| $s.invariant())?;
    };
    (floor $f:ident) => {
        $f.controls
    };
    (result $c:ident) => {
        $c.result
    };
    (height $c:ident) => {
        $c.height
    };
    (loop $c:ident) => {
        $c.kind == Kind::Loop
    };
    (function $c:ident) => {
        $c.kind == Kind::Function
    };
    (clear $c:ident) => {
        $c.result = false
    };
    (start $c:ident) => {
        $c.start
    };
    (after_end $s:ident, $c:ident) => {
        $c.end + 1
    };
    (depth_offset $s:ident, $d:ident) => {
        $d as usize + 1
    };
    (truncate_values $s:ident, $h:expr) => {
        $s.values.truncate($h)
    };
    (truncate_controls $s:ident, $h:expr) => {
        $s.controls.truncate($h)
    };
    (observe $s:ident) => {
        $s.observe()
    };
    (set_pc $s:ident, $pc:expr) => {
        $s.frames.last_mut().ok_or_else(unreachable_failure)?.pc = $pc
    };
    (copy_control $s:ident, $index:ident) => {
        $s.controls[$index]
    };
    (selected $s:ident, $target:ident) => {
        $target.ok_or_else(|| $s.invariant())?
    };
    (room $s:ident) => {
        $s.room_control()
    };
    (depth_limit $s:ident) => {
        $s.cache.spans().limits().control_depth
    };
    (depth_error $s:ident, $f:ident) => {
        $s.error(
            ExecutionFailureKind::ControlExhausted,
            "control_depth_exceeded",
            ($s.controls.len() - $f.controls + 1) as u64,
            $s.cache.spans().limits().control_depth as u64,
        )
    };
    (publish $s:ident, $kind:ident, $f:ident, $end:ident, $result:ident) => {
        $s.controls.push(control_record!(
            $kind,
            $f.pc,
            $end,
            $s.values.len(),
            $result.is_some()
        ))
    };
    (false_pc $s:ident, $alternative:ident, $end:ident) => {
        $s.frames.last_mut().ok_or_else(unreachable_failure)?.pc =
            $alternative.map_or($end, |v| v + 1)
    };
    (else_pc $s:ident, $end:ident) => {
        $s.frames.last_mut().ok_or_else(unreachable_failure)?.pc = $end
    };
    (pop_control $s:ident) => {
        $s.controls.pop().ok_or_else(|| $s.invariant())
    };
    (block_guard $s:ident, $kind:ident, $end:ident, $alternative:ident) => {};
}

#[allow(unused_macros)]
macro_rules! control_record {
    ($kind:ident, $start:expr, $end:ident, $height:expr, $result:expr) => {
        Control {
            kind: match $kind {
                ControlKind::Block => Kind::Block,
                ControlKind::Loop => Kind::Loop,
                ControlKind::If => Kind::If,
            },
            start: $start,
            $end,
            height: $height,
            result: $result,
        }
    };
}

#[allow(unused_imports)]
pub(super) use control_record;
#[allow(unused_imports)]
pub(super) use frozen_control_leaf;
#[cfg(feature = "experimental-span-execution")]
#[allow(unused_imports)]
pub(super) use frozen_control_methods;
#[allow(unused_imports)]
pub(crate) use shared_control_methods;

#[allow(unused_macros)]
macro_rules! shared_control_arm {
    (Block, $this:ident, $leaf:ident, $finished:ident, $kind:ident, $result:ident, $end:ident, $alternative:ident) => {
let cond = if $kind == ControlKind::If {
                        $this.pop32()? != 0
                    } else {
                        true
                    };
                    $leaf!{block_guard $this, $kind, $end, $alternative}
$leaf!(room $this)?;
                    $this.work(1)?;
                    $leaf!(frame $this, frame);
                    if $leaf!(controls $this).len() - $leaf!(floor frame)
                        >= $leaf!(depth_limit $this)
                    {
                        return Err($leaf!(depth_error $this, frame));
                    }
                    $leaf!(publish $this, $kind, frame, $end, $result);
                    if !cond {
                        $leaf!(false_pc $this, $alternative, $end);
                    }
                    $leaf!(observe $this);
    };
    (Else, $this:ident, $leaf:ident, $finished:ident, $end:ident) => {
$leaf!(else_pc $this, $end)
    };
    (End, $this:ident, $leaf:ident, $finished:ident) => {
$this.work(1)?;
                    let control = $leaf!(pop_control $this)?;
                    $this.close_control(control)?;
                    $finished = $leaf!(function control);
                    $leaf!(observe $this);
    };
    (Br, $this:ident, $leaf:ident, $finished:ident, $depth:ident) => {
$finished = $this.branch($depth)?
    };
    (BrIf, $this:ident, $leaf:ident, $finished:ident, $depth:ident) => {
if $this.pop32()? != 0 {
                        $finished = $this.branch($depth)?;
                    }
    };
    (BrTable, $this:ident, $leaf:ident, $finished:ident, $target:ident) => {
$this.pop32()?;
                    $finished = $this.branch($leaf!(selected $this, $target))?;
    };
    (Return, $this:ident, $leaf:ident, $finished:ident) => {
$finished = true
    };
}
#[allow(unused_imports)]
pub(crate) use shared_control_arm;
