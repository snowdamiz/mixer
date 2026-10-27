// Independent compile-only opaque facade controls. Never executed.
fn independent_correlate_v1<'root>(owner: AdmittedImmutableOwnerV1<'root>, supplied: SuppliedLoaderCarrierV1) -> OwnedCorrelationOutcomeV1<'root> {
    let returned = { let (expected, attempt) = owner.correlation_scope_v1().unwrap(); correlate_admitted_loader_v1(attempt, supplied, &expected) };
    retire_admitted_owner_v1(owner);
    returned
}
fn independent_foreign_v1<'original, 'foreign>(owner: AdmittedImmutableOwnerV1<'original>, foreign: AdmittedImmutableOwnerV1<'foreign>, supplied: SuppliedLoaderCarrierV1) -> OwnedCorrelationOutcomeV1<'original> {
    let returned = { let (_own, attempt) = owner.correlation_scope_v1().unwrap(); let (expected, _unused) = foreign.correlation_scope_v1().unwrap(); correlate_admitted_loader_v1(attempt, supplied, &expected) };
    retire_admitted_owner_v1(owner); retire_admitted_owner_v1(foreign);
    returned
}
fn independent_final_v1<'root>(owner: AdmittedImmutableOwnerV1<'root>, supplied: SuppliedLoaderCarrierV1, args: FixtureLeafArgumentsV1) -> RootBoundFixtureOutcomeV1<'root> {
    independent_correlate_v1(owner, supplied).run_fixture_once_v1(args)
}
fn independent_primary_view_v1<'view, 'root: 'view>(value: &'view RootBoundFixtureOutcomeV1<'root>) -> RootBoundPrimaryBorrowV1<'view> { value.primary_v1() }
fn independent_ok_view_v1<'view, 'root: 'view>(value: &'view RootBoundFixtureOutcomeV1<'root>) -> Option<&'view super::control::SnapshotScopeFinishV1> {
    match value.primary_v1() { RootBoundPrimaryBorrowV1::Leaf(Ok(original)) => Some(original), _ => None }
}
fn independent_err_view_v1<'view, 'root: 'view>(value: &'view RootBoundFixtureOutcomeV1<'root>) -> Option<&'view super::control::SnapshotPreScopeFailureV1> {
    match value.primary_v1() { RootBoundPrimaryBorrowV1::Leaf(Err(original)) => Some(original), _ => None }
}
fn independent_loader_view_v1<'view, 'root: 'view>(value: &'view RootBoundFixtureOutcomeV1<'root>) -> Option<&'view LoaderFailureV1> {
    match value.primary_v1() { RootBoundPrimaryBorrowV1::LoaderRefused(original) => Some(original), _ => None }
}
