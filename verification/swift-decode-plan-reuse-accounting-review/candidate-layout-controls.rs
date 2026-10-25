
#[cfg(test)]
pub(super) mod independent_plan {
    use super::*;
    pub fn assert_disjoint_inventory() {
        use std::mem::offset_of;
        let mut fields=vec![
            ("cell",offset_of!(PlanInventory,cell),size_of::<Option<ScanPlan>>()),
            ("plan",offset_of!(PlanInventory,plan),size_of::<ScanPlan>()),
            ("borrowed",offset_of!(PlanInventory,borrowed),size_of::<&ScanPlan>()),
            ("slots",offset_of!(PlanInventory,slots),size_of::<&mut [Option<ScanPlan>]>()),
            ("vec",offset_of!(PlanInventory,vec),size_of::<&mut Vec<Option<ScanPlan>>>()),
            ("reserve_receiver",offset_of!(PlanInventory,reserve_receiver),size_of::<&mut Vec<Option<ScanPlan>>>()),
            ("reserve_control",offset_of!(PlanInventory,reserve_control),size_of::<&mut CacheControl<'static>>()),
            ("index",offset_of!(PlanInventory,index),size_of::<usize>()),
            ("bytes",offset_of!(PlanInventory,bytes),size_of::<usize>()),
            ("counts",offset_of!(PlanInventory,counts),size_of::<decode::Counts>()),
            ("output",offset_of!(PlanInventory,output),size_of::<Result<decode::Counts,SwiftRunFailure>>()),
            ("init",offset_of!(PlanInventory,init),size_of::<std::ops::Range<usize>>()),
        ];
        fields.sort_by_key(|x|x.1);
        let mut end=0;for (name,start,len) in fields {assert!(start>=end);end=start+len;println!("REVIEW_INVENTORY {name} start={start} bytes={len}");}
        assert!(end<=size_of::<PlanInventory>());assert_eq!(size_of::<PlanInventory>(),1304);
        assert_eq!(size_of::<Option<ScanPlan>>(),56);
        assert_eq!(PLAN_CAPACITY*size_of::<Option<ScanPlan>>(),28672);
    }
    pub fn replace_counts(cache:&mut SwiftFunctionCache,to:u32,from:u32) {
        let counts=cache.plans[from as usize & 511].as_ref().unwrap().counts;
        cache.plans[to as usize & 511].as_mut().unwrap().counts=counts;
    }
}
