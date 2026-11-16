//! UI entry invocation through the original accounted dispatcher and unwind.
use super::*;
use super::memory_growth_operations::{self as growth, GrowthCompletion, SwiftGrowthStorage};

pub(crate) fn invoke(owner: &mut SwiftReactorInstance, function: u32, argument: Option<Value>)
    -> (Result<Option<Value>, SwiftRunFailure>, bool) {
    super::R3238_STATS.with(|s|s.set([0;3]));
    eprintln!("R3238_TURN function={function}");
    let cursor = Cursor { stage: SwiftRunStage::Invocation, function: Some(function), offset: None };
    let (mut phase, mut context) = match owner.prepare_growth(cursor) {
        Ok(prepared) => prepared, Err(failure) => return (Err(failure), true),
    };
    let mut pending = SwiftGrowthStorage::empty();
    let mut storage = FrameOperationStorage { preparation: None, entry: None, returned: None, drained: None, controlled: None };
    let mut outcome = (|| {
        if let Some(argument) = argument { phase.phase.push_value(argument)?; }
        phase.enter(function)?;
        call_dispatch::run(&mut phase, &mut context, &mut pending, &mut storage)?;
        match storage.returned {
            Some(Ok(FrameReturn::Outermost(value))) => Ok(value),
            Some(Err(failure)) => Err(failure),
            _ => Err(phase.invariant("swift_ui_result_shape")),
        }
    })();
    if outcome.is_ok() {
        if let Err(failure) = phase.phase.operation.control.check_with_wasi(cursor, Some(phase.phase.operation.wasi.usage())) {
            outcome = Err(failure);
        }
    }
    if let Err(failure) = growth::release_growth_pending(&mut phase, &mut context, &mut pending) {
        if outcome.is_ok() { outcome = Err(failure); }
    }
    super::r3238_dump(&phase, None);
    if outcome.is_err() { phase.terminal(); storage.drained = Some(phase.drain()); }
    let cleaned = matches!(growth::complete_growth(phase, context, pending, storage, None),
        GrowthCompletion::Completed(FrameCompletion::Completed));
    (outcome, cleaned)
}
