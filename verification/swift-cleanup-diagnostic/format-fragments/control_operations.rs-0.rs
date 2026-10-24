impl Placeholder {
    fn control_remove(&mut self, resource: Live, amount: usize) -> Result<(), SwiftRunFailure> {
        #[cfg(test)]
        super::tests::diagnostic_before_remove(self.phase.operation.control, resource, 1);
        let result = self.phase.operation.control.remove_live_at_with_wasi(
            resource,
            amount,
            self.phase.operation.cursor,
            Some(self.phase.operation.wasi.usage()),
        );
        if result.is_err() {
            self.cleanup.live_unreconciled = true;
        }
        result
    }
}
