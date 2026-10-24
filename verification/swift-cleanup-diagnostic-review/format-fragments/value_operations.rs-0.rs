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
