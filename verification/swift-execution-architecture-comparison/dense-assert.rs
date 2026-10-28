fn resident_assert_index(cache: &SwiftFunctionCache) {
    let index = inspection::resident_index(cache);
    assert_eq!(index.len(), 80_000);
    let slots = inspection::elision_slots(cache);
    let mut seen = [false; 256];
    // Independent exhaustive map-to-slot walk, not the candidate's helper.
    for (key, encoded) in index.iter().enumerate() {
        if *encoded == 0 { continue; }
        let slot = usize::from(*encoded - 1);
        assert!(slot < slots.len());
        assert_eq!(slots[slot][1], key as u64);
        assert!(!seen[slot]);
        seen[slot] = true;
    }
    for (slot, actual) in slots.iter().enumerate() {
        assert_eq!(seen[slot], actual[1] != u64::MAX);
    }
    let records = inspection::dense_pin_records(cache);
    let mut expected = 0u64;
    for (slot, (nonce, _)) in records.iter().enumerate() {
        if *nonce == 0 { expected |= 1u64 << slot; }
    }
    assert_eq!(inspection::dense_pin_mask(cache), expected);
}
