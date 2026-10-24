// Derived metadata only. Appended inside the archived execution module.
pub(crate) fn operations_owner_layout_probe() {
    use std::mem::{align_of, offset_of, size_of};
    macro_rules! row { ($t:ty) => { println!("value_owner|{}|{}|{}",stringify!($t),size_of::<$t>(),align_of::<$t>()); }; }
    macro_rules! fields { ($t:ty;$($f:ident),+) => {$(println!("value_owner_field|{}|{}|{}",stringify!($t),stringify!($f),offset_of!($t,$f));)+}; }
    row!(SwiftExecutionState); row!(SwiftReactorInstance); row!(SwiftFrame);
    row!(ExecutionOperationPhase<'static>); row!(SwiftExecutionOperation<'static>);
    row!(Control); row!(ExecutionParts<'static,SwiftMode>);
    row!(ExecutionParts<'static,FrozenMode>); row!(FrozenOperation<'static>);
    row!(crate::experimental::execution::SpanInstance);
    row!(crate::experimental::execution::Frame);
    fields!(SwiftExecutionState;memory,table,globals,values,controls,frames,buffers,execution_header);
    fields!(SwiftReactorInstance;control,cache,wasi,state,lifecycle);
    fields!(SwiftFrame;function,pc,base,operands,controls,result,pin);
    fields!(ExecutionOperationPhase<'static>;parts,operation,previous_bound);
    fields!(SwiftExecutionOperation<'static>;control,wasi,cursor);
    fields!(ExecutionParts<'static,SwiftMode>;cache,memory,table,globals,values,controls,frames);
    println!("value_bounds|header|{}",execution_header_bytes().unwrap());
    println!("value_bounds|construction|{}",construction_bytes().unwrap());
    println!("value_bounds|declared_operation|{}",phase_bytes("operation").unwrap());
}
