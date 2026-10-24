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

#[allow(unused_macros)]
macro_rules! shared_memory_methods {
    ($this:ident, $failure:ty, $leaf:ident, ($($mutable:tt)*), $range:ident, $load:ident, $store:ident, ($($rangevis:tt)*)) => {
$($rangevis)* fn $range(
        &$($mutable)* $this,
        address: usize,
        len: usize,
    ) -> Result<std::ops::Range<usize>, $failure> {
        let end = address
            .checked_add(len)
            .filter(|end| *end <= $leaf!(memory $this).len())
            .ok_or_else(|| $leaf!(trap $this))?;
        Ok(address..end)
    }
fn $load(&mut $this, opcode: u8, offset: u32) -> Result<(), $failure> {
        let address = $leaf!(pop32 $this)? as u32 as usize;
        let width = width(opcode);
        let start = address
            .checked_add(offset as usize)
            .ok_or_else(|| $leaf!(trap $this))?;
        let range = $this.$range(start, width)?;
        $this.work(width)?;
        let mut padded = [0; 8];
        padded[..width].copy_from_slice(&$leaf!(memory $this)[range]);
        let x = u64::from_le_bytes(padded);
        let value = match opcode {
            0x28 => Value::I32(x as i32),
            0x29 => Value::I64(x as i64),
            0x2a => Value::F32(x as u32),
            0x2b => Value::F64(x),
            0x2c => Value::I32(x as i8 as i32),
            0x2d => Value::I32(x as u8 as i32),
            0x2e => Value::I32(x as i16 as i32),
            0x2f => Value::I32(x as u16 as i32),
            0x30 => Value::I64(x as i8 as i64),
            0x31 => Value::I64(x as u8 as i64),
            0x32 => Value::I64(x as i16 as i64),
            0x33 => Value::I64(x as u16 as i64),
            0x34 => Value::I64(x as i32 as i64),
            0x35 => Value::I64(x as u32 as i64),
            _ => return Err($leaf!(invariant $this)),
        };
        $leaf!(push $this, value)
    }
fn $store(&mut $this, opcode: u8, offset: u32) -> Result<(), $failure> {
        let value = $leaf!(pop $this)?;
        let address = $leaf!(pop32 $this)? as u32 as usize;
        let width = width(opcode);
        let start = address
            .checked_add(offset as usize)
            .ok_or_else(|| $leaf!(trap $this))?;
        let range = $this.$range(start, width)?;
        $this.work(width)?;
        let bits = match value {
            Value::I32(x) => x as u32 as u64,
            Value::I64(x) => x as u64,
            Value::F32(x) => x as u64,
            Value::F64(x) => x,
        };
        $leaf!(memory $this)[range].copy_from_slice(&bits.to_le_bytes()[..width]);
        Ok(())
    }
    };
}
#[allow(unused_imports)]
pub(crate) use shared_memory_methods;

#[allow(unused_macros)]
macro_rules! frozen_memory_leaf {
 (pop $s:ident) => { $s.pop() };
 (pop32 $s:ident) => { $s.pop32() };
 (push $s:ident, $v:expr) => { $s.push($v) };
 (memory $s:ident) => { $s.memory };
 (invariant $s:ident) => { $s.invariant() };
 (trap $s:ident) => { $s.trap("memory_out_of_bounds") };
}
#[allow(unused_imports)]
pub(super) use frozen_memory_leaf;

#[allow(unused_macros)]
macro_rules! shared_bulk_memory_methods {
($this:ident, $failure:ty, $leaf:ident, $bulk:ident, $copy:ident, $fill:ident) => {
fn $bulk(&mut $this, len: usize) -> Result<(), $failure> {
        $leaf!(charge $this, len.div_ceil(64) as u64)?;
        $this.work(len)
    }
fn $copy(&mut $this) -> Result<(), $failure> {
        let len = $leaf!(pop32 $this)? as u32 as usize;
        let src = $leaf!(pop32 $this)? as u32 as usize;
        let dst = $leaf!(pop32 $this)? as u32 as usize;
        $leaf!(range $this, src, len)?;
        $leaf!(range $this, dst, len)?;
        $this.$bulk(len)?;
        if dst > src {
            let mut left = len;
            while left != 0 {
                $leaf!(check $this)?;
                let n = left.min(CHUNK);
                left -= n;
                $leaf!(memory $this)
                    .copy_within(src + left..src + left + n, dst + left);
            }
        } else {
            for at in (0..len).step_by(CHUNK) {
                $leaf!(check $this)?;
                let n = (len - at).min(CHUNK);
                $leaf!(memory $this).copy_within(src + at..src + at + n, dst + at);
            }
        }
        Ok(())
    }
fn $fill(&mut $this) -> Result<(), $failure> {
        let len = $leaf!(pop32 $this)? as u32 as usize;
        let value = $leaf!(pop32 $this)? as u8;
        let dst = $leaf!(pop32 $this)? as u32 as usize;
        let range = $leaf!(range $this, dst, len)?;
        $this.$bulk(len)?;
        for start in (range.start..range.end).step_by(CHUNK) {
            $leaf!(check $this)?;
            let end = (start + CHUNK).min(range.end);
            $leaf!(memory $this)[start..end].fill(value);
        }
        Ok(())
    }
};
}
#[allow(unused_imports)]
pub(crate) use shared_bulk_memory_methods;

#[allow(unused_macros)]
macro_rules! frozen_bulk_memory_leaf {
 (pop32 $s:ident) => {$s.pop32()};
 (range $s:ident, $address:expr, $len:expr) => {$s.range($address,$len)};
 (check $s:ident) => {$s.check()};
 (memory $s:ident) => {$s.memory};
 (charge $s:ident, $credits:expr) => {$s.charge($credits,false)};
 (push $s:ident, $value:expr) => {$s.push($value)};
 (pages $s:ident) => {$s.usage.memory_pages};
}
#[allow(unused_imports)]
pub(super) use frozen_bulk_memory_leaf;
#[allow(unused_macros)]
macro_rules! shared_memory_size {
 ($this:ident, $leaf:ident) => {$leaf!(push $this, Value::I32($leaf!(pages $this) as i32))};
}
#[allow(unused_imports)]
pub(crate) use shared_memory_size;

#[allow(unused_macros)]
macro_rules! shared_memory_growth {
($this:ident,$failure:ty,$leaf:ident,$grow:ident)=>{
fn $grow(&mut $this) -> Result<(), $failure> {
        let delta = $leaf!(pop32 $this)? as u32;
        let old = $leaf!(pages $this);
        let maximum = $leaf!(maximum $this);
        let Some(next) = old.checked_add(delta).filter(|next| *next <= maximum) else {
            return $leaf!(push $this, Value::I32(-1));
        };
        if delta == 0 {
            return $leaf!(push $this, Value::I32(old as i32));
        }
        let bytes = (next as usize)
            .checked_mul(PAGE)
            .ok_or_else(|| $leaf!(invariant $this))?;
        $leaf!(work $this,
            bytes
                .checked_add($leaf!(memory $this).len())
                .ok_or_else(|| $leaf!(invariant $this))?,
        )?;
        let mut memory = $leaf!(allocation $this, bytes)?;
        let result = (|| {
            for at in (0..bytes).step_by(CHUNK) {
                $leaf!(zero_check $this, memory)?;
                memory.resize((at + CHUNK).min(bytes), 0);
            }
            for at in (0..$leaf!(memory $this).len()).step_by(CHUNK) {
                $leaf!(copy_check $this, memory)?;
                let end = (at + CHUNK).min($leaf!(memory $this).len());
                memory[at..end].copy_from_slice(&$leaf!(memory $this)[at..end]);
            }
            $leaf!(final_check $this, memory)
        })();
        if let Err(error) = result {
            $leaf!{rollback $this, memory, bytes}
            return Err(error);
        }
        let old_bytes = $leaf!(memory $this).len();
        $leaf!{commit $this, memory, old_bytes, next}
        $leaf!(push $this, Value::I32(old as i32))
    }
};
}
#[allow(unused_imports)]
pub(crate) use shared_memory_growth;

#[allow(unused_macros)]
macro_rules! frozen_growth_leaf {
 (work $s:ident,$amount:expr $(,)?) => {$s.work($amount)};
 (pop32 $s:ident) => {$s.pop32()};
 (pages $s:ident) => {$s.usage.memory_pages};
 (maximum $s:ident) => {$s.cache.spans().execution_memory().ok_or_else(|| $s.invariant())?.1.min($s.cache.spans().limits().memory_pages)};
 (push $s:ident,$value:expr) => {$s.push($value)};
 (invariant $s:ident) => {$s.invariant()};
 (memory $s:ident) => {$s.memory};
 (allocation $s:ident,$bytes:expr) => {$s.allocation($bytes)};
 (check $s:ident) => {$s.check()};
 (zero_check $s:ident,$memory:ident) => {$s.check()};
 (copy_check $s:ident,$memory:ident) => {$s.check()};
 (final_check $s:ident,$memory:ident) => {$s.check()};
 (rollback $s:ident,$memory:ident,$bytes:ident) => {drop($memory);$s.usage.state_reserved -= $bytes;};
 (commit $s:ident,$memory:ident,$old_bytes:ident,$next:ident) => {$s.memory=$memory;$s.usage.state_reserved -= $old_bytes;$s.usage.memory_pages=$next;};
}
#[allow(unused_imports)]
pub(super) use frozen_growth_leaf;

#[allow(unused_macros)]
macro_rules! shared_indirect {
    ($this:ident,$leaf:ident,$index:ident) => {
                    let selector = $leaf!(pop32 $this)? as u32 as usize;
                    let function = $leaf!(table_target $this, selector);
                    let expected = $leaf!(expected_type $this, $index);
                    let actual = $leaf!(actual_type $this, function);
                    let scan = expected
                        .params
                        .len()
                        .checked_add(actual.params.len())
                        .ok_or_else(|| $leaf!(invariant $this))?;
                    $this.work(scan)?;
                    if $leaf!(signature_mismatch $this, $index, function)
                    {
                        return Err($leaf!(trap $this, "indirect_call_type_mismatch"));
                    }
                    $leaf!(call $this, function)?;
                
    };
}
pub(crate) use shared_indirect;

// Complete static run/call orchestration; original Frozen tokens are retained.
#[allow(unused_macros)]
macro_rules! frozen_dispatch_leaf {
    (fetch $s:ident, $instruction:ident, $target:ident, $frame:ident) => {            let $frame = $s.frames.last().ok_or_else(|| $s.invariant())?;
            let view = $s
                .cache
                .view(&$frame.pin)
                .map_err(|error| $s.cache_error(error))?;
            let $instruction = *view
                .instructions
                .get($frame.pc)
                .ok_or_else(|| $s.invariant())?;
            // Copy one selected br_table scalar before ending the cache borrow.
            let $target = if let Operation::BrTable {
                first,
                count,
                default,
            } = $instruction.operation
            {
                let selector = match $s.values.last() {
                    Some(Value::I32(n)) => *n as u32 as usize,
                    _ => return Err($s.invariant()),
                };
                Some(if selector < count {
                    *view
                        .branch_targets
                        .get(first + selector)
                        .ok_or_else(|| $s.invariant())?
                } else {
                    default
                })
            } else {
                None
            };

    };
    (prefix $s:ident, $instruction:ident, $frame:ident) => {            $s.function = Some($frame.function);
            $s.offset = $instruction.offset;
            $s.charge(1, true)?;
            $s.work(1)?;
            $s.frames.last_mut().ok_or_else(unreachable_failure)?.pc += 1;

    };
    (local_get $s:ident, $index:ident) => {
                    let frame = $s.frames.last().ok_or_else(|| $s.invariant())?;
                    let value = *$s
                        .values
                        .get(frame.base + $index as usize)
                        .filter(|_| frame.base + ($index as usize) < frame.operands)
                        .ok_or_else(|| $s.invariant())?;
                    $s.push(value)?;
                
    };
    (local_set $s:ident, $index:ident, $instruction:ident) => {
                    let value = if matches!($instruction.operation, Operation::LocalTee(_)) {
                        $s.work(1)?;
                        *$s.values.last().ok_or_else(|| $s.invariant())?
                    } else {
                        $s.pop()?
                    };
                    let frame = $s.frames.last().ok_or_else(|| $s.invariant())?;
                    let slot = frame.base + $index as usize;
                    if slot >= frame.operands {
                        return Err($s.invariant());
                    }
                    $s.values[slot] = value;
                
    };
    (global_get $s:ident, $index:ident) => {
                    let value = *$s
                        .globals
                        .get($index as usize)
                        .ok_or_else(|| $s.invariant())?;
                    $s.push(value)?;
                
    };
    (global_set $s:ident, $index:ident) => {
                    let value = $s.pop()?;
                    let desc = $s
                        .cache
                        .spans()
                        .execution_global($index as usize)
                        .ok_or_else(|| $s.invariant())?;
                    if !desc.mutable || value.ty() != desc.ty {
                        return Err($s.invariant());
                    }
                    $s.globals[$index as usize] = value;
                
    };
    (finish $s:ident, $finished:ident) => {            if $finished {
                let result = $s.finish()?;
                if $s.frames.is_empty() {
                    return Ok(result);
                }
            }

    };
    (parameters $s:ident, $function:ident) => {         $s
            .cache
            .spans()
            .execution_signature($function)
            .ok_or_else(|| $s.invariant())?
            .params
            .len()
    };
    (base $s:ident, $params:ident, $base:ident) => {        let $base = $s
            .values
            .len()
            .checked_sub($params)
            .ok_or_else(|| $s.invariant())?;
        let frame = $s.frames.last().ok_or_else(|| $s.invariant())?;
        if $base < frame.operands {
            return Err($s.invariant());
        }

    };
    (import $s:ident, $function:ident, $base:ident) => {            // The Call instruction was already charged, exactly as in eager.
            let value = $s.import($function)?;
            $s.values.truncate($base);
            $s.observe();
            if let Some(value) = value {
                $s.push(value)?;
            }
            Ok(())

    };
    (table_target $s:ident, $selector:ident) => {                     $s
                        .table
                        .get($selector)
                        .ok_or_else(|| $s.trap("table_out_of_bounds"))?
                        .ok_or_else(|| $s.trap("indirect_call_null"))?
    };
    (expected_type $s:ident, $index:ident) => {                     $s
                        .cache
                        .spans()
                        .execution_type($index)
                        .ok_or_else(|| $s.invariant())?
    };
    (actual_type $s:ident, $function:ident) => {                     $s
                        .cache
                        .spans()
                        .execution_signature($function)
                        .ok_or_else(|| $s.invariant())?
    };
    (signature_mismatch $s:ident, $index:ident, $function:ident) => {$s.cache.spans().execution_type($index)
                        != $s.cache.spans().execution_signature($function)
    };
    (indirect $s:ident, $index:ident) => {shared_indirect!{$s,frozen_dispatch_leaf,$index}};
    (invariant $s:ident) => {$s.invariant()};
    (select_guard $s:ident) => {};
    (publication $s:ident) => {};
    (trap $s:ident, $code:expr) => {$s.trap($code)};
    (push $s:ident, $value:expr) => {$s.push($value)};
    (pop $s:ident) => {$s.pop()};
    (pop32 $s:ident) => {$s.pop32()};
    (call $s:ident, $function:ident) => {$s.call($function)};
    (parameter_work $s:ident, $params:ident, $function:ident) => {$s.work($params)};
    (is_import $s:ident, $function:ident) => {$s.cache.spans().execution_import($function).is_some()};
    (memory_size $s:ident) => {borrowed::shared_memory_size!($s, frozen_bulk_memory_leaf)};
    (growth $s:ident) => {$s.grow()};
    (copy $s:ident) => {$s.copy()};
    (fill $s:ident) => {$s.fill()};
    (load $s:ident, $opcode:ident, $offset:ident) => {$s.load($opcode,$offset)};
    (store $s:ident, $opcode:ident, $offset:ident) => {$s.store($opcode,$offset)};
    (numeric $s:ident, $opcode:ident) => {$s.numeric($opcode,false)};
    (saturating $s:ident, $opcode:ident) => {$s.numeric($opcode,true)};
}
pub(crate) use frozen_dispatch_leaf;

#[allow(unused_macros)]
macro_rules! shared_run {
    ($this:ident,$leaf:ident,$control:ident,$control_leaf:ident) => {
        loop {
            $leaf!{fetch $this, instruction, target, frame}
            $leaf!{prefix $this, instruction, frame}
            let mut finished = false;
            match instruction.operation {
                Operation::Unreachable => return Err($leaf!(trap $this, "unreachable")),
                Operation::Nop => {}
                Operation::Const(value) => $leaf!(push $this, value)?,
                Operation::Drop => {
                    $leaf!(pop $this)?;
                }
                Operation::Select => {
                    $leaf!{select_guard $this}
                    let cond = $leaf!(pop32 $this)?;
                    let b = $leaf!(pop $this)?;
                    let a = $leaf!(pop $this)?;
                    $leaf!(push $this, if cond != 0 { a } else { b })?;
                }
                Operation::LocalGet(index) => {
                    $leaf!{local_get $this, index}
                },
                Operation::LocalSet(index) | Operation::LocalTee(index) => {
                    $leaf!{local_set $this, index, instruction}
                },
                Operation::GlobalGet(index) => {
                    $leaf!{global_get $this, index}
                },
                Operation::GlobalSet(index) => {
                    $leaf!{global_set $this, index}
                },
                Operation::Block {
                    kind,
                    result,
                    end,
                    alternative,
                } => {
                    $control! {Block, $this, $control_leaf, finished, kind, result, end, alternative}
                }
                Operation::Else { end } => {
                    $control! {Else, $this, $control_leaf, finished, end}
                }
                Operation::End => {
                    $control! {End, $this, $control_leaf, finished}
                }
                Operation::Br(depth) => $control!(Br, $this, $control_leaf, finished, depth),
                Operation::BrIf(depth) => {
                    $control! {BrIf, $this, $control_leaf, finished, depth}
                }
                Operation::BrTable { .. } => {
                    $control! {BrTable, $this, $control_leaf, finished, target}
                }
                Operation::Return => $control!(Return, $this, $control_leaf, finished),
                Operation::Call(function) => $leaf!(call $this, function)?,
                Operation::CallIndirect(index) => {
                    $leaf!{indirect $this, index}
                },
                Operation::MemorySize => $leaf!(memory_size $this)?,
                Operation::MemoryGrow => $leaf!(growth $this)?,
                Operation::MemoryCopy => $leaf!(copy $this)?,
                Operation::MemoryFill => $leaf!(fill $this)?,
                Operation::Load { opcode, offset } => $leaf!(load $this, opcode, offset)?,
                Operation::Store { opcode, offset } => $leaf!(store $this, opcode, offset)?,
                Operation::Numeric(opcode) => $leaf!(numeric $this, opcode)?,
                Operation::Saturating(opcode) => $leaf!(saturating $this, opcode)?,
            }
            $leaf!{publication $this}
            $leaf!{finish $this, finished}
        }
    
    };
}
pub(crate) use shared_run;

#[allow(unused_macros)]
macro_rules! shared_call {
    ($this:ident,$leaf:ident,$function:ident) => {
        let params = $leaf!(parameters $this, $function);
        $leaf!(parameter_work $this, params, $function)?;
        $leaf!{base $this, params, base}
        if $leaf!(is_import $this, $function) {
            $leaf!{import $this, $function, base}
        } else {
            $this.enter($function)
        }
    
    };
}
pub(crate) use shared_call;

// CALL_DISPATCH_KIND_ACCOUNTING_BEGIN
// Private Kind fields remain in the original defining-module child.
#[allow(dead_code)]
pub(crate) mod calls_kind_accounting {
#[allow(dead_code)]
pub(super) struct CallsKindActivePositions {
    m_swift_release_production_984df387ff44_43_source: super::super::Kind,
    m_swift_release_production_984df387ff44_43_argument: super::super::Kind,
    m_swift_release_production_984df387ff44_43_returned: super::super::Kind,
    m_swift_release_production_984df387ff44_43_caller: super::super::Kind,
    #[cfg(test)]
    m_swift_release_unit_984df387ff44_43_source: super::super::Kind,
    #[cfg(test)]
    m_swift_release_unit_984df387ff44_43_argument: super::super::Kind,
    #[cfg(test)]
    m_swift_release_unit_984df387ff44_43_returned: super::super::Kind,
    #[cfg(test)]
    m_swift_release_unit_984df387ff44_43_caller: super::super::Kind,
    m_all_release_production_984df387ff44_43_source: super::super::Kind,
    m_all_release_production_984df387ff44_43_argument: super::super::Kind,
    m_all_release_production_984df387ff44_43_returned: super::super::Kind,
    m_all_release_production_984df387ff44_43_caller: super::super::Kind,
    #[cfg(test)]
    m_all_release_unit_984df387ff44_43_source: super::super::Kind,
    #[cfg(test)]
    m_all_release_unit_984df387ff44_43_argument: super::super::Kind,
    #[cfg(test)]
    m_all_release_unit_984df387ff44_43_returned: super::super::Kind,
    #[cfg(test)]
    m_all_release_unit_984df387ff44_43_caller: super::super::Kind,
}
pub(crate) const ACTIVE_BYTES:usize=std::mem::size_of::<CallsKindActivePositions>();
#[allow(dead_code)]
pub(super) struct CallsKindPermanentPositions {
}
pub(crate) const PERMANENT_BYTES:usize=std::mem::size_of::<CallsKindPermanentPositions>();
}
// CALL_DISPATCH_KIND_ACCOUNTING_END
