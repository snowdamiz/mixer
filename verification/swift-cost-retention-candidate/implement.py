#!/usr/bin/env python3
"""Apply this independently authored candidate only to the fresh live copy."""
from pathlib import Path
BASE = Path(__file__).resolve().parent/'.scratch'/'candidate'
def replace(path, old, new):
    p=BASE/path; text=p.read_text(); assert text.count(old)==1, (path,text.count(old)); p.write_text(text.replace(old,new))
loop='''            let mut oldest: Option<usize> = None;
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
            let victim = oldest
                .ok_or_else(|| meter.error(CacheFailureKind::AllPinned, "all_entries_pinned"))?;'''
default='''    // Literal baseline LRU loop and work trace for the frozen specialization.
    fn resident_victim(
        slots: &[Self::Slot],
        plan: &[bool; MAX_ENTRIES],
        meter: &mut Self::Meter<'_, '_>,
    ) -> Result<usize, Self::Failure> {
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
        oldest.ok_or_else(|| meter.error(CacheFailureKind::AllPinned, "all_entries_pinned"))
    }
'''
replace(Path('src/experimental/cache/borrowed.rs'),'    fn scan(\n        snapshot: &Self::Snapshot,',default+'    fn scan(\n        snapshot: &Self::Snapshot,')
replace(Path('src/experimental/cache/borrowed.rs'),loop,'            let victim = M::resident_victim(parts.slots, &plan, meter)?;')
replace(Path('src/experimental/cache/decode.rs'),'impl Counts {\n    pub fn bytes', '''impl Counts {
    // Conservative build-credit estimate from complete validated scan counts.
    // Parameters, local-group overhead and control patching are omitted.
    pub(crate) fn estimated_build_work(self, body_bytes: usize) -> Option<u64> {
        u64::try_from(body_bytes).ok()?
            .checked_add(u64::try_from(self.locals).ok()?.checked_mul(2)?)?
            .checked_add(u64::try_from(self.instructions).ok()?.checked_mul(2)?)?
            .checked_add(u64::try_from(self.targets).ok()?.checked_mul(2)?)
            .map(|cost| cost.max(1))
    }
    pub fn bytes''')
replace(Path('src/experimental_swift_reactor/cache.rs'),'pub(crate) struct SwiftResident {\n    decoded: DecodedFunction,\n    ticket: ReservationTicket,\n}', '''pub(crate) struct SwiftResident {
    decoded: DecodedFunction,
    ticket: ReservationTicket,
    estimated_build_work: u64,
}''')
insert='''// Miss-only metadata. Hits and releases never inspect or mutate these values.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct RetentionRank {
    slot: usize,
    cost: u64,
    age: u64,
    last_used: u64,
}
// Three complete disjoint copies are added to the operation reservation. These
// named fields cover the new method/helper parameters, locals, closure/reborrow
// values, checked-arithmetic intermediates and caller/return ownership. They do
// not reuse another inventory's unused bytes or claim physical stack placement.
struct CostRetentionInventory {
    victim_slots: &'static [SwiftSlot],
    victim_plan: &'static [bool; 64],
    victim_meter: &'static mut SwiftMeter<'static, 'static>,
    now: u64,
    best: Option<RetentionRank>,
    iterator: std::iter::Enumerate<std::slice::Iter<'static, SwiftSlot>>,
    loop_index: usize,
    loop_slot: &'static SwiftSlot,
    resident: &'static SwiftResident,
    candidate: RetentionRank,
    previous: RetentionRank,
    before: bool,
    helper_candidate: RetentionRank,
    helper_previous: RetentionRank,
    helper_meter: &'static mut SwiftMeter<'static, 'static>,
    left: u128,
    right: u128,
    product_option: Option<u128>,
    product_result: Result<u128, SwiftRunFailure>,
    age_option: Option<u64>,
    age_result: Result<u64, SwiftRunFailure>,
    compare_return: Result<bool, SwiftRunFailure>,
    victim_return: Result<usize, SwiftRunFailure>,
    best_map_receiver: Option<RetentionRank>,
    best_map_arg: RetentionRank,
    best_map_result: Option<usize>,
    failure_reborrow: &'static mut SwiftMeter<'static, 'static>,
    cost_method_self: decode::Counts,
    cost_method_body_bytes: usize,
    cost_conversion: Result<u64, std::num::TryFromIntError>,
    cost_intermediate: Option<u64>,
    cost_map_arg: u64,
    cost_return: Option<u64>,
    build_cost: u64,
    build_cost_result: Result<u64, SwiftRunFailure>,
    build_cost_receiver: decode::Counts,
    build_cost_body: usize,
    build_meter_reborrow: &'static mut SwiftMeter<'static, 'static>,
    default_slots: &'static [SwiftSlot],
    default_plan: &'static [bool; 64],
    default_meter: &'static mut SwiftMeter<'static, 'static>,
    default_oldest: Option<usize>,
    default_iterator: std::iter::Enumerate<std::slice::Iter<'static, SwiftSlot>>,
    default_index: usize,
    default_slot: &'static SwiftSlot,
    default_closure_arg: usize,
    default_result: Result<usize, SwiftRunFailure>,
}
fn retention_before(
    candidate: RetentionRank,
    previous: RetentionRank,
    meter: &mut SwiftMeter<'_, '_>,
) -> Result<bool, SwiftRunFailure> {
    // Both products fit u128 for valid u64 operands, but remain checked.
    let left = u128::from(candidate.cost)
        .checked_mul(u128::from(previous.age))
        .ok_or_else(|| meter.error(CacheFailureKind::DecoderMismatch, "swift_retention_product"))?;
    let right = u128::from(previous.cost)
        .checked_mul(u128::from(candidate.age))
        .ok_or_else(|| meter.error(CacheFailureKind::DecoderMismatch, "swift_retention_product"))?;
    Ok(left < right || (left == right && (candidate.last_used, candidate.slot)
        < (previous.last_used, previous.slot)))
}
'''
replace(Path('src/experimental_swift_reactor/cache.rs'),'pub(crate) struct SwiftScratch',insert+'\npub(crate) struct SwiftScratch')
replace(Path('src/experimental_swift_reactor/cache.rs'),'        (3, size_of::<OperationScalarInventory>()),\n        (3, size_of::<ResidentIndexInventory>()),\n        (3, size_of::<PlanInventory>()),','        (3, size_of::<OperationScalarInventory>()),\n        (3, size_of::<ResidentIndexInventory>()),\n        (3, size_of::<PlanInventory>()),\n        (3, size_of::<CostRetentionInventory>()),')
needle='''    fn scan(
        snapshot: &ValidatedSwiftReactor,'''
victim='''    fn resident_victim(
        slots: &[SwiftSlot],
        plan: &[bool; 64],
        meter: &mut SwiftMeter<'_, '_>,
    ) -> Result<usize, SwiftRunFailure> {
        meter.work(1)?; // one fixed work-clock snapshot per victim scan
        let now = meter.work_used();
        let mut best: Option<RetentionRank> = None;
        for (index, slot) in slots.iter().enumerate() {
            meter.work(1)?; // original per-slot eligibility credit
            if plan[index] || slot.pins != 0 || slot.resident.is_none() {
                continue;
            }
            // Eight logical units, precharged before any added reads/work:
            // cost+nonzero; recency+checked-age/clamp; candidate preparation;
            // best probe; left product; right product; ratio/tie comparison;
            // conditional local-rank publication. Not a CPU instruction count.
            meter.work(8)?;
            let resident = slot.resident.as_ref().expect("eligible resident");
            if resident.estimated_build_work == 0 {
                return Err(meter.error(CacheFailureKind::DecoderMismatch, "swift_retention_cost"));
            }
            let candidate = RetentionRank {
                slot: index,
                cost: resident.estimated_build_work,
                age: now.checked_sub(slot.last_used)
                    .ok_or_else(|| meter.error(CacheFailureKind::DecoderMismatch, "swift_retention_age"))?
                    .max(1),
                last_used: slot.last_used,
            };
            let before = if let Some(previous) = best {
                retention_before(candidate, previous, meter)?
            } else {
                true
            };
            if before { best = Some(candidate); }
        }
        best.map(|rank| rank.slot)
            .ok_or_else(|| meter.error(CacheFailureKind::AllPinned, "all_entries_pinned"))
    }
'''
replace(Path('src/experimental_swift_reactor/cache.rs'),needle,victim+needle)
replace(Path('src/experimental_swift_reactor/cache.rs'),'''    ) -> Result<SwiftResident, SwiftRunFailure> {
        let bytes = counts.bytes(meter)?;''','''    ) -> Result<SwiftResident, SwiftRunFailure> {
        let bytes = counts.bytes(meter)?;
        // Twelve logical units: body+three count reads/conversions; three
        // doubles; three checked sums; clamp; eventual resident field write.
        // Cost checking/publication charge precedes entry admission and build.
        meter.work(12)?;
        let estimated_build_work = counts.estimated_build_work(body.body.len())
            .ok_or_else(|| meter.error(CacheFailureKind::DecoderMismatch, "swift_retention_cost_overflow"))?;
''')
replace(Path('src/experimental_swift_reactor/cache.rs'),'            Ok(decoded) => Ok(SwiftResident { decoded, ticket }),','            Ok(decoded) => Ok(SwiftResident { decoded, ticket, estimated_build_work }),')
print('candidate changes applied only to copied source')
