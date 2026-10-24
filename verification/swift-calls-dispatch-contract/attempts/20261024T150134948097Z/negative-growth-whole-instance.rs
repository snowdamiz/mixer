//! UNCALLED type/borrow witness only; no accounting or runtime acceptance.
use super::*;
use super::memory_growth_operations::{self as growth, SwiftGrowthContext, SwiftGrowthStorage, GrowthCompletion};

fn pop_checked(phase: &mut FrameOperationPhase<'_>) -> Result<Value, SwiftRunFailure> {
    let before = phase.phase.parts.values.len();
    let outcome = phase.phase.pop_value();
    if outcome.is_err() && phase.phase.parts.values.len() != before {
        phase.cleanup.live_unreconciled = true;
    }
    outcome
}
fn typed_i32(phase: &mut FrameOperationPhase<'_>) -> Result<i32, SwiftRunFailure> {
    match pop_checked(phase)? {
        Value::I32(n) => Ok(n),
        _ => Err(phase.invariant("calls_probe_selector_type")),
    }
}
fn call_defined(phase: &mut FrameOperationPhase<'_>, function: u32) -> Result<(), SwiftRunFailure> {
    let parameters = phase.phase.parts.cache.proof().execution_signature(function).map(|signature| signature.params.len())
        .ok_or_else(|| phase.invariant("calls_probe_signature"))?;
    phase.work(parameters)?;
    // Actual enter rechecks ordered types, caller floor, capacity and depth,
    // retains acquired authority on failed completion, and publishes the frame.
    phase.enter(function)
}
fn call_selected(phase: &mut FrameOperationPhase<'_>, function: u32,
    storage: &mut FrameOperationStorage<'_>) -> Result<(), SwiftRunFailure> {
    if (function as usize) < phase.phase.parts.cache.proof().execution_imports().len() {
        // host_operation already owns the params work; do not charge it twice.
        phase.host_operation(function, &mut storage.entry)?;
        match storage.entry.as_ref().expect("published host result") {
            Ok(()) => { storage.entry.take(); Ok(()) },
            Err(failure) => Err(*failure),
        }
    } else { call_defined(phase, function) }
}
fn indirect(phase: &mut FrameOperationPhase<'_>, index: u32,
    storage: &mut FrameOperationStorage<'_>) -> Result<(), SwiftRunFailure> {
    let selector = typed_i32(phase)? as u32 as usize;
    let function = phase.phase.parts.table.get(selector).copied()
        .ok_or_else(|| phase.invariant("calls_probe_table_oob"))?
        .ok_or_else(|| phase.invariant("calls_probe_table_null"))?;
    let scan = {
        let expected = match phase.phase.parts.cache.proof().execution_type(index) {
            Some(expected) => expected, None => return Err(phase.invariant("calls_probe_expected_type")),
        };
        let actual = match phase.phase.parts.cache.proof().execution_signature(function) {
            Some(actual) => actual, None => return Err(phase.invariant("calls_probe_actual_type")),
        };
        let scan = expected.params.len().checked_add(actual.params.len());
        scan.ok_or_else(|| phase.invariant("calls_probe_scan_overflow"))?
    };
    phase.work(scan)?;
    if phase.phase.parts.cache.proof().execution_type(index)
        != phase.phase.parts.cache.proof().execution_signature(function) {
        return Err(phase.invariant("calls_probe_type_mismatch"));
    }
    call_selected(phase, function, storage)
}
fn fetch(phase: &mut FrameOperationPhase<'_>) -> Result<SelectedInstruction, SwiftRunFailure> {
    phase.active()?;
    let (function, instruction, branch_target) = {
        let frame = match phase.phase.parts.frames.last() {
            Some(frame) => frame, None => return Err(phase.invariant("calls_probe_frame")),
        };
        let view = phase.phase.parts.cache.view(&frame.pin, phase.phase.operation.control,
            Some(&*phase.phase.operation.wasi))?;
        let instruction = match view.instructions.get(frame.pc).copied() {
            Some(instruction) => instruction, None => return Err(phase.invariant("calls_probe_instruction")),
        };
        let branch_target = if let Operation::BrTable { first, count, default } = instruction.operation {
            let selector = match phase.phase.parts.values.last() {
                Some(Value::I32(n)) => *n as u32 as usize,
                _ => return Err(phase.invariant("calls_probe_br_table_selector")),
            };
            Some(if selector < count {
                let at = match first.checked_add(selector) { Some(at) => at, None => return Err(phase.invariant("calls_probe_branch_index")) };
                match view.branch_targets.get(at).copied() { Some(target) => target, None => return Err(phase.invariant("calls_probe_branch_bound")) }
            } else { default })
        } else { None };
        (frame.function, instruction, branch_target)
    };
    let cursor = Cursor { stage: SwiftRunStage::Invocation, function: Some(function), offset: Some(instruction.offset) };
    Ok(SelectedInstruction { instruction, branch_target, cursor })
}
fn local_slot(phase: &mut FrameOperationPhase<'_>, index: u32) -> Result<usize, SwiftRunFailure> {
    let frame = match phase.phase.parts.frames.last() { Some(frame) => frame, None => return Err(phase.invariant("calls_probe_local_frame")) };
    frame.base.checked_add(index as usize).filter(|at| *at < frame.operands && *at < phase.phase.parts.values.len())
        .ok_or_else(|| phase.invariant("calls_probe_local_slot"))
}
fn step<'a>(phase: &mut FrameOperationPhase<'a>, context: &mut SwiftGrowthContext<'a>,
    pending: &mut SwiftGrowthStorage, storage: &mut FrameOperationStorage<'a>) -> Result<bool, SwiftRunFailure> {
    let selected = fetch(phase)?;
    phase.phase.operation.cursor = selected.cursor;
    phase.phase.operation.control.instruction_with_wasi(selected.cursor, Some(phase.phase.operation.wasi.usage()))?;
    phase.work(1)?;
    let pc = phase.phase.parts.frames.last().and_then(|frame| frame.pc.checked_add(1))
        .ok_or_else(|| phase.invariant("calls_probe_pc"))?;
    phase.phase.parts.frames.last_mut().expect("actual caller").pc = pc;
    match selected.instruction.operation {
        Operation::Unreachable => return Err(phase.invariant("calls_probe_unreachable")),
        Operation::Nop => {},
        Operation::Const(value) => phase.phase.push_value(value)?,
        Operation::Drop => { pop_checked(phase)?; },
        Operation::Select => {
            let condition = typed_i32(phase)?;
            let b = pop_checked(phase)?;
            let a = pop_checked(phase)?;
            phase.phase.push_value(if condition != 0 { a } else { b })?;
        },
        Operation::LocalGet(index) => {
            let slot = local_slot(phase, index)?;
            let value = phase.phase.parts.values[slot];
            phase.phase.push_value(value)?;
        },
        Operation::LocalSet(index) | Operation::LocalTee(index) => {
            let value = if matches!(selected.instruction.operation, Operation::LocalTee(_)) {
                phase.work(1)?;
                phase.phase.parts.values.last().copied().ok_or_else(|| phase.invariant("calls_probe_tee_empty"))?
            } else { pop_checked(phase)? };
            let slot = local_slot(phase, index)?;
            phase.phase.parts.values[slot] = value;
        },
        Operation::GlobalGet(index) => {
            let value = phase.phase.parts.globals.get(index as usize).copied()
                .ok_or_else(|| phase.invariant("calls_probe_global"))?;
            phase.phase.push_value(value)?;
        },
        Operation::GlobalSet(index) => {
            let value = pop_checked(phase)?;
            let (mutable, ty) = phase.phase.parts.cache.proof().execution_global(index as usize).map(|descriptor| (descriptor.mutable, descriptor.ty))
                .ok_or_else(|| phase.invariant("calls_probe_global"))?;
            if !mutable || ty != value.ty() { return Err(phase.invariant("calls_probe_global_type")); }
            match phase.phase.parts.globals.get_mut(index as usize) {
                Some(slot) => *slot = value, None => return Err(phase.invariant("calls_probe_global_slot")),
            };
        },
        operation @ (Operation::Block { .. } | Operation::Else { .. } | Operation::End |
            Operation::Br(_) | Operation::BrIf(_) | Operation::BrTable { .. } | Operation::Return) => {
            return phase.control_operation(operation, selected.branch_target);
        },
        Operation::Call(function) => call_selected(phase, function, storage)?,
        Operation::CallIndirect(index) => indirect(phase, index, storage)?,
        operation @ (Operation::Load { .. } | Operation::Store { .. }) => phase.memory_operation(operation, &mut storage.entry)?,
        operation @ (Operation::MemoryCopy | Operation::MemoryFill | Operation::MemorySize) => phase.bulk_memory_operation(operation, &mut storage.entry)?,
        operation @ Operation::MemoryGrow => growth::growth_operation(phase, context, pending, operation, &mut storage.entry)?,
        Operation::Numeric(opcode) => phase.phase.numeric_value(opcode, false)?,
        Operation::Saturating(opcode) => phase.phase.numeric_value(opcode, true)?,
    }
    if let Some(Err(failure)) = storage.entry { return Err(failure); }
    storage.entry.take();
    Ok(false)
}
// A full private loop is typechecked but never executed by this contract packet.
fn run<'a>(phase: &mut FrameOperationPhase<'a>, context: &mut SwiftGrowthContext<'a>,
    pending: &mut SwiftGrowthStorage, storage: &mut FrameOperationStorage<'a>) -> Result<(), SwiftRunFailure> {
    if storage.entry.is_some() || storage.returned.is_some() || storage.controlled.is_some() || storage.drained.is_some() || storage.preparation.is_some() {
        let error = phase.invariant("calls_probe_occupied"); phase.terminal(); return Err(error);
    }
    let outcome = (|| loop {
        if step(phase, context, pending, storage)? {
            match phase.finish()? {
                FrameReturn::CallerContinues => {},
                outer @ FrameReturn::Outermost(_) => break Ok(outer),
            }
        }
    })();
    if outcome.is_err() { phase.terminal(); }
    storage.returned = Some(outcome);
    Ok(())
}
fn complete<'a>(phase: FrameOperationPhase<'a>, context: SwiftGrowthContext<'a>,
    pending: SwiftGrowthStorage, storage: FrameOperationStorage<'a>,
    preparation: Option<Result<(FrameOperationPhase<'a>, SwiftGrowthContext<'a>), SwiftRunFailure>>) -> GrowthCompletion<'a> {
    growth::complete_growth(phase, context, pending, storage, preparation)
}

fn bad(instance:&mut SwiftReactorInstance,cursor:Cursor)->Result<(),SwiftRunFailure>{let(mut phase,context)=instance.prepare_growth(cursor)?;let _other=instance.prepare_frames(cursor)?;phase.enter(34)?;drop(context);Ok(())}
