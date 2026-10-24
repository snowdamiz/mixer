
/// Static numeric-only seam. The Swift mode has no implementation.
#[cfg(feature = "experimental-span-execution")]
pub(super) trait NumericMode: ExecutionMode + Sized {
    type NumericState<'a>;
    fn operand_base(state: &Self::NumericState<'_>) -> Option<usize>;
    fn values<'s>(state: &'s Self::NumericState<'_>) -> &'s [Value];
    fn values_mut<'s>(state: &'s mut Self::NumericState<'_>) -> &'s mut Vec<Value>;
    fn work(state: &mut Self::NumericState<'_>, credits: usize) -> Result<(), Self::Failure>;
    fn observe(state: &mut Self::NumericState<'_>, before_values: usize)
        -> Result<(), Self::Failure>;
    fn invariant(state: &mut Self::NumericState<'_>) -> Self::Failure;
    fn trap(state: &mut Self::NumericState<'_>, code: &'static str) -> Self::Failure;
}

#[cfg(feature = "experimental-span-execution")]
impl NumericMode for FrozenMode {
    type NumericState<'a> = SpanInstance;
    fn operand_base(state: &Self::NumericState<'_>) -> Option<usize> {
        state.frames.last().map(|frame| frame.operands)
    }
    fn values<'s>(state: &'s Self::NumericState<'_>) -> &'s [Value] { &state.values }
    fn values_mut<'s>(state: &'s mut Self::NumericState<'_>) -> &'s mut Vec<Value> { &mut state.values }
    fn work(state: &mut Self::NumericState<'_>, credits: usize) -> Result<(), Self::Failure> {
        state.work(credits)
    }
    fn observe(state: &mut Self::NumericState<'_>, _before_values: usize)
        -> Result<(), Self::Failure> {
        state.observe();
        Ok(())
    }
    fn invariant(state: &mut Self::NumericState<'_>) -> Self::Failure { state.invariant() }
    fn trap(state: &mut Self::NumericState<'_>, code: &'static str) -> Self::Failure {
        state.trap(code)
    }
}

#[cfg(feature = "experimental-span-execution")]
pub(super) fn numeric<M: NumericMode>(
    state: &mut M::NumericState<'_>, opcode: u8, saturating: bool,
) -> Result<(), M::Failure> {
    let (ty, count, _) = if saturating {
        let (a, b) = crate::float::saturating_shape(opcode);
        (a, 1, b)
    } else {
        crate::float::shape(opcode).unwrap_or_else(|| crate::validate::numeric_type(opcode))
    };
    let operands = M::operand_base(state).ok_or_else(|| M::invariant(state))?;
    if M::values(state).len() - operands < count
        || M::values(state)[M::values(state).len() - count..]
            .iter().any(|v| v.ty() != ty)
    {
        return Err(M::invariant(state));
    }
    let before_values = M::values(state).len();
    // Helpers consume at least one value and emit at most one, including traps.
    M::work(state, count + 1)?;
    let result = if saturating {
        crate::float::saturating(opcode, M::values_mut(state));
        Ok(())
    } else if crate::float::shape(opcode).is_some() {
        crate::float::numeric(opcode, M::values_mut(state))
    } else {
        crate::execute::numeric(opcode, M::values_mut(state))
    };
    M::observe(state, before_values)?;
    result.map_err(|code| M::trap(state, code))
}
