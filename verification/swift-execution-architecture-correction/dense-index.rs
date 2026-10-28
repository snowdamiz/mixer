// Owned dense index. Validation bounds imports + definitions to 80,000.
const DENSE_FUNCTIONS: usize = 80_000;
// Conservative disjoint locals/borrows/returns, charged in each call envelope.
struct DenseIndexInventory {
    function: u32, slot: usize, probe: usize, encoded: u16, key: usize,
    slots: &'static [SwiftSlot], index: &'static [u16], mutable_index: &'static mut [u16],
    scratch: &'static mut SwiftScratch<'static>, meter: &'static mut SwiftMeter<'static, 'static>,
    entry: &'static DecodedFunction, entry_option: Option<&'static DecodedFunction>,
    slot_option: Option<&'static SwiftSlot>, cell_option: Option<&'static u16>,
    range: std::ops::Range<usize>, pair: (usize, &'static SwiftSlot),
    loop_iter: std::iter::Enumerate<std::slice::Iter<'static, SwiftSlot>>,
    match_value: ResidentMatch, match_return: Result<Option<ResidentMatch>, SwiftRunFailure>,
    audit_return: Result<(), SwiftRunFailure>,
}
struct DensePinInventory {
    pins: &'static [PinRecord], scratch: &'static mut SwiftScratch<'static>,
    mask: u64, permitted: u64, slot: usize, len: usize, remaining: usize, active: usize,
    record: &'static PinRecord, record_option: Option<&'static PinRecord>,
    free_bits: &'static mut u64, meter: &'static mut SwiftMeter<'static, 'static>,
    diagnostic: &'static mut CacheControl<'static>, iter: std::slice::Iter<'static, PinRecord>,
    slot_return: Result<usize, SwiftRunFailure>, check_return: Result<(), SwiftRunFailure>,
    outcome: SwiftRunFailure,
}
fn dense_allowed_pins(len: usize) -> u64 {
    if len == 64 { u64::MAX } else if len == 0 { 0 } else { (1u64 << len) - 1 }
}
fn dense_audit(index: &[u16], slots: &[SwiftSlot], meter: &mut SwiftMeter<'_, '_>) -> Result<(), SwiftRunFailure> {
    if index.len() != DENSE_FUNCTIONS || slots.len() > RESIDENT_LINKS {
        return Err(meter.error(CacheFailureKind::DecoderMismatch, "swift_dense_layout"));
    }
    for (slot, actual) in slots.iter().enumerate() {
        meter.work(1)?; // actual occupied-slot probe
        if let Some(entry) = actual.entry() {
            meter.work(3)?; // actual key, key bounds, reverse cell
            if entry.function as usize >= DENSE_FUNCTIONS || index[entry.function as usize] != (slot + 1) as u16 {
                return Err(meter.error(CacheFailureKind::DecoderMismatch, "swift_dense_reverse"));
            }
        }
    }
    Ok(())
}
fn resident_find(index: &[u16], slots: &[SwiftSlot], function: u32, meter: &mut SwiftMeter<'_, '_>) -> Result<Option<ResidentMatch>, SwiftRunFailure> {
    if index.len() != DENSE_FUNCTIONS || slots.len() > RESIDENT_LINKS {
        return Err(meter.error(CacheFailureKind::DecoderMismatch, "swift_dense_layout"));
    }
    meter.work(2)?; // requested key bound and direct cell
    let encoded = *index.get(function as usize).ok_or_else(|| meter.error(CacheFailureKind::DecoderMismatch, "swift_dense_key"))?;
    if encoded == 0 {
        // Missing map cells cannot turn actual residents into duplicate decodes.
        dense_audit(index, slots, meter)?;
        return Ok(None);
    }
    meter.work(3)?; // encoded slot bound, occupied cell, actual function key
    let slot = usize::from(encoded - 1);
    let entry = slots.get(slot).and_then(CacheSlot::entry).ok_or_else(|| meter.error(CacheFailureKind::DecoderMismatch, "swift_dense_slot"))?;
    if entry.function != function { return Err(meter.error(CacheFailureKind::DecoderMismatch, "swift_dense_identity")); }
    Ok(Some(ResidentMatch { slot, link_cell: function as usize, next: 0 }))
}
