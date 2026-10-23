// Independent source snapshot measurement only. No modeled owner is constructed.
pub(super) fn review_rootleaf_measure(_control:&mut RuntimeControl) {
    use std::mem::{size_of,align_of};
    macro_rules! row {($t:ty)=>{println!("rootleaf_measure {} {} {}",stringify!($t),size_of::<$t>(),align_of::<$t>());};}
    row!(PreflightGroupA); row!(PreflightGroupB); row!(PreflightSetupInventory);
    row!(PreflightOwnerInventory); row!(PreflightPrimitiveInventory); row!(PreflightEnlargeInventory);
    row!(RootLeafInventory); row!(RootAdmissionBoundaryInventory); row!(RootOwnerBoundaryInventory);
    row!(RootWorkLiveBoundaryInventory); row!(RootRefundBoundaryInventory); row!(CompletionBorrowInventory);
    row!(RootRemoveLiveBoundaryInventory); row!(RootRemoveLiveInventory); row!(RootRefundInventory); row!(RootPhaseEndInventory); row!(RootWorkLiveInventory);
    row!(RuntimeControl); row!(ValidatedSwiftReactor); row!(AdoptedProof);
    row!(CleanupCompletionParts<'static>); row!(SwiftRunFailure); row!(SwiftRunUsage);
    row!(Option<WasiUsage>); row!(ReservationTicket);
    inspection::print_layouts();
    println!("rootleaf_bounds construction={} operation={} cleanup={} header={} foundation={}",
        cache_construction_bytes().unwrap(),cache_operation_bytes().unwrap(),cache_cleanup_temporary_bytes().unwrap(),
        cache_header_bytes().unwrap(),foundation_construction_bytes().unwrap());
}
