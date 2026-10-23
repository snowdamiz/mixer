// Test-only ledger corruption, restored before honest owner closure.
impl RuntimeControl {
    pub(crate) fn independent_wasi_current(&mut self, value: usize) -> usize {
        std::mem::replace(&mut self.reservations.wasi.current, value)
    }
}
