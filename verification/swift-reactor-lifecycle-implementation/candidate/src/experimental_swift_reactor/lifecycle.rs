//! Private fixed-target lifecycle over the one original reactor owner.
//! Isolated uncalled candidate: new positions are not yet reservation-authorized.
use super::*;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Request {
    Initialize,
    Corpus,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Rejection {
    AlreadyInitialized,
    NotInitialized,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Reply {
    Initialized,
    Corpus(i32),
}
#[must_use = "Failed completion retains the actual original cleanup authority"]
pub(super) enum Completion<'a> {
    Rejected(Rejection),
    BlockedTerminal,
    PreparationFailed(SwiftRunFailure),
    Completed(Reply),
    Failed {
        failure: Option<SwiftRunFailure>,
        cleanup: GrowthCompletion<'a>,
    },
}

#[derive(Clone, Copy)]
enum Admission {
    Allowed,
    Rejected(Rejection),
    BlockedTerminal,
}
// Ordinary refusals read only lifecycle. No control observation or allocation.
fn precondition(owner: &SwiftReactorInstance, request: Request) -> Admission {
    match (&owner.lifecycle, request) {
        (Lifecycle::Uninitialized, Request::Initialize) | (Lifecycle::Ready, Request::Corpus) => Admission::Allowed,
        (Lifecycle::Ready, Request::Initialize) => Admission::Rejected(Rejection::AlreadyInitialized),
        (Lifecycle::Uninitialized, Request::Corpus) => Admission::Rejected(Rejection::NotInitialized),
        (Lifecycle::Terminal, _) => Admission::BlockedTerminal,
    }
}

pub(super) fn request<'a>(owner: &'a mut SwiftReactorInstance, request: Request) -> Completion<'a> {
    match precondition(owner, request) {
        Admission::Allowed => (),
        Admission::Rejected(rejection) => return Completion::Rejected(rejection),
        Admission::BlockedTerminal => return Completion::BlockedTerminal,
    }
    let (function, stage) = match request {
        Request::Initialize => (35, SwiftRunStage::Initialization),
        Request::Corpus => (62, SwiftRunStage::Invocation),
    };
    let cursor = Cursor { stage, function: Some(function), offset: None };
    let mut preparation = Some(owner.prepare_growth_with_goal(cursor, PreparationGoal::Terminalize));
    let (mut phase, mut context) = match preparation.take().expect("actual preparation result") {
        Ok(prepared) => prepared,
        Err(failure) => {
            // The selected preparation seam has already terminalized the same
            // original lifecycle before constructing any admitted phase borrow.
            return Completion::PreparationFailed(failure);
        }
    };
    let mut pending = SwiftGrowthStorage::empty();
    let mut storage = FrameOperationStorage {
        preparation: None,
        entry: None,
        returned: None,
        drained: None,
        controlled: None,
    };
    let entered = phase.enter(function);
    let execution = match entered {
        Ok(()) => call_dispatch::run(&mut phase, &mut context, &mut pending, &mut storage),
        Err(failure) => Err(failure),
    };
    let mut outcome = match execution {
        Err(failure) => Err(failure),
        Ok(()) => match (request, storage.returned) {
            (_, Some(Err(failure))) => Err(failure),
            (Request::Initialize, Some(Ok(FrameReturn::Outermost(None)))) => Ok(Reply::Initialized),
            (Request::Corpus, Some(Ok(FrameReturn::Outermost(Some(Value::I32(value)))))) => Ok(Reply::Corpus(value)),
            _ => Err(phase.invariant("swift_lifecycle_result_shape")),
        },
    };
    if outcome.is_ok() {
        if matches!(phase.lifecycle, Lifecycle::Terminal) {
            outcome = Err(phase.invariant("swift_lifecycle_terminal_outcome"));
        } else {
            // Actual final observation while the original admitted phase exists.
            // This fixed cursor restores the request's lifecycle stage/target.
            outcome = match phase.phase.operation.control.check_with_wasi(
                cursor, Some(phase.phase.operation.wasi.usage()),
            ) {
                Ok(()) => outcome,
                Err(failure) => Err(failure),
            };
        }
    }
    if outcome.is_err() {
        phase.terminal();
    }
    let released = release_growth_pending(&mut phase, &mut context, &mut pending);
    if let Err(failure) = released {
        if outcome.is_ok() {
            outcome = Err(failure);
        }
        phase.terminal();
    }
    if outcome.is_err() {
        storage.drained = Some(phase.drain());
    }
    let goal = match request {
        Request::Initialize => CompletionGoal::Initialize,
        Request::Corpus => CompletionGoal::Preserve,
    };
    // The i32 remains local through the consuming barrier and cannot escape on
    // a retained/restore-rejected branch. No whole-owner access follows prepare.
    let completed = complete_growth_with_goal(phase, context, pending, storage, preparation, goal);
    match (outcome, completed) {
        (Ok(reply), GrowthCompletion::Completed(FrameCompletion::Completed)) => Completion::Completed(reply),
        (Err(failure), cleanup) => Completion::Failed { failure: Some(failure), cleanup },
        (Ok(_), cleanup) => Completion::Failed { failure: None, cleanup },
    }
}
