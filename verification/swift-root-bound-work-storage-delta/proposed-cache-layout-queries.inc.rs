// PROPOSAL ONLY. Never inserted or compiled by this lane.
// Append inside trusted_local_host_account_entry_v1 in the same isolated copy.
mod root_bound_child_layout_proposal_v1 {
    use super::*;
    fn query_v1() {
        macro_rules! pair {
            ($type:ty) => {{
                let _: [u8; 0] = [0u8; std::mem::size_of::<$type>()];
                let _: [u8; 0] = [0u8; std::mem::align_of::<$type>()];
            }};
        }
        pair!(AdmittedFixtureOutcomeV1<'static>);
        pair!(AdmittedFixturePayloadV1<'static>);
        pair!(PrepaidOwnedV1<'static, AdmittedFixtureOutcomeV1<'static>>);
        pair!(Result<PrepaidOwnedV1<'static, AdmittedFixtureOutcomeV1<'static>>, RefusalV1>);
        pair!(Option<AdmittedFixtureOutcomeV1<'static>>);
        pair!(Option<&'static AdmittedFixtureOutcomeV1<'static>>);
    }
}
