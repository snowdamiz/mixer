// Verification-only proposed private operation bodies. Not linked into product.
// Root review is required before these bodies or their accounting are applied.

impl NumericMode for SwiftMode {
    type NumericState<'a> = Vec<Value>;

    fn values_mut<'short>(state: &'short mut Self::NumericState<'_>) -> &'short mut Vec<Value> {
        state
    }
}

fn primitive_invariant(operation: &mut SwiftExecutionOperation<'_>) -> SwiftRunFailure {
    operation.control.fail(
        operation.cursor,
        Fault::new(SwiftRunFailureKind::Invariant, "swift_execution_value_invariant"),
        Some(operation.wasi.usage()),
    )
}

fn primitive_values_match(values: &[Value], operation: &mut SwiftExecutionOperation<'_>) -> Result<(), SwiftRunFailure> {
    if operation.control.usage(Some(operation.wasi.usage())).live.values.current != values.len() {
        return Err(primitive_invariant(operation));
    }
    Ok(())
}

fn primitive_push(values: &mut Vec<Value>, operand_base: usize, operand_limit: usize,
    operation: &mut SwiftExecutionOperation<'_>, value: Value) -> Result<(), SwiftRunFailure> {
    operation.control.work_with_wasi(Work::Execution, 1, operation.cursor, Some(operation.wasi.usage()))?;
    primitive_values_match(values, operation)?;
    let Some(operands) = values.len().checked_sub(operand_base) else {
        return Err(primitive_invariant(operation));
    };
    if operands >= operand_limit || values.len() == values.capacity() {
        return Err(primitive_invariant(operation));
    }
    // Last fallible admission precedes the infallible publication into known room.
    operation.control.add_live_with_wasi(Live::Values, 1, operation.cursor, Some(operation.wasi.usage()))?;
    values.push(value);
    Ok(())
}

fn primitive_pop(values: &mut Vec<Value>, operand_base: usize,
    operation: &mut SwiftExecutionOperation<'_>) -> Result<Value, SwiftRunFailure> {
    operation.control.work_with_wasi(Work::Execution, 1, operation.cursor, Some(operation.wasi.usage()))?;
    primitive_values_match(values, operation)?;
    if values.len() <= operand_base {
        return Err(primitive_invariant(operation));
    }
    let value = values.pop().expect("checked operand exists");
    operation.control.remove_live_with_wasi(Live::Values, 1, Some(operation.wasi.usage()))?;
    Ok(value)
}

fn primitive_numeric(values: &mut Vec<Value>, operand_base: usize,
    operation: &mut SwiftExecutionOperation<'_>, opcode: u8, saturating: bool) -> Result<(), SwiftRunFailure> {
    // Numeric shape helpers are intentionally partial outside admitted opcodes.
    if if saturating { opcode > 7 } else { !(0x45..=0xc4).contains(&opcode) } {
        return Err(operation.control.fail(operation.cursor,
            Fault::new(SwiftRunFailureKind::UnsupportedEnvironment, "swift_execution_unsupported_numeric"),
            Some(operation.wasi.usage())));
    }
    primitive_values_match(values, operation)?;
    let (ty, count, _) = if saturating {
        let (input, output) = crate::float::saturating_shape(opcode);
        (input, 1, output)
    } else {
        crate::float::shape(opcode).unwrap_or_else(|| crate::validate::numeric_type(opcode))
    };
    let before = values.len();
    if before.checked_sub(operand_base).is_none_or(|n| n < count)
        || values[before - count..].iter().any(|value| value.ty() != ty) {
        return Err(primitive_invariant(operation));
    }
    operation.control.work_with_wasi(Work::Execution, (count + 1) as u64, operation.cursor, Some(operation.wasi.usage()))?;
    // The only arithmetic body is the already accepted shared primitive.
    let result = crate::experimental::execution::borrowed::numeric::<SwiftMode>(values, opcode, saturating);
    let Some(removed) = before.checked_sub(values.len()) else {
        return Err(primitive_invariant(operation));
    };
    // Keep the actual primitive Result alive through after-effect reconciliation.
    // This never checks cancellation/deadline/work or admits increased live data.
    operation.control.remove_live_with_wasi(Live::Values, removed, Some(operation.wasi.usage()))?;
    result.map_err(|code| operation.control.fail(operation.cursor,
        Fault::new(SwiftRunFailureKind::GuestTrap, code), Some(operation.wasi.usage())))
}

fn primitive_clear(values: &mut Vec<Value>, operation: &mut SwiftExecutionOperation<'_>) -> Result<(), SwiftRunFailure> {
    let removed = values.len();
    values.clear();
    operation.control.remove_live_with_wasi(Live::Values, removed, Some(operation.wasi.usage()))
}
