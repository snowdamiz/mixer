    // Inert production-only layout diagnostics. No runtime constructor or call.
    const OUTER_RESULT_REQUEST_SIZE: [u8; 0] = [0; std::mem::size_of::<Result<OneFixtureOuterRequestV1, BindingSelectionRefusalV1>>()];
    const OUTER_RESULT_REQUEST_ALIGN: [u8; 0] = [0; std::mem::align_of::<Result<OneFixtureOuterRequestV1, BindingSelectionRefusalV1>>()];
