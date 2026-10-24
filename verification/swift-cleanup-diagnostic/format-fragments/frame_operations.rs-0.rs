impl Placeholder {
    fn remove_live_at(&mut self, resource: Live, amount: usize) -> bool {
        #[cfg(test)]
        tests::diagnostic_before_remove(self.phase.operation.control, resource, 0);
        if self
            .phase
            .operation
            .control
            .remove_live_at_with_wasi(
                resource,
                amount,
                self.phase.operation.cursor,
                Some(self.phase.operation.wasi.usage()),
            )
            .is_err()
        {
            self.cleanup.live_unreconciled = true;
            false
        } else {
            true
        }
    }
}
