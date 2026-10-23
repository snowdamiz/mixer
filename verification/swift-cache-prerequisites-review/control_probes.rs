// Independent reviewer probes; included only in an archived disposable source.

#[test]
fn reviewer_adopted_each_original_ticket_and_accounting_branch_remains_borrowed() {
    for point in 0..6 {
        let (mut control, mut adopted) = adopt(SwiftRunBudget::default());
        let original = control.reservations;
        let source_owner = adopted.source.owner;
        let metadata_owner = adopted.metadata.owner;
        match point {
            0 => adopted.source.owner = 0,
            1 => adopted.metadata.owner = 0,
            2 => control.reservations.retained_source.current = adopted.source.bytes - 1,
            3 => control.reservations.retained_metadata.current = adopted.metadata.bytes - 1,
            4 => control.reservations.live_tickets = 0,
            5 => control.reservations.combined.current = 0,
            _ => unreachable!(),
        }
        let before = control.reservations;
        let (failure, stats) = super::super::allocation_tests::measure(|| {
            control.check_adopted_owner(&adopted, cursor(SwiftRunStage::Cache), None).unwrap_err()
        });
        no_allocations(stats);
        assert_eq!(stats.deallocations, 0);
        assert_eq!(control.reservations, before);
        assert_eq!(failure.code, if point < 2 { "swift_run_reservation_owner" } else { "swift_run_reservation_underflow" });
        assert_eq!((control.cache_work, control.execution_work, control.host_calls), (0, 0, 0));
        adopted.source.owner = source_owner;
        adopted.metadata.owner = metadata_owner;
        control.reservations = original;
        control.check_adopted_owner(&adopted, cursor(SwiftRunStage::Cleanup), None).unwrap();
        assert_empty(clean(control, adopted));
    }
}

#[test]
fn reviewer_identity_is_exact_nonzero_only_and_terminal_borrow_ignores_cancellation() {
    let (mut control, adopted) = adopt(SwiftRunBudget::default());
    let mut ticket = control.admit(SwiftReservationCategory::Cache, 0, cursor(SwiftRunStage::Cache)).unwrap();
    let original_owner = ticket.owner;
    ticket.bytes = usize::MAX;
    ticket.category = SwiftReservationCategory::RetainedMetadata;
    assert!(control.reservation_owner_matches(&ticket));
    ticket.owner = 0;
    assert!(!control.reservation_owner_matches(&ticket));
    let saved_owner = control.owner;
    control.owner = 0;
    assert!(!control.reservation_owner_matches(&ticket));
    control.owner = saved_owner;
    ticket.owner = original_owner;
    ticket.bytes = 0;
    ticket.category = SwiftReservationCategory::Cache;
    let first = control.fail(cursor(SwiftRunStage::Invocation), Fault::new(SwiftRunFailureKind::GuestTrap, "reviewer_first"), None);
    control.cancellation.cancel();
    control.deadline = Instant::now() - Duration::from_secs(1);
    let before = control.reservations;
    let ((), stats) = super::super::allocation_tests::measure(|| {
        assert!(control.reservation_owner_matches(&ticket));
        control.check_adopted_owner(&adopted, cursor(SwiftRunStage::Cleanup), None).unwrap();
        control.check_reservation_owner(&ticket, cursor(SwiftRunStage::Cleanup), None).unwrap();
    });
    no_allocations(stats);
    assert_eq!(stats.deallocations, 0);
    assert_eq!(control.reservations, before);
    assert_eq!(control.check(cursor(SwiftRunStage::Invocation)).unwrap_err(), first);
    control.drop_reserved((), ticket).unwrap();
    assert_empty(clean(control, adopted));
}

#[test]
fn reviewer_observed_construction_cleanup_covers_all_invariant_branches_and_drops_storage() {
    struct DropWitness<'a>(&'a Cell<usize>);
    impl Drop for DropWitness<'_> { fn drop(&mut self) { self.0.set(self.0.get() + 1); } }
    let observation = WasiUsage { calls: 7, work: 13, ..WasiUsage::default() };
    for point in 0..6 {
        let (mut control, adopted) = adopt(SwiftRunBudget::default());
        let floor = foundation_construction_bytes().unwrap();
        control.enlarge_construction(floor + 8, cursor(SwiftRunStage::Cache)).unwrap();
        let original = control.reservations;
        let mut removed = None;
        match point {
            0 => removed = control.construction.take(),
            1 => control.construction.as_mut().unwrap().owner = 0,
            2 => control.construction.as_mut().unwrap().category = SwiftReservationCategory::Cache,
            3 => {},
            4 => control.reservations.construction.current = 0,
            5 => control.reservations.combined.current = 0,
            _ => unreachable!(),
        }
        let before = control.reservations;
        let drops = Cell::new(0);
        let (failure, stats) = super::super::allocation_tests::measure(|| {
            control.end_construction_phase_with_wasi(DropWitness(&drops), if point == 3 { floor + 9 } else { floor }, Some(observation)).unwrap_err()
        });
        no_allocations(stats);
        assert_eq!(drops.get(), 1);
        assert_eq!(control.reservations, before);
        assert_eq!(failure.at_failure.wasi, Some(observation));
        assert_eq!(failure.code, match point {
            0 => "swift_run_missing_construction", 1 | 2 => "swift_run_construction_owner",
            3 => "swift_run_construction_phase_bound", _ => "swift_run_release_underflow",
        });
        if point == 0 { control.construction = removed; }
        control.construction.as_mut().unwrap().owner = control.owner;
        control.construction.as_mut().unwrap().category = SwiftReservationCategory::Construction;
        control.reservations = original;
        control.end_construction_phase_with_wasi((), floor, Some(observation)).unwrap();
        assert_eq!(control.check(cursor(SwiftRunStage::Cache)).unwrap_err(), failure);
        assert_empty(clean(control, adopted));
    }
}

#[test]
fn reviewer_drop_proof_attempts_second_original_refund_after_first_fault_and_drops_actual_storage() {
    let (mut control, mut adopted) = adopt(SwiftRunBudget::default());
    let observation = WasiUsage { calls: 11, ..WasiUsage::default() };
    let before = control.reservations;
    let expected_source = adopted.source.bytes;
    adopted.source.owner = 0; // Impossible through production construction.
    let (failure, stats) = super::super::allocation_tests::measure(|| {
        control.drop_proof_with_wasi(adopted, Some(observation)).unwrap_err()
    });
    no_allocations(stats);
    assert!(stats.deallocations > 0);
    assert!(stats.freed_bytes >= expected_source);
    assert_eq!(failure.code, "swift_run_release_owner");
    assert_eq!(failure.at_failure.reservations, before);
    assert_eq!(failure.at_failure.wasi, Some(observation));
    assert_eq!(control.reservations.retained_source.current, expected_source);
    assert_eq!(control.reservations.retained_metadata.current, 0);
    assert_eq!(control.reservations.live_tickets, before.live_tickets - 1);
    let after = control.finish_owned_cleanup(Some(observation));
    assert_eq!(after.reservations.combined.current, expected_source);
    assert_eq!(after.reservations.live_tickets, 1);
}

#[test]
fn reviewer_old_control_methods_are_exact_none_specializations() {
    fn normalized(mut failure: SwiftRunFailure) -> SwiftRunFailure {
        failure.at_failure.elapsed_micros = 0;
        failure.at_failure.deadline_overshoot_micros = 0;
        failure.at_failure.validation.elapsed_micros = 0;
        failure
    }
    for point in 0..9 {
        let mut failures = [None, None];
        for observed in [false, true] {
            let (mut control, adopted) = adopt(SwiftRunBudget::default());
            let at = cursor(SwiftRunStage::Cache);
            let error = match (point, observed) {
                (0, false) => control.work(Work::Execution, u64::MAX, at),
                (0, true) => control.work_with_wasi(Work::Execution, u64::MAX, at, None),
                (1, false) => control.admit(SwiftReservationCategory::Cache, usize::MAX, at).map(drop),
                (1, true) => control.admit_with_wasi(SwiftReservationCategory::Cache, usize::MAX, at, None).map(drop),
                (2, false) => control.admit_cache_entry(usize::MAX, at).map(drop),
                (2, true) => control.admit_cache_entry_with_wasi(usize::MAX, at, None).map(drop),
                (3, false) => control.enlarge_construction(0, at),
                (3, true) => control.enlarge_construction_with_wasi(0, at, None),
                (4, false) => control.exact_capacity(4, 5, at),
                (4, true) => control.exact_capacity_with_wasi(4, 5, at, None),
                (5, false) => control.add_live(Live::Values, usize::MAX, at),
                (5, true) => control.add_live_with_wasi(Live::Values, usize::MAX, at, None),
                (6, false) => control.remove_live(Live::Controls, 1),
                (6, true) => control.remove_live_with_wasi(Live::Controls, 1, None),
                (7, false) => control.end_construction_phase((), 0),
                (7, true) => control.end_construction_phase_with_wasi((), 0, None),
                (8, false) => { control.cancellation.cancel(); control.work(Work::Cache, 0, at) },
                (8, true) => { control.cancellation.cancel(); control.work_with_wasi(Work::Cache, 0, at, None) },
                _ => unreachable!(),
            }.unwrap_err();
            assert_eq!(error.at_failure.wasi, None);
            failures[usize::from(observed)] = Some(normalized(error));
            assert_empty(clean(control, adopted));
        }
        assert_eq!(failures[0], failures[1], "delegate {point}");
    }
}
