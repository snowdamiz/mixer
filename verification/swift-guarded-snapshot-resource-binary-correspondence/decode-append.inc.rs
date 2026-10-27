
#[cfg(mixer_bootstrap_one_fixture_v1)]
#[used]
static RESOURCE_BINARY_DROP_PATCHES_V1: fn(Vec<Patch>) = std::mem::drop::<Vec<Patch>>;
