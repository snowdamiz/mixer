// Layout and actual-private-field signature probe only; never executed.
use super::super::control::{ProposalSnapshotAdmissionErrorV1 as AError,ProposalSnapshotStopV1 as Stop};
struct ProposalSnapshotPhaseV1<'a> { control:&'a mut RuntimeControl, previous_bound:usize }
struct ProposalObservationV1 { bytes:u64, calls:u64, planning_debit:u64, emission_debit:u64 }
struct ProposalExportErrorV1 {
    code:u32, block_attempts:u32, acknowledged:u64, calls:u64, requested:u64,
    io:Option<std::io::Error>, post_stop:Option<Stop>, admission:Option<AError>,
}
enum ProposalAttemptV1 {
    NotReached, AdmissionRefused(AError), Attempted(Result<ProposalObservationV1,ProposalExportErrorV1>),
}
struct ProposalOuterV1 { primary:InitialProfileConstructionOutcomeV1, snapshot:ProposalAttemptV1 }
// One concrete conservative shell. It is NOT a claim of globally minimal cost.
// Early outcomes and admission failure still need outer/return/error places.
struct ProposalAdmissionShellPlacesV1<'a> {
    control:&'a mut RuntimeControl, wasi:Option<&'a AccountedWasi>, adopted:&'a AdoptedProof,
    previous:usize, enlarged:Option<usize>,
    phase_return:Result<ProposalSnapshotPhaseV1<'a>,AError>, admission_error:AError,
    attempt_return:ProposalAttemptV1,
    wrapper_return:ProposalOuterV1, caller_return:Option<ProposalOuterV1>,
    wrapper_move:ProposalOuterV1, caller_move:Option<ProposalOuterV1>,
    cleanup_failure:Option<SwiftRunFailure>, cleanup_return:Result<(),SwiftRunFailure>,
}
fn proposal_guard_stop_signature_v1(initial:&InitialProfileBorrowV1<'_>)->Result<(),Stop> {
    initial.control.proposal_observe_snapshot_stop_v1()
}
fn proposal_cache_pair_signature_v1(cache:&SwiftFunctionCache,control:&RuntimeControl)
    ->Result<(),AError> {
    control.proposal_snapshot_owner_v1(cache.owner)?;
    let header=cache.header.as_ref().ok_or(AError::Layout)?;
    control.proposal_snapshot_ticket_v1(header)?;
    control.proposal_snapshot_adopted_v1(&cache.adopted)?;
    for ticket in &cache.buffers {
        control.proposal_snapshot_ticket_v1(ticket.as_ref().ok_or(AError::Layout)?)?;
    }
    Ok(())
}
// Compiler emits exact native sizes/alignment into LLVM IR. No function runs.
#[no_mangle]
pub static MIXER_ADMISSION_DESIGN_LAYOUT_PROBE: [usize;18] = [
    size_of::<RuntimeControl>(),std::mem::align_of::<RuntimeControl>(),
    size_of::<AError>(),std::mem::align_of::<AError>(),
    size_of::<Stop>(),std::mem::align_of::<Stop>(),
    size_of::<ProposalSnapshotPhaseV1<'static>>(),std::mem::align_of::<ProposalSnapshotPhaseV1<'static>>(),
    size_of::<ProposalExportErrorV1>(),std::mem::align_of::<ProposalExportErrorV1>(),
    size_of::<ProposalAttemptV1>(),std::mem::align_of::<ProposalAttemptV1>(),
    size_of::<ProposalOuterV1>(),std::mem::align_of::<ProposalOuterV1>(),
    size_of::<ProposalAdmissionShellPlacesV1<'static>>(),std::mem::align_of::<ProposalAdmissionShellPlacesV1<'static>>(),
    size_of::<InitialProfileConstructionOutcomeV1>(),std::mem::align_of::<InitialProfileConstructionOutcomeV1>(),
];
