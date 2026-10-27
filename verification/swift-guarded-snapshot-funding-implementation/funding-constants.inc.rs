// Exact logical source-place recipe bound to the separately frozen owner
// correction. Every addition is const-evaluated; no runtime helper, local,
// iterable, allocation or second foundation is introduced by this recipe.
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1),
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
