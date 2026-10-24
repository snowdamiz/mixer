//! UNCALLED ownership witness; not product code or an accounting authorization.
use super::*;
use super::memory_growth_operations::{self as growth, GrowthCompletion, SwiftGrowthContext, SwiftGrowthStorage};

#[derive(Clone, Copy)]
enum Request { Initialize, Corpus }
#[derive(Clone, Copy)]
enum Rejection { AlreadyReady, BeforeInitialization, TerminalBlocked }

// No RuntimeControl method is called on ordinary lifecycle misuse. In particular
// this does not call fail, check_with_wasi, record_cleanup, or prepare_growth.
fn precondition(owner: &SwiftReactorInstance, request: Request) -> Result<(), Rejection> {
    match (&owner.lifecycle, request) {
        (Lifecycle::Uninitialized, Request::Initialize) | (Lifecycle::Ready, Request::Corpus) => Ok(()),
        (Lifecycle::Ready, Request::Initialize) => Err(Rejection::AlreadyReady),
        (Lifecycle::Uninitialized, Request::Corpus) => Err(Rejection::BeforeInitialization),
        (Lifecycle::Terminal, _) => Err(Rejection::TerminalBlocked),
    }
}

// The only witness expansion is a consuming publication barrier in the existing
// frame owner. The scalar/result predicate must be checked before this point.
// The exact vacancy predicate is copied solely to make this uncalled witness
// compile against the immutable baseline. A product proposal must instead share
// the original growth::complete_growth boundary, never duplicate this predicate.
fn completion_barrier<'a>(
    mut phase: FrameOperationPhase<'a>,
    context: SwiftGrowthContext<'a>,
    pending: SwiftGrowthStorage,
    storage: FrameOperationStorage<'a>,
    preparation: Option<Result<(FrameOperationPhase<'a>, SwiftGrowthContext<'a>), SwiftRunFailure>>,
    publish_ready: bool,
) -> GrowthCompletion<'a> {
    let vacant = pending.transfer.replacement.capacity() == 0
        && pending.transfer.old.capacity() == 0
        && pending.transfer.ticket.is_none()
        && pending.transfer.old_ticket.is_none()
        && pending.pages_debited == 0
        && !pending.live_unreconciled;
    if !vacant || preparation.is_some() {
        phase.terminal();
        return GrowthCompletion::Retained { phase, context, growth: pending, storage, preparation };
    }
    drop((context, pending, preparation));
    let FrameOperationPhase { phase, cleanup, lifecycle } = phase;
    let completed = FrameOperationPhase {
        phase,
        cleanup,
        lifecycle: &mut *lifecycle,
    }.complete(storage);
    if publish_ready && matches!(completed, FrameCompletion::Completed) {
        *lifecycle = Lifecycle::Ready;
    }
    GrowthCompletion::Completed(completed)
}

// Actual dispatcher entry/return slots are used. This witness intentionally
// returns the completion carrier to its caller and never executes at collection.
fn phase_composition<'a>(
    mut phase: FrameOperationPhase<'a>,
    mut context: SwiftGrowthContext<'a>,
    mut pending: SwiftGrowthStorage,
    mut storage: FrameOperationStorage<'a>,
    preparation: Option<Result<(FrameOperationPhase<'a>, SwiftGrowthContext<'a>), SwiftRunFailure>>,
) -> GrowthCompletion<'a> {
    let entry = phase.enter(35);
    let execution = if entry.is_ok() {
        call_dispatch::run(&mut phase, &mut context, &mut pending, &mut storage)
    } else { entry };
    let expected = matches!(storage.returned, Some(Ok(FrameReturn::Outermost(None))));
    let cleanup = growth::release_growth_pending(&mut phase, &mut context, &mut pending);
    if execution.is_err() || !expected || cleanup.is_err() {
        phase.terminal();
        storage.drained = Some(phase.drain());
    }
    // Semantic completeness, clean-state checks and all added positions remain
    // pending product implementation/accounting. This is borrow composition only.
    completion_barrier(phase, context, pending, storage, preparation,
        execution.is_ok() && expected && cleanup.is_ok())
}

fn bad(owner:&mut SwiftReactorInstance,cursor:Cursor)->Result<(),SwiftRunFailure>{let(mut phase,context)=owner.prepare_growth(cursor)?;owner.lifecycle=Lifecycle::Ready;phase.enter(35)?;drop(context);Ok(())}
