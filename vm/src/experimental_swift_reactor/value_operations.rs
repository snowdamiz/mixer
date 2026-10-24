//! Accounted private zero-frame operations on the original reactor value arena.
//! The accepted owner/frame layouts remain unchanged. No instruction loop exists.
use super::*;
use crate::experimental_swift_reactor::ValidatedSwiftReactor;

/// Exactly the two possible returned slots accepted by operation completion.
/// The caller takes its phase/result out before supplying these slots. Copies
/// retained as diagnostics are separately covered by PERMANENT_BYTES.
pub(crate) struct ValueOperationStorage<'a> {
    pub preparation: Option<Result<ExecutionOperationPhase<'a>, SwiftRunFailure>>,
    pub outcome: Option<Result<Option<Value>, SwiftRunFailure>>,
}

/// Every position here is additional to all accepted construction/cleanup rows.
/// Entire field sizes are added, including containing padding; no interior
/// padding, old aliases or old diagnostic positions supply capacity.
struct PermanentPositions {
    owner_argument: &'static mut SwiftReactorInstance,
    cursor_argument: Cursor,
    control_option: &'static mut Option<RuntimeControl>,
    cache_option: &'static mut Option<SwiftFunctionCache>,
    wasi_option: &'static mut Option<AccountedWasi>,
    state_option: &'static mut Option<SwiftExecutionState>,
    lifecycle_borrow: &'static mut Lifecycle,
    control_borrow: &'static mut RuntimeControl,
    cache_borrow: &'static mut SwiftFunctionCache,
    wasi_borrow: &'static mut AccountedWasi,
    state_borrow: &'static mut SwiftExecutionState,
    owner_checks_source: [Result<(), SwiftRunFailure>; 3],
    owner_checks_caller: [Result<(), SwiftRunFailure>; 3],
    wasi_pair_source: Result<WasiUsage, SwiftRunFailure>,
    wasi_pair_caller: Result<WasiUsage, SwiftRunFailure>,
    ticket_loop: std::slice::Iter<'static, Option<ReservationTicket>>,
    ticket_option: &'static Option<ReservationTicket>,
    ticket_borrow: &'static ReservationTicket,
    ticket_check_source: Result<(), SwiftRunFailure>,
    ticket_check_caller: Result<(), SwiftRunFailure>,
    ticket_option_source: Option<&'static ReservationTicket>,
    ticket_option_caller: Option<&'static ReservationTicket>,
    header_borrow: &'static ReservationTicket,
    header_check_source: Result<(), SwiftRunFailure>,
    header_check_caller: Result<(), SwiftRunFailure>,
    preflight_usage_source: SwiftRunUsage,
    preflight_usage_caller: SwiftRunUsage,
    preflight_live_source: SwiftLiveUsage,
    preflight_live_caller: SwiftLiveUsage,
    preflight_cache_usage_source: super::super::cache::SwiftCacheUsage,
    preflight_cache_usage_caller: super::super::cache::SwiftCacheUsage,
    preflight_empty_state_conditions: [bool; 8],
    preflight_cursor_source_argument_positions: [Cursor; 12],
    preflight_control_reborrow_chain: [&'static mut RuntimeControl; 3],
    preflight_wasi_reborrow_chain: [&'static AccountedWasi; 3],
    preflight_optional_wasi_source_argument_parameter: [Option<&'static AccountedWasi>; 3],
    preflight_cache_control_temporary: super::super::cache::CacheControl<'static>,
    preflight_cache_control_receiver_chain:
        [&'static mut super::super::cache::CacheControl<'static>; 3],
    preflight_cache_receiver_chain: [&'static SwiftFunctionCache; 3],
    // checked_usage and the four unit-result `?` call sites have distinct Try
    // branch/residual types, charged before any operation enlargement occurs.
    preflight_wasi_try_source_return_caller:
        [std::ops::ControlFlow<Result<std::convert::Infallible, SwiftRunFailure>, WasiUsage>; 3],
    preflight_wasi_residual_source_argument_parameter:
        [Result<std::convert::Infallible, SwiftRunFailure>; 3],
    preflight_unit_try_source_return_caller:
        [std::ops::ControlFlow<Result<std::convert::Infallible, SwiftRunFailure>, ()>; 12],
    preflight_unit_residual_source_argument_parameter:
        [Result<std::convert::Infallible, SwiftRunFailure>; 12],
    previous_bound: usize,
    bound_source: Option<usize>,
    bound_caller: Option<usize>,
    phase_constant_source_return_caller: [Option<usize>; 3],
    enlarged_bound: usize,
    enlargement_source: Result<(), SwiftRunFailure>,
    enlargement_caller: Result<(), SwiftRunFailure>,
    preparation_source: Result<ExecutionOperationPhase<'static>, SwiftRunFailure>,
    preparation_return: Result<ExecutionOperationPhase<'static>, SwiftRunFailure>,
    preparation_caller: Option<Result<ExecutionOperationPhase<'static>, SwiftRunFailure>>,
    preparation_match: Result<ExecutionOperationPhase<'static>, SwiftRunFailure>,
    preflight_fault: Fault,
    preflight_fault_argument: Fault,
    preflight_failure_source: SwiftRunFailure,
    preflight_failure_return: SwiftRunFailure,
    preflight_failure_caller: SwiftRunFailure,
    preflight_observation: [Option<WasiUsage>; 6],
    completion_self: ExecutionOperationPhase<'static>,
    completion_self_argument: ExecutionOperationPhase<'static>,
    completion_parts: ExecutionParts<'static, SwiftMode>,
    completion_operation: SwiftExecutionOperation<'static>,
    completion_storage_source: ValueOperationStorage<'static>,
    completion_storage_argument: ValueOperationStorage<'static>,
    completion_drop_argument: (
        ExecutionParts<'static, SwiftMode>,
        ValueOperationStorage<'static>,
    ),
    completion_clear_return: Result<(), SwiftRunFailure>,
    completion_clear_caller: Result<(), SwiftRunFailure>,
    completion_restore_return: Result<(), SwiftRunFailure>,
    completion_restore_caller: Result<(), SwiftRunFailure>,
    completion_result_source: Result<(), SwiftRunFailure>,
    completion_result_return: Result<(), SwiftRunFailure>,
    completion_result_caller: Result<(), SwiftRunFailure>,
    completion_observation: [Option<WasiUsage>; 3],
    caller_outcome_source: Option<Result<Option<Value>, SwiftRunFailure>>,
    caller_outcome_return: Option<Result<Option<Value>, SwiftRunFailure>>,
    caller_outcome_slot: Option<Result<Option<Value>, SwiftRunFailure>>,
    retained_caller_failure: Option<SwiftRunFailure>,
    retained_caller_value: Option<Value>,
    retained_caller_usage: Option<SwiftRunUsage>,
    retained_caller_observation: Option<WasiUsage>,
    retained_cleanup_source: Option<SwiftRunFailure>,
    retained_cleanup_argument: Option<SwiftRunFailure>,
    retained_cleanup_storage: Option<SwiftRunFailure>,
}

/// Additional simultaneously charged operation positions. The sum is purposely
/// conservative across helper windows. Every array element names a distinct
/// source/return/caller or callsite role; none substitutes for an owner payload.
struct ActivePositions {
    phase: ExecutionOperationPhase<'static>,
    phase_reference_source: &'static mut ExecutionOperationPhase<'static>,
    phase_reference_argument: &'static mut ExecutionOperationPhase<'static>,
    parts_reference: &'static mut ExecutionParts<'static, SwiftMode>,
    operation_reference: &'static mut SwiftExecutionOperation<'static>,
    helper_operation_reborrow_chain: [&'static mut SwiftExecutionOperation<'static>; 6],
    helper_control_reborrow_chain: [&'static mut RuntimeControl; 3],
    helper_wasi_reborrow_chain: [&'static AccountedWasi; 3],
    push_work_cursor_source_argument: [Cursor; 2],
    pop_work_cursor_source_argument: [Cursor; 2],
    numeric_work_cursor_source_argument: [Cursor; 2],
    push_admission_cursor_source_argument: [Cursor; 2],
    numeric_trap_cursor_source_argument: [Cursor; 2],
    invariant_cursor_source_argument: [Cursor; 2],
    unsupported_cursor_source_argument: [Cursor; 2],
    limit_cursor_source_argument: [Cursor; 2],
    work_component_source_argument_parameter: [Work; 9],
    live_resource_source_argument_parameter: [Live; 12],
    values_reference_source: &'static mut Vec<Value>,
    values_reference_argument: &'static mut Vec<Value>,
    values_reference_return: &'static mut Vec<Value>,
    values_adapter_argument: &'static mut Vec<Value>,
    values_adapter_return: &'static mut Vec<Value>,
    values_adapter_caller: &'static mut Vec<Value>,
    values_read_source: &'static [Value],
    values_read_argument: &'static [Value],
    values_read_caller: &'static [Value],
    policy_reference: &'static crate::experimental::policy::Policy<'static>,
    proof_cache_receiver_source_argument_parameter: [&'static SwiftFunctionCache; 3],
    proof_adopted_receiver_source_argument_parameter: [&'static AdoptedProof; 3],
    proof_source_return_caller: [&'static ValidatedSwiftReactor; 3],
    policy_receiver_source_argument_parameter: [&'static ValidatedSwiftReactor; 3],
    policy_source_return_caller: [&'static crate::experimental::policy::Policy<'static>; 3],
    operand_base_source: usize,
    operand_base_argument: usize,
    operand_limit_source: usize,
    operand_limit_argument: usize,
    frame_option_source_return_caller: [Option<&'static SwiftFrame>; 3],
    input_value_source: Value,
    input_value_argument: Value,
    input_value_push: Value,
    pop_value_source: Value,
    pop_value_return: Result<Value, SwiftRunFailure>,
    pop_value_caller: Result<Value, SwiftRunFailure>,
    pop_value_match: Result<Value, SwiftRunFailure>,
    primitive_results_source: [Result<(), SwiftRunFailure>; 5],
    primitive_results_return: [Result<(), SwiftRunFailure>; 5],
    primitive_results_caller: [Result<(), SwiftRunFailure>; 5],
    work_results_source: [Result<(), SwiftRunFailure>; 3],
    work_results_caller: [Result<(), SwiftRunFailure>; 3],
    live_results_source: [Result<(), SwiftRunFailure>; 4],
    live_results_caller: [Result<(), SwiftRunFailure>; 4],
    // Each of push/pop/numeric has three unit-result `?` sites. Every site
    // receives its own source/return/caller and residual transfer positions.
    unit_try_source_return_caller:
        [std::ops::ControlFlow<Result<std::convert::Infallible, SwiftRunFailure>, ()>; 27],
    unit_residual_source_argument_parameter:
        [Result<std::convert::Infallible, SwiftRunFailure>; 27],
    observation_source_return_argument: [Option<WasiUsage>; 12],
    mismatch_usage_source: SwiftRunUsage,
    mismatch_usage_return: SwiftRunUsage,
    shape_source: (Type, usize, Type),
    shape_return: Option<(Type, usize, Type)>,
    shape_caller: (Type, usize, Type),
    saturating_shape_source: (Type, Type),
    saturating_shape_return: (Type, Type),
    saturating_shape_caller: (Type, Type),
    opcode_source_argument_return: [u8; 3],
    saturating_source_argument: [bool; 2],
    before: usize,
    removed_source: Option<usize>,
    removed_caller: usize,
    checked_operand_source: Option<usize>,
    checked_operand_caller: Option<usize>,
    work_credits_source: usize,
    work_credits_argument: u64,
    available_operands: usize,
    count_source_argument: [usize; 2],
    type_source_argument: [Type; 2],
    unsupported_opcode_borrow: &'static u8,
    actual_length_source_return: [usize; 2],
    scalar_capacity_source_return: [usize; 2],
    operand_type_iterator: std::slice::Iter<'static, Value>,
    operand_type_reference: &'static Value,
    operand_type_source_return: [Type; 2],
    numeric_raw_source: Result<(), &'static str>,
    numeric_raw_return: Result<(), &'static str>,
    numeric_raw_caller: Result<(), &'static str>,
    numeric_raw_observed: Result<(), &'static str>,
    numeric_error_code: &'static str,
    trap_fault_source_argument: [Fault; 2],
    invariant_fault_source_argument: [Fault; 2],
    limit_fault_source_argument: [Fault; 2],
    failure_source_return_caller: [SwiftRunFailure; 3],
    range_source_argument: std::ops::RangeInclusive<u8>,
    unsupported_condition: bool,
    // Shared primitive scalar/pop/convert windows. These are new Swift roles;
    // Frozen's independently accepted 512-byte component is never borrowed.
    primitive_arena_reborrows: [&'static mut Vec<Value>; 4],
    primitive_opcode_arguments: [u8; 3],
    primitive_saturating_parameter: bool,
    primitive_shape_positions: [(Type, usize, Type); 3],
    primitive_integer_input_output: [Type; 2],
    primitive_integer_count: usize,
    primitive_pop_values: [Option<Value>; 3],
    primitive_i32_positions: [i32; 4],
    primitive_u32_positions: [u32; 4],
    primitive_i64_positions: [i64; 4],
    primitive_u64_positions: [u64; 4],
    primitive_f32_positions: [f32; 4],
    primitive_f64_positions: [f64; 4],
    primitive_checked_i32: [Option<i32>; 3],
    primitive_checked_i64: [Option<i64>; 3],
    primitive_div_i32_result_source_return_caller: [Result<i32, &'static str>; 3],
    primitive_div_i64_result_source_return_caller: [Result<i64, &'static str>; 3],
    primitive_div_i32_try_source_return_caller:
        [std::ops::ControlFlow<Result<std::convert::Infallible, &'static str>, i32>; 3],
    primitive_div_i64_try_source_return_caller:
        [std::ops::ControlFlow<Result<std::convert::Infallible, &'static str>, i64>; 3],
    primitive_div_residual_source_argument_parameter:
        [Result<std::convert::Infallible, &'static str>; 6],
    // a, b, bits and arithmetic_nan source/argument/return/caller positions.
    // These are separate from the integer/bit-conversion scalar windows above.
    primitive_nan32_bits: [u32; 7],
    primitive_nan64_bits: [u64; 7],
    // Distinct nested helper roles; wrapper shape slots remain separately live.
    primitive_dispatch_shape_source_return_caller: [Option<(Type, usize, Type)>; 3],
    primitive_dispatch_shape_present: [bool; 2],
    primitive_conversion_shape_source_return_caller: [Option<(Type, usize, Type)>; 3],
    primitive_conversion_input_output: [Type; 2],
    primitive_conversion_x: f64,
    primitive_saturating_shape_source_return_caller: [(Type, Type); 3],
    primitive_saturating_input_output: [Type; 2],
    primitive_saturating_x: f64,
    truncated_result_source_return_caller: [Result<Value, &'static str>; 3],
    truncated_try_source_return_caller:
        [std::ops::ControlFlow<Result<std::convert::Infallible, &'static str>, Value>; 3],
    truncated_residual_source_argument_parameter:
        [Result<std::convert::Infallible, &'static str>; 3],
    truncated_x_source_argument_parameter: [f64; 3],
    truncated_n: f64,
    truncated_bits_source_argument_parameter: [u32; 3],
    truncated_signed_source_argument_parameter: [bool; 3],
    truncated_saturating_source_argument_parameter: [bool; 3],
    truncated_match_source: (u32, bool),
    truncated_value_source_return_caller: [Value; 3],
    truncated_nan_source_return: [bool; 2],
    truncated_i32_signed_range: std::ops::Range<f64>,
    truncated_i32_unsigned_range: std::ops::Range<f64>,
    truncated_i64_signed_range: std::ops::Range<f64>,
    truncated_i64_unsigned_range: std::ops::Range<f64>,
    // Four disjoint conversion branches, each with source/argument/parameter
    // range/item borrows and contains-result/negation values. All are charged
    // conservatively together; no other primitive scalar slot supplies credit.
    truncated_range_source_argument_parameter: [&'static std::ops::Range<f64>; 12],
    truncated_n_source_argument_parameter: [&'static f64; 12],
    truncated_contains_return_caller_negation: [bool; 12],
    primitive_push_values: [Value; 3],
    primitive_return_results: [Result<(), &'static str>; 4],
}

pub(super) const PERMANENT_BYTES: usize = size_of::<PermanentPositions>();
pub(super) const ACTIVE_BYTES: usize = size_of::<ActivePositions>() + size_of::<super::frame_operations::DiagnosticValuePositions>();

// The named-row traversal must not execute in the pre-admission window. Const
// evaluation is required in Debug too, rather than relying on optimization.
pub(super) const VALUE_OPERATION_BYTES: Option<usize> = match named_bytes("operation") {
    Some(declared) => declared.checked_add(ACTIVE_BYTES),
    None => None,
};
pub(crate) fn value_operation_bytes() -> Option<usize> {
    VALUE_OPERATION_BYTES
}

impl SwiftReactorInstance {
    /// Real original-owner route, restricted to the implemented zero-frame slice.
    /// On any preflight/admission failure all owners stay exactly in this slot.
    pub(crate) fn prepare_value_operation(
        &mut self,
        cursor: Cursor,
    ) -> Result<ExecutionOperationPhase<'_>, SwiftRunFailure> {
        let Self {
            control,
            cache,
            wasi,
            state,
            lifecycle,
        } = self;
        let control = control.as_mut().expect("constructed control");
        let wasi = wasi.as_mut().expect("constructed WASI");
        wasi.checked_usage(control, cursor)?;
        let cache = cache.as_mut().expect("constructed cache");
        cache.check_owner(control, Some(wasi), cursor)?;
        let state = state.as_mut().expect("constructed state");
        let live = control.usage(Some(wasi.usage())).live;
        if matches!(lifecycle, Lifecycle::Terminal)
            || !state.frame_cleanup.is_empty()
            || !state.frames.is_empty()
            || !state.controls.is_empty()
            || !state.values.is_empty()
            || cache.usage().active_pins != 0
            || live.values.current != 0
            || live.controls.current != 0
            || live.frames.current != 0
            || live.active_pins.current != 0
        {
            return Err(construction_failure(
                control,
                wasi,
                cursor,
                SwiftRunFailureKind::Invariant,
                "swift_execution_value_operation_nonempty",
            ));
        }
        let header = match state.execution_header.as_ref() {
            Some(header) => header,
            None => return Err(layout_failure(control, wasi, cursor)),
        };
        control.check_reservation_owner(header, cursor, Some(wasi.usage()))?;
        for ticket in &state.buffers {
            let ticket = match ticket.as_ref() {
                Some(ticket) => ticket,
                None => return Err(layout_failure(control, wasi, cursor)),
            };
            control.check_reservation_owner(ticket, cursor, Some(wasi.usage()))?;
        }
        frame_operations::original_owners(control, cache, wasi, state, cursor)?;
        let previous_bound = control
            .usage(Some(wasi.usage()))
            .reservations
            .construction
            .current;
        let bound = match value_operation_bytes() {
            Some(bytes) => match previous_bound.checked_add(bytes) {
                Some(bound) => bound,
                None => return Err(layout_failure(control, wasi, cursor)),
            },
            None => return Err(layout_failure(control, wasi, cursor)),
        };
        control.enlarge_construction_with_wasi(bound, cursor, Some(wasi.usage()))?;
        Ok(ExecutionOperationPhase {
            parts: ExecutionParts {
                cache,
                memory: &mut state.memory,
                table: &mut state.table,
                globals: &mut state.globals,
                values: &mut state.values,
                controls: &mut state.controls,
                frames: &mut state.frames,
            },
            operation: SwiftExecutionOperation {
                control,
                wasi,
                cursor,
            },
            previous_bound,
        })
    }
}

impl<'a> ExecutionOperationPhase<'a> {
    pub(crate) fn push_value(&mut self, value: Value) -> Result<(), SwiftRunFailure> {
        let operand_base = match self.parts.frames.last() {
            Some(frame) => frame.operands,
            None => 0,
        };
        let operand_limit = self.parts.cache.proof().decode_policy().operand_stack();
        primitive_push(
            self.parts.values,
            operand_base,
            operand_limit,
            &mut self.operation,
            value,
        )
    }
    pub(crate) fn pop_value(&mut self) -> Result<Value, SwiftRunFailure> {
        let operand_base = match self.parts.frames.last() {
            Some(frame) => frame.operands,
            None => 0,
        };
        primitive_pop(self.parts.values, operand_base, &mut self.operation)
    }
    pub(crate) fn numeric_value(
        &mut self,
        opcode: u8,
        saturating: bool,
    ) -> Result<(), SwiftRunFailure> {
        let operand_base = match self.parts.frames.last() {
            Some(frame) => frame.operands,
            None => 0,
        };
        primitive_numeric(
            self.parts.values,
            operand_base,
            &mut self.operation,
            opcode,
            saturating,
        )
    }
    /// Clear the actual zero-frame arena despite cancellation/terminal failure,
    /// then destroy both supplied return slots before restoring the exact bound.
    /// The caller retains its copied operation outcome in the permanent envelope.
    pub(crate) fn complete_values(
        self,
        storage: ValueOperationStorage<'a>,
    ) -> Result<(), SwiftRunFailure> {
        let Self {
            parts,
            mut operation,
            previous_bound,
        } = self;
        let cleared = primitive_clear(parts.values, &mut operation);
        let SwiftExecutionOperation { control, wasi, .. } = operation;
        let restored = control.end_construction_phase_with_wasi(
            (parts, storage),
            previous_bound,
            Some(wasi.usage()),
        );
        cleared.and(restored)
    }
}

#[cfg(test)]
#[path = "value_operation_tests.rs"]
mod tests;

impl NumericMode for SwiftMode {
    type NumericState<'a> = Vec<Value>;

    fn values_mut<'short>(state: &'short mut Self::NumericState<'_>) -> &'short mut Vec<Value> {
        state
    }
}

fn primitive_invariant(operation: &mut SwiftExecutionOperation<'_>) -> SwiftRunFailure {
    operation.control.fail(
        operation.cursor,
        Fault::new(
            SwiftRunFailureKind::Invariant,
            "swift_execution_value_invariant",
        ),
        Some(operation.wasi.usage()),
    )
}

fn primitive_values_match(
    values: &[Value],
    operation: &mut SwiftExecutionOperation<'_>,
) -> Result<(), SwiftRunFailure> {
    if operation
        .control
        .usage(Some(operation.wasi.usage()))
        .live
        .values
        .current
        != values.len()
    {
        return Err(primitive_invariant(operation));
    }
    Ok(())
}

fn primitive_push(
    values: &mut Vec<Value>,
    operand_base: usize,
    operand_limit: usize,
    operation: &mut SwiftExecutionOperation<'_>,
    value: Value,
) -> Result<(), SwiftRunFailure> {
    #[cfg(test)]
    super::frame_operations::control_work_checkpoint(operation.control);
    operation.control.work_with_wasi(
        Work::Execution,
        1,
        operation.cursor,
        Some(operation.wasi.usage()),
    )?;
    primitive_values_match(values, operation)?;
    let Some(operands) = values.len().checked_sub(operand_base) else {
        return Err(primitive_invariant(operation));
    };
    if operands >= operand_limit {
        let mut fault = Fault::new(
            SwiftRunFailureKind::ValueLimit,
            "swift_execution_operand_limit",
        );
        fault.resource = Some(SwiftRunResource::Values);
        fault.attempted = operands.saturating_add(1) as u64;
        fault.limit = operand_limit as u64;
        return Err(operation
            .control
            .fail(operation.cursor, fault, Some(operation.wasi.usage())));
    }
    if values.len() == {
        #[cfg(test)]
        {
            super::frame_operations::observed_push_capacity(values.capacity(), values.len())
        }
        #[cfg(not(test))]
        {
            values.capacity()
        }
    } {
        let mut fault = Fault::new(
            SwiftRunFailureKind::ValueLimit,
            "swift_execution_value_capacity",
        );
        fault.resource = Some(SwiftRunResource::Values);
        fault.attempted = values.len().saturating_add(1) as u64;
        fault.limit = values.capacity() as u64;
        return Err(operation
            .control
            .fail(operation.cursor, fault, Some(operation.wasi.usage())));
    }
    // Last fallible admission precedes the infallible publication into known room.
    operation.control.add_live_with_wasi(
        Live::Values,
        1,
        operation.cursor,
        Some(operation.wasi.usage()),
    )?;
    values.push(value);
    Ok(())
}

fn primitive_pop(
    values: &mut Vec<Value>,
    operand_base: usize,
    operation: &mut SwiftExecutionOperation<'_>,
) -> Result<Value, SwiftRunFailure> {
    #[cfg(test)]
    super::frame_operations::control_work_checkpoint(operation.control);
    operation.control.work_with_wasi(
        Work::Execution,
        1,
        operation.cursor,
        Some(operation.wasi.usage()),
    )?;
    primitive_values_match(values, operation)?;
    if values.len() <= operand_base {
        return Err(primitive_invariant(operation));
    }
    let value = values.pop().expect("checked operand exists");
    #[cfg(test)]
    super::frame_operations::control_after_value_pop(operation.control);
    operation.control.remove_live_at_with_wasi(
        Live::Values,
        1,
        operation.cursor,
        Some(operation.wasi.usage()),
    )?;
    Ok(value)
}

fn primitive_numeric(
    values: &mut Vec<Value>,
    operand_base: usize,
    operation: &mut SwiftExecutionOperation<'_>,
    opcode: u8,
    saturating: bool,
) -> Result<(), SwiftRunFailure> {
    // Numeric shape helpers are intentionally partial outside admitted opcodes.
    if if saturating {
        opcode > 7
    } else {
        !(0x45..=0xc4).contains(&opcode)
    } {
        return Err(operation.control.fail(
            operation.cursor,
            Fault::new(
                SwiftRunFailureKind::UnsupportedEnvironment,
                "swift_execution_unsupported_numeric",
            ),
            Some(operation.wasi.usage()),
        ));
    }
    primitive_values_match(values, operation)?;
    let (ty, count, _) = if saturating {
        let (input, output) = crate::float::saturating_shape(opcode);
        (input, 1, output)
    } else {
        match crate::float::shape(opcode) {
            Some(shape) => shape,
            None => crate::validate::numeric_type(opcode),
        }
    };
    let before = values.len();
    let available = match before.checked_sub(operand_base) {
        Some(available) => available,
        None => return Err(primitive_invariant(operation)),
    };
    if available < count {
        return Err(primitive_invariant(operation));
    }
    for value in &values[before - count..] {
        if value.ty() != ty {
            return Err(primitive_invariant(operation));
        }
    }
    operation.control.work_with_wasi(
        Work::Execution,
        (count + 1) as u64,
        operation.cursor,
        Some(operation.wasi.usage()),
    )?;
    // The only arithmetic body is the already accepted shared primitive.
    let result =
        crate::experimental::execution::borrowed::numeric::<SwiftMode>(values, opcode, saturating);
    let Some(removed) = before.checked_sub(values.len()) else {
        return Err(primitive_invariant(operation));
    };
    #[cfg(test)]
    super::frame_operations::diagnostic_numeric_before_remove(operation.control);
    // Keep the actual primitive Result alive through after-effect reconciliation.
    // This never checks cancellation/deadline/work or admits increased live data.
    operation.control.remove_live_at_with_wasi(
        Live::Values,
        removed,
        operation.cursor,
        Some(operation.wasi.usage()),
    )?;
    match result {
        Ok(()) => Ok(()),
        Err(code) => Err(operation.control.fail(
            operation.cursor,
            Fault::new(SwiftRunFailureKind::GuestTrap, code),
            Some(operation.wasi.usage()),
        )),
    }
}

fn primitive_clear(
    values: &mut Vec<Value>,
    operation: &mut SwiftExecutionOperation<'_>,
) -> Result<(), SwiftRunFailure> {
    let mismatch = primitive_values_match(values, operation);
    let removed = values.len();
    values.clear();
    let removal = operation.control.remove_live_with_wasi(
        Live::Values,
        removed,
        Some(operation.wasi.usage()),
    );
    mismatch.and(removal)
}
