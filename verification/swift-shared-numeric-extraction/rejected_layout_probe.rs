#[test]
fn shared_numeric_actual_layout() {
    use std::mem::{align_of, offset_of, size_of};
    macro_rules! slot {
        ($name:literal, $ty:ty) => {
            println!("numeric_type {} size={} align={}", $name, size_of::<$ty>(), align_of::<$ty>());
        };
    }
    slot!("SpanInstance", SpanInstance);
    slot!("FunctionCache", FunctionCache);
    slot!("Frame", Frame);
    slot!("Control", Control);
    slot!("ExecutionFailure", ExecutionFailure);
    slot!("CacheFailure", CacheFailure);
    slot!("DecodedInstruction", crate::experimental::cache::DecodedInstruction);
    slot!("ScalarReader", ScalarReader<'static>);
    slot!("FrozenMode", FrozenMode);
    slot!("state_argument", &mut SpanInstance);
    slot!("operand_base_return", Option<usize>);
    slot!("frame_source_option", Option<&Frame>);
    slot!("value_slice_return", &[Value]);
    slot!("value_arena_return", &mut Vec<Value>);
    slot!("shape", (crate::Type, usize, crate::Type));
    slot!("shape_option", Option<(crate::Type, usize, crate::Type)>);
    slot!("saturating_shape", (crate::Type, crate::Type));
    slot!("shape_type", crate::Type);
    slot!("count_length_or_credits", usize);
    slot!("helper_result", Result<(), &'static str>);
    slot!("numeric_adapter_result", Result<(), ExecutionFailure>);
    slot!("numeric_adapter_failure", ExecutionFailure);
    slot!("trap_code", &'static str);
    slot!("numeric_operand_result", Result<usize, ExecutionFailure>);
    slot!("run_result", Result<Option<Value>, ExecutionFailure>);
    slot!("operand_iterator", std::slice::Iter<'static, Value>);
    slot!("range_from", std::ops::RangeFrom<usize>);
    // Deliberately retain distinct source, returned, and caller positions.
    // This is the contract inventory, not an inference about optimized stack ABI.
    #[repr(C)]
    struct NumericFallibleAdapterTransfer {
        source_result: Result<(), ExecutionFailure>,
        returned_result: Result<(), ExecutionFailure>,
        caller_result: Result<(), ExecutionFailure>,
    }
    slot!("NumericFallibleAdapterTransfer", NumericFallibleAdapterTransfer);
    println!("numeric_adapter_map source_result {} {} returned_result {} {} caller_result {} {} original_scalar_component {} fits {}",
        offset_of!(NumericFallibleAdapterTransfer, source_result), size_of::<Result<(), ExecutionFailure>>(),
        offset_of!(NumericFallibleAdapterTransfer, returned_result), size_of::<Result<(), ExecutionFailure>>(),
        offset_of!(NumericFallibleAdapterTransfer, caller_result), size_of::<Result<(), ExecutionFailure>>(),
        512, size_of::<NumericFallibleAdapterTransfer>() <= 512);
    // Unit-return candidate: the passed outcome is one caller-owned Result.
    // Retain old helper/trap/error scalar roles and name each adapter addition.
    // Unused shape/count/base/pre-length roles are excluded after their last use.
    #[repr(C)]
    struct NumericUnitTrapWindow<'a> {
        new_caller_outcome: Result<(), ExecutionFailure>,
        original_run_self: &'a mut SpanInstance,
        original_run_selected_target: Option<u32>,
        original_helper_state: &'a mut SpanInstance,
        original_helper_result: Result<(), &'static str>,
        original_matched_code: &'static str,
        new_adapter_state_argument: &'a mut SpanInstance,
        new_adapter_code_argument: &'static str,
        new_adapter_outcome_argument: &'a mut Result<(), ExecutionFailure>,
        original_trap_self: &'a SpanInstance,
        original_trap_code: &'static str,
        original_error_self: &'a SpanInstance,
        original_error_code: &'static str,
        original_error_attempted: u64,
        original_error_limit: u64,
        original_error_kind: ExecutionFailureKind,
        original_run_finished: bool,
        original_run_opcode: u8,
    }
    slot!("NumericUnitTrapWindow", NumericUnitTrapWindow<'static>);
    macro_rules! position {
        ($name:ident, $ty:ty) => {
            println!("numeric_unit_trap_position {} offset={} bytes={}", stringify!($name),
                offset_of!(NumericUnitTrapWindow<'static>, $name), size_of::<$ty>());
        };
    }
    position!(new_caller_outcome, Result<(), ExecutionFailure>);
    position!(original_run_self, &'static mut SpanInstance);
    position!(original_run_selected_target, Option<u32>);
    position!(original_helper_state, &'static mut SpanInstance);
    position!(original_helper_result, Result<(), &'static str>);
    position!(original_matched_code, &'static str);
    position!(new_adapter_state_argument, &'static mut SpanInstance);
    position!(new_adapter_code_argument, &'static str);
    position!(new_adapter_outcome_argument, &'static mut Result<(), ExecutionFailure>);
    position!(original_trap_self, &'static SpanInstance);
    position!(original_trap_code, &'static str);
    position!(original_error_self, &'static SpanInstance);
    position!(original_error_code, &'static str);
    position!(original_error_attempted, u64);
    position!(original_error_limit, u64);
    position!(original_error_kind, ExecutionFailureKind);
    position!(original_run_finished, bool);
    position!(original_run_opcode, u8);
    println!("numeric_unit_trap_map original_scalar_component=512 selected_window={} fits={}",
        size_of::<NumericUnitTrapWindow<'static>>(), size_of::<NumericUnitTrapWindow<'static>>() <= 512);
    println!("numeric_reservation {}", size_of::<SpanInstance>() - size_of::<FunctionCache>()
        + 3 * size_of::<ExecutionFailure>() + 2 * size_of::<CacheFailure>()
        + size_of::<crate::experimental::cache::DecodedInstruction>() + size_of::<Control>()
        + size_of::<ScalarReader<'static>>() + 512);
    macro_rules! fields {
        ($t:ty; $($f:ident),+) => {$({
            println!("numeric_offset {} {} {}", stringify!($t), stringify!($f), offset_of!($t, $f));
        })+};
    }
    fields!(Frame; function, pc, base, operands, controls, result, pin);
    fields!(Control; kind, start, end, height, result);
    fields!(SpanInstance; cache, budget, cancellation, usage, failure, memory, table,
        globals, values, controls, frames, function, offset);
}
