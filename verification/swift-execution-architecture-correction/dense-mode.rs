    fn available_pin(pins: &[PinRecord], scratch: &mut SwiftScratch<'_>, meter: &mut SwiftMeter<'_, '_>) -> Result<usize, SwiftRunFailure> {
        meter.work(3)?; // layout, availability word, live-count agreement
        if pins.len() > 64 || *scratch.free_pins & !dense_allowed_pins(pins.len()) != 0
            || (*scratch.free_pins).count_ones() as usize + meter.usage().active_pins != pins.len()
        { return Err(meter.error(CacheFailureKind::InvalidPin, "swift_dense_pin_mask")); }
        if *scratch.free_pins == 0 {
            for record in pins {
                meter.work(1)?;
                if record.nonce == 0 { return Err(meter.error(CacheFailureKind::InvalidPin, "swift_dense_pin_orphan")); }
            }
            return Err(meter.error(CacheFailureKind::PinExhausted, "pin_slots_exhausted"));
        }
        let slot = (*scratch.free_pins).trailing_zeros() as usize;
        meter.work(2)?; // selected record and eventual single mask write
        if pins.get(slot).is_none_or(|record| record.nonce != 0) { return Err(meter.error(CacheFailureKind::InvalidPin, "swift_dense_pin_occupied")); }
        Ok(slot)
    }
    fn pin_published(scratch: &mut SwiftScratch<'_>, slot: usize) {
        // Exclusive borrow retains the preflight bit; record publication is adjacent.
        *scratch.free_pins &= !(1u64 << slot);
    }
    fn validate_pin_release(pins: &[PinRecord], scratch: &mut SwiftScratch<'_>, slot: usize, diagnostic: &mut impl PinDiagnostic<SwiftRunFailure>) -> Result<(), SwiftRunFailure> {
        // Original checked_record validated owner/nonce/entry. No stop polling
        // here: terminal-owner cleanup must still be able to release its pins.
        if pins.len() > 64 || slot >= pins.len() || *scratch.free_pins & !dense_allowed_pins(pins.len()) != 0 || *scratch.free_pins & (1u64 << slot) != 0 {
            return Err(diagnostic.invalid("swift_dense_release_mask"));
        }
        Ok(())
    }
    fn pin_released(scratch: &mut SwiftScratch<'_>, slot: usize) { *scratch.free_pins |= 1u64 << slot; }
    fn resident_lookup(slots: &[SwiftSlot], scratch: &mut SwiftScratch<'_>, function: u32, meter: &mut SwiftMeter<'_, '_>) -> Result<Option<usize>, SwiftRunFailure> {
        Ok(resident_find(scratch.index, slots, function, meter)?.map(|found| found.slot))
    }
    fn resident_remove(slots: &[SwiftSlot], scratch: &mut SwiftScratch<'_>, slot: usize, meter: &mut SwiftMeter<'_, '_>) -> Result<(), SwiftRunFailure> {
        dense_audit(scratch.index, slots, meter)?;
        meter.work(3)?; // victim bounds, key, reverse cell
        let function = slots.get(slot).and_then(CacheSlot::entry).ok_or_else(|| meter.error(CacheFailureKind::DecoderMismatch, "swift_dense_victim"))?.function;
        if function as usize >= DENSE_FUNCTIONS || scratch.index[function as usize] != (slot + 1) as u16 { return Err(meter.error(CacheFailureKind::DecoderMismatch, "swift_dense_remove")); }
        meter.work(1)?;
        scratch.index[function as usize] = 0;
        Ok(())
    }
    fn resident_insert(slots: &[SwiftSlot], scratch: &mut SwiftScratch<'_>, function: u32, slot: usize, meter: &mut SwiftMeter<'_, '_>) -> Result<(), SwiftRunFailure> {
        dense_audit(scratch.index, slots, meter)?;
        meter.work(4)?; // key/slot bounds, absent mapping, empty slot
        if function as usize >= DENSE_FUNCTIONS || slot >= slots.len() || scratch.index[function as usize] != 0 || slots[slot].entry().is_some() { return Err(meter.error(CacheFailureKind::DecoderMismatch, "swift_dense_insert")); }
        meter.work(1)?;
        scratch.index[function as usize] = (slot + 1) as u16;
        Ok(())
    }
