// Test-only observation and direct finite policy entry points; never compiled
// into the candidate production interface and never execute guest instructions.
#[cfg(test)]
pub(super) mod cost_inspection {
    use super::*;
    pub fn shape() -> (usize,usize,usize,usize) {
        (size_of::<CostRetentionInventory>(),size_of::<SwiftResident>(),size_of::<SwiftSlot>(),cache_operation_bytes().unwrap())
    }
    pub fn records(cache: &SwiftFunctionCache) -> Vec<(usize,u32,usize,u64,u64,usize)> {
        cache.slots.iter().enumerate().filter_map(|(i,s)|s.resident.as_ref().map(|r|(i,r.decoded.function,s.pins,s.last_used,r.estimated_build_work,r.decoded.instructions.as_ptr() as usize))).collect()
    }
    pub fn metadata(cache: &mut SwiftFunctionCache, f:u32, age:u64, cost:u64) {
        let slot=cache.slots.iter_mut().find(|s|s.entry().is_some_and(|e|e.function==f)).unwrap();
        slot.last_used=age; slot.resident.as_mut().unwrap().estimated_build_work=cost;
    }
    pub fn select(cache:&mut SwiftFunctionCache,c:&mut RuntimeControl,plan:&[bool;64]) -> Result<usize,SwiftRunFailure> {
        let mut phase=cache.prepare_operation(c,None,cache_cursor())?;
        let mut meter=SwiftMode::meter(&mut cache.usage,&mut phase.control,34);
        let result=SwiftMode::resident_victim(&cache.slots,plan,&mut meter);
        phase.complete(()).unwrap(); result
    }
    pub fn compare(cache:&mut SwiftFunctionCache,c:&mut RuntimeControl,a:[u64;4],b:[u64;4]) -> bool {
        let mut phase=cache.prepare_operation(c,None,cache_cursor()).unwrap();
        let mut meter=SwiftMode::meter(&mut cache.usage,&mut phase.control,34);
        let result=retention_before(RetentionRank{slot:a[0] as usize,cost:a[1],age:a[2],last_used:a[3]},RetentionRank{slot:b[0] as usize,cost:b[1],age:b[2],last_used:b[3]},&mut meter).unwrap();
        phase.complete(()).unwrap(); result
    }
}
