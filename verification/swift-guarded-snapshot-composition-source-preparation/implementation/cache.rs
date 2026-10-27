
// Opaque owner-tree interfaces, no public strategy/callback or parts extraction.
pub(super) use initial_profile_v1::{
    SnapshotOuterV1,SnapshotPrimaryRetirementV1,
    UnverifiedProfileDigestBytesV1 as SnapshotClaimsV1,
};
pub(super) const SNAPSHOT_FOUNDATION_PLACES_V1:usize=initial_profile_v1::SNAPSHOT_FOUNDATION_PLACES_V1;
pub(super) fn construct_snapshot_in_scope_v1(cache:&mut Option<SwiftFunctionCache>,control:&mut RuntimeControl,wasi:Option<&AccountedWasi>,adopted:AdoptedProof,claims:&SnapshotClaimsV1,rows:&mut std::fs::File,snapshot:&mut std::fs::File)->SnapshotOuterV1{
    initial_profile_v1::construct_snapshot_owned_v1(cache,control,wasi,adopted,claims,rows,snapshot)
}
impl SwiftFunctionCache {
    fn snapshot_pair_v1(&self,control:&RuntimeControl,wasi:Option<&AccountedWasi>)
        ->Result<(),super::control::SnapshotAdmissionErrorV1>{
        use super::control::SnapshotAdmissionErrorV1 as E;
        control.snapshot_existing_v1()?;
        control.snapshot_owner_v1(self.owner)?;
        control.snapshot_ticket_identity_v1(self.header.as_ref().ok_or(E::Layout)?)?;
        for ticket in &self.buffers {control.snapshot_ticket_identity_v1(ticket.as_ref().ok_or(E::Layout)?)?;}
        control.snapshot_adopted_pair_v1(&self.adopted)?;
        let header=cache_header_bytes().ok_or(E::Arithmetic)?;
        control.snapshot_ticket_v1(self.header.as_ref().ok_or(E::Layout)?,SwiftReservationCategory::Cache,header)?;
        let layouts=[self.slots.capacity().checked_mul(size_of::<SwiftSlot>()),
            self.pins.capacity().checked_mul(size_of::<PinRecord>()),self.patches.capacity().checked_mul(size_of::<decode::Patch>())];
        let mut total=header;
        for (ticket,bytes) in self.buffers.iter().zip(layouts) {
            let bytes=bytes.ok_or(E::Arithmetic)?;
            control.snapshot_ticket_v1(ticket.as_ref().ok_or(E::Layout)?,SwiftReservationCategory::Cache,bytes)?;
            total=total.checked_add(bytes).ok_or(E::Arithmetic)?;
        }
        // Owner is actual cache identity; no imported usage is attributed yet.
        let (wasi_bytes,wasi_tickets)=match wasi {Some(wasi)=>(wasi.snapshot_pair_v1(control)?,5),None=>(0,0)};
        let usage=self.proof().usage();
        control.snapshot_totals_v1(usage.source_bytes,usage.metadata_reserved,total,wasi_bytes,wasi_tickets)?;
        control.snapshot_observe_stop_v1().map_err(E::Stop)
    }
}
