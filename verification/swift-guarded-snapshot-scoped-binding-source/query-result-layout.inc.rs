// Inert metadata/MIR signature for the two accepted Result observations.
fn scoped_result_layout_query_v1(
    _selection_result_size: [u8; std::mem::size_of::<Result<OneFixtureOuterRequestV1, BindingSelectionRefusalV1>>()],
    _selection_result_align: [u8; std::mem::align_of::<Result<OneFixtureOuterRequestV1, BindingSelectionRefusalV1>>()],
) {}
