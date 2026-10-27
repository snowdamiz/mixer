
// Separate synthetic host controls for the changed ordinary common floor.
#[test]
fn work_common_correction_host_exact_actual_unit_floors() {
    assert_eq!(FOUNDATION_CONSTRUCTION_BYTES, Some(366_896));
    assert_eq!(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1, 78_240);
    assert_eq!(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1, 1_436);
    assert_eq!(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1, 941_467);
    assert_eq!(foundation_construction_bytes(), Some(446_572));
    assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1, Some(1_388_039));
    assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1, Some(1_469_366));
    assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.unwrap()
        .checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1), Some(1_899_541));
    println!("actual unit F0=366896 common=446572 selected=1388039 selected_with_H=1469366 admitted_with_H=1899541");
}

#[test]
fn work_common_correction_host_ordinary_changed_floor_boundary() {
    let required = foundation_construction_bytes().unwrap();
    for headroom in [0usize, 1_435, 1_436, 1_437] {
        let sealed = proof();
        let validation = sealed.usage();
        let before = validation.source_bytes + validation.metadata_reserved
            + size_of::<RuntimeControl>() + Cancellation::requested_backing_layout().size();
        let limit = before + required - 1_436 + headroom;
        let budget = SwiftRunBudget { combined_bytes: limit, execution_work: 0, ..SwiftRunBudget::default() };
        let result = RuntimeControl::adopt(sealed, budget, Instant::now(), Cancellation::default());
        if headroom < 1_436 {
            let failure = result.err().expect("new ordinary common bytes must be admitted");
            assert_eq!(failure.kind, SwiftRunFailureKind::CombinedExhausted);
            assert_eq!(failure.resource, Some(SwiftRunResource::Combined));
            assert_eq!(failure.attempted as usize, before + required);
            assert_eq!(failure.limit as usize, limit);
            assert_eq!(failure.at_failure.reservations.construction.current, 0);
            assert_eq!(failure.at_failure.execution_work, 0);
            assert_empty(failure.after_cleanup.unwrap());
        } else {
            let (control, adopted) = result.ok().expect("equality and +1 must admit");
            assert_eq!(control.usage(None).reservations.construction.current, required);
            assert_eq!(control.usage(None).reservations.combined.current, before + required);
            assert_eq!(clean(control, adopted).execution_work, 0);
        }
    }
    println!("ordinary common delta1436 boundary old/required-1/equality/+1 passed; execution_work remains0");
}
