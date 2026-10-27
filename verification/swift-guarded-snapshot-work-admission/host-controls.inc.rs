
// Test-only private policy fixture. Actual in-memory parser/validator execution
// makes an ordinary sealed proof; no authentic loader or snapshot route runs.
fn work_admission_host_selected(
    budget: SwiftRunBudget, started: Instant, cancellation: Cancellation,
) -> Result<(RuntimeControl, AdoptedProof), SnapshotPreScopeFailureV1> {
    RuntimeControl::adopt_body_core_v1::<SnapshotAdoptionV1>(
        AdoptionBodyV1::ordinary(proof()), budget, started, cancellation,
    )
}

fn work_admission_host_error(
    result: Result<(RuntimeControl, AdoptedProof), SnapshotPreScopeFailureV1>,
) -> SnapshotPreScopeFailureV1 {
    match result { Err(failure) => failure, Ok((control, adopted)) => {
        clean(control, adopted);
        panic!("expected private policy refusal")
    }}
}

fn work_admission_host_unpaid(failure: &SnapshotPreScopeFailureV1) {
    assert_eq!(failure.primary.at_failure.execution_work, 0);
    assert_eq!(failure.primary.at_failure.reservations.combined.current, 0);
    assert_eq!(failure.primary.at_failure.reservations.combined.peak, 0);
    assert_eq!(failure.primary.at_failure.reservations.live_tickets, 0);
    assert_eq!(failure.primary.at_failure.reservations.peak_tickets, 0);
    let after = failure.primary.after_cleanup.expect("actual consumed core cleanup");
    assert_eq!(after.execution_work, 0);
    assert_eq!(after.reservations.combined.current, 0);
    assert_eq!(after.reservations.combined.peak, 0);
    assert_eq!(after.reservations.live_tickets, 0);
    assert_eq!(after.reservations.peak_tickets, 0);
    assert!(failure.retirement.is_ok());
}

#[test]
fn work_admission_host_refusal_is_atomic_and_before_any_admission() {
    for limit in [0, SNAPSHOT_FIXED_EXECUTION_WORK_V1 - 1] {
        let budget = SwiftRunBudget {execution_work: limit, ..SwiftRunBudget::default()};
        let failure = work_admission_host_error(work_admission_host_selected(
            budget, Instant::now(), Cancellation::default()));
        assert_eq!(failure.primary.kind, SwiftRunFailureKind::WorkExhausted);
        assert_eq!(failure.primary.resource, Some(SwiftRunResource::ExecutionWork));
        assert_eq!(failure.primary.code, "swift_run_work");
        assert_eq!(failure.primary.attempted, SNAPSHOT_FIXED_EXECUTION_WORK_V1);
        assert_eq!(failure.primary.limit, limit);
        assert_eq!(failure.primary.stage, SwiftRunStage::Adoption);
        work_admission_host_unpaid(&failure);
    }
}

#[test]
fn work_admission_host_equality_and_above_prepay_exactly_once() {
    assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1, 451_814_442);
    for limit in [SNAPSHOT_FIXED_EXECUTION_WORK_V1, SNAPSHOT_FIXED_EXECUTION_WORK_V1 + 1, 1_000_000_000] {
        let budget = SwiftRunBudget {execution_work: limit, ..SwiftRunBudget::default()};
        let (control, adopted) = match work_admission_host_selected(budget, Instant::now(), Cancellation::default()) {
            Ok(value) => value, Err(failure) => panic!("unexpected {:?}", failure.primary),
        };
        let usage = control.usage(None);
        assert_eq!(usage.execution_work, SNAPSHOT_FIXED_EXECUTION_WORK_V1);
        assert_eq!(usage.cache_work, 0);
        assert_eq!(usage.reservations.live_tickets, 5);
        assert_eq!(usage.reservations.construction.current, SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.unwrap());
        assert_eq!(clean(control, adopted).execution_work, SNAPSHOT_FIXED_EXECUTION_WORK_V1);
    }
}

#[test]
fn work_admission_host_invalid_budget_precedence_is_unpaid() {
    let budget = SwiftRunBudget {execution_work: 1_000_000_001, ..SwiftRunBudget::default()};
    let failure = work_admission_host_error(work_admission_host_selected(budget, Instant::now(), Cancellation::default()));
    assert_eq!(failure.primary.kind, SwiftRunFailureKind::InvalidBudget);
    assert_eq!(failure.primary.code, "swift_run_invalid_budget");
    work_admission_host_unpaid(&failure);
}

#[test]
fn work_admission_host_cancelled_precedence_is_unpaid() {
    let token = Cancellation::default(); token.cancel();
    let budget = SwiftRunBudget {execution_work: 0, ..SwiftRunBudget::default()};
    let failure = work_admission_host_error(work_admission_host_selected(budget, Instant::now(), token));
    assert_eq!(failure.primary.kind, SwiftRunFailureKind::Cancelled);
    work_admission_host_unpaid(&failure);
}

#[test]
fn work_admission_host_deadline_precedence_is_unpaid() {
    let budget = SwiftRunBudget {execution_work: 0, deadline_ms: 0, ..SwiftRunBudget::default()};
    let failure = work_admission_host_error(work_admission_host_selected(budget, Instant::now(), Cancellation::default()));
    assert_eq!(failure.primary.kind, SwiftRunFailureKind::Deadline);
    work_admission_host_unpaid(&failure);
}

#[test]
fn work_admission_host_price_is_committed_before_first_source_admission() {
    let budget = SwiftRunBudget {execution_work: SNAPSHOT_FIXED_EXECUTION_WORK_V1, source_bytes: 0, ..SwiftRunBudget::default()};
    let failure = work_admission_host_error(work_admission_host_selected(budget, Instant::now(), Cancellation::default()));
    assert_eq!(failure.primary.kind, SwiftRunFailureKind::Adoption);
    assert_eq!(failure.primary.resource, Some(SwiftRunResource::Reservation(SwiftReservationCategory::RetainedSource)));
    assert_eq!(failure.primary.at_failure.execution_work, SNAPSHOT_FIXED_EXECUTION_WORK_V1);
    assert_eq!(failure.primary.at_failure.reservations.combined.peak, 0);
    assert_eq!(failure.primary.at_failure.reservations.peak_tickets, 0);
    assert!(failure.retirement.is_ok());
    assert_eq!(failure.primary.after_cleanup.unwrap().execution_work, SNAPSHOT_FIXED_EXECUTION_WORK_V1);
}

#[test]
fn work_admission_host_original_policy_keeps_zero_work() {
    assert_eq!(OriginalAdoptionV1::FIXED_EXECUTION_WORK_V1, 0);
    let budget = SwiftRunBudget {execution_work: 0, ..SwiftRunBudget::default()};
    let (control, adopted) = adopt(budget);
    assert_eq!(control.usage(None).execution_work, 0);
    assert_eq!(clean(control, adopted).execution_work, 0);
}
