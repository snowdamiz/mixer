include!("P01-facade.inc.rs");
fn independent_own_leaf_ok_v1<'root>(owner: AdmittedImmutableOwnerV1<'root>, supplied: SuppliedLoaderCarrierV1, args: FixtureLeafArgumentsV1) -> Option<super::control::SnapshotScopeFinishV1> {
    let complete = independent_final_v1(owner, supplied, args);
    match complete.primary_v1() { RootBoundPrimaryBorrowV1::Leaf(Ok(original)) => Some(*original), _ => None }
}
