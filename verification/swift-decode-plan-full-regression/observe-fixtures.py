#!/usr/bin/env python3
"""Add read-only test observations before updating stale inherited assertions."""
from pathlib import Path
H=Path(__file__).resolve().parent
assert (H/'commands/original-swift-debug/receipt.json').is_file()
S=H/'source/src/experimental_swift_reactor'
with (S/'cache_tests.rs').open('a') as f:f.write(r'''

#[test]
fn full_regression_observe_cache_fixture_shapes() {
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
    let (cache, stats) = measure(|| construct(&mut c, a, None).unwrap());
    println!("REGRESSION_CACHE stats={stats:?} header={} fixed={} work={}", cache_header_bytes().unwrap(), c.usage(None).reservations.cache.current, c.usage(None).cache_work);
    assert_eq!(stats.reallocations, 0);
    finish(cache, c);
}
''')
with (S/'execution_tests.rs').open('a') as f:f.write(r'''

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
        let (failure, observed) = super::allocation_tests::measure_extended(Some(ordinal), || construct_failed(pair));
        let after = failure.after_cleanup.unwrap();
        println!("REGRESSION_INTEGRATED_ALLOCATION ordinal={ordinal} stats={observed:?} code={} combined={} tickets={}", failure.code, after.reservations.combined.current, after.reservations.live_tickets);
        assert_eq!(observed.injected_failures, 1);
        assert_eq!(observed.attempts, ordinal + 1);
        assert_eq!(after.reservations.combined.current, 0);
        assert_eq!(after.reservations.live_tickets, 0);
    }
    for ordinal in 0..6 {
        construction_hooks(ConstructionHooks { capacity: Some(ordinal), ..ConstructionHooks::default() });
        let pair = construction_adopt(SwiftRunBudget::default());
        let (failure, observed) = measure(|| construct_failed(pair));
        println!("REGRESSION_INTEGRATED_CAPACITY ordinal={ordinal} stats={observed:?} attempted={} observed={:?}", failure.attempted, failure.observed_capacity);
        assert_eq!(failure.code, "swift_run_unexpected_capacity");
        assert_eq!(failure.after_cleanup.unwrap().reservations.combined.current, 0);
    }
    construction_hooks(ConstructionHooks::default());
    let mut pair = construction_adopt(SwiftRunBudget {frames:0, values:0, controls:0, ..SwiftRunBudget::default()});
    let (owner, stats) = measure(|| construct_owned(&mut pair).unwrap());
    drop(pair);
    println!("REGRESSION_ZERO_STACK stats={stats:?}");
    construction_finish(owner);
    let pair = construction_adopt(SwiftRunBudget {memory_pages:583, ..SwiftRunBudget::default()});
    let (failure, stats) = measure(|| construct_failed(pair));
    println!("REGRESSION_BEFORE_STATE stats={stats:?} code={}", failure.code);
    assert_eq!(failure.code, "swift_execution_memory_minimum");
    assert_eq!(failure.after_cleanup.unwrap().reservations.combined.current, 0);
    construction_hooks(ConstructionHooks {bad_restore:true, ..ConstructionHooks::default()});
    let pair = construction_adopt(SwiftRunBudget::default());
    let (failure, stats) = measure(|| construct_failed(pair));
    println!("REGRESSION_FAILED_RESTORE stats={stats:?} code={}", failure.code);
    assert_eq!(failure.code, "swift_run_construction_phase_bound");
    construction_hooks(ConstructionHooks::default());
}
''')
with (S/'lifecycle_tests.rs').open('a') as f:f.write(r'''

#[test]
fn full_regression_observe_lifecycle_fixture_work() {
    let mut o = owner_with(&state_spec(), &[36], SwiftRunBudget::default(), WasiGrants::default(), WasiBudget::default());
    let start = observed(&o);
    assert_eq!(success(&mut o, Request::Initialize), Reply::Initialized);
    let initialized = observed(&o);
    assert_eq!(success(&mut o, Request::Corpus), Reply::Corpus(2));
    let first = observed(&o);
    assert_eq!(success(&mut o, Request::Corpus), Reply::Corpus(3));
    let second = observed(&o);
    println!("REGRESSION_LIFECYCLE work={:?} instructions={:?} host_calls={:?} entries={:?} tickets={:?}", [start.cache_work, initialized.cache_work, first.cache_work, second.cache_work], [start.instructions, initialized.instructions, first.instructions, second.instructions], [start.host_calls, initialized.host_calls, first.host_calls, second.host_calls], [start.live.cache_entries.current, initialized.live.cache_entries.current, first.live.cache_entries.current, second.live.cache_entries.current], [start.reservations.live_tickets, initialized.reservations.live_tickets, first.reservations.live_tickets, second.reservations.live_tickets]);
    retire(o);
    let mut o = owner(&[]);
    let start = observed(&o).cache_work;
    success(&mut o, Request::Initialize);
    println!("REGRESSION_EMPTY_INIT start={start} initialized={}", observed(&o).cache_work);
    retire(o);
}
''')
print('Added three observation controls; all original fixture assertions remain intact.')
