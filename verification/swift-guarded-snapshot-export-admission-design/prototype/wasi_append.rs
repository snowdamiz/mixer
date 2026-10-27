// Actual private context reads; preparation compile only, not output production.
impl AccountedWasi {
    pub(crate) fn proposal_snapshot_configuration_v1(&self,control:&RuntimeControl)
        ->Result<(WasiBudget,WasiGrants),crate::experimental_swift_reactor::control::ProposalSnapshotAdmissionErrorV1> {
        use crate::experimental_swift_reactor::control::ProposalSnapshotAdmissionErrorV1 as E;
        let header=self.header.as_ref().ok_or(E::Layout)?;
        control.proposal_snapshot_ticket_v1(header)?;
        for ticket in &self.buffers { control.proposal_snapshot_ticket_v1(ticket.as_ref().ok_or(E::Layout)?)?; }
        Ok((self.context.budget,self.context.grants))
    }
}
