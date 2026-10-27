
// Independent common-floor correction tests. The existing proof() executes the
// actual ordinary in-memory parser/validator; only the private control core is
// then selected synthetically. No authentic selected ingress is exercised.
const CI_COMMON_FIXED: u64 = 451_814_442;
const CI_COMMON_NEW: usize = 446_572;
const CI_COMMON_OLD: usize = CI_COMMON_NEW - 1_436;
const CI_SELECTED: usize = 1_469_366;
fn ci_common_before(sealed: &ValidatedSwiftReactor) -> usize {
    let usage = sealed.usage();
    usage.source_bytes + usage.metadata_reserved + size_of::<RuntimeControl>()
        + Cancellation::requested_backing_layout().size()
}
fn ci_common_selected(sealed: ValidatedSwiftReactor, budget: SwiftRunBudget)
    -> Result<(RuntimeControl, AdoptedProof), SnapshotPreScopeFailureV1> {
    RuntimeControl::adopt_body_core_v1::<SnapshotAdoptionV1>(
        AdoptionBodyV1::ordinary(sealed), budget, Instant::now(), Cancellation::default())
}
#[test]
fn ci_common_actual_unit_floors_and_original_f0() {
    assert_eq!(FOUNDATION_CONSTRUCTION_BYTES, Some(366_896));
    assert_eq!(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1, 78_240);
    assert_eq!(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1, 1_436);
    assert_eq!(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1, 941_467);
    assert_eq!(foundation_construction_bytes(), Some(CI_COMMON_NEW));
    assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1, Some(1_388_039));
    assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1, Some(CI_SELECTED));
    assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.unwrap()
        .checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1), Some(1_899_541));
    assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1, CI_COMMON_FIXED);
    assert_eq!(OriginalAdoptionV1::FIXED_EXECUTION_WORK_V1, 0);
}
#[test]
fn ci_common_original_combined_boundary_changes_by_1436() {
    for floor in [CI_COMMON_OLD, CI_COMMON_NEW - 1, CI_COMMON_NEW, CI_COMMON_NEW + 1] {
        let sealed = proof(); let before = ci_common_before(&sealed);
        let budget = SwiftRunBudget { combined_bytes: before + floor,
            execution_work: 0, ..SwiftRunBudget::default() };
        let result = RuntimeControl::adopt(sealed, budget, Instant::now(), Cancellation::default());
        if floor < CI_COMMON_NEW {
            let failure = result.err().expect("new common floor must refuse");
            assert_eq!(failure.kind, SwiftRunFailureKind::CombinedExhausted);
            assert_eq!(failure.attempted as usize, before + CI_COMMON_NEW);
            assert_eq!(failure.limit as usize, before + floor);
            assert_eq!(failure.at_failure.reservations.combined.current, before);
            assert_eq!(failure.at_failure.reservations.construction.current, 0);
            assert_eq!(failure.at_failure.execution_work, 0);
            assert_empty(failure.after_cleanup.unwrap());
        } else {
            let (control, adopted) = result.unwrap();
            let usage = control.usage(None);
            assert_eq!(usage.execution_work, 0);
            assert_eq!(usage.reservations.construction.current, CI_COMMON_NEW);
            assert_eq!(usage.reservations.combined.current, before + CI_COMMON_NEW);
            assert_eq!(usage.reservations.live_tickets, 5);
            assert_empty(clean(control, adopted));
        }
    }
}
#[test]
fn ci_common_selected_combined_boundary_and_cleanup_are_preserved() {
    for floor in [CI_SELECTED - 1, CI_SELECTED, CI_SELECTED + 1] {
        let sealed = proof(); let before = ci_common_before(&sealed);
        let budget = SwiftRunBudget { combined_bytes: before + floor,
            execution_work: CI_COMMON_FIXED, ..SwiftRunBudget::default() };
        match ci_common_selected(sealed, budget) {
            Err(failure) => {
                assert!(floor < CI_SELECTED);
                assert_eq!(failure.primary.kind, SwiftRunFailureKind::CombinedExhausted);
                assert_eq!(failure.primary.attempted as usize, before + CI_SELECTED);
                assert_eq!(failure.primary.limit as usize, before + floor);
                assert_eq!(failure.primary.at_failure.execution_work, CI_COMMON_FIXED);
                assert_eq!(failure.primary.at_failure.reservations.construction.current, 0);
                assert!(failure.retirement.is_ok());
                assert_empty(failure.primary.after_cleanup.unwrap());
            },
            Ok((mut control, adopted)) => {
                assert!(floor >= CI_SELECTED);
                assert_eq!(control.usage(None).reservations.construction.current, CI_SELECTED);
                assert_eq!(control.usage(None).reservations.combined.current, before + CI_SELECTED);
                for _ in 0..3 { control.check(Cursor::adoption()).unwrap(); }
                assert_eq!(control.usage(None).execution_work, CI_COMMON_FIXED);
                let after = clean(control, adopted);
                assert_eq!(after.execution_work, CI_COMMON_FIXED);
                assert_eq!(after.reservations.construction.current, CI_SELECTED);
                assert_eq!(after.reservations.combined.current, CI_SELECTED);
                assert_eq!(after.reservations.live_tickets, 1);
                assert_eq!(after.cleanup_invariant, Some(SwiftCleanupInvariant::ConstructionBound));
            }
        }
    }
}
#[test]
fn ci_common_work_refusal_still_precedes_construction_refusal() {
    let sealed = proof(); let before = ci_common_before(&sealed);
    let failure = ci_common_selected(sealed, SwiftRunBudget {
        combined_bytes: before + CI_COMMON_OLD, execution_work: CI_COMMON_FIXED - 1,
        ..SwiftRunBudget::default() }).err().expect("work refusal");
    assert_eq!(failure.primary.kind, SwiftRunFailureKind::WorkExhausted);
    assert_eq!(failure.primary.at_failure.execution_work, 0);
    assert_eq!(failure.primary.at_failure.reservations.combined.peak, 0);
    assert_eq!(failure.primary.at_failure.reservations.peak_tickets, 0);
    assert!(failure.retirement.is_ok());
    assert_empty(failure.primary.after_cleanup.unwrap());
}
