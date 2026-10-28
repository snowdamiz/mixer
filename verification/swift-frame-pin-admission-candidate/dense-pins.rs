// Two fixed words avoid new 16-byte alignment requirements. Every shift is
// strictly below 64, including empty, 64-pin and 128-pin selections.
fn dense_allowed_pins(len: usize) -> [u64; 2] {
    if len <= 64 {
        [if len == 64 { u64::MAX } else { (1u64 << len) - 1 }, 0]
    } else if len <= 128 {
        [u64::MAX, if len == 128 { u64::MAX } else { (1u64 << (len - 64)) - 1 }]
    } else {
        [0; 2] // Invalid layout is rejected by admission/release, never widened.
    }
}
// MODE METHODS
    fn available_pin(pins: &[PinRecord], scratch: &mut SwiftScratch<'_>, meter: &mut SwiftMeter<'_, '_>) -> Result<usize, SwiftRunFailure> {
        meter.work(6)?; // layout, two mask words, two popcounts, live agreement
        let permitted = dense_allowed_pins(pins.len());
        if pins.len() > 128
            || scratch.free_pins[0] & !permitted[0] != 0
            || scratch.free_pins[1] & !permitted[1] != 0
            || (scratch.free_pins[0].count_ones() + scratch.free_pins[1].count_ones()) as usize + meter.usage().active_pins != pins.len()
        { return Err(meter.error(CacheFailureKind::InvalidPin, "swift_dense_pin_mask")); }
        if *scratch.free_pins == [0; 2] {
            for record in pins {
                meter.work(1)?;
                if record.nonce == 0 { return Err(meter.error(CacheFailureKind::InvalidPin, "swift_dense_pin_orphan")); }
            }
            return Err(meter.error(CacheFailureKind::PinExhausted, "pin_slots_exhausted"));
        }
        let word = usize::from(scratch.free_pins[0] == 0);
        let slot = word * 64 + scratch.free_pins[word].trailing_zeros() as usize;
        meter.work(4)?; // word choice, bit choice, actual record, eventual bit write
        if pins.get(slot).is_none_or(|record| record.nonce != 0) { return Err(meter.error(CacheFailureKind::InvalidPin, "swift_dense_pin_occupied")); }
        Ok(slot)
    }
    fn pin_published(scratch: &mut SwiftScratch<'_>, slot: usize) {
        // The validated free slot and actual nonce record publish adjacently.
        scratch.free_pins[slot / 64] &= !(1u64 << (slot % 64));
    }
    fn validate_pin_release(pins: &[PinRecord], scratch: &mut SwiftScratch<'_>, slot: usize, diagnostic: &mut impl PinDiagnostic<SwiftRunFailure>) -> Result<(), SwiftRunFailure> {
        let permitted = dense_allowed_pins(pins.len());
        // Original checked_record already validates owner, nonce and entry.
        // No fuel/cancellation polling is added to terminal-owner cleanup.
        if pins.len() > 128 || slot >= pins.len()
            || scratch.free_pins[0] & !permitted[0] != 0
            || scratch.free_pins[1] & !permitted[1] != 0
            || scratch.free_pins[slot / 64] & (1u64 << (slot % 64)) != 0 {
            return Err(diagnostic.invalid("swift_dense_release_mask"));
        }
        Ok(())
    }
    fn pin_released(scratch: &mut SwiftScratch<'_>, slot: usize) {
        scratch.free_pins[slot / 64] |= 1u64 << (slot % 64);
    }
