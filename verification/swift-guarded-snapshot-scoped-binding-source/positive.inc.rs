// Inert metadata/MIR probe only. Never selected or called.
fn scoped_local_binding_compiles_v1<'p0>(
    preexisting: PreexistingImmutableBindingV1<'p0>,
) -> OuterResultV1 {
    let request = OneFixtureOuterRequestV1 { preexisting: &preexisting };
    consume_outer_request_v1(request)
}
