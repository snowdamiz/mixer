
// Independent inert metadata/MIR layout query, excluded from candidate distribution.
fn independent_provider_layout_query_v1(
    _input_backing_size: [u8; std::mem::size_of::<InputBackingDescriptionV1>()],
    _input_backing_align: [u8; std::mem::align_of::<InputBackingDescriptionV1>()],
    _pending_requirement_size: [u8; std::mem::size_of::<PendingUpstreamRequirementV1>()],
    _pending_requirement_align: [u8; std::mem::align_of::<PendingUpstreamRequirementV1>()],
    _pending_requirements_size: [u8; std::mem::size_of::<PendingUpstreamRequirementsV1>()],
    _pending_requirements_align: [u8; std::mem::align_of::<PendingUpstreamRequirementsV1>()],
    _unqualified_candidate_size: [u8; std::mem::size_of::<UnqualifiedExistingOwnerCandidateV1<'static>>()],
    _unqualified_candidate_align: [u8; std::mem::align_of::<UnqualifiedExistingOwnerCandidateV1<'static>>()],
    _shape_refusal_size: [u8; std::mem::size_of::<CandidateShapeRefusalV1>()],
    _shape_refusal_align: [u8; std::mem::align_of::<CandidateShapeRefusalV1>()],
    _candidate_result_size: [u8; std::mem::size_of::<Result<UnqualifiedExistingOwnerCandidateV1<'static>, CandidateShapeRefusalV1>>()],
    _candidate_result_align: [u8; std::mem::align_of::<Result<UnqualifiedExistingOwnerCandidateV1<'static>, CandidateShapeRefusalV1>>()],
    _identity_references_size: [u8; std::mem::size_of::<[&'static super::ImmutableIdentityPreimageV1<'static>;12]>()],
    _identity_references_align: [u8; std::mem::align_of::<[&'static super::ImmutableIdentityPreimageV1<'static>;12]>()],
    _identity_counts_size: [u8; std::mem::size_of::<[usize;12]>()],
    _identity_counts_align: [u8; std::mem::align_of::<[usize;12]>()],
    _path_counts_size: [u8; std::mem::size_of::<[usize;5]>()],
    _path_counts_align: [u8; std::mem::align_of::<[usize;5]>()],
    _retained_path_references_size: [u8; std::mem::size_of::<[&'static [u8];5]>()],
    _retained_path_references_align: [u8; std::mem::align_of::<[&'static [u8];5]>()],
) {}
