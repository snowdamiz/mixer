
    #[cfg(test)]
    pub(super) fn composition_synthetic_cycle_v1(
        action: impl FnOnce(&dyn Fn() -> (u64, u64, u64)), implicit_drop: bool,
    ) {
        host_account_v1::composition_synthetic_cycle_v1(action, implicit_drop);
    }
