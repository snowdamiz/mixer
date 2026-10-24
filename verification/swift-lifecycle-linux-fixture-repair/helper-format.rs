#[cfg(test)]
impl RuntimeControl {
    /// Expire a healthy prepared fixture without racing its construction time.
    /// Keep its actual origin, budgets, counters and first-failure state intact.
    pub(crate) fn test_expire_deadline(&mut self) -> Instant {
        assert!(self.first_failure.is_none());
        let expired = Instant::now();
        assert!(expired < self.deadline);
        self.deadline = expired;
        expired
    }
}
