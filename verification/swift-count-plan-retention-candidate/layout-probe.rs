// Layout-only prospective declarations; no CacheMode or runtime behavior edit.
#[cfg(test)]
mod count_plan_layout_probe {
    use super::*;
    #[repr(u8)]
    #[derive(Clone, Copy)]
    enum Insertion { Cold, Reused }
    #[repr(C)]
    #[derive(Clone, Copy)]
    struct ScanOutcome { counts: decode::Counts, insertion: Insertion, reserved: [u8;7] }
    struct CandidateInventory {
        scan_created: ScanOutcome, scan_return: ScanOutcome, scan_caller: ScanOutcome,
        result_created: Result<ScanOutcome,SwiftRunFailure>,
        result_return: Result<ScanOutcome,SwiftRunFailure>,
        result_caller: Result<ScanOutcome,SwiftRunFailure>,
        counts_created: decode::Counts, counts_return: decode::Counts, counts_caller: decode::Counts,
        preparation_created: Result<(),SwiftRunFailure>, preparation_return: Result<(),SwiftRunFailure>,
        preparation_caller: Result<(),SwiftRunFailure>,
        index_created: usize, index_caller: usize,
        timestamp_created: u64, timestamp_return: u64, timestamp_caller: u64,
        original_match: bool, identity_valid: bool, reused_choice: bool, cold_choice: bool,
        counts_borrow: &'static ScanOutcome, timestamp_borrow: &'static ScanOutcome,
        timestamp_meter: &'static mut SwiftMeter<'static,'static>,
        timestamp_meter_reborrow: &'static mut SwiftMeter<'static,'static>,
    }
    #[test]
    fn count_plan_prospective_exact_layout() {
        assert_eq!(size_of::<ScanOutcome>(),32);
        println!("COUNT_LAYOUT {{\"outcome\":{},\"result\":{},\"countsResult\":{},\"unitResult\":{},\"inventory\":{},\"dedicatedThree\":{},\"planInventory\":{},\"operationScalar\":{},\"operationBorrow\":{},\"constructionScalar\":{},\"constructionBorrow\":{},\"slot\":{},\"resident\":{},\"header\":{},\"construction\":{},\"operation\":{},\"cleanup\":{}}}",
          size_of::<ScanOutcome>(),size_of::<Result<ScanOutcome,SwiftRunFailure>>(),size_of::<Result<decode::Counts,SwiftRunFailure>>(),
          size_of::<Result<(),SwiftRunFailure>>(),
          size_of::<CandidateInventory>(),3*size_of::<CandidateInventory>(),size_of::<PlanInventory>(),size_of::<OperationScalarInventory>(),
          size_of::<OperationBorrowChainInventory>(),size_of::<ConstructionScalarInventory>(),size_of::<ConstructionBorrowChainInventory>(),
          size_of::<SwiftSlot>(),size_of::<SwiftResident>(),cache_header_bytes().unwrap(),cache_construction_bytes().unwrap(),
          cache_operation_bytes().unwrap(),cache_cleanup_temporary_bytes().unwrap());
    }
}
