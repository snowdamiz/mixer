
#[cfg(all(test, mixer_bootstrap_one_fixture_v1))]
pub(in crate::experimental_swift_reactor) fn composition_test_account_cycle_v1(
    action: impl FnOnce(&dyn Fn() -> (u64, u64, u64)), implicit_drop: bool,
) {
    trusted_local_host_account_entry_v1::composition_synthetic_cycle_v1(action, implicit_drop);
}
