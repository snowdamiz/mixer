#[test]
fn full_regression_observe_lifecycle_fixture_work() {
    let mut o = owner_with(
        &state_spec(),
        &[36],
        SwiftRunBudget::default(),
        WasiGrants::default(),
        WasiBudget::default(),
    );
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
    println!(
        "REGRESSION_EMPTY_INIT start={start} initialized={}",
        observed(&o).cache_work
    );
    retire(o);
}
