#[test]
fn full_regression_observe_integrated_fixture_shapes() {
    construction_hooks(ConstructionHooks::default());
    let mut pair = construction_adopt(SwiftRunBudget::default());
    let (owner, stats) = measure(|| construct_owned(&mut pair).unwrap());
    drop(pair);
    let (usage, cleanup) = measure(|| construction_finish(owner));
    println!("REGRESSION_INTEGRATED stats={stats:?} cleanup={cleanup:?} final_tickets={} final_combined={}", usage.reservations.live_tickets, usage.reservations.combined.current);
    for ordinal in 0..stats.attempts {
        let pair = construction_adopt(SwiftRunBudget::default());
        let (failure, observed) =
            super::allocation_tests::measure_extended(Some(ordinal), || construct_failed(pair));
        let after = failure.after_cleanup.unwrap();
        println!("REGRESSION_INTEGRATED_ALLOCATION ordinal={ordinal} stats={observed:?} code={} combined={} tickets={}", failure.code, after.reservations.combined.current, after.reservations.live_tickets);
        assert_eq!(observed.injected_failures, 1);
        assert_eq!(observed.attempts, ordinal + 1);
        assert_eq!(after.reservations.combined.current, 0);
        assert_eq!(after.reservations.live_tickets, 0);
    }
    for ordinal in 0..6 {
        construction_hooks(ConstructionHooks {
            capacity: Some(ordinal),
            ..ConstructionHooks::default()
        });
        let pair = construction_adopt(SwiftRunBudget::default());
        let (failure, observed) = measure(|| construct_failed(pair));
        println!("REGRESSION_INTEGRATED_CAPACITY ordinal={ordinal} stats={observed:?} attempted={} observed={:?}", failure.attempted, failure.observed_capacity);
        assert_eq!(failure.code, "swift_run_unexpected_capacity");
        assert_eq!(
            failure.after_cleanup.unwrap().reservations.combined.current,
            0
        );
    }
    construction_hooks(ConstructionHooks::default());
    let mut pair = construction_adopt(SwiftRunBudget {
        frames: 0,
        values: 0,
        controls: 0,
        ..SwiftRunBudget::default()
    });
    let (owner, stats) = measure(|| construct_owned(&mut pair).unwrap());
    drop(pair);
    println!("REGRESSION_ZERO_STACK stats={stats:?}");
    construction_finish(owner);
    let pair = construction_adopt(SwiftRunBudget {
        memory_pages: 583,
        ..SwiftRunBudget::default()
    });
    let (failure, stats) = measure(|| construct_failed(pair));
    println!(
        "REGRESSION_BEFORE_STATE stats={stats:?} code={}",
        failure.code
    );
    assert_eq!(failure.code, "swift_execution_memory_minimum");
    assert_eq!(
        failure.after_cleanup.unwrap().reservations.combined.current,
        0
    );
    construction_hooks(ConstructionHooks {
        bad_restore: true,
        ..ConstructionHooks::default()
    });
    let pair = construction_adopt(SwiftRunBudget::default());
    let (failure, stats) = measure(|| construct_failed(pair));
    println!(
        "REGRESSION_FAILED_RESTORE stats={stats:?} code={}",
        failure.code
    );
    assert_eq!(failure.code, "swift_run_construction_phase_bound");
    construction_hooks(ConstructionHooks::default());
}
