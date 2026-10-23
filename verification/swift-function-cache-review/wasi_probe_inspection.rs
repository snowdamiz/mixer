// Move the actual ticket intact; no authority is forged.
impl AccountedWasi {
    pub(crate) fn review_take_header(&mut self) -> ReservationTicket {
        self.header.take().unwrap()
    }
    pub(crate) fn review_restore_header(&mut self, ticket: ReservationTicket) {
        assert!(self.header.is_none());
        self.header = Some(ticket);
    }
}
