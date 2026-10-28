#[test]
fn framepin_campaign_resident_boundary_geometry_and_rejection() {
    let budget = SwiftRunBudget::default();
    let n = budget.cache_entries;
    assert!([256, 512].contains(&n));
    assert_eq!(MAX_RESERVATION_TICKETS, n + 22);
    let bytes = fixture(0, &[0, 0x0b], n + 40);
    hooks(Hooks::default());
    let (mut c, mut cache) = new(&bytes, budget);
    for function in 34..34 + n as u32 { plan_reuse_release(&mut cache, &mut c, function); }
    assert_eq!(c.usage(None).live.cache_entries.current, n);
    assert_eq!(inspection::resident_index(&cache)[33 + n], n as u16);
    resident_assert_index(&cache);
    assert_eq!(cache.usage().decodes, n as u64);
    // Above-capacity cell is rejected against the actual selected slot arena.
    inspection::corrupt_index(&mut cache, 34, (n + 1) as u16);
    assert_eq!(pin(&mut cache, &mut c, 34, None).unwrap_err().kind, SwiftRunFailureKind::DecoderMismatch);
    finish(cache, c);
    let proof = validate_swift_reactor(&bytes, SwiftValidationBudget::default(), &Cancellation::default()).unwrap();
    assert!(RuntimeControl::adopt(proof, SwiftRunBudget { cache_entries: n + 1, ..budget }, Instant::now(), Cancellation::default()).is_err());
    println!("CACHEWINDOW capacity residents={n} highest_encoded={n} tickets={} dense_index_bytes=160000 pin_bitmap_bytes=16 above_capacity_rejected=true cleanup_zero=true", n + 22);
}
