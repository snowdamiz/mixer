
// Inert work/storage query only. Exact production function pointer forces
// code generation of the unchanged function and its actual and_then closure.
#[used]
static OWNED_PROVIDER_LAYOUT_FORCE_V1: for<'p0> fn(
    super::super::ReviewedFixtureBindingV1<'p0>,
    super::ImmutableFixtureIdentitiesV1<'p0>,
    [&'p0 [u8]; 5],
) -> Result<UnqualifiedExistingOwnerCandidateV1<'p0>, CandidateShapeRefusalV1>
    = describe_existing_owner_candidate_v1;
fn owned_provider_remaining_layout_query_v1(
    _option_usize_size: [u8; std::mem::size_of::<Option<usize>>()],
    _option_usize_align: [u8; std::mem::align_of::<Option<usize>>()],
    _result_usize_size: [u8; std::mem::size_of::<Result<usize, CandidateShapeRefusalV1>>()],
    _result_usize_align: [u8; std::mem::align_of::<Result<usize, CandidateShapeRefusalV1>>()],
    _residual_size: [u8; std::mem::size_of::<Result<std::convert::Infallible, CandidateShapeRefusalV1>>()],
    _residual_align: [u8; std::mem::align_of::<Result<std::convert::Infallible, CandidateShapeRefusalV1>>()],
    _control_flow_size: [u8; std::mem::size_of::<std::ops::ControlFlow<Result<std::convert::Infallible, CandidateShapeRefusalV1>, usize>>()],
    _control_flow_align: [u8; std::mem::align_of::<std::ops::ControlFlow<Result<std::convert::Infallible, CandidateShapeRefusalV1>, usize>>()],
    _range_size: [u8; std::mem::size_of::<std::ops::Range<usize>>()],
    _range_align: [u8; std::mem::align_of::<std::ops::Range<usize>>()],
    _slice_ref_size: [u8; std::mem::size_of::<&'static [u8]>()],
    _slice_ref_align: [u8; std::mem::align_of::<&'static [u8]>()],
    _path_ref_size: [u8; std::mem::size_of::<&'static std::path::Path>()],
    _path_ref_align: [u8; std::mem::align_of::<&'static std::path::Path>()],
    _osstr_ref_size: [u8; std::mem::size_of::<&'static std::ffi::OsStr>()],
    _osstr_ref_align: [u8; std::mem::align_of::<&'static std::ffi::OsStr>()],
    _slice_header_ref_size: [u8; std::mem::size_of::<&'static &'static [u8]>()],
    _slice_header_ref_align: [u8; std::mem::align_of::<&'static &'static [u8]>()],
    _retained_array_ref_size: [u8; std::mem::size_of::<&'static [&'static [u8]; 5]>()],
    _retained_array_ref_align: [u8; std::mem::align_of::<&'static [&'static [u8]; 5]>()],
    _identity_ref_size: [u8; std::mem::size_of::<&'static super::ImmutableIdentityPreimageV1<'static>>()],
    _identity_ref_align: [u8; std::mem::align_of::<&'static super::ImmutableIdentityPreimageV1<'static>>()],
    _range_ref_size: [u8; std::mem::size_of::<&'static mut std::ops::Range<usize>>()],
    _range_ref_align: [u8; std::mem::align_of::<&'static mut std::ops::Range<usize>>()],
    _usize_ref_size: [u8; std::mem::size_of::<&'static usize>()],
    _usize_ref_align: [u8; std::mem::align_of::<&'static usize>()],
    _byte_ref_size: [u8; std::mem::size_of::<&'static u8>()],
    _byte_ref_align: [u8; std::mem::align_of::<&'static u8>()],
    _digest_ref_size: [u8; std::mem::size_of::<&'static [u8; 32]>()],
    _digest_ref_align: [u8; std::mem::align_of::<&'static [u8; 32]>()],
    _binding_size: [u8; std::mem::size_of::<super::super::ReviewedFixtureBindingV1<'static>>()],
    _binding_align: [u8; std::mem::align_of::<super::super::ReviewedFixtureBindingV1<'static>>()],
    _identities_size: [u8; std::mem::size_of::<super::ImmutableFixtureIdentitiesV1<'static>>()],
    _identities_align: [u8; std::mem::align_of::<super::ImmutableFixtureIdentitiesV1<'static>>()],
    _preexisting_size: [u8; std::mem::size_of::<super::PreexistingImmutableBindingV1<'static>>()],
    _preexisting_align: [u8; std::mem::align_of::<super::PreexistingImmutableBindingV1<'static>>()],
) {}
