use super::*;
use std::mem::{align_of, offset_of, size_of};

#[test]
fn frozen_executor_layout_prerequisite() {
    println!(
        "layout Frame {} {}",
        size_of::<Frame>(),
        align_of::<Frame>()
    );
    println!(
        "layout Control {} {}",
        size_of::<Control>(),
        align_of::<Control>()
    );
    println!(
        "layout SpanInstance {} {}",
        size_of::<SpanInstance>(),
        align_of::<SpanInstance>()
    );
    macro_rules! fields {
        ($t:ty; $($f:ident),+) => {$({
            println!("offset {} {} {}", stringify!($t), stringify!($f), offset_of!($t, $f));
        })+};
    }
    fields!(Frame; function, pc, base, operands, controls, result, pin);
    fields!(Control; kind, start, end, height, result);
    fields!(SpanInstance; cache, budget, cancellation, usage, failure, memory, table,
        globals, values, controls, frames, function, offset);
    fields!(ExecutionParts<'static, FrozenMode>; cache, memory, table, globals, values, controls, frames);
    fields!(FrozenOperation<'static>; budget, cancellation, usage, failure, function, offset);
    assert_eq!(
        size_of::<ExecutionParts<'static, FrozenMode>>(),
        7 * size_of::<usize>()
    );
    assert_eq!(
        size_of::<FrozenOperation<'static>>(),
        6 * size_of::<usize>()
    );
}
