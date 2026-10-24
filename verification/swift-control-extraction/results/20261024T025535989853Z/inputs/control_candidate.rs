// Isolated contract probe only. Never included by product source.
trait ControlMode: ExecutionMode + Sized {
    type ControlState<'owner>;
    fn work(state: &mut Self::ControlState<'_>, amount: usize) -> Result<(), Self::Failure>;
    fn pop(state: &mut Self::ControlState<'_>) -> Result<Value, Self::Failure>;
    fn push(state: &mut Self::ControlState<'_>, value: Value) -> Result<(), Self::Failure>;
    fn invariant(state: &Self::ControlState<'_>) -> Self::Failure;
    fn values_len(state: &Self::ControlState<'_>) -> usize;
    fn controls_len(state: &Self::ControlState<'_>) -> usize;
    fn frame_control_base(state: &Self::ControlState<'_>) -> Option<usize>;
    fn control_at(state: &Self::ControlState<'_>, index: usize) -> Control;
    fn truncate_values(state: &mut Self::ControlState<'_>, height: usize)
        -> Result<(), Self::Failure>;
    fn truncate_controls(state: &mut Self::ControlState<'_>, height: usize)
        -> Result<(), Self::Failure>;
    fn set_pc(state: &mut Self::ControlState<'_>, pc: usize) -> Result<(), Self::Failure>;
    fn observe(state: &mut Self::ControlState<'_>) -> Result<(), Self::Failure>;
}

impl ControlMode for FrozenMode {
    type ControlState<'owner> = SpanInstance;
    fn work(state: &mut SpanInstance, amount: usize) -> Result<(), ExecutionFailure> {
        state.work(amount)
    }
    fn pop(state: &mut SpanInstance) -> Result<Value, ExecutionFailure> {
        state.pop()
    }
    fn push(state: &mut SpanInstance, value: Value) -> Result<(), ExecutionFailure> {
        state.push(value)
    }
    fn invariant(state: &SpanInstance) -> ExecutionFailure {
        state.invariant()
    }
    fn values_len(state: &SpanInstance) -> usize {
        state.values.len()
    }
    fn controls_len(state: &SpanInstance) -> usize {
        state.controls.len()
    }
    fn frame_control_base(state: &SpanInstance) -> Option<usize> {
        state.frames.last().map(|frame| frame.controls)
    }
    fn control_at(state: &SpanInstance, index: usize) -> Control {
        state.controls[index]
    }
    fn truncate_values(state: &mut SpanInstance, height: usize) -> Result<(), ExecutionFailure> {
        state.values.truncate(height);
        Ok(())
    }
    fn truncate_controls(state: &mut SpanInstance, height: usize) -> Result<(), ExecutionFailure> {
        state.controls.truncate(height);
        Ok(())
    }
    fn set_pc(state: &mut SpanInstance, pc: usize) -> Result<(), ExecutionFailure> {
        state.frames.last_mut().ok_or_else(unreachable_failure)?.pc = pc;
        Ok(())
    }
    fn observe(state: &mut SpanInstance) -> Result<(), ExecutionFailure> {
        state.observe();
        Ok(())
    }
}

fn pop32<M: ControlMode>(state: &mut M::ControlState<'_>) -> Result<i32, M::Failure> {
    match M::pop(state)? {
        Value::I32(value) => Ok(value),
        _ => Err(M::invariant(state)),
    }
}

fn close_control<M: ControlMode>(
    state: &mut M::ControlState<'_>,
    control: Control,
) -> Result<(), M::Failure> {
    let value = if control.result { Some(M::pop(state)?) } else { None };
    if control.height > M::values_len(state) {
        return Err(M::invariant(state));
    }
    M::work(state, M::values_len(state) - control.height + 1)?;
    M::truncate_values(state, control.height)?;
    M::observe(state)?;
    if let Some(value) = value {
        M::push(state, value)?;
    }
    Ok(())
}

fn branch<M: ControlMode>(
    state: &mut M::ControlState<'_>,
    depth: u32,
) -> Result<bool, M::Failure> {
    let frame_controls = M::frame_control_base(state).ok_or_else(|| M::invariant(state))?;
    let index = M::controls_len(state)
        .checked_sub(depth as usize + 1)
        .filter(|index| *index >= frame_controls)
        .ok_or_else(|| M::invariant(state))?;
    let mut control = M::control_at(state, index);
    M::work(state, M::controls_len(state) - index)?;
    if control.kind == Kind::Loop {
        control.result = false;
    }
    close_control::<M>(state, control)?;
    M::truncate_controls(state, if control.kind == Kind::Loop { index + 1 } else { index })?;
    let pc = if control.kind == Kind::Loop { control.start } else { control.end + 1 };
    M::set_pc(state, pc)?;
    M::observe(state)?;
    Ok(control.kind == Kind::Function)
}

#[test]
fn control_adapter_transfer_accounting_probe() {
    use std::mem::{align_of, offset_of, size_of};
    // These are additional transfer roles in the proposed ControlMode::work
    // boundary. They cannot alias the original owner error positions. This is
    // a necessary subset only, not a claimed complete simultaneous inventory.
    #[repr(C)]
    struct NewControlWorkTransfer {
        source_result: Result<(), ExecutionFailure>,
        returned_result: Result<(), ExecutionFailure>,
        caller_result: Result<(), ExecutionFailure>,
    }
    macro_rules! row {
        ($field:ident) => {
            println!("control_transfer_position {} offset={} bytes={}",
                stringify!($field), offset_of!(NewControlWorkTransfer, $field),
                size_of::<Result<(), ExecutionFailure>>());
        };
    }
    row!(source_result);
    row!(returned_result);
    row!(caller_result);
    let scalar_component = 512usize;
    let transfer = size_of::<NewControlWorkTransfer>();
    let formula = size_of::<SpanInstance>() - size_of::<FunctionCache>()
        + 3 * size_of::<ExecutionFailure>() + 2 * size_of::<CacheFailure>()
        + size_of::<crate::experimental::cache::DecodedInstruction>()
        + size_of::<Control>() + size_of::<ScalarReader<'static>>() + scalar_component;
    println!("control_accounting failure={} unit_result={} value_result={} bool_result={} i32_result={} transfer={} align={} scalar_component={} overflow={} frozen_formula={} minimum_with_new_transfers={}",
        size_of::<ExecutionFailure>(), size_of::<Result<(), ExecutionFailure>>(),
        size_of::<Result<Value, ExecutionFailure>>(), size_of::<Result<bool, ExecutionFailure>>(),
        size_of::<Result<i32, ExecutionFailure>>(), transfer,
        align_of::<NewControlWorkTransfer>(), scalar_component,
        transfer - scalar_component, formula, formula - scalar_component + transfer);
    // Bind actual compiled signatures to original-owner state. No call executes
    // a helper, creates a frame/pin, instantiates a guest, or drives a platform.
    let _: fn(&mut SpanInstance) -> Result<i32, ExecutionFailure> = pop32::<FrozenMode>;
    let _: fn(&mut SpanInstance, Control) -> Result<(), ExecutionFailure> =
        close_control::<FrozenMode>;
    let _: fn(&mut SpanInstance, u32) -> Result<bool, ExecutionFailure> = branch::<FrozenMode>;
    assert_eq!(formula, 2912);
    assert_eq!(size_of::<ExecutionFailure>(), 392);
    assert_eq!(transfer, 1176);
    assert!(transfer > scalar_component);
}
