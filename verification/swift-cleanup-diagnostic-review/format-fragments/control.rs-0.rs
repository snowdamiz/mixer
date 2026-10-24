impl Placeholder {
    pub(crate) fn remove_live_at_with_wasi(
        &mut self,
        resource: Live,
        amount: usize,
        cursor: Cursor,
        wasi: Option<WasiUsage>,
    ) -> Result<(), SwiftRunFailure> {
        let (usage, _, kind, _) = self.live_parts(resource);
        let Some(next) = usage.current.checked_sub(amount) else {
            self.cleanup_invariant
                .get_or_insert(SwiftCleanupInvariant::LiveUnderflow);
            return Err(self.fail(
                cursor,
                Fault::new(SwiftRunFailureKind::Invariant, "swift_run_live_underflow").limit(
                    kind,
                    amount as u64,
                    usage.current as u64,
                ),
                wasi,
            ));
        };
        self.live_mut(resource).current = next;
        Ok(())
    }
}
