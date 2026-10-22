mod common;
use common::*;
use mixer_vm::{Instance, Limits, Module, Profile, Type, Value};
fn limits() -> Limits {
    Limits {
        profile: Profile::NumericV2,
        ..Limits::default()
    }
}
fn execute(code: Vec<u8>, result: Type) -> Result<Value, mixer_vm::Error> {
    let bytes = single(code, Some(result));
    let mut instance = Instance::new(Module::decode(&bytes, &limits())?, limits())?;
    Ok(instance.invoke("run", &[])?.unwrap())
}
fn unary(op: u8, value: Value, result: Type) -> Result<Value, mixer_vm::Error> {
    let mut c = constant(value);
    c.extend([op, 0x0b]);
    execute(c, result)
}
fn binary(op: u8, a: Value, b: Value, result: Type) -> Value {
    let mut c = constant(a);
    c.extend(constant(b));
    c.extend([op, 0x0b]);
    execute(c, result).unwrap()
}
#[test]
fn integer_profile_remains_closed_to_floats() {
    let bytes = single(
        [constant(Value::F32(1f32.to_bits())), vec![0x0b]].concat(),
        Some(Type::F32),
    );
    assert_eq!(
        Module::decode(&bytes, &Limits::default()).unwrap_err().code,
        "unsupported"
    );
    assert!(Module::decode(&bytes, &limits()).is_ok());
}
#[test]
fn constants_reinterpret_and_bitwise_preserve_nan_payloads() {
    for bits in [0, 0x80000000, 0x7fc12345, 0xff812345, 1, 0x7f800000] {
        assert_eq!(
            unary(0xbc, Value::F32(bits), Type::I32).unwrap(),
            Value::I32(bits as i32)
        );
        assert_eq!(
            unary(0xbe, Value::I32(bits as i32), Type::F32).unwrap(),
            Value::F32(bits)
        );
        assert_eq!(
            unary(0x8b, Value::F32(bits), Type::F32).unwrap(),
            Value::F32(bits & 0x7fffffff)
        );
        assert_eq!(
            unary(0x8c, Value::F32(bits), Type::F32).unwrap(),
            Value::F32(bits ^ 0x80000000)
        );
    }
    let bits = 0xfff0123456789abc;
    assert_eq!(
        unary(0xbd, Value::F64(bits), Type::I64).unwrap(),
        Value::I64(bits as i64)
    );
    assert_eq!(
        unary(0xbf, Value::I64(bits as i64), Type::F64).unwrap(),
        Value::F64(bits)
    );
}
#[test]
fn signed_zero_min_max_and_copysign() {
    assert_eq!(
        binary(0x96, Value::F32(0), Value::F32(0x80000000), Type::F32),
        Value::F32(0x80000000)
    );
    assert_eq!(
        binary(0x97, Value::F32(0x80000000), Value::F32(0), Type::F32),
        Value::F32(0)
    );
    assert_eq!(
        binary(0xa4, Value::F64(0), Value::F64(1 << 63), Type::F64),
        Value::F64(1 << 63)
    );
    assert_eq!(
        binary(0xa5, Value::F64(1 << 63), Value::F64(0), Type::F64),
        Value::F64(0)
    );
    assert_eq!(
        binary(
            0x98,
            Value::F32(0x7f812345),
            Value::F32(0x80000000),
            Type::F32
        ),
        Value::F32(0xff812345)
    );
}
#[test]
fn rounding_is_ties_even_and_retains_negative_zero() {
    for (x, want) in [
        (0.5f64, 0.0f64),
        (1.5, 2.0),
        (2.5, 2.0),
        (-0.5, -0.0),
        (-1.5, -2.0),
        (-2.5, -2.0),
    ] {
        assert_eq!(
            unary(0x90, Value::F32((x as f32).to_bits()), Type::F32).unwrap(),
            Value::F32((want as f32).to_bits())
        );
        assert_eq!(
            unary(0x9e, Value::F64(x.to_bits()), Type::F64).unwrap(),
            Value::F64(want.to_bits())
        );
    }
    assert_eq!(
        unary(0x91, Value::F32(0x80000000), Type::F32).unwrap(),
        Value::F32(0x80000000)
    );
}
#[test]
fn division_and_nan_comparison_follow_ieee() {
    assert_eq!(
        binary(0x95, Value::F32(1f32.to_bits()), Value::F32(0), Type::F32),
        Value::F32(f32::INFINITY.to_bits())
    );
    assert_eq!(
        binary(
            0x5b,
            Value::F32(f32::NAN.to_bits()),
            Value::F32(f32::NAN.to_bits()),
            Type::I32
        ),
        Value::I32(0)
    );
    assert_eq!(
        binary(
            0x5c,
            Value::F32(f32::NAN.to_bits()),
            Value::F32(0),
            Type::I32
        ),
        Value::I32(1)
    );
    let Value::F64(bits) = unary(0x9f, Value::F64((-1f64).to_bits()), Type::F64).unwrap() else {
        panic!()
    };
    assert!(f64::from_bits(bits).is_nan());
}
#[test]
fn float_to_integer_traps_are_distinct_and_boundaries_truncate() {
    assert_eq!(
        unary(0xaa, Value::F64(f64::NAN.to_bits()), Type::I32)
            .unwrap_err()
            .code,
        "invalid_conversion_to_integer"
    );
    for x in [f64::INFINITY, 2147483648.0, -2147483649.0] {
        assert_eq!(
            unary(0xaa, Value::F64(x.to_bits()), Type::I32)
                .unwrap_err()
                .code,
            "integer_overflow"
        );
    }
    assert_eq!(
        unary(0xaa, Value::F64((-2147483648.75f64).to_bits()), Type::I32).unwrap(),
        Value::I32(i32::MIN)
    );
    assert_eq!(
        unary(0xab, Value::F64((-0.999f64).to_bits()), Type::I32).unwrap(),
        Value::I32(0)
    );
    assert_eq!(
        unary(
            0xb1,
            Value::F64(18446744073709551616f64.to_bits()),
            Type::I64
        )
        .unwrap_err()
        .code,
        "integer_overflow"
    );
}
#[test]
fn saturating_conversions_clamp_and_meter_one_instruction() {
    for (sub, input, want) in [
        (0, Value::F32(f32::NAN.to_bits()), Value::I32(0)),
        (1, Value::F32(f32::INFINITY.to_bits()), Value::I32(-1)),
        (
            4,
            Value::F32(f32::NEG_INFINITY.to_bits()),
            Value::I64(i64::MIN),
        ),
        (7, Value::F64(f64::INFINITY.to_bits()), Value::I64(-1)),
    ] {
        let mut code = constant(input);
        code.extend([0xfc, sub, 0x0b]);
        assert_eq!(execute(code, want.ty()).unwrap(), want);
    }
    let bytes = single(vec![0x43, 0, 0, 0, 0, 0xfc, 8, 0x0b], Some(Type::I32));
    assert_eq!(
        Module::decode(&bytes, &limits()).unwrap_err().code,
        "unsupported"
    );
}
#[test]
fn float_memory_locals_globals_and_control_are_typed() {
    let mut spec = Spec::one(
        vec![],
        Some(Type::F64),
        vec![
            0x23, 0, 0x21, 0, 0x41, 3, 0x20, 0, 0x39, 0, 0, 0x41, 1, 4, 0x7c, 0x41, 3, 0x2b, 0, 0,
            5, 0x44, 0, 0, 0, 0, 0, 0, 0, 0, 0x0b, 0x0b,
        ],
    );
    spec.functions[0].locals = vec![Type::F64];
    spec.globals = vec![(Value::F64((-0f64).to_bits()), false)];
    spec.memory = Some((1, 1));
    let mut instance =
        Instance::new(Module::decode(&spec.bytes(), &limits()).unwrap(), limits()).unwrap();
    assert_eq!(
        instance.invoke("run", &[]).unwrap(),
        Some(Value::F64(1 << 63))
    );
    assert_eq!(&instance.memory()[3..11], &(1u64 << 63).to_le_bytes());
}
#[test]
fn numeric_profile_cannot_be_reinstantiated_as_integer() {
    let bytes = single(vec![0x0b], None);
    let module = Module::decode(&bytes, &limits()).unwrap();
    let error = match Instance::new(module, Limits::default()) {
        Ok(_) => panic!("profile change must fail"),
        Err(e) => e,
    };
    assert_eq!(error.code, "invalid_limits");
}
#[test]
fn malformed_float_immediates_and_type_mismatch_reject() {
    for code in [
        vec![0x43, 0, 0, 0],
        vec![0x44, 0, 0, 0, 0, 0, 0, 0],
        vec![0x41, 0, 0x91, 0x0b],
        vec![0x43, 0, 0, 0, 0, 0x41, 0, 0x92, 0x0b],
    ] {
        assert!(Module::decode(&single(code, Some(Type::F32)), &limits()).is_err());
    }
}

#[test]
fn prefix_metering_and_float_mutation_execution_are_bounded() {
    let bytes = single(vec![0x43, 0, 0, 0, 0, 0xfc, 0, 0x0b], Some(Type::I32));
    let mut instance = Instance::new(
        Module::decode(&bytes, &limits()).unwrap(),
        Limits {
            fuel: 3,
            ..limits()
        },
    )
    .unwrap();
    assert_eq!(instance.invoke("run", &[]).unwrap(), Some(Value::I32(0)));
    assert_eq!(instance.fuel_remaining, 0);
    let mut instance = Instance::new(
        Module::decode(&bytes, &limits()).unwrap(),
        Limits {
            fuel: 2,
            ..limits()
        },
    )
    .unwrap();
    assert_eq!(
        instance.invoke("run", &[]).unwrap_err().code,
        "fuel_exhausted"
    );
    for index in 0..bytes.len() {
        for bit in 0..8 {
            let mut mutated = bytes.clone();
            mutated[index] ^= 1 << bit;
            let l = Limits {
                fuel: 100,
                call_depth: 4,
                memory_pages: 2,
                ..limits()
            };
            assert!(
                std::panic::catch_unwind(|| {
                    if let Ok(m) = Module::decode(&mutated, &l) {
                        if let Ok(mut instance) = Instance::new(m, l) {
                            let _ = instance.invoke("run", &[]);
                        }
                    }
                })
                .is_ok(),
                "index={index} bit={bit}"
            );
        }
    }
}
