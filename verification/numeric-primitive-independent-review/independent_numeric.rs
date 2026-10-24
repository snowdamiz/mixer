#![cfg(feature = "experimental-span-execution")]
mod common;
use common::Spec;
use mixer_vm::experimental::{cache::*, execution::*, validate_spans, ValidationBudget};
use mixer_vm::{Cancellation, Limits, Profile, Type, Value};
#[path = "common/allocation_observer.rs"]
mod allocation_observer;
use allocation_observer::{begin, Background, Observed, Ownership, CALLS, REALLOCATIONS};
use std::sync::atomic::Ordering::SeqCst;

#[global_allocator]
static ALLOCATOR: Observed = Observed;

fn build(bytes: &[u8], work: u64, cancellation: Cancellation) -> SpanInstance {
    let limits = Limits {
        profile: Profile::TableMemoryV3,
        call_depth: 4,
        operand_stack: 8,
        fuel: 100,
        ..Limits::default()
    };
    let proof = validate_spans(bytes, limits, ValidationBudget::default(), &cancellation).unwrap();
    let cache = FunctionCache::new(proof, CacheBudget::default(), &cancellation).unwrap();
    SpanInstance::new(cache, ExecutionBudget {
        live_values: 16, live_controls: 4, work_credits: work, ..ExecutionBudget::default()
    }, cancellation).unwrap()
}
fn clean(span: &SpanInstance) {
    let u = span.usage();
    assert_eq!((u.frames, u.live_values, u.live_controls, u.active_pins), (0, 0, 0, 0));
    assert_eq!((span.cache_usage().active_pins, span.cache_usage().pinned_bytes), (0, 0));
}

#[test]
fn independent_numeric_values_traps_work_and_warm_allocation_contract() {
    let background = Background::new();
    let _ownership = Ownership::new();
    background.check_observer();
    // Explicit values are independent of the production helpers and of the producer's traces.
    let cases: Vec<(&str, Vec<Value>, Type, Vec<u8>, Result<Option<Value>, &str>)> = vec![
        ("integer-add", vec![Value::I32(i32::MAX), Value::I32(1)], Type::I32, vec![0x6a], Ok(Some(Value::I32(i32::MIN)))),
        ("integer-rotate", vec![Value::I64(1), Value::I64(63)], Type::I64, vec![0x89], Ok(Some(Value::I64(i64::MIN)))),
        ("float-zero-min", vec![Value::F64(0), Value::F64(0x8000000000000000)], Type::F64, vec![0xa4], Ok(Some(Value::F64(0x8000000000000000)))),
        ("float-snan", vec![Value::F32(0x7f800042), Value::F32(0)], Type::F32, vec![0x92], Ok(Some(Value::F32(0x7fc00000)))),
        ("saturating-positive-infinity", vec![Value::F64(f64::INFINITY.to_bits())], Type::I64, vec![0xfc, 7], Ok(Some(Value::I64(-1)))),
        ("saturating-negative-nan", vec![Value::F32(0xff800042)], Type::I32, vec![0xfc, 0], Ok(Some(Value::I32(0)))),
        ("integer-zero-divisor", vec![Value::I32(23), Value::I32(0)], Type::I32, vec![0x6d], Err("integer_divide_by_zero")),
        ("integer-overflow", vec![Value::I64(i64::MIN), Value::I64(-1)], Type::I64, vec![0x7f], Err("integer_overflow")),
        ("conversion-nan", vec![Value::F32(0x7fc00042)], Type::I32, vec![0xa8], Err("invalid_conversion_to_integer")),
        ("conversion-infinity", vec![Value::F64(f64::INFINITY.to_bits())], Type::I64, vec![0xb0], Err("integer_overflow")),
    ];
    for (label, args, output, operation, expected) in cases {
        let mut code = Vec::new();
        for i in 0..args.len() { code.extend([0x20, i as u8]); }
        code.extend(&operation);
        code.push(0x0b);
        let bytes = Spec::one(args.iter().map(|v| v.ty()).collect(), Some(output), code).bytes();
        let numeric_offset = bytes.len() - operation.len() - 1;
        let cancellation = Cancellation::default();
        let mut span = build(&bytes, 1_000_000, cancellation.clone());
        let interval = begin(0, 0, &cancellation);
        let actual = span.invoke("run", &args);
        interval.finish();
        assert_eq!(REALLOCATIONS.load(SeqCst), 0, "{label}");
        match expected {
            Ok(value) => assert_eq!(actual, Ok(value), "{label}"),
            Err(code) => {
                let error = actual.unwrap_err();
                assert_eq!((error.kind, error.code, error.function, error.offset),
                    (ExecutionFailureKind::GuestTrap, code, Some(0), numeric_offset), "{label}");
                assert_eq!(error.usage, span.usage(), "{label}");
                assert_eq!(error.usage.instructions, (args.len() + 1) as u64, "{label}");
                assert_eq!(error.usage.fuel_used, (args.len() + 1) as u64, "{label}");
                // One credit below the terminal numeric debit fails before primitive dispatch.
                let needed = span.usage().work_used;
                let mut bounded = build(&bytes, needed - 1, Cancellation::default());
                let boundary = bounded.invoke("run", &args).unwrap_err();
                assert_eq!((boundary.kind, boundary.code, boundary.offset, boundary.attempted, boundary.limit),
                    (ExecutionFailureKind::WorkExhausted, "execution_work", numeric_offset, needed, needed - 1), "{label}");
                assert_eq!(bounded.invoke("run", &args), Err(boundary), "{label}");
                clean(&bounded);
                let mut exact = build(&bytes, needed, Cancellation::default());
                assert_eq!(exact.invoke("run", &args).unwrap_err().code, code, "{label}");
                clean(&exact);
            }
        }
        clean(&span);
        let before = span.usage();
        let interval = begin(1, 0, &cancellation);
        let repeated = span.invoke("run", &args);
        interval.finish();
        assert_eq!((CALLS.load(SeqCst), REALLOCATIONS.load(SeqCst)), (0, 0), "{label}");
        assert_eq!(repeated, actual, "{label}");
        if actual.is_err() { assert_eq!(before, span.usage(), "{label}"); }
        clean(&span);
        println!("independent_numeric {label} result={actual:?} work={} numeric_offset={numeric_offset} warm_allocations=0", before.work_used);
    }
}
