#![cfg(feature = "experimental-span-execution")]
mod common;
use common::*;
use mixer_vm::experimental::{cache::*, execution::*, validate_spans, ValidationBudget};
use mixer_vm::{Cancellation, Limits, Profile, Type, Value};
#[path = "common/allocation_observer.rs"]
mod allocation_observer;
use allocation_observer::{begin, Observed, Ownership, CALLS, PEAK, REALLOCATIONS};
use std::sync::atomic::Ordering::SeqCst;

#[global_allocator]
static ALLOCATOR: Observed = Observed;

fn limits(fuel: u64) -> Limits {
    Limits {
        profile: Profile::TableMemoryV3,
        operand_stack: 4,
        call_depth: 4,
        fuel,
        ..Limits::default()
    }
}
fn budget(work: u64) -> ExecutionBudget {
    ExecutionBudget {
        live_values: 8,
        live_controls: 4,
        work_credits: work,
        ..ExecutionBudget::default()
    }
}
fn cache(bytes: &[u8], fuel: u64) -> FunctionCache {
    let cancellation = Cancellation::default();
    let proof = validate_spans(
        bytes,
        limits(fuel),
        ValidationBudget::default(),
        &cancellation,
    )
    .unwrap();
    FunctionCache::new(proof, CacheBudget::default(), &cancellation).unwrap()
}
fn module(args: &[Value], output: Type, opcode: u8, saturating: bool) -> Vec<u8> {
    let mut code = Vec::new();
    for arg in args {
        code.extend(constant(*arg));
    }
    if saturating {
        code.push(0xfc);
    }
    code.extend([opcode, 0x0b]);
    Spec::one(vec![], Some(output), code).bytes()
}
fn clean(span: &SpanInstance) {
    let usage = span.usage();
    assert_eq!(
        (
            usage.frames,
            usage.live_values,
            usage.live_controls,
            usage.active_pins
        ),
        (0, 0, 0, 0)
    );
    assert_eq!(span.cache_usage().active_pins, 0);
}
fn shape(opcode: u8) -> (Type, usize, Type) {
    use Type::*;
    match opcode {
        0x45 => (I32, 1, I32),
        0x46..=0x4f => (I32, 2, I32),
        0x50 => (I64, 1, I32),
        0x51..=0x5a => (I64, 2, I32),
        0x5b..=0x60 => (F32, 2, I32),
        0x61..=0x66 => (F64, 2, I32),
        0x67..=0x69 | 0xc0..=0xc1 => (I32, 1, I32),
        0x6a..=0x78 => (I32, 2, I32),
        0x79..=0x7b | 0xc2..=0xc4 => (I64, 1, I64),
        0x7c..=0x8a => (I64, 2, I64),
        0x8b..=0x91 => (F32, 1, F32),
        0x92..=0x98 => (F32, 2, F32),
        0x99..=0x9f => (F64, 1, F64),
        0xa0..=0xa6 => (F64, 2, F64),
        0xa7 => (I64, 1, I32),
        0xa8..=0xa9 | 0xbc => (F32, 1, I32),
        0xaa..=0xab => (F64, 1, I32),
        0xac..=0xad => (I32, 1, I64),
        0xae..=0xaf => (F32, 1, I64),
        0xb0..=0xb1 | 0xbd => (F64, 1, I64),
        0xb2..=0xb3 | 0xbe => (I32, 1, F32),
        0xb4..=0xb5 => (I64, 1, F32),
        0xb6 => (F64, 1, F32),
        0xb7..=0xb8 => (I32, 1, F64),
        0xb9..=0xba | 0xbf => (I64, 1, F64),
        0xbb => (F32, 1, F64),
        _ => unreachable!(),
    }
}
fn trace(label: &str, bytes: &[u8], fuel: u64, work: u64, cancel: bool) -> ExecutionUsage {
    let cancellation = Cancellation::default();
    let proof = cache(bytes, fuel);
    let interval = begin(0, 0, &cancellation);
    let built = SpanInstance::new(proof, budget(work), cancellation.clone());
    let baseline = interval.finish();
    let construction = (
        CALLS.load(SeqCst),
        REALLOCATIONS.load(SeqCst),
        PEAK.load(SeqCst) - baseline,
    );
    let mut span = match built {
        Ok(span) => span,
        Err(error) => {
            println!("numeric_trace {label} fuel={fuel} work={work} cancelled={cancel} constructor={error:?} alloc={construction:?}");
            return error.usage;
        }
    };
    let initial = span.usage();
    if cancel {
        cancellation.cancel();
    }
    let interval = begin(0, 0, &cancellation);
    let first = span.invoke("run", &[]);
    let baseline = interval.finish();
    let cold = (
        CALLS.load(SeqCst),
        REALLOCATIONS.load(SeqCst),
        PEAK.load(SeqCst) - baseline,
    );
    assert_eq!(REALLOCATIONS.load(SeqCst), 0);
    clean(&span);
    let first_usage = span.usage();
    let first_cache = span.cache_usage();
    let interval = begin(1, 0, &cancellation);
    let second = span.invoke("run", &[]);
    interval.finish();
    let warm = (CALLS.load(SeqCst), REALLOCATIONS.load(SeqCst));
    assert_eq!(warm, (0, 0));
    clean(&span);
    if first.is_err() {
        assert_eq!(first, second);
        assert_eq!(span.usage(), first_usage);
    }
    println!("numeric_trace {label} fuel={fuel} work={work} cancelled={cancel} initial={initial:?} first={first:?} first_usage={first_usage:?} first_cache={first_cache:?} second={second:?} second_usage={:?} second_cache={:?} alloc={construction:?}/{cold:?}/{warm:?}", span.usage(), span.cache_usage());
    first_usage
}

#[test]
fn shared_numeric_public_parity_trace() {
    let _ownership = Ownership::new();
    let mut count = 0;
    for opcode in 0x45..=0xc4 {
        let (input, arity, output) = shape(opcode);
        let args = (0..arity)
            .map(|index| match input {
                Type::I32 => Value::I32(if index == 0 { 23 } else { 3 }),
                Type::I64 => Value::I64(if index == 0 { -57 } else { 3 }),
                Type::F32 => Value::F32((if index == 0 { 6.25f32 } else { 2.0 }).to_bits()),
                Type::F64 => Value::F64((if index == 0 { -6.25f64 } else { 2.0 }).to_bits()),
            })
            .collect::<Vec<_>>();
        trace(
            &format!("op{opcode:02x}"),
            &module(&args, output, opcode, false),
            100,
            1_000_000,
            false,
        );
        count += 1;
    }
    for opcode in 0..8 {
        for bits in [
            0u64,
            0x8000000000000000,
            0x7ff0000000000000,
            0xfff0000000000000,
            0x7ff0000000000042,
            0x7ff8000000000042,
            (-1.75f64).to_bits(),
            1.0e40f64.to_bits(),
        ] {
            let arg = if opcode % 4 < 2 {
                Value::F32((f64::from_bits(bits) as f32).to_bits())
            } else {
                Value::F64(bits)
            };
            let output = if opcode < 4 { Type::I32 } else { Type::I64 };
            trace(
                &format!("sat{opcode}-{bits:016x}"),
                &module(&[arg], output, opcode, true),
                100,
                1_000_000,
                false,
            );
            count += 1;
        }
    }
    for (label, args, output, opcode) in [
        (
            "i32-divzero",
            vec![Value::I32(17), Value::I32(0)],
            Type::I32,
            0x6d,
        ),
        (
            "i32-overflow",
            vec![Value::I32(i32::MIN), Value::I32(-1)],
            Type::I32,
            0x6d,
        ),
        (
            "i64-divzero",
            vec![Value::I64(17), Value::I64(0)],
            Type::I64,
            0x80,
        ),
        (
            "i64-overflow",
            vec![Value::I64(i64::MIN), Value::I64(-1)],
            Type::I64,
            0x7f,
        ),
        (
            "f32-snan",
            vec![Value::F32(0x7f800042), Value::F32(0)],
            Type::F32,
            0x92,
        ),
        (
            "f64-snan",
            vec![Value::F64(0x7ff0000000000042), Value::F64(0)],
            Type::F64,
            0xa0,
        ),
        (
            "f32-negzero",
            vec![Value::F32(0x80000000), Value::F32(0)],
            Type::F32,
            0x96,
        ),
        (
            "f64-negzero",
            vec![Value::F64(0x8000000000000000), Value::F64(0)],
            Type::F64,
            0xa4,
        ),
        (
            "f32-conv-nan",
            vec![Value::F32(0x7fc00042)],
            Type::I32,
            0xa8,
        ),
        (
            "f64-conv-inf",
            vec![Value::F64(0x7ff0000000000000)],
            Type::I64,
            0xb0,
        ),
    ] {
        let bytes = module(&args, output, opcode, false);
        let usage = trace(label, &bytes, 100, 1_000_000, false);
        for work in 0..=usage.work_used + 1 {
            trace(label, &bytes, 100, work, false);
        }
        for fuel in 0..=5 {
            trace(label, &bytes, fuel, 1_000_000, false);
        }
        trace(label, &bytes, 100, 1_000_000, true);
        count += 1;
    }
    println!("numeric_cases scalar=128 saturating=64 corners=10 total={count}; all work boundaries through first terminal/success debit, fuel=0..5, pre-dispatch cancellation; actual public construction/cold/warm allocation intervals");
}
