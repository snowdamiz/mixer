// Independent compile-only child/root and destruction token controls.
fn independent_child_v1<'child, 'root>(account: &'child TrustedHostAccountV1, fixture: FrozenFixtureV1<'_>, owner: AdmittedImmutableOwnerV1<'root>) -> Result<PrepaidOwnedV1<'child, AdmittedFixtureOutcomeV1<'root>>, RefusalV1> {
    let returned = { let (expected, attempt) = owner.correlation_scope_v1().unwrap(); run_one_admitted_fixture_v1(account, fixture, attempt, &expected) };
    crate::experimental_swift_reactor::retained_profile_loader_v1::retire_admitted_owner_v1(owner);
    returned
}
fn independent_destroy_child_v1<'child, 'root>(owned: PrepaidOwnedV1<'child, AdmittedFixtureOutcomeV1<'root>>) -> Option<DestroyedStorageV1<'child>> { destroy_returned_admitted_fixture_v1(owned) }
