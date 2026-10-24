//! Compiling prerequisite only: private original-owner memory Load/Store seam.
//! No dispatcher, Ready/public route, target invocation, or runtime qualification.
#![allow(dead_code, clippy::result_large_err)]
use super::*;
use crate::experimental::execution::width;

macro_rules! swift_memory_leaf {
    (pop $s:ident) => { $s.memory_pop_value() };
    (pop32 $s:ident) => { $s.memory_pop32() };
    (push $s:ident, $v:expr) => { $s.memory_push_value($v) };
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

    fn memory_push_value(&mut self, value: Value) -> Result<(), SwiftRunFailure> {
        #[cfg(test)]
        let old = super::tests::before_result_push(self.phase.operation.control);
        let result = self.phase.push_value(value);
        #[cfg(test)]
        super::tests::after_result_push(self.phase.operation.control, old);
        result
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

/// Bounded one-step actual pinned caller. Outer success means publication only.
/// No fetch can follow an occupied result; the caller takes successful outcomes
/// before reuse and retains a failure through terminal drain and completion.
fn memory_pinned_caller_prerequisite<'owner>(
    phase: &mut FrameOperationPhase<'owner>,
    storage: &mut FrameOperationStorage<'owner>,
) -> Result<(), SwiftRunFailure> {
    if storage.entry.is_some() {
        let failure = phase.invariant("swift_memory_result_occupied");
        phase.terminal();
        return Err(failure);
    }
    let result = memory_pinned_step(phase);
    if result.is_err() { phase.terminal(); }
    storage.entry = Some(result);
    Ok(())
}

fn memory_pinned_step(phase: &mut FrameOperationPhase<'_>) -> Result<(), SwiftRunFailure> {
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
    phase.phase.operation.cursor = Cursor {
        stage: SwiftRunStage::Invocation,
        function: Some(function), offset: Some(instruction.offset),
    };
    match instruction.operation {
        Operation::Load { opcode: 0x28..=0x35, .. }
        | Operation::Store { opcode: 0x36..=0x3e, .. } => {},
        _ => return Err(phase.memory_unsupported()),
    }
    phase.phase.operation.control.instruction_with_wasi(
        phase.phase.operation.cursor, Some(phase.phase.operation.wasi.usage()),
    )?;
    phase.work(1)?;
    #[cfg(test)]
    if tests::PC_OVERFLOW.with(std::cell::Cell::get) {
        phase.phase.parts.frames.last_mut().expect("actual frame").pc = usize::MAX;
    }
    let pc = match phase.phase.parts.frames.last().and_then(|frame| frame.pc.checked_add(1)) {
        Some(pc) => pc,
        None => return Err(phase.invariant("swift_memory_caller_pc")),
    };
    phase.phase.parts.frames.last_mut().expect("active original frame").pc = pc;
    phase.memory_operation_inner(instruction.operation)
}

#[cfg(test)]
#[path = "memory_operations_tests.rs"]
mod tests;

// ACCOUNTING_START
struct PermanentPositions {
    source_fixed_memory_caller_storage_source: FrameOperationStorage<'static>,
    source_fixed_memory_caller_storage_argument: FrameOperationStorage<'static>,
    source_fixed_memory_caller_storage_returned: FrameOperationStorage<'static>,
    source_fixed_memory_caller_storage_caller: FrameOperationStorage<'static>,
    source_fixed_memory_caller_slot_source: Option<Result<(), SwiftRunFailure>>,
    source_fixed_memory_caller_slot_argument: Option<Result<(), SwiftRunFailure>>,
    source_fixed_memory_caller_slot_returned: Option<Result<(), SwiftRunFailure>>,
    source_fixed_memory_caller_slot_caller: Option<Result<(), SwiftRunFailure>>,
    source_fixed_memory_caller_result_source: Result<(), SwiftRunFailure>,
    source_fixed_memory_caller_result_argument: Result<(), SwiftRunFailure>,
    source_fixed_memory_caller_result_returned: Result<(), SwiftRunFailure>,
    source_fixed_memory_caller_result_caller: Result<(), SwiftRunFailure>,
    source_fixed_memory_caller_admission_source: Result<(), SwiftRunFailure>,
    source_fixed_memory_caller_admission_argument: Result<(), SwiftRunFailure>,
    source_fixed_memory_caller_admission_returned: Result<(), SwiftRunFailure>,
    source_fixed_memory_caller_admission_caller: Result<(), SwiftRunFailure>,
    source_fixed_memory_caller_failure_source: SwiftRunFailure,
    source_fixed_memory_caller_failure_argument: SwiftRunFailure,
    source_fixed_memory_caller_failure_returned: SwiftRunFailure,
    source_fixed_memory_caller_failure_caller: SwiftRunFailure,
    source_fixed_memory_caller_retained_failure_source: Option<SwiftRunFailure>,
    source_fixed_memory_caller_retained_failure_argument: Option<SwiftRunFailure>,
    source_fixed_memory_caller_retained_failure_returned: Option<SwiftRunFailure>,
    source_fixed_memory_caller_retained_failure_caller: Option<SwiftRunFailure>,
    source_fixed_memory_completion_storage_source: FrameOperationStorage<'static>,
    source_fixed_memory_completion_storage_argument: FrameOperationStorage<'static>,
    source_fixed_memory_completion_storage_returned: FrameOperationStorage<'static>,
    source_fixed_memory_completion_storage_caller: FrameOperationStorage<'static>,
    source_fixed_memory_completion_drop_tuple_source: (ExecutionParts<'static, SwiftMode>, FrameOperationStorage<'static>),
    source_fixed_memory_completion_drop_tuple_argument: (ExecutionParts<'static, SwiftMode>, FrameOperationStorage<'static>),
    source_fixed_memory_completion_drop_tuple_returned: (ExecutionParts<'static, SwiftMode>, FrameOperationStorage<'static>),
    source_fixed_memory_completion_drop_tuple_caller: (ExecutionParts<'static, SwiftMode>, FrameOperationStorage<'static>),
    source_fixed_memory_completion_slot_source: Option<Result<(), SwiftRunFailure>>,
    source_fixed_memory_completion_slot_argument: Option<Result<(), SwiftRunFailure>>,
    source_fixed_memory_completion_slot_returned: Option<Result<(), SwiftRunFailure>>,
    source_fixed_memory_completion_slot_caller: Option<Result<(), SwiftRunFailure>>,
    source_fixed_memory_completion_result_source: Result<(), SwiftRunFailure>,
    source_fixed_memory_completion_result_argument: Result<(), SwiftRunFailure>,
    source_fixed_memory_completion_result_returned: Result<(), SwiftRunFailure>,
    source_fixed_memory_completion_result_caller: Result<(), SwiftRunFailure>,
    source_fixed_memory_completion_admission_source: Result<(), SwiftRunFailure>,
    source_fixed_memory_completion_admission_argument: Result<(), SwiftRunFailure>,
    source_fixed_memory_completion_admission_returned: Result<(), SwiftRunFailure>,
    source_fixed_memory_completion_admission_caller: Result<(), SwiftRunFailure>,
    source_fixed_memory_completion_failure_source: SwiftRunFailure,
    source_fixed_memory_completion_failure_argument: SwiftRunFailure,
    source_fixed_memory_completion_failure_returned: SwiftRunFailure,
    source_fixed_memory_completion_failure_caller: SwiftRunFailure,
    source_fixed_memory_completion_report_source: FrameDrainReport,
    source_fixed_memory_completion_report_argument: FrameDrainReport,
    source_fixed_memory_completion_report_returned: FrameDrainReport,
    source_fixed_memory_completion_report_caller: FrameDrainReport,
}
struct ActivePositions {
    mir_production_0_0_source: usize,
    mir_production_0_0_argument: usize,
    mir_production_0_0_returned: usize,
    mir_production_0_0_caller: usize,
    mir_production_0_1_source: u8,
    mir_production_0_1_argument: u8,
    mir_production_0_1_returned: u8,
    mir_production_0_1_caller: u8,
    alias_production_0_1_0_op_source: u8,
    alias_production_0_1_0_op_argument: u8,
    alias_production_0_1_0_op_returned: u8,
    alias_production_0_1_0_op_caller: u8,
    literal_production_0_0_source: usize,
    literal_production_0_0_argument: usize,
    literal_production_0_0_returned: usize,
    literal_production_0_0_caller: usize,
    literal_production_0_1_source: usize,
    literal_production_0_1_argument: usize,
    literal_production_0_1_returned: usize,
    literal_production_0_1_caller: usize,
    literal_production_0_2_source: usize,
    literal_production_0_2_argument: usize,
    literal_production_0_2_returned: usize,
    literal_production_0_2_caller: usize,
    literal_production_0_3_source: usize,
    literal_production_0_3_argument: usize,
    literal_production_0_3_returned: usize,
    literal_production_0_3_caller: usize,
    mir_production_1_0_source: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_0_argument: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_0_returned: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_0_caller: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_4_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    mir_production_1_4_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    mir_production_1_4_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    mir_production_1_4_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    mir_production_1_5_source: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_5_argument: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_5_returned: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_5_caller: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_6_source: std::option::Option<usize>,
    mir_production_1_6_argument: std::option::Option<usize>,
    mir_production_1_6_returned: std::option::Option<usize>,
    mir_production_1_6_caller: std::option::Option<usize>,
    mir_production_1_7_source: std::option::Option<usize>,
    mir_production_1_7_argument: std::option::Option<usize>,
    mir_production_1_7_returned: std::option::Option<usize>,
    mir_production_1_7_caller: std::option::Option<usize>,
    mir_production_1_8_source: (&'static std::vec::Vec<u8>,),
    mir_production_1_8_argument: (&'static std::vec::Vec<u8>,),
    mir_production_1_8_returned: (&'static std::vec::Vec<u8>,),
    mir_production_1_8_caller: (&'static std::vec::Vec<u8>,),
    mir_production_1_9_source: &'static std::vec::Vec<u8>,
    mir_production_1_9_argument: &'static std::vec::Vec<u8>,
    mir_production_1_9_returned: &'static std::vec::Vec<u8>,
    mir_production_1_9_caller: &'static std::vec::Vec<u8>,
    mir_production_1_10_source: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_1_10_argument: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_1_10_returned: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_1_10_caller: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_1_11_source: isize,
    mir_production_1_11_argument: isize,
    mir_production_1_11_returned: isize,
    mir_production_1_11_caller: isize,
    mir_production_1_12_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_12_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_12_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_12_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_12_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_12_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_12_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_12_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_13_source: usize,
    mir_production_1_13_argument: usize,
    mir_production_1_13_returned: usize,
    mir_production_1_13_caller: usize,
    alias_production_1_13_0_end_source: usize,
    alias_production_1_13_0_end_argument: usize,
    alias_production_1_13_0_end_returned: usize,
    alias_production_1_13_0_end_caller: usize,
    alias_production_1_13_1_val_source: usize,
    alias_production_1_13_1_val_argument: usize,
    alias_production_1_13_1_val_returned: usize,
    alias_production_1_13_1_val_caller: usize,
    mir_production_1_14_source: std::ops::Range<usize>,
    mir_production_1_14_argument: std::ops::Range<usize>,
    mir_production_1_14_returned: std::ops::Range<usize>,
    mir_production_1_14_caller: std::ops::Range<usize>,
    mir_production_1_15_source: &'static mut std::vec::Vec<u8>,
    mir_production_1_15_argument: &'static mut std::vec::Vec<u8>,
    mir_production_1_15_returned: &'static mut std::vec::Vec<u8>,
    mir_production_1_15_caller: &'static mut std::vec::Vec<u8>,
    mir_production_1_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_1_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_1_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_1_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_1_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_1_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_1_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_1_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_1_2_source: usize,
    mir_production_1_2_argument: usize,
    mir_production_1_2_returned: usize,
    mir_production_1_2_caller: usize,
    alias_production_1_2_0_address_source: usize,
    alias_production_1_2_0_address_argument: usize,
    alias_production_1_2_0_address_returned: usize,
    alias_production_1_2_0_address_caller: usize,
    mir_production_1_3_source: usize,
    mir_production_1_3_argument: usize,
    mir_production_1_3_returned: usize,
    mir_production_1_3_caller: usize,
    alias_production_1_3_0_len_source: usize,
    alias_production_1_3_0_len_argument: usize,
    alias_production_1_3_0_len_returned: usize,
    alias_production_1_3_0_len_caller: usize,
    mir_production_2_0_source: bool,
    mir_production_2_0_argument: bool,
    mir_production_2_0_returned: bool,
    mir_production_2_0_caller: bool,
    mir_production_2_3_source: usize,
    mir_production_2_3_argument: usize,
    mir_production_2_3_returned: usize,
    mir_production_2_3_caller: usize,
    mir_production_2_4_source: usize,
    mir_production_2_4_argument: usize,
    mir_production_2_4_returned: usize,
    mir_production_2_4_caller: usize,
    mir_production_2_5_source: &'static std::vec::Vec<u8>,
    mir_production_2_5_argument: &'static std::vec::Vec<u8>,
    mir_production_2_5_returned: &'static std::vec::Vec<u8>,
    mir_production_2_5_caller: &'static std::vec::Vec<u8>,
    mir_production_2_1_source: (&'static std::vec::Vec<u8>,),
    mir_production_2_1_argument: (&'static std::vec::Vec<u8>,),
    mir_production_2_1_returned: (&'static std::vec::Vec<u8>,),
    mir_production_2_1_caller: (&'static std::vec::Vec<u8>,),
    mir_production_2_2_source: &'static usize,
    mir_production_2_2_argument: &'static usize,
    mir_production_2_2_returned: &'static usize,
    mir_production_2_2_caller: &'static usize,
    alias_production_2_2_0_end_source: &'static usize,
    alias_production_2_2_0_end_argument: &'static usize,
    alias_production_2_2_0_end_returned: &'static usize,
    alias_production_2_2_0_end_caller: &'static usize,
    mir_production_3_0_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_0_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_0_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_0_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_2_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_3_2_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_3_2_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_3_2_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_3_1_source: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_3_1_argument: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_3_1_returned: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_3_1_caller: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_4_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_4_source: usize,
    mir_production_4_4_argument: usize,
    mir_production_4_4_returned: usize,
    mir_production_4_4_caller: usize,
    alias_production_4_4_0_address_source: usize,
    alias_production_4_4_0_address_argument: usize,
    alias_production_4_4_0_address_returned: usize,
    alias_production_4_4_0_address_caller: usize,
    mir_production_4_5_source: u32,
    mir_production_4_5_argument: u32,
    mir_production_4_5_returned: u32,
    mir_production_4_5_caller: u32,
    mir_production_4_6_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i32>,
    mir_production_4_6_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i32>,
    mir_production_4_6_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i32>,
    mir_production_4_6_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i32>,
    mir_production_4_7_source: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_7_argument: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_7_returned: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_7_caller: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_8_source: isize,
    mir_production_4_8_argument: isize,
    mir_production_4_8_returned: isize,
    mir_production_4_8_caller: isize,
    mir_production_4_9_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_9_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_9_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_9_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_4_9_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_4_9_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_4_9_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_4_9_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_10_source: i32,
    mir_production_4_10_argument: i32,
    mir_production_4_10_returned: i32,
    mir_production_4_10_caller: i32,
    alias_production_4_10_0_val_source: i32,
    alias_production_4_10_0_val_argument: i32,
    alias_production_4_10_0_val_returned: i32,
    alias_production_4_10_0_val_caller: i32,
    mir_production_4_12_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    mir_production_4_12_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    mir_production_4_12_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    mir_production_4_12_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    mir_production_4_13_source: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_13_argument: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_13_returned: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_13_caller: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_14_source: std::option::Option<usize>,
    mir_production_4_14_argument: std::option::Option<usize>,
    mir_production_4_14_returned: std::option::Option<usize>,
    mir_production_4_14_caller: std::option::Option<usize>,
    mir_production_4_15_source: usize,
    mir_production_4_15_argument: usize,
    mir_production_4_15_returned: usize,
    mir_production_4_15_caller: usize,
    mir_production_4_16_source: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_4_16_argument: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_4_16_returned: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_4_16_caller: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_4_17_source: isize,
    mir_production_4_17_argument: isize,
    mir_production_4_17_returned: isize,
    mir_production_4_17_caller: isize,
    mir_production_4_20_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::ops::Range<usize>>,
    mir_production_4_20_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::ops::Range<usize>>,
    mir_production_4_20_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::ops::Range<usize>>,
    mir_production_4_20_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::ops::Range<usize>>,
    mir_production_4_21_source: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_21_argument: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_21_returned: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_21_caller: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_22_source: isize,
    mir_production_4_22_argument: isize,
    mir_production_4_22_returned: isize,
    mir_production_4_22_caller: isize,
    mir_production_4_25_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_4_25_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_4_25_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_4_25_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_4_26_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_26_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_26_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_26_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_27_source: isize,
    mir_production_4_27_argument: isize,
    mir_production_4_27_returned: isize,
    mir_production_4_27_caller: isize,
    mir_production_4_30_source: (),
    mir_production_4_30_argument: (),
    mir_production_4_30_returned: (),
    mir_production_4_30_caller: (),
    mir_production_4_31_source: &'static mut [u8],
    mir_production_4_31_argument: &'static mut [u8],
    mir_production_4_31_returned: &'static mut [u8],
    mir_production_4_31_caller: &'static mut [u8],
    mir_production_4_32_source: &'static mut [u8; 8],
    mir_production_4_32_argument: &'static mut [u8; 8],
    mir_production_4_32_returned: &'static mut [u8; 8],
    mir_production_4_32_caller: &'static mut [u8; 8],
    mir_production_4_33_source: std::ops::RangeTo<usize>,
    mir_production_4_33_argument: std::ops::RangeTo<usize>,
    mir_production_4_33_returned: std::ops::RangeTo<usize>,
    mir_production_4_33_caller: std::ops::RangeTo<usize>,
    mir_production_4_34_source: &'static [u8],
    mir_production_4_34_argument: &'static [u8],
    mir_production_4_34_returned: &'static [u8],
    mir_production_4_34_caller: &'static [u8],
    mir_production_4_35_source: &'static std::vec::Vec<u8>,
    mir_production_4_35_argument: &'static std::vec::Vec<u8>,
    mir_production_4_35_returned: &'static std::vec::Vec<u8>,
    mir_production_4_35_caller: &'static std::vec::Vec<u8>,
    mir_production_4_37_source: [u8; 8],
    mir_production_4_37_argument: [u8; 8],
    mir_production_4_37_returned: [u8; 8],
    mir_production_4_37_caller: [u8; 8],
    mir_production_4_39_source: i32,
    mir_production_4_39_argument: i32,
    mir_production_4_39_returned: i32,
    mir_production_4_39_caller: i32,
    mir_production_4_40_source: i64,
    mir_production_4_40_argument: i64,
    mir_production_4_40_returned: i64,
    mir_production_4_40_caller: i64,
    mir_production_4_41_source: u32,
    mir_production_4_41_argument: u32,
    mir_production_4_41_returned: u32,
    mir_production_4_41_caller: u32,
    mir_production_4_42_source: i32,
    mir_production_4_42_argument: i32,
    mir_production_4_42_returned: i32,
    mir_production_4_42_caller: i32,
    mir_production_4_43_source: i8,
    mir_production_4_43_argument: i8,
    mir_production_4_43_returned: i8,
    mir_production_4_43_caller: i8,
    mir_production_4_44_source: i32,
    mir_production_4_44_argument: i32,
    mir_production_4_44_returned: i32,
    mir_production_4_44_caller: i32,
    mir_production_4_45_source: u8,
    mir_production_4_45_argument: u8,
    mir_production_4_45_returned: u8,
    mir_production_4_45_caller: u8,
    mir_production_4_46_source: i32,
    mir_production_4_46_argument: i32,
    mir_production_4_46_returned: i32,
    mir_production_4_46_caller: i32,
    mir_production_4_47_source: i16,
    mir_production_4_47_argument: i16,
    mir_production_4_47_returned: i16,
    mir_production_4_47_caller: i16,
    mir_production_4_48_source: i32,
    mir_production_4_48_argument: i32,
    mir_production_4_48_returned: i32,
    mir_production_4_48_caller: i32,
    mir_production_4_49_source: u16,
    mir_production_4_49_argument: u16,
    mir_production_4_49_returned: u16,
    mir_production_4_49_caller: u16,
    mir_production_4_50_source: i64,
    mir_production_4_50_argument: i64,
    mir_production_4_50_returned: i64,
    mir_production_4_50_caller: i64,
    mir_production_4_51_source: i8,
    mir_production_4_51_argument: i8,
    mir_production_4_51_returned: i8,
    mir_production_4_51_caller: i8,
    mir_production_4_52_source: i64,
    mir_production_4_52_argument: i64,
    mir_production_4_52_returned: i64,
    mir_production_4_52_caller: i64,
    mir_production_4_53_source: u8,
    mir_production_4_53_argument: u8,
    mir_production_4_53_returned: u8,
    mir_production_4_53_caller: u8,
    mir_production_4_54_source: i64,
    mir_production_4_54_argument: i64,
    mir_production_4_54_returned: i64,
    mir_production_4_54_caller: i64,
    mir_production_4_55_source: i16,
    mir_production_4_55_argument: i16,
    mir_production_4_55_returned: i16,
    mir_production_4_55_caller: i16,
    mir_production_4_56_source: i64,
    mir_production_4_56_argument: i64,
    mir_production_4_56_returned: i64,
    mir_production_4_56_caller: i64,
    mir_production_4_57_source: u16,
    mir_production_4_57_argument: u16,
    mir_production_4_57_returned: u16,
    mir_production_4_57_caller: u16,
    mir_production_4_58_source: i64,
    mir_production_4_58_argument: i64,
    mir_production_4_58_returned: i64,
    mir_production_4_58_caller: i64,
    mir_production_4_59_source: i32,
    mir_production_4_59_argument: i32,
    mir_production_4_59_returned: i32,
    mir_production_4_59_caller: i32,
    mir_production_4_60_source: i64,
    mir_production_4_60_argument: i64,
    mir_production_4_60_returned: i64,
    mir_production_4_60_caller: i64,
    mir_production_4_61_source: u32,
    mir_production_4_61_argument: u32,
    mir_production_4_61_returned: u32,
    mir_production_4_61_caller: u32,
    mir_production_4_62_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_4_62_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_4_62_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_4_62_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_4_63_source: Value,
    mir_production_4_63_argument: Value,
    mir_production_4_63_returned: Value,
    mir_production_4_63_caller: Value,
    mir_production_4_64_source: &'static mut std::vec::Vec<u8>,
    mir_production_4_64_argument: &'static mut std::vec::Vec<u8>,
    mir_production_4_64_returned: &'static mut std::vec::Vec<u8>,
    mir_production_4_64_caller: &'static mut std::vec::Vec<u8>,
    mir_production_4_11_source: usize,
    mir_production_4_11_argument: usize,
    mir_production_4_11_returned: usize,
    mir_production_4_11_caller: usize,
    alias_production_4_11_0_width_source: usize,
    alias_production_4_11_0_width_argument: usize,
    alias_production_4_11_0_width_returned: usize,
    alias_production_4_11_0_width_caller: usize,
    mir_production_4_18_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_18_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_18_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_18_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_4_18_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_4_18_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_4_18_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_4_18_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_19_source: usize,
    mir_production_4_19_argument: usize,
    mir_production_4_19_returned: usize,
    mir_production_4_19_caller: usize,
    alias_production_4_19_0_start_source: usize,
    alias_production_4_19_0_start_argument: usize,
    alias_production_4_19_0_start_returned: usize,
    alias_production_4_19_0_start_caller: usize,
    alias_production_4_19_1_val_source: usize,
    alias_production_4_19_1_val_argument: usize,
    alias_production_4_19_1_val_returned: usize,
    alias_production_4_19_1_val_caller: usize,
    mir_production_4_23_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_23_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_23_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_23_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_4_23_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_4_23_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_4_23_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_4_23_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_24_source: std::ops::Range<usize>,
    mir_production_4_24_argument: std::ops::Range<usize>,
    mir_production_4_24_returned: std::ops::Range<usize>,
    mir_production_4_24_caller: std::ops::Range<usize>,
    alias_production_4_24_0_range_source: std::ops::Range<usize>,
    alias_production_4_24_0_range_argument: std::ops::Range<usize>,
    alias_production_4_24_0_range_returned: std::ops::Range<usize>,
    alias_production_4_24_0_range_caller: std::ops::Range<usize>,
    alias_production_4_24_1_val_source: std::ops::Range<usize>,
    alias_production_4_24_1_val_argument: std::ops::Range<usize>,
    alias_production_4_24_1_val_returned: std::ops::Range<usize>,
    alias_production_4_24_1_val_caller: std::ops::Range<usize>,
    mir_production_4_28_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_28_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_28_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_28_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_4_28_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_4_28_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_4_28_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_4_28_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_4_29_source: [u8; 8],
    mir_production_4_29_argument: [u8; 8],
    mir_production_4_29_returned: [u8; 8],
    mir_production_4_29_caller: [u8; 8],
    alias_production_4_29_0_padded_source: [u8; 8],
    alias_production_4_29_0_padded_argument: [u8; 8],
    alias_production_4_29_0_padded_returned: [u8; 8],
    alias_production_4_29_0_padded_caller: [u8; 8],
    mir_production_4_36_source: u64,
    mir_production_4_36_argument: u64,
    mir_production_4_36_returned: u64,
    mir_production_4_36_caller: u64,
    alias_production_4_36_0_x_source: u64,
    alias_production_4_36_0_x_argument: u64,
    alias_production_4_36_0_x_returned: u64,
    alias_production_4_36_0_x_caller: u64,
    mir_production_4_38_source: Value,
    mir_production_4_38_argument: Value,
    mir_production_4_38_returned: Value,
    mir_production_4_38_caller: Value,
    alias_production_4_38_0_value_source: Value,
    alias_production_4_38_0_value_argument: Value,
    alias_production_4_38_0_value_returned: Value,
    alias_production_4_38_0_value_caller: Value,
    mir_production_4_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_4_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_4_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_4_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_4_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_4_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_4_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_4_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_4_2_source: u8,
    mir_production_4_2_argument: u8,
    mir_production_4_2_returned: u8,
    mir_production_4_2_caller: u8,
    alias_production_4_2_0_opcode_source: u8,
    alias_production_4_2_0_opcode_argument: u8,
    alias_production_4_2_0_opcode_returned: u8,
    alias_production_4_2_0_opcode_caller: u8,
    mir_production_4_3_source: u32,
    mir_production_4_3_argument: u32,
    mir_production_4_3_returned: u32,
    mir_production_4_3_caller: u32,
    alias_production_4_3_0_offset_source: u32,
    alias_production_4_3_0_offset_argument: u32,
    alias_production_4_3_0_offset_returned: u32,
    alias_production_4_3_0_offset_caller: u32,
    literal_production_4_0_source: u8,
    literal_production_4_0_argument: u8,
    literal_production_4_0_returned: u8,
    literal_production_4_0_caller: u8,
    literal_production_4_1_source: &'static str,
    literal_production_4_1_argument: &'static str,
    literal_production_4_1_returned: &'static str,
    literal_production_4_1_caller: &'static str,
    mir_production_5_0_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_5_0_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_5_0_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_5_0_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_5_2_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_5_2_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_5_2_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_5_2_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_5_1_source: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_5_1_argument: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_5_1_returned: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_5_1_caller: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_6_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_4_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>,
    mir_production_6_4_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>,
    mir_production_6_4_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>,
    mir_production_6_4_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>,
    mir_production_6_5_source: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_5_argument: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_5_returned: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_5_caller: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_6_source: isize,
    mir_production_6_6_argument: isize,
    mir_production_6_6_returned: isize,
    mir_production_6_6_caller: isize,
    mir_production_6_7_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_7_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_7_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_7_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_6_7_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_6_7_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_6_7_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_6_7_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_8_source: Value,
    mir_production_6_8_argument: Value,
    mir_production_6_8_returned: Value,
    mir_production_6_8_caller: Value,
    alias_production_6_8_0_value_source: Value,
    alias_production_6_8_0_value_argument: Value,
    alias_production_6_8_0_value_returned: Value,
    alias_production_6_8_0_value_caller: Value,
    alias_production_6_8_1_val_source: Value,
    alias_production_6_8_1_val_argument: Value,
    alias_production_6_8_1_val_returned: Value,
    alias_production_6_8_1_val_caller: Value,
    mir_production_6_10_source: u32,
    mir_production_6_10_argument: u32,
    mir_production_6_10_returned: u32,
    mir_production_6_10_caller: u32,
    mir_production_6_11_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i32>,
    mir_production_6_11_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i32>,
    mir_production_6_11_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i32>,
    mir_production_6_11_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i32>,
    mir_production_6_12_source: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_12_argument: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_12_returned: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_12_caller: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_13_source: isize,
    mir_production_6_13_argument: isize,
    mir_production_6_13_returned: isize,
    mir_production_6_13_caller: isize,
    mir_production_6_17_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    mir_production_6_17_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    mir_production_6_17_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    mir_production_6_17_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    mir_production_6_18_source: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_18_argument: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_18_returned: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_18_caller: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_19_source: std::option::Option<usize>,
    mir_production_6_19_argument: std::option::Option<usize>,
    mir_production_6_19_returned: std::option::Option<usize>,
    mir_production_6_19_caller: std::option::Option<usize>,
    mir_production_6_20_source: usize,
    mir_production_6_20_argument: usize,
    mir_production_6_20_returned: usize,
    mir_production_6_20_caller: usize,
    mir_production_6_21_source: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_6_21_argument: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_6_21_returned: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_6_21_caller: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_6_22_source: isize,
    mir_production_6_22_argument: isize,
    mir_production_6_22_returned: isize,
    mir_production_6_22_caller: isize,
    mir_production_6_25_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::ops::Range<usize>>,
    mir_production_6_25_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::ops::Range<usize>>,
    mir_production_6_25_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::ops::Range<usize>>,
    mir_production_6_25_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::ops::Range<usize>>,
    mir_production_6_26_source: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_26_argument: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_26_returned: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_26_caller: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_27_source: isize,
    mir_production_6_27_argument: isize,
    mir_production_6_27_returned: isize,
    mir_production_6_27_caller: isize,
    mir_production_6_30_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_6_30_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_6_30_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_6_30_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_6_31_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_31_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_31_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_31_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_32_source: isize,
    mir_production_6_32_argument: isize,
    mir_production_6_32_returned: isize,
    mir_production_6_32_caller: isize,
    mir_production_6_35_source: isize,
    mir_production_6_35_argument: isize,
    mir_production_6_35_returned: isize,
    mir_production_6_35_caller: isize,
    mir_production_6_37_source: u32,
    mir_production_6_37_argument: u32,
    mir_production_6_37_returned: u32,
    mir_production_6_37_caller: u32,
    mir_production_6_41_source: (),
    mir_production_6_41_argument: (),
    mir_production_6_41_returned: (),
    mir_production_6_41_caller: (),
    mir_production_6_42_source: &'static mut [u8],
    mir_production_6_42_argument: &'static mut [u8],
    mir_production_6_42_returned: &'static mut [u8],
    mir_production_6_42_caller: &'static mut [u8],
    mir_production_6_43_source: &'static [u8],
    mir_production_6_43_argument: &'static [u8],
    mir_production_6_43_returned: &'static [u8],
    mir_production_6_43_caller: &'static [u8],
    mir_production_6_44_source: &'static [u8; 8],
    mir_production_6_44_argument: &'static [u8; 8],
    mir_production_6_44_returned: &'static [u8; 8],
    mir_production_6_44_caller: &'static [u8; 8],
    mir_production_6_45_source: [u8; 8],
    mir_production_6_45_argument: [u8; 8],
    mir_production_6_45_returned: [u8; 8],
    mir_production_6_45_caller: [u8; 8],
    mir_production_6_46_source: u64,
    mir_production_6_46_argument: u64,
    mir_production_6_46_returned: u64,
    mir_production_6_46_caller: u64,
    mir_production_6_47_source: std::ops::RangeTo<usize>,
    mir_production_6_47_argument: std::ops::RangeTo<usize>,
    mir_production_6_47_returned: std::ops::RangeTo<usize>,
    mir_production_6_47_caller: std::ops::RangeTo<usize>,
    mir_production_6_48_source: &'static mut std::vec::Vec<u8>,
    mir_production_6_48_argument: &'static mut std::vec::Vec<u8>,
    mir_production_6_48_returned: &'static mut std::vec::Vec<u8>,
    mir_production_6_48_caller: &'static mut std::vec::Vec<u8>,
    mir_production_6_9_source: usize,
    mir_production_6_9_argument: usize,
    mir_production_6_9_returned: usize,
    mir_production_6_9_caller: usize,
    alias_production_6_9_0_address_source: usize,
    alias_production_6_9_0_address_argument: usize,
    alias_production_6_9_0_address_returned: usize,
    alias_production_6_9_0_address_caller: usize,
    mir_production_6_14_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_14_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_14_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_14_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_6_14_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_6_14_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_6_14_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_6_14_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_15_source: i32,
    mir_production_6_15_argument: i32,
    mir_production_6_15_returned: i32,
    mir_production_6_15_caller: i32,
    alias_production_6_15_0_val_source: i32,
    alias_production_6_15_0_val_argument: i32,
    alias_production_6_15_0_val_returned: i32,
    alias_production_6_15_0_val_caller: i32,
    mir_production_6_16_source: usize,
    mir_production_6_16_argument: usize,
    mir_production_6_16_returned: usize,
    mir_production_6_16_caller: usize,
    alias_production_6_16_0_width_source: usize,
    alias_production_6_16_0_width_argument: usize,
    alias_production_6_16_0_width_returned: usize,
    alias_production_6_16_0_width_caller: usize,
    mir_production_6_23_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_23_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_23_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_23_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_6_23_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_6_23_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_6_23_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_6_23_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_24_source: usize,
    mir_production_6_24_argument: usize,
    mir_production_6_24_returned: usize,
    mir_production_6_24_caller: usize,
    alias_production_6_24_0_start_source: usize,
    alias_production_6_24_0_start_argument: usize,
    alias_production_6_24_0_start_returned: usize,
    alias_production_6_24_0_start_caller: usize,
    alias_production_6_24_1_val_source: usize,
    alias_production_6_24_1_val_argument: usize,
    alias_production_6_24_1_val_returned: usize,
    alias_production_6_24_1_val_caller: usize,
    mir_production_6_28_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_28_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_28_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_28_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_6_28_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_6_28_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_6_28_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_6_28_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_29_source: std::ops::Range<usize>,
    mir_production_6_29_argument: std::ops::Range<usize>,
    mir_production_6_29_returned: std::ops::Range<usize>,
    mir_production_6_29_caller: std::ops::Range<usize>,
    alias_production_6_29_0_range_source: std::ops::Range<usize>,
    alias_production_6_29_0_range_argument: std::ops::Range<usize>,
    alias_production_6_29_0_range_returned: std::ops::Range<usize>,
    alias_production_6_29_0_range_caller: std::ops::Range<usize>,
    alias_production_6_29_1_val_source: std::ops::Range<usize>,
    alias_production_6_29_1_val_argument: std::ops::Range<usize>,
    alias_production_6_29_1_val_returned: std::ops::Range<usize>,
    alias_production_6_29_1_val_caller: std::ops::Range<usize>,
    mir_production_6_33_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_33_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_33_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_33_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_6_33_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_6_33_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_6_33_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_6_33_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_6_34_source: u64,
    mir_production_6_34_argument: u64,
    mir_production_6_34_returned: u64,
    mir_production_6_34_caller: u64,
    alias_production_6_34_0_bits_source: u64,
    alias_production_6_34_0_bits_argument: u64,
    alias_production_6_34_0_bits_returned: u64,
    alias_production_6_34_0_bits_caller: u64,
    mir_production_6_36_source: i32,
    mir_production_6_36_argument: i32,
    mir_production_6_36_returned: i32,
    mir_production_6_36_caller: i32,
    alias_production_6_36_0_x_source: i32,
    alias_production_6_36_0_x_argument: i32,
    alias_production_6_36_0_x_returned: i32,
    alias_production_6_36_0_x_caller: i32,
    mir_production_6_38_source: i64,
    mir_production_6_38_argument: i64,
    mir_production_6_38_returned: i64,
    mir_production_6_38_caller: i64,
    alias_production_6_38_0_x_source: i64,
    alias_production_6_38_0_x_argument: i64,
    alias_production_6_38_0_x_returned: i64,
    alias_production_6_38_0_x_caller: i64,
    mir_production_6_39_source: u32,
    mir_production_6_39_argument: u32,
    mir_production_6_39_returned: u32,
    mir_production_6_39_caller: u32,
    alias_production_6_39_0_x_source: u32,
    alias_production_6_39_0_x_argument: u32,
    alias_production_6_39_0_x_returned: u32,
    alias_production_6_39_0_x_caller: u32,
    mir_production_6_40_source: u64,
    mir_production_6_40_argument: u64,
    mir_production_6_40_returned: u64,
    mir_production_6_40_caller: u64,
    alias_production_6_40_0_x_source: u64,
    alias_production_6_40_0_x_argument: u64,
    alias_production_6_40_0_x_returned: u64,
    alias_production_6_40_0_x_caller: u64,
    mir_production_6_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_6_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_6_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_6_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_6_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_6_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_6_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_6_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_6_2_source: u8,
    mir_production_6_2_argument: u8,
    mir_production_6_2_returned: u8,
    mir_production_6_2_caller: u8,
    alias_production_6_2_0_opcode_source: u8,
    alias_production_6_2_0_opcode_argument: u8,
    alias_production_6_2_0_opcode_returned: u8,
    alias_production_6_2_0_opcode_caller: u8,
    mir_production_6_3_source: u32,
    mir_production_6_3_argument: u32,
    mir_production_6_3_returned: u32,
    mir_production_6_3_caller: u32,
    alias_production_6_3_0_offset_source: u32,
    alias_production_6_3_0_offset_argument: u32,
    alias_production_6_3_0_offset_returned: u32,
    alias_production_6_3_0_offset_caller: u32,
    mir_production_7_0_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_7_0_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_7_0_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_7_0_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_7_2_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_7_2_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_7_2_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_7_2_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_7_1_source: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_7_1_argument: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_7_1_returned: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_7_1_caller: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    mir_production_8_0_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_8_0_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_8_0_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_8_0_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_8_2_source: crate::experimental_swift_reactor::control::Cursor,
    mir_production_8_2_argument: crate::experimental_swift_reactor::control::Cursor,
    mir_production_8_2_returned: crate::experimental_swift_reactor::control::Cursor,
    mir_production_8_2_caller: crate::experimental_swift_reactor::control::Cursor,
    mir_production_8_3_source: crate::experimental_swift_reactor::control::Fault,
    mir_production_8_3_argument: crate::experimental_swift_reactor::control::Fault,
    mir_production_8_3_returned: crate::experimental_swift_reactor::control::Fault,
    mir_production_8_3_caller: crate::experimental_swift_reactor::control::Fault,
    mir_production_8_4_source: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_8_4_argument: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_8_4_returned: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_8_4_caller: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_8_5_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_8_5_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_8_5_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_8_5_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_8_6_source: crate::experimental_wasi::WasiUsage,
    mir_production_8_6_argument: crate::experimental_wasi::WasiUsage,
    mir_production_8_6_returned: crate::experimental_wasi::WasiUsage,
    mir_production_8_6_caller: crate::experimental_wasi::WasiUsage,
    mir_production_8_7_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_8_7_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_8_7_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_8_7_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_8_8_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_8_8_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_8_8_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_8_8_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_8_9_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_8_9_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_8_9_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_8_9_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_8_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_8_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_8_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_8_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_8_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_8_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_8_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_8_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    literal_production_8_0_source: &'static str,
    literal_production_8_0_argument: &'static str,
    literal_production_8_0_returned: &'static str,
    literal_production_8_0_caller: &'static str,
    mir_production_9_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_9_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_9_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_9_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_9_0_0_result_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_9_0_0_result_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_9_0_0_result_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_9_0_0_result_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_9_3_source: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    mir_production_9_3_argument: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    mir_production_9_3_returned: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    mir_production_9_3_caller: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    mir_production_9_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_9_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_9_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_9_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_9_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_9_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_9_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_9_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_9_2_source: Value,
    mir_production_9_2_argument: Value,
    mir_production_9_2_returned: Value,
    mir_production_9_2_caller: Value,
    alias_production_9_2_0_value_source: Value,
    alias_production_9_2_0_value_argument: Value,
    alias_production_9_2_0_value_returned: Value,
    alias_production_9_2_0_value_caller: Value,
    mir_production_10_0_source: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_10_0_argument: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_10_0_returned: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_10_0_caller: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_10_0_0_result_source: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_10_0_0_result_argument: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_10_0_0_result_returned: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_10_0_0_result_caller: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_10_2_source: usize,
    mir_production_10_2_argument: usize,
    mir_production_10_2_returned: usize,
    mir_production_10_2_caller: usize,
    alias_production_10_2_0_before_source: usize,
    alias_production_10_2_0_before_argument: usize,
    alias_production_10_2_0_before_returned: usize,
    alias_production_10_2_0_before_caller: usize,
    mir_production_10_3_source: &'static std::vec::Vec<Value>,
    mir_production_10_3_argument: &'static std::vec::Vec<Value>,
    mir_production_10_3_returned: &'static std::vec::Vec<Value>,
    mir_production_10_3_caller: &'static std::vec::Vec<Value>,
    mir_production_10_4_source: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    mir_production_10_4_argument: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    mir_production_10_4_returned: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    mir_production_10_4_caller: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    mir_production_10_5_source: bool,
    mir_production_10_5_argument: bool,
    mir_production_10_5_returned: bool,
    mir_production_10_5_caller: bool,
    mir_production_10_6_source: &'static std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_10_6_argument: &'static std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_10_6_returned: &'static std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_10_6_caller: &'static std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_10_7_source: bool,
    mir_production_10_7_argument: bool,
    mir_production_10_7_returned: bool,
    mir_production_10_7_caller: bool,
    mir_production_10_8_source: usize,
    mir_production_10_8_argument: usize,
    mir_production_10_8_returned: usize,
    mir_production_10_8_caller: usize,
    mir_production_10_9_source: &'static std::vec::Vec<Value>,
    mir_production_10_9_argument: &'static std::vec::Vec<Value>,
    mir_production_10_9_returned: &'static std::vec::Vec<Value>,
    mir_production_10_9_caller: &'static std::vec::Vec<Value>,
    mir_production_10_10_source: &'static mut std::vec::Vec<Value>,
    mir_production_10_10_argument: &'static mut std::vec::Vec<Value>,
    mir_production_10_10_returned: &'static mut std::vec::Vec<Value>,
    mir_production_10_10_caller: &'static mut std::vec::Vec<Value>,
    mir_production_10_11_source: &'static mut std::vec::Vec<Value>,
    mir_production_10_11_argument: &'static mut std::vec::Vec<Value>,
    mir_production_10_11_returned: &'static mut std::vec::Vec<Value>,
    mir_production_10_11_caller: &'static mut std::vec::Vec<Value>,
    mir_production_10_12_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameCleanupState,
    mir_production_10_12_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameCleanupState,
    mir_production_10_12_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameCleanupState,
    mir_production_10_12_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameCleanupState,
    mir_production_10_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_10_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_10_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_10_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_10_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_10_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_10_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_10_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    literal_production_10_0_source: bool,
    literal_production_10_0_argument: bool,
    literal_production_10_0_returned: bool,
    literal_production_10_0_caller: bool,
    mir_production_11_0_source: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_11_0_argument: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_11_0_returned: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_11_0_caller: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_11_2_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>,
    mir_production_11_2_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>,
    mir_production_11_2_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>,
    mir_production_11_2_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>,
    mir_production_11_3_source: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_11_3_argument: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_11_3_returned: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_11_3_caller: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_11_4_source: isize,
    mir_production_11_4_argument: isize,
    mir_production_11_4_returned: isize,
    mir_production_11_4_caller: isize,
    mir_production_11_5_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_11_5_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_11_5_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_11_5_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_11_5_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_11_5_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_11_5_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_11_5_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_11_6_source: Value,
    mir_production_11_6_argument: Value,
    mir_production_11_6_returned: Value,
    mir_production_11_6_caller: Value,
    alias_production_11_6_0_val_source: Value,
    alias_production_11_6_0_val_argument: Value,
    alias_production_11_6_0_val_returned: Value,
    alias_production_11_6_0_val_caller: Value,
    mir_production_11_7_source: isize,
    mir_production_11_7_argument: isize,
    mir_production_11_7_returned: isize,
    mir_production_11_7_caller: isize,
    mir_production_11_8_source: i32,
    mir_production_11_8_argument: i32,
    mir_production_11_8_returned: i32,
    mir_production_11_8_caller: i32,
    alias_production_11_8_0_value_source: i32,
    alias_production_11_8_0_value_argument: i32,
    alias_production_11_8_0_value_returned: i32,
    alias_production_11_8_0_value_caller: i32,
    mir_production_11_9_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_11_9_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_11_9_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_11_9_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_11_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_11_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_11_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_11_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_11_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_11_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_11_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_11_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    literal_production_11_0_source: &'static str,
    literal_production_11_0_argument: &'static str,
    literal_production_11_0_returned: &'static str,
    literal_production_11_0_caller: &'static str,
    mir_production_12_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_12_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_12_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_12_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_12_4_source: Type,
    mir_production_12_4_argument: Type,
    mir_production_12_4_returned: Type,
    mir_production_12_4_caller: Type,
    alias_production_12_4_0_expected_source: Type,
    alias_production_12_4_0_expected_argument: Type,
    alias_production_12_4_0_expected_returned: Type,
    alias_production_12_4_0_expected_caller: Type,
    mir_production_12_5_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_5_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_5_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_5_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_6_source: bool,
    mir_production_12_6_argument: bool,
    mir_production_12_6_returned: bool,
    mir_production_12_6_caller: bool,
    mir_production_12_7_source: &'static std::ops::RangeInclusive<u8>,
    mir_production_12_7_argument: &'static std::ops::RangeInclusive<u8>,
    mir_production_12_7_returned: &'static std::ops::RangeInclusive<u8>,
    mir_production_12_7_caller: &'static std::ops::RangeInclusive<u8>,
    mir_production_12_8_source: &'static u8,
    mir_production_12_8_argument: &'static u8,
    mir_production_12_8_returned: &'static u8,
    mir_production_12_8_caller: &'static u8,
    mir_production_12_9_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_9_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_9_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_9_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_10_source: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_12_10_argument: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_12_10_returned: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_12_10_caller: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_12_11_source: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_12_11_argument: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_12_11_returned: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_12_11_caller: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_12_12_source: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_12_12_argument: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_12_12_returned: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_12_12_caller: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_12_13_source: isize,
    mir_production_12_13_argument: isize,
    mir_production_12_13_returned: isize,
    mir_production_12_13_caller: isize,
    mir_production_12_15_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_15_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_15_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_15_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_17_source: bool,
    mir_production_12_17_argument: bool,
    mir_production_12_17_returned: bool,
    mir_production_12_17_caller: bool,
    mir_production_12_18_source: usize,
    mir_production_12_18_argument: usize,
    mir_production_12_18_returned: usize,
    mir_production_12_18_caller: usize,
    mir_production_12_19_source: bool,
    mir_production_12_19_argument: bool,
    mir_production_12_19_returned: bool,
    mir_production_12_19_caller: bool,
    mir_production_12_20_source: usize,
    mir_production_12_20_argument: usize,
    mir_production_12_20_returned: usize,
    mir_production_12_20_caller: usize,
    mir_production_12_21_source: usize,
    mir_production_12_21_argument: usize,
    mir_production_12_21_returned: usize,
    mir_production_12_21_caller: usize,
    mir_production_12_22_source: &'static std::vec::Vec<crate::experimental::execution::Control>,
    mir_production_12_22_argument: &'static std::vec::Vec<crate::experimental::execution::Control>,
    mir_production_12_22_returned: &'static std::vec::Vec<crate::experimental::execution::Control>,
    mir_production_12_22_caller: &'static std::vec::Vec<crate::experimental::execution::Control>,
    mir_production_12_23_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_23_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_23_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_23_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_24_source: std::option::Option<usize>,
    mir_production_12_24_argument: std::option::Option<usize>,
    mir_production_12_24_returned: std::option::Option<usize>,
    mir_production_12_24_caller: std::option::Option<usize>,
    mir_production_12_25_source: usize,
    mir_production_12_25_argument: usize,
    mir_production_12_25_returned: usize,
    mir_production_12_25_caller: usize,
    mir_production_12_26_source: &'static std::vec::Vec<Value>,
    mir_production_12_26_argument: &'static std::vec::Vec<Value>,
    mir_production_12_26_returned: &'static std::vec::Vec<Value>,
    mir_production_12_26_caller: &'static std::vec::Vec<Value>,
    mir_production_12_27_source: isize,
    mir_production_12_27_argument: isize,
    mir_production_12_27_returned: isize,
    mir_production_12_27_caller: isize,
    mir_production_12_29_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_29_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_29_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_29_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_31_source: bool,
    mir_production_12_31_argument: bool,
    mir_production_12_31_returned: bool,
    mir_production_12_31_caller: bool,
    mir_production_12_32_source: usize,
    mir_production_12_32_argument: usize,
    mir_production_12_32_returned: usize,
    mir_production_12_32_caller: usize,
    mir_production_12_33_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_33_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_33_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_33_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_35_source: &'static std::vec::Vec<Value>,
    mir_production_12_35_argument: &'static std::vec::Vec<Value>,
    mir_production_12_35_returned: &'static std::vec::Vec<Value>,
    mir_production_12_35_caller: &'static std::vec::Vec<Value>,
    mir_production_12_36_source: bool,
    mir_production_12_36_argument: bool,
    mir_production_12_36_returned: bool,
    mir_production_12_36_caller: bool,
    mir_production_12_37_source: &'static Type,
    mir_production_12_37_argument: &'static Type,
    mir_production_12_37_returned: &'static Type,
    mir_production_12_37_caller: &'static Type,
    mir_production_12_38_source: Type,
    mir_production_12_38_argument: Type,
    mir_production_12_38_returned: Type,
    mir_production_12_38_caller: Type,
    mir_production_12_39_source: Value,
    mir_production_12_39_argument: Value,
    mir_production_12_39_returned: Value,
    mir_production_12_39_caller: Value,
    mir_production_12_40_source: &'static Value,
    mir_production_12_40_argument: &'static Value,
    mir_production_12_40_returned: &'static Value,
    mir_production_12_40_caller: &'static Value,
    mir_production_12_41_source: &'static std::vec::Vec<Value>,
    mir_production_12_41_argument: &'static std::vec::Vec<Value>,
    mir_production_12_41_returned: &'static std::vec::Vec<Value>,
    mir_production_12_41_caller: &'static std::vec::Vec<Value>,
    mir_production_12_42_source: usize,
    mir_production_12_42_argument: usize,
    mir_production_12_42_returned: usize,
    mir_production_12_42_caller: usize,
    mir_production_12_43_source: (usize, bool),
    mir_production_12_43_argument: (usize, bool),
    mir_production_12_43_returned: (usize, bool),
    mir_production_12_43_caller: (usize, bool),
    mir_production_12_44_source: &'static Type,
    mir_production_12_44_argument: &'static Type,
    mir_production_12_44_returned: &'static Type,
    mir_production_12_44_caller: &'static Type,
    mir_production_12_45_source: bool,
    mir_production_12_45_argument: bool,
    mir_production_12_45_returned: bool,
    mir_production_12_45_caller: bool,
    mir_production_12_46_source: &'static Type,
    mir_production_12_46_argument: &'static Type,
    mir_production_12_46_returned: &'static Type,
    mir_production_12_46_caller: &'static Type,
    mir_production_12_47_source: Type,
    mir_production_12_47_argument: Type,
    mir_production_12_47_returned: Type,
    mir_production_12_47_caller: Type,
    mir_production_12_48_source: Value,
    mir_production_12_48_argument: Value,
    mir_production_12_48_returned: Value,
    mir_production_12_48_caller: Value,
    mir_production_12_49_source: &'static Value,
    mir_production_12_49_argument: &'static Value,
    mir_production_12_49_returned: &'static Value,
    mir_production_12_49_caller: &'static Value,
    mir_production_12_50_source: &'static std::vec::Vec<Value>,
    mir_production_12_50_argument: &'static std::vec::Vec<Value>,
    mir_production_12_50_returned: &'static std::vec::Vec<Value>,
    mir_production_12_50_caller: &'static std::vec::Vec<Value>,
    mir_production_12_51_source: usize,
    mir_production_12_51_argument: usize,
    mir_production_12_51_returned: usize,
    mir_production_12_51_caller: usize,
    mir_production_12_52_source: (usize, bool),
    mir_production_12_52_argument: (usize, bool),
    mir_production_12_52_returned: (usize, bool),
    mir_production_12_52_caller: (usize, bool),
    mir_production_12_53_source: &'static Type,
    mir_production_12_53_argument: &'static Type,
    mir_production_12_53_returned: &'static Type,
    mir_production_12_53_caller: &'static Type,
    mir_production_12_54_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_54_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_54_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_54_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_12_55_source: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_12_55_argument: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_12_55_returned: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_12_55_caller: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_12_56_source: &'static mut std::vec::Vec<crate::experimental::execution::Control>,
    mir_production_12_56_argument: &'static mut std::vec::Vec<crate::experimental::execution::Control>,
    mir_production_12_56_returned: &'static mut std::vec::Vec<crate::experimental::execution::Control>,
    mir_production_12_56_caller: &'static mut std::vec::Vec<crate::experimental::execution::Control>,
    mir_production_12_57_source: &'static mut std::vec::Vec<Value>,
    mir_production_12_57_argument: &'static mut std::vec::Vec<Value>,
    mir_production_12_57_returned: &'static mut std::vec::Vec<Value>,
    mir_production_12_57_caller: &'static mut std::vec::Vec<Value>,
    mir_production_12_58_source: &'static mut std::vec::Vec<Value>,
    mir_production_12_58_argument: &'static mut std::vec::Vec<Value>,
    mir_production_12_58_returned: &'static mut std::vec::Vec<Value>,
    mir_production_12_58_caller: &'static mut std::vec::Vec<Value>,
    mir_production_12_59_source: &'static mut std::vec::Vec<Value>,
    mir_production_12_59_argument: &'static mut std::vec::Vec<Value>,
    mir_production_12_59_returned: &'static mut std::vec::Vec<Value>,
    mir_production_12_59_caller: &'static mut std::vec::Vec<Value>,
    mir_production_12_60_source: &'static mut std::vec::Vec<Value>,
    mir_production_12_60_argument: &'static mut std::vec::Vec<Value>,
    mir_production_12_60_returned: &'static mut std::vec::Vec<Value>,
    mir_production_12_60_caller: &'static mut std::vec::Vec<Value>,
    mir_production_12_14_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_12_14_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_12_14_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_12_14_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_12_14_0_frame_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_12_14_0_frame_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_12_14_0_frame_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_12_14_0_frame_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_12_14_1_frame_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_12_14_1_frame_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_12_14_1_frame_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_12_14_1_frame_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_12_16_source: usize,
    mir_production_12_16_argument: usize,
    mir_production_12_16_returned: usize,
    mir_production_12_16_caller: usize,
    alias_production_12_16_0_floor_source: usize,
    alias_production_12_16_0_floor_argument: usize,
    alias_production_12_16_0_floor_returned: usize,
    alias_production_12_16_0_floor_caller: usize,
    mir_production_12_28_source: usize,
    mir_production_12_28_argument: usize,
    mir_production_12_28_returned: usize,
    mir_production_12_28_caller: usize,
    alias_production_12_28_0_available_source: usize,
    alias_production_12_28_0_available_argument: usize,
    alias_production_12_28_0_available_returned: usize,
    alias_production_12_28_0_available_caller: usize,
    alias_production_12_28_1_available_source: usize,
    alias_production_12_28_1_available_argument: usize,
    alias_production_12_28_1_available_returned: usize,
    alias_production_12_28_1_available_caller: usize,
    mir_production_12_30_source: usize,
    mir_production_12_30_argument: usize,
    mir_production_12_30_returned: usize,
    mir_production_12_30_caller: usize,
    alias_production_12_30_0_count_source: usize,
    alias_production_12_30_0_count_argument: usize,
    alias_production_12_30_0_count_returned: usize,
    alias_production_12_30_0_count_caller: usize,
    mir_production_12_34_source: usize,
    mir_production_12_34_argument: usize,
    mir_production_12_34_returned: usize,
    mir_production_12_34_caller: usize,
    alias_production_12_34_0_length_source: usize,
    alias_production_12_34_0_length_argument: usize,
    alias_production_12_34_0_length_returned: usize,
    alias_production_12_34_0_length_caller: usize,
    mir_production_12_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_12_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_12_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_12_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_12_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_12_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_12_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_12_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_12_2_source: u8,
    mir_production_12_2_argument: u8,
    mir_production_12_2_returned: u8,
    mir_production_12_2_caller: u8,
    alias_production_12_2_0_opcode_source: u8,
    alias_production_12_2_0_opcode_argument: u8,
    alias_production_12_2_0_opcode_returned: u8,
    alias_production_12_2_0_opcode_caller: u8,
    mir_production_12_3_source: bool,
    mir_production_12_3_argument: bool,
    mir_production_12_3_returned: bool,
    mir_production_12_3_caller: bool,
    alias_production_12_3_0_store_source: bool,
    alias_production_12_3_0_store_argument: bool,
    alias_production_12_3_0_store_returned: bool,
    alias_production_12_3_0_store_caller: bool,
    literal_production_12_0_source: &'static str,
    literal_production_12_0_argument: &'static str,
    literal_production_12_0_returned: &'static str,
    literal_production_12_0_caller: &'static str,
    literal_production_12_1_source: &'static str,
    literal_production_12_1_argument: &'static str,
    literal_production_12_1_returned: &'static str,
    literal_production_12_1_caller: &'static str,
    literal_production_12_2_source: &'static str,
    literal_production_12_2_argument: &'static str,
    literal_production_12_2_returned: &'static str,
    literal_production_12_2_caller: &'static str,
    literal_production_12_3_source: usize,
    literal_production_12_3_argument: usize,
    literal_production_12_3_returned: usize,
    literal_production_12_3_caller: usize,
    literal_production_12_4_source: usize,
    literal_production_12_4_argument: usize,
    literal_production_12_4_returned: usize,
    literal_production_12_4_caller: usize,
    literal_production_12_5_source: &'static str,
    literal_production_12_5_argument: &'static str,
    literal_production_12_5_returned: &'static str,
    literal_production_12_5_caller: &'static str,
    literal_production_12_6_source: usize,
    literal_production_12_6_argument: usize,
    literal_production_12_6_returned: usize,
    literal_production_12_6_caller: usize,
    literal_production_12_7_source: usize,
    literal_production_12_7_argument: usize,
    literal_production_12_7_returned: usize,
    literal_production_12_7_caller: usize,
    literal_production_12_8_source: usize,
    literal_production_12_8_argument: usize,
    literal_production_12_8_returned: usize,
    literal_production_12_8_caller: usize,
    literal_production_12_9_source: usize,
    literal_production_12_9_argument: usize,
    literal_production_12_9_returned: usize,
    literal_production_12_9_caller: usize,
    literal_production_12_10_source: &'static str,
    literal_production_12_10_argument: &'static str,
    literal_production_12_10_returned: &'static str,
    literal_production_12_10_caller: &'static str,
    mir_production_13_0_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_13_0_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_13_0_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_13_0_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_13_2_source: crate::experimental_swift_reactor::control::Cursor,
    mir_production_13_2_argument: crate::experimental_swift_reactor::control::Cursor,
    mir_production_13_2_returned: crate::experimental_swift_reactor::control::Cursor,
    mir_production_13_2_caller: crate::experimental_swift_reactor::control::Cursor,
    mir_production_13_3_source: crate::experimental_swift_reactor::control::Fault,
    mir_production_13_3_argument: crate::experimental_swift_reactor::control::Fault,
    mir_production_13_3_returned: crate::experimental_swift_reactor::control::Fault,
    mir_production_13_3_caller: crate::experimental_swift_reactor::control::Fault,
    mir_production_13_4_source: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_13_4_argument: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_13_4_returned: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_13_4_caller: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_13_5_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_13_5_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_13_5_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_13_5_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_13_6_source: crate::experimental_wasi::WasiUsage,
    mir_production_13_6_argument: crate::experimental_wasi::WasiUsage,
    mir_production_13_6_returned: crate::experimental_wasi::WasiUsage,
    mir_production_13_6_caller: crate::experimental_wasi::WasiUsage,
    mir_production_13_7_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_13_7_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_13_7_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_13_7_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_13_8_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_13_8_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_13_8_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_13_8_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_13_9_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_13_9_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_13_9_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_13_9_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_13_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_13_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_13_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_13_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_13_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_13_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_13_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_13_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    literal_production_13_0_source: &'static str,
    literal_production_13_0_argument: &'static str,
    literal_production_13_0_returned: &'static str,
    literal_production_13_0_caller: &'static str,
    mir_production_14_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_14_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_14_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_14_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_14_4_source: bool,
    mir_production_14_4_argument: bool,
    mir_production_14_4_returned: bool,
    mir_production_14_4_caller: bool,
    mir_production_14_5_source: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_14_5_argument: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_14_5_returned: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_14_5_caller: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_14_6_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_14_6_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_14_6_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_14_6_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_14_6_0_failure_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_14_6_0_failure_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_14_6_0_failure_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_14_6_0_failure_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_14_7_source: (),
    mir_production_14_7_argument: (),
    mir_production_14_7_returned: (),
    mir_production_14_7_caller: (),
    mir_production_14_8_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_14_8_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_14_8_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_14_8_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_14_8_0_result_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_14_8_0_result_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_14_8_0_result_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_14_8_0_result_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_14_9_source: bool,
    mir_production_14_9_argument: bool,
    mir_production_14_9_returned: bool,
    mir_production_14_9_caller: bool,
    mir_production_14_10_source: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_14_10_argument: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_14_10_returned: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_14_10_caller: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_14_11_source: (),
    mir_production_14_11_argument: (),
    mir_production_14_11_returned: (),
    mir_production_14_11_caller: (),
    mir_production_14_12_source: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_14_12_argument: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_14_12_returned: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_14_12_caller: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_14_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_14_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_14_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_14_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_14_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_14_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_14_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_14_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_14_2_source: crate::experimental::cache::Operation,
    mir_production_14_2_argument: crate::experimental::cache::Operation,
    mir_production_14_2_returned: crate::experimental::cache::Operation,
    mir_production_14_2_caller: crate::experimental::cache::Operation,
    alias_production_14_2_0_operation_source: crate::experimental::cache::Operation,
    alias_production_14_2_0_operation_argument: crate::experimental::cache::Operation,
    alias_production_14_2_0_operation_returned: crate::experimental::cache::Operation,
    alias_production_14_2_0_operation_caller: crate::experimental::cache::Operation,
    mir_production_14_3_source: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_14_3_argument: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_14_3_returned: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_14_3_caller: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    alias_production_14_3_0_returned_source: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    alias_production_14_3_0_returned_argument: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    alias_production_14_3_0_returned_returned: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    alias_production_14_3_0_returned_caller: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    literal_production_14_0_source: &'static str,
    literal_production_14_0_argument: &'static str,
    literal_production_14_0_returned: &'static str,
    literal_production_14_0_caller: &'static str,
    mir_production_15_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_3_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_15_3_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_15_3_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_15_3_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_15_4_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_4_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_4_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_4_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_5_source: isize,
    mir_production_15_5_argument: isize,
    mir_production_15_5_returned: isize,
    mir_production_15_5_caller: isize,
    mir_production_15_6_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_6_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_6_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_6_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_15_6_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_15_6_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_15_6_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_15_6_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_7_source: isize,
    mir_production_15_7_argument: isize,
    mir_production_15_7_returned: isize,
    mir_production_15_7_caller: isize,
    mir_production_15_8_source: u8,
    mir_production_15_8_argument: u8,
    mir_production_15_8_returned: u8,
    mir_production_15_8_caller: u8,
    alias_production_15_8_0_opcode_source: u8,
    alias_production_15_8_0_opcode_argument: u8,
    alias_production_15_8_0_opcode_returned: u8,
    alias_production_15_8_0_opcode_caller: u8,
    mir_production_15_9_source: u32,
    mir_production_15_9_argument: u32,
    mir_production_15_9_returned: u32,
    mir_production_15_9_caller: u32,
    alias_production_15_9_0_offset_source: u32,
    alias_production_15_9_0_offset_argument: u32,
    alias_production_15_9_0_offset_returned: u32,
    alias_production_15_9_0_offset_caller: u32,
    mir_production_15_10_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_15_10_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_15_10_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_15_10_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_15_11_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_11_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_11_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_11_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_12_source: isize,
    mir_production_15_12_argument: isize,
    mir_production_15_12_returned: isize,
    mir_production_15_12_caller: isize,
    mir_production_15_14_source: u8,
    mir_production_15_14_argument: u8,
    mir_production_15_14_returned: u8,
    mir_production_15_14_caller: u8,
    alias_production_15_14_0_opcode_source: u8,
    alias_production_15_14_0_opcode_argument: u8,
    alias_production_15_14_0_opcode_returned: u8,
    alias_production_15_14_0_opcode_caller: u8,
    mir_production_15_15_source: u32,
    mir_production_15_15_argument: u32,
    mir_production_15_15_returned: u32,
    mir_production_15_15_caller: u32,
    alias_production_15_15_0_offset_source: u32,
    alias_production_15_15_0_offset_argument: u32,
    alias_production_15_15_0_offset_returned: u32,
    alias_production_15_15_0_offset_caller: u32,
    mir_production_15_16_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_15_16_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_15_16_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_15_16_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_15_17_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_17_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_17_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_17_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_18_source: isize,
    mir_production_15_18_argument: isize,
    mir_production_15_18_returned: isize,
    mir_production_15_18_caller: isize,
    mir_production_15_20_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_15_20_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_15_20_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_15_20_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_15_13_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_13_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_13_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_13_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_15_13_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_15_13_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_15_13_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_15_13_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_19_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_19_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_19_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_19_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_15_19_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_15_19_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_15_19_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_15_19_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_15_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_15_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_15_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_15_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_15_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_15_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_15_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_15_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_15_2_source: crate::experimental::cache::Operation,
    mir_production_15_2_argument: crate::experimental::cache::Operation,
    mir_production_15_2_returned: crate::experimental::cache::Operation,
    mir_production_15_2_caller: crate::experimental::cache::Operation,
    alias_production_15_2_0_operation_source: crate::experimental::cache::Operation,
    alias_production_15_2_0_operation_argument: crate::experimental::cache::Operation,
    alias_production_15_2_0_operation_returned: crate::experimental::cache::Operation,
    alias_production_15_2_0_operation_caller: crate::experimental::cache::Operation,
    literal_production_15_0_source: bool,
    literal_production_15_0_argument: bool,
    literal_production_15_0_returned: bool,
    literal_production_15_0_caller: bool,
    literal_production_15_1_source: bool,
    literal_production_15_1_argument: bool,
    literal_production_15_1_returned: bool,
    literal_production_15_1_caller: bool,
    mir_production_16_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_16_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_16_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_16_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_16_3_source: bool,
    mir_production_16_3_argument: bool,
    mir_production_16_3_returned: bool,
    mir_production_16_3_caller: bool,
    mir_production_16_4_source: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_16_4_argument: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_16_4_returned: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_16_4_caller: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_16_5_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_16_5_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_16_5_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_16_5_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_16_5_0_failure_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_16_5_0_failure_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_16_5_0_failure_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_16_5_0_failure_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_16_6_source: (),
    mir_production_16_6_argument: (),
    mir_production_16_6_returned: (),
    mir_production_16_6_caller: (),
    mir_production_16_7_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_16_7_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_16_7_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_16_7_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_16_7_0_result_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_16_7_0_result_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_16_7_0_result_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_16_7_0_result_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_16_8_source: bool,
    mir_production_16_8_argument: bool,
    mir_production_16_8_returned: bool,
    mir_production_16_8_caller: bool,
    mir_production_16_9_source: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_16_9_argument: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_16_9_returned: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_16_9_caller: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_16_10_source: (),
    mir_production_16_10_argument: (),
    mir_production_16_10_returned: (),
    mir_production_16_10_caller: (),
    mir_production_16_11_source: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_16_11_argument: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_16_11_returned: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_16_11_caller: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_16_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_16_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_16_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_16_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_16_1_0_phase_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_16_1_0_phase_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_16_1_0_phase_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_16_1_0_phase_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_16_2_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    mir_production_16_2_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    mir_production_16_2_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    mir_production_16_2_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    alias_production_16_2_0_storage_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    alias_production_16_2_0_storage_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    alias_production_16_2_0_storage_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    alias_production_16_2_0_storage_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    literal_production_16_0_source: &'static str,
    literal_production_16_0_argument: &'static str,
    literal_production_16_0_returned: &'static str,
    literal_production_16_0_caller: &'static str,
    mir_production_17_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_2_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_17_2_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_17_2_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_17_2_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_17_3_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_3_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_3_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_3_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_4_source: isize,
    mir_production_17_4_argument: isize,
    mir_production_17_4_returned: isize,
    mir_production_17_4_caller: isize,
    mir_production_17_5_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_5_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_5_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_5_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_17_5_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_17_5_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_17_5_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_17_5_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_6_source: (u32, crate::experimental::cache::DecodedInstruction),
    mir_production_17_6_argument: (u32, crate::experimental::cache::DecodedInstruction),
    mir_production_17_6_returned: (u32, crate::experimental::cache::DecodedInstruction),
    mir_production_17_6_caller: (u32, crate::experimental::cache::DecodedInstruction),
    alias_production_17_6_0_selected_source: (u32, crate::experimental::cache::DecodedInstruction),
    alias_production_17_6_0_selected_argument: (u32, crate::experimental::cache::DecodedInstruction),
    alias_production_17_6_0_selected_returned: (u32, crate::experimental::cache::DecodedInstruction),
    alias_production_17_6_0_selected_caller: (u32, crate::experimental::cache::DecodedInstruction),
    mir_production_17_7_source: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_7_argument: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_7_returned: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_7_caller: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_8_source: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_17_8_argument: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_17_8_returned: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_17_8_caller: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_17_9_source: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_9_argument: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_9_returned: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_9_caller: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_10_source: isize,
    mir_production_17_10_argument: isize,
    mir_production_17_10_returned: isize,
    mir_production_17_10_caller: isize,
    mir_production_17_11_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_17_11_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_17_11_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_17_11_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_17_11_0_frame_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_17_11_0_frame_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_17_11_0_frame_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_17_11_0_frame_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_17_11_1_frame_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_17_11_1_frame_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_17_11_1_frame_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_17_11_1_frame_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_17_12_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_17_12_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_17_12_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_17_12_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_17_13_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::cache::FunctionView<'static>>,
    mir_production_17_13_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::cache::FunctionView<'static>>,
    mir_production_17_13_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::cache::FunctionView<'static>>,
    mir_production_17_13_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::cache::FunctionView<'static>>,
    mir_production_17_14_source: std::result::Result<crate::experimental::cache::FunctionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_14_argument: std::result::Result<crate::experimental::cache::FunctionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_14_returned: std::result::Result<crate::experimental::cache::FunctionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_14_caller: std::result::Result<crate::experimental::cache::FunctionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_15_source: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_17_15_argument: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_17_15_returned: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_17_15_caller: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_17_16_source: &'static crate::experimental_swift_reactor::cache::SwiftFunctionPin,
    mir_production_17_16_argument: &'static crate::experimental_swift_reactor::cache::SwiftFunctionPin,
    mir_production_17_16_returned: &'static crate::experimental_swift_reactor::cache::SwiftFunctionPin,
    mir_production_17_16_caller: &'static crate::experimental_swift_reactor::cache::SwiftFunctionPin,
    mir_production_17_17_source: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    mir_production_17_17_argument: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    mir_production_17_17_returned: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    mir_production_17_17_caller: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    mir_production_17_18_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_17_18_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_17_18_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_17_18_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_17_19_source: isize,
    mir_production_17_19_argument: isize,
    mir_production_17_19_returned: isize,
    mir_production_17_19_caller: isize,
    mir_production_17_23_source: std::option::Option<&'static crate::experimental::cache::DecodedInstruction>,
    mir_production_17_23_argument: std::option::Option<&'static crate::experimental::cache::DecodedInstruction>,
    mir_production_17_23_returned: std::option::Option<&'static crate::experimental::cache::DecodedInstruction>,
    mir_production_17_23_caller: std::option::Option<&'static crate::experimental::cache::DecodedInstruction>,
    mir_production_17_24_source: usize,
    mir_production_17_24_argument: usize,
    mir_production_17_24_returned: usize,
    mir_production_17_24_caller: usize,
    mir_production_17_25_source: isize,
    mir_production_17_25_argument: isize,
    mir_production_17_25_returned: isize,
    mir_production_17_25_caller: isize,
    mir_production_17_27_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_17_27_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_17_27_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_17_27_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_17_28_source: u32,
    mir_production_17_28_argument: u32,
    mir_production_17_28_returned: u32,
    mir_production_17_28_caller: u32,
    mir_production_17_31_source: crate::experimental_swift_reactor::control::Cursor,
    mir_production_17_31_argument: crate::experimental_swift_reactor::control::Cursor,
    mir_production_17_31_returned: crate::experimental_swift_reactor::control::Cursor,
    mir_production_17_31_caller: crate::experimental_swift_reactor::control::Cursor,
    mir_production_17_32_source: crate::experimental_swift_reactor::control::SwiftRunStage,
    mir_production_17_32_argument: crate::experimental_swift_reactor::control::SwiftRunStage,
    mir_production_17_32_returned: crate::experimental_swift_reactor::control::SwiftRunStage,
    mir_production_17_32_caller: crate::experimental_swift_reactor::control::SwiftRunStage,
    mir_production_17_33_source: std::option::Option<u32>,
    mir_production_17_33_argument: std::option::Option<u32>,
    mir_production_17_33_returned: std::option::Option<u32>,
    mir_production_17_33_caller: std::option::Option<u32>,
    mir_production_17_34_source: std::option::Option<usize>,
    mir_production_17_34_argument: std::option::Option<usize>,
    mir_production_17_34_returned: std::option::Option<usize>,
    mir_production_17_34_caller: std::option::Option<usize>,
    mir_production_17_35_source: usize,
    mir_production_17_35_argument: usize,
    mir_production_17_35_returned: usize,
    mir_production_17_35_caller: usize,
    mir_production_17_36_source: bool,
    mir_production_17_36_argument: bool,
    mir_production_17_36_returned: bool,
    mir_production_17_36_caller: bool,
    mir_production_17_37_source: bool,
    mir_production_17_37_argument: bool,
    mir_production_17_37_returned: bool,
    mir_production_17_37_caller: bool,
    mir_production_17_38_source: bool,
    mir_production_17_38_argument: bool,
    mir_production_17_38_returned: bool,
    mir_production_17_38_caller: bool,
    mir_production_17_39_source: bool,
    mir_production_17_39_argument: bool,
    mir_production_17_39_returned: bool,
    mir_production_17_39_caller: bool,
    mir_production_17_40_source: isize,
    mir_production_17_40_argument: isize,
    mir_production_17_40_returned: isize,
    mir_production_17_40_caller: isize,
    mir_production_17_41_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_17_41_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_17_41_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_17_41_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_17_42_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_17_42_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_17_42_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_17_42_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_17_43_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_43_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_43_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_43_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_44_source: crate::experimental_swift_reactor::control::Cursor,
    mir_production_17_44_argument: crate::experimental_swift_reactor::control::Cursor,
    mir_production_17_44_returned: crate::experimental_swift_reactor::control::Cursor,
    mir_production_17_44_caller: crate::experimental_swift_reactor::control::Cursor,
    mir_production_17_45_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_17_45_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_17_45_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_17_45_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_17_46_source: crate::experimental_wasi::WasiUsage,
    mir_production_17_46_argument: crate::experimental_wasi::WasiUsage,
    mir_production_17_46_returned: crate::experimental_wasi::WasiUsage,
    mir_production_17_46_caller: crate::experimental_wasi::WasiUsage,
    mir_production_17_47_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_17_47_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_17_47_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_17_47_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_17_48_source: isize,
    mir_production_17_48_argument: isize,
    mir_production_17_48_returned: isize,
    mir_production_17_48_caller: isize,
    mir_production_17_50_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_17_50_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_17_50_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_17_50_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_17_51_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_51_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_51_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_51_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_52_source: isize,
    mir_production_17_52_argument: isize,
    mir_production_17_52_returned: isize,
    mir_production_17_52_caller: isize,
    mir_production_17_54_source: std::option::Option<usize>,
    mir_production_17_54_argument: std::option::Option<usize>,
    mir_production_17_54_returned: std::option::Option<usize>,
    mir_production_17_54_caller: std::option::Option<usize>,
    mir_production_17_55_source: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_55_argument: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_55_returned: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_55_caller: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_56_source: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_17_56_argument: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_17_56_returned: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_17_56_caller: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_17_57_source: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_57_argument: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_57_returned: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_57_caller: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_58_source: isize,
    mir_production_17_58_argument: isize,
    mir_production_17_58_returned: isize,
    mir_production_17_58_caller: isize,
    mir_production_17_60_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_17_60_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_17_60_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_17_60_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_17_61_source: &'static mut crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_17_61_argument: &'static mut crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_17_61_returned: &'static mut crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_17_61_caller: &'static mut crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_17_62_source: std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_62_argument: std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_62_returned: std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_62_caller: std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_63_source: &'static mut [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_17_63_argument: &'static mut [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_17_63_returned: &'static mut [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_17_63_caller: &'static mut [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_17_64_source: &'static str,
    mir_production_17_64_argument: &'static str,
    mir_production_17_64_returned: &'static str,
    mir_production_17_64_caller: &'static str,
    mir_production_17_65_source: crate::experimental::cache::Operation,
    mir_production_17_65_argument: crate::experimental::cache::Operation,
    mir_production_17_65_returned: crate::experimental::cache::Operation,
    mir_production_17_65_caller: crate::experimental::cache::Operation,
    mir_production_17_66_source: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_66_argument: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_66_returned: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_66_caller: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_67_source: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_17_67_argument: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_17_67_returned: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_17_67_caller: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_17_68_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_17_68_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_17_68_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_17_68_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_17_69_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_17_69_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_17_69_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_17_69_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_17_70_source: &'static [crate::experimental::cache::DecodedInstruction],
    mir_production_17_70_argument: &'static [crate::experimental::cache::DecodedInstruction],
    mir_production_17_70_returned: &'static [crate::experimental::cache::DecodedInstruction],
    mir_production_17_70_caller: &'static [crate::experimental::cache::DecodedInstruction],
    mir_production_17_71_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_17_71_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_17_71_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_17_71_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_17_72_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_17_72_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_17_72_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_17_72_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_17_73_source: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_73_argument: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_73_returned: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_73_caller: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_74_source: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_74_argument: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_74_returned: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_74_caller: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_17_29_source: u32,
    mir_production_17_29_argument: u32,
    mir_production_17_29_returned: u32,
    mir_production_17_29_caller: u32,
    alias_production_17_29_0_function_source: u32,
    alias_production_17_29_0_function_argument: u32,
    alias_production_17_29_0_function_returned: u32,
    alias_production_17_29_0_function_caller: u32,
    mir_production_17_30_source: crate::experimental::cache::DecodedInstruction,
    mir_production_17_30_argument: crate::experimental::cache::DecodedInstruction,
    mir_production_17_30_returned: crate::experimental::cache::DecodedInstruction,
    mir_production_17_30_caller: crate::experimental::cache::DecodedInstruction,
    alias_production_17_30_0_instruction_source: crate::experimental::cache::DecodedInstruction,
    alias_production_17_30_0_instruction_argument: crate::experimental::cache::DecodedInstruction,
    alias_production_17_30_0_instruction_returned: crate::experimental::cache::DecodedInstruction,
    alias_production_17_30_0_instruction_caller: crate::experimental::cache::DecodedInstruction,
    mir_production_17_49_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_49_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_49_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_49_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_17_49_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_17_49_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_17_49_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_17_49_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_53_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_53_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_53_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_53_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_17_53_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_17_53_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_17_53_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_17_53_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_59_source: usize,
    mir_production_17_59_argument: usize,
    mir_production_17_59_returned: usize,
    mir_production_17_59_caller: usize,
    alias_production_17_59_0_pc_source: usize,
    alias_production_17_59_0_pc_argument: usize,
    alias_production_17_59_0_pc_returned: usize,
    alias_production_17_59_0_pc_caller: usize,
    alias_production_17_59_1_pc_source: usize,
    alias_production_17_59_1_pc_argument: usize,
    alias_production_17_59_1_pc_returned: usize,
    alias_production_17_59_1_pc_caller: usize,
    mir_production_17_20_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_20_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_20_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_20_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_17_20_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_17_20_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_17_20_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_17_20_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_17_21_source: crate::experimental::cache::FunctionView<'static>,
    mir_production_17_21_argument: crate::experimental::cache::FunctionView<'static>,
    mir_production_17_21_returned: crate::experimental::cache::FunctionView<'static>,
    mir_production_17_21_caller: crate::experimental::cache::FunctionView<'static>,
    alias_production_17_21_0_view_source: crate::experimental::cache::FunctionView<'static>,
    alias_production_17_21_0_view_argument: crate::experimental::cache::FunctionView<'static>,
    alias_production_17_21_0_view_returned: crate::experimental::cache::FunctionView<'static>,
    alias_production_17_21_0_view_caller: crate::experimental::cache::FunctionView<'static>,
    alias_production_17_21_1_val_source: crate::experimental::cache::FunctionView<'static>,
    alias_production_17_21_1_val_argument: crate::experimental::cache::FunctionView<'static>,
    alias_production_17_21_1_val_returned: crate::experimental::cache::FunctionView<'static>,
    alias_production_17_21_1_val_caller: crate::experimental::cache::FunctionView<'static>,
    mir_production_17_22_source: crate::experimental::cache::DecodedInstruction,
    mir_production_17_22_argument: crate::experimental::cache::DecodedInstruction,
    mir_production_17_22_returned: crate::experimental::cache::DecodedInstruction,
    mir_production_17_22_caller: crate::experimental::cache::DecodedInstruction,
    alias_production_17_22_0_instruction_source: crate::experimental::cache::DecodedInstruction,
    alias_production_17_22_0_instruction_argument: crate::experimental::cache::DecodedInstruction,
    alias_production_17_22_0_instruction_returned: crate::experimental::cache::DecodedInstruction,
    alias_production_17_22_0_instruction_caller: crate::experimental::cache::DecodedInstruction,
    mir_production_17_26_source: &'static crate::experimental::cache::DecodedInstruction,
    mir_production_17_26_argument: &'static crate::experimental::cache::DecodedInstruction,
    mir_production_17_26_returned: &'static crate::experimental::cache::DecodedInstruction,
    mir_production_17_26_caller: &'static crate::experimental::cache::DecodedInstruction,
    alias_production_17_26_0_instruction_source: &'static crate::experimental::cache::DecodedInstruction,
    alias_production_17_26_0_instruction_argument: &'static crate::experimental::cache::DecodedInstruction,
    alias_production_17_26_0_instruction_returned: &'static crate::experimental::cache::DecodedInstruction,
    alias_production_17_26_0_instruction_caller: &'static crate::experimental::cache::DecodedInstruction,
    mir_production_17_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_17_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_17_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_17_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_17_1_0_phase_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_17_1_0_phase_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_17_1_0_phase_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_17_1_0_phase_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    literal_production_17_0_source: &'static str,
    literal_production_17_0_argument: &'static str,
    literal_production_17_0_returned: &'static str,
    literal_production_17_0_caller: &'static str,
    literal_production_17_1_source: &'static str,
    literal_production_17_1_argument: &'static str,
    literal_production_17_1_returned: &'static str,
    literal_production_17_1_caller: &'static str,
    literal_production_17_2_source: u8,
    literal_production_17_2_argument: u8,
    literal_production_17_2_returned: u8,
    literal_production_17_2_caller: u8,
    literal_production_17_3_source: u8,
    literal_production_17_3_argument: u8,
    literal_production_17_3_returned: u8,
    literal_production_17_3_caller: u8,
    literal_production_17_4_source: u8,
    literal_production_17_4_argument: u8,
    literal_production_17_4_returned: u8,
    literal_production_17_4_caller: u8,
    literal_production_17_5_source: u8,
    literal_production_17_5_argument: u8,
    literal_production_17_5_returned: u8,
    literal_production_17_5_caller: u8,
    literal_production_17_6_source: usize,
    literal_production_17_6_argument: usize,
    literal_production_17_6_returned: usize,
    literal_production_17_6_caller: usize,
    literal_production_17_7_source: &'static str,
    literal_production_17_7_argument: &'static str,
    literal_production_17_7_returned: &'static str,
    literal_production_17_7_caller: &'static str,
    literal_production_17_8_source: &'static str,
    literal_production_17_8_argument: &'static str,
    literal_production_17_8_returned: &'static str,
    literal_production_17_8_caller: &'static str,
    mir_production_18_0_source: std::option::Option<usize>,
    mir_production_18_0_argument: std::option::Option<usize>,
    mir_production_18_0_returned: std::option::Option<usize>,
    mir_production_18_0_caller: std::option::Option<usize>,
    mir_production_18_3_source: usize,
    mir_production_18_3_argument: usize,
    mir_production_18_3_returned: usize,
    mir_production_18_3_caller: usize,
    mir_production_18_1_source: (),
    mir_production_18_1_argument: (),
    mir_production_18_1_returned: (),
    mir_production_18_1_caller: (),
    mir_production_18_2_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_18_2_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_18_2_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_18_2_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_18_2_0_frame_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_18_2_0_frame_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_18_2_0_frame_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_18_2_0_frame_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    literal_production_18_0_source: usize,
    literal_production_18_0_argument: usize,
    literal_production_18_0_returned: usize,
    literal_production_18_0_caller: usize,
    mir_production_19_0_source: &'static Type,
    mir_production_19_0_argument: &'static Type,
    mir_production_19_0_returned: &'static Type,
    mir_production_19_0_caller: &'static Type,
    mir_production_19_1_source: Type,
    mir_production_19_1_argument: Type,
    mir_production_19_1_returned: Type,
    mir_production_19_1_caller: Type,
    mir_production_20_0_source: &'static std::ops::RangeInclusive<u8>,
    mir_production_20_0_argument: &'static std::ops::RangeInclusive<u8>,
    mir_production_20_0_returned: &'static std::ops::RangeInclusive<u8>,
    mir_production_20_0_caller: &'static std::ops::RangeInclusive<u8>,
    mir_production_20_1_source: std::ops::RangeInclusive<u8>,
    mir_production_20_1_argument: std::ops::RangeInclusive<u8>,
    mir_production_20_1_returned: std::ops::RangeInclusive<u8>,
    mir_production_20_1_caller: std::ops::RangeInclusive<u8>,
    literal_production_20_0_source: u8,
    literal_production_20_0_argument: u8,
    literal_production_20_0_returned: u8,
    literal_production_20_0_caller: u8,
    literal_production_20_1_source: u8,
    literal_production_20_1_argument: u8,
    literal_production_20_1_returned: u8,
    literal_production_20_1_caller: u8,
    #[cfg(test)]
    mir_unit_0_0_source: usize,
    #[cfg(test)]
    mir_unit_0_0_argument: usize,
    #[cfg(test)]
    mir_unit_0_0_returned: usize,
    #[cfg(test)]
    mir_unit_0_0_caller: usize,
    #[cfg(test)]
    mir_unit_0_1_source: u8,
    #[cfg(test)]
    mir_unit_0_1_argument: u8,
    #[cfg(test)]
    mir_unit_0_1_returned: u8,
    #[cfg(test)]
    mir_unit_0_1_caller: u8,
    #[cfg(test)]
    alias_unit_0_1_0_op_source: u8,
    #[cfg(test)]
    alias_unit_0_1_0_op_argument: u8,
    #[cfg(test)]
    alias_unit_0_1_0_op_returned: u8,
    #[cfg(test)]
    alias_unit_0_1_0_op_caller: u8,
    #[cfg(test)]
    literal_unit_0_0_source: usize,
    #[cfg(test)]
    literal_unit_0_0_argument: usize,
    #[cfg(test)]
    literal_unit_0_0_returned: usize,
    #[cfg(test)]
    literal_unit_0_0_caller: usize,
    #[cfg(test)]
    literal_unit_0_1_source: usize,
    #[cfg(test)]
    literal_unit_0_1_argument: usize,
    #[cfg(test)]
    literal_unit_0_1_returned: usize,
    #[cfg(test)]
    literal_unit_0_1_caller: usize,
    #[cfg(test)]
    literal_unit_0_2_source: usize,
    #[cfg(test)]
    literal_unit_0_2_argument: usize,
    #[cfg(test)]
    literal_unit_0_2_returned: usize,
    #[cfg(test)]
    literal_unit_0_2_caller: usize,
    #[cfg(test)]
    literal_unit_0_3_source: usize,
    #[cfg(test)]
    literal_unit_0_3_argument: usize,
    #[cfg(test)]
    literal_unit_0_3_returned: usize,
    #[cfg(test)]
    literal_unit_0_3_caller: usize,
    #[cfg(test)]
    mir_unit_1_0_source: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_0_argument: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_0_returned: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_0_caller: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_4_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    #[cfg(test)]
    mir_unit_1_4_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    #[cfg(test)]
    mir_unit_1_4_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    #[cfg(test)]
    mir_unit_1_4_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    #[cfg(test)]
    mir_unit_1_5_source: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_5_argument: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_5_returned: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_5_caller: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_6_source: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_1_6_argument: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_1_6_returned: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_1_6_caller: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_1_7_source: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_1_7_argument: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_1_7_returned: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_1_7_caller: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_1_8_source: (&'static std::vec::Vec<u8>,),
    #[cfg(test)]
    mir_unit_1_8_argument: (&'static std::vec::Vec<u8>,),
    #[cfg(test)]
    mir_unit_1_8_returned: (&'static std::vec::Vec<u8>,),
    #[cfg(test)]
    mir_unit_1_8_caller: (&'static std::vec::Vec<u8>,),
    #[cfg(test)]
    mir_unit_1_9_source: &'static std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_1_9_argument: &'static std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_1_9_returned: &'static std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_1_9_caller: &'static std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_1_10_source: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_1_10_argument: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_1_10_returned: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_1_10_caller: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_1_11_source: isize,
    #[cfg(test)]
    mir_unit_1_11_argument: isize,
    #[cfg(test)]
    mir_unit_1_11_returned: isize,
    #[cfg(test)]
    mir_unit_1_11_caller: isize,
    #[cfg(test)]
    mir_unit_1_12_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_12_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_12_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_12_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_12_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_12_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_12_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_12_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_13_source: usize,
    #[cfg(test)]
    mir_unit_1_13_argument: usize,
    #[cfg(test)]
    mir_unit_1_13_returned: usize,
    #[cfg(test)]
    mir_unit_1_13_caller: usize,
    #[cfg(test)]
    alias_unit_1_13_0_end_source: usize,
    #[cfg(test)]
    alias_unit_1_13_0_end_argument: usize,
    #[cfg(test)]
    alias_unit_1_13_0_end_returned: usize,
    #[cfg(test)]
    alias_unit_1_13_0_end_caller: usize,
    #[cfg(test)]
    alias_unit_1_13_1_val_source: usize,
    #[cfg(test)]
    alias_unit_1_13_1_val_argument: usize,
    #[cfg(test)]
    alias_unit_1_13_1_val_returned: usize,
    #[cfg(test)]
    alias_unit_1_13_1_val_caller: usize,
    #[cfg(test)]
    mir_unit_1_14_source: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_1_14_argument: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_1_14_returned: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_1_14_caller: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_1_15_source: &'static mut std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_1_15_argument: &'static mut std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_1_15_returned: &'static mut std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_1_15_caller: &'static mut std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_1_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_1_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_1_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_1_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_1_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_1_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_1_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_1_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_1_2_source: usize,
    #[cfg(test)]
    mir_unit_1_2_argument: usize,
    #[cfg(test)]
    mir_unit_1_2_returned: usize,
    #[cfg(test)]
    mir_unit_1_2_caller: usize,
    #[cfg(test)]
    alias_unit_1_2_0_address_source: usize,
    #[cfg(test)]
    alias_unit_1_2_0_address_argument: usize,
    #[cfg(test)]
    alias_unit_1_2_0_address_returned: usize,
    #[cfg(test)]
    alias_unit_1_2_0_address_caller: usize,
    #[cfg(test)]
    mir_unit_1_3_source: usize,
    #[cfg(test)]
    mir_unit_1_3_argument: usize,
    #[cfg(test)]
    mir_unit_1_3_returned: usize,
    #[cfg(test)]
    mir_unit_1_3_caller: usize,
    #[cfg(test)]
    alias_unit_1_3_0_len_source: usize,
    #[cfg(test)]
    alias_unit_1_3_0_len_argument: usize,
    #[cfg(test)]
    alias_unit_1_3_0_len_returned: usize,
    #[cfg(test)]
    alias_unit_1_3_0_len_caller: usize,
    #[cfg(test)]
    mir_unit_2_0_source: bool,
    #[cfg(test)]
    mir_unit_2_0_argument: bool,
    #[cfg(test)]
    mir_unit_2_0_returned: bool,
    #[cfg(test)]
    mir_unit_2_0_caller: bool,
    #[cfg(test)]
    mir_unit_2_3_source: usize,
    #[cfg(test)]
    mir_unit_2_3_argument: usize,
    #[cfg(test)]
    mir_unit_2_3_returned: usize,
    #[cfg(test)]
    mir_unit_2_3_caller: usize,
    #[cfg(test)]
    mir_unit_2_4_source: usize,
    #[cfg(test)]
    mir_unit_2_4_argument: usize,
    #[cfg(test)]
    mir_unit_2_4_returned: usize,
    #[cfg(test)]
    mir_unit_2_4_caller: usize,
    #[cfg(test)]
    mir_unit_2_5_source: &'static std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_2_5_argument: &'static std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_2_5_returned: &'static std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_2_5_caller: &'static std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_2_1_source: (&'static std::vec::Vec<u8>,),
    #[cfg(test)]
    mir_unit_2_1_argument: (&'static std::vec::Vec<u8>,),
    #[cfg(test)]
    mir_unit_2_1_returned: (&'static std::vec::Vec<u8>,),
    #[cfg(test)]
    mir_unit_2_1_caller: (&'static std::vec::Vec<u8>,),
    #[cfg(test)]
    mir_unit_2_2_source: &'static usize,
    #[cfg(test)]
    mir_unit_2_2_argument: &'static usize,
    #[cfg(test)]
    mir_unit_2_2_returned: &'static usize,
    #[cfg(test)]
    mir_unit_2_2_caller: &'static usize,
    #[cfg(test)]
    alias_unit_2_2_0_end_source: &'static usize,
    #[cfg(test)]
    alias_unit_2_2_0_end_argument: &'static usize,
    #[cfg(test)]
    alias_unit_2_2_0_end_returned: &'static usize,
    #[cfg(test)]
    alias_unit_2_2_0_end_caller: &'static usize,
    #[cfg(test)]
    mir_unit_3_0_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_0_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_0_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_0_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_2_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_3_2_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_3_2_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_3_2_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_3_1_source: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_3_1_argument: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_3_1_returned: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_3_1_caller: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_4_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_4_source: usize,
    #[cfg(test)]
    mir_unit_4_4_argument: usize,
    #[cfg(test)]
    mir_unit_4_4_returned: usize,
    #[cfg(test)]
    mir_unit_4_4_caller: usize,
    #[cfg(test)]
    alias_unit_4_4_0_address_source: usize,
    #[cfg(test)]
    alias_unit_4_4_0_address_argument: usize,
    #[cfg(test)]
    alias_unit_4_4_0_address_returned: usize,
    #[cfg(test)]
    alias_unit_4_4_0_address_caller: usize,
    #[cfg(test)]
    mir_unit_4_5_source: u32,
    #[cfg(test)]
    mir_unit_4_5_argument: u32,
    #[cfg(test)]
    mir_unit_4_5_returned: u32,
    #[cfg(test)]
    mir_unit_4_5_caller: u32,
    #[cfg(test)]
    mir_unit_4_6_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i32>,
    #[cfg(test)]
    mir_unit_4_6_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i32>,
    #[cfg(test)]
    mir_unit_4_6_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i32>,
    #[cfg(test)]
    mir_unit_4_6_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i32>,
    #[cfg(test)]
    mir_unit_4_7_source: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_7_argument: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_7_returned: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_7_caller: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_8_source: isize,
    #[cfg(test)]
    mir_unit_4_8_argument: isize,
    #[cfg(test)]
    mir_unit_4_8_returned: isize,
    #[cfg(test)]
    mir_unit_4_8_caller: isize,
    #[cfg(test)]
    mir_unit_4_9_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_9_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_9_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_9_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_4_9_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_4_9_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_4_9_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_4_9_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_10_source: i32,
    #[cfg(test)]
    mir_unit_4_10_argument: i32,
    #[cfg(test)]
    mir_unit_4_10_returned: i32,
    #[cfg(test)]
    mir_unit_4_10_caller: i32,
    #[cfg(test)]
    alias_unit_4_10_0_val_source: i32,
    #[cfg(test)]
    alias_unit_4_10_0_val_argument: i32,
    #[cfg(test)]
    alias_unit_4_10_0_val_returned: i32,
    #[cfg(test)]
    alias_unit_4_10_0_val_caller: i32,
    #[cfg(test)]
    mir_unit_4_12_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    #[cfg(test)]
    mir_unit_4_12_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    #[cfg(test)]
    mir_unit_4_12_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    #[cfg(test)]
    mir_unit_4_12_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    #[cfg(test)]
    mir_unit_4_13_source: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_13_argument: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_13_returned: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_13_caller: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_14_source: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_4_14_argument: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_4_14_returned: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_4_14_caller: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_4_15_source: usize,
    #[cfg(test)]
    mir_unit_4_15_argument: usize,
    #[cfg(test)]
    mir_unit_4_15_returned: usize,
    #[cfg(test)]
    mir_unit_4_15_caller: usize,
    #[cfg(test)]
    mir_unit_4_16_source: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_4_16_argument: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_4_16_returned: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_4_16_caller: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_4_17_source: isize,
    #[cfg(test)]
    mir_unit_4_17_argument: isize,
    #[cfg(test)]
    mir_unit_4_17_returned: isize,
    #[cfg(test)]
    mir_unit_4_17_caller: isize,
    #[cfg(test)]
    mir_unit_4_20_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::ops::Range<usize>>,
    #[cfg(test)]
    mir_unit_4_20_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::ops::Range<usize>>,
    #[cfg(test)]
    mir_unit_4_20_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::ops::Range<usize>>,
    #[cfg(test)]
    mir_unit_4_20_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::ops::Range<usize>>,
    #[cfg(test)]
    mir_unit_4_21_source: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_21_argument: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_21_returned: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_21_caller: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_22_source: isize,
    #[cfg(test)]
    mir_unit_4_22_argument: isize,
    #[cfg(test)]
    mir_unit_4_22_returned: isize,
    #[cfg(test)]
    mir_unit_4_22_caller: isize,
    #[cfg(test)]
    mir_unit_4_25_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_4_25_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_4_25_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_4_25_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_4_26_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_26_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_26_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_26_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_27_source: isize,
    #[cfg(test)]
    mir_unit_4_27_argument: isize,
    #[cfg(test)]
    mir_unit_4_27_returned: isize,
    #[cfg(test)]
    mir_unit_4_27_caller: isize,
    #[cfg(test)]
    mir_unit_4_30_source: (),
    #[cfg(test)]
    mir_unit_4_30_argument: (),
    #[cfg(test)]
    mir_unit_4_30_returned: (),
    #[cfg(test)]
    mir_unit_4_30_caller: (),
    #[cfg(test)]
    mir_unit_4_31_source: &'static mut [u8],
    #[cfg(test)]
    mir_unit_4_31_argument: &'static mut [u8],
    #[cfg(test)]
    mir_unit_4_31_returned: &'static mut [u8],
    #[cfg(test)]
    mir_unit_4_31_caller: &'static mut [u8],
    #[cfg(test)]
    mir_unit_4_32_source: &'static mut [u8; 8],
    #[cfg(test)]
    mir_unit_4_32_argument: &'static mut [u8; 8],
    #[cfg(test)]
    mir_unit_4_32_returned: &'static mut [u8; 8],
    #[cfg(test)]
    mir_unit_4_32_caller: &'static mut [u8; 8],
    #[cfg(test)]
    mir_unit_4_33_source: std::ops::RangeTo<usize>,
    #[cfg(test)]
    mir_unit_4_33_argument: std::ops::RangeTo<usize>,
    #[cfg(test)]
    mir_unit_4_33_returned: std::ops::RangeTo<usize>,
    #[cfg(test)]
    mir_unit_4_33_caller: std::ops::RangeTo<usize>,
    #[cfg(test)]
    mir_unit_4_34_source: &'static [u8],
    #[cfg(test)]
    mir_unit_4_34_argument: &'static [u8],
    #[cfg(test)]
    mir_unit_4_34_returned: &'static [u8],
    #[cfg(test)]
    mir_unit_4_34_caller: &'static [u8],
    #[cfg(test)]
    mir_unit_4_35_source: &'static std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_4_35_argument: &'static std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_4_35_returned: &'static std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_4_35_caller: &'static std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_4_37_source: [u8; 8],
    #[cfg(test)]
    mir_unit_4_37_argument: [u8; 8],
    #[cfg(test)]
    mir_unit_4_37_returned: [u8; 8],
    #[cfg(test)]
    mir_unit_4_37_caller: [u8; 8],
    #[cfg(test)]
    mir_unit_4_39_source: i32,
    #[cfg(test)]
    mir_unit_4_39_argument: i32,
    #[cfg(test)]
    mir_unit_4_39_returned: i32,
    #[cfg(test)]
    mir_unit_4_39_caller: i32,
    #[cfg(test)]
    mir_unit_4_40_source: i64,
    #[cfg(test)]
    mir_unit_4_40_argument: i64,
    #[cfg(test)]
    mir_unit_4_40_returned: i64,
    #[cfg(test)]
    mir_unit_4_40_caller: i64,
    #[cfg(test)]
    mir_unit_4_41_source: u32,
    #[cfg(test)]
    mir_unit_4_41_argument: u32,
    #[cfg(test)]
    mir_unit_4_41_returned: u32,
    #[cfg(test)]
    mir_unit_4_41_caller: u32,
    #[cfg(test)]
    mir_unit_4_42_source: i32,
    #[cfg(test)]
    mir_unit_4_42_argument: i32,
    #[cfg(test)]
    mir_unit_4_42_returned: i32,
    #[cfg(test)]
    mir_unit_4_42_caller: i32,
    #[cfg(test)]
    mir_unit_4_43_source: i8,
    #[cfg(test)]
    mir_unit_4_43_argument: i8,
    #[cfg(test)]
    mir_unit_4_43_returned: i8,
    #[cfg(test)]
    mir_unit_4_43_caller: i8,
    #[cfg(test)]
    mir_unit_4_44_source: i32,
    #[cfg(test)]
    mir_unit_4_44_argument: i32,
    #[cfg(test)]
    mir_unit_4_44_returned: i32,
    #[cfg(test)]
    mir_unit_4_44_caller: i32,
    #[cfg(test)]
    mir_unit_4_45_source: u8,
    #[cfg(test)]
    mir_unit_4_45_argument: u8,
    #[cfg(test)]
    mir_unit_4_45_returned: u8,
    #[cfg(test)]
    mir_unit_4_45_caller: u8,
    #[cfg(test)]
    mir_unit_4_46_source: i32,
    #[cfg(test)]
    mir_unit_4_46_argument: i32,
    #[cfg(test)]
    mir_unit_4_46_returned: i32,
    #[cfg(test)]
    mir_unit_4_46_caller: i32,
    #[cfg(test)]
    mir_unit_4_47_source: i16,
    #[cfg(test)]
    mir_unit_4_47_argument: i16,
    #[cfg(test)]
    mir_unit_4_47_returned: i16,
    #[cfg(test)]
    mir_unit_4_47_caller: i16,
    #[cfg(test)]
    mir_unit_4_48_source: i32,
    #[cfg(test)]
    mir_unit_4_48_argument: i32,
    #[cfg(test)]
    mir_unit_4_48_returned: i32,
    #[cfg(test)]
    mir_unit_4_48_caller: i32,
    #[cfg(test)]
    mir_unit_4_49_source: u16,
    #[cfg(test)]
    mir_unit_4_49_argument: u16,
    #[cfg(test)]
    mir_unit_4_49_returned: u16,
    #[cfg(test)]
    mir_unit_4_49_caller: u16,
    #[cfg(test)]
    mir_unit_4_50_source: i64,
    #[cfg(test)]
    mir_unit_4_50_argument: i64,
    #[cfg(test)]
    mir_unit_4_50_returned: i64,
    #[cfg(test)]
    mir_unit_4_50_caller: i64,
    #[cfg(test)]
    mir_unit_4_51_source: i8,
    #[cfg(test)]
    mir_unit_4_51_argument: i8,
    #[cfg(test)]
    mir_unit_4_51_returned: i8,
    #[cfg(test)]
    mir_unit_4_51_caller: i8,
    #[cfg(test)]
    mir_unit_4_52_source: i64,
    #[cfg(test)]
    mir_unit_4_52_argument: i64,
    #[cfg(test)]
    mir_unit_4_52_returned: i64,
    #[cfg(test)]
    mir_unit_4_52_caller: i64,
    #[cfg(test)]
    mir_unit_4_53_source: u8,
    #[cfg(test)]
    mir_unit_4_53_argument: u8,
    #[cfg(test)]
    mir_unit_4_53_returned: u8,
    #[cfg(test)]
    mir_unit_4_53_caller: u8,
    #[cfg(test)]
    mir_unit_4_54_source: i64,
    #[cfg(test)]
    mir_unit_4_54_argument: i64,
    #[cfg(test)]
    mir_unit_4_54_returned: i64,
    #[cfg(test)]
    mir_unit_4_54_caller: i64,
    #[cfg(test)]
    mir_unit_4_55_source: i16,
    #[cfg(test)]
    mir_unit_4_55_argument: i16,
    #[cfg(test)]
    mir_unit_4_55_returned: i16,
    #[cfg(test)]
    mir_unit_4_55_caller: i16,
    #[cfg(test)]
    mir_unit_4_56_source: i64,
    #[cfg(test)]
    mir_unit_4_56_argument: i64,
    #[cfg(test)]
    mir_unit_4_56_returned: i64,
    #[cfg(test)]
    mir_unit_4_56_caller: i64,
    #[cfg(test)]
    mir_unit_4_57_source: u16,
    #[cfg(test)]
    mir_unit_4_57_argument: u16,
    #[cfg(test)]
    mir_unit_4_57_returned: u16,
    #[cfg(test)]
    mir_unit_4_57_caller: u16,
    #[cfg(test)]
    mir_unit_4_58_source: i64,
    #[cfg(test)]
    mir_unit_4_58_argument: i64,
    #[cfg(test)]
    mir_unit_4_58_returned: i64,
    #[cfg(test)]
    mir_unit_4_58_caller: i64,
    #[cfg(test)]
    mir_unit_4_59_source: i32,
    #[cfg(test)]
    mir_unit_4_59_argument: i32,
    #[cfg(test)]
    mir_unit_4_59_returned: i32,
    #[cfg(test)]
    mir_unit_4_59_caller: i32,
    #[cfg(test)]
    mir_unit_4_60_source: i64,
    #[cfg(test)]
    mir_unit_4_60_argument: i64,
    #[cfg(test)]
    mir_unit_4_60_returned: i64,
    #[cfg(test)]
    mir_unit_4_60_caller: i64,
    #[cfg(test)]
    mir_unit_4_61_source: u32,
    #[cfg(test)]
    mir_unit_4_61_argument: u32,
    #[cfg(test)]
    mir_unit_4_61_returned: u32,
    #[cfg(test)]
    mir_unit_4_61_caller: u32,
    #[cfg(test)]
    mir_unit_4_62_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_4_62_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_4_62_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_4_62_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_4_63_source: Value,
    #[cfg(test)]
    mir_unit_4_63_argument: Value,
    #[cfg(test)]
    mir_unit_4_63_returned: Value,
    #[cfg(test)]
    mir_unit_4_63_caller: Value,
    #[cfg(test)]
    mir_unit_4_64_source: &'static mut std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_4_64_argument: &'static mut std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_4_64_returned: &'static mut std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_4_64_caller: &'static mut std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_4_11_source: usize,
    #[cfg(test)]
    mir_unit_4_11_argument: usize,
    #[cfg(test)]
    mir_unit_4_11_returned: usize,
    #[cfg(test)]
    mir_unit_4_11_caller: usize,
    #[cfg(test)]
    alias_unit_4_11_0_width_source: usize,
    #[cfg(test)]
    alias_unit_4_11_0_width_argument: usize,
    #[cfg(test)]
    alias_unit_4_11_0_width_returned: usize,
    #[cfg(test)]
    alias_unit_4_11_0_width_caller: usize,
    #[cfg(test)]
    mir_unit_4_18_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_18_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_18_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_18_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_4_18_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_4_18_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_4_18_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_4_18_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_19_source: usize,
    #[cfg(test)]
    mir_unit_4_19_argument: usize,
    #[cfg(test)]
    mir_unit_4_19_returned: usize,
    #[cfg(test)]
    mir_unit_4_19_caller: usize,
    #[cfg(test)]
    alias_unit_4_19_0_start_source: usize,
    #[cfg(test)]
    alias_unit_4_19_0_start_argument: usize,
    #[cfg(test)]
    alias_unit_4_19_0_start_returned: usize,
    #[cfg(test)]
    alias_unit_4_19_0_start_caller: usize,
    #[cfg(test)]
    alias_unit_4_19_1_val_source: usize,
    #[cfg(test)]
    alias_unit_4_19_1_val_argument: usize,
    #[cfg(test)]
    alias_unit_4_19_1_val_returned: usize,
    #[cfg(test)]
    alias_unit_4_19_1_val_caller: usize,
    #[cfg(test)]
    mir_unit_4_23_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_23_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_23_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_23_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_4_23_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_4_23_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_4_23_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_4_23_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_24_source: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_4_24_argument: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_4_24_returned: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_4_24_caller: std::ops::Range<usize>,
    #[cfg(test)]
    alias_unit_4_24_0_range_source: std::ops::Range<usize>,
    #[cfg(test)]
    alias_unit_4_24_0_range_argument: std::ops::Range<usize>,
    #[cfg(test)]
    alias_unit_4_24_0_range_returned: std::ops::Range<usize>,
    #[cfg(test)]
    alias_unit_4_24_0_range_caller: std::ops::Range<usize>,
    #[cfg(test)]
    alias_unit_4_24_1_val_source: std::ops::Range<usize>,
    #[cfg(test)]
    alias_unit_4_24_1_val_argument: std::ops::Range<usize>,
    #[cfg(test)]
    alias_unit_4_24_1_val_returned: std::ops::Range<usize>,
    #[cfg(test)]
    alias_unit_4_24_1_val_caller: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_4_28_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_28_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_28_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_28_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_4_28_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_4_28_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_4_28_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_4_28_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_4_29_source: [u8; 8],
    #[cfg(test)]
    mir_unit_4_29_argument: [u8; 8],
    #[cfg(test)]
    mir_unit_4_29_returned: [u8; 8],
    #[cfg(test)]
    mir_unit_4_29_caller: [u8; 8],
    #[cfg(test)]
    alias_unit_4_29_0_padded_source: [u8; 8],
    #[cfg(test)]
    alias_unit_4_29_0_padded_argument: [u8; 8],
    #[cfg(test)]
    alias_unit_4_29_0_padded_returned: [u8; 8],
    #[cfg(test)]
    alias_unit_4_29_0_padded_caller: [u8; 8],
    #[cfg(test)]
    mir_unit_4_36_source: u64,
    #[cfg(test)]
    mir_unit_4_36_argument: u64,
    #[cfg(test)]
    mir_unit_4_36_returned: u64,
    #[cfg(test)]
    mir_unit_4_36_caller: u64,
    #[cfg(test)]
    alias_unit_4_36_0_x_source: u64,
    #[cfg(test)]
    alias_unit_4_36_0_x_argument: u64,
    #[cfg(test)]
    alias_unit_4_36_0_x_returned: u64,
    #[cfg(test)]
    alias_unit_4_36_0_x_caller: u64,
    #[cfg(test)]
    mir_unit_4_38_source: Value,
    #[cfg(test)]
    mir_unit_4_38_argument: Value,
    #[cfg(test)]
    mir_unit_4_38_returned: Value,
    #[cfg(test)]
    mir_unit_4_38_caller: Value,
    #[cfg(test)]
    alias_unit_4_38_0_value_source: Value,
    #[cfg(test)]
    alias_unit_4_38_0_value_argument: Value,
    #[cfg(test)]
    alias_unit_4_38_0_value_returned: Value,
    #[cfg(test)]
    alias_unit_4_38_0_value_caller: Value,
    #[cfg(test)]
    mir_unit_4_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_4_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_4_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_4_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_4_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_4_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_4_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_4_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_4_2_source: u8,
    #[cfg(test)]
    mir_unit_4_2_argument: u8,
    #[cfg(test)]
    mir_unit_4_2_returned: u8,
    #[cfg(test)]
    mir_unit_4_2_caller: u8,
    #[cfg(test)]
    alias_unit_4_2_0_opcode_source: u8,
    #[cfg(test)]
    alias_unit_4_2_0_opcode_argument: u8,
    #[cfg(test)]
    alias_unit_4_2_0_opcode_returned: u8,
    #[cfg(test)]
    alias_unit_4_2_0_opcode_caller: u8,
    #[cfg(test)]
    mir_unit_4_3_source: u32,
    #[cfg(test)]
    mir_unit_4_3_argument: u32,
    #[cfg(test)]
    mir_unit_4_3_returned: u32,
    #[cfg(test)]
    mir_unit_4_3_caller: u32,
    #[cfg(test)]
    alias_unit_4_3_0_offset_source: u32,
    #[cfg(test)]
    alias_unit_4_3_0_offset_argument: u32,
    #[cfg(test)]
    alias_unit_4_3_0_offset_returned: u32,
    #[cfg(test)]
    alias_unit_4_3_0_offset_caller: u32,
    #[cfg(test)]
    literal_unit_4_0_source: u8,
    #[cfg(test)]
    literal_unit_4_0_argument: u8,
    #[cfg(test)]
    literal_unit_4_0_returned: u8,
    #[cfg(test)]
    literal_unit_4_0_caller: u8,
    #[cfg(test)]
    literal_unit_4_1_source: &'static str,
    #[cfg(test)]
    literal_unit_4_1_argument: &'static str,
    #[cfg(test)]
    literal_unit_4_1_returned: &'static str,
    #[cfg(test)]
    literal_unit_4_1_caller: &'static str,
    #[cfg(test)]
    mir_unit_5_0_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_5_0_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_5_0_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_5_0_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_5_2_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_5_2_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_5_2_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_5_2_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_5_1_source: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_5_1_argument: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_5_1_returned: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_5_1_caller: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_6_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_4_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>,
    #[cfg(test)]
    mir_unit_6_4_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>,
    #[cfg(test)]
    mir_unit_6_4_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>,
    #[cfg(test)]
    mir_unit_6_4_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>,
    #[cfg(test)]
    mir_unit_6_5_source: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_5_argument: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_5_returned: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_5_caller: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_6_source: isize,
    #[cfg(test)]
    mir_unit_6_6_argument: isize,
    #[cfg(test)]
    mir_unit_6_6_returned: isize,
    #[cfg(test)]
    mir_unit_6_6_caller: isize,
    #[cfg(test)]
    mir_unit_6_7_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_7_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_7_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_7_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_6_7_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_6_7_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_6_7_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_6_7_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_8_source: Value,
    #[cfg(test)]
    mir_unit_6_8_argument: Value,
    #[cfg(test)]
    mir_unit_6_8_returned: Value,
    #[cfg(test)]
    mir_unit_6_8_caller: Value,
    #[cfg(test)]
    alias_unit_6_8_0_value_source: Value,
    #[cfg(test)]
    alias_unit_6_8_0_value_argument: Value,
    #[cfg(test)]
    alias_unit_6_8_0_value_returned: Value,
    #[cfg(test)]
    alias_unit_6_8_0_value_caller: Value,
    #[cfg(test)]
    alias_unit_6_8_1_val_source: Value,
    #[cfg(test)]
    alias_unit_6_8_1_val_argument: Value,
    #[cfg(test)]
    alias_unit_6_8_1_val_returned: Value,
    #[cfg(test)]
    alias_unit_6_8_1_val_caller: Value,
    #[cfg(test)]
    mir_unit_6_10_source: u32,
    #[cfg(test)]
    mir_unit_6_10_argument: u32,
    #[cfg(test)]
    mir_unit_6_10_returned: u32,
    #[cfg(test)]
    mir_unit_6_10_caller: u32,
    #[cfg(test)]
    mir_unit_6_11_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i32>,
    #[cfg(test)]
    mir_unit_6_11_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i32>,
    #[cfg(test)]
    mir_unit_6_11_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i32>,
    #[cfg(test)]
    mir_unit_6_11_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i32>,
    #[cfg(test)]
    mir_unit_6_12_source: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_12_argument: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_12_returned: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_12_caller: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_13_source: isize,
    #[cfg(test)]
    mir_unit_6_13_argument: isize,
    #[cfg(test)]
    mir_unit_6_13_returned: isize,
    #[cfg(test)]
    mir_unit_6_13_caller: isize,
    #[cfg(test)]
    mir_unit_6_17_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    #[cfg(test)]
    mir_unit_6_17_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    #[cfg(test)]
    mir_unit_6_17_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    #[cfg(test)]
    mir_unit_6_17_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    #[cfg(test)]
    mir_unit_6_18_source: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_18_argument: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_18_returned: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_18_caller: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_19_source: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_6_19_argument: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_6_19_returned: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_6_19_caller: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_6_20_source: usize,
    #[cfg(test)]
    mir_unit_6_20_argument: usize,
    #[cfg(test)]
    mir_unit_6_20_returned: usize,
    #[cfg(test)]
    mir_unit_6_20_caller: usize,
    #[cfg(test)]
    mir_unit_6_21_source: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_6_21_argument: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_6_21_returned: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_6_21_caller: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_6_22_source: isize,
    #[cfg(test)]
    mir_unit_6_22_argument: isize,
    #[cfg(test)]
    mir_unit_6_22_returned: isize,
    #[cfg(test)]
    mir_unit_6_22_caller: isize,
    #[cfg(test)]
    mir_unit_6_25_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::ops::Range<usize>>,
    #[cfg(test)]
    mir_unit_6_25_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::ops::Range<usize>>,
    #[cfg(test)]
    mir_unit_6_25_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::ops::Range<usize>>,
    #[cfg(test)]
    mir_unit_6_25_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::ops::Range<usize>>,
    #[cfg(test)]
    mir_unit_6_26_source: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_26_argument: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_26_returned: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_26_caller: std::result::Result<std::ops::Range<usize>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_27_source: isize,
    #[cfg(test)]
    mir_unit_6_27_argument: isize,
    #[cfg(test)]
    mir_unit_6_27_returned: isize,
    #[cfg(test)]
    mir_unit_6_27_caller: isize,
    #[cfg(test)]
    mir_unit_6_30_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_6_30_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_6_30_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_6_30_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_6_31_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_31_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_31_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_31_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_32_source: isize,
    #[cfg(test)]
    mir_unit_6_32_argument: isize,
    #[cfg(test)]
    mir_unit_6_32_returned: isize,
    #[cfg(test)]
    mir_unit_6_32_caller: isize,
    #[cfg(test)]
    mir_unit_6_35_source: isize,
    #[cfg(test)]
    mir_unit_6_35_argument: isize,
    #[cfg(test)]
    mir_unit_6_35_returned: isize,
    #[cfg(test)]
    mir_unit_6_35_caller: isize,
    #[cfg(test)]
    mir_unit_6_37_source: u32,
    #[cfg(test)]
    mir_unit_6_37_argument: u32,
    #[cfg(test)]
    mir_unit_6_37_returned: u32,
    #[cfg(test)]
    mir_unit_6_37_caller: u32,
    #[cfg(test)]
    mir_unit_6_41_source: (),
    #[cfg(test)]
    mir_unit_6_41_argument: (),
    #[cfg(test)]
    mir_unit_6_41_returned: (),
    #[cfg(test)]
    mir_unit_6_41_caller: (),
    #[cfg(test)]
    mir_unit_6_42_source: &'static mut [u8],
    #[cfg(test)]
    mir_unit_6_42_argument: &'static mut [u8],
    #[cfg(test)]
    mir_unit_6_42_returned: &'static mut [u8],
    #[cfg(test)]
    mir_unit_6_42_caller: &'static mut [u8],
    #[cfg(test)]
    mir_unit_6_43_source: &'static [u8],
    #[cfg(test)]
    mir_unit_6_43_argument: &'static [u8],
    #[cfg(test)]
    mir_unit_6_43_returned: &'static [u8],
    #[cfg(test)]
    mir_unit_6_43_caller: &'static [u8],
    #[cfg(test)]
    mir_unit_6_44_source: &'static [u8; 8],
    #[cfg(test)]
    mir_unit_6_44_argument: &'static [u8; 8],
    #[cfg(test)]
    mir_unit_6_44_returned: &'static [u8; 8],
    #[cfg(test)]
    mir_unit_6_44_caller: &'static [u8; 8],
    #[cfg(test)]
    mir_unit_6_45_source: [u8; 8],
    #[cfg(test)]
    mir_unit_6_45_argument: [u8; 8],
    #[cfg(test)]
    mir_unit_6_45_returned: [u8; 8],
    #[cfg(test)]
    mir_unit_6_45_caller: [u8; 8],
    #[cfg(test)]
    mir_unit_6_46_source: u64,
    #[cfg(test)]
    mir_unit_6_46_argument: u64,
    #[cfg(test)]
    mir_unit_6_46_returned: u64,
    #[cfg(test)]
    mir_unit_6_46_caller: u64,
    #[cfg(test)]
    mir_unit_6_47_source: std::ops::RangeTo<usize>,
    #[cfg(test)]
    mir_unit_6_47_argument: std::ops::RangeTo<usize>,
    #[cfg(test)]
    mir_unit_6_47_returned: std::ops::RangeTo<usize>,
    #[cfg(test)]
    mir_unit_6_47_caller: std::ops::RangeTo<usize>,
    #[cfg(test)]
    mir_unit_6_48_source: &'static mut std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_6_48_argument: &'static mut std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_6_48_returned: &'static mut std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_6_48_caller: &'static mut std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_6_9_source: usize,
    #[cfg(test)]
    mir_unit_6_9_argument: usize,
    #[cfg(test)]
    mir_unit_6_9_returned: usize,
    #[cfg(test)]
    mir_unit_6_9_caller: usize,
    #[cfg(test)]
    alias_unit_6_9_0_address_source: usize,
    #[cfg(test)]
    alias_unit_6_9_0_address_argument: usize,
    #[cfg(test)]
    alias_unit_6_9_0_address_returned: usize,
    #[cfg(test)]
    alias_unit_6_9_0_address_caller: usize,
    #[cfg(test)]
    mir_unit_6_14_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_14_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_14_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_14_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_6_14_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_6_14_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_6_14_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_6_14_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_15_source: i32,
    #[cfg(test)]
    mir_unit_6_15_argument: i32,
    #[cfg(test)]
    mir_unit_6_15_returned: i32,
    #[cfg(test)]
    mir_unit_6_15_caller: i32,
    #[cfg(test)]
    alias_unit_6_15_0_val_source: i32,
    #[cfg(test)]
    alias_unit_6_15_0_val_argument: i32,
    #[cfg(test)]
    alias_unit_6_15_0_val_returned: i32,
    #[cfg(test)]
    alias_unit_6_15_0_val_caller: i32,
    #[cfg(test)]
    mir_unit_6_16_source: usize,
    #[cfg(test)]
    mir_unit_6_16_argument: usize,
    #[cfg(test)]
    mir_unit_6_16_returned: usize,
    #[cfg(test)]
    mir_unit_6_16_caller: usize,
    #[cfg(test)]
    alias_unit_6_16_0_width_source: usize,
    #[cfg(test)]
    alias_unit_6_16_0_width_argument: usize,
    #[cfg(test)]
    alias_unit_6_16_0_width_returned: usize,
    #[cfg(test)]
    alias_unit_6_16_0_width_caller: usize,
    #[cfg(test)]
    mir_unit_6_23_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_23_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_23_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_23_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_6_23_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_6_23_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_6_23_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_6_23_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_24_source: usize,
    #[cfg(test)]
    mir_unit_6_24_argument: usize,
    #[cfg(test)]
    mir_unit_6_24_returned: usize,
    #[cfg(test)]
    mir_unit_6_24_caller: usize,
    #[cfg(test)]
    alias_unit_6_24_0_start_source: usize,
    #[cfg(test)]
    alias_unit_6_24_0_start_argument: usize,
    #[cfg(test)]
    alias_unit_6_24_0_start_returned: usize,
    #[cfg(test)]
    alias_unit_6_24_0_start_caller: usize,
    #[cfg(test)]
    alias_unit_6_24_1_val_source: usize,
    #[cfg(test)]
    alias_unit_6_24_1_val_argument: usize,
    #[cfg(test)]
    alias_unit_6_24_1_val_returned: usize,
    #[cfg(test)]
    alias_unit_6_24_1_val_caller: usize,
    #[cfg(test)]
    mir_unit_6_28_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_28_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_28_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_28_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_6_28_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_6_28_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_6_28_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_6_28_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_29_source: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_6_29_argument: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_6_29_returned: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_6_29_caller: std::ops::Range<usize>,
    #[cfg(test)]
    alias_unit_6_29_0_range_source: std::ops::Range<usize>,
    #[cfg(test)]
    alias_unit_6_29_0_range_argument: std::ops::Range<usize>,
    #[cfg(test)]
    alias_unit_6_29_0_range_returned: std::ops::Range<usize>,
    #[cfg(test)]
    alias_unit_6_29_0_range_caller: std::ops::Range<usize>,
    #[cfg(test)]
    alias_unit_6_29_1_val_source: std::ops::Range<usize>,
    #[cfg(test)]
    alias_unit_6_29_1_val_argument: std::ops::Range<usize>,
    #[cfg(test)]
    alias_unit_6_29_1_val_returned: std::ops::Range<usize>,
    #[cfg(test)]
    alias_unit_6_29_1_val_caller: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_6_33_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_33_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_33_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_33_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_6_33_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_6_33_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_6_33_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_6_33_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_6_34_source: u64,
    #[cfg(test)]
    mir_unit_6_34_argument: u64,
    #[cfg(test)]
    mir_unit_6_34_returned: u64,
    #[cfg(test)]
    mir_unit_6_34_caller: u64,
    #[cfg(test)]
    alias_unit_6_34_0_bits_source: u64,
    #[cfg(test)]
    alias_unit_6_34_0_bits_argument: u64,
    #[cfg(test)]
    alias_unit_6_34_0_bits_returned: u64,
    #[cfg(test)]
    alias_unit_6_34_0_bits_caller: u64,
    #[cfg(test)]
    mir_unit_6_36_source: i32,
    #[cfg(test)]
    mir_unit_6_36_argument: i32,
    #[cfg(test)]
    mir_unit_6_36_returned: i32,
    #[cfg(test)]
    mir_unit_6_36_caller: i32,
    #[cfg(test)]
    alias_unit_6_36_0_x_source: i32,
    #[cfg(test)]
    alias_unit_6_36_0_x_argument: i32,
    #[cfg(test)]
    alias_unit_6_36_0_x_returned: i32,
    #[cfg(test)]
    alias_unit_6_36_0_x_caller: i32,
    #[cfg(test)]
    mir_unit_6_38_source: i64,
    #[cfg(test)]
    mir_unit_6_38_argument: i64,
    #[cfg(test)]
    mir_unit_6_38_returned: i64,
    #[cfg(test)]
    mir_unit_6_38_caller: i64,
    #[cfg(test)]
    alias_unit_6_38_0_x_source: i64,
    #[cfg(test)]
    alias_unit_6_38_0_x_argument: i64,
    #[cfg(test)]
    alias_unit_6_38_0_x_returned: i64,
    #[cfg(test)]
    alias_unit_6_38_0_x_caller: i64,
    #[cfg(test)]
    mir_unit_6_39_source: u32,
    #[cfg(test)]
    mir_unit_6_39_argument: u32,
    #[cfg(test)]
    mir_unit_6_39_returned: u32,
    #[cfg(test)]
    mir_unit_6_39_caller: u32,
    #[cfg(test)]
    alias_unit_6_39_0_x_source: u32,
    #[cfg(test)]
    alias_unit_6_39_0_x_argument: u32,
    #[cfg(test)]
    alias_unit_6_39_0_x_returned: u32,
    #[cfg(test)]
    alias_unit_6_39_0_x_caller: u32,
    #[cfg(test)]
    mir_unit_6_40_source: u64,
    #[cfg(test)]
    mir_unit_6_40_argument: u64,
    #[cfg(test)]
    mir_unit_6_40_returned: u64,
    #[cfg(test)]
    mir_unit_6_40_caller: u64,
    #[cfg(test)]
    alias_unit_6_40_0_x_source: u64,
    #[cfg(test)]
    alias_unit_6_40_0_x_argument: u64,
    #[cfg(test)]
    alias_unit_6_40_0_x_returned: u64,
    #[cfg(test)]
    alias_unit_6_40_0_x_caller: u64,
    #[cfg(test)]
    mir_unit_6_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_6_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_6_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_6_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_6_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_6_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_6_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_6_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_6_2_source: u8,
    #[cfg(test)]
    mir_unit_6_2_argument: u8,
    #[cfg(test)]
    mir_unit_6_2_returned: u8,
    #[cfg(test)]
    mir_unit_6_2_caller: u8,
    #[cfg(test)]
    alias_unit_6_2_0_opcode_source: u8,
    #[cfg(test)]
    alias_unit_6_2_0_opcode_argument: u8,
    #[cfg(test)]
    alias_unit_6_2_0_opcode_returned: u8,
    #[cfg(test)]
    alias_unit_6_2_0_opcode_caller: u8,
    #[cfg(test)]
    mir_unit_6_3_source: u32,
    #[cfg(test)]
    mir_unit_6_3_argument: u32,
    #[cfg(test)]
    mir_unit_6_3_returned: u32,
    #[cfg(test)]
    mir_unit_6_3_caller: u32,
    #[cfg(test)]
    alias_unit_6_3_0_offset_source: u32,
    #[cfg(test)]
    alias_unit_6_3_0_offset_argument: u32,
    #[cfg(test)]
    alias_unit_6_3_0_offset_returned: u32,
    #[cfg(test)]
    alias_unit_6_3_0_offset_caller: u32,
    #[cfg(test)]
    mir_unit_7_0_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_7_0_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_7_0_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_7_0_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_7_2_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_7_2_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_7_2_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_7_2_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_7_1_source: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_7_1_argument: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_7_1_returned: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_7_1_caller: (&'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,),
    #[cfg(test)]
    mir_unit_8_0_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_8_0_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_8_0_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_8_0_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_8_2_source: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_8_2_argument: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_8_2_returned: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_8_2_caller: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_8_3_source: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_8_3_argument: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_8_3_returned: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_8_3_caller: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_8_4_source: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_8_4_argument: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_8_4_returned: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_8_4_caller: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_8_5_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_8_5_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_8_5_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_8_5_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_8_6_source: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_8_6_argument: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_8_6_returned: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_8_6_caller: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_8_7_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_8_7_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_8_7_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_8_7_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_8_8_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_8_8_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_8_8_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_8_8_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_8_9_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_8_9_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_8_9_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_8_9_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_8_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_8_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_8_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_8_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_8_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_8_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_8_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_8_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    literal_unit_8_0_source: &'static str,
    #[cfg(test)]
    literal_unit_8_0_argument: &'static str,
    #[cfg(test)]
    literal_unit_8_0_returned: &'static str,
    #[cfg(test)]
    literal_unit_8_0_caller: &'static str,
    #[cfg(test)]
    mir_unit_9_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_9_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_9_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_9_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_9_0_0_result_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_9_0_0_result_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_9_0_0_result_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_9_0_0_result_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_9_3_source: std::option::Option<(u8, u64)>,
    #[cfg(test)]
    mir_unit_9_3_argument: std::option::Option<(u8, u64)>,
    #[cfg(test)]
    mir_unit_9_3_returned: std::option::Option<(u8, u64)>,
    #[cfg(test)]
    mir_unit_9_3_caller: std::option::Option<(u8, u64)>,
    #[cfg(test)]
    alias_unit_9_3_0_old_source: std::option::Option<(u8, u64)>,
    #[cfg(test)]
    alias_unit_9_3_0_old_argument: std::option::Option<(u8, u64)>,
    #[cfg(test)]
    alias_unit_9_3_0_old_returned: std::option::Option<(u8, u64)>,
    #[cfg(test)]
    alias_unit_9_3_0_old_caller: std::option::Option<(u8, u64)>,
    #[cfg(test)]
    mir_unit_9_4_source: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_9_4_argument: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_9_4_returned: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_9_4_caller: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_9_5_source: (),
    #[cfg(test)]
    mir_unit_9_5_argument: (),
    #[cfg(test)]
    mir_unit_9_5_returned: (),
    #[cfg(test)]
    mir_unit_9_5_caller: (),
    #[cfg(test)]
    mir_unit_9_6_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_9_6_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_9_6_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_9_6_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_9_7_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_9_7_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_9_7_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_9_7_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_9_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_9_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_9_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_9_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_9_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_9_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_9_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_9_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_9_2_source: Value,
    #[cfg(test)]
    mir_unit_9_2_argument: Value,
    #[cfg(test)]
    mir_unit_9_2_returned: Value,
    #[cfg(test)]
    mir_unit_9_2_caller: Value,
    #[cfg(test)]
    alias_unit_9_2_0_value_source: Value,
    #[cfg(test)]
    alias_unit_9_2_0_value_argument: Value,
    #[cfg(test)]
    alias_unit_9_2_0_value_returned: Value,
    #[cfg(test)]
    alias_unit_9_2_0_value_caller: Value,
    #[cfg(test)]
    mir_unit_10_0_source: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_10_0_argument: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_10_0_returned: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_10_0_caller: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_10_0_0_result_source: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_10_0_0_result_argument: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_10_0_0_result_returned: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_10_0_0_result_caller: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_10_2_source: usize,
    #[cfg(test)]
    mir_unit_10_2_argument: usize,
    #[cfg(test)]
    mir_unit_10_2_returned: usize,
    #[cfg(test)]
    mir_unit_10_2_caller: usize,
    #[cfg(test)]
    alias_unit_10_2_0_before_source: usize,
    #[cfg(test)]
    alias_unit_10_2_0_before_argument: usize,
    #[cfg(test)]
    alias_unit_10_2_0_before_returned: usize,
    #[cfg(test)]
    alias_unit_10_2_0_before_caller: usize,
    #[cfg(test)]
    mir_unit_10_3_source: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_10_3_argument: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_10_3_returned: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_10_3_caller: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_10_4_source: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_10_4_argument: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_10_4_returned: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_10_4_caller: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_10_5_source: bool,
    #[cfg(test)]
    mir_unit_10_5_argument: bool,
    #[cfg(test)]
    mir_unit_10_5_returned: bool,
    #[cfg(test)]
    mir_unit_10_5_caller: bool,
    #[cfg(test)]
    mir_unit_10_6_source: &'static std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_10_6_argument: &'static std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_10_6_returned: &'static std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_10_6_caller: &'static std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_10_7_source: bool,
    #[cfg(test)]
    mir_unit_10_7_argument: bool,
    #[cfg(test)]
    mir_unit_10_7_returned: bool,
    #[cfg(test)]
    mir_unit_10_7_caller: bool,
    #[cfg(test)]
    mir_unit_10_8_source: usize,
    #[cfg(test)]
    mir_unit_10_8_argument: usize,
    #[cfg(test)]
    mir_unit_10_8_returned: usize,
    #[cfg(test)]
    mir_unit_10_8_caller: usize,
    #[cfg(test)]
    mir_unit_10_9_source: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_10_9_argument: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_10_9_returned: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_10_9_caller: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_10_10_source: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_10_10_argument: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_10_10_returned: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_10_10_caller: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_10_11_source: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_10_11_argument: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_10_11_returned: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_10_11_caller: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_10_12_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameCleanupState,
    #[cfg(test)]
    mir_unit_10_12_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameCleanupState,
    #[cfg(test)]
    mir_unit_10_12_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameCleanupState,
    #[cfg(test)]
    mir_unit_10_12_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameCleanupState,
    #[cfg(test)]
    mir_unit_10_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_10_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_10_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_10_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_10_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_10_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_10_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_10_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    literal_unit_10_0_source: bool,
    #[cfg(test)]
    literal_unit_10_0_argument: bool,
    #[cfg(test)]
    literal_unit_10_0_returned: bool,
    #[cfg(test)]
    literal_unit_10_0_caller: bool,
    #[cfg(test)]
    mir_unit_11_0_source: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_11_0_argument: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_11_0_returned: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_11_0_caller: std::result::Result<i32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_11_2_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>,
    #[cfg(test)]
    mir_unit_11_2_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>,
    #[cfg(test)]
    mir_unit_11_2_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>,
    #[cfg(test)]
    mir_unit_11_2_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>,
    #[cfg(test)]
    mir_unit_11_3_source: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_11_3_argument: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_11_3_returned: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_11_3_caller: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_11_4_source: isize,
    #[cfg(test)]
    mir_unit_11_4_argument: isize,
    #[cfg(test)]
    mir_unit_11_4_returned: isize,
    #[cfg(test)]
    mir_unit_11_4_caller: isize,
    #[cfg(test)]
    mir_unit_11_5_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_11_5_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_11_5_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_11_5_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_11_5_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_11_5_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_11_5_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_11_5_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_11_6_source: Value,
    #[cfg(test)]
    mir_unit_11_6_argument: Value,
    #[cfg(test)]
    mir_unit_11_6_returned: Value,
    #[cfg(test)]
    mir_unit_11_6_caller: Value,
    #[cfg(test)]
    alias_unit_11_6_0_val_source: Value,
    #[cfg(test)]
    alias_unit_11_6_0_val_argument: Value,
    #[cfg(test)]
    alias_unit_11_6_0_val_returned: Value,
    #[cfg(test)]
    alias_unit_11_6_0_val_caller: Value,
    #[cfg(test)]
    mir_unit_11_7_source: isize,
    #[cfg(test)]
    mir_unit_11_7_argument: isize,
    #[cfg(test)]
    mir_unit_11_7_returned: isize,
    #[cfg(test)]
    mir_unit_11_7_caller: isize,
    #[cfg(test)]
    mir_unit_11_8_source: i32,
    #[cfg(test)]
    mir_unit_11_8_argument: i32,
    #[cfg(test)]
    mir_unit_11_8_returned: i32,
    #[cfg(test)]
    mir_unit_11_8_caller: i32,
    #[cfg(test)]
    alias_unit_11_8_0_value_source: i32,
    #[cfg(test)]
    alias_unit_11_8_0_value_argument: i32,
    #[cfg(test)]
    alias_unit_11_8_0_value_returned: i32,
    #[cfg(test)]
    alias_unit_11_8_0_value_caller: i32,
    #[cfg(test)]
    mir_unit_11_9_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_11_9_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_11_9_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_11_9_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_11_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_11_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_11_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_11_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_11_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_11_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_11_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_11_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    literal_unit_11_0_source: &'static str,
    #[cfg(test)]
    literal_unit_11_0_argument: &'static str,
    #[cfg(test)]
    literal_unit_11_0_returned: &'static str,
    #[cfg(test)]
    literal_unit_11_0_caller: &'static str,
    #[cfg(test)]
    mir_unit_12_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_12_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_12_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_12_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_12_4_source: Type,
    #[cfg(test)]
    mir_unit_12_4_argument: Type,
    #[cfg(test)]
    mir_unit_12_4_returned: Type,
    #[cfg(test)]
    mir_unit_12_4_caller: Type,
    #[cfg(test)]
    alias_unit_12_4_0_expected_source: Type,
    #[cfg(test)]
    alias_unit_12_4_0_expected_argument: Type,
    #[cfg(test)]
    alias_unit_12_4_0_expected_returned: Type,
    #[cfg(test)]
    alias_unit_12_4_0_expected_caller: Type,
    #[cfg(test)]
    mir_unit_12_5_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_5_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_5_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_5_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_6_source: bool,
    #[cfg(test)]
    mir_unit_12_6_argument: bool,
    #[cfg(test)]
    mir_unit_12_6_returned: bool,
    #[cfg(test)]
    mir_unit_12_6_caller: bool,
    #[cfg(test)]
    mir_unit_12_7_source: &'static std::ops::RangeInclusive<u8>,
    #[cfg(test)]
    mir_unit_12_7_argument: &'static std::ops::RangeInclusive<u8>,
    #[cfg(test)]
    mir_unit_12_7_returned: &'static std::ops::RangeInclusive<u8>,
    #[cfg(test)]
    mir_unit_12_7_caller: &'static std::ops::RangeInclusive<u8>,
    #[cfg(test)]
    mir_unit_12_8_source: &'static u8,
    #[cfg(test)]
    mir_unit_12_8_argument: &'static u8,
    #[cfg(test)]
    mir_unit_12_8_returned: &'static u8,
    #[cfg(test)]
    mir_unit_12_8_caller: &'static u8,
    #[cfg(test)]
    mir_unit_12_9_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_9_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_9_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_9_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_10_source: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_12_10_argument: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_12_10_returned: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_12_10_caller: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_12_11_source: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_12_11_argument: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_12_11_returned: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_12_11_caller: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_12_12_source: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_12_12_argument: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_12_12_returned: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_12_12_caller: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_12_13_source: isize,
    #[cfg(test)]
    mir_unit_12_13_argument: isize,
    #[cfg(test)]
    mir_unit_12_13_returned: isize,
    #[cfg(test)]
    mir_unit_12_13_caller: isize,
    #[cfg(test)]
    mir_unit_12_15_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_15_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_15_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_15_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_17_source: bool,
    #[cfg(test)]
    mir_unit_12_17_argument: bool,
    #[cfg(test)]
    mir_unit_12_17_returned: bool,
    #[cfg(test)]
    mir_unit_12_17_caller: bool,
    #[cfg(test)]
    mir_unit_12_18_source: usize,
    #[cfg(test)]
    mir_unit_12_18_argument: usize,
    #[cfg(test)]
    mir_unit_12_18_returned: usize,
    #[cfg(test)]
    mir_unit_12_18_caller: usize,
    #[cfg(test)]
    mir_unit_12_19_source: bool,
    #[cfg(test)]
    mir_unit_12_19_argument: bool,
    #[cfg(test)]
    mir_unit_12_19_returned: bool,
    #[cfg(test)]
    mir_unit_12_19_caller: bool,
    #[cfg(test)]
    mir_unit_12_20_source: usize,
    #[cfg(test)]
    mir_unit_12_20_argument: usize,
    #[cfg(test)]
    mir_unit_12_20_returned: usize,
    #[cfg(test)]
    mir_unit_12_20_caller: usize,
    #[cfg(test)]
    mir_unit_12_21_source: usize,
    #[cfg(test)]
    mir_unit_12_21_argument: usize,
    #[cfg(test)]
    mir_unit_12_21_returned: usize,
    #[cfg(test)]
    mir_unit_12_21_caller: usize,
    #[cfg(test)]
    mir_unit_12_22_source: &'static std::vec::Vec<crate::experimental::execution::Control>,
    #[cfg(test)]
    mir_unit_12_22_argument: &'static std::vec::Vec<crate::experimental::execution::Control>,
    #[cfg(test)]
    mir_unit_12_22_returned: &'static std::vec::Vec<crate::experimental::execution::Control>,
    #[cfg(test)]
    mir_unit_12_22_caller: &'static std::vec::Vec<crate::experimental::execution::Control>,
    #[cfg(test)]
    mir_unit_12_23_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_23_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_23_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_23_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_24_source: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_12_24_argument: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_12_24_returned: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_12_24_caller: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_12_25_source: usize,
    #[cfg(test)]
    mir_unit_12_25_argument: usize,
    #[cfg(test)]
    mir_unit_12_25_returned: usize,
    #[cfg(test)]
    mir_unit_12_25_caller: usize,
    #[cfg(test)]
    mir_unit_12_26_source: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_26_argument: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_26_returned: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_26_caller: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_27_source: isize,
    #[cfg(test)]
    mir_unit_12_27_argument: isize,
    #[cfg(test)]
    mir_unit_12_27_returned: isize,
    #[cfg(test)]
    mir_unit_12_27_caller: isize,
    #[cfg(test)]
    mir_unit_12_29_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_29_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_29_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_29_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_31_source: bool,
    #[cfg(test)]
    mir_unit_12_31_argument: bool,
    #[cfg(test)]
    mir_unit_12_31_returned: bool,
    #[cfg(test)]
    mir_unit_12_31_caller: bool,
    #[cfg(test)]
    mir_unit_12_32_source: usize,
    #[cfg(test)]
    mir_unit_12_32_argument: usize,
    #[cfg(test)]
    mir_unit_12_32_returned: usize,
    #[cfg(test)]
    mir_unit_12_32_caller: usize,
    #[cfg(test)]
    mir_unit_12_33_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_33_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_33_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_33_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_35_source: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_35_argument: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_35_returned: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_35_caller: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_36_source: bool,
    #[cfg(test)]
    mir_unit_12_36_argument: bool,
    #[cfg(test)]
    mir_unit_12_36_returned: bool,
    #[cfg(test)]
    mir_unit_12_36_caller: bool,
    #[cfg(test)]
    mir_unit_12_37_source: &'static Type,
    #[cfg(test)]
    mir_unit_12_37_argument: &'static Type,
    #[cfg(test)]
    mir_unit_12_37_returned: &'static Type,
    #[cfg(test)]
    mir_unit_12_37_caller: &'static Type,
    #[cfg(test)]
    mir_unit_12_38_source: Type,
    #[cfg(test)]
    mir_unit_12_38_argument: Type,
    #[cfg(test)]
    mir_unit_12_38_returned: Type,
    #[cfg(test)]
    mir_unit_12_38_caller: Type,
    #[cfg(test)]
    mir_unit_12_39_source: Value,
    #[cfg(test)]
    mir_unit_12_39_argument: Value,
    #[cfg(test)]
    mir_unit_12_39_returned: Value,
    #[cfg(test)]
    mir_unit_12_39_caller: Value,
    #[cfg(test)]
    mir_unit_12_40_source: &'static Value,
    #[cfg(test)]
    mir_unit_12_40_argument: &'static Value,
    #[cfg(test)]
    mir_unit_12_40_returned: &'static Value,
    #[cfg(test)]
    mir_unit_12_40_caller: &'static Value,
    #[cfg(test)]
    mir_unit_12_41_source: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_41_argument: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_41_returned: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_41_caller: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_42_source: usize,
    #[cfg(test)]
    mir_unit_12_42_argument: usize,
    #[cfg(test)]
    mir_unit_12_42_returned: usize,
    #[cfg(test)]
    mir_unit_12_42_caller: usize,
    #[cfg(test)]
    mir_unit_12_43_source: (usize, bool),
    #[cfg(test)]
    mir_unit_12_43_argument: (usize, bool),
    #[cfg(test)]
    mir_unit_12_43_returned: (usize, bool),
    #[cfg(test)]
    mir_unit_12_43_caller: (usize, bool),
    #[cfg(test)]
    mir_unit_12_44_source: &'static Type,
    #[cfg(test)]
    mir_unit_12_44_argument: &'static Type,
    #[cfg(test)]
    mir_unit_12_44_returned: &'static Type,
    #[cfg(test)]
    mir_unit_12_44_caller: &'static Type,
    #[cfg(test)]
    mir_unit_12_45_source: bool,
    #[cfg(test)]
    mir_unit_12_45_argument: bool,
    #[cfg(test)]
    mir_unit_12_45_returned: bool,
    #[cfg(test)]
    mir_unit_12_45_caller: bool,
    #[cfg(test)]
    mir_unit_12_46_source: &'static Type,
    #[cfg(test)]
    mir_unit_12_46_argument: &'static Type,
    #[cfg(test)]
    mir_unit_12_46_returned: &'static Type,
    #[cfg(test)]
    mir_unit_12_46_caller: &'static Type,
    #[cfg(test)]
    mir_unit_12_47_source: Type,
    #[cfg(test)]
    mir_unit_12_47_argument: Type,
    #[cfg(test)]
    mir_unit_12_47_returned: Type,
    #[cfg(test)]
    mir_unit_12_47_caller: Type,
    #[cfg(test)]
    mir_unit_12_48_source: Value,
    #[cfg(test)]
    mir_unit_12_48_argument: Value,
    #[cfg(test)]
    mir_unit_12_48_returned: Value,
    #[cfg(test)]
    mir_unit_12_48_caller: Value,
    #[cfg(test)]
    mir_unit_12_49_source: &'static Value,
    #[cfg(test)]
    mir_unit_12_49_argument: &'static Value,
    #[cfg(test)]
    mir_unit_12_49_returned: &'static Value,
    #[cfg(test)]
    mir_unit_12_49_caller: &'static Value,
    #[cfg(test)]
    mir_unit_12_50_source: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_50_argument: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_50_returned: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_50_caller: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_51_source: usize,
    #[cfg(test)]
    mir_unit_12_51_argument: usize,
    #[cfg(test)]
    mir_unit_12_51_returned: usize,
    #[cfg(test)]
    mir_unit_12_51_caller: usize,
    #[cfg(test)]
    mir_unit_12_52_source: (usize, bool),
    #[cfg(test)]
    mir_unit_12_52_argument: (usize, bool),
    #[cfg(test)]
    mir_unit_12_52_returned: (usize, bool),
    #[cfg(test)]
    mir_unit_12_52_caller: (usize, bool),
    #[cfg(test)]
    mir_unit_12_53_source: &'static Type,
    #[cfg(test)]
    mir_unit_12_53_argument: &'static Type,
    #[cfg(test)]
    mir_unit_12_53_returned: &'static Type,
    #[cfg(test)]
    mir_unit_12_53_caller: &'static Type,
    #[cfg(test)]
    mir_unit_12_54_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_54_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_54_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_54_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_12_55_source: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_12_55_argument: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_12_55_returned: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_12_55_caller: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_12_56_source: &'static mut std::vec::Vec<crate::experimental::execution::Control>,
    #[cfg(test)]
    mir_unit_12_56_argument: &'static mut std::vec::Vec<crate::experimental::execution::Control>,
    #[cfg(test)]
    mir_unit_12_56_returned: &'static mut std::vec::Vec<crate::experimental::execution::Control>,
    #[cfg(test)]
    mir_unit_12_56_caller: &'static mut std::vec::Vec<crate::experimental::execution::Control>,
    #[cfg(test)]
    mir_unit_12_57_source: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_57_argument: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_57_returned: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_57_caller: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_58_source: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_58_argument: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_58_returned: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_58_caller: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_59_source: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_59_argument: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_59_returned: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_59_caller: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_60_source: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_60_argument: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_60_returned: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_60_caller: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_12_14_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_12_14_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_12_14_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_12_14_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_12_14_0_frame_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_12_14_0_frame_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_12_14_0_frame_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_12_14_0_frame_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_12_14_1_frame_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_12_14_1_frame_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_12_14_1_frame_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_12_14_1_frame_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_12_16_source: usize,
    #[cfg(test)]
    mir_unit_12_16_argument: usize,
    #[cfg(test)]
    mir_unit_12_16_returned: usize,
    #[cfg(test)]
    mir_unit_12_16_caller: usize,
    #[cfg(test)]
    alias_unit_12_16_0_floor_source: usize,
    #[cfg(test)]
    alias_unit_12_16_0_floor_argument: usize,
    #[cfg(test)]
    alias_unit_12_16_0_floor_returned: usize,
    #[cfg(test)]
    alias_unit_12_16_0_floor_caller: usize,
    #[cfg(test)]
    mir_unit_12_28_source: usize,
    #[cfg(test)]
    mir_unit_12_28_argument: usize,
    #[cfg(test)]
    mir_unit_12_28_returned: usize,
    #[cfg(test)]
    mir_unit_12_28_caller: usize,
    #[cfg(test)]
    alias_unit_12_28_0_available_source: usize,
    #[cfg(test)]
    alias_unit_12_28_0_available_argument: usize,
    #[cfg(test)]
    alias_unit_12_28_0_available_returned: usize,
    #[cfg(test)]
    alias_unit_12_28_0_available_caller: usize,
    #[cfg(test)]
    alias_unit_12_28_1_available_source: usize,
    #[cfg(test)]
    alias_unit_12_28_1_available_argument: usize,
    #[cfg(test)]
    alias_unit_12_28_1_available_returned: usize,
    #[cfg(test)]
    alias_unit_12_28_1_available_caller: usize,
    #[cfg(test)]
    mir_unit_12_30_source: usize,
    #[cfg(test)]
    mir_unit_12_30_argument: usize,
    #[cfg(test)]
    mir_unit_12_30_returned: usize,
    #[cfg(test)]
    mir_unit_12_30_caller: usize,
    #[cfg(test)]
    alias_unit_12_30_0_count_source: usize,
    #[cfg(test)]
    alias_unit_12_30_0_count_argument: usize,
    #[cfg(test)]
    alias_unit_12_30_0_count_returned: usize,
    #[cfg(test)]
    alias_unit_12_30_0_count_caller: usize,
    #[cfg(test)]
    mir_unit_12_34_source: usize,
    #[cfg(test)]
    mir_unit_12_34_argument: usize,
    #[cfg(test)]
    mir_unit_12_34_returned: usize,
    #[cfg(test)]
    mir_unit_12_34_caller: usize,
    #[cfg(test)]
    alias_unit_12_34_0_length_source: usize,
    #[cfg(test)]
    alias_unit_12_34_0_length_argument: usize,
    #[cfg(test)]
    alias_unit_12_34_0_length_returned: usize,
    #[cfg(test)]
    alias_unit_12_34_0_length_caller: usize,
    #[cfg(test)]
    mir_unit_12_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_12_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_12_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_12_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_12_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_12_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_12_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_12_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_12_2_source: u8,
    #[cfg(test)]
    mir_unit_12_2_argument: u8,
    #[cfg(test)]
    mir_unit_12_2_returned: u8,
    #[cfg(test)]
    mir_unit_12_2_caller: u8,
    #[cfg(test)]
    alias_unit_12_2_0_opcode_source: u8,
    #[cfg(test)]
    alias_unit_12_2_0_opcode_argument: u8,
    #[cfg(test)]
    alias_unit_12_2_0_opcode_returned: u8,
    #[cfg(test)]
    alias_unit_12_2_0_opcode_caller: u8,
    #[cfg(test)]
    mir_unit_12_3_source: bool,
    #[cfg(test)]
    mir_unit_12_3_argument: bool,
    #[cfg(test)]
    mir_unit_12_3_returned: bool,
    #[cfg(test)]
    mir_unit_12_3_caller: bool,
    #[cfg(test)]
    alias_unit_12_3_0_store_source: bool,
    #[cfg(test)]
    alias_unit_12_3_0_store_argument: bool,
    #[cfg(test)]
    alias_unit_12_3_0_store_returned: bool,
    #[cfg(test)]
    alias_unit_12_3_0_store_caller: bool,
    #[cfg(test)]
    literal_unit_12_0_source: &'static str,
    #[cfg(test)]
    literal_unit_12_0_argument: &'static str,
    #[cfg(test)]
    literal_unit_12_0_returned: &'static str,
    #[cfg(test)]
    literal_unit_12_0_caller: &'static str,
    #[cfg(test)]
    literal_unit_12_1_source: &'static str,
    #[cfg(test)]
    literal_unit_12_1_argument: &'static str,
    #[cfg(test)]
    literal_unit_12_1_returned: &'static str,
    #[cfg(test)]
    literal_unit_12_1_caller: &'static str,
    #[cfg(test)]
    literal_unit_12_2_source: &'static str,
    #[cfg(test)]
    literal_unit_12_2_argument: &'static str,
    #[cfg(test)]
    literal_unit_12_2_returned: &'static str,
    #[cfg(test)]
    literal_unit_12_2_caller: &'static str,
    #[cfg(test)]
    literal_unit_12_3_source: usize,
    #[cfg(test)]
    literal_unit_12_3_argument: usize,
    #[cfg(test)]
    literal_unit_12_3_returned: usize,
    #[cfg(test)]
    literal_unit_12_3_caller: usize,
    #[cfg(test)]
    literal_unit_12_4_source: usize,
    #[cfg(test)]
    literal_unit_12_4_argument: usize,
    #[cfg(test)]
    literal_unit_12_4_returned: usize,
    #[cfg(test)]
    literal_unit_12_4_caller: usize,
    #[cfg(test)]
    literal_unit_12_5_source: &'static str,
    #[cfg(test)]
    literal_unit_12_5_argument: &'static str,
    #[cfg(test)]
    literal_unit_12_5_returned: &'static str,
    #[cfg(test)]
    literal_unit_12_5_caller: &'static str,
    #[cfg(test)]
    literal_unit_12_6_source: usize,
    #[cfg(test)]
    literal_unit_12_6_argument: usize,
    #[cfg(test)]
    literal_unit_12_6_returned: usize,
    #[cfg(test)]
    literal_unit_12_6_caller: usize,
    #[cfg(test)]
    literal_unit_12_7_source: usize,
    #[cfg(test)]
    literal_unit_12_7_argument: usize,
    #[cfg(test)]
    literal_unit_12_7_returned: usize,
    #[cfg(test)]
    literal_unit_12_7_caller: usize,
    #[cfg(test)]
    literal_unit_12_8_source: usize,
    #[cfg(test)]
    literal_unit_12_8_argument: usize,
    #[cfg(test)]
    literal_unit_12_8_returned: usize,
    #[cfg(test)]
    literal_unit_12_8_caller: usize,
    #[cfg(test)]
    literal_unit_12_9_source: usize,
    #[cfg(test)]
    literal_unit_12_9_argument: usize,
    #[cfg(test)]
    literal_unit_12_9_returned: usize,
    #[cfg(test)]
    literal_unit_12_9_caller: usize,
    #[cfg(test)]
    literal_unit_12_10_source: &'static str,
    #[cfg(test)]
    literal_unit_12_10_argument: &'static str,
    #[cfg(test)]
    literal_unit_12_10_returned: &'static str,
    #[cfg(test)]
    literal_unit_12_10_caller: &'static str,
    #[cfg(test)]
    mir_unit_13_0_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_13_0_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_13_0_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_13_0_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_13_2_source: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_13_2_argument: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_13_2_returned: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_13_2_caller: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_13_3_source: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_13_3_argument: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_13_3_returned: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_13_3_caller: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_13_4_source: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_13_4_argument: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_13_4_returned: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_13_4_caller: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_13_5_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_13_5_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_13_5_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_13_5_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_13_6_source: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_13_6_argument: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_13_6_returned: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_13_6_caller: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_13_7_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_13_7_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_13_7_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_13_7_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_13_8_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_13_8_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_13_8_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_13_8_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_13_9_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_13_9_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_13_9_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_13_9_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_13_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_13_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_13_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_13_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_13_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_13_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_13_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_13_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    literal_unit_13_0_source: &'static str,
    #[cfg(test)]
    literal_unit_13_0_argument: &'static str,
    #[cfg(test)]
    literal_unit_13_0_returned: &'static str,
    #[cfg(test)]
    literal_unit_13_0_caller: &'static str,
    #[cfg(test)]
    mir_unit_14_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_14_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_14_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_14_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_14_4_source: bool,
    #[cfg(test)]
    mir_unit_14_4_argument: bool,
    #[cfg(test)]
    mir_unit_14_4_returned: bool,
    #[cfg(test)]
    mir_unit_14_4_caller: bool,
    #[cfg(test)]
    mir_unit_14_5_source: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_14_5_argument: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_14_5_returned: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_14_5_caller: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_14_6_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_14_6_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_14_6_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_14_6_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_14_6_0_failure_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_14_6_0_failure_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_14_6_0_failure_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_14_6_0_failure_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_14_7_source: (),
    #[cfg(test)]
    mir_unit_14_7_argument: (),
    #[cfg(test)]
    mir_unit_14_7_returned: (),
    #[cfg(test)]
    mir_unit_14_7_caller: (),
    #[cfg(test)]
    mir_unit_14_8_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_14_8_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_14_8_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_14_8_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_14_8_0_result_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_14_8_0_result_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_14_8_0_result_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_14_8_0_result_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_14_9_source: bool,
    #[cfg(test)]
    mir_unit_14_9_argument: bool,
    #[cfg(test)]
    mir_unit_14_9_returned: bool,
    #[cfg(test)]
    mir_unit_14_9_caller: bool,
    #[cfg(test)]
    mir_unit_14_10_source: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_14_10_argument: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_14_10_returned: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_14_10_caller: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_14_11_source: (),
    #[cfg(test)]
    mir_unit_14_11_argument: (),
    #[cfg(test)]
    mir_unit_14_11_returned: (),
    #[cfg(test)]
    mir_unit_14_11_caller: (),
    #[cfg(test)]
    mir_unit_14_12_source: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_14_12_argument: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_14_12_returned: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_14_12_caller: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_14_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_14_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_14_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_14_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_14_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_14_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_14_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_14_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_14_2_source: crate::experimental::cache::Operation,
    #[cfg(test)]
    mir_unit_14_2_argument: crate::experimental::cache::Operation,
    #[cfg(test)]
    mir_unit_14_2_returned: crate::experimental::cache::Operation,
    #[cfg(test)]
    mir_unit_14_2_caller: crate::experimental::cache::Operation,
    #[cfg(test)]
    alias_unit_14_2_0_operation_source: crate::experimental::cache::Operation,
    #[cfg(test)]
    alias_unit_14_2_0_operation_argument: crate::experimental::cache::Operation,
    #[cfg(test)]
    alias_unit_14_2_0_operation_returned: crate::experimental::cache::Operation,
    #[cfg(test)]
    alias_unit_14_2_0_operation_caller: crate::experimental::cache::Operation,
    #[cfg(test)]
    mir_unit_14_3_source: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_14_3_argument: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_14_3_returned: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_14_3_caller: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    alias_unit_14_3_0_returned_source: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    alias_unit_14_3_0_returned_argument: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    alias_unit_14_3_0_returned_returned: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    alias_unit_14_3_0_returned_caller: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    literal_unit_14_0_source: &'static str,
    #[cfg(test)]
    literal_unit_14_0_argument: &'static str,
    #[cfg(test)]
    literal_unit_14_0_returned: &'static str,
    #[cfg(test)]
    literal_unit_14_0_caller: &'static str,
    #[cfg(test)]
    mir_unit_15_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_3_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_15_3_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_15_3_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_15_3_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_15_4_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_4_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_4_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_4_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_5_source: isize,
    #[cfg(test)]
    mir_unit_15_5_argument: isize,
    #[cfg(test)]
    mir_unit_15_5_returned: isize,
    #[cfg(test)]
    mir_unit_15_5_caller: isize,
    #[cfg(test)]
    mir_unit_15_6_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_6_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_6_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_6_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_15_6_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_15_6_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_15_6_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_15_6_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_7_source: isize,
    #[cfg(test)]
    mir_unit_15_7_argument: isize,
    #[cfg(test)]
    mir_unit_15_7_returned: isize,
    #[cfg(test)]
    mir_unit_15_7_caller: isize,
    #[cfg(test)]
    mir_unit_15_8_source: u8,
    #[cfg(test)]
    mir_unit_15_8_argument: u8,
    #[cfg(test)]
    mir_unit_15_8_returned: u8,
    #[cfg(test)]
    mir_unit_15_8_caller: u8,
    #[cfg(test)]
    alias_unit_15_8_0_opcode_source: u8,
    #[cfg(test)]
    alias_unit_15_8_0_opcode_argument: u8,
    #[cfg(test)]
    alias_unit_15_8_0_opcode_returned: u8,
    #[cfg(test)]
    alias_unit_15_8_0_opcode_caller: u8,
    #[cfg(test)]
    mir_unit_15_9_source: u32,
    #[cfg(test)]
    mir_unit_15_9_argument: u32,
    #[cfg(test)]
    mir_unit_15_9_returned: u32,
    #[cfg(test)]
    mir_unit_15_9_caller: u32,
    #[cfg(test)]
    alias_unit_15_9_0_offset_source: u32,
    #[cfg(test)]
    alias_unit_15_9_0_offset_argument: u32,
    #[cfg(test)]
    alias_unit_15_9_0_offset_returned: u32,
    #[cfg(test)]
    alias_unit_15_9_0_offset_caller: u32,
    #[cfg(test)]
    mir_unit_15_10_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_15_10_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_15_10_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_15_10_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_15_11_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_11_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_11_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_11_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_12_source: isize,
    #[cfg(test)]
    mir_unit_15_12_argument: isize,
    #[cfg(test)]
    mir_unit_15_12_returned: isize,
    #[cfg(test)]
    mir_unit_15_12_caller: isize,
    #[cfg(test)]
    mir_unit_15_14_source: u8,
    #[cfg(test)]
    mir_unit_15_14_argument: u8,
    #[cfg(test)]
    mir_unit_15_14_returned: u8,
    #[cfg(test)]
    mir_unit_15_14_caller: u8,
    #[cfg(test)]
    alias_unit_15_14_0_opcode_source: u8,
    #[cfg(test)]
    alias_unit_15_14_0_opcode_argument: u8,
    #[cfg(test)]
    alias_unit_15_14_0_opcode_returned: u8,
    #[cfg(test)]
    alias_unit_15_14_0_opcode_caller: u8,
    #[cfg(test)]
    mir_unit_15_15_source: u32,
    #[cfg(test)]
    mir_unit_15_15_argument: u32,
    #[cfg(test)]
    mir_unit_15_15_returned: u32,
    #[cfg(test)]
    mir_unit_15_15_caller: u32,
    #[cfg(test)]
    alias_unit_15_15_0_offset_source: u32,
    #[cfg(test)]
    alias_unit_15_15_0_offset_argument: u32,
    #[cfg(test)]
    alias_unit_15_15_0_offset_returned: u32,
    #[cfg(test)]
    alias_unit_15_15_0_offset_caller: u32,
    #[cfg(test)]
    mir_unit_15_16_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_15_16_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_15_16_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_15_16_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_15_17_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_17_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_17_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_17_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_18_source: isize,
    #[cfg(test)]
    mir_unit_15_18_argument: isize,
    #[cfg(test)]
    mir_unit_15_18_returned: isize,
    #[cfg(test)]
    mir_unit_15_18_caller: isize,
    #[cfg(test)]
    mir_unit_15_20_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_15_20_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_15_20_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_15_20_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_15_13_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_13_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_13_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_13_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_15_13_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_15_13_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_15_13_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_15_13_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_19_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_19_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_19_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_19_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_15_19_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_15_19_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_15_19_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_15_19_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_15_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_15_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_15_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_15_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_15_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_15_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_15_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_15_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_15_2_source: crate::experimental::cache::Operation,
    #[cfg(test)]
    mir_unit_15_2_argument: crate::experimental::cache::Operation,
    #[cfg(test)]
    mir_unit_15_2_returned: crate::experimental::cache::Operation,
    #[cfg(test)]
    mir_unit_15_2_caller: crate::experimental::cache::Operation,
    #[cfg(test)]
    alias_unit_15_2_0_operation_source: crate::experimental::cache::Operation,
    #[cfg(test)]
    alias_unit_15_2_0_operation_argument: crate::experimental::cache::Operation,
    #[cfg(test)]
    alias_unit_15_2_0_operation_returned: crate::experimental::cache::Operation,
    #[cfg(test)]
    alias_unit_15_2_0_operation_caller: crate::experimental::cache::Operation,
    #[cfg(test)]
    literal_unit_15_0_source: bool,
    #[cfg(test)]
    literal_unit_15_0_argument: bool,
    #[cfg(test)]
    literal_unit_15_0_returned: bool,
    #[cfg(test)]
    literal_unit_15_0_caller: bool,
    #[cfg(test)]
    literal_unit_15_1_source: bool,
    #[cfg(test)]
    literal_unit_15_1_argument: bool,
    #[cfg(test)]
    literal_unit_15_1_returned: bool,
    #[cfg(test)]
    literal_unit_15_1_caller: bool,
    #[cfg(test)]
    mir_unit_16_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_16_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_16_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_16_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_16_3_source: bool,
    #[cfg(test)]
    mir_unit_16_3_argument: bool,
    #[cfg(test)]
    mir_unit_16_3_returned: bool,
    #[cfg(test)]
    mir_unit_16_3_caller: bool,
    #[cfg(test)]
    mir_unit_16_4_source: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_16_4_argument: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_16_4_returned: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_16_4_caller: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_16_5_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_16_5_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_16_5_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_16_5_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_16_5_0_failure_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_16_5_0_failure_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_16_5_0_failure_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_16_5_0_failure_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_16_6_source: (),
    #[cfg(test)]
    mir_unit_16_6_argument: (),
    #[cfg(test)]
    mir_unit_16_6_returned: (),
    #[cfg(test)]
    mir_unit_16_6_caller: (),
    #[cfg(test)]
    mir_unit_16_7_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_16_7_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_16_7_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_16_7_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_16_7_0_result_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_16_7_0_result_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_16_7_0_result_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_16_7_0_result_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_16_8_source: bool,
    #[cfg(test)]
    mir_unit_16_8_argument: bool,
    #[cfg(test)]
    mir_unit_16_8_returned: bool,
    #[cfg(test)]
    mir_unit_16_8_caller: bool,
    #[cfg(test)]
    mir_unit_16_9_source: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_16_9_argument: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_16_9_returned: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_16_9_caller: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_16_10_source: (),
    #[cfg(test)]
    mir_unit_16_10_argument: (),
    #[cfg(test)]
    mir_unit_16_10_returned: (),
    #[cfg(test)]
    mir_unit_16_10_caller: (),
    #[cfg(test)]
    mir_unit_16_11_source: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_16_11_argument: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_16_11_returned: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_16_11_caller: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_16_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_16_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_16_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_16_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_16_1_0_phase_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_16_1_0_phase_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_16_1_0_phase_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_16_1_0_phase_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_16_2_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    #[cfg(test)]
    mir_unit_16_2_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    #[cfg(test)]
    mir_unit_16_2_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    #[cfg(test)]
    mir_unit_16_2_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    #[cfg(test)]
    alias_unit_16_2_0_storage_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    #[cfg(test)]
    alias_unit_16_2_0_storage_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    #[cfg(test)]
    alias_unit_16_2_0_storage_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    #[cfg(test)]
    alias_unit_16_2_0_storage_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    #[cfg(test)]
    literal_unit_16_0_source: &'static str,
    #[cfg(test)]
    literal_unit_16_0_argument: &'static str,
    #[cfg(test)]
    literal_unit_16_0_returned: &'static str,
    #[cfg(test)]
    literal_unit_16_0_caller: &'static str,
    #[cfg(test)]
    mir_unit_17_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_2_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_17_2_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_17_2_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_17_2_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_17_3_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_3_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_3_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_3_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_4_source: isize,
    #[cfg(test)]
    mir_unit_17_4_argument: isize,
    #[cfg(test)]
    mir_unit_17_4_returned: isize,
    #[cfg(test)]
    mir_unit_17_4_caller: isize,
    #[cfg(test)]
    mir_unit_17_5_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_5_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_5_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_5_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_17_5_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_17_5_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_17_5_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_17_5_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_6_source: (u32, crate::experimental::cache::DecodedInstruction),
    #[cfg(test)]
    mir_unit_17_6_argument: (u32, crate::experimental::cache::DecodedInstruction),
    #[cfg(test)]
    mir_unit_17_6_returned: (u32, crate::experimental::cache::DecodedInstruction),
    #[cfg(test)]
    mir_unit_17_6_caller: (u32, crate::experimental::cache::DecodedInstruction),
    #[cfg(test)]
    alias_unit_17_6_0_selected_source: (u32, crate::experimental::cache::DecodedInstruction),
    #[cfg(test)]
    alias_unit_17_6_0_selected_argument: (u32, crate::experimental::cache::DecodedInstruction),
    #[cfg(test)]
    alias_unit_17_6_0_selected_returned: (u32, crate::experimental::cache::DecodedInstruction),
    #[cfg(test)]
    alias_unit_17_6_0_selected_caller: (u32, crate::experimental::cache::DecodedInstruction),
    #[cfg(test)]
    mir_unit_17_7_source: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_7_argument: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_7_returned: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_7_caller: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_8_source: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_17_8_argument: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_17_8_returned: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_17_8_caller: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_17_9_source: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_9_argument: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_9_returned: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_9_caller: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_10_source: isize,
    #[cfg(test)]
    mir_unit_17_10_argument: isize,
    #[cfg(test)]
    mir_unit_17_10_returned: isize,
    #[cfg(test)]
    mir_unit_17_10_caller: isize,
    #[cfg(test)]
    mir_unit_17_11_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_17_11_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_17_11_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_17_11_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_17_11_0_frame_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_17_11_0_frame_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_17_11_0_frame_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_17_11_0_frame_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_17_11_1_frame_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_17_11_1_frame_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_17_11_1_frame_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_17_11_1_frame_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_17_12_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_17_12_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_17_12_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_17_12_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_17_13_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::cache::FunctionView<'static>>,
    #[cfg(test)]
    mir_unit_17_13_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::cache::FunctionView<'static>>,
    #[cfg(test)]
    mir_unit_17_13_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::cache::FunctionView<'static>>,
    #[cfg(test)]
    mir_unit_17_13_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::cache::FunctionView<'static>>,
    #[cfg(test)]
    mir_unit_17_14_source: std::result::Result<crate::experimental::cache::FunctionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_14_argument: std::result::Result<crate::experimental::cache::FunctionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_14_returned: std::result::Result<crate::experimental::cache::FunctionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_14_caller: std::result::Result<crate::experimental::cache::FunctionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_15_source: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_17_15_argument: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_17_15_returned: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_17_15_caller: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_17_16_source: &'static crate::experimental_swift_reactor::cache::SwiftFunctionPin,
    #[cfg(test)]
    mir_unit_17_16_argument: &'static crate::experimental_swift_reactor::cache::SwiftFunctionPin,
    #[cfg(test)]
    mir_unit_17_16_returned: &'static crate::experimental_swift_reactor::cache::SwiftFunctionPin,
    #[cfg(test)]
    mir_unit_17_16_caller: &'static crate::experimental_swift_reactor::cache::SwiftFunctionPin,
    #[cfg(test)]
    mir_unit_17_17_source: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    #[cfg(test)]
    mir_unit_17_17_argument: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    #[cfg(test)]
    mir_unit_17_17_returned: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    #[cfg(test)]
    mir_unit_17_17_caller: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    #[cfg(test)]
    mir_unit_17_18_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_17_18_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_17_18_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_17_18_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_17_19_source: isize,
    #[cfg(test)]
    mir_unit_17_19_argument: isize,
    #[cfg(test)]
    mir_unit_17_19_returned: isize,
    #[cfg(test)]
    mir_unit_17_19_caller: isize,
    #[cfg(test)]
    mir_unit_17_23_source: std::option::Option<&'static crate::experimental::cache::DecodedInstruction>,
    #[cfg(test)]
    mir_unit_17_23_argument: std::option::Option<&'static crate::experimental::cache::DecodedInstruction>,
    #[cfg(test)]
    mir_unit_17_23_returned: std::option::Option<&'static crate::experimental::cache::DecodedInstruction>,
    #[cfg(test)]
    mir_unit_17_23_caller: std::option::Option<&'static crate::experimental::cache::DecodedInstruction>,
    #[cfg(test)]
    mir_unit_17_24_source: usize,
    #[cfg(test)]
    mir_unit_17_24_argument: usize,
    #[cfg(test)]
    mir_unit_17_24_returned: usize,
    #[cfg(test)]
    mir_unit_17_24_caller: usize,
    #[cfg(test)]
    mir_unit_17_25_source: isize,
    #[cfg(test)]
    mir_unit_17_25_argument: isize,
    #[cfg(test)]
    mir_unit_17_25_returned: isize,
    #[cfg(test)]
    mir_unit_17_25_caller: isize,
    #[cfg(test)]
    mir_unit_17_27_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_17_27_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_17_27_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_17_27_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_17_28_source: u32,
    #[cfg(test)]
    mir_unit_17_28_argument: u32,
    #[cfg(test)]
    mir_unit_17_28_returned: u32,
    #[cfg(test)]
    mir_unit_17_28_caller: u32,
    #[cfg(test)]
    mir_unit_17_31_source: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_17_31_argument: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_17_31_returned: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_17_31_caller: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_17_32_source: crate::experimental_swift_reactor::control::SwiftRunStage,
    #[cfg(test)]
    mir_unit_17_32_argument: crate::experimental_swift_reactor::control::SwiftRunStage,
    #[cfg(test)]
    mir_unit_17_32_returned: crate::experimental_swift_reactor::control::SwiftRunStage,
    #[cfg(test)]
    mir_unit_17_32_caller: crate::experimental_swift_reactor::control::SwiftRunStage,
    #[cfg(test)]
    mir_unit_17_33_source: std::option::Option<u32>,
    #[cfg(test)]
    mir_unit_17_33_argument: std::option::Option<u32>,
    #[cfg(test)]
    mir_unit_17_33_returned: std::option::Option<u32>,
    #[cfg(test)]
    mir_unit_17_33_caller: std::option::Option<u32>,
    #[cfg(test)]
    mir_unit_17_34_source: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_17_34_argument: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_17_34_returned: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_17_34_caller: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_17_35_source: usize,
    #[cfg(test)]
    mir_unit_17_35_argument: usize,
    #[cfg(test)]
    mir_unit_17_35_returned: usize,
    #[cfg(test)]
    mir_unit_17_35_caller: usize,
    #[cfg(test)]
    mir_unit_17_36_source: bool,
    #[cfg(test)]
    mir_unit_17_36_argument: bool,
    #[cfg(test)]
    mir_unit_17_36_returned: bool,
    #[cfg(test)]
    mir_unit_17_36_caller: bool,
    #[cfg(test)]
    mir_unit_17_37_source: bool,
    #[cfg(test)]
    mir_unit_17_37_argument: bool,
    #[cfg(test)]
    mir_unit_17_37_returned: bool,
    #[cfg(test)]
    mir_unit_17_37_caller: bool,
    #[cfg(test)]
    mir_unit_17_38_source: bool,
    #[cfg(test)]
    mir_unit_17_38_argument: bool,
    #[cfg(test)]
    mir_unit_17_38_returned: bool,
    #[cfg(test)]
    mir_unit_17_38_caller: bool,
    #[cfg(test)]
    mir_unit_17_39_source: bool,
    #[cfg(test)]
    mir_unit_17_39_argument: bool,
    #[cfg(test)]
    mir_unit_17_39_returned: bool,
    #[cfg(test)]
    mir_unit_17_39_caller: bool,
    #[cfg(test)]
    mir_unit_17_40_source: isize,
    #[cfg(test)]
    mir_unit_17_40_argument: isize,
    #[cfg(test)]
    mir_unit_17_40_returned: isize,
    #[cfg(test)]
    mir_unit_17_40_caller: isize,
    #[cfg(test)]
    mir_unit_17_41_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_17_41_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_17_41_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_17_41_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_17_42_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_17_42_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_17_42_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_17_42_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_17_43_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_43_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_43_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_43_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_44_source: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_17_44_argument: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_17_44_returned: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_17_44_caller: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_17_45_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_17_45_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_17_45_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_17_45_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_17_46_source: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_17_46_argument: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_17_46_returned: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_17_46_caller: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_17_47_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_17_47_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_17_47_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_17_47_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_17_48_source: isize,
    #[cfg(test)]
    mir_unit_17_48_argument: isize,
    #[cfg(test)]
    mir_unit_17_48_returned: isize,
    #[cfg(test)]
    mir_unit_17_48_caller: isize,
    #[cfg(test)]
    mir_unit_17_50_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_17_50_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_17_50_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_17_50_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_17_51_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_51_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_51_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_51_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_52_source: isize,
    #[cfg(test)]
    mir_unit_17_52_argument: isize,
    #[cfg(test)]
    mir_unit_17_52_returned: isize,
    #[cfg(test)]
    mir_unit_17_52_caller: isize,
    #[cfg(test)]
    mir_unit_17_54_source: bool,
    #[cfg(test)]
    mir_unit_17_54_argument: bool,
    #[cfg(test)]
    mir_unit_17_54_returned: bool,
    #[cfg(test)]
    mir_unit_17_54_caller: bool,
    #[cfg(test)]
    mir_unit_17_55_source: &'static std::thread::LocalKey<std::cell::Cell<bool>>,
    #[cfg(test)]
    mir_unit_17_55_argument: &'static std::thread::LocalKey<std::cell::Cell<bool>>,
    #[cfg(test)]
    mir_unit_17_55_returned: &'static std::thread::LocalKey<std::cell::Cell<bool>>,
    #[cfg(test)]
    mir_unit_17_55_caller: &'static std::thread::LocalKey<std::cell::Cell<bool>>,
    #[cfg(test)]
    mir_unit_17_56_source: &'static mut crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_17_56_argument: &'static mut crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_17_56_returned: &'static mut crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_17_56_caller: &'static mut crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_17_57_source: std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_57_argument: std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_57_returned: std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_57_caller: std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_58_source: &'static mut [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_17_58_argument: &'static mut [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_17_58_returned: &'static mut [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_17_58_caller: &'static mut [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_17_59_source: &'static str,
    #[cfg(test)]
    mir_unit_17_59_argument: &'static str,
    #[cfg(test)]
    mir_unit_17_59_returned: &'static str,
    #[cfg(test)]
    mir_unit_17_59_caller: &'static str,
    #[cfg(test)]
    mir_unit_17_60_source: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_17_60_argument: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_17_60_returned: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_17_60_caller: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_17_61_source: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_61_argument: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_61_returned: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_61_caller: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_62_source: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_17_62_argument: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_17_62_returned: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_17_62_caller: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_17_63_source: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_63_argument: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_63_returned: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_63_caller: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_64_source: isize,
    #[cfg(test)]
    mir_unit_17_64_argument: isize,
    #[cfg(test)]
    mir_unit_17_64_returned: isize,
    #[cfg(test)]
    mir_unit_17_64_caller: isize,
    #[cfg(test)]
    mir_unit_17_66_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_17_66_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_17_66_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_17_66_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_17_67_source: &'static mut crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_17_67_argument: &'static mut crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_17_67_returned: &'static mut crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_17_67_caller: &'static mut crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_17_68_source: std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_68_argument: std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_68_returned: std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_68_caller: std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_69_source: &'static mut [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_17_69_argument: &'static mut [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_17_69_returned: &'static mut [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_17_69_caller: &'static mut [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_17_70_source: &'static str,
    #[cfg(test)]
    mir_unit_17_70_argument: &'static str,
    #[cfg(test)]
    mir_unit_17_70_returned: &'static str,
    #[cfg(test)]
    mir_unit_17_70_caller: &'static str,
    #[cfg(test)]
    mir_unit_17_71_source: crate::experimental::cache::Operation,
    #[cfg(test)]
    mir_unit_17_71_argument: crate::experimental::cache::Operation,
    #[cfg(test)]
    mir_unit_17_71_returned: crate::experimental::cache::Operation,
    #[cfg(test)]
    mir_unit_17_71_caller: crate::experimental::cache::Operation,
    #[cfg(test)]
    mir_unit_17_72_source: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_72_argument: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_72_returned: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_72_caller: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_73_source: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_17_73_argument: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_17_73_returned: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_17_73_caller: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_17_74_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_17_74_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_17_74_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_17_74_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_17_75_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_17_75_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_17_75_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_17_75_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_17_76_source: &'static [crate::experimental::cache::DecodedInstruction],
    #[cfg(test)]
    mir_unit_17_76_argument: &'static [crate::experimental::cache::DecodedInstruction],
    #[cfg(test)]
    mir_unit_17_76_returned: &'static [crate::experimental::cache::DecodedInstruction],
    #[cfg(test)]
    mir_unit_17_76_caller: &'static [crate::experimental::cache::DecodedInstruction],
    #[cfg(test)]
    mir_unit_17_77_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_17_77_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_17_77_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_17_77_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_17_78_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_17_78_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_17_78_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_17_78_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_17_79_source: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_79_argument: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_79_returned: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_79_caller: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_80_source: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_80_argument: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_80_returned: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_80_caller: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_81_source: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_81_argument: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_81_returned: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_81_caller: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_17_29_source: u32,
    #[cfg(test)]
    mir_unit_17_29_argument: u32,
    #[cfg(test)]
    mir_unit_17_29_returned: u32,
    #[cfg(test)]
    mir_unit_17_29_caller: u32,
    #[cfg(test)]
    alias_unit_17_29_0_function_source: u32,
    #[cfg(test)]
    alias_unit_17_29_0_function_argument: u32,
    #[cfg(test)]
    alias_unit_17_29_0_function_returned: u32,
    #[cfg(test)]
    alias_unit_17_29_0_function_caller: u32,
    #[cfg(test)]
    mir_unit_17_30_source: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_17_30_argument: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_17_30_returned: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_17_30_caller: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_17_30_0_instruction_source: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_17_30_0_instruction_argument: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_17_30_0_instruction_returned: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_17_30_0_instruction_caller: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_17_49_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_49_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_49_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_49_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_17_49_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_17_49_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_17_49_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_17_49_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_53_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_53_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_53_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_53_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_17_53_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_17_53_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_17_53_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_17_53_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_65_source: usize,
    #[cfg(test)]
    mir_unit_17_65_argument: usize,
    #[cfg(test)]
    mir_unit_17_65_returned: usize,
    #[cfg(test)]
    mir_unit_17_65_caller: usize,
    #[cfg(test)]
    alias_unit_17_65_0_pc_source: usize,
    #[cfg(test)]
    alias_unit_17_65_0_pc_argument: usize,
    #[cfg(test)]
    alias_unit_17_65_0_pc_returned: usize,
    #[cfg(test)]
    alias_unit_17_65_0_pc_caller: usize,
    #[cfg(test)]
    alias_unit_17_65_1_pc_source: usize,
    #[cfg(test)]
    alias_unit_17_65_1_pc_argument: usize,
    #[cfg(test)]
    alias_unit_17_65_1_pc_returned: usize,
    #[cfg(test)]
    alias_unit_17_65_1_pc_caller: usize,
    #[cfg(test)]
    mir_unit_17_20_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_20_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_20_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_20_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_17_20_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_17_20_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_17_20_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_17_20_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_17_21_source: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    mir_unit_17_21_argument: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    mir_unit_17_21_returned: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    mir_unit_17_21_caller: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    alias_unit_17_21_0_view_source: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    alias_unit_17_21_0_view_argument: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    alias_unit_17_21_0_view_returned: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    alias_unit_17_21_0_view_caller: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    alias_unit_17_21_1_val_source: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    alias_unit_17_21_1_val_argument: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    alias_unit_17_21_1_val_returned: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    alias_unit_17_21_1_val_caller: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    mir_unit_17_22_source: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_17_22_argument: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_17_22_returned: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_17_22_caller: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_17_22_0_instruction_source: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_17_22_0_instruction_argument: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_17_22_0_instruction_returned: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_17_22_0_instruction_caller: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_17_26_source: &'static crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_17_26_argument: &'static crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_17_26_returned: &'static crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_17_26_caller: &'static crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_17_26_0_instruction_source: &'static crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_17_26_0_instruction_argument: &'static crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_17_26_0_instruction_returned: &'static crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_17_26_0_instruction_caller: &'static crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_17_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_17_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_17_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_17_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_17_1_0_phase_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_17_1_0_phase_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_17_1_0_phase_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_17_1_0_phase_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    literal_unit_17_0_source: &'static str,
    #[cfg(test)]
    literal_unit_17_0_argument: &'static str,
    #[cfg(test)]
    literal_unit_17_0_returned: &'static str,
    #[cfg(test)]
    literal_unit_17_0_caller: &'static str,
    #[cfg(test)]
    literal_unit_17_1_source: &'static str,
    #[cfg(test)]
    literal_unit_17_1_argument: &'static str,
    #[cfg(test)]
    literal_unit_17_1_returned: &'static str,
    #[cfg(test)]
    literal_unit_17_1_caller: &'static str,
    #[cfg(test)]
    literal_unit_17_2_source: u8,
    #[cfg(test)]
    literal_unit_17_2_argument: u8,
    #[cfg(test)]
    literal_unit_17_2_returned: u8,
    #[cfg(test)]
    literal_unit_17_2_caller: u8,
    #[cfg(test)]
    literal_unit_17_3_source: u8,
    #[cfg(test)]
    literal_unit_17_3_argument: u8,
    #[cfg(test)]
    literal_unit_17_3_returned: u8,
    #[cfg(test)]
    literal_unit_17_3_caller: u8,
    #[cfg(test)]
    literal_unit_17_4_source: u8,
    #[cfg(test)]
    literal_unit_17_4_argument: u8,
    #[cfg(test)]
    literal_unit_17_4_returned: u8,
    #[cfg(test)]
    literal_unit_17_4_caller: u8,
    #[cfg(test)]
    literal_unit_17_5_source: u8,
    #[cfg(test)]
    literal_unit_17_5_argument: u8,
    #[cfg(test)]
    literal_unit_17_5_returned: u8,
    #[cfg(test)]
    literal_unit_17_5_caller: u8,
    #[cfg(test)]
    literal_unit_17_6_source: usize,
    #[cfg(test)]
    literal_unit_17_6_argument: usize,
    #[cfg(test)]
    literal_unit_17_6_returned: usize,
    #[cfg(test)]
    literal_unit_17_6_caller: usize,
    #[cfg(test)]
    literal_unit_17_7_source: &'static str,
    #[cfg(test)]
    literal_unit_17_7_argument: &'static str,
    #[cfg(test)]
    literal_unit_17_7_returned: &'static str,
    #[cfg(test)]
    literal_unit_17_7_caller: &'static str,
    #[cfg(test)]
    literal_unit_17_8_source: &'static str,
    #[cfg(test)]
    literal_unit_17_8_argument: &'static str,
    #[cfg(test)]
    literal_unit_17_8_returned: &'static str,
    #[cfg(test)]
    literal_unit_17_8_caller: &'static str,
    #[cfg(test)]
    literal_unit_17_9_source: &'static str,
    #[cfg(test)]
    literal_unit_17_9_argument: &'static str,
    #[cfg(test)]
    literal_unit_17_9_returned: &'static str,
    #[cfg(test)]
    literal_unit_17_9_caller: &'static str,
    #[cfg(test)]
    mir_unit_18_0_source: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_18_0_argument: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_18_0_returned: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_18_0_caller: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_18_3_source: usize,
    #[cfg(test)]
    mir_unit_18_3_argument: usize,
    #[cfg(test)]
    mir_unit_18_3_returned: usize,
    #[cfg(test)]
    mir_unit_18_3_caller: usize,
    #[cfg(test)]
    mir_unit_18_1_source: (),
    #[cfg(test)]
    mir_unit_18_1_argument: (),
    #[cfg(test)]
    mir_unit_18_1_returned: (),
    #[cfg(test)]
    mir_unit_18_1_caller: (),
    #[cfg(test)]
    mir_unit_18_2_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_18_2_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_18_2_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_18_2_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_18_2_0_frame_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_18_2_0_frame_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_18_2_0_frame_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_18_2_0_frame_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    literal_unit_18_0_source: usize,
    #[cfg(test)]
    literal_unit_18_0_argument: usize,
    #[cfg(test)]
    literal_unit_18_0_returned: usize,
    #[cfg(test)]
    literal_unit_18_0_caller: usize,
    #[cfg(test)]
    mir_unit_19_0_source: &'static Type,
    #[cfg(test)]
    mir_unit_19_0_argument: &'static Type,
    #[cfg(test)]
    mir_unit_19_0_returned: &'static Type,
    #[cfg(test)]
    mir_unit_19_0_caller: &'static Type,
    #[cfg(test)]
    mir_unit_19_1_source: Type,
    #[cfg(test)]
    mir_unit_19_1_argument: Type,
    #[cfg(test)]
    mir_unit_19_1_returned: Type,
    #[cfg(test)]
    mir_unit_19_1_caller: Type,
    #[cfg(test)]
    mir_unit_20_0_source: &'static std::ops::RangeInclusive<u8>,
    #[cfg(test)]
    mir_unit_20_0_argument: &'static std::ops::RangeInclusive<u8>,
    #[cfg(test)]
    mir_unit_20_0_returned: &'static std::ops::RangeInclusive<u8>,
    #[cfg(test)]
    mir_unit_20_0_caller: &'static std::ops::RangeInclusive<u8>,
    #[cfg(test)]
    mir_unit_20_1_source: std::ops::RangeInclusive<u8>,
    #[cfg(test)]
    mir_unit_20_1_argument: std::ops::RangeInclusive<u8>,
    #[cfg(test)]
    mir_unit_20_1_returned: std::ops::RangeInclusive<u8>,
    #[cfg(test)]
    mir_unit_20_1_caller: std::ops::RangeInclusive<u8>,
    #[cfg(test)]
    literal_unit_20_0_source: u8,
    #[cfg(test)]
    literal_unit_20_0_argument: u8,
    #[cfg(test)]
    literal_unit_20_0_returned: u8,
    #[cfg(test)]
    literal_unit_20_0_caller: u8,
    #[cfg(test)]
    literal_unit_20_1_source: u8,
    #[cfg(test)]
    literal_unit_20_1_argument: u8,
    #[cfg(test)]
    literal_unit_20_1_returned: u8,
    #[cfg(test)]
    literal_unit_20_1_caller: u8,
    #[cfg(test)]
    mir_unit_21_0_source: &'static std::thread::LocalKey<std::cell::Cell<bool>>,
    #[cfg(test)]
    mir_unit_21_0_argument: &'static std::thread::LocalKey<std::cell::Cell<bool>>,
    #[cfg(test)]
    mir_unit_21_0_returned: &'static std::thread::LocalKey<std::cell::Cell<bool>>,
    #[cfg(test)]
    mir_unit_21_0_caller: &'static std::thread::LocalKey<std::cell::Cell<bool>>,
    #[cfg(test)]
    mir_unit_21_1_source: std::thread::LocalKey<std::cell::Cell<bool>>,
    #[cfg(test)]
    mir_unit_21_1_argument: std::thread::LocalKey<std::cell::Cell<bool>>,
    #[cfg(test)]
    mir_unit_21_1_returned: std::thread::LocalKey<std::cell::Cell<bool>>,
    #[cfg(test)]
    mir_unit_21_1_caller: std::thread::LocalKey<std::cell::Cell<bool>>,
    source_memory_range_phase_source: &'static mut FrameOperationPhase<'static>,
    source_memory_range_phase_argument: &'static mut FrameOperationPhase<'static>,
    source_memory_range_phase_returned: &'static mut FrameOperationPhase<'static>,
    source_memory_range_phase_caller: &'static mut FrameOperationPhase<'static>,
    source_memory_range_address_source: usize,
    source_memory_range_address_argument: usize,
    source_memory_range_address_returned: usize,
    source_memory_range_address_caller: usize,
    source_memory_range_length_source: usize,
    source_memory_range_length_argument: usize,
    source_memory_range_length_returned: usize,
    source_memory_range_length_caller: usize,
    source_memory_range_end_source: usize,
    source_memory_range_end_argument: usize,
    source_memory_range_end_returned: usize,
    source_memory_range_end_caller: usize,
    source_memory_range_checked_end_source: Option<usize>,
    source_memory_range_checked_end_argument: Option<usize>,
    source_memory_range_checked_end_returned: Option<usize>,
    source_memory_range_checked_end_caller: Option<usize>,
    source_memory_range_range_source: std::ops::Range<usize>,
    source_memory_range_range_argument: std::ops::Range<usize>,
    source_memory_range_range_returned: std::ops::Range<usize>,
    source_memory_range_range_caller: std::ops::Range<usize>,
    source_memory_range_result_source: Result<std::ops::Range<usize>, SwiftRunFailure>,
    source_memory_range_result_argument: Result<std::ops::Range<usize>, SwiftRunFailure>,
    source_memory_range_result_returned: Result<std::ops::Range<usize>, SwiftRunFailure>,
    source_memory_range_result_caller: Result<std::ops::Range<usize>, SwiftRunFailure>,
    source_memory_range_memory_source: &'static Vec<u8>,
    source_memory_range_memory_argument: &'static Vec<u8>,
    source_memory_range_memory_returned: &'static Vec<u8>,
    source_memory_range_memory_caller: &'static Vec<u8>,
    source_memory_range_end_reference_source: &'static usize,
    source_memory_range_end_reference_argument: &'static usize,
    source_memory_range_end_reference_returned: &'static usize,
    source_memory_range_end_reference_caller: &'static usize,
    source_memory_load_phase_source: &'static mut FrameOperationPhase<'static>,
    source_memory_load_phase_argument: &'static mut FrameOperationPhase<'static>,
    source_memory_load_phase_returned: &'static mut FrameOperationPhase<'static>,
    source_memory_load_phase_caller: &'static mut FrameOperationPhase<'static>,
    source_memory_load_opcode_source: u8,
    source_memory_load_opcode_argument: u8,
    source_memory_load_opcode_returned: u8,
    source_memory_load_opcode_caller: u8,
    source_memory_load_offset_source: u32,
    source_memory_load_offset_argument: u32,
    source_memory_load_offset_returned: u32,
    source_memory_load_offset_caller: u32,
    source_memory_load_address_source: usize,
    source_memory_load_address_argument: usize,
    source_memory_load_address_returned: usize,
    source_memory_load_address_caller: usize,
    source_memory_load_width_source: usize,
    source_memory_load_width_argument: usize,
    source_memory_load_width_returned: usize,
    source_memory_load_width_caller: usize,
    source_memory_load_start_source: usize,
    source_memory_load_start_argument: usize,
    source_memory_load_start_returned: usize,
    source_memory_load_start_caller: usize,
    source_memory_load_checked_start_source: Option<usize>,
    source_memory_load_checked_start_argument: Option<usize>,
    source_memory_load_checked_start_returned: Option<usize>,
    source_memory_load_checked_start_caller: Option<usize>,
    source_memory_load_range_source: std::ops::Range<usize>,
    source_memory_load_range_argument: std::ops::Range<usize>,
    source_memory_load_range_returned: std::ops::Range<usize>,
    source_memory_load_range_caller: std::ops::Range<usize>,
    source_memory_load_padded_source: [u8; 8],
    source_memory_load_padded_argument: [u8; 8],
    source_memory_load_padded_returned: [u8; 8],
    source_memory_load_padded_caller: [u8; 8],
    source_memory_load_x_source: u64,
    source_memory_load_x_argument: u64,
    source_memory_load_x_returned: u64,
    source_memory_load_x_caller: u64,
    source_memory_load_value_source: Value,
    source_memory_load_value_argument: Value,
    source_memory_load_value_returned: Value,
    source_memory_load_value_caller: Value,
    source_memory_load_address_result_source: Result<i32, SwiftRunFailure>,
    source_memory_load_address_result_argument: Result<i32, SwiftRunFailure>,
    source_memory_load_address_result_returned: Result<i32, SwiftRunFailure>,
    source_memory_load_address_result_caller: Result<i32, SwiftRunFailure>,
    source_memory_load_padded_slice_source: &'static mut [u8],
    source_memory_load_padded_slice_argument: &'static mut [u8],
    source_memory_load_padded_slice_returned: &'static mut [u8],
    source_memory_load_padded_slice_caller: &'static mut [u8],
    source_memory_load_memory_slice_source: &'static [u8],
    source_memory_load_memory_slice_argument: &'static [u8],
    source_memory_load_memory_slice_returned: &'static [u8],
    source_memory_load_memory_slice_caller: &'static [u8],
    source_memory_load_result_source: Result<(), SwiftRunFailure>,
    source_memory_load_result_argument: Result<(), SwiftRunFailure>,
    source_memory_load_result_returned: Result<(), SwiftRunFailure>,
    source_memory_load_result_caller: Result<(), SwiftRunFailure>,
    source_memory_store_phase_source: &'static mut FrameOperationPhase<'static>,
    source_memory_store_phase_argument: &'static mut FrameOperationPhase<'static>,
    source_memory_store_phase_returned: &'static mut FrameOperationPhase<'static>,
    source_memory_store_phase_caller: &'static mut FrameOperationPhase<'static>,
    source_memory_store_opcode_source: u8,
    source_memory_store_opcode_argument: u8,
    source_memory_store_opcode_returned: u8,
    source_memory_store_opcode_caller: u8,
    source_memory_store_offset_source: u32,
    source_memory_store_offset_argument: u32,
    source_memory_store_offset_returned: u32,
    source_memory_store_offset_caller: u32,
    source_memory_store_value_source: Value,
    source_memory_store_value_argument: Value,
    source_memory_store_value_returned: Value,
    source_memory_store_value_caller: Value,
    source_memory_store_address_source: usize,
    source_memory_store_address_argument: usize,
    source_memory_store_address_returned: usize,
    source_memory_store_address_caller: usize,
    source_memory_store_width_source: usize,
    source_memory_store_width_argument: usize,
    source_memory_store_width_returned: usize,
    source_memory_store_width_caller: usize,
    source_memory_store_start_source: usize,
    source_memory_store_start_argument: usize,
    source_memory_store_start_returned: usize,
    source_memory_store_start_caller: usize,
    source_memory_store_range_source: std::ops::Range<usize>,
    source_memory_store_range_argument: std::ops::Range<usize>,
    source_memory_store_range_returned: std::ops::Range<usize>,
    source_memory_store_range_caller: std::ops::Range<usize>,
    source_memory_store_bits_source: u64,
    source_memory_store_bits_argument: u64,
    source_memory_store_bits_returned: u64,
    source_memory_store_bits_caller: u64,
    source_memory_store_little_endian_source: [u8; 8],
    source_memory_store_little_endian_argument: [u8; 8],
    source_memory_store_little_endian_returned: [u8; 8],
    source_memory_store_little_endian_caller: [u8; 8],
    source_memory_store_narrow_bytes_source: &'static [u8],
    source_memory_store_narrow_bytes_argument: &'static [u8],
    source_memory_store_narrow_bytes_returned: &'static [u8],
    source_memory_store_narrow_bytes_caller: &'static [u8],
    source_memory_store_destination_source: &'static mut [u8],
    source_memory_store_destination_argument: &'static mut [u8],
    source_memory_store_destination_returned: &'static mut [u8],
    source_memory_store_destination_caller: &'static mut [u8],
    source_memory_store_result_source: Result<(), SwiftRunFailure>,
    source_memory_store_result_argument: Result<(), SwiftRunFailure>,
    source_memory_store_result_returned: Result<(), SwiftRunFailure>,
    source_memory_store_result_caller: Result<(), SwiftRunFailure>,
    source_memory_pop_value_phase_source: &'static mut FrameOperationPhase<'static>,
    source_memory_pop_value_phase_argument: &'static mut FrameOperationPhase<'static>,
    source_memory_pop_value_phase_returned: &'static mut FrameOperationPhase<'static>,
    source_memory_pop_value_phase_caller: &'static mut FrameOperationPhase<'static>,
    source_memory_pop_value_before_source: usize,
    source_memory_pop_value_before_argument: usize,
    source_memory_pop_value_before_returned: usize,
    source_memory_pop_value_before_caller: usize,
    source_memory_pop_value_result_source: Result<Value, SwiftRunFailure>,
    source_memory_pop_value_result_argument: Result<Value, SwiftRunFailure>,
    source_memory_pop_value_result_returned: Result<Value, SwiftRunFailure>,
    source_memory_pop_value_result_caller: Result<Value, SwiftRunFailure>,
    source_memory_pop_value_after_source: usize,
    source_memory_pop_value_after_argument: usize,
    source_memory_pop_value_after_returned: usize,
    source_memory_pop_value_after_caller: usize,
    source_memory_pop_value_debt_source: &'static mut bool,
    source_memory_pop_value_debt_argument: &'static mut bool,
    source_memory_pop_value_debt_returned: &'static mut bool,
    source_memory_pop_value_debt_caller: &'static mut bool,
    source_memory_pop32_phase_source: &'static mut FrameOperationPhase<'static>,
    source_memory_pop32_phase_argument: &'static mut FrameOperationPhase<'static>,
    source_memory_pop32_phase_returned: &'static mut FrameOperationPhase<'static>,
    source_memory_pop32_phase_caller: &'static mut FrameOperationPhase<'static>,
    source_memory_pop32_value_source: i32,
    source_memory_pop32_value_argument: i32,
    source_memory_pop32_value_returned: i32,
    source_memory_pop32_value_caller: i32,
    source_memory_pop32_raw_source: Result<Value, SwiftRunFailure>,
    source_memory_pop32_raw_argument: Result<Value, SwiftRunFailure>,
    source_memory_pop32_raw_returned: Result<Value, SwiftRunFailure>,
    source_memory_pop32_raw_caller: Result<Value, SwiftRunFailure>,
    source_memory_pop32_result_source: Result<i32, SwiftRunFailure>,
    source_memory_pop32_result_argument: Result<i32, SwiftRunFailure>,
    source_memory_pop32_result_returned: Result<i32, SwiftRunFailure>,
    source_memory_pop32_result_caller: Result<i32, SwiftRunFailure>,
    source_memory_preflight_phase_source: &'static mut FrameOperationPhase<'static>,
    source_memory_preflight_phase_argument: &'static mut FrameOperationPhase<'static>,
    source_memory_preflight_phase_returned: &'static mut FrameOperationPhase<'static>,
    source_memory_preflight_phase_caller: &'static mut FrameOperationPhase<'static>,
    source_memory_preflight_opcode_source: u8,
    source_memory_preflight_opcode_argument: u8,
    source_memory_preflight_opcode_returned: u8,
    source_memory_preflight_opcode_caller: u8,
    source_memory_preflight_store_source: bool,
    source_memory_preflight_store_argument: bool,
    source_memory_preflight_store_returned: bool,
    source_memory_preflight_store_caller: bool,
    source_memory_preflight_expected_source: Type,
    source_memory_preflight_expected_argument: Type,
    source_memory_preflight_expected_returned: Type,
    source_memory_preflight_expected_caller: Type,
    source_memory_preflight_frame_source: &'static SwiftFrame,
    source_memory_preflight_frame_argument: &'static SwiftFrame,
    source_memory_preflight_frame_returned: &'static SwiftFrame,
    source_memory_preflight_frame_caller: &'static SwiftFrame,
    source_memory_preflight_floor_source: usize,
    source_memory_preflight_floor_argument: usize,
    source_memory_preflight_floor_returned: usize,
    source_memory_preflight_floor_caller: usize,
    source_memory_preflight_available_source: usize,
    source_memory_preflight_available_argument: usize,
    source_memory_preflight_available_returned: usize,
    source_memory_preflight_available_caller: usize,
    source_memory_preflight_checked_available_source: Option<usize>,
    source_memory_preflight_checked_available_argument: Option<usize>,
    source_memory_preflight_checked_available_returned: Option<usize>,
    source_memory_preflight_checked_available_caller: Option<usize>,
    source_memory_preflight_count_source: usize,
    source_memory_preflight_count_argument: usize,
    source_memory_preflight_count_returned: usize,
    source_memory_preflight_count_caller: usize,
    source_memory_preflight_length_source: usize,
    source_memory_preflight_length_argument: usize,
    source_memory_preflight_length_returned: usize,
    source_memory_preflight_length_caller: usize,
    source_memory_preflight_type_reference_source: &'static Value,
    source_memory_preflight_type_reference_argument: &'static Value,
    source_memory_preflight_type_reference_returned: &'static Value,
    source_memory_preflight_type_reference_caller: &'static Value,
    source_memory_preflight_result_source: Result<(), SwiftRunFailure>,
    source_memory_preflight_result_argument: Result<(), SwiftRunFailure>,
    source_memory_preflight_result_returned: Result<(), SwiftRunFailure>,
    source_memory_preflight_result_caller: Result<(), SwiftRunFailure>,
    source_memory_trap_phase_source: &'static mut FrameOperationPhase<'static>,
    source_memory_trap_phase_argument: &'static mut FrameOperationPhase<'static>,
    source_memory_trap_phase_returned: &'static mut FrameOperationPhase<'static>,
    source_memory_trap_phase_caller: &'static mut FrameOperationPhase<'static>,
    source_memory_trap_cursor_source: Cursor,
    source_memory_trap_cursor_argument: Cursor,
    source_memory_trap_cursor_returned: Cursor,
    source_memory_trap_cursor_caller: Cursor,
    source_memory_trap_fault_source: Fault,
    source_memory_trap_fault_argument: Fault,
    source_memory_trap_fault_returned: Fault,
    source_memory_trap_fault_caller: Fault,
    source_memory_trap_wasi_source: Option<WasiUsage>,
    source_memory_trap_wasi_argument: Option<WasiUsage>,
    source_memory_trap_wasi_returned: Option<WasiUsage>,
    source_memory_trap_wasi_caller: Option<WasiUsage>,
    source_memory_trap_failure_source: SwiftRunFailure,
    source_memory_trap_failure_argument: SwiftRunFailure,
    source_memory_trap_failure_returned: SwiftRunFailure,
    source_memory_trap_failure_caller: SwiftRunFailure,
    source_memory_unsupported_phase_source: &'static mut FrameOperationPhase<'static>,
    source_memory_unsupported_phase_argument: &'static mut FrameOperationPhase<'static>,
    source_memory_unsupported_phase_returned: &'static mut FrameOperationPhase<'static>,
    source_memory_unsupported_phase_caller: &'static mut FrameOperationPhase<'static>,
    source_memory_unsupported_cursor_source: Cursor,
    source_memory_unsupported_cursor_argument: Cursor,
    source_memory_unsupported_cursor_returned: Cursor,
    source_memory_unsupported_cursor_caller: Cursor,
    source_memory_unsupported_fault_source: Fault,
    source_memory_unsupported_fault_argument: Fault,
    source_memory_unsupported_fault_returned: Fault,
    source_memory_unsupported_fault_caller: Fault,
    source_memory_unsupported_wasi_source: Option<WasiUsage>,
    source_memory_unsupported_wasi_argument: Option<WasiUsage>,
    source_memory_unsupported_wasi_returned: Option<WasiUsage>,
    source_memory_unsupported_wasi_caller: Option<WasiUsage>,
    source_memory_unsupported_failure_source: SwiftRunFailure,
    source_memory_unsupported_failure_argument: SwiftRunFailure,
    source_memory_unsupported_failure_returned: SwiftRunFailure,
    source_memory_unsupported_failure_caller: SwiftRunFailure,
    source_memory_operation_phase_source: &'static mut FrameOperationPhase<'static>,
    source_memory_operation_phase_argument: &'static mut FrameOperationPhase<'static>,
    source_memory_operation_phase_returned: &'static mut FrameOperationPhase<'static>,
    source_memory_operation_phase_caller: &'static mut FrameOperationPhase<'static>,
    source_memory_operation_operation_source: Operation,
    source_memory_operation_operation_argument: Operation,
    source_memory_operation_operation_returned: Operation,
    source_memory_operation_operation_caller: Operation,
    source_memory_operation_returned_source: &'static mut Option<Result<(), SwiftRunFailure>>,
    source_memory_operation_returned_argument: &'static mut Option<Result<(), SwiftRunFailure>>,
    source_memory_operation_returned_returned: &'static mut Option<Result<(), SwiftRunFailure>>,
    source_memory_operation_returned_caller: &'static mut Option<Result<(), SwiftRunFailure>>,
    source_memory_operation_previous_slot_source: &'static Option<Result<(), SwiftRunFailure>>,
    source_memory_operation_previous_slot_argument: &'static Option<Result<(), SwiftRunFailure>>,
    source_memory_operation_previous_slot_returned: &'static Option<Result<(), SwiftRunFailure>>,
    source_memory_operation_previous_slot_caller: &'static Option<Result<(), SwiftRunFailure>>,
    source_memory_operation_vacant_source: bool,
    source_memory_operation_vacant_argument: bool,
    source_memory_operation_vacant_returned: bool,
    source_memory_operation_vacant_caller: bool,
    source_memory_operation_failure_source: SwiftRunFailure,
    source_memory_operation_failure_argument: SwiftRunFailure,
    source_memory_operation_failure_returned: SwiftRunFailure,
    source_memory_operation_failure_caller: SwiftRunFailure,
    source_memory_operation_result_source: Result<(), SwiftRunFailure>,
    source_memory_operation_result_argument: Result<(), SwiftRunFailure>,
    source_memory_operation_result_returned: Result<(), SwiftRunFailure>,
    source_memory_operation_result_caller: Result<(), SwiftRunFailure>,
    source_memory_operation_published_source: Option<Result<(), SwiftRunFailure>>,
    source_memory_operation_published_argument: Option<Result<(), SwiftRunFailure>>,
    source_memory_operation_published_returned: Option<Result<(), SwiftRunFailure>>,
    source_memory_operation_published_caller: Option<Result<(), SwiftRunFailure>>,
    source_memory_operation_admission_source: Result<(), SwiftRunFailure>,
    source_memory_operation_admission_argument: Result<(), SwiftRunFailure>,
    source_memory_operation_admission_returned: Result<(), SwiftRunFailure>,
    source_memory_operation_admission_caller: Result<(), SwiftRunFailure>,
    source_memory_operation_inner_phase_source: &'static mut FrameOperationPhase<'static>,
    source_memory_operation_inner_phase_argument: &'static mut FrameOperationPhase<'static>,
    source_memory_operation_inner_phase_returned: &'static mut FrameOperationPhase<'static>,
    source_memory_operation_inner_phase_caller: &'static mut FrameOperationPhase<'static>,
    source_memory_operation_inner_operation_source: Operation,
    source_memory_operation_inner_operation_argument: Operation,
    source_memory_operation_inner_operation_returned: Operation,
    source_memory_operation_inner_operation_caller: Operation,
    source_memory_operation_inner_opcode_source: u8,
    source_memory_operation_inner_opcode_argument: u8,
    source_memory_operation_inner_opcode_returned: u8,
    source_memory_operation_inner_opcode_caller: u8,
    source_memory_operation_inner_offset_source: u32,
    source_memory_operation_inner_offset_argument: u32,
    source_memory_operation_inner_offset_returned: u32,
    source_memory_operation_inner_offset_caller: u32,
    source_memory_operation_inner_result_source: Result<(), SwiftRunFailure>,
    source_memory_operation_inner_result_argument: Result<(), SwiftRunFailure>,
    source_memory_operation_inner_result_returned: Result<(), SwiftRunFailure>,
    source_memory_operation_inner_result_caller: Result<(), SwiftRunFailure>,
    source_memory_pinned_caller_prerequisite_phase_source: &'static mut FrameOperationPhase<'static>,
    source_memory_pinned_caller_prerequisite_phase_argument: &'static mut FrameOperationPhase<'static>,
    source_memory_pinned_caller_prerequisite_phase_returned: &'static mut FrameOperationPhase<'static>,
    source_memory_pinned_caller_prerequisite_phase_caller: &'static mut FrameOperationPhase<'static>,
    source_memory_pinned_caller_prerequisite_storage_source: &'static mut FrameOperationStorage<'static>,
    source_memory_pinned_caller_prerequisite_storage_argument: &'static mut FrameOperationStorage<'static>,
    source_memory_pinned_caller_prerequisite_storage_returned: &'static mut FrameOperationStorage<'static>,
    source_memory_pinned_caller_prerequisite_storage_caller: &'static mut FrameOperationStorage<'static>,
    source_memory_pinned_caller_prerequisite_slot_source: &'static mut Option<Result<(), SwiftRunFailure>>,
    source_memory_pinned_caller_prerequisite_slot_argument: &'static mut Option<Result<(), SwiftRunFailure>>,
    source_memory_pinned_caller_prerequisite_slot_returned: &'static mut Option<Result<(), SwiftRunFailure>>,
    source_memory_pinned_caller_prerequisite_slot_caller: &'static mut Option<Result<(), SwiftRunFailure>>,
    source_memory_pinned_caller_prerequisite_frame_source: &'static SwiftFrame,
    source_memory_pinned_caller_prerequisite_frame_argument: &'static SwiftFrame,
    source_memory_pinned_caller_prerequisite_frame_returned: &'static SwiftFrame,
    source_memory_pinned_caller_prerequisite_frame_caller: &'static SwiftFrame,
    source_memory_pinned_caller_prerequisite_pin_source: &'static SwiftFunctionPin,
    source_memory_pinned_caller_prerequisite_pin_argument: &'static SwiftFunctionPin,
    source_memory_pinned_caller_prerequisite_pin_returned: &'static SwiftFunctionPin,
    source_memory_pinned_caller_prerequisite_pin_caller: &'static SwiftFunctionPin,
    source_memory_pinned_caller_prerequisite_view_source: FunctionView<'static>,
    source_memory_pinned_caller_prerequisite_view_argument: FunctionView<'static>,
    source_memory_pinned_caller_prerequisite_view_returned: FunctionView<'static>,
    source_memory_pinned_caller_prerequisite_view_caller: FunctionView<'static>,
    source_memory_pinned_caller_prerequisite_instruction_source: DecodedInstruction,
    source_memory_pinned_caller_prerequisite_instruction_argument: DecodedInstruction,
    source_memory_pinned_caller_prerequisite_instruction_returned: DecodedInstruction,
    source_memory_pinned_caller_prerequisite_instruction_caller: DecodedInstruction,
    source_memory_pinned_caller_prerequisite_instruction_borrow_source: &'static DecodedInstruction,
    source_memory_pinned_caller_prerequisite_instruction_borrow_argument: &'static DecodedInstruction,
    source_memory_pinned_caller_prerequisite_instruction_borrow_returned: &'static DecodedInstruction,
    source_memory_pinned_caller_prerequisite_instruction_borrow_caller: &'static DecodedInstruction,
    source_memory_pinned_caller_prerequisite_selection_source: (u32, DecodedInstruction),
    source_memory_pinned_caller_prerequisite_selection_argument: (u32, DecodedInstruction),
    source_memory_pinned_caller_prerequisite_selection_returned: (u32, DecodedInstruction),
    source_memory_pinned_caller_prerequisite_selection_caller: (u32, DecodedInstruction),
    source_memory_pinned_caller_prerequisite_function_source: u32,
    source_memory_pinned_caller_prerequisite_function_argument: u32,
    source_memory_pinned_caller_prerequisite_function_returned: u32,
    source_memory_pinned_caller_prerequisite_function_caller: u32,
    source_memory_pinned_caller_prerequisite_cursor_source: Cursor,
    source_memory_pinned_caller_prerequisite_cursor_argument: Cursor,
    source_memory_pinned_caller_prerequisite_cursor_returned: Cursor,
    source_memory_pinned_caller_prerequisite_cursor_caller: Cursor,
    source_memory_pinned_caller_prerequisite_charged_source: Result<(), SwiftRunFailure>,
    source_memory_pinned_caller_prerequisite_charged_argument: Result<(), SwiftRunFailure>,
    source_memory_pinned_caller_prerequisite_charged_returned: Result<(), SwiftRunFailure>,
    source_memory_pinned_caller_prerequisite_charged_caller: Result<(), SwiftRunFailure>,
    source_memory_pinned_caller_prerequisite_pc_source: usize,
    source_memory_pinned_caller_prerequisite_pc_argument: usize,
    source_memory_pinned_caller_prerequisite_pc_returned: usize,
    source_memory_pinned_caller_prerequisite_pc_caller: usize,
    source_memory_pinned_caller_prerequisite_checked_pc_source: Option<usize>,
    source_memory_pinned_caller_prerequisite_checked_pc_argument: Option<usize>,
    source_memory_pinned_caller_prerequisite_checked_pc_returned: Option<usize>,
    source_memory_pinned_caller_prerequisite_checked_pc_caller: Option<usize>,
    source_memory_pinned_caller_prerequisite_frame_mut_source: &'static mut SwiftFrame,
    source_memory_pinned_caller_prerequisite_frame_mut_argument: &'static mut SwiftFrame,
    source_memory_pinned_caller_prerequisite_frame_mut_returned: &'static mut SwiftFrame,
    source_memory_pinned_caller_prerequisite_frame_mut_caller: &'static mut SwiftFrame,
    source_memory_pinned_caller_prerequisite_failure_source: SwiftRunFailure,
    source_memory_pinned_caller_prerequisite_failure_argument: SwiftRunFailure,
    source_memory_pinned_caller_prerequisite_failure_returned: SwiftRunFailure,
    source_memory_pinned_caller_prerequisite_failure_caller: SwiftRunFailure,
    source_memory_pinned_caller_prerequisite_admission_source: Result<(), SwiftRunFailure>,
    source_memory_pinned_caller_prerequisite_admission_argument: Result<(), SwiftRunFailure>,
    source_memory_pinned_caller_prerequisite_admission_returned: Result<(), SwiftRunFailure>,
    source_memory_pinned_caller_prerequisite_admission_caller: Result<(), SwiftRunFailure>,
    source_shared_width_opcode_source: u8,
    source_shared_width_opcode_argument: u8,
    source_shared_width_opcode_returned: u8,
    source_shared_width_opcode_caller: u8,
    source_shared_width_width_source: usize,
    source_shared_width_width_argument: usize,
    source_shared_width_width_returned: usize,
    source_shared_width_width_caller: usize,
    source_memory_pinned_step_phase_source: &'static mut FrameOperationPhase<'static>,
    source_memory_pinned_step_phase_argument: &'static mut FrameOperationPhase<'static>,
    source_memory_pinned_step_phase_returned: &'static mut FrameOperationPhase<'static>,
    source_memory_pinned_step_phase_caller: &'static mut FrameOperationPhase<'static>,
    source_memory_pinned_step_frame_source: &'static SwiftFrame,
    source_memory_pinned_step_frame_argument: &'static SwiftFrame,
    source_memory_pinned_step_frame_returned: &'static SwiftFrame,
    source_memory_pinned_step_frame_caller: &'static SwiftFrame,
    source_memory_pinned_step_pin_source: &'static SwiftFunctionPin,
    source_memory_pinned_step_pin_argument: &'static SwiftFunctionPin,
    source_memory_pinned_step_pin_returned: &'static SwiftFunctionPin,
    source_memory_pinned_step_pin_caller: &'static SwiftFunctionPin,
    source_memory_pinned_step_view_source: FunctionView<'static>,
    source_memory_pinned_step_view_argument: FunctionView<'static>,
    source_memory_pinned_step_view_returned: FunctionView<'static>,
    source_memory_pinned_step_view_caller: FunctionView<'static>,
    source_memory_pinned_step_instruction_source: DecodedInstruction,
    source_memory_pinned_step_instruction_argument: DecodedInstruction,
    source_memory_pinned_step_instruction_returned: DecodedInstruction,
    source_memory_pinned_step_instruction_caller: DecodedInstruction,
    source_memory_pinned_step_instruction_borrow_source: &'static DecodedInstruction,
    source_memory_pinned_step_instruction_borrow_argument: &'static DecodedInstruction,
    source_memory_pinned_step_instruction_borrow_returned: &'static DecodedInstruction,
    source_memory_pinned_step_instruction_borrow_caller: &'static DecodedInstruction,
    source_memory_pinned_step_selection_source: (u32, DecodedInstruction),
    source_memory_pinned_step_selection_argument: (u32, DecodedInstruction),
    source_memory_pinned_step_selection_returned: (u32, DecodedInstruction),
    source_memory_pinned_step_selection_caller: (u32, DecodedInstruction),
    source_memory_pinned_step_function_source: u32,
    source_memory_pinned_step_function_argument: u32,
    source_memory_pinned_step_function_returned: u32,
    source_memory_pinned_step_function_caller: u32,
    source_memory_pinned_step_cursor_source: Cursor,
    source_memory_pinned_step_cursor_argument: Cursor,
    source_memory_pinned_step_cursor_returned: Cursor,
    source_memory_pinned_step_cursor_caller: Cursor,
    source_memory_pinned_step_charged_source: Result<(), SwiftRunFailure>,
    source_memory_pinned_step_charged_argument: Result<(), SwiftRunFailure>,
    source_memory_pinned_step_charged_returned: Result<(), SwiftRunFailure>,
    source_memory_pinned_step_charged_caller: Result<(), SwiftRunFailure>,
    source_memory_pinned_step_pc_source: usize,
    source_memory_pinned_step_pc_argument: usize,
    source_memory_pinned_step_pc_returned: usize,
    source_memory_pinned_step_pc_caller: usize,
    source_memory_pinned_step_checked_pc_source: Option<usize>,
    source_memory_pinned_step_checked_pc_argument: Option<usize>,
    source_memory_pinned_step_checked_pc_returned: Option<usize>,
    source_memory_pinned_step_checked_pc_caller: Option<usize>,
    source_memory_pinned_step_frame_mut_source: &'static mut SwiftFrame,
    source_memory_pinned_step_frame_mut_argument: &'static mut SwiftFrame,
    source_memory_pinned_step_frame_mut_returned: &'static mut SwiftFrame,
    source_memory_pinned_step_frame_mut_caller: &'static mut SwiftFrame,
    source_memory_pinned_step_failure_source: SwiftRunFailure,
    source_memory_pinned_step_failure_argument: SwiftRunFailure,
    source_memory_pinned_step_failure_returned: SwiftRunFailure,
    source_memory_pinned_step_failure_caller: SwiftRunFailure,
    source_memory_pinned_step_admission_source: Result<(), SwiftRunFailure>,
    source_memory_pinned_step_admission_argument: Result<(), SwiftRunFailure>,
    source_memory_pinned_step_admission_returned: Result<(), SwiftRunFailure>,
    source_memory_pinned_step_admission_caller: Result<(), SwiftRunFailure>,
    source_memory_pinned_step_result_source: Result<(), SwiftRunFailure>,
    source_memory_pinned_step_result_argument: Result<(), SwiftRunFailure>,
    source_memory_pinned_step_result_returned: Result<(), SwiftRunFailure>,
    source_memory_pinned_step_result_caller: Result<(), SwiftRunFailure>,
    source_memory_push_value_phase_source: &'static mut FrameOperationPhase<'static>,
    source_memory_push_value_phase_argument: &'static mut FrameOperationPhase<'static>,
    source_memory_push_value_phase_returned: &'static mut FrameOperationPhase<'static>,
    source_memory_push_value_phase_caller: &'static mut FrameOperationPhase<'static>,
    source_memory_push_value_value_source: Value,
    source_memory_push_value_value_argument: Value,
    source_memory_push_value_value_returned: Value,
    source_memory_push_value_value_caller: Value,
    source_memory_push_value_result_source: Result<(), SwiftRunFailure>,
    source_memory_push_value_result_argument: Result<(), SwiftRunFailure>,
    source_memory_push_value_result_returned: Result<(), SwiftRunFailure>,
    source_memory_push_value_result_caller: Result<(), SwiftRunFailure>,
}
pub(in crate::experimental_swift_reactor::execution) const PERMANENT_BYTES: usize = size_of::<PermanentPositions>();
pub(super) const ACTIVE_BYTES: usize = size_of::<ActivePositions>();
