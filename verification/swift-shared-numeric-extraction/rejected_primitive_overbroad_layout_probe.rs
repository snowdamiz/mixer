#[test]
fn shared_numeric_actual_layout() {
    use std::mem::{align_of, offset_of, size_of};
    #[repr(C)]
    struct PrimitiveIntegerWindow<'a> {
        old_run_self: &'a mut SpanInstance,
        old_run_target: Option<u32>,
        old_run_finished: bool,
        old_run_opcode: u8,
        old_numeric_self: &'a mut SpanInstance,
        old_numeric_opcode: u8,
        old_numeric_saturating: bool,
        old_numeric_type: crate::Type,
        old_numeric_count: usize,
        old_numeric_frame: &'a Frame,
        new_helper_state_source: &'a mut SpanInstance,
        new_helper_state_argument: &'a mut SpanInstance,
        new_helper_opcode_source: u8,
        new_helper_opcode_argument: u8,
        new_helper_saturating_source: bool,
        new_helper_saturating_argument: bool,
        new_values_state_source: &'a mut SpanInstance,
        new_values_state_argument: &'a mut SpanInstance,
        new_values_arena_source: &'a mut Vec<Value>,
        new_values_arena_returned: &'a mut Vec<Value>,
        new_values_arena_caller: &'a mut Vec<Value>,
        old_primitive_arena_argument: &'a mut Vec<Value>,
        old_primitive_opcode_argument: u8,
        old_primitive_result_source: Result<(), &'static str>,
        old_primitive_result_returned: Result<(), &'static str>,
        new_helper_result_caller: Result<(), &'static str>,
        new_helper_result_returned: Result<(), &'static str>,
        old_owner_result_caller: Result<(), &'static str>,
        old_dispatch_shape_source: Option<(crate::Type,usize,crate::Type)>,
        old_dispatch_shape_returned: Option<(crate::Type,usize,crate::Type)>,
        old_dispatch_shape_caller: Option<(crate::Type,usize,crate::Type)>,
        old_shape_opcode: u8,
        old_pop_arena: &'a mut Vec<Value>,
        old_pop_source: Option<Value>,
        old_pop_returned: Option<Value>,
        old_pop_caller: Option<Value>,
        old_pop_matched: Value,
        old_pop_scalar_source: u64,
        old_pop_scalar_returned: u64,
        old_pop_scalar_caller: u64,
        old_integer_shape_source: (crate::Type,usize,crate::Type),
        old_integer_shape_returned: (crate::Type,usize,crate::Type),
        old_integer_shape_caller: (crate::Type,usize,crate::Type),
        old_integer_type: crate::Type,
        old_integer_count: usize,
        old_integer_output: crate::Type,
        old_integer_a: i64,
        old_integer_b: i64,
        old_integer_x: i64,
        old_checked_div_source: Option<i64>,
        old_checked_div_returned: Option<i64>,
        old_checked_div_caller: Option<i64>,
        old_push_value: Value,
    }
    println!("primitive_window PrimitiveIntegerWindow size={} align={} scalar_limit=512 fits={}",size_of::<PrimitiveIntegerWindow<'static>>(),align_of::<PrimitiveIntegerWindow<'static>>(),size_of::<PrimitiveIntegerWindow<'static>>()<=512);
    println!("primitive_position PrimitiveIntegerWindow old_run_self offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_run_self),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveIntegerWindow old_run_target offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_run_target),size_of::<Option<u32>>());
    println!("primitive_position PrimitiveIntegerWindow old_run_finished offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_run_finished),size_of::<bool>());
    println!("primitive_position PrimitiveIntegerWindow old_run_opcode offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_run_opcode),size_of::<u8>());
    println!("primitive_position PrimitiveIntegerWindow old_numeric_self offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_numeric_self),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveIntegerWindow old_numeric_opcode offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_numeric_opcode),size_of::<u8>());
    println!("primitive_position PrimitiveIntegerWindow old_numeric_saturating offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_numeric_saturating),size_of::<bool>());
    println!("primitive_position PrimitiveIntegerWindow old_numeric_type offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_numeric_type),size_of::<crate::Type>());
    println!("primitive_position PrimitiveIntegerWindow old_numeric_count offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_numeric_count),size_of::<usize>());
    println!("primitive_position PrimitiveIntegerWindow old_numeric_frame offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_numeric_frame),size_of::<&'static Frame>());
    println!("primitive_position PrimitiveIntegerWindow new_helper_state_source offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,new_helper_state_source),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveIntegerWindow new_helper_state_argument offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,new_helper_state_argument),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveIntegerWindow new_helper_opcode_source offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,new_helper_opcode_source),size_of::<u8>());
    println!("primitive_position PrimitiveIntegerWindow new_helper_opcode_argument offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,new_helper_opcode_argument),size_of::<u8>());
    println!("primitive_position PrimitiveIntegerWindow new_helper_saturating_source offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,new_helper_saturating_source),size_of::<bool>());
    println!("primitive_position PrimitiveIntegerWindow new_helper_saturating_argument offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,new_helper_saturating_argument),size_of::<bool>());
    println!("primitive_position PrimitiveIntegerWindow new_values_state_source offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,new_values_state_source),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveIntegerWindow new_values_state_argument offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,new_values_state_argument),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveIntegerWindow new_values_arena_source offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,new_values_arena_source),size_of::<&'static mut Vec<Value>>());
    println!("primitive_position PrimitiveIntegerWindow new_values_arena_returned offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,new_values_arena_returned),size_of::<&'static mut Vec<Value>>());
    println!("primitive_position PrimitiveIntegerWindow new_values_arena_caller offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,new_values_arena_caller),size_of::<&'static mut Vec<Value>>());
    println!("primitive_position PrimitiveIntegerWindow old_primitive_arena_argument offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_primitive_arena_argument),size_of::<&'static mut Vec<Value>>());
    println!("primitive_position PrimitiveIntegerWindow old_primitive_opcode_argument offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_primitive_opcode_argument),size_of::<u8>());
    println!("primitive_position PrimitiveIntegerWindow old_primitive_result_source offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_primitive_result_source),size_of::<Result<(), &'static str>>());
    println!("primitive_position PrimitiveIntegerWindow old_primitive_result_returned offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_primitive_result_returned),size_of::<Result<(), &'static str>>());
    println!("primitive_position PrimitiveIntegerWindow new_helper_result_caller offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,new_helper_result_caller),size_of::<Result<(), &'static str>>());
    println!("primitive_position PrimitiveIntegerWindow new_helper_result_returned offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,new_helper_result_returned),size_of::<Result<(), &'static str>>());
    println!("primitive_position PrimitiveIntegerWindow old_owner_result_caller offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_owner_result_caller),size_of::<Result<(), &'static str>>());
    println!("primitive_position PrimitiveIntegerWindow old_dispatch_shape_source offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_dispatch_shape_source),size_of::<Option<(crate::Type,usize,crate::Type)>>());
    println!("primitive_position PrimitiveIntegerWindow old_dispatch_shape_returned offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_dispatch_shape_returned),size_of::<Option<(crate::Type,usize,crate::Type)>>());
    println!("primitive_position PrimitiveIntegerWindow old_dispatch_shape_caller offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_dispatch_shape_caller),size_of::<Option<(crate::Type,usize,crate::Type)>>());
    println!("primitive_position PrimitiveIntegerWindow old_shape_opcode offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_shape_opcode),size_of::<u8>());
    println!("primitive_position PrimitiveIntegerWindow old_pop_arena offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_pop_arena),size_of::<&'static mut Vec<Value>>());
    println!("primitive_position PrimitiveIntegerWindow old_pop_source offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_pop_source),size_of::<Option<Value>>());
    println!("primitive_position PrimitiveIntegerWindow old_pop_returned offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_pop_returned),size_of::<Option<Value>>());
    println!("primitive_position PrimitiveIntegerWindow old_pop_caller offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_pop_caller),size_of::<Option<Value>>());
    println!("primitive_position PrimitiveIntegerWindow old_pop_matched offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_pop_matched),size_of::<Value>());
    println!("primitive_position PrimitiveIntegerWindow old_pop_scalar_source offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_pop_scalar_source),size_of::<u64>());
    println!("primitive_position PrimitiveIntegerWindow old_pop_scalar_returned offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_pop_scalar_returned),size_of::<u64>());
    println!("primitive_position PrimitiveIntegerWindow old_pop_scalar_caller offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_pop_scalar_caller),size_of::<u64>());
    println!("primitive_position PrimitiveIntegerWindow old_integer_shape_source offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_integer_shape_source),size_of::<(crate::Type,usize,crate::Type)>());
    println!("primitive_position PrimitiveIntegerWindow old_integer_shape_returned offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_integer_shape_returned),size_of::<(crate::Type,usize,crate::Type)>());
    println!("primitive_position PrimitiveIntegerWindow old_integer_shape_caller offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_integer_shape_caller),size_of::<(crate::Type,usize,crate::Type)>());
    println!("primitive_position PrimitiveIntegerWindow old_integer_type offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_integer_type),size_of::<crate::Type>());
    println!("primitive_position PrimitiveIntegerWindow old_integer_count offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_integer_count),size_of::<usize>());
    println!("primitive_position PrimitiveIntegerWindow old_integer_output offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_integer_output),size_of::<crate::Type>());
    println!("primitive_position PrimitiveIntegerWindow old_integer_a offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_integer_a),size_of::<i64>());
    println!("primitive_position PrimitiveIntegerWindow old_integer_b offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_integer_b),size_of::<i64>());
    println!("primitive_position PrimitiveIntegerWindow old_integer_x offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_integer_x),size_of::<i64>());
    println!("primitive_position PrimitiveIntegerWindow old_checked_div_source offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_checked_div_source),size_of::<Option<i64>>());
    println!("primitive_position PrimitiveIntegerWindow old_checked_div_returned offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_checked_div_returned),size_of::<Option<i64>>());
    println!("primitive_position PrimitiveIntegerWindow old_checked_div_caller offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_checked_div_caller),size_of::<Option<i64>>());
    println!("primitive_position PrimitiveIntegerWindow old_push_value offset={} bytes={}",offset_of!(PrimitiveIntegerWindow<'static>,old_push_value),size_of::<Value>());
    assert!(size_of::<PrimitiveIntegerWindow<'static>>()<=512,"PrimitiveIntegerWindow exceeds original scalar component");
    #[repr(C)]
    struct PrimitiveFloatWindow<'a> {
        old_run_self: &'a mut SpanInstance,
        old_run_target: Option<u32>,
        old_run_finished: bool,
        old_run_opcode: u8,
        old_numeric_self: &'a mut SpanInstance,
        old_numeric_opcode: u8,
        old_numeric_saturating: bool,
        old_numeric_type: crate::Type,
        old_numeric_count: usize,
        old_numeric_frame: &'a Frame,
        new_helper_state_source: &'a mut SpanInstance,
        new_helper_state_argument: &'a mut SpanInstance,
        new_helper_opcode_source: u8,
        new_helper_opcode_argument: u8,
        new_helper_saturating_source: bool,
        new_helper_saturating_argument: bool,
        new_values_state_source: &'a mut SpanInstance,
        new_values_state_argument: &'a mut SpanInstance,
        new_values_arena_source: &'a mut Vec<Value>,
        new_values_arena_returned: &'a mut Vec<Value>,
        new_values_arena_caller: &'a mut Vec<Value>,
        old_primitive_arena_argument: &'a mut Vec<Value>,
        old_primitive_opcode_argument: u8,
        old_primitive_result_source: Result<(), &'static str>,
        old_primitive_result_returned: Result<(), &'static str>,
        new_helper_result_caller: Result<(), &'static str>,
        new_helper_result_returned: Result<(), &'static str>,
        old_owner_result_caller: Result<(), &'static str>,
        old_dispatch_shape_source: Option<(crate::Type,usize,crate::Type)>,
        old_dispatch_shape_returned: Option<(crate::Type,usize,crate::Type)>,
        old_dispatch_shape_caller: Option<(crate::Type,usize,crate::Type)>,
        old_shape_opcode: u8,
        old_pop_arena: &'a mut Vec<Value>,
        old_pop_source: Option<Value>,
        old_pop_returned: Option<Value>,
        old_pop_caller: Option<Value>,
        old_pop_matched: Value,
        old_pop_scalar_source: u64,
        old_pop_scalar_returned: u64,
        old_pop_scalar_caller: u64,
        old_float_a: u64,
        old_float_b: u64,
        old_float_x: f64,
        old_float_y: f64,
        old_float_bits: u64,
        old_nan_bits_source: u64,
        old_nan_bits_argument: u64,
        old_nan_bits_returned: u64,
        old_nan_bits_caller: u64,
        old_push_value: Value,
    }
    println!("primitive_window PrimitiveFloatWindow size={} align={} scalar_limit=512 fits={}",size_of::<PrimitiveFloatWindow<'static>>(),align_of::<PrimitiveFloatWindow<'static>>(),size_of::<PrimitiveFloatWindow<'static>>()<=512);
    println!("primitive_position PrimitiveFloatWindow old_run_self offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_run_self),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveFloatWindow old_run_target offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_run_target),size_of::<Option<u32>>());
    println!("primitive_position PrimitiveFloatWindow old_run_finished offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_run_finished),size_of::<bool>());
    println!("primitive_position PrimitiveFloatWindow old_run_opcode offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_run_opcode),size_of::<u8>());
    println!("primitive_position PrimitiveFloatWindow old_numeric_self offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_numeric_self),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveFloatWindow old_numeric_opcode offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_numeric_opcode),size_of::<u8>());
    println!("primitive_position PrimitiveFloatWindow old_numeric_saturating offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_numeric_saturating),size_of::<bool>());
    println!("primitive_position PrimitiveFloatWindow old_numeric_type offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_numeric_type),size_of::<crate::Type>());
    println!("primitive_position PrimitiveFloatWindow old_numeric_count offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_numeric_count),size_of::<usize>());
    println!("primitive_position PrimitiveFloatWindow old_numeric_frame offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_numeric_frame),size_of::<&'static Frame>());
    println!("primitive_position PrimitiveFloatWindow new_helper_state_source offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,new_helper_state_source),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveFloatWindow new_helper_state_argument offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,new_helper_state_argument),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveFloatWindow new_helper_opcode_source offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,new_helper_opcode_source),size_of::<u8>());
    println!("primitive_position PrimitiveFloatWindow new_helper_opcode_argument offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,new_helper_opcode_argument),size_of::<u8>());
    println!("primitive_position PrimitiveFloatWindow new_helper_saturating_source offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,new_helper_saturating_source),size_of::<bool>());
    println!("primitive_position PrimitiveFloatWindow new_helper_saturating_argument offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,new_helper_saturating_argument),size_of::<bool>());
    println!("primitive_position PrimitiveFloatWindow new_values_state_source offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,new_values_state_source),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveFloatWindow new_values_state_argument offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,new_values_state_argument),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveFloatWindow new_values_arena_source offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,new_values_arena_source),size_of::<&'static mut Vec<Value>>());
    println!("primitive_position PrimitiveFloatWindow new_values_arena_returned offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,new_values_arena_returned),size_of::<&'static mut Vec<Value>>());
    println!("primitive_position PrimitiveFloatWindow new_values_arena_caller offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,new_values_arena_caller),size_of::<&'static mut Vec<Value>>());
    println!("primitive_position PrimitiveFloatWindow old_primitive_arena_argument offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_primitive_arena_argument),size_of::<&'static mut Vec<Value>>());
    println!("primitive_position PrimitiveFloatWindow old_primitive_opcode_argument offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_primitive_opcode_argument),size_of::<u8>());
    println!("primitive_position PrimitiveFloatWindow old_primitive_result_source offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_primitive_result_source),size_of::<Result<(), &'static str>>());
    println!("primitive_position PrimitiveFloatWindow old_primitive_result_returned offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_primitive_result_returned),size_of::<Result<(), &'static str>>());
    println!("primitive_position PrimitiveFloatWindow new_helper_result_caller offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,new_helper_result_caller),size_of::<Result<(), &'static str>>());
    println!("primitive_position PrimitiveFloatWindow new_helper_result_returned offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,new_helper_result_returned),size_of::<Result<(), &'static str>>());
    println!("primitive_position PrimitiveFloatWindow old_owner_result_caller offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_owner_result_caller),size_of::<Result<(), &'static str>>());
    println!("primitive_position PrimitiveFloatWindow old_dispatch_shape_source offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_dispatch_shape_source),size_of::<Option<(crate::Type,usize,crate::Type)>>());
    println!("primitive_position PrimitiveFloatWindow old_dispatch_shape_returned offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_dispatch_shape_returned),size_of::<Option<(crate::Type,usize,crate::Type)>>());
    println!("primitive_position PrimitiveFloatWindow old_dispatch_shape_caller offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_dispatch_shape_caller),size_of::<Option<(crate::Type,usize,crate::Type)>>());
    println!("primitive_position PrimitiveFloatWindow old_shape_opcode offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_shape_opcode),size_of::<u8>());
    println!("primitive_position PrimitiveFloatWindow old_pop_arena offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_pop_arena),size_of::<&'static mut Vec<Value>>());
    println!("primitive_position PrimitiveFloatWindow old_pop_source offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_pop_source),size_of::<Option<Value>>());
    println!("primitive_position PrimitiveFloatWindow old_pop_returned offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_pop_returned),size_of::<Option<Value>>());
    println!("primitive_position PrimitiveFloatWindow old_pop_caller offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_pop_caller),size_of::<Option<Value>>());
    println!("primitive_position PrimitiveFloatWindow old_pop_matched offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_pop_matched),size_of::<Value>());
    println!("primitive_position PrimitiveFloatWindow old_pop_scalar_source offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_pop_scalar_source),size_of::<u64>());
    println!("primitive_position PrimitiveFloatWindow old_pop_scalar_returned offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_pop_scalar_returned),size_of::<u64>());
    println!("primitive_position PrimitiveFloatWindow old_pop_scalar_caller offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_pop_scalar_caller),size_of::<u64>());
    println!("primitive_position PrimitiveFloatWindow old_float_a offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_float_a),size_of::<u64>());
    println!("primitive_position PrimitiveFloatWindow old_float_b offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_float_b),size_of::<u64>());
    println!("primitive_position PrimitiveFloatWindow old_float_x offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_float_x),size_of::<f64>());
    println!("primitive_position PrimitiveFloatWindow old_float_y offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_float_y),size_of::<f64>());
    println!("primitive_position PrimitiveFloatWindow old_float_bits offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_float_bits),size_of::<u64>());
    println!("primitive_position PrimitiveFloatWindow old_nan_bits_source offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_nan_bits_source),size_of::<u64>());
    println!("primitive_position PrimitiveFloatWindow old_nan_bits_argument offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_nan_bits_argument),size_of::<u64>());
    println!("primitive_position PrimitiveFloatWindow old_nan_bits_returned offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_nan_bits_returned),size_of::<u64>());
    println!("primitive_position PrimitiveFloatWindow old_nan_bits_caller offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_nan_bits_caller),size_of::<u64>());
    println!("primitive_position PrimitiveFloatWindow old_push_value offset={} bytes={}",offset_of!(PrimitiveFloatWindow<'static>,old_push_value),size_of::<Value>());
    assert!(size_of::<PrimitiveFloatWindow<'static>>()<=512,"PrimitiveFloatWindow exceeds original scalar component");
    #[repr(C)]
    struct PrimitiveConversionWindow<'a> {
        old_run_self: &'a mut SpanInstance,
        old_run_target: Option<u32>,
        old_run_finished: bool,
        old_run_opcode: u8,
        old_numeric_self: &'a mut SpanInstance,
        old_numeric_opcode: u8,
        old_numeric_saturating: bool,
        old_numeric_type: crate::Type,
        old_numeric_count: usize,
        old_numeric_frame: &'a Frame,
        new_helper_state_source: &'a mut SpanInstance,
        new_helper_state_argument: &'a mut SpanInstance,
        new_helper_opcode_source: u8,
        new_helper_opcode_argument: u8,
        new_helper_saturating_source: bool,
        new_helper_saturating_argument: bool,
        new_values_state_source: &'a mut SpanInstance,
        new_values_state_argument: &'a mut SpanInstance,
        new_values_arena_source: &'a mut Vec<Value>,
        new_values_arena_returned: &'a mut Vec<Value>,
        new_values_arena_caller: &'a mut Vec<Value>,
        old_primitive_arena_argument: &'a mut Vec<Value>,
        old_primitive_opcode_argument: u8,
        old_primitive_result_source: Result<(), &'static str>,
        old_primitive_result_returned: Result<(), &'static str>,
        new_helper_result_caller: Result<(), &'static str>,
        new_helper_result_returned: Result<(), &'static str>,
        old_owner_result_caller: Result<(), &'static str>,
        old_dispatch_shape_source: Option<(crate::Type,usize,crate::Type)>,
        old_dispatch_shape_returned: Option<(crate::Type,usize,crate::Type)>,
        old_dispatch_shape_caller: Option<(crate::Type,usize,crate::Type)>,
        old_shape_opcode: u8,
        old_pop_arena: &'a mut Vec<Value>,
        old_pop_source: Option<Value>,
        old_pop_returned: Option<Value>,
        old_pop_caller: Option<Value>,
        old_pop_matched: Value,
        old_pop_scalar_source: u64,
        old_pop_scalar_returned: u64,
        old_pop_scalar_caller: u64,
        old_conversion_input: crate::Type,
        old_conversion_output: crate::Type,
        old_conversion_x: f64,
        old_truncated_x: f64,
        old_truncated_bits: u32,
        old_truncated_signed: bool,
        old_truncated_saturating: bool,
        old_truncated_n: f64,
        old_truncated_range: std::ops::Range<f64>,
        old_truncated_range_value: &'a f64,
        old_truncated_value: Value,
        old_truncated_result_source: Result<Value,&'static str>,
        old_truncated_result_returned: Result<Value,&'static str>,
        old_truncated_result_caller: Result<Value,&'static str>,
    }
    println!("primitive_window PrimitiveConversionWindow size={} align={} scalar_limit=512 fits={}",size_of::<PrimitiveConversionWindow<'static>>(),align_of::<PrimitiveConversionWindow<'static>>(),size_of::<PrimitiveConversionWindow<'static>>()<=512);
    println!("primitive_position PrimitiveConversionWindow old_run_self offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_run_self),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveConversionWindow old_run_target offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_run_target),size_of::<Option<u32>>());
    println!("primitive_position PrimitiveConversionWindow old_run_finished offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_run_finished),size_of::<bool>());
    println!("primitive_position PrimitiveConversionWindow old_run_opcode offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_run_opcode),size_of::<u8>());
    println!("primitive_position PrimitiveConversionWindow old_numeric_self offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_numeric_self),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveConversionWindow old_numeric_opcode offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_numeric_opcode),size_of::<u8>());
    println!("primitive_position PrimitiveConversionWindow old_numeric_saturating offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_numeric_saturating),size_of::<bool>());
    println!("primitive_position PrimitiveConversionWindow old_numeric_type offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_numeric_type),size_of::<crate::Type>());
    println!("primitive_position PrimitiveConversionWindow old_numeric_count offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_numeric_count),size_of::<usize>());
    println!("primitive_position PrimitiveConversionWindow old_numeric_frame offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_numeric_frame),size_of::<&'static Frame>());
    println!("primitive_position PrimitiveConversionWindow new_helper_state_source offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,new_helper_state_source),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveConversionWindow new_helper_state_argument offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,new_helper_state_argument),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveConversionWindow new_helper_opcode_source offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,new_helper_opcode_source),size_of::<u8>());
    println!("primitive_position PrimitiveConversionWindow new_helper_opcode_argument offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,new_helper_opcode_argument),size_of::<u8>());
    println!("primitive_position PrimitiveConversionWindow new_helper_saturating_source offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,new_helper_saturating_source),size_of::<bool>());
    println!("primitive_position PrimitiveConversionWindow new_helper_saturating_argument offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,new_helper_saturating_argument),size_of::<bool>());
    println!("primitive_position PrimitiveConversionWindow new_values_state_source offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,new_values_state_source),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveConversionWindow new_values_state_argument offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,new_values_state_argument),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveConversionWindow new_values_arena_source offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,new_values_arena_source),size_of::<&'static mut Vec<Value>>());
    println!("primitive_position PrimitiveConversionWindow new_values_arena_returned offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,new_values_arena_returned),size_of::<&'static mut Vec<Value>>());
    println!("primitive_position PrimitiveConversionWindow new_values_arena_caller offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,new_values_arena_caller),size_of::<&'static mut Vec<Value>>());
    println!("primitive_position PrimitiveConversionWindow old_primitive_arena_argument offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_primitive_arena_argument),size_of::<&'static mut Vec<Value>>());
    println!("primitive_position PrimitiveConversionWindow old_primitive_opcode_argument offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_primitive_opcode_argument),size_of::<u8>());
    println!("primitive_position PrimitiveConversionWindow old_primitive_result_source offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_primitive_result_source),size_of::<Result<(), &'static str>>());
    println!("primitive_position PrimitiveConversionWindow old_primitive_result_returned offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_primitive_result_returned),size_of::<Result<(), &'static str>>());
    println!("primitive_position PrimitiveConversionWindow new_helper_result_caller offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,new_helper_result_caller),size_of::<Result<(), &'static str>>());
    println!("primitive_position PrimitiveConversionWindow new_helper_result_returned offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,new_helper_result_returned),size_of::<Result<(), &'static str>>());
    println!("primitive_position PrimitiveConversionWindow old_owner_result_caller offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_owner_result_caller),size_of::<Result<(), &'static str>>());
    println!("primitive_position PrimitiveConversionWindow old_dispatch_shape_source offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_dispatch_shape_source),size_of::<Option<(crate::Type,usize,crate::Type)>>());
    println!("primitive_position PrimitiveConversionWindow old_dispatch_shape_returned offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_dispatch_shape_returned),size_of::<Option<(crate::Type,usize,crate::Type)>>());
    println!("primitive_position PrimitiveConversionWindow old_dispatch_shape_caller offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_dispatch_shape_caller),size_of::<Option<(crate::Type,usize,crate::Type)>>());
    println!("primitive_position PrimitiveConversionWindow old_shape_opcode offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_shape_opcode),size_of::<u8>());
    println!("primitive_position PrimitiveConversionWindow old_pop_arena offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_pop_arena),size_of::<&'static mut Vec<Value>>());
    println!("primitive_position PrimitiveConversionWindow old_pop_source offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_pop_source),size_of::<Option<Value>>());
    println!("primitive_position PrimitiveConversionWindow old_pop_returned offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_pop_returned),size_of::<Option<Value>>());
    println!("primitive_position PrimitiveConversionWindow old_pop_caller offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_pop_caller),size_of::<Option<Value>>());
    println!("primitive_position PrimitiveConversionWindow old_pop_matched offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_pop_matched),size_of::<Value>());
    println!("primitive_position PrimitiveConversionWindow old_pop_scalar_source offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_pop_scalar_source),size_of::<u64>());
    println!("primitive_position PrimitiveConversionWindow old_pop_scalar_returned offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_pop_scalar_returned),size_of::<u64>());
    println!("primitive_position PrimitiveConversionWindow old_pop_scalar_caller offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_pop_scalar_caller),size_of::<u64>());
    println!("primitive_position PrimitiveConversionWindow old_conversion_input offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_conversion_input),size_of::<crate::Type>());
    println!("primitive_position PrimitiveConversionWindow old_conversion_output offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_conversion_output),size_of::<crate::Type>());
    println!("primitive_position PrimitiveConversionWindow old_conversion_x offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_conversion_x),size_of::<f64>());
    println!("primitive_position PrimitiveConversionWindow old_truncated_x offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_truncated_x),size_of::<f64>());
    println!("primitive_position PrimitiveConversionWindow old_truncated_bits offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_truncated_bits),size_of::<u32>());
    println!("primitive_position PrimitiveConversionWindow old_truncated_signed offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_truncated_signed),size_of::<bool>());
    println!("primitive_position PrimitiveConversionWindow old_truncated_saturating offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_truncated_saturating),size_of::<bool>());
    println!("primitive_position PrimitiveConversionWindow old_truncated_n offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_truncated_n),size_of::<f64>());
    println!("primitive_position PrimitiveConversionWindow old_truncated_range offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_truncated_range),size_of::<std::ops::Range<f64>>());
    println!("primitive_position PrimitiveConversionWindow old_truncated_range_value offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_truncated_range_value),size_of::<&'static f64>());
    println!("primitive_position PrimitiveConversionWindow old_truncated_value offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_truncated_value),size_of::<Value>());
    println!("primitive_position PrimitiveConversionWindow old_truncated_result_source offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_truncated_result_source),size_of::<Result<Value,&'static str>>());
    println!("primitive_position PrimitiveConversionWindow old_truncated_result_returned offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_truncated_result_returned),size_of::<Result<Value,&'static str>>());
    println!("primitive_position PrimitiveConversionWindow old_truncated_result_caller offset={} bytes={}",offset_of!(PrimitiveConversionWindow<'static>,old_truncated_result_caller),size_of::<Result<Value,&'static str>>());
    assert!(size_of::<PrimitiveConversionWindow<'static>>()<=512,"PrimitiveConversionWindow exceeds original scalar component");
    #[repr(C)]
    struct PrimitiveSaturatingWindow<'a> {
        old_run_self: &'a mut SpanInstance,
        old_run_target: Option<u32>,
        old_run_finished: bool,
        old_run_opcode: u8,
        old_numeric_self: &'a mut SpanInstance,
        old_numeric_opcode: u8,
        old_numeric_saturating: bool,
        old_numeric_type: crate::Type,
        old_numeric_count: usize,
        old_numeric_frame: &'a Frame,
        new_helper_state_source: &'a mut SpanInstance,
        new_helper_state_argument: &'a mut SpanInstance,
        new_helper_opcode_source: u8,
        new_helper_opcode_argument: u8,
        new_helper_saturating_source: bool,
        new_helper_saturating_argument: bool,
        new_values_state_source: &'a mut SpanInstance,
        new_values_state_argument: &'a mut SpanInstance,
        new_values_arena_source: &'a mut Vec<Value>,
        new_values_arena_returned: &'a mut Vec<Value>,
        new_values_arena_caller: &'a mut Vec<Value>,
        old_primitive_arena_argument: &'a mut Vec<Value>,
        old_primitive_opcode_argument: u8,
        old_primitive_result_source: Result<(), &'static str>,
        old_primitive_result_returned: Result<(), &'static str>,
        new_helper_result_caller: Result<(), &'static str>,
        new_helper_result_returned: Result<(), &'static str>,
        old_owner_result_caller: Result<(), &'static str>,
        old_dispatch_shape_source: Option<(crate::Type,usize,crate::Type)>,
        old_dispatch_shape_returned: Option<(crate::Type,usize,crate::Type)>,
        old_dispatch_shape_caller: Option<(crate::Type,usize,crate::Type)>,
        old_shape_opcode: u8,
        old_pop_arena: &'a mut Vec<Value>,
        old_pop_source: Option<Value>,
        old_pop_returned: Option<Value>,
        old_pop_caller: Option<Value>,
        old_pop_matched: Value,
        old_pop_scalar_source: u64,
        old_pop_scalar_returned: u64,
        old_pop_scalar_caller: u64,
        old_conversion_input: crate::Type,
        old_conversion_output: crate::Type,
        old_conversion_x: f64,
        old_truncated_x: f64,
        old_truncated_bits: u32,
        old_truncated_signed: bool,
        old_truncated_saturating: bool,
        old_truncated_n: f64,
        old_truncated_range: std::ops::Range<f64>,
        old_truncated_range_value: &'a f64,
        old_truncated_value: Value,
        old_truncated_result_source: Result<Value,&'static str>,
        old_truncated_result_returned: Result<Value,&'static str>,
        old_truncated_result_caller: Result<Value,&'static str>,
        old_sat_shape_source: (crate::Type,crate::Type),
        old_sat_shape_returned: (crate::Type,crate::Type),
        old_sat_shape_caller: (crate::Type,crate::Type),
    }
    println!("primitive_window PrimitiveSaturatingWindow size={} align={} scalar_limit=512 fits={}",size_of::<PrimitiveSaturatingWindow<'static>>(),align_of::<PrimitiveSaturatingWindow<'static>>(),size_of::<PrimitiveSaturatingWindow<'static>>()<=512);
    println!("primitive_position PrimitiveSaturatingWindow old_run_self offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_run_self),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveSaturatingWindow old_run_target offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_run_target),size_of::<Option<u32>>());
    println!("primitive_position PrimitiveSaturatingWindow old_run_finished offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_run_finished),size_of::<bool>());
    println!("primitive_position PrimitiveSaturatingWindow old_run_opcode offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_run_opcode),size_of::<u8>());
    println!("primitive_position PrimitiveSaturatingWindow old_numeric_self offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_numeric_self),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveSaturatingWindow old_numeric_opcode offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_numeric_opcode),size_of::<u8>());
    println!("primitive_position PrimitiveSaturatingWindow old_numeric_saturating offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_numeric_saturating),size_of::<bool>());
    println!("primitive_position PrimitiveSaturatingWindow old_numeric_type offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_numeric_type),size_of::<crate::Type>());
    println!("primitive_position PrimitiveSaturatingWindow old_numeric_count offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_numeric_count),size_of::<usize>());
    println!("primitive_position PrimitiveSaturatingWindow old_numeric_frame offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_numeric_frame),size_of::<&'static Frame>());
    println!("primitive_position PrimitiveSaturatingWindow new_helper_state_source offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,new_helper_state_source),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveSaturatingWindow new_helper_state_argument offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,new_helper_state_argument),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveSaturatingWindow new_helper_opcode_source offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,new_helper_opcode_source),size_of::<u8>());
    println!("primitive_position PrimitiveSaturatingWindow new_helper_opcode_argument offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,new_helper_opcode_argument),size_of::<u8>());
    println!("primitive_position PrimitiveSaturatingWindow new_helper_saturating_source offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,new_helper_saturating_source),size_of::<bool>());
    println!("primitive_position PrimitiveSaturatingWindow new_helper_saturating_argument offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,new_helper_saturating_argument),size_of::<bool>());
    println!("primitive_position PrimitiveSaturatingWindow new_values_state_source offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,new_values_state_source),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveSaturatingWindow new_values_state_argument offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,new_values_state_argument),size_of::<&'static mut SpanInstance>());
    println!("primitive_position PrimitiveSaturatingWindow new_values_arena_source offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,new_values_arena_source),size_of::<&'static mut Vec<Value>>());
    println!("primitive_position PrimitiveSaturatingWindow new_values_arena_returned offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,new_values_arena_returned),size_of::<&'static mut Vec<Value>>());
    println!("primitive_position PrimitiveSaturatingWindow new_values_arena_caller offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,new_values_arena_caller),size_of::<&'static mut Vec<Value>>());
    println!("primitive_position PrimitiveSaturatingWindow old_primitive_arena_argument offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_primitive_arena_argument),size_of::<&'static mut Vec<Value>>());
    println!("primitive_position PrimitiveSaturatingWindow old_primitive_opcode_argument offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_primitive_opcode_argument),size_of::<u8>());
    println!("primitive_position PrimitiveSaturatingWindow old_primitive_result_source offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_primitive_result_source),size_of::<Result<(), &'static str>>());
    println!("primitive_position PrimitiveSaturatingWindow old_primitive_result_returned offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_primitive_result_returned),size_of::<Result<(), &'static str>>());
    println!("primitive_position PrimitiveSaturatingWindow new_helper_result_caller offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,new_helper_result_caller),size_of::<Result<(), &'static str>>());
    println!("primitive_position PrimitiveSaturatingWindow new_helper_result_returned offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,new_helper_result_returned),size_of::<Result<(), &'static str>>());
    println!("primitive_position PrimitiveSaturatingWindow old_owner_result_caller offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_owner_result_caller),size_of::<Result<(), &'static str>>());
    println!("primitive_position PrimitiveSaturatingWindow old_dispatch_shape_source offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_dispatch_shape_source),size_of::<Option<(crate::Type,usize,crate::Type)>>());
    println!("primitive_position PrimitiveSaturatingWindow old_dispatch_shape_returned offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_dispatch_shape_returned),size_of::<Option<(crate::Type,usize,crate::Type)>>());
    println!("primitive_position PrimitiveSaturatingWindow old_dispatch_shape_caller offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_dispatch_shape_caller),size_of::<Option<(crate::Type,usize,crate::Type)>>());
    println!("primitive_position PrimitiveSaturatingWindow old_shape_opcode offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_shape_opcode),size_of::<u8>());
    println!("primitive_position PrimitiveSaturatingWindow old_pop_arena offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_pop_arena),size_of::<&'static mut Vec<Value>>());
    println!("primitive_position PrimitiveSaturatingWindow old_pop_source offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_pop_source),size_of::<Option<Value>>());
    println!("primitive_position PrimitiveSaturatingWindow old_pop_returned offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_pop_returned),size_of::<Option<Value>>());
    println!("primitive_position PrimitiveSaturatingWindow old_pop_caller offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_pop_caller),size_of::<Option<Value>>());
    println!("primitive_position PrimitiveSaturatingWindow old_pop_matched offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_pop_matched),size_of::<Value>());
    println!("primitive_position PrimitiveSaturatingWindow old_pop_scalar_source offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_pop_scalar_source),size_of::<u64>());
    println!("primitive_position PrimitiveSaturatingWindow old_pop_scalar_returned offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_pop_scalar_returned),size_of::<u64>());
    println!("primitive_position PrimitiveSaturatingWindow old_pop_scalar_caller offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_pop_scalar_caller),size_of::<u64>());
    println!("primitive_position PrimitiveSaturatingWindow old_conversion_input offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_conversion_input),size_of::<crate::Type>());
    println!("primitive_position PrimitiveSaturatingWindow old_conversion_output offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_conversion_output),size_of::<crate::Type>());
    println!("primitive_position PrimitiveSaturatingWindow old_conversion_x offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_conversion_x),size_of::<f64>());
    println!("primitive_position PrimitiveSaturatingWindow old_truncated_x offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_truncated_x),size_of::<f64>());
    println!("primitive_position PrimitiveSaturatingWindow old_truncated_bits offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_truncated_bits),size_of::<u32>());
    println!("primitive_position PrimitiveSaturatingWindow old_truncated_signed offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_truncated_signed),size_of::<bool>());
    println!("primitive_position PrimitiveSaturatingWindow old_truncated_saturating offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_truncated_saturating),size_of::<bool>());
    println!("primitive_position PrimitiveSaturatingWindow old_truncated_n offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_truncated_n),size_of::<f64>());
    println!("primitive_position PrimitiveSaturatingWindow old_truncated_range offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_truncated_range),size_of::<std::ops::Range<f64>>());
    println!("primitive_position PrimitiveSaturatingWindow old_truncated_range_value offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_truncated_range_value),size_of::<&'static f64>());
    println!("primitive_position PrimitiveSaturatingWindow old_truncated_value offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_truncated_value),size_of::<Value>());
    println!("primitive_position PrimitiveSaturatingWindow old_truncated_result_source offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_truncated_result_source),size_of::<Result<Value,&'static str>>());
    println!("primitive_position PrimitiveSaturatingWindow old_truncated_result_returned offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_truncated_result_returned),size_of::<Result<Value,&'static str>>());
    println!("primitive_position PrimitiveSaturatingWindow old_truncated_result_caller offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_truncated_result_caller),size_of::<Result<Value,&'static str>>());
    println!("primitive_position PrimitiveSaturatingWindow old_sat_shape_source offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_sat_shape_source),size_of::<(crate::Type,crate::Type)>());
    println!("primitive_position PrimitiveSaturatingWindow old_sat_shape_returned offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_sat_shape_returned),size_of::<(crate::Type,crate::Type)>());
    println!("primitive_position PrimitiveSaturatingWindow old_sat_shape_caller offset={} bytes={}",offset_of!(PrimitiveSaturatingWindow<'static>,old_sat_shape_caller),size_of::<(crate::Type,crate::Type)>());
    assert!(size_of::<PrimitiveSaturatingWindow<'static>>()<=512,"PrimitiveSaturatingWindow exceeds original scalar component");
    println!("numeric_reservation {}",size_of::<SpanInstance>()-size_of::<FunctionCache>()+3*size_of::<ExecutionFailure>()+2*size_of::<CacheFailure>()+size_of::<crate::experimental::cache::DecodedInstruction>()+size_of::<Control>()+size_of::<ScalarReader<'static>>()+512);
    macro_rules! fields { ($t:ty; $($f:ident),+) => {$({ println!("numeric_offset {} {} {}",stringify!($t),stringify!($f),offset_of!($t,$f)); })+}; }
    fields!(Frame; function,pc,base,operands,controls,result,pin);
    fields!(Control; kind,start,end,height,result);
    fields!(SpanInstance; cache,budget,cancellation,usage,failure,memory,table,globals,values,controls,frames,function,offset);
    println!("numeric_owner Frame {} {}",size_of::<Frame>(),align_of::<Frame>());
    println!("numeric_owner Control {} {}",size_of::<Control>(),align_of::<Control>());
    println!("numeric_owner SpanInstance {} {}",size_of::<SpanInstance>(),align_of::<SpanInstance>());
}
