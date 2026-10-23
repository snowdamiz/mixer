// Independent reviewer probes; all observations come from the actual context.

#[test]
fn reviewer_checked_usage_missing_header_is_unattributed_and_preserves_storage() {
    let (mut control, proof) = adopt(SwiftRunBudget::default());
    let mut owner = construct(&mut control, grants(), small()).unwrap();
    owner.dispatch(&mut control, WasiFunction::ArgsSizesGet, &[i(0), i(4)], &mut [0; 8], cursor()).unwrap();
    let observed = owner.usage();
    let header = owner.header.take();
    let before = control.usage(Some(observed));
    let (failure, stats) = measure(|| owner.checked_usage(&mut control, cursor()).unwrap_err());
    no_alloc(stats);
    assert_eq!(stats.deallocations, 0);
    assert_eq!(failure.code, "swift_run_wasi_missing_header");
    assert_eq!(failure.at_failure.wasi, None);
    assert_eq!(control.usage(None).reservations, before.reservations);
    assert_eq!(owner.usage(), observed);
    owner.header = header;
    assert_eq!(owner.checked_usage(&mut control, cursor()).unwrap(), observed);
    empty(clean(control, proof, owner));
}

#[test]
fn reviewer_actual_wasi_pairing_succeeds_under_expired_cancelled_terminal_control_without_effects() {
    let (mut control, proof) = adopt(SwiftRunBudget::default());
    let mut owner = construct(&mut control, grants(), small()).unwrap();
    owner.dispatch(&mut control, WasiFunction::ArgsSizesGet, &[i(0), i(4)], &mut [0; 8], cursor()).unwrap();
    let observed = owner.usage();
    control.carry_wasi_deadline(Instant::now(), WasiBudget { deadline_ms: 1, ..WasiBudget::default() }, cursor()).unwrap();
    let failure = control.fail(cursor(), Fault::new(SwiftRunFailureKind::GuestTrap, "reviewer_prior_trap"), Some(observed));
    control.cancellation().cancel();
    std::thread::sleep(Duration::from_millis(2));
    let before = control.usage(Some(observed));
    let ((), stats) = measure(|| {
        for _ in 0..16 { assert_eq!(owner.checked_usage(&mut control, cursor()).unwrap(), observed); }
    });
    no_alloc(stats);
    assert_eq!(stats.deallocations, 0);
    let after = control.usage(Some(observed));
    assert!(after.deadline_overshoot_micros > 0);
    assert_eq!(after.reservations, before.reservations);
    assert_eq!((after.cache_work, after.execution_work, after.host_calls), (before.cache_work, before.execution_work, before.host_calls));
    assert_eq!(owner.usage(), observed);
    assert_eq!(control.check(cursor()).unwrap_err(), failure);
    empty(clean(control, proof, owner));
}
