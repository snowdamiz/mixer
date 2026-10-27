#![allow(dead_code)]
// Minimal native compiler reproduction of the frozen design's lifetime relation.
// Types are opaque stand-ins; this is not an actual-source Mixer integration.
struct RuntimeControl;
struct SwiftFunctionCache;
struct InitialProfileScalarsV1;
struct InitialProfileBorrowV1<'a> {
    cache: &'a SwiftFunctionCache,
    control: &'a RuntimeControl,
    scalars: InitialProfileScalarsV1,
}
struct SnapshotPhaseV1<'c> {
    control: &'c mut RuntimeControl,
    previous_bound: usize,
}
impl RuntimeControl {
    fn begin_snapshot_phase_v1<'c>(&'c mut self) -> SnapshotPhaseV1<'c> {
        SnapshotPhaseV1 { control: self, previous_bound: 1 }
    }
}
impl SnapshotPhaseV1<'_> {
    fn complete<T>(self, actual_temporary_storage: T) { drop(actual_temporary_storage); }
}
fn observe(_: &InitialProfileBorrowV1<'_>) {}
fn proposed_sequence(control: &mut RuntimeControl, cache: &SwiftFunctionCache) {
    let phase = control.begin_snapshot_phase_v1();
    // This is the accepted original guard's direct immutable control field.
    let initial = InitialProfileBorrowV1 { cache, control, scalars: InitialProfileScalarsV1 };
    observe(&initial);
    drop(initial);
    // Required actual phase retirement extends phase's mutable borrow to here.
    phase.complete(());
}
