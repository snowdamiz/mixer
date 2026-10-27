// Combined inert production metadata-only rejected ownership probes.
fn reject_escaping_request_v1<'p0>(
    preexisting: PreexistingImmutableBindingV1<'p0>,
) -> OneFixtureOuterRequestV1<'p0> {
    OneFixtureOuterRequestV1 { preexisting: &preexisting }
}
fn reject_stack_identity_static_v1() -> ImmutableIdentityPreimageV1<'static> {
    let bytes = [0u8; 4];
    ImmutableIdentityPreimageV1 { bytes: &bytes, sha256: [0; 32] }
}
fn reject_mutation_live_identity_v1(bytes: &mut [u8]) {
    let identity = ImmutableIdentityPreimageV1 { bytes, sha256: [0; 32] };
    bytes[0] = 1;
    std::hint::black_box(identity.bytes);
}
fn reject_drop_live_identity_v1(bytes: Vec<u8>) {
    let identity = ImmutableIdentityPreimageV1 { bytes: &bytes, sha256: [0; 32] };
    drop(bytes);
    std::hint::black_box(identity.bytes);
}
fn reject_double_consume_request_v1(request: OneFixtureOuterRequestV1<'_>) {
    consume_outer_request_v1(request);
    consume_outer_request_v1(request);
}
