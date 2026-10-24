//! Isolated, uncalled real-owner signature/borrow witness. No guest executes.
use super::*;
use crate::experimental::cache::ControlKind;

macro_rules! swift_contract_leaf {
    (pop $s:ident) => { $s.phase.pop_value() };
    (push $s:ident, $v:expr) => { $s.phase.push_value($v) };
    (invariant $s:ident) => { $s.invariant("swift_control_contract_invariant") };
    (values $s:ident) => { $s.phase.parts.values };
    (controls $s:ident) => { $s.phase.parts.controls };
    (frame $s:ident, $f:ident) => {
        let $f = match $s.phase.parts.frames.last() {
            Some(frame) => frame.controls,
            None => return Err($s.invariant("swift_control_contract_frame")),
        };
    };
    (floor $f:ident) => { $f };
    (result $c:ident) => { $c.contract_result() };
    (height $c:ident) => { $c.contract_height() };
    (loop $c:ident) => { $c.contract_is_loop() };
    (function $c:ident) => { $c.contract_is_function() };
    (clear $c:ident) => { $c.contract_clear_result() };
    (start $c:ident) => { $c.contract_start() };
    (after_end $c:ident) => { $c.contract_end() + 1 };
    (truncate_values $s:ident, $height:expr) => { $s.contract_truncate_values($height)? };
    (truncate_controls $s:ident, $height:expr) => { $s.contract_truncate_controls($height)? };
    (observe $s:ident) => { $s.agreement()? };
    (set_pc $s:ident, $pc:expr) => {
        match $s.phase.parts.frames.last_mut() {
            Some(frame) => frame.pc = $pc,
            None => return Err($s.invariant("swift_control_contract_pc")),
        }
    };
}

impl FrameOperationPhase<'_> {
    crate::experimental::execution::borrowed::contract_control_methods!(
        self, SwiftRunFailure, swift_contract_leaf, control,
        { self.contract_close_floor(control)?; }
    );

    // Type declarations only; these bodies are intentionally never implemented
    // or called by the metadata test. They cannot qualify control behavior.
    fn contract_close_floor(&mut self, _: Control) -> Result<(), SwiftRunFailure> {
        unimplemented!("contract declaration only")
    }
    fn contract_truncate_values(&mut self, _: usize) -> Result<(), SwiftRunFailure> {
        unimplemented!("contract declaration only")
    }
    fn contract_truncate_controls(&mut self, _: usize) -> Result<(), SwiftRunFailure> {
        unimplemented!("contract declaration only")
    }
    fn contract_control_operation(
        &mut self, _: Operation, _: Option<u32>,
    ) -> Result<bool, SwiftRunFailure> {
        unimplemented!("contract declaration only")
    }

    // Checks short original-field borrows against actual leaf APIs. Not called.
    fn contract_original_borrows(&mut self, control: Control) -> Result<(), SwiftRunFailure> {
        self.active()?;
        let frame = match self.phase.parts.frames.last() {
            Some(frame) => (frame.operands, frame.controls, frame.pc),
            None => return Err(self.invariant("swift_control_contract_frame")),
        };
        let (operands, controls, pc) = frame;
        let _ = (operands, controls, pc, control.contract_height());
        let selected = {
            let frame = self.phase.parts.frames.last().unwrap();
            let view = self.phase.parts.cache.view(
                &frame.pin, self.phase.operation.control, Some(&*self.phase.operation.wasi),
            )?;
            *view.instructions.get(pc).unwrap()
        };
        self.phase.operation.cursor = Cursor {
            stage: SwiftRunStage::Invocation,
            function: Some(self.phase.parts.frames.last().unwrap().function),
            offset: Some(selected.offset),
        };
        self.phase.operation.control.work_with_wasi(
            Work::Execution, 1, self.phase.operation.cursor,
            Some(self.phase.operation.wasi.usage()),
        )?;
        self.phase.operation.control.add_live_with_wasi(
            Live::Controls, 1, self.phase.operation.cursor,
            Some(self.phase.operation.wasi.usage()),
        )?;
        let removed = self.phase.operation.control.remove_live_with_wasi(
            Live::Controls, 1, Some(self.phase.operation.wasi.usage()),
        );
        if removed.is_err() { self.cleanup.live_unreconciled = true; }
        removed?;
        self.phase.pop_value()?;
        self.phase.push_value(Value::I32(0))?;
        self.agreement()?;
        Ok(())
    }
}

/// Proposed exact additional caller slot, measured with the real phase lifetime.
struct ProposedFrameOperationStorage<'a> {
    existing: FrameOperationStorage<'a>,
    controlled: Option<Result<bool, SwiftRunFailure>>,
}

#[test]
fn control_invocation_contract_metadata_only() {
    let _: fn(&mut FrameOperationPhase<'static>, Operation, Option<u32>)
        -> Result<bool, SwiftRunFailure> = FrameOperationPhase::contract_control_operation;
    let _: fn(&mut FrameOperationPhase<'static>, u32)
        -> Result<bool, SwiftRunFailure> = FrameOperationPhase::branch;
    let _: fn(&mut FrameOperationPhase<'static>, Control)
        -> Result<(), SwiftRunFailure> = FrameOperationPhase::close_control;
    let _: fn(&mut FrameOperationPhase<'static>)
        -> Result<i32, SwiftRunFailure> = FrameOperationPhase::pop32;
    let _: fn(ControlKind, usize, usize, usize, bool) -> Control = Control::contract_decoded;
    macro_rules! row { ($t:ty) => { println!("contract_size|{}|{}", stringify!($t), size_of::<$t>()); }; }
    row!(Control); row!(SwiftFrame); row!(FrameOperationPhase<'static>);
    row!(FrameOperationStorage<'static>); row!(ProposedFrameOperationStorage<'static>);
    row!(SwiftRunFailure); row!(Result<bool, SwiftRunFailure>);
    row!(Option<Result<bool, SwiftRunFailure>>); row!(Operation);
    row!(Option<u32>); row!(Cursor); row!(Value); row!(Option<Value>);
    row!(Option<&'static SwiftFrame>); row!(Option<&'static mut SwiftFrame>);
    row!(ControlFlow<Result<Infallible, SwiftRunFailure>, bool>);
    row!(Result<Infallible, SwiftRunFailure>);
    assert!(size_of::<ProposedFrameOperationStorage<'static>>() > size_of::<FrameOperationStorage<'static>>());
}
