//! Native-explicit one-shot diagnostic command. No production decoder or CLI route.
use super::{ValidatedSwiftCommand, control::*, execution::*};
use crate::{Cancellation, experimental_wasi::{WasiBudget, WasiGrants}};
use std::{io::Write, time::Instant};

#[derive(Debug)]
pub struct SwiftCommandReport {
    /// Includes the expected proc_exit(0) terminal event, if the guest used it.
    pub terminal: Option<SwiftRunFailure>,
    pub after_cleanup: Option<SwiftRunUsage>,
    pub cleanup_completed: bool,
    pub output_error: bool,
    pub calls_by_function: [u64; 34],
}
impl SwiftCommandReport {
    pub fn succeeded(&self) -> bool {
        self.cleanup_completed && !self.output_error && self.terminal.is_none_or(|failure|
            failure.kind == SwiftRunFailureKind::GuestExit && failure.guest_exit == Some(0))
    }
}

/// Consumes the sealed command once. Guest output is already bounded in the
/// accounted adapter. Native output sinks and caller input buffers are external
/// to the engine reservation ledger; the caller must bound their time/storage.
/// All engine resource, fuel, work, cancellation and deadline checks remain live.
pub fn execute_swift_command(
    command: ValidatedSwiftCommand, budget: SwiftRunBudget, grants: WasiGrants,
    wasi_budget: WasiBudget, cancellation: Cancellation,
    stdout: &mut impl Write, stderr: &mut impl Write,
) -> SwiftCommandReport {
    let (proof, function) = command.into_parts();
    let started = Instant::now();
    let mut report = SwiftCommandReport { terminal: None, after_cleanup: None,
        cleanup_completed: false, output_error: false, calls_by_function: [0; 34] };
    let mut adopted = match RuntimeControl::adopt(proof, budget, started, cancellation) {
        Ok(pair) => Some(pair),
        Err(failure) => {
            report.after_cleanup = failure.after_cleanup;
            report.terminal = Some(failure);
            report.cleanup_completed = clean(report.after_cleanup);
            return report;
        }
    };
    let mut constructed = Some(SwiftReactorInstance::construct(&mut adopted, grants, wasi_budget,
        started, Cursor { stage: SwiftRunStage::Initialization, function: None, offset: None }));
    let instance = match constructed.take().expect("one constructor result") {
        Ok(instance) => instance,
        Err(ConstructionFailure::Rejected(failure)) => {
            let (mut control, proof) = adopted.take().expect("rejected constructor retains pair");
            let _ = control.drop_proof(proof);
            report.after_cleanup = Some(control.finish_owned_cleanup(None));
            report.terminal = Some(failure);
            report.cleanup_completed = clean(report.after_cleanup);
            return report;
        }
        Err(ConstructionFailure::Cleanup(tail)) => {
            tail.complete((adopted, constructed), &mut report.terminal, &mut report.after_cleanup);
            report.cleanup_completed = clean(report.after_cleanup);
            return report;
        }
    };
    drop((adopted, constructed));
    let mut owned = Some(instance);
    let (failure, frames_clean) = frame_operations::command_execution::run(owned.as_mut().unwrap(), function);
    report.terminal = failure;
    {
        let wasi = owned.as_ref().unwrap().wasi.as_ref().unwrap();
        report.calls_by_function = wasi.calls_by_function();
        report.output_error = stdout.write_all(wasi.stdout()).is_err();
        report.output_error |= stderr.write_all(wasi.stderr()).is_err();
    }
    if !frames_clean {
        // No false zero reservation receipt: the report stays incomplete. Dropping
        // this one-shot Rust owner still consumes its in-process allocations.
        drop(owned);
        return report;
    }
    let mut returned = Some(SwiftReactorInstance::cleanup_owned(&mut owned));
    match returned.take().expect("one cleanup result") {
        Ok(tail) => {
            let mut terminal = None;
            tail.complete((owned, returned), &mut terminal, &mut report.after_cleanup);
            if report.terminal.is_none() { report.terminal = terminal; }
            report.cleanup_completed = clean(report.after_cleanup);
        }
        Err(failure) => {
            if report.terminal.is_none() { report.terminal = Some(failure); }
            drop((owned, returned));
        }
    }
    report
}
fn clean(usage: Option<SwiftRunUsage>) -> bool {
    usage.is_some_and(|u| u.reservations.combined.current == 0
        && u.reservations.live_tickets == 0 && u.cleanup_invariant.is_none()
        && u.live.frames.current == 0 && u.live.active_pins.current == 0
        && u.live.values.current == 0 && u.live.controls.current == 0
        && u.live.memory_pages.current == 0)
}
