#!/usr/bin/env python3
"""Apply the isolated, coordinated SLRU candidate to the exact live source copy."""
from pathlib import Path
import hashlib, json, difflib

H = Path(__file__).resolve().parent
S = H / 'candidate'
def edit(n, old, new):
    p = S / n
    s = p.read_text()
    assert s.count(old) == 1, (n, old[:100], s.count(old))
    p.write_text(s.replace(old, new))

B = 'src/experimental/cache/borrowed.rs'
C = 'src/experimental_swift_reactor/cache.rs'
edit(B, '    type Scratch<\'a>;\n', '    type Scratch<\'a>;\n    type HitPlan: Default;\n')
edit(B, '    fn resident_remove(\n', '''    // Mode-specific plans are zero-sized for the frozen non-Swift cache.
    // The default victim scan preserves its original literal LRU work trace.
    fn resident_victim(
        slots: &[Self::Slot],
        plan: &[bool],
        meter: &mut Self::Meter<'_, '_>,
    ) -> Result<Option<usize>, Self::Failure> {
        let mut oldest: Option<usize> = None;
        for (index, slot) in slots.iter().enumerate() {
            meter.work(1)?;
            if !plan[index]
                && slot.pins() == 0
                && slot.entry().is_some()
                && oldest.is_none_or(|p| slot.last_used() < slots[p].last_used())
            {
                oldest = Some(index);
            }
        }
        Ok(oldest)
    }
    fn prepare_resident_hit(
        _: &[Self::Slot],
        _: usize,
        _: &mut Self::Meter<'_, '_>,
    ) -> Result<Self::HitPlan, Self::Failure> {
        Ok(Self::HitPlan::default())
    }
    fn commit_resident_hit(_: &mut [Self::Slot], _: usize, _: Self::HitPlan) {}
    fn resident_remove(
''')
edit(B, '    type Scratch<\'a> = ();', '    type Scratch<\'a> = ();\n    type HitPlan = ();')
edit(B, '    let index = if let Some(index) = hit {', '    let mut hit_plan = M::HitPlan::default();\n    let index = if let Some(index) = hit {')
edit(B, '        meter.usage_mut().hit(hits);', '        hit_plan = M::prepare_resident_hit(parts.slots, index, meter)?;\n        meter.usage_mut().hit(hits);')
edit(B, '''            let mut oldest: Option<usize> = None;
            for (index, slot) in parts.slots.iter().enumerate() {
                meter.work(1)?;
                if !plan[index]
                    && slot.pins() == 0
                    && slot.entry().is_some()
                    && oldest.is_none_or(|p| slot.last_used() < parts.slots[p].last_used())
                {
                    oldest = Some(index);
                }
            }
''', '            let oldest = M::resident_victim(parts.slots, &plan, meter)?;\n')
edit(B, '    let slot = &mut parts.slots[index];\n    meter.usage_mut().pin(', '    M::commit_resident_hit(parts.slots, index, hit_plan);\n    let slot = &mut parts.slots[index];\n    meter.usage_mut().pin(')

edit(C, '''    last_used: u64,
}
impl CacheSlot for SwiftSlot''', '''    last_used: u64,
    protected: bool,
}
impl CacheSlot for SwiftSlot''')
edit(C, '''    fn set(&mut self, r: SwiftResident) {
        self.resident = Some(r);
    }''', '''    fn set(&mut self, r: SwiftResident) {
        // The tier write was admitted with resident_insert before publication.
        self.protected = false;
        self.resident = Some(r);
    }''')
edit(C, '''        for _ in 0..entries {
            self.control.work(1)?;
            partial.slots.push(SwiftSlot {
                resident: None,
                pins: 0,
                last_used: 0,
            });''', '''        for _ in 0..entries {
            self.control.work(2)?; // original slot initialization plus tier write
            partial.slots.push(SwiftSlot {
                resident: None,
                pins: 0,
                last_used: 0,
                protected: false,
            });''')
edit(C, 'pub(crate) struct SwiftFunctionCache {', '''#[derive(Default)]
pub(crate) enum SwiftHitPlan {
    #[default]
    Unchanged,
    Promote { demote: Option<usize> },
}
// Disjoint named objects from the private victim/promotion/commit chain,
// including caller/return plans, iterators, closures, and reborrows. Three
// complete copies are reserved alongside all existing operation inventories.
struct RetentionInventory {
    caller_plan: SwiftHitPlan,
    prepared_plan: SwiftHitPlan,
    returned_plan: Result<SwiftHitPlan, SwiftRunFailure>,
    hit_slots: &'static [SwiftSlot],
    hit_index: usize,
    hit_meter: &'static mut SwiftMeter<'static, 'static>,
    capacity_slots: usize,
    capacity_return: usize,
    protected_capacity: usize,
    protected_count: usize,
    oldest_protected: Option<(usize, u64)>,
    hit_search: std::iter::Enumerate<std::slice::Iter<'static, SwiftSlot>>,
    hit_candidate: usize,
    hit_slot: &'static SwiftSlot,
    hit_age: u64,
    hit_older: &'static (usize, u64),
    hit_oldest_reborrow: Option<&'static (usize, u64)>,
    hit_age_capture: &'static u64,
    hit_map_argument: (usize, u64),
    hit_demote: Option<usize>,
    hit_write_credits: u64,
    commit_slots: &'static mut [SwiftSlot],
    commit_index: usize,
    commit_plan: SwiftHitPlan,
    commit_demote: Option<usize>,
    commit_victim: usize,
    victim_slots: &'static [SwiftSlot],
    victim_selected: &'static [bool],
    victim_meter: &'static mut SwiftMeter<'static, 'static>,
    oldest: Option<(usize, bool, u64)>,
    victim_search: std::iter::Enumerate<std::slice::Iter<'static, SwiftSlot>>,
    victim_index: usize,
    victim_slot: &'static SwiftSlot,
    victim_rank: (bool, u64),
    victim_older: &'static (usize, bool, u64),
    victim_oldest_reborrow: Option<&'static (usize, bool, u64)>,
    victim_rank_capture: &'static (bool, u64),
    victim_map_argument: (usize, bool, u64),
    victim_return: Result<Option<usize>, SwiftRunFailure>,
    victim_mapped: Option<usize>,
}
fn protected_capacity(slots: usize) -> usize {
    // Construction and resident_find bound slots to 64, so this cannot overflow.
    slots * 3 / 4
}
pub(crate) struct SwiftFunctionCache {''')
edit(C, '        (3, size_of::<ResidentIndexInventory>()),', '        (3, size_of::<ResidentIndexInventory>()),\n        (3, size_of::<RetentionInventory>()),')
edit(C, '    type Scratch<\'a> = SwiftScratch<\'a>;', '    type Scratch<\'a> = SwiftScratch<\'a>;\n    type HitPlan = SwiftHitPlan;')
edit(C, '''    fn resident_remove(
        slots: &[SwiftSlot],''', '''    fn resident_victim(
        slots: &[SwiftSlot],
        selected: &[bool],
        meter: &mut SwiftMeter<'_, '_>,
    ) -> Result<Option<usize>, SwiftRunFailure> {
        let mut oldest: Option<(usize, bool, u64)> = None;
        for (index, slot) in slots.iter().enumerate() {
            meter.work(1)?; // original eligibility/age probe
            if !selected[index] && slot.pins() == 0 && slot.entry().is_some() {
                meter.work(1)?; // additional tier read, before observing it
                let rank = (slot.protected, slot.last_used());
                if oldest.as_ref().is_none_or(|p| rank < (p.1, p.2)) {
                    oldest = Some((index, rank.0, rank.1));
                }
            }
        }
        Ok(oldest.map(|p| p.0))
    }
    fn prepare_resident_hit(
        slots: &[SwiftSlot],
        index: usize,
        meter: &mut SwiftMeter<'_, '_>,
    ) -> Result<SwiftHitPlan, SwiftRunFailure> {
        meter.work(1)?; // additional hit-tier read
        let capacity = protected_capacity(slots.len());
        if slots[index].protected || capacity == 0 {
            return Ok(SwiftHitPlan::Unchanged);
        }
        let mut protected = 0;
        let mut oldest: Option<(usize, u64)> = None;
        for (candidate, slot) in slots.iter().enumerate() {
            meter.work(2)?; // occupied tag and protected tier read
            if slot.entry().is_some() && slot.protected {
                protected += 1;
                meter.work(1)?; // age read used solely by promotion planning
                let age = slot.last_used();
                if oldest.as_ref().is_none_or(|p| age < p.1) {
                    oldest = Some((candidate, age));
                }
            }
        }
        if protected > capacity {
            return Err(meter.error(CacheFailureKind::DecoderMismatch, "swift_retention_capacity"));
        }
        let demote = if protected == capacity { oldest.map(|p| p.0) } else { None };
        // Admit the complete infallible commit before changing any tier.
        meter.work(1 + u64::from(demote.is_some()))?;
        Ok(SwiftHitPlan::Promote { demote })
    }
    fn commit_resident_hit(slots: &mut [SwiftSlot], index: usize, plan: SwiftHitPlan) {
        if let SwiftHitPlan::Promote { demote } = plan {
            if let Some(victim) = demote {
                slots[victim].protected = false;
            }
            slots[index].protected = true;
        }
    }
    fn resident_remove(
        slots: &[SwiftSlot],''')
edit(C, '''        meter.work(2)?; // admit both link writes before infallible publication''', '''        meter.work(3)?; // admit both link writes and new resident tier reset''')

(H/'implementation.patch').write_text(''.join(''.join(difflib.unified_diff((H/'baseline'/n).read_text().splitlines(True),(S/n).read_text().splitlines(True),fromfile='baseline/'+n,tofile='candidate/'+n)) for n in [B,C]))
print(json.dumps({'changedProductFiles':[B,C]}))
