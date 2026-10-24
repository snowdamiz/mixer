
/// Static primitive dispatch only. Owner validation/metering/observation/errors
/// remain on the existing frozen path; Swift has no numeric mode adapter.
#[cfg(feature = "experimental-span-execution")]
pub(super) trait NumericMode: ExecutionMode + Sized {
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

#[cfg(feature = "experimental-span-execution")]
pub(super) fn numeric<M: NumericMode>(
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
