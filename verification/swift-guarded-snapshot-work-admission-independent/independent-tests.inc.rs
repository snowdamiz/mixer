
// Independent synthetic private-policy fixture: actual ordinary in-memory
// parser/validator proof; no authentic selected carrier/loader route executes.
const IA_FIXED: u64 = 451_814_442;
fn ia_selected(budget: SwiftRunBudget, token: Cancellation)
    -> Result<(RuntimeControl, AdoptedProof), SnapshotPreScopeFailureV1> {
    RuntimeControl::adopt_body_core_v1::<SnapshotAdoptionV1>(
        AdoptionBodyV1::ordinary(proof()), budget, Instant::now(), token)
}
fn ia_refusal(budget: SwiftRunBudget, token: Cancellation) -> SnapshotPreScopeFailureV1 {
    match ia_selected(budget, token) {
        Err(value) => value,
        Ok((control, adopted)) => { clean(control, adopted); panic!("expected refusal") }
    }
}
fn ia_unpaid(failure: &SnapshotPreScopeFailureV1) {
    assert!(failure.retirement.is_ok());
    for usage in [failure.primary.at_failure, failure.primary.after_cleanup.unwrap()] {
        assert_eq!(usage.execution_work, 0);
        assert_eq!(usage.cache_work, 0);
        assert_eq!(usage.reservations.combined.current, 0);
        assert_eq!(usage.reservations.combined.peak, 0);
        assert_eq!(usage.reservations.live_tickets, 0);
        assert_eq!(usage.reservations.peak_tickets, 0);
    }
}
#[test]
fn ia_work_refusal_minus_one_zero_and_midpoint_is_atomic() {
    for limit in [0, 1, IA_FIXED / 2, IA_FIXED - 1] {
        let failure = ia_refusal(SwiftRunBudget { execution_work: limit,
            ..SwiftRunBudget::default() }, Cancellation::default());
        assert_eq!(failure.primary.kind, SwiftRunFailureKind::WorkExhausted);
        assert_eq!(failure.primary.resource, Some(SwiftRunResource::ExecutionWork));
        assert_eq!(failure.primary.code, "swift_run_work");
        assert_eq!(failure.primary.stage, SwiftRunStage::Adoption);
        assert_eq!(failure.primary.attempted, IA_FIXED);
        assert_eq!(failure.primary.limit, limit);
        ia_unpaid(&failure);
    }
}
#[test]
fn ia_work_equality_plus_one_and_ceiling_use_same_counter_once() {
    assert_eq!(SnapshotAdoptionV1::FIXED_EXECUTION_WORK_V1, IA_FIXED);
    for limit in [IA_FIXED, IA_FIXED + 1, 1_000_000_000] {
        let (mut control, adopted) = ia_selected(SwiftRunBudget {
            execution_work: limit, ..SwiftRunBudget::default()
        }, Cancellation::default()).unwrap_or_else(|e| panic!("{:?}", e.primary));
        assert_ne!(control.owner, 0);
        assert_eq!(control.usage(None).reservations.live_tickets, 5);
        assert_eq!(control.usage(None).reservations.construction.current,
            SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.unwrap());
        for _ in 0..3 {
            control.check(Cursor::adoption()).unwrap();
            assert_eq!(control.usage(None).execution_work, IA_FIXED);
        }
        let after = clean(control, adopted);
        assert_eq!(after.execution_work, IA_FIXED);
        // Preserved conservative finalizer cannot infer selected phase storage
        // retirement from this synthetic private-core fixture.
        assert_eq!(after.reservations.combined.current,
            SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.unwrap());
        assert_eq!(after.reservations.live_tickets, 1);
        assert_eq!(after.cleanup_invariant, Some(SwiftCleanupInvariant::ConstructionBound));
    }
}
#[test]
fn ia_work_invalid_budget_wins_over_cancel_deadline_and_work_refusal() {
    let token = Cancellation::default(); token.cancel();
    let failure = ia_refusal(SwiftRunBudget { execution_work: 1_000_000_001,
        deadline_ms: 0, ..SwiftRunBudget::default() }, token);
    assert_eq!(failure.primary.kind, SwiftRunFailureKind::InvalidBudget);
    assert_eq!(failure.primary.code, "swift_run_invalid_budget");
    ia_unpaid(&failure);
}
#[test]
fn ia_work_cancel_wins_over_deadline_and_work_refusal() {
    let token = Cancellation::default(); token.cancel();
    let failure = ia_refusal(SwiftRunBudget { execution_work: 0,
        deadline_ms: 0, ..SwiftRunBudget::default() }, token);
    assert_eq!(failure.primary.kind, SwiftRunFailureKind::Cancelled);
    assert_eq!(failure.primary.code, "swift_run_cancelled");
    ia_unpaid(&failure);
}
#[test]
fn ia_work_deadline_wins_over_work_refusal() {
    let failure = ia_refusal(SwiftRunBudget { execution_work: 0,
        deadline_ms: 0, ..SwiftRunBudget::default() }, Cancellation::default());
    assert_eq!(failure.primary.kind, SwiftRunFailureKind::Deadline);
    assert_eq!(failure.primary.code, "swift_run_deadline");
    ia_unpaid(&failure);
}
#[test]
fn ia_work_refusal_wins_over_source_refusal() {
    let failure = ia_refusal(SwiftRunBudget { execution_work: IA_FIXED - 1,
        source_bytes: 0, ..SwiftRunBudget::default() }, Cancellation::default());
    assert_eq!(failure.primary.kind, SwiftRunFailureKind::WorkExhausted);
    ia_unpaid(&failure);
}
#[test]
fn ia_work_source_refusal_after_exact_successful_charge() {
    let failure = ia_refusal(SwiftRunBudget { execution_work: IA_FIXED,
        source_bytes: 0, ..SwiftRunBudget::default() }, Cancellation::default());
    assert_eq!(failure.primary.kind, SwiftRunFailureKind::Adoption);
    assert_eq!(failure.primary.resource,
        Some(SwiftRunResource::Reservation(SwiftReservationCategory::RetainedSource)));
    assert!(failure.retirement.is_ok());
    for usage in [failure.primary.at_failure, failure.primary.after_cleanup.unwrap()] {
        assert_eq!(usage.execution_work, IA_FIXED);
        assert_eq!(usage.reservations.combined.current, 0);
        assert_eq!(usage.reservations.combined.peak, 0);
        assert_eq!(usage.reservations.live_tickets, 0);
        assert_eq!(usage.reservations.peak_tickets, 0);
    }
}
#[test]
fn ia_work_original_policy_accepts_zero_budget_and_stays_zero() {
    assert_eq!(OriginalAdoptionV1::FIXED_EXECUTION_WORK_V1, 0);
    let (mut control, adopted) = adopt(SwiftRunBudget {
        execution_work: 0, ..SwiftRunBudget::default()
    });
    control.check(Cursor::adoption()).unwrap();
    assert_eq!(control.usage(None).execution_work, 0);
    assert_eq!(clean(control, adopted).execution_work, 0);
}
