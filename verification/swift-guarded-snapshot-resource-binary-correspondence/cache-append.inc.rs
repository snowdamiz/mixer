
#[cfg(mixer_bootstrap_one_fixture_v1)]
#[used]
static RESOURCE_BINARY_DROP_SWIFT_SLOTS_V1: fn(Vec<SwiftSlot>) = std::mem::drop::<Vec<SwiftSlot>>;
#[cfg(mixer_bootstrap_one_fixture_v1)]
#[used]
static RESOURCE_BINARY_DROP_SCAN_PLANS_V1: fn(Vec<Option<ScanPlan>>) = std::mem::drop::<Vec<Option<ScanPlan>>>;
#[cfg(mixer_bootstrap_one_fixture_v1)]
#[used]
static RESOURCE_BINARY_DROP_FILE_V1: fn(std::fs::File) = std::mem::drop::<std::fs::File>;
