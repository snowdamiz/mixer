
// Compile-only assertion overlay; excluded from the production source manifest.
const _: () = {
    let f0 = match FOUNDATION_CONSTRUCTION_BYTES {Some(n)=>n,None=>panic!("F0 overflow")};
    let common = match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {Some(n)=>n,None=>panic!("common overflow")};
    let selected = match SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1 {Some(n)=>n,None=>panic!("selected overflow")};
    let admitted = match selected.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1) {Some(n)=>n,None=>panic!("admitted overflow")};
    assert!(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1 == 78_240);
    assert!(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1 == 1_436);
    assert!(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1 == 941_467);
    assert!(SNAPSHOT_FIXED_EXECUTION_WORK_V1 == 451_814_442);
    if cfg!(test) {
        assert!(f0 == 366_896 && common == 446_572 && selected == 1_469_366 && admitted == 1_899_541);
    } else {
        assert!(f0 == 366_312 && common == 445_988 && selected == 1_387_455 && admitted == 1_817_630);
    }
};
