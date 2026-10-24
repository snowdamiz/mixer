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
