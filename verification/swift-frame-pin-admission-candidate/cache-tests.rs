// Real 128-record owners; no fabricated frame, token or accounting ledger.
#[test]
fn framepin_campaign_pin_boundaries_stale_reuse_and_foreign_release() {
    for selected in [0, 63, 64, 127] {
        hooks(Hooks::default());
        let bytes = fixture(0, &[0, 0x0b], 100);
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
        let (mut other_c, other) = new(&bytes, SwiftRunBudget::default());
        let mut pins: Vec<Option<SwiftFunctionPin>> = (0..128)
            .map(|_| Some(pin(&mut cache, &mut c, 34, None).unwrap())).collect();
        let p = pins[selected].take().unwrap();
        assert_eq!(inspection::elision_pin_parts(&p)[0], selected as u64);
        let stale = inspection::stale(&p);
        // The original release path returns ownership after foreign control.
        let rejected = cache.release(p, &mut other_c, None).err().unwrap();
        assert_eq!(c.usage(None).live.active_pins.current, 128);
        cache.release(rejected.into_pin(), &mut c, None).map_err(|e| e.failure).unwrap();
        let replacement = pin(&mut cache, &mut c, 35, None).unwrap();
        assert_eq!(inspection::elision_pin_parts(&replacement)[0], selected as u64);
        assert_eq!(cache.release(stale, &mut c, None).err().unwrap().failure.code, "stale_pin");
        // Release remains available after the first failure becomes sticky.
        cache.release(replacement, &mut c, None).map_err(|e| e.failure).unwrap();
        for p in pins.into_iter().flatten() { cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap(); }
        resident_assert_index(&cache);
        finish(cache, c);
        finish(other, other_c);
    }
    println!("FRAMEPIN pin_slots=0,63,64,127 recursive_records=128 foreign_stale_reuse_and_terminal_release=true");
}

#[test]
fn framepin_campaign_constructor_pin_payload_and_work_delta() {
    let bytes = fixture(0, &[0, 0x0b], 100);
    let mut rows = Vec::new();
    for pins in [0, 63, 64, 65, 127, 128] {
        hooks(Hooks::default());
        let (c, cache) = new(&bytes, SwiftRunBudget { active_pins: pins, ..SwiftRunBudget::default() });
        let u = c.usage(None);
        rows.push((pins, u.reservations.cache.current, u.cache_work));
        finish(cache, c);
    }
    for pair in rows.windows(2) {
        let added = pair[1].0 - pair[0].0;
        assert_eq!(pair[1].1 - pair[0].1, added * size_of::<crate::experimental::cache::PinRecord>());
        assert_eq!(pair[1].2 - pair[0].2, added as u64);
    }
    assert_eq!(size_of::<crate::experimental::cache::PinRecord>(), 16); // selected x86_64 CI target
    println!("FRAMEPIN constructor_pin_payload_delta=1024 constructor_pin_work_delta=64 additional_allocations=0 additional_tickets=0");
}

#[test]
fn framepin_campaign_upper_bounds_and_original_identity_controls() {
    foreign_stale_nonce_and_control_ownership();
    crate::experimental::cache::architecture_frozen_controls();
    let bytes = fixture(0, &[0, 0x0b], 100);
    for budget in [
        SwiftRunBudget { active_pins: 129, ..SwiftRunBudget::default() },
        SwiftRunBudget { frames: 129, ..SwiftRunBudget::default() },
    ] {
        let proof = validate_swift_reactor(&bytes, SwiftValidationBudget::default(), &Cancellation::default()).unwrap();
        assert!(RuntimeControl::adopt(proof, budget, Instant::now(), Cancellation::default()).is_err());
    }
    println!("FRAMEPIN above128_rejected=true original_nonce_owner_exhaustion_controls=true");
}
