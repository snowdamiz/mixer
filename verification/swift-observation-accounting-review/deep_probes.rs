// Independent probes appended only to the frozen review source.
#[test]
fn review_six_optional_floor_covers_standalone_deep_fault_paths() {
    use crate::experimental_wasi::accounted::AccountedWasi;
    use crate::experimental_wasi::{WasiBudget, WasiGrants};
    assert_eq!(foundation_construction_bytes().unwrap(), 16_504);
    assert_eq!(size_of::<[Option<WasiUsage>; 6]>(), 672);
    for case in 0..3 {
        let budget = SwiftRunBudget { cache_bytes: 0, ..SwiftRunBudget::default() };
        let (mut control, adopted) = adopt(budget);
        let at = cursor(SwiftRunStage::Invocation);
        let mut phase = AccountedWasi::prepare(&mut control, at).unwrap();
        let mut owner = phase.construct(WasiGrants::default(), WasiBudget::default(), Instant::now(), at).unwrap();
        phase.complete().unwrap();
        owner.dispatch(&mut control, WasiFunction::ArgsSizesGet,
            &[crate::Value::I32(0), crate::Value::I32(4)], &mut [0u8; 8], at).unwrap();
        // Retain an actual final observation while destroying the context and
        // its header. The following control fault cannot borrow that envelope.
        let retained = Some(owner.checked_usage(&mut control, at).unwrap());
        owner.cleanup(&mut control).unwrap();
        assert_eq!(control.usage(retained).reservations.wasi.current, 0);
        assert_eq!(control.usage(retained).reservations.construction.current, 16_504);
        if case == 0 {
            let before = control.usage(retained);
            let (failure, stats) = super::super::allocation_tests::measure(|| {
                control.admit_cache_entry_with_wasi(1, at, retained).unwrap_err()
            });
            no_allocations(stats);
            assert_eq!(stats.deallocations, 0);
            assert_eq!(failure.kind, SwiftRunFailureKind::CategoryExhausted);
            assert_eq!(failure.resource, Some(SwiftRunResource::Reservation(SwiftReservationCategory::Cache)));
            assert_eq!(failure.at_failure.wasi, retained);
            assert_eq!(failure.at_failure.reservations, before.reservations);
            control.drop_proof_with_wasi(adopted, retained).unwrap();
            let after = control.finish_owned_cleanup(retained);
            assert_empty(after);
        } else {
            // Test-only damaged ledger scalars reach the first or second
            // proof-ticket refund invariant; proof/ticket authority is genuine.
            let category = if case == 1 { SwiftReservationCategory::RetainedSource }
                else { SwiftReservationCategory::RetainedMetadata };
            control.reservations.category_mut(category).current -= 1;
            let (failure, stats) = super::super::allocation_tests::measure(|| {
                control.drop_proof_with_wasi(adopted, retained).unwrap_err()
            });
            no_allocations(stats);
            assert!(stats.deallocations > 0);
            assert_eq!(failure.kind, SwiftRunFailureKind::Invariant);
            assert_eq!(failure.code, "swift_run_release_underflow");
            assert_eq!(failure.at_failure.wasi, retained);
            assert_eq!(failure.at_failure.reservations.wasi.current, 0);
            assert_eq!(control.instruction_with_wasi(at, None).unwrap_err(), failure);
            assert_eq!(control.record_cleanup(retained).unwrap().at_failure, failure.at_failure);
            let after = control.finish_owned_cleanup(retained);
            assert!(after.reservations.combined.current > 0);
            assert_eq!(after.reservations.live_tickets, 1);
            assert_eq!(after.cleanup_invariant, Some(SwiftCleanupInvariant::ReservationUnderflow));
            assert_eq!(after.wasi, retained);
        }
    }
}
