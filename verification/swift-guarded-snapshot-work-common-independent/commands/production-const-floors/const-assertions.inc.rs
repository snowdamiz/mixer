
// Independent production-only const floor probe; no runtime helper is emitted.
const _: () = {
    assert!(matches!(FOUNDATION_CONSTRUCTION_BYTES, Some(366_312)));
    assert!(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1 == 78_240);
    assert!(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1 == 1_436);
    assert!(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1 == 941_467);
    assert!(matches!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1, Some(445_988)));
    assert!(matches!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1, Some(1_387_455)));
    assert!(matches!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1, Some(1_387_455)));
    assert!(matches!(1_387_455usize.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1), Some(1_817_630)));
    assert!(SNAPSHOT_FIXED_EXECUTION_WORK_V1 == 451_814_442);
};
