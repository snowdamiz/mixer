//! Isolated contract/type/lifetime proposal only. Never linked into product.
#![allow(dead_code, clippy::result_large_err)]
use super::*;
use std::convert::Infallible;
use std::ops::ControlFlow;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum FrameDisposition { Idle, Active, Draining, Retained, RestorePending }
#[derive(Clone, Copy)]
pub(super) struct FrameBound { pub previous: usize, pub admitted: usize }
pub(super) struct FrameCleanupState {
    pub disposition: FrameDisposition,
    pub bound: Option<FrameBound>,
    pub unvisited: usize,
    pub nested_restore: Option<usize>,
    pub entry: Option<EntryGuard>,
}
impl FrameCleanupState {
    pub(super) const fn empty() -> Self {
        Self { disposition: FrameDisposition::Idle, bound: None, unvisited: 0, nested_restore: None, entry: None }
    }
}
#[must_use = "The actual State owns every pin; the recorded envelope remains until explicit completion"]
pub(super) struct FrameOperationPhase<'a> {
    pub phase: ExecutionOperationPhase<'a>,
    pub cleanup: &'a mut FrameCleanupState,
    pub lifecycle: &'a mut Lifecycle,
}
pub(super) struct PinAttempt {
    pub pin: Option<SwiftFunctionPin>,
    pub failure: Option<SwiftRunFailure>,
    pub nested_restore: Option<usize>,
}
#[derive(Clone, Copy)]
pub(super) struct FrameScalars {
    pub function: u32, pub pc: usize, pub base: usize, pub operands: usize,
    pub controls: usize, pub result: bool,
}
#[derive(Clone, Copy)]
pub(super) enum FrameReturn { CallerContinues, Outermost(Option<Value>) }
#[derive(Clone, Copy)]
pub(super) struct FrameDrainReport {
    pub retained_frames: usize,
    pub retained_entry: bool,
    pub live: SwiftLiveUsage,
    pub cache_pins: usize,
    pub first_failure: Option<SwiftRunFailure>,
}
#[derive(Clone, Copy)]
pub(super) enum FrameCompletion {
    Completed,
    Retained(FrameDrainReport),
    RestoreRejected(FrameDrainReport),
}
/// Exact fixed caller storage. No generic T at this boundary.
pub(super) struct FrameOperationStorage<'a> {
    pub preparation: Option<Result<FrameOperationPhase<'a>, SwiftRunFailure>>,
    pub entry: Option<Result<(), SwiftRunFailure>>,
    pub returned: Option<Result<FrameReturn, SwiftRunFailure>>,
    pub drained: Option<FrameDrainReport>,
}

// Signature freeze only. These bodies intentionally do not implement product behavior.
impl SwiftReactorInstance {
    pub(super) fn prepare_frames(&mut self, _: Cursor) -> Result<FrameOperationPhase<'_>, SwiftRunFailure> {
        unimplemented!("contract only")
    }
    pub(super) fn resume_frame_cleanup(&mut self) -> Result<FrameOperationPhase<'_>, SwiftRunFailure> {
        unimplemented!("contract only")
    }
}
impl<'a> FrameOperationPhase<'a> {
    pub(super) fn enter(&mut self, _: u32) -> Result<(), SwiftRunFailure> { unimplemented!("contract only") }
    pub(super) fn finish(&mut self) -> Result<FrameReturn, SwiftRunFailure> { unimplemented!("contract only") }
    pub(super) fn drain(&mut self) -> FrameDrainReport { unimplemented!("contract only") }
    pub(super) fn complete(self, _: FrameOperationStorage<'a>) -> FrameCompletion { unimplemented!("contract only") }
}

/// Never called. Real cache types/APIs prove the short phase ends before the
/// acquired authority and optional completion failure are returned together.
fn acquire_pin_lifetime_witness(
    parts: &mut ExecutionParts<'_, SwiftMode>,
    operation: &mut SwiftExecutionOperation<'_>, function: u32,
) -> PinAttempt {
    let frame_bound = operation.control.usage(Some(operation.wasi.usage())).reservations.construction.current;
    let mut preparation = Some(parts.cache.prepare_operation(
        operation.control, Some(&*operation.wasi), operation.cursor));
    match preparation.take().expect("occupied local slot") {
        Err(failure) => PinAttempt { pin: None, failure: Some(failure), nested_restore: None },
        Ok(mut phase) => {
            let mut returned = Some(phase.pin(parts.cache, function));
            let (pin, mut failure) = match returned.take().expect("occupied local slot") {
                Ok(pin) => (Some(pin), None),
                Err(failure) => (None, Some(failure)),
            };
            let completion = phase.complete((preparation, returned));
            let nested_restore = if completion.is_err() { Some(frame_bound) } else { None };
            if let Err(completion_failure) = completion {
                failure = failure.or(Some(completion_failure));
            }
            PinAttempt { pin, failure, nested_restore }
        }
    }
}

/// Never called. A rejected release reconstitutes the SAME moved actual frame
/// and SAME pin at the SAME index; no clone/new/PinToken constructor exists here.
/// Successful lower removals shift a retained suffix, never the next prefix.
fn drain_frame_transfer_witness(
    parts: &mut ExecutionParts<'_, SwiftMode>,
    operation: &mut SwiftExecutionOperation<'_>, unvisited: &mut usize,
) {
    while *unvisited != 0 {
        *unvisited -= 1;
        let index = *unvisited;
        let frame = parts.frames.remove(index);
        let SwiftFrame { function, pc, base, operands, controls, result, pin } = frame;
        match parts.cache.release(pin, operation.control, Some(&*operation.wasi)) {
            Ok(()) => {
                // Failure here retains conservative count and does not stop drain.
                let _removed = operation.control.remove_live_with_wasi(
                    Live::Frames, 1, Some(operation.wasi.usage()));
            }
            Err(rejected) => {
                let _failure = rejected.failure;
                let pin = rejected.into_pin();
                parts.frames.insert(index, SwiftFrame { function, pc, base, operands, controls, result, pin });
            }
        }
    }
}

fn original_state_borrow_witness(instance: &mut SwiftReactorInstance, cursor: Cursor) -> FrameOperationPhase<'_> {
    // Never called. Demonstrates disjoint actual owner field borrows, no cloned owner.
    let state = instance.state.as_mut().unwrap();
    FrameOperationPhase {
        phase: ExecutionOperationPhase {
            parts: ExecutionParts { cache: instance.cache.as_mut().unwrap(),
                memory: &mut state.memory, table: &mut state.table, globals: &mut state.globals,
                values: &mut state.values, controls: &mut state.controls, frames: &mut state.frames },
            operation: SwiftExecutionOperation { control: instance.control.as_mut().unwrap(),
                wasi: instance.wasi.as_mut().unwrap(), cursor },
            previous_bound: 0, // Type witness only; production must use recorded exact bound.
        },
        cleanup: &mut state.frame_cleanup,
        lifecycle: &mut instance.lifecycle,
    }
}

// INVENTORY_INSERTION_POINT

pub(super) fn print_contract_layout() {
    macro_rules! ty { ($t:ty) => { println!("AF_TYPE {} {} {}", stringify!($t), size_of::<$t>(), std::mem::align_of::<$t>()); }; }
    ty!(FrameCleanupState); ty!(FrameOperationPhase<'static>); ty!(FrameBound);
    ty!(PinAttempt); ty!(FrameScalars); ty!(FrameReturn); ty!(FrameDrainReport);
    ty!(FrameCompletion); ty!(FrameOperationStorage<'static>);
    ty!(PermanentPositions); ty!(ActivePositions);
    println!("AF_BOUNDS {} {}", PERMANENT_BYTES, ACTIVE_BYTES);
    // INVENTORY_PRINT_POINT
}
