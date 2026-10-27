include!("P01-facade.inc.rs");
fn independent_view_cannot_be_root_length_v1<'view, 'root: 'view>(value: &'view RootBoundFixtureOutcomeV1<'root>) -> RootBoundPrimaryBorrowV1<'root> { value.primary_v1() }
