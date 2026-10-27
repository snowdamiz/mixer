
impl AccountedWasi {
    pub(crate) fn snapshot_pair_v1(&self,control:&RuntimeControl)->Result<usize,crate::experimental_swift_reactor::control::SnapshotAdmissionErrorV1>{
        use crate::experimental_swift_reactor::control::SnapshotAdmissionErrorV1 as E;
        use crate::experimental_swift_reactor::control::SwiftReservationCategory as C;
        let header=accounted_header_bytes().ok_or(E::Arithmetic)?;
        control.snapshot_ticket_identity_v1(self.header.as_ref().ok_or(E::Layout)?)?;
        for ticket in &self.buffers {control.snapshot_ticket_identity_v1(ticket.as_ref().ok_or(E::Layout)?)?;}
        control.snapshot_ticket_v1(self.header.as_ref().ok_or(E::Layout)?,C::Wasi,header)?;
        let capacities=[self.context.scratch.capacity(),self.context.rollback.capacity(),self.context.stdout.capacity(),self.context.stderr.capacity()];
        let mut total=header;
        for (ticket,bytes) in self.buffers.iter().zip(capacities) {
            control.snapshot_ticket_v1(ticket.as_ref().ok_or(E::Layout)?,C::Wasi,bytes)?;
            total=total.checked_add(bytes).ok_or(E::Arithmetic)?;
        }
        Ok(total)
    }
}
