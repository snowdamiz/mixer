    // Frozen defaults preserve literal first-free search and original work trace.
    fn available_pin(pins: &[PinRecord], _: &mut Self::Scratch<'_>, meter: &mut Self::Meter<'_, '_>) -> Result<usize, Self::Failure> {
        for (index, record) in pins.iter().enumerate() {
            meter.work(1)?;
            if record.nonce == 0 { return Ok(index); }
        }
        Err(meter.error(CacheFailureKind::PinExhausted, "pin_slots_exhausted"))
    }
    fn pin_published(_: &mut Self::Scratch<'_>, _: usize) {}
    fn validate_pin_release(_: &[PinRecord], _: &mut Self::Scratch<'_>, _: usize, _: &mut impl PinDiagnostic<Self::Failure>) -> Result<(), Self::Failure> { Ok(()) }
    fn pin_released(_: &mut Self::Scratch<'_>, _: usize) {}
