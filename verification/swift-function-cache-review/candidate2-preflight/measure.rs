// Included only in the isolated private cache module, to measure actual types.
pub(super) fn review_preflight_measure(control:&mut RuntimeControl) {
    use std::mem::{size_of,align_of,size_of_val,align_of_val};
    macro_rules! row {($t:ty)=>{println!("preflight_measure {} {} {}",stringify!($t),size_of::<$t>(),align_of::<$t>());};}
    row!(PreflightBorrowChainInventory);
    row!(PreflightGroupA);
    row!(PreflightGroupB);
    row!(RuntimeControl);
    row!(Result<PreparedBounds,SwiftRunFailure>);
    row!(Result<WasiUsage,SwiftRunFailure>);
    row!(Option<Result<WasiUsage,SwiftRunFailure>>);
    row!(Result<Option<WasiUsage>,SwiftRunFailure>);
    row!(Result<(),SwiftRunFailure>);
    row!(Option<(SwiftCleanupInvariant,&'static str)>);
    row!(SwiftCleanupInvariant);
    row!(std::time::Instant);
    row!(std::time::Duration);
    row!(u128);
    row!(Result<u64,std::num::TryFromIntError>);
    let cursor=cache_cursor();
    {
        let closure=|w:&AccountedWasi|w.checked_usage(control,cursor);
        println!("preflight_closure pairing {} {}",size_of_val(&closure),align_of_val(&closure));
    }
    {
        let observation=None;
        let closure=||layout_failure(control,observation,cursor);
        println!("preflight_closure layout_failure {} {}",size_of_val(&closure),align_of_val(&closure));
    }
    {
        let previous=0usize;
        let closure=|n:usize|previous.checked_add(n);
        println!("preflight_closure bound_add {} {}",size_of_val(&closure),align_of_val(&closure));
    }
}
