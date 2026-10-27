// Diagnostic-only suffix inside the copied private host_account_v1 module.
fn outer_parent_account_layout_query_v1(
    _root_size: [u8; std::mem::size_of::<TrustedRootPolicyV1>()],
    _root_align: [u8; std::mem::align_of::<TrustedRootPolicyV1>()],
    _cost_size: [u8; std::mem::size_of::<CostV1>()],
    _cost_align: [u8; std::mem::align_of::<CostV1>()],
    _quote_size: [u8; std::mem::size_of::<ReviewedWholeQuoteV1>()],
    _quote_align: [u8; std::mem::align_of::<ReviewedWholeQuoteV1>()],
    _reservation_size: [u8; std::mem::size_of::<ReservationV1<'static>>()],
    _reservation_align: [u8; std::mem::align_of::<ReservationV1<'static>>()],
) {}
