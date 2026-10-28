#![cfg(feature = "experimental-span-execution")]
#![allow(clippy::result_large_err)]
mod common;
use common::*;
use mixer_vm::experimental::{cache::*, execution::*, validate_spans, ValidationBudget};
use mixer_vm::{Cancellation, Instance, Limits, Module, Profile, Type, Value};
#[path = "common/allocation_observer.rs"]
#[allow(dead_code)] // Other observer facilities belong to separate allocation test binaries.
mod allocation_observer;

#[global_allocator]
static ALLOCATOR: allocation_observer::Observed = allocation_observer::Observed;

fn cache(bytes: &[u8], limits: Limits, budget: CacheBudget) -> FunctionCache {
    let cancel = Cancellation::default();
    FunctionCache::new(
        validate_spans(bytes, limits, ValidationBudget::default(), &cancel).unwrap(),
        budget,
        &cancel,
    )
    .unwrap()
}
fn owned(bytes: &[u8], limits: Limits) -> SpanInstance {
    SpanInstance::new(
        cache(bytes, limits, CacheBudget::default()),
        ExecutionBudget::default(),
        Cancellation::default(),
    )
    .unwrap()
}
fn limits() -> Limits {
    Limits {
        profile: Profile::TableMemoryV3,
        ..Limits::default()
    }
}
fn clean(instance: &SpanInstance) {
    let u = instance.usage();
    assert_eq!(
        (u.frames, u.live_values, u.live_controls, u.active_pins),
        (0, 0, 0, 0)
    );
    assert_eq!(
        (
            instance.cache_usage().active_pins,
            instance.cache_usage().pinned_bytes
        ),
        (0, 0)
    );
}
fn parity(spec: &Spec, args: &[Value]) -> SpanInstance {
    let bytes = spec.bytes();
    let l = limits();
    let mut eager = Instance::new(Module::decode(&bytes, &l).unwrap(), l.clone()).unwrap();
    let mut span = owned(&bytes, l);
    match (eager.invoke("run", args), span.invoke("run", args)) {
        (Ok(a), Ok(b)) => assert_eq!(a, b),
        (Err(a), Err(b)) => {
            assert_eq!(
                (a.code, a.function, a.offset),
                (b.code, b.function, b.offset)
            );
            assert_eq!(b.kind, ExecutionFailureKind::GuestTrap);
        }
        (a, b) => panic!("parity mismatch: {a:?} {b:?}"),
    }
    assert_eq!(eager.memory(), span.memory());
    clean(&span);
    span
}
#[test]
fn rejected_pre_pinned_cache_reports_no_live_owner_resources() {
    let bytes = Spec::one(vec![], Some(Type::I32), vec![0x41, 7, 0x0b]).bytes();
    let cancellation = Cancellation::default();
    let mut cache = cache(&bytes, limits(), CacheBudget::default());
    // The opaque token outlives the consumed cache but owns no cache allocation.
    let _stale_pin = cache.pin(0, &cancellation).unwrap();
    let error = SpanInstance::new(cache, ExecutionBudget::default(), cancellation)
        .err()
        .unwrap();
    assert_eq!(error.kind, ExecutionFailureKind::Invariant);
    assert_eq!(error.code, "preexisting_cache_pins");
    assert_eq!(error.attempted, 1);
    assert_eq!(error.usage.state_reserved, 0);
    assert_eq!(error.usage.memory_pages, 0);
    assert_eq!(error.usage.active_pins, 0);
}
#[test]
fn complete_scalar_numeric_and_saturating_dispatch_matches_frozen_semantics() {
    use Type::*;
    let mut cases = 0;
    for opcode in 0x45..=0xc4 {
        let (input, count, output) = match opcode {
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
        };
        let mut code = vec![];
        for index in 0..count {
            let value = match input {
                I32 => Value::I32(if index == 0 { 7 } else { 2 }),
                I64 => Value::I64(if index == 0 { 7 } else { 2 }),
                F32 => Value::F32((if index == 0 { 3.5f32 } else { 2.0 }).to_bits()),
                F64 => Value::F64((if index == 0 { 3.5f64 } else { 2.0 }).to_bits()),
            };
            code.extend(constant(value));
        }
        code.extend([opcode, 0x0b]);
        parity(&Spec::one(vec![], Some(output), code), &[]);
        cases += 1;
    }
    for opcode in 0..8 {
        let input64 = opcode % 4 >= 2;
        let output = if opcode < 4 { I32 } else { I64 };
        for number in [
            f64::NAN,
            f64::INFINITY,
            f64::NEG_INFINITY,
            -0.0,
            -1.5,
            1.0e30,
        ] {
            let value = if input64 {
                Value::F64(number.to_bits())
            } else {
                Value::F32((number as f32).to_bits())
            };
            let mut code = constant(value);
            code.extend([0xfc, opcode, 0x0b]);
            parity(&Spec::one(vec![], Some(output), code), &[]);
            cases += 1;
        }
    }
    println!("numeric parity cases={cases}; all scalar 0x45..0xc4 and saturating 0..7 dispatched");
}
#[test]
fn numeric_nan_signed_zero_overflow_and_conversion_traps_preserve_source() {
    for (a, b, opcode, result) in [
        (Value::I32(1), Value::I32(0), 0x6d, Type::I32),
        (Value::I32(i32::MIN), Value::I32(-1), 0x6d, Type::I32),
        (Value::I64(i64::MIN), Value::I64(-1), 0x7f, Type::I64),
        (Value::F32(0x7fa00001), Value::F32(0), 0x92, Type::F32),
        (
            Value::F64(0x7ff0000000000001),
            Value::F64(0),
            0xa0,
            Type::F64,
        ),
        (Value::F32(0x80000000), Value::F32(0), 0x96, Type::F32),
        (
            Value::F64(0x8000000000000000),
            Value::F64(0),
            0xa5,
            Type::F64,
        ),
    ] {
        let mut code = constant(a);
        code.extend(constant(b));
        code.extend([opcode, 0x0b]);
        parity(&Spec::one(vec![], Some(result), code), &[]);
    }
    for (value, opcode, result) in [
        (Value::F32(f32::NAN.to_bits()), 0xa8, Type::I32),
        (Value::F64(f64::INFINITY.to_bits()), 0xb0, Type::I64),
    ] {
        let mut code = constant(value);
        code.extend([opcode, 0x0b]);
        parity(&Spec::one(vec![], Some(result), code), &[]);
    }
}
#[test]
fn every_load_and_store_width_signedness_and_float_bits() {
    for store in 0x36..=0x3e {
        let (value, load, result) = match store {
            0x36 => (Value::I32(-1234567), 0x28, Type::I32),
            0x37 => (Value::I64(-1234567890123), 0x29, Type::I64),
            0x38 => (Value::F32(0xffa01234), 0x2a, Type::F32),
            0x39 => (Value::F64(0xfff1234567890123), 0x2b, Type::F64),
            0x3a => (Value::I32(-123), 0x2d, Type::I32),
            0x3b => (Value::I32(-1234), 0x2f, Type::I32),
            0x3c => (Value::I64(-123), 0x31, Type::I64),
            0x3d => (Value::I64(-1234), 0x33, Type::I64),
            _ => (Value::I64(-1234567), 0x35, Type::I64),
        };
        let mut code = constant(Value::I32(3));
        code.extend(constant(value));
        code.extend([store, 0, 2]);
        code.extend(constant(Value::I32(3)));
        code.extend([load, 0, 2, 0x0b]);
        let mut spec = Spec::one(vec![], Some(result), code);
        spec.memory = Some((1, 2));
        parity(&spec, &[]);
    }
    for load in 0x28..=0x35 {
        let result = match load {
            0x28 | 0x2c..=0x2f => Type::I32,
            0x2a => Type::F32,
            0x2b => Type::F64,
            _ => Type::I64,
        };
        let mut spec = Spec::one(vec![], Some(result), vec![0x41, 0, load, 0, 0, 0x0b]);
        spec.memory = Some((1, 1));
        spec.data = vec![(0, vec![0x80, 0xff, 0x00, 0x80, 0xff, 0xff, 0xff, 0xff])];
        parity(&spec, &[]);
    }
    let mut spec = Spec::one(vec![], Some(Type::I32), vec![0x41, 0x7f, 0x28, 2, 0, 0x0b]);
    spec.memory = Some((1, 1));
    parity(&spec, &[]);
}
#[test]
fn direct_recursive_calls_arguments_locals_if_and_return() {
    // factorial with a call to itself and independent parent operands.
    let mut spec = Spec::one(
        vec![Type::I32],
        Some(Type::I32),
        vec![
            0x20, 0, 0x45, 0x04, 0x7f, 0x41, 1, 0x05, 0x20, 0, 0x20, 0, 0x41, 1, 0x6b, 0x10, 0,
            0x6c, 0x0b, 0x0b,
        ],
    );
    spec.functions[0].locals = vec![Type::I64, Type::F32];
    let span = parity(&spec, &[Value::I32(8)]);
    assert_eq!(span.usage().peak_frames, 9);
    assert_eq!(span.cache_usage().decodes, 1);
    assert_eq!(span.cache_usage().hits, 8);
    let mut spec = Spec::one(
        vec![Type::I32],
        Some(Type::I32),
        vec![0x20, 0, 0x41, 3, 0x10, 1, 0x41, 1, 0x6a, 0x0b],
    );
    spec.functions.push(Function::new(
        vec![Type::I32, Type::I32],
        Some(Type::I32),
        vec![0x20, 0, 0x20, 1, 0x6c, 0x0f, 0x00, 0x0b],
    ));
    parity(&spec, &[Value::I32(4)]);
    let spec = Spec::one(
        vec![],
        Some(Type::I32),
        vec![0x41, 3, 0x21, 0, 0x20, 0, 0x41, 4, 0x6a, 0x22, 0, 0x0b],
    );
    let mut spec = spec;
    spec.functions[0].locals = vec![Type::I32];
    parity(&spec, &[]);
}
#[test]
fn loop_br_if_br_table_blocks_select_and_unreachable_cleanup() {
    let mut spec = Spec::one(
        vec![Type::I32],
        Some(Type::I32),
        vec![
            0x02, 0x40, 0x03, 0x40, 0x20, 0, 0x45, 0x0d, 1, 0x20, 0, 0x41, 1, 0x6b, 0x21, 0, 0x0c,
            0, 0x0b, 0x0b, 0x20, 0, 0x0b,
        ],
    );
    parity(&spec, &[Value::I32(20)]);
    spec = Spec::one(
        vec![Type::I32],
        Some(Type::I32),
        vec![
            0x02, 0x7f, 0x41, 17, 0x20, 0, 0x0e, 2, 0, 0, 0, 0x00, 0x0b, 0x0b,
        ],
    );
    for selector in [0, 1, 2, -1] {
        parity(&spec, &[Value::I32(selector)]);
    }
    let spec = Spec::one(
        vec![Type::I32],
        Some(Type::I64),
        vec![0x01, 0x42, 3, 0x42, 4, 0x20, 0, 0x1b, 0x0b],
    );
    parity(&spec, &[Value::I32(0)]);
    parity(&spec, &[Value::I32(1)]);
    parity(
        &Spec::one(vec![], None, vec![0x02, 0x40, 0x00, 0x0b, 0x0b]),
        &[],
    );
}
fn indirect() -> Spec {
    let mut spec = Spec::one(
        vec![Type::I32],
        Some(Type::I32),
        vec![0x20, 0, 0x11, 1, 0, 0x0b],
    );
    spec.functions
        .push(Function::new(vec![], Some(Type::I32), vec![0x41, 42, 0x0b]));
    spec.functions
        .push(Function::new(vec![], Some(Type::I32), vec![0x41, 9, 0x0b]));
    spec.table = Some((3, 3));
    spec.elements = vec![(1, vec![1, 1]), (2, vec![2]), (3, vec![])];
    spec.explicit_elements = true;
    spec
}
#[test]
fn table_order_structural_signature_null_bounds_and_mismatch() {
    for selector in [0, 1, 2, 3, -1] {
        parity(&indirect(), &[Value::I32(selector)]);
    }
    let mut spec = indirect();
    spec.functions[2].result = Some(Type::I64);
    spec.functions[2].code = vec![0x42, 9, 0x0b];
    parity(&spec, &[Value::I32(2)]);
    let mut spec = indirect();
    spec.elements = vec![(4, vec![])];
    let error = SpanInstance::new(
        cache(&spec.bytes(), limits(), CacheBudget::default()),
        ExecutionBudget::default(),
        Cancellation::default(),
    )
    .err()
    .unwrap();
    assert_eq!(error.code, "table_out_of_bounds");
    assert_eq!(error.usage.state_reserved, 0);
}
#[test]
fn ordered_data_and_bulk_memmove_fill_growth_and_size() {
    for copy in [false, true] {
        let mut code = vec![
            0x20,
            0,
            0x20,
            1,
            0x20,
            2,
            0xfc,
            if copy { 10 } else { 11 },
            0,
        ];
        if copy {
            code.push(0);
        }
        code.push(0x0b);
        let mut spec = Spec::one(vec![Type::I32; 3], None, code);
        spec.memory = Some((1, 2));
        spec.data = vec![(0, (0..32).collect()), (4, vec![80, 81]), (65536, vec![])];
        for (dst, src, len) in [
            (4, 0, 16000),
            (0, 4, 16000),
            (65536, 65536, 0),
            (-1, 0, 0),
            (65530, 0, 7),
        ] {
            parity(&spec, &[Value::I32(dst), Value::I32(src), Value::I32(len)]);
        }
    }
    let mut spec = Spec::one(
        vec![Type::I32],
        Some(Type::I32),
        vec![0x20, 0, 0x40, 0, 0x0b],
    );
    spec.memory = Some((1, 3));
    spec.data = vec![(0, vec![1, 2, 3])];
    for delta in [0, 1, 2, 3, -1] {
        parity(&spec, &[Value::I32(delta)]);
    }
    spec.functions[0] = Function::new(vec![], Some(Type::I32), vec![0x3f, 0, 0x0b]);
    parity(&spec, &[]);
    spec.data = vec![(65537, vec![])];
    let error = SpanInstance::new(
        cache(&spec.bytes(), limits(), CacheBudget::default()),
        ExecutionBudget::default(),
        Cancellation::default(),
    )
    .err()
    .unwrap();
    assert_eq!(error.code, "memory_out_of_bounds");
    assert_eq!(error.usage.state_reserved, 0);
}
#[test]
fn state_survives_success_and_prior_guest_writes_survive_trap() {
    let mut spec = Spec::one(
        vec![],
        Some(Type::I32),
        vec![0x23, 0, 0x41, 1, 0x6a, 0x24, 0, 0x23, 0, 0x0b],
    );
    spec.globals = vec![
        (Value::I32(0), true),
        (Value::F32(0x80000000), false),
        (Value::F64(0x7ff8000000000001), false),
        (Value::I64(-123), false),
    ];
    let bytes = spec.bytes();
    let mut span = owned(&bytes, limits());
    let mut eager = Instance::new(Module::decode(&bytes, &limits()).unwrap(), limits()).unwrap();
    for _ in 0..6 {
        assert_eq!(
            span.invoke("run", &[]).unwrap(),
            eager.invoke("run", &[]).unwrap()
        );
        clean(&span);
    }
    assert_eq!(span.usage().instructions, 36);
    spec = Spec::one(
        vec![],
        None,
        vec![0x41, 0, 0x41, 42, 0x36, 2, 0, 0x00, 0x0b],
    );
    spec.memory = Some((1, 1));
    let span = parity(&spec, &[]);
    assert_eq!(span.memory()[0], 42);
}
#[test]
fn exact_import_accounting_sticky_abort_and_host_budget() {
    let mut spec = Spec::one(vec![], None, vec![0x10, 0, 0x0b]);
    spec.imports = vec![("checkpoint".into(), vec![], None)];
    let mut span = owned(&spec.bytes(), limits());
    span.invoke("run", &[]).unwrap();
    assert_eq!(
        (
            span.usage().instructions,
            span.usage().fuel_used,
            span.usage().host_calls
        ),
        (2, 2, 1)
    );
    span.invoke("run", &[]).unwrap();
    assert_eq!((span.usage().instructions, span.usage().host_calls), (4, 2));
    clean(&span);
    let l = Limits {
        fuel: 1,
        ..limits()
    };
    let mut span = owned(&spec.bytes(), l);
    let error = span.invoke("run", &[]).unwrap_err();
    assert_eq!(error.kind, ExecutionFailureKind::FuelExhausted);
    assert_eq!(span.usage().host_calls, 1);
    assert_eq!(span.invoke("run", &[]), Err(error));
    clean(&span);
    let l = Limits {
        host_calls: 1,
        ..limits()
    };
    let mut span = owned(&spec.bytes(), l);
    span.invoke("run", &[]).unwrap();
    let error = span.invoke("run", &[]).unwrap_err();
    assert_eq!(error.kind, ExecutionFailureKind::HostCallLimit);
    clean(&span);
    spec.imports = vec![("abort".into(), vec![Type::I32], None)];
    spec.functions[0].code = vec![0x41, 7, 0x10, 0, 0x0b];
    parity(&spec, &[]);
    // Directly exported import pays its own single fuel charge.
    let mut bytes = b"\0asm\x01\0\0\0".to_vec();
    section(&mut bytes, 1, vec![1, 0x60, 0, 0]);
    section(
        &mut bytes,
        2,
        b"\x01\x05mixer\x0acheckpoint\x00\x00".to_vec(),
    );
    section(&mut bytes, 7, b"\x01\x03run\x00\x00".to_vec());
    let mut span = owned(&bytes, limits());
    span.invoke("run", &[]).unwrap();
    assert_eq!(
        (
            span.usage().fuel_used,
            span.usage().instructions,
            span.usage().host_calls
        ),
        (1, 1, 1)
    );
    clean(&span);
}
#[test]
fn fuel_work_values_controls_call_depth_and_pin_failures_cleanup() {
    let bytes = Spec::one(vec![], None, vec![0x10, 0, 0x0b]).bytes();
    for (l, b, c, kind) in [
        (
            Limits {
                call_depth: 3,
                ..limits()
            },
            ExecutionBudget::default(),
            CacheBudget::default(),
            ExecutionFailureKind::CallDepthExceeded,
        ),
        (
            limits(),
            ExecutionBudget {
                live_controls: 2,
                ..ExecutionBudget::default()
            },
            CacheBudget::default(),
            ExecutionFailureKind::ControlExhausted,
        ),
        (
            limits(),
            ExecutionBudget::default(),
            CacheBudget {
                max_pins: 2,
                ..CacheBudget::default()
            },
            ExecutionFailureKind::Cache,
        ),
        (
            Limits {
                fuel: 2,
                ..limits()
            },
            ExecutionBudget::default(),
            CacheBudget::default(),
            ExecutionFailureKind::FuelExhausted,
        ),
    ] {
        let mut span = SpanInstance::new(cache(&bytes, l, c), b, Cancellation::default()).unwrap();
        let error = span.invoke("run", &[]).unwrap_err();
        assert_eq!(error.kind, kind);
        clean(&span);
        let used = span.usage();
        assert_eq!(span.invoke("run", &[]), Err(error));
        assert_eq!(span.usage(), used);
    }
    let bytes = Spec::one(vec![], Some(Type::I32), vec![0x41, 1, 0x0b]).bytes();
    let mut span = SpanInstance::new(
        cache(&bytes, limits(), CacheBudget::default()),
        ExecutionBudget {
            live_values: 0,
            ..ExecutionBudget::default()
        },
        Cancellation::default(),
    )
    .unwrap();
    assert_eq!(
        span.invoke("run", &[]).unwrap_err().kind,
        ExecutionFailureKind::ValueExhausted
    );
    clean(&span);
    let mut probe = owned(&bytes, limits());
    probe.invoke("run", &[]).unwrap();
    let work = probe.usage().work_used;
    let mut span = SpanInstance::new(
        cache(&bytes, limits(), CacheBudget::default()),
        ExecutionBudget {
            work_credits: work,
            ..ExecutionBudget::default()
        },
        Cancellation::default(),
    )
    .unwrap();
    span.invoke("run", &[]).unwrap();
    assert_eq!(
        span.invoke("run", &[]).unwrap_err().kind,
        ExecutionFailureKind::WorkExhausted
    );
    clean(&span);
    let mut span = SpanInstance::new(
        cache(
            &bytes,
            limits(),
            CacheBudget {
                entry_bytes: 0,
                ..CacheBudget::default()
            },
        ),
        ExecutionBudget::default(),
        Cancellation::default(),
    )
    .unwrap();
    assert_eq!(
        span.invoke("run", &[])
            .unwrap_err()
            .cache_failure
            .unwrap()
            .kind,
        CacheFailureKind::EntryOversize
    );
    clean(&span);
}
#[test]
fn exact_state_reservations_growth_overlap_and_terminal_resource_denial() {
    let mut spec = Spec::one(vec![], Some(Type::I32), vec![0x41, 1, 0x40, 0, 0x0b]);
    spec.memory = Some((1, 2));
    let bytes = spec.bytes();
    let mut probe = owned(&bytes, limits());
    let initial = probe.usage().state_reserved;
    probe.invoke("run", &[]).unwrap();
    let peak = probe.usage().peak_state_reserved;
    assert_eq!(peak - initial, 2 * 65536);
    assert_eq!(probe.usage().state_reserved - initial, 65536);
    let make = |state_bytes| {
        SpanInstance::new(
            cache(&bytes, limits(), CacheBudget::default()),
            ExecutionBudget {
                state_bytes,
                ..ExecutionBudget::default()
            },
            Cancellation::default(),
        )
    };
    let mut exact = make(peak).unwrap();
    exact.invoke("run", &[]).unwrap();
    clean(&exact);
    let mut short = make(peak - 1).unwrap();
    let error = short.invoke("run", &[]).unwrap_err();
    assert_eq!(error.kind, ExecutionFailureKind::StateExhausted);
    assert_eq!(error.attempted, peak as u64);
    assert_eq!(short.memory().len(), 65536);
    clean(&short);
    let error = make(initial - 1).err().unwrap();
    assert_eq!(error.kind, ExecutionFailureKind::StateExhausted);
    assert_eq!(error.usage.state_reserved, 0);
    let mut empty = owned(&Spec::one(vec![], None, vec![0x0b]).bytes(), limits());
    empty.invoke("run", &[]).unwrap();
    clean(&empty);
    let bytes = Spec::one(vec![], None, vec![0x0b]).bytes();
    let mut zero = SpanInstance::new(
        cache(&bytes, limits(), CacheBudget::default()),
        ExecutionBudget {
            live_values: 0,
            live_controls: 1,
            ..ExecutionBudget::default()
        },
        Cancellation::default(),
    )
    .unwrap();
    zero.invoke("run", &[]).unwrap();
    clean(&zero);
}
#[test]
fn invocation_admission_is_terminal_and_cancellation_before_construct_or_dispatch() {
    let mut spec = Spec::one(vec![Type::I32], None, vec![0x0b]);
    spec.memory = Some((0, 0));
    spec.export_memory = true;
    let bytes = spec.bytes();
    for (name, args, kind) in [
        ("missing", vec![], ExecutionFailureKind::UnknownExport),
        ("memory", vec![], ExecutionFailureKind::InvalidArguments),
        (
            "run",
            vec![Value::I64(1)],
            ExecutionFailureKind::InvalidArguments,
        ),
    ] {
        let mut span = owned(&bytes, limits());
        let error = span.invoke(name, &args).unwrap_err();
        assert_eq!(error.kind, kind);
        assert_eq!(span.invoke("run", &[Value::I32(1)]), Err(error));
        clean(&span);
    }
    let token = Cancellation::default();
    token.cancel();
    let error = SpanInstance::new(
        cache(&bytes, limits(), CacheBudget::default()),
        ExecutionBudget::default(),
        token,
    )
    .err()
    .unwrap();
    assert_eq!(error.kind, ExecutionFailureKind::Cancelled);
    assert_eq!(error.usage.state_reserved, 0);
    let mut span = owned(&bytes, limits());
    span.cancellation().cancel();
    assert_eq!(
        span.invoke("run", &[Value::I32(1)]).unwrap_err().kind,
        ExecutionFailureKind::Cancelled
    );
    clean(&span);
}
#[test]
fn cancellation_during_guest_memory_growth_is_terminal_and_cleans_frames() {
    let _ownership = allocation_observer::Ownership::new();
    let mut spec = Spec::one(
        vec![],
        None,
        vec![0x41, 0, 0x41, 7, 0x36, 2, 0, 0x41, 1, 0x40, 0, 0x1a, 0x0b],
    );
    spec.memory = Some((1, 2));
    let bytes = spec.bytes();
    let token = Cancellation::default();
    // Warm decoding before invocation so its first allocation is memory.grow,
    // after the guest has already committed a store in an active pinned frame.
    let mut functions = cache(&bytes, limits(), CacheBudget::default());
    let pin = functions.pin(0, &token).unwrap();
    functions.release(pin).unwrap();
    let mut span = SpanInstance::new(functions, ExecutionBudget::default(), token.clone()).unwrap();
    let initial_state = span.usage().state_reserved;
    assert!(!token.is_cancelled());
    // The TLS observer cancels synchronously at the real growth allocation;
    // neither scheduler timing nor a competing finite loop budget selects it.
    let operation = allocation_observer::begin(0, 1, &token);
    let result = span.invoke("run", &[]);
    operation.finish();
    let error = result.unwrap_err();
    assert_eq!(error.kind, ExecutionFailureKind::Cancelled, "{error:?}");
    assert_eq!(error.code, "cancelled", "{error:?}");
    assert_eq!(error.cache_failure, None, "{error:?}");
    assert!(token.is_cancelled());
    assert_eq!(error.usage.instructions, 5, "{error:?}");
    assert_eq!(
        allocation_observer::CALLS.load(std::sync::atomic::Ordering::SeqCst),
        1
    );
    assert_eq!(&span.memory()[..4], &[7, 0, 0, 0]);
    assert_eq!(span.memory().len(), 65536);
    assert_eq!(error.usage.memory_pages, 1);
    assert_eq!(error.usage.state_reserved, initial_state);
    assert_eq!(span.invoke("run", &[]), Err(error));
    clean(&span);
}
#[test]
fn callee_cache_failure_preserves_callsite_and_cleans_caller_pin() {
    let mut spec = Spec::one(vec![], None, vec![0x10, 1, 0x0b]);
    let mut code = vec![0x01; 200];
    code.push(0x0b);
    spec.functions.push(Function::new(vec![], None, code));
    let bytes = spec.bytes();
    let token = Cancellation::default();
    let mut probe = cache(&bytes, limits(), CacheBudget::default());
    let pin = probe.pin(0, &token).unwrap();
    let entry = probe.usage().resident_bytes;
    probe.release(pin).unwrap();
    let mut span = SpanInstance::new(
        cache(
            &bytes,
            limits(),
            CacheBudget {
                entry_bytes: entry,
                ..CacheBudget::default()
            },
        ),
        ExecutionBudget::default(),
        token,
    )
    .unwrap();
    let error = span.invoke("run", &[]).unwrap_err();
    assert_eq!(error.kind, ExecutionFailureKind::Cache);
    assert_eq!(error.function, Some(0));
    assert!(error.offset > 8);
    assert_eq!(error.cache_failure.unwrap().function, Some(1));
    clean(&span);
}

#[test]
fn profiles_aggregate_arena_boundaries_and_narrowing_budgets() {
    let bytes = Spec::one(vec![], Some(Type::I32), vec![0x41, 7, 0x0b]).bytes();
    for profile in [
        Profile::IntegerV1,
        Profile::NumericV2,
        Profile::TableMemoryV3,
    ] {
        let mut span = owned(
            &bytes,
            Limits {
                profile,
                ..Limits::default()
            },
        );
        assert_eq!(span.invoke("run", &[]).unwrap(), Some(Value::I32(7)));
        clean(&span);
    }
    for budget in [
        ExecutionBudget {
            state_bytes: ExecutionBudget::default().state_bytes + 1,
            ..ExecutionBudget::default()
        },
        ExecutionBudget {
            live_values: ExecutionBudget::default().live_values + 1,
            ..ExecutionBudget::default()
        },
        ExecutionBudget {
            live_controls: ExecutionBudget::default().live_controls + 1,
            ..ExecutionBudget::default()
        },
        ExecutionBudget {
            work_credits: ExecutionBudget::default().work_credits + 1,
            ..ExecutionBudget::default()
        },
    ] {
        let error = SpanInstance::new(
            cache(&bytes, limits(), CacheBudget::default()),
            budget,
            Cancellation::default(),
        )
        .err()
        .unwrap();
        assert_eq!(error.kind, ExecutionFailureKind::InvalidBudget);
        assert_eq!(error.usage.state_reserved, 0);
    }
    let mut spec = Spec::one(
        vec![Type::I32],
        Some(Type::I32),
        vec![
            0x20, 0, 0x45, 0x04, 0x7f, 0x41, 1, 0x05, 0x20, 0, 0x20, 0, 0x41, 1, 0x6b, 0x10, 0,
            0x6c, 0x0b, 0x0b,
        ],
    );
    spec.functions[0].locals = vec![Type::I64];
    let bytes = spec.bytes();
    let mut probe = owned(&bytes, limits());
    probe.invoke("run", &[Value::I32(4)]).unwrap();
    let usage = probe.usage();
    assert!(usage.peak_live_values > usage.peak_frames);
    assert!(usage.peak_live_controls > usage.peak_frames);
    for (values, controls, expected) in [
        (usage.peak_live_values, usage.peak_live_controls, None),
        (
            usage.peak_live_values - 1,
            usage.peak_live_controls,
            Some(ExecutionFailureKind::ValueExhausted),
        ),
        (
            usage.peak_live_values,
            usage.peak_live_controls - 1,
            Some(ExecutionFailureKind::ControlExhausted),
        ),
    ] {
        let mut span = SpanInstance::new(
            cache(&bytes, limits(), CacheBudget::default()),
            ExecutionBudget {
                live_values: values,
                live_controls: controls,
                ..ExecutionBudget::default()
            },
            Cancellation::default(),
        )
        .unwrap();
        let result = span.invoke("run", &[Value::I32(4)]);
        match expected {
            None => assert_eq!(result.unwrap(), Some(Value::I32(24))),
            Some(kind) => assert_eq!(result.unwrap_err().kind, kind),
        }
        clean(&span);
    }
}

#[test]
fn cache_callee_lifetime_work_exhaustion_releases_every_frame() {
    let mut spec = Spec::one(vec![], None, vec![0x10, 1, 0x0b]);
    spec.functions.push(Function::new(vec![], None, vec![0x0b]));
    let bytes = spec.bytes();
    let token = Cancellation::default();
    let mut probe = cache(&bytes, limits(), CacheBudget::default());
    let pin = probe.pin(0, &token).unwrap();
    let exact_work = probe.usage().work_used;
    probe.release(pin).unwrap();
    let mut span = SpanInstance::new(
        cache(
            &bytes,
            limits(),
            CacheBudget {
                work_credits: exact_work,
                ..CacheBudget::default()
            },
        ),
        ExecutionBudget::default(),
        token,
    )
    .unwrap();
    let error = span.invoke("run", &[]).unwrap_err();
    assert_eq!(
        error.cache_failure.unwrap().kind,
        CacheFailureKind::WorkExhausted
    );
    assert_eq!(span.cache_usage().work_used, exact_work);
    clean(&span);
}
