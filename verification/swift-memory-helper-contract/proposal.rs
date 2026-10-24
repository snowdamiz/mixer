//! Compiling prerequisite only: private original-owner memory Load/Store seam.
//! No dispatcher, Ready/public route, target invocation, or runtime qualification.
#![allow(dead_code, clippy::result_large_err)]
use super::*;
use crate::experimental::execution::width;

macro_rules! swift_memory_leaf {
    (pop $s:ident) => { $s.memory_pop_value() };
    (pop32 $s:ident) => { $s.memory_pop32() };
    (push $s:ident, $v:expr) => { $s.phase.push_value($v) };
    (memory $s:ident) => { $s.phase.parts.memory };
    (invariant $s:ident) => { $s.invariant("swift_memory_invariant") };
    (trap $s:ident) => { $s.memory_trap() };
}

impl FrameOperationPhase<'_> {
    crate::experimental::execution::borrowed::shared_memory_methods!(
        self, SwiftRunFailure, swift_memory_leaf, (mut), memory_range,
        memory_load, memory_store
    );

    fn memory_trap(&mut self) -> SwiftRunFailure {
        self.phase.operation.control.fail(
            self.phase.operation.cursor,
            Fault::new(SwiftRunFailureKind::GuestTrap, "memory_out_of_bounds"),
            Some(self.phase.operation.wasi.usage()),
        )
    }

    fn memory_pop_value(&mut self) -> Result<Value, SwiftRunFailure> {
        let before = self.phase.parts.values.len();
        let result = self.phase.pop_value();
        if result.is_err() && self.phase.parts.values.len() != before {
            self.cleanup.live_unreconciled = true;
        }
        result
    }

    fn memory_pop32(&mut self) -> Result<i32, SwiftRunFailure> {
        match self.memory_pop_value()? {
            Value::I32(value) => Ok(value),
            _ => Err(self.invariant("swift_memory_address_type")),
        }
    }

    fn memory_preflight(&mut self, opcode: u8, store: bool) -> Result<(), SwiftRunFailure> {
        let expected = if store {
            match opcode {
                0x36 | 0x3a | 0x3b => crate::Type::I32,
                0x37 | 0x3c | 0x3d | 0x3e => crate::Type::I64,
                0x38 => crate::Type::F32,
                0x39 => crate::Type::F64,
                _ => return Err(self.memory_unsupported()),
            }
        } else {
            if !(0x28..=0x35).contains(&opcode) {
                return Err(self.memory_unsupported());
            }
            crate::Type::I32
        };
        let frame = match self.phase.parts.frames.last() {
            Some(frame) => frame,
            None => return Err(self.invariant("swift_memory_frame_missing")),
        };
        let floor = frame.operands;
        if frame.base > floor || frame.controls > self.phase.parts.controls.len() {
            return Err(self.invariant("swift_memory_frame_floor"));
        }
        let available = match self.phase.parts.values.len().checked_sub(floor) {
            Some(available) => available,
            None => return Err(self.invariant("swift_memory_operand_floor")),
        };
        let count = if store { 2 } else { 1 };
        if available < count {
            return Err(self.invariant("swift_memory_operand_count"));
        }
        let length = self.phase.parts.values.len();
        if self.phase.parts.values[length - 1].ty() != expected
            || (store && self.phase.parts.values[length - 2].ty() != crate::Type::I32)
        {
            return Err(self.invariant("swift_memory_operand_type"));
        }
        Ok(())
    }

    fn memory_unsupported(&mut self) -> SwiftRunFailure {
        self.phase.operation.control.fail(
            self.phase.operation.cursor,
            Fault::new(SwiftRunFailureKind::UnsupportedEnvironment, "swift_memory_unsupported_operation"),
            Some(self.phase.operation.wasi.usage()),
        )
    }

    /// Atomic fixed-slot publication. Ok means a result was published; the
    /// actual Load/Store success/failure is retained in `returned` for completion.
    /// Occupied slots are preserved and return Err before operation mutation.
    pub(crate) fn memory_operation(
        &mut self,
        operation: Operation,
        returned: &mut Option<Result<(), SwiftRunFailure>>,
    ) -> Result<(), SwiftRunFailure> {
        if returned.is_some() {
            let failure = self.invariant("swift_memory_result_occupied");
            self.terminal();
            return Err(failure);
        }
        let result = self.memory_operation_inner(operation);
        if result.is_err() {
            self.terminal();
        }
        *returned = Some(result);
        Ok(())
    }

    fn memory_operation_inner(&mut self, operation: Operation) -> Result<(), SwiftRunFailure> {
        self.active()?;
        match operation {
            Operation::Load { opcode, offset } => {
                self.memory_preflight(opcode, false)?;
                self.memory_load(opcode, offset)
            }
            Operation::Store { opcode, offset } => {
                self.memory_preflight(opcode, true)?;
                self.memory_store(opcode, offset)
            }
            _ => Err(self.memory_unsupported()),
        }
    }
}

/// Uncalled compiling caller witness. Binds the fixed slot, selected actual
/// pinned instruction, original fuel/work/pc boundary and short reborrows.
/// A behavior lane must execute/adversarially test this boundary separately.
fn memory_pinned_caller_prerequisite<'owner>(
    phase: &mut FrameOperationPhase<'owner>,
    storage: &mut FrameOperationStorage<'owner>,
) -> Result<(), SwiftRunFailure> {
    // This precedes cache view, cursor publication, any debit and pc update.
    if storage.entry.is_some() {
        let failure = phase.invariant("swift_memory_result_occupied");
        phase.terminal();
        return Err(failure);
    }
    phase.active()?;
    let selected = {
        let frame = match phase.phase.parts.frames.last() {
            Some(frame) => frame,
            None => return Err(phase.invariant("swift_memory_caller_frame")),
        };
        let view = phase.phase.parts.cache.view(
            &frame.pin, phase.phase.operation.control,
            Some(&*phase.phase.operation.wasi),
        )?;
        let instruction = match view.instructions.get(frame.pc) {
            Some(instruction) => *instruction,
            None => return Err(phase.invariant("swift_memory_caller_instruction")),
        };
        (frame.function, instruction)
    };
    let (function, instruction) = selected;
    // Install the actual decoded cursor before any opcode rejection.
    phase.phase.operation.cursor = Cursor {
        stage: SwiftRunStage::Invocation,
        function: Some(function), offset: Some(instruction.offset),
    };
    // The actual decoded operation is never synthesized by the caller.
    match instruction.operation {
        Operation::Load { opcode: 0x28..=0x35, .. }
        | Operation::Store { opcode: 0x36..=0x3e, .. } => {},
        _ => {
            let failure = phase.memory_unsupported();
            phase.terminal();
            storage.entry = Some(Err(failure));
            return Ok(());
        }
    }
    let charged = phase.phase.operation.control.instruction_with_wasi(
        phase.phase.operation.cursor, Some(phase.phase.operation.wasi.usage()),
    ).and_then(|()| phase.work(1));
    if let Err(failure) = charged {
        phase.terminal();
        storage.entry = Some(Err(failure));
        return Ok(());
    }
    let pc = match phase.phase.parts.frames.last().and_then(|frame| frame.pc.checked_add(1)) {
        Some(pc) => pc,
        None => {
            let failure = phase.invariant("swift_memory_caller_pc");
            phase.terminal();
            storage.entry = Some(Err(failure));
            return Ok(());
        }
    };
    phase.phase.parts.frames.last_mut().expect("active original frame").pc = pc;
    phase.memory_operation(instruction.operation, &mut storage.entry)?;
    // A future loop must inspect the stored outcome before it fetches again.
    // This witness retains it in fixed storage for the existing completion API.
    Ok(())
}

// ACCOUNTING_START
struct PermanentPositions {}
struct ActivePositions {}
pub(in crate::experimental_swift_reactor::execution) const PERMANENT_BYTES: usize = size_of::<PermanentPositions>();
pub(super) const ACTIVE_BYTES: usize = size_of::<ActivePositions>();
