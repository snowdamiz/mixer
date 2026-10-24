// Isolated metadata only; no guest/owner constructor or algorithm executes.
#[allow(dead_code)]
pub(crate) fn control_macro_layout_probe() {
    use std::mem::{align_of, offset_of, size_of};
    macro_rules! size {
        ($ty:ty) => {
            println!("control_macro_type {} {} {}", stringify!($ty),
                size_of::<$ty>(), align_of::<$ty>());
        };
    }
    macro_rules! fields {
        ($ty:ty; $($field:ident),+) => {$({
            println!("control_macro_offset {} {} {}", stringify!($ty),
                stringify!($field), offset_of!($ty, $field));
        })+};
    }
    size!(Frame);
    size!(Control);
    size!(SpanInstance);
    size!(borrowed::ExecutionParts<'static, borrowed::FrozenMode>);
    size!(borrowed::FrozenOperation<'static>);
    size!(ExecutionFailure);
    size!(Result<(), ExecutionFailure>);
    size!(Result<Value, ExecutionFailure>);
    size!(Result<i32, ExecutionFailure>);
    size!(Result<bool, ExecutionFailure>);
    size!(std::ops::ControlFlow<Result<std::convert::Infallible, ExecutionFailure>, ()>);
    size!(std::ops::ControlFlow<Result<std::convert::Infallible, ExecutionFailure>, Value>);
    size!(std::ops::ControlFlow<Result<std::convert::Infallible, ExecutionFailure>, i32>);
    size!(std::ops::ControlFlow<Result<std::convert::Infallible, ExecutionFailure>, bool>);
    size!(Result<std::convert::Infallible, ExecutionFailure>);
    size!(Value);
    size!(Option<Value>);
    size!(Option<usize>);
    size!(Option<&Frame>);
    size!(&mut SpanInstance);
    size!(Option<&mut Frame>);
    size!(Result<&Frame, ExecutionFailure>);
    size!(Result<&mut Frame, ExecutionFailure>);
    size!(Result<usize, ExecutionFailure>);
    size!(std::ops::ControlFlow<Result<std::convert::Infallible, ExecutionFailure>, &Frame>);
    size!(std::ops::ControlFlow<Result<std::convert::Infallible, ExecutionFailure>, &mut Frame>);
    size!(std::ops::ControlFlow<Result<std::convert::Infallible, ExecutionFailure>, usize>);
    fields!(Frame; function, pc, base, operands, controls, result, pin);
    fields!(Control; kind, start, end, height, result);
    fields!(SpanInstance; cache, budget, cancellation, usage, failure, memory, table,
        globals, values, controls, frames, function, offset);
    fields!(borrowed::ExecutionParts<'static, borrowed::FrozenMode>;
        cache, memory, table, globals, values, controls, frames);
    fields!(borrowed::FrozenOperation<'static>;
        budget, cancellation, usage, failure, function, offset);
    let reservation = size_of::<SpanInstance>() - size_of::<FunctionCache>()
        + 3 * size_of::<ExecutionFailure>() + 2 * size_of::<CacheFailure>()
        + size_of::<crate::experimental::cache::DecodedInstruction>()
        + size_of::<Control>() + size_of::<ScalarReader<'static>>() + 512;
    println!("control_macro_reservation {}", reservation);
    assert_eq!(reservation, 2912);
}

#[test]
fn control_macro_layout_only() {
    control_macro_layout_probe();
}
