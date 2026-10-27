
#[test]
fn host_composition_interaction_explicit_retirement_holds_host_charge_during_product_failure() {
    use super::super::cache::composition_test_account_cycle_v1;
    use super::super::cache::phase_retention_test_complete_v1 as complete;
    composition_test_account_cycle_v1(|observe| {
        let (mut control, adopted) = combined_source_selected_core_v1();
        assert_eq!(observe(), (17, 29, 29));
        let retained = control.snapshot_commit_storage_v1(430_175).unwrap();
        assert_eq!(retained, 1_899_541);
        let before = control.reservations;
        let failure = complete(&mut control, retained + 1, None, true).unwrap_err();
        assert_eq!(failure.code, "swift_run_construction_phase_bound");
        assert_eq!(control.reservations, before);
        assert_eq!(observe(), (17, 29, 29));
        let _ = control.drop_proof(adopted);
        let usage = control.finish_owned_cleanup(None);
        assert_eq!(usage.execution_work, 451_814_442);
        assert_eq!(usage.reservations.construction.current, retained);
        assert_eq!(usage.cleanup_invariant, Some(SwiftCleanupInvariant::ConstructionBound));
        assert_eq!(observe(), (17, 29, 29));
    }, false);
}

#[test]
fn host_composition_interaction_implicit_drop_keeps_host_charge_after_product_complete() {
    use super::super::cache::composition_test_account_cycle_v1;
    use super::super::cache::phase_retention_test_complete_v1 as complete;
    composition_test_account_cycle_v1(|observe| {
        let (mut control, adopted) = combined_source_selected_core_v1();
        let retained = control.snapshot_commit_storage_v1(430_175).unwrap();
        assert_eq!(complete(&mut control, retained, None, true), Ok(()));
        assert_eq!(control.construction.as_ref().unwrap().bytes, 1_899_541);
        combined_source_assert_price_v1(&control);
        assert_eq!(observe(), (17, 29, 29));
        let usage = clean(control, adopted);
        assert_eq!(usage.execution_work, 451_814_442);
        assert_eq!(usage.reservations.construction.current, retained);
        assert_eq!(usage.cleanup_invariant, Some(SwiftCleanupInvariant::ConstructionBound));
        assert_eq!(observe(), (17, 29, 29));
    }, true);
}
