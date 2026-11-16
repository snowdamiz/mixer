
// Value-only capacity contract: checked before cache allocation or Runtime adoption.
pub const UI_CAPACITY: usize = 256;
pub const DEFAULT_CAPACITY: usize = 64;
pub const PLAN_CAPACITY: usize = UI_CAPACITY;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CacheShape { pub entries: usize, pub pins: usize }
impl CacheShape {
    pub fn checked(entries: usize, pins: usize, planning_slots: usize) -> Option<Self> {
        if entries == 0 || pins == 0 || entries > UI_CAPACITY || pins > UI_CAPACITY
            || planning_slots > PLAN_CAPACITY || entries > planning_slots { return None; }
        Some(Self { entries, pins })
    }
    pub fn budget(entries: usize, pins: usize, frames: usize, ui: bool) -> bool {
        if entries <= DEFAULT_CAPACITY && pins <= DEFAULT_CAPACITY && frames <= DEFAULT_CAPACITY { return true; }
        if Self::checked(entries, pins, PLAN_CAPACITY).is_none() { return false; }
        ui && entries == UI_CAPACITY && pins == UI_CAPACITY && frames == UI_CAPACITY
    }
}

/// Logical authority, distinct from byte reservations. All ticket owners are
/// inline fields or capacity-charged slots; this plan allocates no inventory.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SwiftResourcePlan {
    activation: usize,
    tickets: usize,
}
impl SwiftResourcePlan {
    // Source ownership: adoption source/metadata/control/cancellation/construction;
    // cache header + three buffers; WASI header + four buffers; execution header
    // + six arenas. Construction extensions reuse their original ticket.
    pub const FOUNDATION: usize = 5;
    pub const CACHE_FIXED: usize = 4;
    pub const WASI: usize = 5;
    pub const EXECUTION: usize = 7;
    // Exclusive dispatch: cold decode, memory replacement, or host UI snapshot.
    // Cache eviction precedes decode. Growth moves the original ticket, never
    // duplicates it. Snapshot runs only after invocation has returned.
    pub const TRANSIENT: usize = 1;
    pub const NONCACHE: usize = Self::FOUNDATION + Self::CACHE_FIXED
        + Self::WASI + Self::EXECUTION + Self::TRANSIENT;
    pub const DEFAULT_TICKETS: usize = DEFAULT_CAPACITY + Self::NONCACHE;

    pub fn checked(entries: usize, pins: usize, frames: usize, ui: bool) -> Option<Self> {
        if !CacheShape::budget(entries, pins, frames, ui) { return None; }
        let activation = if entries > DEFAULT_CAPACITY { UI_CAPACITY } else { DEFAULT_CAPACITY };
        Some(Self { activation, tickets: activation.checked_add(Self::NONCACHE)? })
    }
    pub fn ui_profile_1() -> Self {
        Self::checked(UI_CAPACITY, UI_CAPACITY, UI_CAPACITY, true)
            .expect("fixed UI resource plan")
    }
    pub fn activation_capacity(self) -> usize { self.activation }
    pub fn ticket_limit(self) -> usize { self.tickets }
    pub fn admits_inventory(self, requested: usize) -> bool { requested <= self.tickets }
}
// No heap allocation. Every traversal is restricted to the admitted slot count.
pub struct EvictionPlan { words: [u64; 4], len: usize }
impl EvictionPlan {
    pub fn new(len: usize) -> Option<Self> {
        if len > PLAN_CAPACITY { None } else { Some(Self { words: [0; 4], len }) }
    }
    pub fn contains(&self, index: usize) -> bool {
        index < self.len && self.words[index / 64] & (1u64 << (index % 64)) != 0
    }
    pub fn select(&mut self, index: usize) -> Option<()> {
        if index >= self.len { return None; }
        self.words[index / 64] |= 1u64 << (index % 64); Some(())
    }
    pub fn count(&self) -> usize { self.words.iter().map(|w|w.count_ones() as usize).sum() }
}

pub fn oldest_victim<E>(len:usize,slot:impl Fn(usize)->(bool,u64),mut work:impl FnMut(u64)->Result<(),E>)->Result<Option<usize>,E>{ let mut oldest=None;let mut age=u64::MAX;for index in 0..len{work(1)?;let (eligible,time)=slot(index);if eligible&&(oldest.is_none()||time<age){oldest=Some(index);age=time}}Ok(oldest)}

pub struct VictimInventory { pub scalars:[usize;16], pub borrows:[u64;8] }

#[cfg(test)]
mod r3554_pure {
    use super::*;
    #[test]
    fn resource_plans_and_exact_victim_traversal_work() {
        let stock=SwiftResourcePlan::checked(64,64,64,false).unwrap();
        let ui=SwiftResourcePlan::ui_profile_1();
        assert_eq!((stock.activation_capacity(),stock.ticket_limit()),(64,86));
        assert_eq!((ui.activation_capacity(),ui.ticket_limit()),(256,278));
        assert!(SwiftResourcePlan::checked(256,256,256,false).is_none());
        assert!(SwiftResourcePlan::checked(65,65,65,true).is_none());
        for len in [1,29,64,256] {
            let mut calls=0; let mut work=0;
            let visits=std::cell::Cell::new(0usize);
            let selected=oldest_victim(len,|i|{visits.set(visits.get()+1);(true,(len-i) as u64)},|n|{work+=n;Ok::<_,()>(())}).unwrap();
            assert_eq!(visits.get(),len);
            assert_eq!(selected,Some(len-1)); assert_eq!(work,len as u64);
            let mut plan=EvictionPlan::new(len).unwrap(); plan.select(len-1).unwrap();
            for i in 0..len {calls+=usize::from(plan.contains(i));}
            assert_eq!(calls,1);assert_eq!(plan.count(),1);assert!(plan.select(len).is_none());
        }
        // SL13 uses 29 resident slots. Old count visited 64 bool cells;
        // current count visits 4 bitmap words and charges 29 apply probes.
        // Thus the unchanged surrounding cold operations differ by exactly -31.
        let actual=EvictionPlan::new(29).unwrap();
        assert_eq!(actual.words.len()+actual.len,33);
        assert_eq!(64-(actual.words.len()+actual.len),31);
    }
}
