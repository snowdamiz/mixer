// Test-only corruption hooks, included only in the isolated reconstructed tree.
pub(crate) fn independent_replace_tail_header(
    tail: &mut CacheCleanupTail<'_>, ticket: ReservationTicket,
) -> ReservationTicket {
    std::mem::replace(tail.header.as_mut().unwrap(), ticket)
}

pub(crate) fn independent_print_missing_shapes() {
    macro_rules! shape {($t:ty)=>{println!("independent_shape {} {} {}",stringify!($t),size_of::<$t>(),std::mem::align_of::<$t>());};}
    shape!(SwiftRunBudget);
    shape!(CacheParts<'static,SwiftMode>);
    shape!(PinRecord);
    shape!(FunctionView<'static>);
    shape!(Result<FunctionView<'static>,SwiftRunFailure>);
    shape!(Result<PinRecord,SwiftRunFailure>);
    shape!(Result<(),(SwiftRunFailure,SwiftFunctionPin)>);
    shape!([(usize,usize);19]);
    shape!([(usize,usize);23]);
    shape!([(usize,usize);27]);
    shape!(std::slice::Iter<'static,(usize,usize)>);
    shape!(crate::experimental::cache::Operation);
    shape!(decode::Patch);
    shape!(CleanupCompletionParts<'static>);
}
