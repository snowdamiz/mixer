
// Isolated source preparation. No route in this tree invokes the new ingress.
mod adoption_state_seal_v1 { pub(super) trait Closed {} }
struct OriginalAdoptionV1;
struct SnapshotAdoptionV1;
impl adoption_state_seal_v1::Closed for OriginalAdoptionV1 {}
impl adoption_state_seal_v1::Closed for SnapshotAdoptionV1 {}
trait ClosedAdoptionV1: adoption_state_seal_v1::Closed {
    type Failure;
    type Retirement;
    fn foundation()->Option<usize>;
    fn retire_tickets(control:&mut RuntimeControl,source:Option<ReservationTicket>,metadata:Option<ReservationTicket>)->Self::Retirement;
    fn failure(primary:SwiftRunFailure,retirement:Self::Retirement)->Self::Failure;
}
impl ClosedAdoptionV1 for OriginalAdoptionV1 {
    type Failure=SwiftRunFailure;
    type Retirement=();
    fn foundation()->Option<usize>{foundation_construction_bytes()}
    fn retire_tickets(control:&mut RuntimeControl,source:Option<ReservationTicket>,metadata:Option<ReservationTicket>){
        // Exact Original order/semantics; there is no Selected retirement value.
        if let Some(ticket)=source {let _=control.refund(ticket);}
        if let Some(ticket)=metadata {let _=control.refund(ticket);}
    }
    fn failure(primary:SwiftRunFailure,_:())->SwiftRunFailure{primary}
}
pub(super) struct SnapshotPreScopeFailureV1 {
    pub(super) primary:SwiftRunFailure,
    pub(super) retirement:Result<(),SwiftRunFailure>,
}
impl ClosedAdoptionV1 for SnapshotAdoptionV1 {
    type Failure=SnapshotPreScopeFailureV1;
    type Retirement=Result<(),SwiftRunFailure>;
    fn foundation()->Option<usize>{snapshot_scope_candidate_foundation_v1()}
    fn retire_tickets(control:&mut RuntimeControl,source:Option<ReservationTicket>,metadata:Option<ReservationTicket>)->Self::Retirement{
        let source=match source {Some(ticket)=>control.refund(ticket),None=>Ok(())};
        let metadata=match metadata {Some(ticket)=>control.refund(ticket),None=>Ok(())};
        source.and(metadata) // Both actual refunds occur even when the first fails.
    }
    fn failure(primary:SwiftRunFailure,retirement:Self::Retirement)->Self::Failure{
        SnapshotPreScopeFailureV1 {primary,retirement}
    }
}

use super::cache::{SnapshotClaimsV1,SnapshotOuterV1,SnapshotPrimaryRetirementV1};
use crate::experimental_wasi::accounted::AccountedWasi;
use crate::experimental_wasi::WasiGrants;
use std::fs::File;

/// No control/proof extraction and no parts constructor. Actual slots only.
pub(super) struct SnapshotScopeV1 {
    control:RuntimeControl,
    adopted:Option<AdoptedProof>,
    cache:Option<super::cache::SwiftFunctionCache>,
    wasi:Option<AccountedWasi>,
    wasi_attachment:Option<SnapshotWasiAttachmentV1>,
    base_foundation:usize,
}
pub(super) struct SnapshotRunV1 { scope:SnapshotScopeV1,outer:SnapshotOuterV1 }
pub(super) struct SnapshotScopeFinishV1 {
    pub(super) primary_retirement:SnapshotPrimaryRetirementV1,
    pub(super) cache_retirement:Option<SwiftRunFailure>,
    pub(super) scope_adopted_retirement:Result<(),SwiftRunFailure>,
    pub(super) wasi_attachment:Option<SnapshotWasiAttachmentV1>,
    pub(super) wasi_retirement:Result<(),SwiftRunFailure>,
    pub(super) usage:SwiftRunUsage,
}
pub(super) struct SnapshotWasiAttachmentV1 {
    pub(super) construction:Result<(),SwiftRunFailure>,
    pub(super) completion:Result<(),SwiftRunFailure>,
}
impl RuntimeControl {
    // Only the authentic consuming carrier calls this. Selected provenance is
    // rechecked from the actual opaque body, never from a caller boolean.
    pub(super) fn adopt_snapshot_body_v1(body:super::retained_profile_loader_v1::SelectedSnapshotBodyV1,budget:SwiftRunBudget,started:Instant,cancellation:Cancellation)
        ->Result<SnapshotScopeV1,SnapshotPreScopeFailureV1> {
        let body=body.into_adoption_body_v1();
        let (control,adopted)=Self::adopt_body_core_v1::<SnapshotAdoptionV1>(body,budget,started,cancellation)?;
        let base_foundation=control.construction.as_ref().expect("actual Construction admitted").bytes;
        Ok(SnapshotScopeV1 {control,adopted:Some(adopted),cache:None,wasi:None,wasi_attachment:None,base_foundation})
    }
}
impl SnapshotScopeV1 {
    pub(super) fn attach_wasi_v1(&mut self,grants:WasiGrants,budget:WasiBudget,started:Instant)->&SnapshotWasiAttachmentV1 {
        if self.wasi_attachment.is_some(){return self.wasi_attachment.as_ref().expect("one actual attachment attempt");}
        let result=self.attach_wasi_inner_v1(grants,budget,started);
        self.wasi_attachment=Some(result);
        self.wasi_attachment.as_ref().expect("actual retained attachment result")
    }
    fn attach_wasi_inner_v1(&mut self,grants:WasiGrants,budget:WasiBudget,started:Instant)->SnapshotWasiAttachmentV1 {
        let cursor=Cursor {stage:SwiftRunStage::Initialization,function:None,offset:None};
        if self.wasi.is_some() {
            let failure=self.control.fail(cursor,Fault::new(SwiftRunFailureKind::Invariant,"swift_snapshot_wasi_slot_occupied"),None);
            return SnapshotWasiAttachmentV1 {construction:Err(failure),completion:Ok(())};
        }
        let mut phase=match AccountedWasi::prepare(&mut self.control,cursor) {
            Ok(phase)=>phase,
            Err(failure)=>return SnapshotWasiAttachmentV1 {construction:Err(failure),completion:Ok(())},
        };
        let construction=match phase.construct(grants,budget,started,cursor) {
            Ok(wasi)=>{self.wasi=Some(wasi);Ok(())},Err(failure)=>Err(failure),
        };
        let completion=phase.complete();
        SnapshotWasiAttachmentV1 {construction,completion}
    }
    pub(super) fn construct_v1(mut self,claims:&SnapshotClaimsV1,rows:&mut File,snapshot:&mut File)->SnapshotRunV1 {
        let adopted=self.adopted.take().expect("one-shot actual adopted owner");
        let outer=super::cache::construct_snapshot_in_scope_v1(
            &mut self.cache,&mut self.control,self.wasi.as_ref(),adopted,claims,rows,snapshot);
        SnapshotRunV1 {scope:self,outer}
    }
}
impl SnapshotRunV1 {
    pub(super) fn outer_v1(&self)->&SnapshotOuterV1{&self.outer}
    // Consuming run ties this exact outer to this exact authentic owner.
    pub(super) fn finish_v1(self)->SnapshotScopeFinishV1 {
        let Self {scope,outer}=self;
        let SnapshotScopeV1 {mut control,adopted,mut cache,wasi,wasi_attachment,base_foundation}=scope;
        let observation=match wasi.as_ref(){
            Some(wasi) if wasi.snapshot_pair_v1(&control).is_ok()=>Some(wasi.usage()),_=>None,
        };
        let primary_retirement=outer.retire_v1(&mut control,observation);
        let scope_adopted_retirement=match adopted{Some(adopted)=>control.drop_proof_with_wasi(adopted,observation),None=>Ok(())};
        let mut cache_retirement=None;
        if cache.is_some() {
            match super::cache::SwiftFunctionCache::cleanup(&mut cache,&mut control,wasi.as_ref()) {
                Ok(tail)=>tail.complete(cache,&mut cache_retirement),
                Err(failure)=>{cache_retirement=Some(failure);drop(cache);},
            }
        }else{drop(cache);}
        // A failed original cleanup can leave a real cache owner in this slot.
        // Its storage dies, but its uncertain tickets are never repaired/refunded.
        let wasi_retirement=match wasi {Some(wasi)=>wasi.cleanup(&mut control),None=>Ok(())};
        let _captured_foundation=base_foundation;
        // Finalizer return/error/move lifetime closure is not proven. Do not
        // narrow to a byte-only alternate foundation. Original finish records
        // ConstructionBound and retains the enlarged charge, including F1.
        let usage=control.finish_owned_cleanup(observation);
        SnapshotScopeFinishV1 {primary_retirement,cache_retirement,scope_adopted_retirement,wasi_attachment,wasi_retirement,usage}
    }
}

#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(crate) enum SnapshotStopV1 {Existing(SwiftRunFailure),Cancelled,Deadline(SwiftDeadlineOrigin)}
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(crate) enum SnapshotAdmissionErrorV1 {
    Stop(SnapshotStopV1),Owner,Layout,Arithmetic,WorkAuditPending,
    Work {used:u64,requested:u64,limit:u64},
    Storage {current:usize,additional:usize,limit:usize},
}
impl RuntimeControl {
    pub(super) fn snapshot_existing_v1(&self)->Result<(),SnapshotAdmissionErrorV1>{
        match self.first_failure {Some(f)=>Err(SnapshotAdmissionErrorV1::Stop(SnapshotStopV1::Existing(f))),None=>Ok(())}
    }
    pub(super) fn snapshot_observe_stop_v1(&self)->Result<(),SnapshotStopV1>{
        if let Some(f)=self.first_failure{return Err(SnapshotStopV1::Existing(f));}
        if self.cancellation.is_cancelled(){return Err(SnapshotStopV1::Cancelled);}
        if Instant::now()>=self.deadline{return Err(SnapshotStopV1::Deadline(self.deadline_origin));}
        Ok(())
    }
    pub(crate) fn snapshot_ticket_v1(&self,ticket:&ReservationTicket,category:SwiftReservationCategory,bytes:usize)
        ->Result<(),SnapshotAdmissionErrorV1>{
        self.snapshot_existing_v1()?;
        if ticket.owner==0 || ticket.owner!=self.owner{return Err(SnapshotAdmissionErrorV1::Owner);}
        if !ticket.matches_layout(category,bytes) || self.reservations.live_tickets==0
            || self.reservations.category(category).current<bytes || self.reservations.combined.current<bytes {
            return Err(SnapshotAdmissionErrorV1::Layout);
        }
        Ok(())
    }
    pub(super) fn snapshot_owner_v1(&self,owner:u64)->Result<(),SnapshotAdmissionErrorV1>{
        self.snapshot_existing_v1()?;
        if owner==0 || owner!=self.owner{return Err(SnapshotAdmissionErrorV1::Owner);}
        Ok(())
    }
    pub(crate) fn snapshot_ticket_identity_v1(&self,ticket:&ReservationTicket)->Result<(),SnapshotAdmissionErrorV1>{
        self.snapshot_ticket_v1(ticket,ticket.category,ticket.bytes)
    }
    pub(super) fn snapshot_adopted_pair_v1(&self,adopted:&AdoptedProof)->Result<(),SnapshotAdmissionErrorV1>{
        self.snapshot_ticket_identity_v1(&adopted.source)?;
        self.snapshot_ticket_identity_v1(&adopted.metadata)?;
        self.snapshot_ticket_v1(&adopted.source,SwiftReservationCategory::RetainedSource,adopted.proof().usage().source_bytes)?;
        self.snapshot_ticket_v1(&adopted.metadata,SwiftReservationCategory::RetainedMetadata,adopted.proof().usage().metadata_reserved)
    }
    pub(super) fn snapshot_foundation_pair_v1(&self)->Result<usize,SnapshotAdmissionErrorV1>{
        let construction=self.construction.as_ref().ok_or(SnapshotAdmissionErrorV1::Layout)?;
        self.snapshot_ticket_v1(construction,SwiftReservationCategory::Construction,construction.bytes)?;
        self.snapshot_ticket_v1(self.control_header.as_ref().ok_or(SnapshotAdmissionErrorV1::Layout)?,SwiftReservationCategory::Shared,size_of::<Self>())?;
        self.snapshot_ticket_v1(self.cancellation_backing.as_ref().ok_or(SnapshotAdmissionErrorV1::Layout)?,SwiftReservationCategory::Shared,Cancellation::requested_backing_layout().size())?;
        if self.reservations.construction.current!=construction.bytes{return Err(SnapshotAdmissionErrorV1::Layout);}
        Ok(construction.bytes)
    }
    pub(super) fn snapshot_totals_v1(&self,source:usize,metadata:usize,cache:usize,wasi:usize,wasi_tickets:usize)->Result<(),SnapshotAdmissionErrorV1>{
        let construction=self.snapshot_foundation_pair_v1()?;
        let shared=size_of::<Self>().checked_add(Cancellation::requested_backing_layout().size()).ok_or(SnapshotAdmissionErrorV1::Arithmetic)?;
        let terms=[(SwiftReservationCategory::RetainedSource,source),(SwiftReservationCategory::RetainedMetadata,metadata),
            (SwiftReservationCategory::Cache,cache),(SwiftReservationCategory::Wasi,wasi),
            (SwiftReservationCategory::Shared,shared),(SwiftReservationCategory::Construction,construction)];
        let mut sum=0usize;
        for (category,bytes) in terms {
            if self.reservations.category(category).current<bytes{return Err(SnapshotAdmissionErrorV1::Layout);}
            sum=sum.checked_add(bytes).ok_or(SnapshotAdmissionErrorV1::Arithmetic)?;
        }
        let tickets=9usize.checked_add(wasi_tickets).ok_or(SnapshotAdmissionErrorV1::Arithmetic)?;
        if self.reservations.combined.current<sum || self.reservations.live_tickets<tickets{return Err(SnapshotAdmissionErrorV1::Layout);}
        Ok(())
    }
    pub(super) fn snapshot_debit_v1(&mut self,credits:u64)->Result<(),SnapshotAdmissionErrorV1>{
        self.snapshot_observe_stop_v1().map_err(SnapshotAdmissionErrorV1::Stop)?;
        let used=self.execution_work;let limit=self.budget.execution_work;
        let next=used.checked_add(credits).filter(|next|*next<=limit)
            .ok_or(SnapshotAdmissionErrorV1::Work {used,requested:credits,limit})?;
        self.execution_work=next;Ok(())
    }
    pub(super) fn snapshot_storage_preflight_v1(&self,additional:usize)->Result<usize,SnapshotAdmissionErrorV1>{
        let previous=self.snapshot_foundation_pair_v1()?;
        for (current,limit) in [(self.reservations.construction.current,self.category_limit(SwiftReservationCategory::Construction)),
            (self.reservations.combined.current,self.budget.combined_bytes)] {
            current.checked_add(additional).filter(|next|*next<=limit)
                .ok_or(SnapshotAdmissionErrorV1::Storage {current,additional,limit})?;
        }
        self.snapshot_observe_stop_v1().map_err(SnapshotAdmissionErrorV1::Stop)?;
        Ok(previous)
    }
    pub(super) fn snapshot_commit_storage_v1(&mut self,additional:usize)->Result<usize,SnapshotAdmissionErrorV1>{
        let previous=self.snapshot_storage_preflight_v1(additional)?;
        // All fallible operations precede this one atomic same-ticket commit.
        let construction=previous.checked_add(additional).ok_or(SnapshotAdmissionErrorV1::Arithmetic)?;
        let combined=self.reservations.combined.current.checked_add(additional).ok_or(SnapshotAdmissionErrorV1::Arithmetic)?;
        self.construction.as_mut().expect("preflight actual ticket").bytes=construction;
        self.reservations.construction.current=construction;
        self.reservations.construction.peak=self.reservations.construction.peak.max(construction);
        self.reservations.combined.current=combined;
        self.reservations.combined.peak=self.reservations.combined.peak.max(combined);
        Ok(previous)
    }
}

// Conservative candidate source roles. Not a selected operational floor.
struct CommonAdoptionPlacesV1 {
    body_argument:AdoptionBodyV1,body_move:AdoptionBodyV1,
    budgets:[SwiftRunBudget;2],started:[Instant;2],cancellations:[Cancellation;2],
    original_return:Result<(RuntimeControl,AdoptedProof),SwiftRunFailure>,
    original_adapter_return:Result<(RuntimeControl,AdoptedProof),SwiftRunFailure>,
}
struct SnapshotScopePlacesV1 {
    scopes:[SnapshotScopeV1;3],scope_return:Result<SnapshotScopeV1,SnapshotPreScopeFailureV1>,
    scope_option:Option<Result<SnapshotScopeV1,SnapshotPreScopeFailureV1>>,
    core_returns:[Result<(RuntimeControl,AdoptedProof),SnapshotPreScopeFailureV1>;3],
    pre_scope_errors:[SnapshotPreScopeFailureV1;4],
    retirement:[Result<(),SwiftRunFailure>;4],
    run:SnapshotRunV1,run_move:SnapshotRunV1,
    finish_return:SnapshotScopeFinishV1,finish_move:SnapshotScopeFinishV1,
    attachment:SnapshotWasiAttachmentV1,attachment_return:SnapshotWasiAttachmentV1,
    body_moves:[AdoptionBodyV1;3],outer_return:SnapshotOuterV1,outer_option:Option<SnapshotOuterV1>,
    selected_body_moves:[super::retained_profile_loader_v1::SelectedSnapshotBodyV1;4],
    borrows:[&'static mut RuntimeControl;8],scalars:[usize;16],
}
fn snapshot_scope_candidate_foundation_v1()->Option<usize>{
    // Original common-core funding is separately pending selection. These are
    // intentionally conservative additional named source roles, not RSS.
    foundation_construction_bytes()?.checked_add(size_of::<CommonAdoptionPlacesV1>())?
        .checked_add(size_of::<SnapshotScopePlacesV1>())?
        .checked_add(super::cache::SNAPSHOT_FOUNDATION_PLACES_V1)
}
#[cfg(mixer_snapshot_composition_layout)]
#[no_mangle]
pub static MIXER_COMPOSITION_CONTROL_LAYOUTS_V1:[usize;24]=[
 size_of::<RuntimeControl>(),std::mem::align_of::<RuntimeControl>(),
 size_of::<CommonAdoptionPlacesV1>(),std::mem::align_of::<CommonAdoptionPlacesV1>(),
 size_of::<SnapshotScopeV1>(),std::mem::align_of::<SnapshotScopeV1>(),
 size_of::<SnapshotPreScopeFailureV1>(),std::mem::align_of::<SnapshotPreScopeFailureV1>(),
 size_of::<SnapshotScopePlacesV1>(),std::mem::align_of::<SnapshotScopePlacesV1>(),
 size_of::<SnapshotRunV1>(),std::mem::align_of::<SnapshotRunV1>(),
 size_of::<SnapshotScopeFinishV1>(),std::mem::align_of::<SnapshotScopeFinishV1>(),
 size_of::<Result<SnapshotScopeV1,SnapshotPreScopeFailureV1>>(),std::mem::align_of::<Result<SnapshotScopeV1,SnapshotPreScopeFailureV1>>(),
 size_of::<Option<Result<SnapshotScopeV1,SnapshotPreScopeFailureV1>>>(),std::mem::align_of::<Option<Result<SnapshotScopeV1,SnapshotPreScopeFailureV1>>>(),
 size_of::<Result<(RuntimeControl,AdoptedProof),SnapshotPreScopeFailureV1>>(),std::mem::align_of::<Result<(RuntimeControl,AdoptedProof),SnapshotPreScopeFailureV1>>(),
 size_of::<SnapshotWasiAttachmentV1>(),std::mem::align_of::<SnapshotWasiAttachmentV1>(),
 size_of::<SnapshotStopV1>(),size_of::<SnapshotAdmissionErrorV1>(),
];
