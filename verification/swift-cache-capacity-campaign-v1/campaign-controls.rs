// Isolated campaign controls appended to the original cache_tests module.
// These actual-cache tests execute no guest instructions.
#[test]
fn campaign_retention_churn_and_pin_bound() {
    hooks(Hooks::default());
    let n = SwiftRunBudget::default().cache_entries;
    let bytes = fixture(0, &[0, 0x0b], n + 40);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    assert_eq!(SwiftRunBudget::default().active_pins, 64);
    for _ in 0..2 {
        for f in 34..34 + n as u32 {
            let p = pin(&mut cache, &mut c, f, None).unwrap();
            assert_eq!(cache.view(&p, &mut c, None).unwrap().function, f);
            cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
        }
    }
    assert_eq!(cache.usage().decodes, n as u64);
    assert_eq!(cache.usage().hits, n as u64);
    assert_eq!(cache.usage().evictions, 0);
    assert_eq!(c.usage(None).live.cache_entries.current, n);
    resident_assert_index(&cache);
    let p = pin(&mut cache, &mut c, 34 + n as u32, None).unwrap();
    cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
    assert_eq!(cache.usage().evictions, 1);
    resident_assert_index(&cache);
    // A larger resident table must not create a 65th active pin.
    let mut pins = Vec::new();
    for _ in 0..64 { pins.push(pin(&mut cache, &mut c, 35, None).unwrap()); }
    let f = pin(&mut cache, &mut c, 35, None).unwrap_err();
    assert_eq!(f.kind, SwiftRunFailureKind::PinLimit);
    assert_eq!(c.usage(None).live.active_pins.current, 64);
    for p in pins { cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap(); }
    println!("CAMPAIGN retention residents={n} decodes={} hits={} evictions={} fixed_bytes={} peak_tickets={}",
        cache.usage().decodes, cache.usage().hits, cache.usage().evictions,
        cache.usage().fixed_reserved, c.usage(None).reservations.peak_tickets);
    finish(cache, c);
}

#[test]
fn campaign_full_chain_cycle_and_high_link() {
    hooks(Hooks::default());
    let n = SwiftRunBudget::default().cache_entries;
    let bucket = |f: u32| (f.wrapping_mul(0x9e37_79b9) >> 25) as usize;
    let functions: Vec<u32> = (34..40_034).filter(|f| bucket(*f) == bucket(34)).take(n).collect();
    assert_eq!(functions.len(), n);
    let bytes = fixture(0, &[0, 0x0b], 40_000);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    for f in &functions {
        let p = pin(&mut cache, &mut c, *f, None).unwrap();
        cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
    }
    resident_assert_index(&cache);
    assert_eq!(inspection::resident_index(&cache)[bucket(34)], n as u16);
    let before = c.usage(None).cache_work;
    let p = pin(&mut cache, &mut c, functions[0], None).unwrap();
    assert_eq!(c.usage(None).cache_work - before, 4 + 4 * n as u64);
    cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
    let head = inspection::resident_index(&cache)[bucket(34)];
    inspection::corrupt_index(&mut cache, 128, head);
    assert_eq!(pin(&mut cache, &mut c, functions[0], None).unwrap_err().code, "swift_cache_index_cycle");
    finish(cache, c);
    hooks(Hooks::default());
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    inspection::corrupt_index(&mut cache, bucket(34), (n + 1) as u16);
    assert_eq!(pin(&mut cache, &mut c, 34, None).unwrap_err().code, "swift_cache_index_slot");
    finish(cache, c);
    println!("CAMPAIGN full_chain={n} high_link={n} cycle_and_invalid_link_fail_closed=true");
}

#[test]
fn campaign_original_failure_atomicity_and_allocation_controls() {
    // Existing controls enumerate each work prefix and cancellation checkpoint
    // in a three-resident replacement, and every constructor allocation.
    resident_index_every_collision_replacement_work_and_cancel_boundary();
    plan_reuse_constructor_all_boundaries();
    plan_reuse_header_lifetime_and_narrow_admission();
}

#[test]
fn campaign_budget_geometry_and_reservations() {
    let b = SwiftRunBudget::default();
    let n = b.cache_entries;
    assert!([64, 128, 256].contains(&n));
    assert!([64_000_000, 128_000_000].contains(&b.cache_work));
    assert_eq!((b.cache_bytes, b.cache_entry_bytes, b.active_pins), (16 << 20, 8 << 20, 64));
    assert_eq!((b.memory_pages, b.combined_bytes), (768, 256 << 20));
    assert_eq!((b.instruction_fuel, b.execution_work, b.deadline_ms), (100_000_000, 1_000_000_000, 30_000));
    assert_eq!(MAX_RESERVATION_TICKETS, n + 22);
    let bytes = fixture(0, &[0, 0x0b], n + 40);
    let (mut c, mut cache) = new(&bytes, b);
    for f in 34..34 + n as u32 {
        let p = pin(&mut cache, &mut c, f, None).unwrap();
        cache.release(p, &mut c, None).map_err(|e| e.failure).unwrap();
    }
    let u = c.usage(None);
    assert!(u.reservations.cache.peak <= b.cache_bytes);
    assert!(u.reservations.combined.peak <= b.combined_bytes);
    assert!(u.reservations.peak_tickets <= MAX_RESERVATION_TICKETS);
    println!("CAMPAIGN geometry residents={n} index_cells={} index_bytes={} cycle_bytes={} plan_bytes={n} tickets={} cache_fixed={} operation_bound={} combined_peak={}",
        128+n, (128+n)*2, n/8, MAX_RESERVATION_TICKETS,
        cache.usage().fixed_reserved, cache_operation_bytes().unwrap(), u.reservations.combined.peak);
    finish(cache, c);
    plan_reuse_profile_envelopes_without_guest_execution();
}
