
// Policy-neutral extraction of the reviewed pin bookkeeping. These are actual
// owner tests; the pure model is supporting evidence, never their replacement.
fn pin_bitmap_assert_actual(cache: &SwiftFunctionCache) {
    let records = inspection::dense_pin_records(cache);
    let expected = records.iter().enumerate().fold(0u64, |bits, (slot, record)| {
        bits | if record.0 == 0 { 1u64 << slot } else { 0 }
    });
    assert_eq!(inspection::dense_pin_mask(cache), expected);
    assert_eq!(records.iter().filter(|record| record.0 != 0).count(), cache.usage().active_pins);
}

#[test]
fn pin_bitmap_integration_masks_and_unchanged_policy() {
    for len in 0..=64 {
        let expected = (0..len).fold(0u64, |mask, bit| mask | (1u64 << bit));
        assert_eq!(inspection::dense_allowed_mask(len), expected);
    }
    for len in [65, 128, usize::MAX] {
        assert_eq!(inspection::dense_allowed_mask(len), 0);
    }
    let b = SwiftRunBudget::default();
    assert_eq!((b.cache_entries, b.active_pins, b.frames), (64, 64, 64));
    assert_eq!((b.cache_work, b.instruction_fuel, b.execution_work, b.deadline_ms),
        (64_000_000, 100_000_000, 1_000_000_000, 30_000));
    assert_eq!((b.cache_bytes, b.cache_entry_bytes, b.combined_bytes), (16 << 20, 8 << 20, 256 << 20));
    assert_eq!(MAX_RESERVATION_TICKETS, 86);
    let bytes = fixture(0, &[0, 0x0b], 100);
    for wider in [
        SwiftRunBudget { active_pins: 65, ..b },
        SwiftRunBudget { frames: 65, ..b },
        SwiftRunBudget { cache_entries: 512, ..b },
        SwiftRunBudget { cache_work: 4_000_000_000, ..b },
        SwiftRunBudget { instruction_fuel: 4_000_000_000, ..b },
        SwiftRunBudget { execution_work: 16_000_000_000, ..b },
        SwiftRunBudget { deadline_ms: 1_200_000, ..b },
    ] {
        let failure = RuntimeControl::adopt(proof(&bytes), wider, Instant::now(), Cancellation::default())
            .err().expect("experimental completion limits must remain inadmissible");
        assert_eq!(failure.kind, SwiftRunFailureKind::InvalidBudget);
    }
}

#[test]
fn pin_bitmap_integration_every_narrow_capacity_and_last_bit() {
    hooks(Hooks::default());
    let bytes = fixture(0, &[0, 0x0b], 100);
    for count in 0..=64 {
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget { active_pins: count, ..SwiftRunBudget::default() });
        let mut pins = Vec::with_capacity(count);
        for expected in 0..count {
            let p = pin(&mut cache, &mut c, 34, None).unwrap();
            assert_eq!(inspection::elision_pin_parts(&p)[0], expected as u64);
            pins.push(p);
            pin_bitmap_assert_actual(&cache);
        }
        let records = inspection::dense_pin_records(&cache);
        let before = cache.usage();
        let (failure, allocations) = measure(|| pin(&mut cache, &mut c, 34, None).unwrap_err());
        assert_eq!(failure.code, "pin_slots_exhausted");
        assert_eq!(allocations.attempts, 0);
        assert_eq!(inspection::dense_pin_records(&cache), records);
        assert_eq!(cache.usage(), before);
        let work = c.usage(None).cache_work;
        for p in pins.into_iter().rev() {
            cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
            pin_bitmap_assert_actual(&cache);
        }
        assert_eq!(c.usage(None).cache_work, work);
        finish(cache, c);
    }
}

#[test]
fn pin_bitmap_integration_hole_reuse_and_constant_selection_work() {
    hooks(Hooks::default());
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let warm = pin(&mut cache, &mut c, 34, None).unwrap();
    cache.release(warm, &mut c, None).map_err(|e| e.failure).unwrap();
    let mut pins = Vec::with_capacity(64);
    for expected in 0..64 {
        let before = c.usage(None).cache_work;
        let (p, allocations) = measure(|| pin(&mut cache, &mut c, 34, None).unwrap());
        assert_eq!(allocations.attempts, 0);
        assert_eq!(c.usage(None).cache_work - before, 12);
        assert_eq!(inspection::elision_pin_parts(&p)[0], expected);
        pins.push(Some(p));
    }
    for slot in [63, 1, 32, 0] {
        cache.release(pins[slot].take().unwrap(), &mut c, None).map_err(|e| e.failure).unwrap();
    }
    for slot in [0, 1, 32, 63] {
        let p = pin(&mut cache, &mut c, 34, None).unwrap();
        assert_eq!(inspection::elision_pin_parts(&p)[0], slot as u64);
        pins[slot] = Some(p);
        pin_bitmap_assert_actual(&cache);
    }
    for p in pins.into_iter().flatten() {
        cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
    }
    finish(cache, c);
}

#[test]
fn pin_bitmap_integration_corruption_preserves_records_and_token() {
    hooks(Hooks::default());
    let bytes = fixture(0, &[0, 0x0b], 100);
    for occupied in [false, true] {
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget { active_pins: 8, ..SwiftRunBudget::default() });
        let p = pin(&mut cache, &mut c, 34, None).unwrap();
        let valid = inspection::dense_pin_mask(&cache);
        let corrupt = if occupied { valid ^ 1 ^ 2 } else { valid | (1 << 63) };
        inspection::dense_set_pin_mask(&mut cache, corrupt);
        let records = inspection::dense_pin_records(&cache);
        let before = cache.usage();
        let failure = pin(&mut cache, &mut c, 34, None).unwrap_err();
        assert_eq!(failure.code, if occupied { "swift_dense_pin_occupied" } else { "swift_dense_pin_mask" });
        assert_eq!(inspection::dense_pin_records(&cache), records);
        assert_eq!(inspection::dense_pin_mask(&cache), corrupt);
        assert_eq!(cache.usage(), before);
        inspection::dense_set_pin_mask(&mut cache, valid);
        cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
        finish(cache, c);
    }
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let p = pin(&mut cache, &mut c, 34, None).unwrap();
    let valid = inspection::dense_pin_mask(&cache);
    inspection::dense_set_pin_mask(&mut cache, valid | 1);
    let records = inspection::dense_pin_records(&cache);
    let work = c.usage(None).cache_work;
    let rejected = cache.release(p, &mut c, None).err().unwrap();
    assert_eq!(rejected.failure.code, "swift_dense_release_mask");
    assert_eq!(inspection::dense_pin_records(&cache), records);
    assert_eq!(c.usage(None).cache_work, work);
    inspection::dense_set_pin_mask(&mut cache, valid);
    cache.release(rejected.into_pin(), &mut c, None).map_err(|e| e.failure).unwrap();
    finish(cache, c);
}

#[test]
fn pin_bitmap_integration_all_failure_prefixes_and_constructor_admission() {
    every_constructor_allocation_ordinal();
    every_work_prefix_and_cancellation_boundary();
    construction_and_operation_phase_boundaries();
    foreign_stale_nonce_and_control_ownership();
}

#[test]
fn pin_bitmap_integration_terminal_cancellation_keeps_release_available() {
    hooks(Hooks::default());
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let p = pin(&mut cache, &mut c, 34, None).unwrap();
    let records = inspection::dense_pin_records(&cache);
    let mask = inspection::dense_pin_mask(&cache);
    c.cancellation().cancel();
    assert!(pin(&mut cache, &mut c, 34, None).is_err());
    assert_eq!(inspection::dense_pin_records(&cache), records);
    assert_eq!(inspection::dense_pin_mask(&cache), mask);
    let work = c.usage(None).cache_work;
    cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
    assert_eq!(c.usage(None).cache_work, work);
    pin_bitmap_assert_actual(&cache);
    finish(cache, c);
}

#[test]
fn pin_bitmap_integration_geometry_and_consuming_cleanup() {
    assert!(inspection::dense_pin_inventory_bytes() > 0);
    permanent_patch_arena_exact_requests();
    plan_reuse_shapes_and_admission();
    plan_reuse_profile_envelopes_without_guest_execution();
}
