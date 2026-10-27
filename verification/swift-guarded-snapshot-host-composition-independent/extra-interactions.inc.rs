
#[test]
fn independent_composition_explicit_retirement_after_product_success() {
    use super::super::cache::composition_test_account_cycle_v1;
    use super::super::cache::phase_retention_test_complete_v1 as complete;
    composition_test_account_cycle_v1(|observe| {
        let (mut control, adopted) = combined_source_selected_core_v1();
        assert_eq!(observe(), (17, 29, 29));
        let retained = control.snapshot_commit_storage_v1(430_175).unwrap();
        assert_eq!(complete(&mut control, retained, None, true), Ok(()));
        let usage = clean(control, adopted);
        assert_eq!(usage.execution_work, 451_814_442);
        assert_eq!(usage.reservations.construction.current, 1_899_541);
        assert_eq!(usage.cleanup_invariant, Some(SwiftCleanupInvariant::ConstructionBound));
        assert_eq!(observe(), (17, 29, 29));
    }, false);
}

#[test]
fn independent_composition_storage_refusal_keeps_host_prepayment_until_retirement() {
    use super::super::cache::composition_test_account_cycle_v1;
    use super::super::cache::phase_retention_test_complete_v1 as complete;
    composition_test_account_cycle_v1(|observe| {
        let (mut control, adopted) = combined_source_selected_core_v1();
        let before = control.reservations;
        control.budget.combined_bytes = before.combined.current + 430_175 - 1;
        assert_eq!(control.snapshot_commit_storage_v1(430_175).unwrap_err(),
            SnapshotAdmissionErrorV1::Storage {
                current: before.combined.current,
                additional: 430_175,
                limit: before.combined.current + 430_175 - 1,
            });
        assert_eq!(control.reservations, before);
        assert_eq!(observe(), (17, 29, 29));
        assert_eq!(complete(&mut control, 0, None, false), Ok(()));
        let usage = clean(control, adopted);
        assert_eq!(usage.execution_work, 451_814_442);
        assert_eq!(usage.reservations.construction.current, 1_469_366);
        assert_eq!(usage.cleanup_invariant, Some(SwiftCleanupInvariant::ConstructionBound));
        assert_eq!(observe(), (17, 29, 29));
    }, false);
}
