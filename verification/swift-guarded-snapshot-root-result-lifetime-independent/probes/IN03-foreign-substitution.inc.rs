include!("P01-facade.inc.rs");
fn independent_substitute_foreign_v1<'original, 'foreign>(owner: AdmittedImmutableOwnerV1<'original>, foreign: AdmittedImmutableOwnerV1<'foreign>, supplied: SuppliedLoaderCarrierV1) -> OwnedCorrelationOutcomeV1<'foreign> { independent_foreign_v1(owner, foreign, supplied) }
