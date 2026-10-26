//! Complete source-expression Results and try/residual layout closure.
use super::*;
#[test]
fn complete_scalar_descriptor_metadata_results_and_try_places() {
    use std::mem::size_of as s;
    use std::ops::ControlFlow as C;
    use std::convert::Infallible;
    use crate::experimental::descriptors::FunctionSpanView as D;
    type E=ProfileAdapterErrorV1;
    println!("RESULT_CLOSURE scalar_usize_result={} scalar_u64_result={} descriptor_result={} metadata_profile_result={} residual_result={} usize_control={} u64_control={} descriptor_control={} metadata_control={} row_control={} writer_control={} unit_control={} unit_result={}",
        s::<Result<usize,E>>(),s::<Result<u64,E>>(),s::<Result<D<'_>,E>>(),s::<Result<std::fs::Metadata,E>>(),
        s::<Result<Infallible,E>>(),s::<C<Result<Infallible,E>,usize>>(),s::<C<Result<Infallible,E>,u64>>(),
        s::<C<Result<Infallible,E>,D<'_>>>(),s::<C<Result<Infallible,E>,std::fs::Metadata>>(),
        s::<C<Result<Infallible,E>,ProfileRowV1>>(),s::<C<Result<Infallible,E>,ProfileRowsObservationV1>>(),
        s::<C<Result<Infallible,E>,()>>(),s::<Result<(),E>>());
}
