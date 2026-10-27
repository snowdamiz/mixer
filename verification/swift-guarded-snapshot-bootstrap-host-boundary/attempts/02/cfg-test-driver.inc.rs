// Compile-only private leaf for a future trusted-local, no-WASI fixture.
// No test registration, export, CLI route, grant constructor or dispatch.
// The external host reservation must predate File setup, loading, argument
// creation and this call, and survive the returned diagnostic's destruction.
#[cfg(test)]
pub(in crate::experimental_swift_reactor) fn run_one_loaded_fixture_v1(
    selected: super::super::retained_profile_loader_v1::SelectedValidatedProfileV1,
    budget: super::super::control::SwiftRunBudget,
    started: std::time::Instant,
    cancellation: crate::Cancellation,
    claims: &UnverifiedProfileDigestBytesV1,
    rows: &mut File,
    snapshot: &mut File,
) -> Result<super::super::control::SnapshotScopeFinishV1,
            super::super::control::SnapshotPreScopeFailureV1> {
    let scope = match selected.into_snapshot_scope_v1(budget, started, cancellation) {
        Ok(scope) => scope,
        Err(failure) => return Err(failure),
    };
    let run = scope.construct_v1(claims, rows, snapshot);
    let _ = run.outer_v1();
    Ok(run.finish_v1())
}
