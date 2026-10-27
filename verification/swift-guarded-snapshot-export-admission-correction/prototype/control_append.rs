// Design/source-proof correction only. No canonical entry or operational grant.
// These are concrete additional retained places, not a complete source closure.
enum CorrectionFoundationProfileV1 { Original, Snapshot }
struct CorrectionOwnedScopeV1 {
    control: RuntimeControl, adopted: Option<AdoptedProof>,
    cache: Option<super::cache::SwiftFunctionCache>,
    wasi: Option<crate::experimental_wasi::accounted::AccountedWasi>, base: usize,
}
type CorrectionScopeReturnV1 = Result<CorrectionOwnedScopeV1, SwiftRunFailure>;
struct CorrectionEarlyStorageV1 {
    ingress_body: Option<AdoptionBodyV1>,
    profile: CorrectionFoundationProfileV1,
    scope_return: Option<CorrectionScopeReturnV1>,
    caller_return: Option<CorrectionScopeReturnV1>,
    cleanup_return: Option<Result<(),SwiftRunFailure>>,
    retirement_ticket: Option<ReservationTicket>,
}
struct CorrectionPreScopeFailureV1 {
    primary: SwiftRunFailure,
    retirement: Result<(),SwiftRunFailure>,
}
type CorrectionCoreReturnV1 = Result<(RuntimeControl,AdoptedProof),CorrectionPreScopeFailureV1>;
struct CorrectionPreScopePlacesV1 {
    early: CorrectionEarlyStorageV1, early_argument: CorrectionEarlyStorageV1,
    early_drop_argument: CorrectionEarlyStorageV1,
    core_return: CorrectionCoreReturnV1, adapter_return: CorrectionCoreReturnV1,
    caller_return: Option<CorrectionCoreReturnV1>,
    primary: SwiftRunFailure, primary_move: SwiftRunFailure,
    retirement_result: Result<(),SwiftRunFailure>,
    retirement_return: Result<(),SwiftRunFailure>,
    error: CorrectionPreScopeFailureV1, error_move: CorrectionPreScopeFailureV1,
    error_option: Option<CorrectionPreScopeFailureV1>,
    control_borrows: [&'static mut RuntimeControl;3],
}
impl CorrectionEarlyStorageV1 {
    // Drop the actual aggregate before its optional actual ticket refund. This
    // does NOT retire the Snapshot foundation: primary/error/results remain live.
    fn retire(self, control: &mut RuntimeControl) -> Result<(),SwiftRunFailure> {
        let Self { ingress_body,profile,scope_return,caller_return,cleanup_return,retirement_ticket }=self;
        drop((ingress_body,profile,scope_return,caller_return,cleanup_return));
        match retirement_ticket { Some(ticket)=>control.refund(ticket), None=>Ok(()) }
    }
}
impl RuntimeControl {
    // Signature bridge only. No admission mutation, no additional grant. The
    // full cache/WASI pairing and conditional storage preflight remain absent.
    pub(super) fn correction_signature_bound_v1(&self)
        -> Result<usize,ProposalSnapshotAdmissionErrorV1> {
        self.proposal_observe_snapshot_stop_v1().map_err(ProposalSnapshotAdmissionErrorV1::Stop)?;
        let ticket=self.construction.as_ref().ok_or(ProposalSnapshotAdmissionErrorV1::Layout)?;
        self.proposal_snapshot_ticket_v1(ticket)?;
        if ticket.category!=SwiftReservationCategory::Construction {return Err(ProposalSnapshotAdmissionErrorV1::Layout);}
        Ok(ticket.bytes)
    }
}
#[no_mangle]
pub static MIXER_CORRECTION_EARLY_LAYOUT_V1:[usize;24]=[
    size_of::<RuntimeControl>(),std::mem::align_of::<RuntimeControl>(),
    size_of::<CorrectionOwnedScopeV1>(),std::mem::align_of::<CorrectionOwnedScopeV1>(),
    size_of::<CorrectionScopeReturnV1>(),std::mem::align_of::<CorrectionScopeReturnV1>(),
    size_of::<Option<CorrectionScopeReturnV1>>(),std::mem::align_of::<Option<CorrectionScopeReturnV1>>(),
    size_of::<CorrectionEarlyStorageV1>(),std::mem::align_of::<CorrectionEarlyStorageV1>(),
    size_of::<CorrectionPreScopeFailureV1>(),std::mem::align_of::<CorrectionPreScopeFailureV1>(),
    size_of::<CorrectionCoreReturnV1>(),std::mem::align_of::<CorrectionCoreReturnV1>(),
    size_of::<Option<CorrectionCoreReturnV1>>(),std::mem::align_of::<Option<CorrectionCoreReturnV1>>(),
    size_of::<CorrectionPreScopePlacesV1>(),std::mem::align_of::<CorrectionPreScopePlacesV1>(),
    size_of::<Result<(),SwiftRunFailure>>(),std::mem::align_of::<Result<(),SwiftRunFailure>>(),
    size_of::<Option<ReservationTicket>>(),std::mem::align_of::<Option<ReservationTicket>>(),
    size_of::<CorrectionFoundationProfileV1>(),std::mem::align_of::<CorrectionFoundationProfileV1>(),
];
