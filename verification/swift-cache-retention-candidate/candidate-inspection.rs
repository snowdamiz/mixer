#[cfg(test)]
pub(super) mod retention_inspection {
    use super::*;
    pub fn states(cache: &SwiftFunctionCache) -> Vec<(usize, Option<u32>, bool, usize, u64)> {
        cache.slots.iter().enumerate().map(|(i,s)|(i,s.entry().map(|e|e.function),s.protected,s.pins,s.last_used)).collect()
    }
    pub fn ages(cache: &mut SwiftFunctionCache, equal: Option<u64>, shift: u64) {
        for slot in &mut cache.slots {
            if slot.entry().is_some() {
                slot.last_used = equal.unwrap_or(slot.last_used) + shift;
            }
        }
    }
    pub fn capacity(n: usize) -> usize { protected_capacity(n) }
    pub fn plan_bytes() -> (usize, usize, usize) {
        (size_of::<SwiftHitPlan>(),size_of::<RetentionInventory>(),size_of::<<FrozenMode as CacheMode>::HitPlan>())
    }
}
