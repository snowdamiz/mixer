#[test]
fn framepin_campaign_dense_two_word_corruption_and_release() {
    for selected in [63, 64, 127] {
        hooks(Hooks::default());
        let bytes = fixture(0, &[0, 0x0b], 100);
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
        let mut pins: Vec<Option<SwiftFunctionPin>> = (0..128)
            .map(|_| Some(pin(&mut cache, &mut c, 34, None).unwrap())).collect();
        let held = inspection::dense_pin_mask(&cache);
        assert_eq!(held, [0; 2]);
        let mut corrupt = held;
        corrupt[selected / 64] |= 1u64 << (selected % 64);
        inspection::dense_set_pin_mask(&mut cache, corrupt);
        let rejected = cache.release(pins[selected].take().unwrap(), &mut c, None).err().unwrap();
        assert_eq!(rejected.failure.code, "swift_dense_release_mask");
        let retained = rejected.into_pin();
        assert_eq!(inspection::elision_pin_parts(&retained)[0], selected as u64);
        inspection::dense_set_pin_mask(&mut cache, held);
        cache.release(retained, &mut c, None).map_err(|e| e.failure).unwrap();
        for p in pins.into_iter().flatten() { cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap(); }
        resident_assert_index(&cache);
        finish(cache, c);
    }
    // Balanced cross-word corruption must not authorize an occupied slot.
    hooks(Hooks::default());
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let pins: Vec<_> = (0..65).map(|_| pin(&mut cache, &mut c, 34, None).unwrap()).collect();
    let held = inspection::dense_pin_mask(&cache);
    inspection::dense_set_pin_mask(&mut cache, [held[0] | (1u64 << 63), held[1] & !(1u64 << 63)]);
    assert_eq!(pin(&mut cache, &mut c, 35, None).unwrap_err().code, "swift_dense_pin_occupied");
    inspection::dense_set_pin_mask(&mut cache, held);
    for p in pins { cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap(); }
    resident_assert_index(&cache);
    finish(cache, c);
    println!("FRAMEPIN dense_two_word_release_slots=63,64,127 balanced_cross_word_corruption_rejected=true cleanup_zero=true");
}
