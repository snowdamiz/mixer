mod common;
use common::*;
use mixer_vm::{Instance, Limits, Module, Profile, Type, Value};
use std::{
    io::Write,
    process::{Command, Stdio},
};
struct Case {
    bytes: Vec<u8>,
    float_bits: u32,
    nan_allowed: bool,
    canonical: bool,
    label: String,
}
fn canonical_inputs(values: &[Value]) -> bool {
    values.iter().all(|v| match v {
        Value::F32(b) => !f32::from_bits(*b).is_nan() || b & 0x7fffffff == 0x7fc00000,
        Value::F64(b) => {
            !f64::from_bits(*b).is_nan() || b & 0x7fffffffffffffff == 0x7ff8000000000000
        }
        _ => true,
    })
}
fn case(op: u8, args: &[Value], output: Type) -> Case {
    let mut code = vec![];
    for v in args {
        code.extend(constant(*v));
    }
    code.push(op);
    let float_bits = match output {
        Type::F32 => {
            code.push(0xbc);
            32
        }
        Type::F64 => {
            code.push(0xbd);
            64
        }
        _ => 0,
    };
    code.push(0x0b);
    let output = if float_bits == 32 {
        Type::I32
    } else if float_bits == 64 {
        Type::I64
    } else {
        output
    };
    Case {
        bytes: single(code, Some(output)),
        float_bits,
        nan_allowed: float_bits != 0
            && !matches!(op, 0x8b | 0x8c | 0x98 | 0x99 | 0x9a | 0xa6 | 0xbe | 0xbf),
        canonical: canonical_inputs(args),
        label: format!("opcode0x{op:02x} {args:?}"),
    }
}
fn outcome(case: &Case) -> String {
    let limits = Limits {
        profile: Profile::NumericV2,
        ..Limits::default()
    };
    let mut i = Instance::new(
        Module::decode(&case.bytes, &limits).unwrap_or_else(|e| panic!("{}: {e}", case.label)),
        limits,
    )
    .unwrap();
    let value = match i.invoke("run", &[]) {
        Err(_) => return "trap".into(),
        Ok(Some(v)) => v,
        _ => panic!("expected value"),
    };
    let (bits, text) = match value {
        Value::I32(v) => (v as u32 as u64, v.to_string()),
        Value::I64(v) => (v as u64, v.to_string()),
        _ => panic!("fixture must reinterpret float"),
    };
    if case.nan_allowed {
        let (nan, quiet, canonical) = if case.float_bits == 32 {
            (
                bits & 0x7f800000 == 0x7f800000 && bits & 0x7fffff != 0,
                bits & 0x400000 != 0,
                bits & 0x7fffffff == 0x7fc00000,
            )
        } else {
            (
                bits & 0x7ff0000000000000 == 0x7ff0000000000000 && bits & 0xfffffffffffff != 0,
                bits & 0x8000000000000 != 0,
                bits & 0x7fffffffffffffff == 0x7ff8000000000000,
            )
        };
        if nan {
            assert!(
                quiet && (!case.canonical || canonical),
                "invalid owned NaN {}: 0x{bits:x}",
                case.label
            );
            return "nan".into();
        }
    }
    text
}
fn assert_node(cases: Vec<Case>) {
    let input = format!(
        "[{}]",
        cases
            .iter()
            .map(|c| format!(
                "{{\"hex\":\"{}\",\"width\":{},\"nan\":{},\"canonical\":{}}}",
                c.bytes
                    .iter()
                    .map(|b| format!("{b:02x}"))
                    .collect::<String>(),
                c.float_bits,
                c.nan_allowed,
                c.canonical
            ))
            .collect::<Vec<_>>()
            .join(",")
    );
    let script = r#"const fs=require('node:fs');for(const c of JSON.parse(fs.readFileSync(0,'utf8'))){const b=Buffer.from(c.hex,'hex');if(!WebAssembly.validate(b)){console.log('invalid');continue;}const i=new WebAssembly.Instance(new WebAssembly.Module(b));try{const v=i.exports.run();if(c.nan&&c.width===32){const b=v>>>0;if((b&0x7f800000)===0x7f800000&&(b&0x7fffff)!==0){console.log((b&0x400000)!==0&&(!c.canonical||(b&0x7fffffff)===0x7fc00000)?'nan':'badnan');continue;}}if(c.nan&&c.width===64){const b=BigInt.asUintN(64,v);if((b&0x7ff0000000000000n)===0x7ff0000000000000n&&(b&0xfffffffffffffn)!==0n){console.log((b&0x8000000000000n)!==0n&&(!c.canonical||(b&0x7fffffffffffffffn)===0x7ff8000000000000n)?'nan':'badnan');continue;}}console.log(String(v));}catch(e){if(e instanceof WebAssembly.RuntimeError)console.log('trap');else throw e;}}"#;
    let mut child = Command::new(std::env::var("MIXER_NODE").unwrap_or_else(|_| "node".into()))
        .args(["-e", script])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(input.as_bytes())
        .unwrap();
    let output = child.wait_with_output().unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let text = String::from_utf8(output.stdout).unwrap();
    let lines = text.lines().collect::<Vec<_>>();
    assert_eq!(lines.len(), cases.len());
    for (c, line) in cases.iter().zip(lines) {
        assert_eq!(outcome(c), line, "{}", c.label);
    }
    eprintln!("numeric-v2 differential cases matched: {}", cases.len());
}
fn values(ty: Type) -> Vec<Value> {
    let base = [
        0.0f64,
        -0.0,
        1.0,
        -1.0,
        0.5,
        -0.5,
        1.5,
        -1.5,
        2.5,
        -2.5,
        f64::INFINITY,
        f64::NEG_INFINITY,
        2147483647.0,
        2147483648.0,
        4294967296.0,
        9223372036854775808.0,
        18446744073709551616.0,
    ];
    if ty == Type::F32 {
        let mut v = base
            .iter()
            .map(|x| Value::F32((*x as f32).to_bits()))
            .collect::<Vec<_>>();
        v.extend(
            [
                1, 0x80000001, 0x007fffff, 0x00800000, 0x7f7fffff, 0xff7fffff, 0x7fc00000,
                0xffc00000, 0x7fc12345, 0x7f812345, 0xff812345,
            ]
            .map(Value::F32),
        );
        v
    } else {
        let mut v = base
            .iter()
            .map(|x| Value::F64(x.to_bits()))
            .collect::<Vec<_>>();
        v.extend(
            [
                1,
                0x8000000000000001,
                0x000fffffffffffff,
                0x0010000000000000,
                0x7fefffffffffffff,
                0xffefffffffffffff,
                0x7ff8000000000000,
                0xfff8000000000000,
                0x7ff8123456789abc,
                0x7ff0123456789abc,
                0xfff0123456789abc,
            ]
            .map(Value::F64),
        );
        v
    }
}
#[test]
#[ignore = "development Node oracle; run explicitly"]
fn every_float_arithmetic_comparison_rounding_and_bitwise_opcode() {
    let mut cases = vec![];
    for (input, compare, unary, binary) in [
        (Type::F32, 0x5bu8, 0x8bu8, 0x92u8),
        (Type::F64, 0x61, 0x99, 0xa0),
    ] {
        let values = values(input);
        for op in compare..compare + 6 {
            for a in &values {
                for b in &values {
                    cases.push(case(op, &[*a, *b], Type::I32));
                }
            }
        }
        for op in unary..unary + 7 {
            for a in &values {
                cases.push(case(op, &[*a], input));
            }
        }
        for op in binary..binary + 7 {
            for a in &values {
                for b in &values {
                    cases.push(case(op, &[*a, *b], input));
                }
            }
        }
        let mut seed = 0x9e3779b97f4a7c15u64;
        for _ in 0..256 {
            seed ^= seed << 13;
            seed ^= seed >> 7;
            seed ^= seed << 17;
            let a = if input == Type::F32 {
                Value::F32(seed as u32)
            } else {
                Value::F64(seed)
            };
            seed = seed.rotate_left(29) ^ 0xa123456789bcdef0;
            let b = if input == Type::F32 {
                Value::F32(seed as u32)
            } else {
                Value::F64(seed)
            };
            for op in unary..unary + 7 {
                cases.push(case(op, &[a], input));
            }
            for op in binary..binary + 7 {
                cases.push(case(op, &[a, b], input));
            }
        }
    }
    assert_node(cases);
}
#[test]
#[ignore = "development Node oracle; run explicitly"]
fn conversions_reinterpret_and_saturating_boundaries() {
    let mut cases = vec![];
    for input in [Type::F32, Type::F64] {
        let mut vals = values(input);
        for edge in [
            -9223372036854775808f64,
            -2147483648.0,
            -1.0,
            0.0,
            2147483648.0,
            4294967296.0,
            9223372036854775808.0,
            18446744073709551616.0,
        ] {
            if input == Type::F32 {
                for f in [
                    (edge as f32).next_down(),
                    edge as f32,
                    (edge as f32).next_up(),
                ] {
                    vals.push(Value::F32(f.to_bits()));
                }
            } else {
                for f in [
                    edge.next_down(),
                    edge,
                    edge.next_up(),
                    edge - 0.75,
                    edge + 0.75,
                ] {
                    vals.push(Value::F64(f.to_bits()));
                }
            }
        }
        for value in vals {
            let ops = if input == Type::F32 {
                [0xa8, 0xa9, 0xae, 0xaf]
            } else {
                [0xaa, 0xab, 0xb0, 0xb1]
            };
            for op in ops {
                cases.push(case(
                    op,
                    &[value],
                    if op < 0xae { Type::I32 } else { Type::I64 },
                ));
            }
            cases.push(case(
                if input == Type::F32 { 0xbb } else { 0xb6 },
                &[value],
                if input == Type::F32 {
                    Type::F64
                } else {
                    Type::F32
                },
            ));
            cases.push(case(
                if input == Type::F32 { 0xbc } else { 0xbd },
                &[value],
                if input == Type::F32 {
                    Type::I32
                } else {
                    Type::I64
                },
            ));
            for sub in if input == Type::F32 {
                [0u8, 1, 4, 5]
            } else {
                [2, 3, 6, 7]
            } {
                let mut code = constant(value);
                code.extend([0xfc, sub, 0x0b]);
                cases.push(Case {
                    bytes: single(code, Some(if sub < 4 { Type::I32 } else { Type::I64 })),
                    float_bits: 0,
                    nan_allowed: false,
                    canonical: false,
                    label: format!("sat{sub} {value:?}"),
                });
            }
        }
    }
    for v in [
        i64::MIN,
        i64::MAX,
        i32::MIN as i64,
        i32::MAX as i64,
        -1,
        0,
        1,
        16777217,
        9007199254740993,
    ] {
        for (input, ops) in [
            (Value::I32(v as i32), [0xb2, 0xb3, 0xb7, 0xb8]),
            (Value::I64(v), [0xb4, 0xb5, 0xb9, 0xba]),
        ] {
            for op in ops {
                cases.push(case(
                    op,
                    &[input],
                    if op < 0xb7 { Type::F32 } else { Type::F64 },
                ));
            }
            cases.push(case(
                if input.ty() == Type::I32 { 0xbe } else { 0xbf },
                &[input],
                if input.ty() == Type::I32 {
                    Type::F32
                } else {
                    Type::F64
                },
            ));
        }
    }
    assert_node(cases);
}

#[test]
#[ignore = "development Node oracle; run explicitly"]
fn float_memory_calls_and_global_ownership_preserve_bits() {
    let mut cases = vec![];
    for ty in [Type::F32, Type::F64] {
        for value in values(ty) {
            for address in [0, 1, 65528, 65529, 65532, 65533, 65535, 65536, -1] {
                let mut code = constant(Value::I32(address));
                code.extend(constant(value));
                code.extend([if ty == Type::F32 { 0x38 } else { 0x39 }, 0, 0]);
                code.extend(constant(Value::I32(address)));
                code.extend([
                    if ty == Type::F32 { 0x2a } else { 0x2b },
                    0,
                    0,
                    if ty == Type::F32 { 0xbc } else { 0xbd },
                    0x0b,
                ]);
                let mut spec = Spec::one(
                    vec![],
                    Some(if ty == Type::F32 {
                        Type::I32
                    } else {
                        Type::I64
                    }),
                    code,
                );
                spec.memory = Some((1, 1));
                cases.push(Case {
                    bytes: spec.bytes(),
                    float_bits: 0,
                    nan_allowed: false,
                    canonical: false,
                    label: format!("memory {value:?} at {address}"),
                });
            }
            let mut code = constant(value);
            code.extend([0x10, 1, if ty == Type::F32 { 0xbc } else { 0xbd }, 0x0b]);
            let mut spec = Spec::one(
                vec![],
                Some(if ty == Type::F32 {
                    Type::I32
                } else {
                    Type::I64
                }),
                code,
            );
            spec.functions.push(Function::new(
                vec![ty],
                Some(ty),
                vec![0x20, 0, 0x24, 0, 0x23, 0, 0x0b],
            ));
            spec.globals = vec![(Value::zero(ty), true)];
            cases.push(Case {
                bytes: spec.bytes(),
                float_bits: 0,
                nan_allowed: false,
                canonical: false,
                label: format!("call/global {value:?}"),
            });
        }
    }
    assert_node(cases);
}
