#!/usr/bin/env python3
"""Original selected bounded resident-index implementation in an isolated VM copy."""
from pathlib import Path
HERE=Path(__file__).resolve().parent; S=HERE/'source'
def edit(name,old,new,count=1):
    p=S/name;s=p.read_text();assert s.count(old)==count,(name,old[:80],s.count(old),count);p.write_text(s.replace(old,new))
b='src/experimental/cache/borrowed.rs';c='src/experimental_swift_reactor/cache.rs'
edit(b,'    fn scan(\n        snapshot: &Self::Snapshot,','''    // Defaults deliberately preserve the literal frozen lookup and work trace.
    fn resident_lookup(
        slots: &[Self::Slot],
        _: &mut Self::Scratch<'_>,
        function: u32,
        meter: &mut Self::Meter<'_, '_>,
    ) -> Result<Option<usize>, Self::Failure> {
        let mut hit = None;
        for (index, slot) in slots.iter().enumerate() {
            meter.work(1)?;
            if slot.entry().is_some_and(|e| e.function == function) {
                hit = Some(index);
                break;
            }
        }
        Ok(hit)
    }
    fn resident_remove(
        _: &[Self::Slot],
        _: &mut Self::Scratch<'_>,
        _: usize,
        _: &mut Self::Meter<'_, '_>,
    ) -> Result<(), Self::Failure> {
        Ok(())
    }
    fn resident_insert(
        _: &[Self::Slot],
        _: &mut Self::Scratch<'_>,
        _: u32,
        _: usize,
        _: &mut Self::Meter<'_, '_>,
    ) -> Result<(), Self::Failure> {
        Ok(())
    }
    fn scan(
        snapshot: &Self::Snapshot,''')
edit(b,'''    let mut hit = None;
    for (index, slot) in parts.slots.iter().enumerate() {
        meter.work(1)?;
        if slot.entry().is_some_and(|e| e.function == function) {
            hit = Some(index);
            break;
        }
    }''','''    let hit = M::resident_lookup(parts.slots, &mut parts.scratch, function, meter)?;''')
edit(b,'''                let old = parts.slots[index].take().expect("planned entry");''','''                M::resident_remove(parts.slots, &mut parts.scratch, index, meter)?;
                let old = parts.slots[index].take().expect("planned entry");''')
edit(b,'''        meter.usage_mut().decoded(next_decodes, bytes);
        parts.slots[index].set(entry);''','''        if let Err(error) = M::resident_insert(
            parts.slots, &mut parts.scratch, function, index, meter,
        ) {
            let _ = M::drop_entry(entry, meter);
            let _ = meter.construction(0);
            return Err(error);
        }
        // Both hooks precharge their complete mutation; no fallible operation
        // separates the index update from the infallible slot publication.
        meter.usage_mut().decoded(next_decodes, bytes);
        parts.slots[index].set(entry);''')
edit(c,'const PATCH_CAPACITY: usize = 512;','''const PATCH_CAPACITY: usize = 512;
const RESIDENT_BUCKETS: usize = 128;
const RESIDENT_LINKS: usize = 64;
const RESIDENT_INDEX_BYTES: usize = RESIDENT_BUCKETS + RESIDENT_LINKS;

pub(crate) struct SwiftScratch<'a> {
    patches: &'a mut [decode::Patch],
    index: &'a mut [u8],
}
// Original fixed hash. The key always remains the actual decoded slot value.
fn resident_bucket(function: u32) -> usize {
    (function.wrapping_mul(0x9e37_79b9) >> 25) as usize
}
struct ResidentMatch {
    slot: usize,
    link_cell: usize,
    next: u8,
}
// Every named scalar/borrow in the bounded helper chain has disjoint modeled
// storage, in addition to the actual owner and generic caller inventories.
struct ResidentIndexInventory {
    function: u32,
    bucket: usize,
    link_cell: usize,
    node: u8,
    slot: usize,
    next: u8,
    seen: u64,
    bit: u64,
    visited: std::ops::Range<usize>,
    hit: Option<ResidentMatch>,
    found: ResidentMatch,
    index: &'static [u8],
    mutable_index: &'static mut [u8],
    slots: &'static [SwiftSlot],
    entry: &'static DecodedFunction,
    scratch: &'static mut SwiftScratch<'static>,
    meter: &'static mut SwiftMeter<'static, 'static>,
    lookup_return: Result<Option<ResidentMatch>, SwiftRunFailure>,
    insert_remove_return: Result<(), SwiftRunFailure>,
    match_option: Option<ResidentMatch>,
    index_reborrow: &'static mut [u8],
    slots_reborrow: &'static [SwiftSlot],
    meter_reborrow: &'static mut SwiftMeter<'static, 'static>,
}
fn resident_find(
    index: &[u8],
    slots: &[SwiftSlot],
    function: u32,
    meter: &mut SwiftMeter<'_, '_>,
) -> Result<Option<ResidentMatch>, SwiftRunFailure> {
    if index.len() != RESIDENT_INDEX_BYTES || slots.len() > RESIDENT_LINKS {
        return Err(meter.error(CacheFailureKind::DecoderMismatch, "swift_cache_index_layout"));
    }
    meter.work(1)?; // requested-key hash
    let bucket = resident_bucket(function);
    meter.work(1)?; // head read
    let mut link_cell = bucket;
    let mut node = index[link_cell];
    let mut seen = 0u64;
    let mut hit = None;
    for _ in 0..RESIDENT_LINKS {
        if node == 0 { return Ok(hit); }
        meter.work(1)?; // encoded-link/slot and cycle validation
        let slot = usize::from(node - 1);
        if slot >= slots.len() {
            return Err(meter.error(CacheFailureKind::DecoderMismatch, "swift_cache_index_slot"));
        }
        let bit = 1u64 << slot;
        if seen & bit != 0 {
            return Err(meter.error(CacheFailureKind::DecoderMismatch, "swift_cache_index_cycle"));
        }
        seen |= bit;
        meter.work(1)?; // actual resident-key probe
        let entry = slots[slot].entry().ok_or_else(||
            meter.error(CacheFailureKind::DecoderMismatch, "swift_cache_index_empty"))?;
        meter.work(1)?; // actual key hash validation, never trust the index alone
        if resident_bucket(entry.function) != bucket {
            return Err(meter.error(CacheFailureKind::DecoderMismatch, "swift_cache_index_bucket"));
        }
        meter.work(1)?; // next-link read
        let next = index[RESIDENT_BUCKETS + slot];
        if entry.function == function {
            if hit.is_some() {
                return Err(meter.error(CacheFailureKind::DecoderMismatch, "swift_cache_index_duplicate"));
            }
            hit = Some(ResidentMatch { slot, link_cell, next });
        }
        link_cell = RESIDENT_BUCKETS + slot;
        node = next;
    }
    // An exactly64-node chain ending here is valid; any further link fails.
    if node == 0 { Ok(hit) } else {
        Err(meter.error(CacheFailureKind::DecoderMismatch, "swift_cache_index_cycle"))
    }
}''')
edit(c,'    patches: Vec<decode::Patch>,\n    buffers: [Option<ReservationTicket>; 3],','    patches: Vec<decode::Patch>,\n    index: Vec<u8>,\n    buffers: [Option<ReservationTicket>; 4],',2)
edit(c,'            patches: Vec::new(),','            patches: Vec::new(),\n            index: Vec::new(),')
edit(c,'''        if let Some(adopted) = self.adopted.take() {''','''        if let Some(ticket) = self.buffers[3].take() {
            let _ = control.drop_reserved(take(&mut self.index), ticket);
        }
        if let Some(adopted) = self.adopted.take() {''')
edit(c,'''    buffers_range: std::ops::Range<usize>,''','''    buffers_range: std::ops::Range<usize>,
    index_range: std::ops::Range<usize>,
    index: &'static mut Vec<u8>,
    reserve_index_values: &'static mut Vec<u8>,
    reserve_index_control: &'static mut CacheControl<'static>,''',2)
# These concrete reborrow types change when the associated Scratch expands.
edit(c,"&'static mut &'static mut [decode::Patch]","&'static mut SwiftScratch<'static>",6)
# Three instances above are declarations; three are layout field type assertions.
edit(c,'        (4, size_of::<Vec<decode::Patch>>()),','''        (4, size_of::<Vec<decode::Patch>>()),
        (4, size_of::<Vec<u8>>()),
        (3, size_of::<SwiftScratch<'static>>()),''')
edit(c,'        (3, size_of::<Vec<decode::Patch>>()),','''        (3, size_of::<Vec<decode::Patch>>()),
        (3, size_of::<Vec<u8>>()),
        (4, size_of::<Option<ReservationTicket>>()),
        (4, size_of::<ReservationTicket>()),''')
edit(c,'        (3, size_of::<OperationScalarInventory>()),','''        (3, size_of::<OperationScalarInventory>()),
        (3, size_of::<ResidentIndexInventory>()),
        (3, size_of::<SwiftScratch<'static>>()),
        (3, size_of::<ResidentMatch>()),
        (3, size_of::<Option<ResidentMatch>>()),''')
edit(c,'                scratch: &mut self.patches,','''                scratch: SwiftScratch { patches: &mut self.patches, index: &mut self.index },''')
edit(c,'''        let SwiftFunctionCache {
            adopted, header, ..
        } = cache;''','''        if let Some(ticket) = cache.buffers[3].take() {
            capture(&mut failure, control.drop_reserved_with_wasi(
                take(&mut cache.index), ticket, wasi.map(AccountedWasi::usage),
            ));
        }
        let SwiftFunctionCache {
            adopted, header, ..
        } = cache;''')
edit(c,'                patches: take(&mut partial.patches),','                patches: take(&mut partial.patches),\n                index: take(&mut partial.index),')
edit(c,'''        self.control.check()?;
        let owner = next_owner()''','''        partial.buffers[3] = Some(self.control.admit(RESIDENT_INDEX_BYTES)?);
        reserve(&mut partial.index, RESIDENT_INDEX_BYTES, &mut self.control)?;
        for _ in 0..RESIDENT_INDEX_BYTES {
            self.control.work(1)?;
            partial.index.push(0);
        }
        self.control.check()?;
        let owner = next_owner()''')
edit(c,'            + PATCH_CAPACITY * size_of::<decode::Patch>();','            + PATCH_CAPACITY * size_of::<decode::Patch>()\n            + RESIDENT_INDEX_BYTES;')
edit(c,'                scratch: &mut cache.patches,','''                scratch: SwiftScratch { patches: &mut cache.patches, index: &mut cache.index },''')
edit(c,"    type Scratch<'a> = &'a mut [decode::Patch];","    type Scratch<'a> = SwiftScratch<'a>;")
edit(c,'        scratch: &mut &mut [decode::Patch],','        scratch: &mut SwiftScratch<\'_>,',3)
edit(c,'        reset(scratch, meter)?;','        reset(scratch.patches, meter)?;',2)
edit(c,'                controls: scratch,','                controls: scratch.patches,',2)
edit(c,'''    fn scan(
        snapshot: &ValidatedSwiftReactor,''','''    fn resident_lookup(
        slots: &[SwiftSlot], scratch: &mut SwiftScratch<'_>, function: u32,
        meter: &mut SwiftMeter<'_, '_>,
    ) -> Result<Option<usize>, SwiftRunFailure> {
        Ok(resident_find(scratch.index, slots, function, meter)?.map(|found| found.slot))
    }
    fn resident_remove(
        slots: &[SwiftSlot], scratch: &mut SwiftScratch<'_>, slot: usize,
        meter: &mut SwiftMeter<'_, '_>,
    ) -> Result<(), SwiftRunFailure> {
        meter.work(1)?; // victim-key probe
        let function = slots.get(slot).and_then(CacheSlot::entry)
            .ok_or_else(|| meter.error(CacheFailureKind::DecoderMismatch, "swift_cache_index_victim"))?.function;
        let found = resident_find(scratch.index, slots, function, meter)?
            .filter(|found| found.slot == slot)
            .ok_or_else(|| meter.error(CacheFailureKind::DecoderMismatch, "swift_cache_index_missing"))?;
        // One complete link mutation is admitted before either write.
        meter.work(2)?;
        scratch.index[found.link_cell] = found.next;
        scratch.index[RESIDENT_BUCKETS + slot] = 0;
        Ok(())
    }
    fn resident_insert(
        slots: &[SwiftSlot], scratch: &mut SwiftScratch<'_>, function: u32, slot: usize,
        meter: &mut SwiftMeter<'_, '_>,
    ) -> Result<(), SwiftRunFailure> {
        if resident_find(scratch.index, slots, function, meter)?.is_some() {
            return Err(meter.error(CacheFailureKind::DecoderMismatch, "swift_cache_index_duplicate"));
        }
        meter.work(1)?; // insertion slot/link validation
        if slot >= slots.len() || slots[slot].entry().is_some()
            || scratch.index[RESIDENT_BUCKETS + slot] != 0 {
            return Err(meter.error(CacheFailureKind::DecoderMismatch, "swift_cache_index_insert"));
        }
        meter.work(1)?; // insertion hash
        let bucket = resident_bucket(function);
        meter.work(1)?; // head read for new link
        let next = scratch.index[bucket];
        meter.work(2)?; // admit both link writes before infallible publication
        scratch.index[RESIDENT_BUCKETS + slot] = next;
        scratch.index[bucket] = (slot + 1) as u8;
        Ok(())
    }
    fn scan(
        snapshot: &ValidatedSwiftReactor,''')
# Test-only direct decoder helper constructs the expanded scratch as well.
edit(c,'            &mut &mut cache.patches,','            &mut SwiftScratch { patches: &mut cache.patches, index: &mut cache.index },',2)
# New measurable inventory and storage rows are included in existing layout receipt.
edit(c,'        row!(PermanentScalarInventory);','''        row!(ResidentIndexInventory);
        row!(ResidentMatch);
        row!(SwiftScratch<'static>);
        row!(Vec<u8>);
        row!(PermanentScalarInventory);''')
