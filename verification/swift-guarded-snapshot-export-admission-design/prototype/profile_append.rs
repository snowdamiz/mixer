// Selected-scope proposal layout only. No constructor, executable path or owner extraction.
enum ProposalFoundationProfileV1 { Original, Snapshot }
type ProposalOriginalAdoptionReturnV1 = Result<(RuntimeControl,AdoptedProof),SwiftRunFailure>;
// Concrete conservative ADDITIONAL common-core wrapper/transfer roles. Existing
// foundation/entry inventories remain included, not subtracted or reused.
struct ProposalCommonCoreDeltaPlacesV1 {
    adapter_body:AdoptionBodyV1, adapter_budget:SwiftRunBudget,
    adapter_started:Instant, adapter_cancellation:Cancellation,
    profile_argument:ProposalFoundationProfileV1,
    core_body_move:AdoptionBodyV1, core_budget_move:SwiftRunBudget,
    core_started_move:Instant, core_cancellation_move:Cancellation,
    core_return:ProposalOriginalAdoptionReturnV1,
    adapter_return:ProposalOriginalAdoptionReturnV1,
}
// Own the ORIGINAL authorities. A later method may borrow them, never extract
// an owned RuntimeControl. Scope must retain or consume all actual owner slots.
struct ProposalSnapshotAdoptionScopeV1 {
    control:RuntimeControl, adopted:Option<AdoptedProof>,
    cache:Option<super::cache::SwiftFunctionCache>,
    wasi:Option<crate::experimental_wasi::accounted::AccountedWasi>,
    base_foundation:usize,
}
fn proposal_preserve_adopt_body_signature_v1() {
    let _entry:fn(AdoptionBodyV1,SwiftRunBudget,Instant,Cancellation)->ProposalOriginalAdoptionReturnV1
        = RuntimeControl::adopt_body;
}
#[no_mangle]
pub static MIXER_ADMISSION_PROFILE_LAYOUT_PROBE:[usize;16]=[
    size_of::<ProposalFoundationProfileV1>(),std::mem::align_of::<ProposalFoundationProfileV1>(),
    size_of::<AdoptionBodyV1>(),std::mem::align_of::<AdoptionBodyV1>(),
    size_of::<SwiftRunBudget>(),std::mem::align_of::<SwiftRunBudget>(),
    size_of::<Instant>(),std::mem::align_of::<Instant>(),
    size_of::<Cancellation>(),std::mem::align_of::<Cancellation>(),
    size_of::<ProposalOriginalAdoptionReturnV1>(),std::mem::align_of::<ProposalOriginalAdoptionReturnV1>(),
    size_of::<ProposalCommonCoreDeltaPlacesV1>(),std::mem::align_of::<ProposalCommonCoreDeltaPlacesV1>(),
    size_of::<ProposalSnapshotAdoptionScopeV1>(),std::mem::align_of::<ProposalSnapshotAdoptionScopeV1>(),
];
