fn plan_reuse_cached_deadline_and_precedence() {
    let bytes = fixture(0, &body(1, &[0, 0x0e, 1, 0, 0, 0x0b]), 100);
    for step in [
        CacheStep::Lookup,
        CacheStep::BuildReset,
        CacheStep::Build,
        CacheStep::Publication,
    ] {
        for cancel in [false, true] {
            hooks(Hooks::default());
            let (mut c, mut cache) = plan_reuse_seed(
                &bytes,
                SwiftRunBudget {
                    cache_entries: 1,
                    deadline_ms: 20,
                    ..SwiftRunBudget::default()
                },
            );
            hooks(Hooks {
                pause: Some(step),
                cancel_pause: cancel,
                ..Hooks::default()
            });
            let f = pin(&mut cache, &mut c, 34, None).unwrap_err();
            hooks(Hooks::default());
            assert_eq!(
                f.kind,
                if cancel {
                    SwiftRunFailureKind::Cancelled
                } else {
                    SwiftRunFailureKind::Deadline
                }
            );
            assert_eq!(c.usage(None).live.active_pins.current, 0);
            plan_reuse_primary(f, pin(&mut cache, &mut c, 34, None).unwrap_err());
            finish(cache, c);
        }
    }
    println!("PLAN_CACHED_DEADLINE boundaries=4 precedence_pairs=4 cleanup_zero=true");
}
