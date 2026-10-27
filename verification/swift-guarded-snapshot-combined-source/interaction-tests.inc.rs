// New combined-interaction controls; separately hashed test overlay, never source145.
// The selected core uses the existing ordinary in-memory parser/validator proof.
// No authentic loader, cache, scope, construct, guest or writer route is called.
fn combined_source_selected_core_v1() -> (RuntimeControl, AdoptedProof) {
    let budget = SwiftRunBudget {
        execution_work: SNAPSHOT_FIXED_EXECUTION_WORK_V1,
        ..SwiftRunBudget::default()
    };
    match RuntimeControl::adopt_body_core_v1::<SnapshotAdoptionV1>(
        AdoptionBodyV1::ordinary(proof()), budget, Instant::now(), Cancellation::default(),
    ) {
        Ok(value) => value,
        Err(failure) => panic!("unexpected private selected refusal: {:?}", failure.primary),
    }
}

fn combined_source_assert_price_v1(control: &RuntimeControl) {
    assert_eq!(control.execution_work, 451_814_442);
    assert_eq!(control.cache_work, 0);
    assert_eq!(control.instruction_fuel, 0);
    assert_eq!(control.instructions, 0);
    assert_eq!(control.host_calls, 0);
}

#[test]
fn combined_source_interaction_selected_commit_complete_retains_corrected_floor() {
    use super::super::cache::phase_retention_test_complete_v1 as complete;
    let (mut control, adopted) = combined_source_selected_core_v1();
    let before = control.reservations;
    let selected = control.construction.as_ref().unwrap().bytes;
    assert_eq!(selected, 1_469_366);
    assert_eq!(selected + SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1, 1_899_541);
    // Frozen phase-only tests expected 1_898_105. The corrected common floor
    // adds exactly 1_436; this new combined test does not modify those tests.
    assert_eq!(1_899_541 - 1_898_105, 1_436);
    let address = control.construction.as_ref().unwrap() as *const ReservationTicket as usize;
    let retained = control.snapshot_commit_storage_v1(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1).unwrap();
    assert_eq!(retained, 1_899_541);
    assert_eq!(control.reservations.live_tickets, 5);
    assert_eq!(control.reservations.peak_tickets, 5);
    assert_eq!(control.reservations.combined.current, before.combined.current + 430_175);
    assert_eq!(control.reservations.combined.peak, before.combined.peak + 430_175);
    let committed = control.reservations;
    assert_eq!(complete(&mut control, retained, None, true), Ok(()));
    assert_eq!(control.reservations, committed);
    assert_eq!(control.construction.as_ref().unwrap().bytes, retained);
    assert_eq!(control.construction.as_ref().unwrap() as *const ReservationTicket as usize, address);
    combined_source_assert_price_v1(&control);
    let usage = clean(control, adopted);
    assert_eq!(usage.execution_work, 451_814_442);
    assert_eq!(usage.cleanup_invariant, Some(SwiftCleanupInvariant::ConstructionBound));
    assert_eq!(usage.reservations.construction.current, retained);
    assert_eq!(usage.reservations.combined.current, retained);
    assert_eq!(usage.reservations.live_tickets, 1);
}

#[test]
fn combined_source_interaction_prior_peaks_and_wasi_survive_completion() {
    use super::super::cache::phase_retention_test_complete_v1 as complete;
    let (mut control, adopted) = combined_source_selected_core_v1();
    control.reservations.construction.peak += 430_175 + 19;
    control.reservations.combined.peak += 430_175 + 29;
    let peaks = (control.reservations.construction.peak, control.reservations.combined.peak);
    let retained = control.snapshot_commit_storage_v1(430_175).unwrap();
    let wasi = WasiUsage {calls:17, work:23, transfer_bytes:31, ..WasiUsage::default()};
    assert_eq!(complete(&mut control, retained, Some(wasi), true), Ok(()));
    assert_eq!((control.reservations.construction.peak, control.reservations.combined.peak), peaks);
    combined_source_assert_price_v1(&control);
    control.drop_proof_with_wasi(adopted, Some(wasi)).unwrap();
    let usage = control.finish_owned_cleanup(Some(wasi));
    assert_eq!(usage.wasi, Some(wasi));
    assert_eq!(usage.execution_work, 451_814_442);
    assert_eq!(usage.reservations.construction.current, 1_899_541);
    assert_eq!(usage.cleanup_invariant, Some(SwiftCleanupInvariant::ConstructionBound));
}

#[test]
fn combined_source_interaction_storage_refusal_preserves_selected_prepayment() {
    use super::super::cache::phase_retention_test_complete_v1 as complete;
    let (mut control, adopted) = combined_source_selected_core_v1();
    let before = control.reservations;
    control.budget.combined_bytes = before.combined.current + 430_175 - 1;
    let refusal = control.snapshot_commit_storage_v1(430_175).unwrap_err();
    assert_eq!(refusal, SnapshotAdmissionErrorV1::Storage {
        current:before.combined.current, additional:430_175,
        limit:before.combined.current + 430_175 - 1,
    });
    assert_eq!(control.reservations, before);
    assert_eq!(complete(&mut control, 0, None, false), Ok(()));
    assert_eq!(control.reservations, before);
    assert_eq!(control.construction.as_ref().unwrap().bytes, 1_469_366);
    combined_source_assert_price_v1(&control);
    let usage = clean(control, adopted);
    assert_eq!(usage.execution_work, 451_814_442);
    assert_eq!(usage.reservations.construction.current, 1_469_366);
    assert_eq!(usage.cleanup_invariant, Some(SwiftCleanupInvariant::ConstructionBound));
}

#[test]
fn combined_source_interaction_completion_bound_fault_retains_A_and_price() {
    use super::super::cache::phase_retention_test_complete_v1 as complete;
    let (mut control, adopted) = combined_source_selected_core_v1();
    let retained = control.snapshot_commit_storage_v1(430_175).unwrap();
    let before = control.reservations;
    let fault = complete(&mut control, retained + 1, None, true).unwrap_err();
    assert_eq!(fault.code, "swift_run_construction_phase_bound");
    assert_eq!(fault.at_failure.execution_work, 451_814_442);
    assert_eq!(fault.at_failure.cleanup_invariant, Some(SwiftCleanupInvariant::ConstructionBound));
    assert_eq!(control.reservations, before);
    assert_eq!(control.construction.as_ref().unwrap().bytes, 1_899_541);
    combined_source_assert_price_v1(&control);
    // This preserves the normalizer failure. Source/metadata ownership is still
    // retired by the actual private control; no healthy-cleanup claim is made.
    let _retirement = control.drop_proof(adopted);
    let usage = control.finish_owned_cleanup(None);
    assert_eq!(usage.execution_work, 451_814_442);
    assert_eq!(usage.reservations.construction.current, 1_899_541);
    assert_eq!(usage.cleanup_invariant, Some(SwiftCleanupInvariant::ConstructionBound));
}
