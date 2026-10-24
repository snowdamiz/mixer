from pathlib import Path
import json,re
H=Path(__file__).resolve().parent
S=Path(json.loads((H/'session.json').read_text())['scratch'])
v=S/'candidate/vm'
p=v/'src/experimental_swift_reactor/memory_operations.rs'
s=p.read_text(); a=s.index('/// Uncalled compiling caller witness.'); b=s.index('// ACCOUNTING_START')
s=s[:a]+'''/// Bounded one-step actual pinned caller. Outer success means publication only.
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

'''+s[b:]
s=s.replace('(push $s:ident, $v:expr) => { $s.phase.push_value($v) };','(push $s:ident, $v:expr) => { $s.memory_push_value($v) };')
pos=s.index('    fn memory_pop_value(')
s=s[:pos]+'''    fn memory_push_value(&mut self, value: Value) -> Result<(), SwiftRunFailure> {
        #[cfg(test)]
        let old = super::tests::before_result_push(self.phase.operation.control);
        let result = self.phase.push_value(value);
        #[cfg(test)]
        super::tests::after_result_push(self.phase.operation.control, old);
        result
    }

'''+s[pos:];p.write_text(s)
# Reuse the original authored fixtures and actual fault hooks. Visibility only;
# no new constructor, owner shape, cache algorithm or ledger is introduced.
p=v/'src/experimental_swift_reactor/frame_operations_tests.rs';s=p.read_text()
for n in ['hooks','cursor','owner','retire','drain_complete','pin_ids','install_foreign','restore_foreign']:
 s=s.replace('fn '+n+'(', 'pub(super) fn '+n+'(',1)
s=s.replace('mod control_tests;','pub(super) mod control_tests;')
a=s.index('pub(super) struct Hooks {');b=s.index('\n}',a)
s=s[:a]+re.sub(r'(?m)^    (\w+:)',r'    pub(super) \1',s[a:b])+s[b:]
p.write_text(s)
p=v/'src/experimental_swift_reactor/control_operations_tests.rs';s=p.read_text().replace('fn body_owner(', 'pub(in crate::experimental_swift_reactor::execution::frame_operations) fn body_owner(',1);p.write_text(s)
