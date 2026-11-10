//! One command invocation through the original owned dispatcher and frame cleanup.
use super::*;
use super::memory_growth_operations::{self as growth, GrowthCompletion, SwiftGrowthStorage};

pub(crate) fn run(owner: &mut SwiftReactorInstance, function: u32) -> (Option<SwiftRunFailure>, bool) {
    let cursor = Cursor { stage: SwiftRunStage::Invocation, function: Some(function), offset: None };
    let (mut phase, mut context) = match owner.prepare_growth(cursor) {
        Ok(prepared) => prepared,
        Err(failure) => return (Some(failure), true),
    };
    let mut pending = SwiftGrowthStorage::empty();
    let mut storage = FrameOperationStorage {
        preparation: None, entry: None, returned: None, drained: None, controlled: None,
    };
    let mut outcome = match phase.enter(function) {
        Err(failure) => Err(failure),
        Ok(()) => match call_dispatch::run(&mut phase, &mut context, &mut pending, &mut storage) {
            Err(failure) => Err(failure),
            Ok(()) => match storage.returned {
                Some(Ok(FrameReturn::Outermost(None))) => Ok(()),
                Some(Err(failure)) => Err(failure),
                _ => Err(phase.invariant("swift_command_result_shape")),
            },
        },
    };
    if outcome.is_ok() {
        outcome = phase.phase.operation.control.check_with_wasi(cursor, Some(phase.phase.operation.wasi.usage()));
    }
    if let Err(failure) = growth::release_growth_pending(&mut phase, &mut context, &mut pending) {
        if outcome.is_ok() { outcome = Err(failure); }
    }
    if outcome.is_err() {
        phase.terminal();
        storage.drained = Some(phase.drain());
    }
    // These consuming barriers retire actual pins, pending growth and caller storage.
    let cleaned = matches!(growth::complete_growth(phase, context, pending, storage, None),
        GrowthCompletion::Completed(FrameCompletion::Completed));
    (outcome.err(), cleaned)
}
