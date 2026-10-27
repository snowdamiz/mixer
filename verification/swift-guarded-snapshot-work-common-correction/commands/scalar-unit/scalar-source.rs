// Exact corrected const recipe with separately declared synthetic F0 inputs.
mod recipe_0 {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=None;
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Twenty new shared, non-P-dependent unoptimized source roles total1436
// logical bytes. Charge every role to common C; no old role is credited.
const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {
            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.


pub fn check()->usize {
 let base=FOUNDATION_CONSTRUCTION_BYTES.map(|n|n as u128);
 let expected=|extra:u128|base.and_then(|n|n.checked_add(extra)).filter(|n|*n<=usize::MAX as u128).map(|n|n as usize);
 assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436));
 assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.and_then(|n|n.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1)),
     expected(78_240+1_436+941_467+430_175+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
 5
}
}

mod recipe_1 {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=Some(0);
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Twenty new shared, non-P-dependent unoptimized source roles total1436
// logical bytes. Charge every role to common C; no old role is credited.
const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {
            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.


pub fn check()->usize {
 let base=FOUNDATION_CONSTRUCTION_BYTES.map(|n|n as u128);
 let expected=|extra:u128|base.and_then(|n|n.checked_add(extra)).filter(|n|*n<=usize::MAX as u128).map(|n|n as usize);
 assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436));
 assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.and_then(|n|n.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1)),
     expected(78_240+1_436+941_467+430_175+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
 5
}
}

mod recipe_2 {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=Some(366312);
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Twenty new shared, non-P-dependent unoptimized source roles total1436
// logical bytes. Charge every role to common C; no old role is credited.
const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {
            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.


pub fn check()->usize {
 let base=FOUNDATION_CONSTRUCTION_BYTES.map(|n|n as u128);
 let expected=|extra:u128|base.and_then(|n|n.checked_add(extra)).filter(|n|*n<=usize::MAX as u128).map(|n|n as usize);
 assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436));
 assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.and_then(|n|n.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1)),
     expected(78_240+1_436+941_467+430_175+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
 5
}
}

mod recipe_3 {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=Some(366896);
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Twenty new shared, non-P-dependent unoptimized source roles total1436
// logical bytes. Charge every role to common C; no old role is credited.
const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {
            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.


pub fn check()->usize {
 let base=FOUNDATION_CONSTRUCTION_BYTES.map(|n|n as u128);
 let expected=|extra:u128|base.and_then(|n|n.checked_add(extra)).filter(|n|*n<=usize::MAX as u128).map(|n|n as usize);
 assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436));
 assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.and_then(|n|n.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1)),
     expected(78_240+1_436+941_467+430_175+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
 5
}
}

mod recipe_4 {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=Some(18446744073709473374);
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Twenty new shared, non-P-dependent unoptimized source roles total1436
// logical bytes. Charge every role to common C; no old role is credited.
const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {
            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.


pub fn check()->usize {
 let base=FOUNDATION_CONSTRUCTION_BYTES.map(|n|n as u128);
 let expected=|extra:u128|base.and_then(|n|n.checked_add(extra)).filter(|n|*n<=usize::MAX as u128).map(|n|n as usize);
 assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436));
 assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.and_then(|n|n.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1)),
     expected(78_240+1_436+941_467+430_175+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
 5
}
}

mod recipe_5 {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=Some(18446744073709473375);
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Twenty new shared, non-P-dependent unoptimized source roles total1436
// logical bytes. Charge every role to common C; no old role is credited.
const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {
            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.


pub fn check()->usize {
 let base=FOUNDATION_CONSTRUCTION_BYTES.map(|n|n as u128);
 let expected=|extra:u128|base.and_then(|n|n.checked_add(extra)).filter(|n|*n<=usize::MAX as u128).map(|n|n as usize);
 assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436));
 assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.and_then(|n|n.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1)),
     expected(78_240+1_436+941_467+430_175+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
 5
}
}

mod recipe_6 {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=Some(18446744073709473376);
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Twenty new shared, non-P-dependent unoptimized source roles total1436
// logical bytes. Charge every role to common C; no old role is credited.
const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {
            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.


pub fn check()->usize {
 let base=FOUNDATION_CONSTRUCTION_BYTES.map(|n|n as u128);
 let expected=|extra:u128|base.and_then(|n|n.checked_add(extra)).filter(|n|*n<=usize::MAX as u128).map(|n|n as usize);
 assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436));
 assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.and_then(|n|n.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1)),
     expected(78_240+1_436+941_467+430_175+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
 5
}
}

mod recipe_7 {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=Some(18446744073709471938);
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Twenty new shared, non-P-dependent unoptimized source roles total1436
// logical bytes. Charge every role to common C; no old role is credited.
const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {
            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.


pub fn check()->usize {
 let base=FOUNDATION_CONSTRUCTION_BYTES.map(|n|n as u128);
 let expected=|extra:u128|base.and_then(|n|n.checked_add(extra)).filter(|n|*n<=usize::MAX as u128).map(|n|n as usize);
 assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436));
 assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.and_then(|n|n.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1)),
     expected(78_240+1_436+941_467+430_175+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
 5
}
}

mod recipe_8 {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=Some(18446744073709471939);
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Twenty new shared, non-P-dependent unoptimized source roles total1436
// logical bytes. Charge every role to common C; no old role is credited.
const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {
            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.


pub fn check()->usize {
 let base=FOUNDATION_CONSTRUCTION_BYTES.map(|n|n as u128);
 let expected=|extra:u128|base.and_then(|n|n.checked_add(extra)).filter(|n|*n<=usize::MAX as u128).map(|n|n as usize);
 assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436));
 assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.and_then(|n|n.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1)),
     expected(78_240+1_436+941_467+430_175+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
 5
}
}

mod recipe_9 {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=Some(18446744073709471940);
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Twenty new shared, non-P-dependent unoptimized source roles total1436
// logical bytes. Charge every role to common C; no old role is credited.
const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {
            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.


pub fn check()->usize {
 let base=FOUNDATION_CONSTRUCTION_BYTES.map(|n|n as u128);
 let expected=|extra:u128|base.and_then(|n|n.checked_add(extra)).filter(|n|*n<=usize::MAX as u128).map(|n|n as usize);
 assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436));
 assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.and_then(|n|n.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1)),
     expected(78_240+1_436+941_467+430_175+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
 5
}
}

mod recipe_10 {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=Some(18446744073708530471);
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Twenty new shared, non-P-dependent unoptimized source roles total1436
// logical bytes. Charge every role to common C; no old role is credited.
const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {
            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.


pub fn check()->usize {
 let base=FOUNDATION_CONSTRUCTION_BYTES.map(|n|n as u128);
 let expected=|extra:u128|base.and_then(|n|n.checked_add(extra)).filter(|n|*n<=usize::MAX as u128).map(|n|n as usize);
 assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436));
 assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.and_then(|n|n.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1)),
     expected(78_240+1_436+941_467+430_175+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
 5
}
}

mod recipe_11 {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=Some(18446744073708530472);
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Twenty new shared, non-P-dependent unoptimized source roles total1436
// logical bytes. Charge every role to common C; no old role is credited.
const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {
            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.


pub fn check()->usize {
 let base=FOUNDATION_CONSTRUCTION_BYTES.map(|n|n as u128);
 let expected=|extra:u128|base.and_then(|n|n.checked_add(extra)).filter(|n|*n<=usize::MAX as u128).map(|n|n as usize);
 assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436));
 assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.and_then(|n|n.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1)),
     expected(78_240+1_436+941_467+430_175+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
 5
}
}

mod recipe_12 {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=Some(18446744073708530473);
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Twenty new shared, non-P-dependent unoptimized source roles total1436
// logical bytes. Charge every role to common C; no old role is credited.
const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {
            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.


pub fn check()->usize {
 let base=FOUNDATION_CONSTRUCTION_BYTES.map(|n|n as u128);
 let expected=|extra:u128|base.and_then(|n|n.checked_add(extra)).filter(|n|*n<=usize::MAX as u128).map(|n|n as usize);
 assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436));
 assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.and_then(|n|n.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1)),
     expected(78_240+1_436+941_467+430_175+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
 5
}
}

mod recipe_13 {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=Some(18446744073708449144);
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Twenty new shared, non-P-dependent unoptimized source roles total1436
// logical bytes. Charge every role to common C; no old role is credited.
const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {
            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.


pub fn check()->usize {
 let base=FOUNDATION_CONSTRUCTION_BYTES.map(|n|n as u128);
 let expected=|extra:u128|base.and_then(|n|n.checked_add(extra)).filter(|n|*n<=usize::MAX as u128).map(|n|n as usize);
 assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436));
 assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.and_then(|n|n.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1)),
     expected(78_240+1_436+941_467+430_175+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
 5
}
}

mod recipe_14 {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=Some(18446744073708449145);
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Twenty new shared, non-P-dependent unoptimized source roles total1436
// logical bytes. Charge every role to common C; no old role is credited.
const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {
            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.


pub fn check()->usize {
 let base=FOUNDATION_CONSTRUCTION_BYTES.map(|n|n as u128);
 let expected=|extra:u128|base.and_then(|n|n.checked_add(extra)).filter(|n|*n<=usize::MAX as u128).map(|n|n as usize);
 assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436));
 assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.and_then(|n|n.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1)),
     expected(78_240+1_436+941_467+430_175+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
 5
}
}

mod recipe_15 {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=Some(18446744073708449146);
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Twenty new shared, non-P-dependent unoptimized source roles total1436
// logical bytes. Charge every role to common C; no old role is credited.
const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {
            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.


pub fn check()->usize {
 let base=FOUNDATION_CONSTRUCTION_BYTES.map(|n|n as u128);
 let expected=|extra:u128|base.and_then(|n|n.checked_add(extra)).filter(|n|*n<=usize::MAX as u128).map(|n|n as usize);
 assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436));
 assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.and_then(|n|n.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1)),
     expected(78_240+1_436+941_467+430_175+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
 5
}
}

mod recipe_16 {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=Some(18446744073708100296);
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Twenty new shared, non-P-dependent unoptimized source roles total1436
// logical bytes. Charge every role to common C; no old role is credited.
const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {
            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.


pub fn check()->usize {
 let base=FOUNDATION_CONSTRUCTION_BYTES.map(|n|n as u128);
 let expected=|extra:u128|base.and_then(|n|n.checked_add(extra)).filter(|n|*n<=usize::MAX as u128).map(|n|n as usize);
 assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436));
 assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.and_then(|n|n.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1)),
     expected(78_240+1_436+941_467+430_175+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
 5
}
}

mod recipe_17 {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=Some(18446744073708100297);
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Twenty new shared, non-P-dependent unoptimized source roles total1436
// logical bytes. Charge every role to common C; no old role is credited.
const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {
            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.


pub fn check()->usize {
 let base=FOUNDATION_CONSTRUCTION_BYTES.map(|n|n as u128);
 let expected=|extra:u128|base.and_then(|n|n.checked_add(extra)).filter(|n|*n<=usize::MAX as u128).map(|n|n as usize);
 assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436));
 assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.and_then(|n|n.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1)),
     expected(78_240+1_436+941_467+430_175+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
 5
}
}

mod recipe_18 {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=Some(18446744073708100298);
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Twenty new shared, non-P-dependent unoptimized source roles total1436
// logical bytes. Charge every role to common C; no old role is credited.
const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {
            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.


pub fn check()->usize {
 let base=FOUNDATION_CONSTRUCTION_BYTES.map(|n|n as u128);
 let expected=|extra:u128|base.and_then(|n|n.checked_add(extra)).filter(|n|*n<=usize::MAX as u128).map(|n|n as usize);
 assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436));
 assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,expected(78_240+1_436+941_467+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.and_then(|n|n.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1)),
     expected(78_240+1_436+941_467+430_175+if cfg!(test){81_327}else{0}));
 assert_eq!(SNAPSHOT_FIXED_EXECUTION_WORK_V1,451_814_442);
 5
}
}
fn main(){let mut checks=0usize;
checks+=recipe_0::check();
checks+=recipe_1::check();
checks+=recipe_2::check();
checks+=recipe_3::check();
checks+=recipe_4::check();
checks+=recipe_5::check();
checks+=recipe_6::check();
checks+=recipe_7::check();
checks+=recipe_8::check();
checks+=recipe_9::check();
checks+=recipe_10::check();
checks+=recipe_11::check();
checks+=recipe_12::check();
checks+=recipe_13::check();
checks+=recipe_14::check();
checks+=recipe_15::check();
checks+=recipe_16::check();
checks+=recipe_17::check();
checks+=recipe_18::check();

for bits in [32u32,64] {
 let limit=(1u128<<bits)-1;
 for host in [0u128,81_327] {
  for delta in [78_240u128,78_240+1_436,78_240+1_436+941_467,78_240+1_436+941_467+host,78_240+1_436+941_467+host+430_175] {
   for base in [0u128,366_312,366_896,limit-delta-1,limit-delta,limit-delta+1,limit] {
    let mut actual=Some(base);
    for term in [78_240u128,1_436,941_467,host,430_175] {actual=actual.and_then(|n|n.checked_add(term)).filter(|n|*n<=limit);}
    let wide=base+78_240+1_436+941_467+host+430_175;
    assert_eq!(actual,if wide<=limit{Some(wide)}else{None});checks+=1;
   }
  }
 }
}
assert!(usize::MAX.checked_add(1_436).is_none());checks+=1;
assert!(u64::MAX.checked_add(1_272).is_none());checks+=1;
println!("{} checked common/selected/admitted floor and overflow controls passed; standalone integers; cfg_test={}",checks,cfg!(test));
}
