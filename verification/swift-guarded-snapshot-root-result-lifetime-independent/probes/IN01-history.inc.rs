// Historical IR02 production-facade signature, deliberately unchanged.
// Include only inside the existing permitted reactor module API domain.
// It needs no private fields, fabricated File, constructor, or runtime call.
// Desired result on the new minimum repair: compile failure. A missing-lifetime
// diagnostic alone is historical API-shape evidence; semantic closure also
// requires N02 and N14, plus the positive original-root companion in the roster.
fn escape<'root>(owner: AdmittedImmutableOwnerV1<'root>, supplied: SuppliedLoaderCarrierV1) -> OwnedCorrelationOutcomeV1 {
    let result = {
        let (expected, attempt) = owner.correlation_scope_v1().unwrap();
        correlate_admitted_loader_v1(attempt, supplied, &expected)
    };
    retire_admitted_owner_v1(owner);
    result
}
