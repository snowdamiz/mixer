// PROPOSAL ONLY. Appended to a disposable accepted-source copy for compilation.
// No encoder, output entry, proof entry, RuntimeControl field, or owner mint.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum ProposalSnapshotStopV1 {
    Existing(SwiftRunFailure), Cancelled, Deadline(SwiftDeadlineOrigin),
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum ProposalSnapshotAdmissionErrorV1 {
    Stop(ProposalSnapshotStopV1), Owner, Layout, Arithmetic,
    Work { used:u64, requested:u64, limit:u64 },
    Storage { current:usize, additional:usize, limit:usize },
}
pub(super) struct ProposalSnapshotDebitV1 { pub(super) credits:u64 }
impl RuntimeControl {
    // Actual Cancellation backing read, no clone, no caller clock hook.
    pub(super) fn proposal_observe_snapshot_stop_v1(&self)
        -> Result<(),ProposalSnapshotStopV1> {
        if let Some(failure)=self.first_failure { return Err(ProposalSnapshotStopV1::Existing(failure)); }
        if self.cancellation.is_cancelled() { return Err(ProposalSnapshotStopV1::Cancelled); }
        if Instant::now()>=self.deadline { return Err(ProposalSnapshotStopV1::Deadline(self.deadline_origin)); }
        Ok(())
    }
    pub(super) fn proposal_snapshot_owner_v1(&self, owner:u64)
        -> Result<(),ProposalSnapshotAdmissionErrorV1> {
        if owner==0 || owner!=self.owner { return Err(ProposalSnapshotAdmissionErrorV1::Owner); }
        Ok(())
    }
    pub(crate) fn proposal_snapshot_ticket_v1(&self, ticket:&ReservationTicket)
        -> Result<(),ProposalSnapshotAdmissionErrorV1> {
        self.proposal_snapshot_owner_v1(ticket.owner)?;
        if self.reservations.live_tickets==0
            || self.reservations.category(ticket.category).current<ticket.bytes
            || self.reservations.combined.current<ticket.bytes {
            return Err(ProposalSnapshotAdmissionErrorV1::Layout);
        }
        Ok(())
    }
    pub(super) fn proposal_snapshot_adopted_v1(&self, adopted:&AdoptedProof)
        -> Result<(),ProposalSnapshotAdmissionErrorV1> {
        self.proposal_snapshot_ticket_v1(&adopted.source)?;
        self.proposal_snapshot_ticket_v1(&adopted.metadata)?;
        if !adopted.source.matches_layout(SwiftReservationCategory::RetainedSource,adopted.proof().usage().source_bytes)
            || !adopted.metadata.matches_layout(SwiftReservationCategory::RetainedMetadata,adopted.proof().usage().metadata_reserved) {
            return Err(ProposalSnapshotAdmissionErrorV1::Layout);
        }
        Ok(())
    }
    // Called only by the actual cache bridge after its full immutable pairing.
    // A successful precharge advances ORIGINAL ExecutionWork. No refunds exist.
    pub(super) fn proposal_debit_snapshot_work_v1(&mut self, credits:u64)
        -> Result<ProposalSnapshotDebitV1,ProposalSnapshotAdmissionErrorV1> {
        self.proposal_observe_snapshot_stop_v1().map_err(ProposalSnapshotAdmissionErrorV1::Stop)?;
        let used=self.execution_work;
        let limit=self.budget.execution_work;
        let next=used.checked_add(credits).filter(|next|*next<=limit)
            .ok_or(ProposalSnapshotAdmissionErrorV1::Work { used,requested:credits,limit })?;
        self.execution_work=next;
        Ok(ProposalSnapshotDebitV1 {credits})
    }
}
