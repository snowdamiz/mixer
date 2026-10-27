// PROPOSAL ONLY. Never inserted or compiled by this lane.
// Append inside prepaid_input_owner_v1 in an isolated diagnostic-only copy.
// 'static is a type parameter for compile-only layout; no root value is made.
mod root_bound_named_layout_proposal_v1 {
    use super::*;
    fn query_v1() {
        macro_rules! pair {
            ($type:ty) => {{
                let _: [u8; 0] = [0u8; std::mem::size_of::<$type>()];
                let _: [u8; 0] = [0u8; std::mem::align_of::<$type>()];
            }};
        }
        pair!(AdmittedLoaderCorrespondenceV1<'static, 'static>);
        pair!(PrepaidCorrelationAttemptV1<'static, 'static>);
        pair!(RootBoundV1<'static, LoaderCarrierCoreV1<File>>);
        pair!(RootBoundV1<'static, (OriginalCorrelationRefusalV1, LoaderCarrierCoreV1<File>)>);
        pair!(RootBoundV1<'static, Result<LoaderCarrierCoreV1<File>, (OriginalCorrelationRefusalV1, LoaderCarrierCoreV1<File>)>>);
        pair!(Result<RootBoundV1<'static, LoaderCarrierCoreV1<File>>, RootBoundV1<'static, (OriginalCorrelationRefusalV1, LoaderCarrierCoreV1<File>)>>);
        pair!(RawSelectedBundleV1);
        pair!(RootBoundV1<'static, RawSelectedBundleV1>);
        pair!(CorrelatedSelectedProfileV1<'static>);
        pair!(RootBoundSelectedProfileV1<'static>);
        pair!(RawCorrelationOutcomeV1);
        pair!(RootBoundV1<'static, RawCorrelationOutcomeV1>);
        pair!(OwnedCorrelationOutcomeV1<'static>);
        pair!(FixtureLeafArgumentsV1);
        pair!(RawFixturePrimaryV1);
        pair!(RawFixtureResultV1);
        pair!(RootBoundV1<'static, RawFixtureResultV1>);
        pair!(RootBoundFixtureOutcomeV1<'static>);
        pair!(RootBoundPrimaryBorrowV1<'static>);
        pair!((AdmittedLoaderCorrespondenceV1<'static, 'static>, PrepaidCorrelationAttemptV1<'static, 'static>));
        pair!(Result<(AdmittedLoaderCorrespondenceV1<'static, 'static>, PrepaidCorrelationAttemptV1<'static, 'static>), BootstrapFailureV1>);
        pair!((RawFixturePrimaryV1, ReturnedLoaderFilesV1, LoaderUsageV1, &'static BootstrapLedgerV1));
    }
}
