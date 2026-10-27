// Independent synthetic private-policy controls. The ordinary validator proof
// remains ordinary: this fixture grants no selected loader provenance.
fn combined_independent_selected_v1() -> (RuntimeControl, AdoptedProof) {
    let value = RuntimeControl::adopt_body_core_v1::<SnapshotAdoptionV1>(
        AdoptionBodyV1::ordinary(proof()),
        SwiftRunBudget {execution_work:451_814_442, ..SwiftRunBudget::default()},
        Instant::now(), Cancellation::default());
    match value {
        Ok((control, adopted)) => {
            assert!(adopted.selected_provenance().is_none());
            (control, adopted)
        },
        Err(failure) => panic!("synthetic selected policy refused: {:?}", failure.primary),
    }
}

#[test]
fn combined_independent_first_work_failure_is_reservation_atomic() {
    for ceiling in [0, 451_814_441] {
        let result = RuntimeControl::adopt_body_core_v1::<SnapshotAdoptionV1>(
            AdoptionBodyV1::ordinary(proof()),
            SwiftRunBudget {execution_work:ceiling, ..SwiftRunBudget::default()},
            Instant::now(), Cancellation::default());
        let failure = match result {Err(f) => f, Ok(_) => panic!("underfunded success")};
        assert_eq!(failure.primary.stage, SwiftRunStage::Adoption);
        assert_eq!(failure.primary.kind, SwiftRunFailureKind::WorkExhausted);
        assert_eq!(failure.primary.resource, Some(SwiftRunResource::ExecutionWork));
        assert_eq!(failure.primary.attempted, 451_814_442);
        assert_eq!(failure.primary.limit, ceiling);
        assert_eq!(failure.primary.at_failure.execution_work, 0);
        assert_eq!(failure.primary.at_failure.reservations, SwiftReservations::default());
        let cleaned = failure.primary.after_cleanup.unwrap();
        assert_eq!(cleaned.execution_work, 0);
        assert_eq!(cleaned.reservations, SwiftReservations::default());
        assert_eq!(cleaned.cleanup_invariant, None);
        assert!(failure.retirement.is_ok());
        println!("witness first-work ceiling={} attempted={} work=0 live=0 peak=0", ceiling, failure.primary.attempted);
    }
}

#[test]
fn combined_independent_existing_checks_precede_work_comparison() {
    for scenario in 0..3 {
        let mut budget = SwiftRunBudget {execution_work:0, ..SwiftRunBudget::default()};
        let token = Cancellation::default();
        let started;
        let expected;
        if scenario == 0 {
            budget.source_bytes += 1;
            started = Instant::now();
            expected = SwiftRunFailureKind::InvalidBudget;
        } else if scenario == 1 {
            token.cancel();
            started = Instant::now();
            expected = SwiftRunFailureKind::Cancelled;
        } else {
            budget.deadline_ms = 1;
            started = Instant::now() - Duration::from_millis(10);
            expected = SwiftRunFailureKind::Deadline;
        }
        let result = RuntimeControl::adopt_body_core_v1::<SnapshotAdoptionV1>(
            AdoptionBodyV1::ordinary(proof()), budget, started, token);
        let failure = match result {Err(f) => f, Ok(_) => panic!("unhealthy success")};
        assert_eq!(failure.primary.kind, expected);
        assert_eq!(failure.primary.at_failure.execution_work, 0);
        assert_eq!(failure.primary.at_failure.reservations, SwiftReservations::default());
        assert_eq!(failure.primary.after_cleanup.unwrap().reservations, SwiftReservations::default());
        assert!(failure.retirement.is_ok());
    }
}

#[test]
fn combined_independent_actual_commit_complete_holds_ticket_and_counter() {
    use super::super::cache::phase_retention_test_complete_v1 as complete;
    let (mut control, adopted) = combined_independent_selected_v1();
    assert_eq!(control.execution_work, 451_814_442);
    assert_eq!(control.construction.as_ref().unwrap().bytes, 1_469_366);
    let ticket = control.construction.as_ref().unwrap();
    let owner = ticket.owner;
    let address = ticket as *const ReservationTicket;
    assert_eq!(ticket.category, SwiftReservationCategory::Construction);
    let before = control.reservations;
    let retained = control.snapshot_commit_storage_v1(430_175).unwrap();
    assert_eq!(retained, 1_899_541);
    assert_eq!(retained - 1_898_105, 1_436);
    assert_eq!(control.reservations.live_tickets, before.live_tickets);
    assert_eq!(control.reservations.peak_tickets, before.peak_tickets);
    assert_eq!(control.reservations.combined.current - before.combined.current, 430_175);
    let committed = control.reservations;
    assert_eq!(complete(&mut control, retained, None, true), Ok(()));
    assert_eq!(control.reservations, committed);
    let ticket = control.construction.as_ref().unwrap();
    assert_eq!(ticket as *const ReservationTicket, address);
    assert_eq!(ticket.owner, owner);
    assert_eq!(ticket.category, SwiftReservationCategory::Construction);
    assert_eq!(ticket.bytes, retained);
    assert_eq!(control.execution_work, 451_814_442);
    assert_eq!((control.cache_work, control.instructions, control.instruction_fuel, control.host_calls), (0,0,0,0));
    println!("witness admitted=1469366 A=430175 retained={} work={} live={} same_ticket=true provenance=ordinary-synthetic", retained, control.execution_work, control.reservations.live_tickets);
    let usage = clean(control, adopted);
    assert_eq!(usage.cleanup_invariant, Some(SwiftCleanupInvariant::ConstructionBound));
    assert_eq!(usage.reservations.construction.current, retained);
    assert_eq!(usage.reservations.live_tickets, 1);
    assert_eq!(usage.execution_work, 451_814_442);
}

#[test]
fn combined_independent_atomic_A_refusal_keeps_prepayment_and_bound() {
    use super::super::cache::phase_retention_test_complete_v1 as complete;
    let (mut control, adopted) = combined_independent_selected_v1();
    let before = control.reservations;
    let owner = control.construction.as_ref().unwrap().owner;
    let address = control.construction.as_ref().unwrap() as *const ReservationTicket;
    control.budget.combined_bytes = before.combined.current + 430_174;
    assert_eq!(control.snapshot_commit_storage_v1(430_175), Err(SnapshotAdmissionErrorV1::Storage {
        current:before.combined.current, additional:430_175, limit:before.combined.current + 430_174,
    }));
    assert_eq!(control.reservations, before);
    assert_eq!(control.execution_work, 451_814_442);
    assert_eq!(complete(&mut control, 0, None, false), Ok(()));
    assert_eq!(control.reservations, before);
    let ticket = control.construction.as_ref().unwrap();
    assert_eq!(ticket as *const ReservationTicket, address);
    assert_eq!(ticket.owner, owner);
    assert_eq!(ticket.bytes, 1_469_366);
    let usage = clean(control, adopted);
    assert_eq!(usage.execution_work, 451_814_442);
    assert_eq!(usage.reservations.construction.current, 1_469_366);
    assert_eq!(usage.cleanup_invariant, Some(SwiftCleanupInvariant::ConstructionBound));
}
