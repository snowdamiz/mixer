#[cfg(test)]
pub(super) mod count_candidate_inspection {
    use super::*;
    pub fn common_shape() -> [usize;12] {
        [size_of::<PlanInventory>(),size_of::<OperationScalarInventory>(),size_of::<OperationBorrowChainInventory>(),
         size_of::<ConstructionScalarInventory>(),size_of::<ConstructionBorrowChainInventory>(),size_of::<SwiftSlot>(),
         size_of::<SwiftResident>(),cache_header_bytes().unwrap(),cache_construction_bytes().unwrap(),
         cache_operation_bytes().unwrap(),cache_cleanup_temporary_bytes().unwrap(),size_of::<Result<decode::Counts,SwiftRunFailure>>()]
    }
    pub fn rank_state(cache:&SwiftFunctionCache) -> Vec<(u32,usize,u64,usize)> {
        cache.slots.iter().enumerate().filter_map(|(i,s)|s.entry().map(|e|(e.function,s.pins,s.last_used,i))).collect()
    }
    pub fn bad_scan(cache:&mut SwiftFunctionCache,c:&mut RuntimeControl) -> SwiftRunFailure {
        let mut phase=cache.prepare_operation(c,None,cache_cursor()).unwrap();
        let (body_offset,type_index)={let original=cache.proof().execution_function(34).unwrap();(original.body_offset,original.type_index)};
        let malformed=[0,0xff,0x0b];
        let body=FunctionSpanView { absolute_index:34,type_index,body:&malformed,body_offset };
        let outcome=SwiftMode::scan(cache.adopted.proof(),body,
            &mut SwiftScratch { patches:&mut cache.patches,index:&mut cache.index,plans:&mut cache.plans },
            &mut SwiftMeter { operation:&mut phase.control,usage:&mut cache.usage });
        let failure=outcome.err().unwrap();phase.complete(()).unwrap();failure
    }
}
