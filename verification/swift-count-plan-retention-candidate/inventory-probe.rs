#[cfg(test)]
mod count_candidate_inventory_probe {
    use super::*;
    #[test]
    fn count_candidate_exact_implemented_inventory() {
        use std::mem::offset_of;
        assert_eq!(size_of::<CountPlanPolicyInventory>(),6824);
        assert_eq!(size_of::<CountPlanScanOutcome>(),32);
        assert_eq!(size_of::<Result<CountPlanScanOutcome,SwiftRunFailure>>(),1096);
        assert_eq!(cache_operation_bytes().unwrap(),112822);
        println!("COUNT_IMPLEMENTED {{\"outcome\":32,\"result\":1096,\"inventory\":6824,\"threeInventories\":20472,\"operation\":112822,\"persistentPolicyBytes\":0,\"newTickets\":0}}");
        macro_rules! field { ($name:ident,$ty:ty)=> {println!("COUNT_FIELD {{\"name\":\"{}\",\"offset\":{},\"bytes\":{}}}",stringify!($name),offset_of!(CountPlanPolicyInventory,$name),size_of::<$ty>());}; }
        field!(scan_created,CountPlanScanOutcome);field!(scan_return,CountPlanScanOutcome);field!(scan_caller,CountPlanScanOutcome);
        field!(result_created,Result<CountPlanScanOutcome,SwiftRunFailure>);field!(result_return,Result<CountPlanScanOutcome,SwiftRunFailure>);field!(result_caller,Result<CountPlanScanOutcome,SwiftRunFailure>);
        field!(index_created,usize);field!(index_caller,usize);
        field!(timestamp_created,u64);field!(timestamp_return,u64);field!(timestamp_caller,u64);
        field!(original_match,bool);field!(identity_valid,bool);field!(reused_choice,bool);field!(cold_choice,bool);
        field!(counts_borrow,&'static CountPlanScanOutcome);field!(prepare_meter,&'static mut SwiftMeter<'static,'static>);
        field!(timestamp_borrow,&'static CountPlanScanOutcome);field!(timestamp_meter,&'static SwiftMeter<'static,'static>);
        field!(counts_created,decode::Counts);field!(counts_return,decode::Counts);field!(counts_caller,decode::Counts);
        field!(preparation_created,Result<(),SwiftRunFailure>);field!(preparation_return,Result<(),SwiftRunFailure>);field!(preparation_caller,Result<(),SwiftRunFailure>);
    }
}
