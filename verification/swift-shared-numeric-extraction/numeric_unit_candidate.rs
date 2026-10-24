
/// Static numeric-only seam. The Swift mode has no implementation.
#[cfg(feature = "experimental-span-execution")]
pub(super) trait NumericMode: ExecutionMode + Sized {
    type NumericState<'a>;
    fn operand_base(state: &Self::NumericState<'_>) -> Option<usize>;
    fn values<'s>(state: &'s Self::NumericState<'_>) -> &'s [Value];
    fn values_mut<'s>(state: &'s mut Self::NumericState<'_>) -> &'s mut Vec<Value>;
    fn work(state: &mut Self::NumericState<'_>, credits: usize,
        outcome: &mut Result<(), Self::Failure>);
    fn observe(state: &mut Self::NumericState<'_>, before_values: usize,
        outcome: &mut Result<(), Self::Failure>);
    fn invariant(state: &mut Self::NumericState<'_>, outcome: &mut Result<(), Self::Failure>);
    fn trap(state: &mut Self::NumericState<'_>, code: &'static str,
        outcome: &mut Result<(), Self::Failure>);
}

#[cfg(feature = "experimental-span-execution")]
impl NumericMode for FrozenMode {
    type NumericState<'a> = SpanInstance;
    fn operand_base(state: &Self::NumericState<'_>) -> Option<usize> {
        state.frames.last().map(|frame| frame.operands)
    }
    fn values<'s>(state: &'s Self::NumericState<'_>) -> &'s [Value] { &state.values }
    fn values_mut<'s>(state: &'s mut Self::NumericState<'_>) -> &'s mut Vec<Value> { &mut state.values }
    fn work(state: &mut Self::NumericState<'_>, credits: usize,
        outcome: &mut Result<(), Self::Failure>) {
        *outcome = state.work(credits);
    }
    fn observe(state: &mut Self::NumericState<'_>, _before_values: usize,
        outcome: &mut Result<(), Self::Failure>) {
        state.observe();
        *outcome = Ok(());
    }
    fn invariant(state: &mut Self::NumericState<'_>, outcome: &mut Result<(), Self::Failure>) {
        *outcome = Err(state.invariant());
    }
    fn trap(state: &mut Self::NumericState<'_>, code: &'static str,
        outcome: &mut Result<(), Self::Failure>) {
        *outcome = Err(state.trap(code));
    }
}

#[cfg(feature = "experimental-span-execution")]
pub(super) fn numeric<M: NumericMode>(
    state: &mut M::NumericState<'_>, opcode: u8, saturating: bool,
) -> Result<(), M::Failure> {
    let credits = {
        let (ty, count, _) = if saturating {
            let (a, b) = crate::float::saturating_shape(opcode);
            (a, 1, b)
        } else {
            crate::float::shape(opcode).unwrap_or_else(|| crate::validate::numeric_type(opcode))
        };
        let operands = match M::operand_base(state) {
            Some(operands) => operands,
            None => {
                let mut outcome = Ok(());
                M::invariant(state, &mut outcome);
                return outcome;
            }
        };
        let invalid = {
            let values = M::values(state);
            values.len() - operands < count
                || values[values.len() - count..].iter().any(|v| v.ty() != ty)
        };
        if invalid {
            let mut outcome = Ok(());
            M::invariant(state, &mut outcome);
            return outcome;
        }
        count + 1
    };
    let mut outcome = Ok(());
    // Helpers consume at least one value and emit at most one, including traps.
    M::work(state, credits, &mut outcome);
    match outcome { Ok(()) => {}, Err(error) => return Err(error) }
    let before_values = M::values(state).len();
    let result = if saturating {
        crate::float::saturating(opcode, M::values_mut(state));
        Ok(())
    } else if crate::float::shape(opcode).is_some() {
        crate::float::numeric(opcode, M::values_mut(state))
    } else {
        crate::execute::numeric(opcode, M::values_mut(state))
    };
    M::observe(state, before_values, &mut outcome);
    match outcome { Ok(()) => {}, Err(error) => return Err(error) }
    match result {
        Ok(()) => {},
        Err(code) => M::trap(state, code, &mut outcome),
    }
    outcome
}
