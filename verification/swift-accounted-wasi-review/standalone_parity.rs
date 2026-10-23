use mixer_vm::experimental_wasi::{WasiBudget, WasiContext, WasiFunction, WasiGrants};
use mixer_vm::{Cancellation, Type, Value};

fn main() {
    println!("context_size={} context_align={}", std::mem::size_of::<WasiContext>(), std::mem::align_of::<WasiContext>());
    for function in WasiFunction::ALL {
        for variant in 0..4 {
            let mut context = WasiContext::new(
                WasiGrants::default(),
                WasiBudget { one_transfer_bytes: 13, log_bytes: 17, ..WasiBudget::default() },
                Cancellation::default(),
            ).unwrap();
            let mut arguments: Vec<_> = function.parameters().iter().map(|ty| {
                let value = if variant == 1 { u32::MAX } else { 0 };
                match ty {
                    Type::I32 => Value::I32(value as i32),
                    Type::I64 => Value::I64(value as i64),
                    Type::F32 => Value::F32(value),
                    Type::F64 => Value::F64(value as u64),
                }
            }).collect();
            if variant == 2 { arguments.push(Value::I32(0)); }
            if variant == 3 && !arguments.is_empty() {
                arguments[0] = if function.parameters()[0] == Type::I32 { Value::I64(0) } else { Value::I32(0) };
            }
            let mut memory = [0xa5; 64];
            let outcome = context.dispatch(function, &arguments, &mut memory);
            println!("{function:?} variant={variant} outcome={outcome:?} usage={:?} stdout={:?} stderr={:?} memory={memory:?}", context.usage(), context.stdout(), context.stderr());
        }
    }
}
