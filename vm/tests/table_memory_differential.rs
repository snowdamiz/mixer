mod common;
use common::*;
use mixer_vm::{Instance, Limits, Module, Profile, Type, Value};
use std::{
    io::Write,
    process::{Command, Stdio},
};
struct Case {
    bytes: Vec<u8>,
    calls: Vec<Vec<Value>>,
    spans: Vec<(usize, usize)>,
    label: String,
}
fn outcomes(c: &Case) -> Vec<String> {
    let l = Limits {
        profile: Profile::TableMemoryV3,
        ..Limits::default()
    };
    let module = match Module::decode(&c.bytes, &l) {
        Ok(m) => m,
        Err(_) => return vec!["invalid".into()],
    };
    let mut i = match Instance::new(module, l) {
        Ok(i) => i,
        Err(_) => return vec!["trap".into()],
    };
    c.calls
        .iter()
        .map(|args| {
            let mut output = match i.invoke("run", args) {
                Ok(Some(Value::I32(v))) => v.to_string(),
                Ok(Some(Value::I64(v))) => v.to_string(),
                Ok(None) => "void".into(),
                Err(_) => "trap".into(),
                _ => panic!("integer oracle result"),
            };
            for (start, end) in &c.spans {
                output.push(':');
                for b in &i.memory()[*start..*end] {
                    output.push_str(&format!("{b:02x}"));
                }
            }
            output
        })
        .collect()
}
fn oracle(cases: Vec<Case>) -> usize {
    let input = format!(
        "[{}]",
        cases
            .iter()
            .map(|c| format!(
                "{{\"hex\":\"{}\",\"calls\":[{}],\"spans\":[{}]}}",
                c.bytes
                    .iter()
                    .map(|b| format!("{b:02x}"))
                    .collect::<String>(),
                c.calls
                    .iter()
                    .map(|args| {
                        let values = args
                            .iter()
                            .map(|v| match v {
                                Value::I32(x) => format!("[32,\"{x}\"]"),
                                Value::I64(x) => format!("[64,\"{x}\"]"),
                                _ => panic!(),
                            })
                            .collect::<Vec<_>>()
                            .join(",");
                        format!("[{values}]")
                    })
                    .collect::<Vec<_>>()
                    .join(","),
                c.spans
                    .iter()
                    .map(|(a, b)| format!("[{a},{b}]"))
                    .collect::<Vec<_>>()
                    .join(",")
            ))
            .collect::<Vec<_>>()
            .join(",")
    );
    let script = r#"
const fs = require('node:fs');
for (const c of JSON.parse(fs.readFileSync(0, 'utf8'))) {
    const bytes = Buffer.from(c.hex, 'hex');
    if (!WebAssembly.validate(bytes)) {
        console.log('invalid');
        continue;
    }
    let instance;
    try {
        instance = new WebAssembly.Instance(new WebAssembly.Module(bytes));
    } catch (error) {
        if (!(error instanceof WebAssembly.RuntimeError)) throw error;
        console.log('trap');
        continue;
    }
    for (const args of c.calls) {
        let result;
        try {
            const value = instance.exports.run(...args.map(([type, value]) =>
                type === 64 ? BigInt(value) : Number(value)));
            result = value === undefined ? 'void' : String(value);
        } catch (error) {
            if (!(error instanceof WebAssembly.RuntimeError)) throw error;
            result = 'trap';
        }
        for (const [start, end] of c.spans) {
            result += ':' + Buffer.from(instance.exports.memory.buffer)
                .subarray(start, end).toString('hex');
        }
        console.log(result);
    }
}
"#;
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
    let mut lines = text.lines();
    let mut observations = 0;
    for c in &cases {
        for (step, result) in outcomes(c).iter().enumerate() {
            assert_eq!(
                Some(result.as_str()),
                lines.next(),
                "{} step {step}",
                c.label
            );
            observations += 1;
        }
    }
    assert!(
        lines.next().is_none(),
        "reference returned extra observations"
    );
    observations
}
#[test]
#[ignore = "development Node oracle; run explicitly"]
fn copy_fill_overlap_bounds_and_zero_length() {
    let mut cases = vec![];
    for copy in [true, false] {
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
        spec.memory = Some((1, 1));
        spec.export_memory = true;
        spec.data = vec![(0, (0..=255).collect())];
        let bytes = spec.bytes();
        for dst in [-1, 0, 1, 7, 16, 128, 65520, 65535, 65536, 65537] {
            for second in if copy {
                vec![-1, 0, 1, 7, 16, 128, 65520, 65535, 65536, 65537]
            } else {
                vec![-1, 0, 1, 255, 256, 0x1234]
            } {
                for len in [-1, 0, 1, 7, 16, 31, 32, 64, 65, 128, 65536] {
                    let mut spans = vec![(0, 256), (65520, 65536)];
                    if (0..65536).contains(&dst) {
                        spans.push((dst as usize, (dst as usize + 128).min(65536)));
                    }
                    cases.push(Case {
                        bytes: bytes.clone(),
                        calls: vec![vec![Value::I32(dst), Value::I32(second), Value::I32(len)]],
                        spans,
                        label: format!("copy={copy} dst={dst} second={second} len={len}"),
                    });
                }
            }
        }
    }
    eprintln!(
        "table-memory-v3 differential cases matched: {}",
        oracle(cases)
    );
}
#[test]
#[ignore = "development Node oracle; run explicitly"]
fn indirect_types_arguments_nulls_elements_and_instantiation() {
    let mut cases = vec![];
    for explicit in [false, true] {
        for offset in [0, 1, 2, 3, u32::MAX] {
            for table_min in [0, 1, 2, 3, 4] {
                for target in [1, 2, 3, 99] {
                    for selector in [-1, 0, 1, 2, 3, 4] {
                        let mut s = Spec::one(
                            vec![Type::I32],
                            Some(Type::I32),
                            vec![0x20, 0, 0x11, 1, 0, 0x0b],
                        );
                        s.functions.push(Function::new(
                            vec![],
                            Some(Type::I32),
                            vec![0x41, 42, 0x0b],
                        ));
                        s.functions.push(Function::new(
                            vec![],
                            Some(Type::I32),
                            vec![0x41, 7, 0x0b],
                        ));
                        s.functions.push(Function::new(
                            vec![],
                            Some(Type::I64),
                            vec![0x42, 9, 0x0b],
                        ));
                        s.table = Some((table_min, table_min));
                        s.elements = vec![(offset, vec![target])];
                        s.explicit_elements = explicit;
                        cases.push(Case{bytes:s.bytes(),calls:vec![vec![Value::I32(selector)]],spans:vec![],label:format!("explicit{explicit} offset{offset} table{table_min} target{target} selector{selector}")});
                    }
                }
            }
        }
    }
    for a in [i32::MIN, -1, 0, 1, i32::MAX] {
        for b in [i64::MIN, -1, 0, 1, i64::MAX] {
            let mut s = Spec::one(
                vec![Type::I32, Type::I64],
                Some(Type::I64),
                vec![0x20, 0, 0x20, 1, 0x41, 0, 0x11, 1, 0, 0x0b],
            );
            s.functions.push(Function::new(
                vec![Type::I32, Type::I64],
                Some(Type::I64),
                vec![0x20, 0, 0xac, 0x20, 1, 0x7c, 0x0b],
            ));
            s.table = Some((1, 1));
            s.elements = vec![(0, vec![1])];
            cases.push(Case {
                bytes: s.bytes(),
                calls: vec![vec![Value::I32(a), Value::I64(b)]],
                spans: vec![],
                label: format!("argument order {a} {b}"),
            });
        }
    }
    for selector in [0, 1, 2] {
        let mut s = Spec::one(
            vec![Type::I32],
            Some(Type::I32),
            vec![0x20, 0, 0x11, 1, 0, 0x0b],
        );
        s.functions
            .push(Function::new(vec![], Some(Type::I32), vec![0x41, 42, 0x0b]));
        s.functions
            .push(Function::new(vec![], Some(Type::I32), vec![0x41, 7, 0x0b]));
        s.table = Some((3, 3));
        s.elements = vec![(0, vec![1, 1]), (1, vec![2])];
        cases.push(Case {
            bytes: s.bytes(),
            calls: vec![vec![Value::I32(selector)]],
            spans: vec![],
            label: format!("overlapping segments selector{selector}"),
        });
    }
    for value in [
        Value::F32(0),
        Value::F32(0x8000_0000),
        Value::F32(1),
        Value::F32(0xff80_0001),
        Value::F64(0),
        Value::F64(0x8000_0000_0000_0000),
        Value::F64(1),
        Value::F64(0xfff0_0000_0000_0001),
    ] {
        let (integer_type, reinterpret) = match value {
            Value::F32(_) => (Type::I32, 0xbc),
            _ => (Type::I64, 0xbd),
        };
        let mut code = constant(value);
        code.extend([0x41, 0, 0x11, 1, 0, reinterpret, 0x0b]);
        let mut s = Spec::one(vec![], Some(integer_type), code);
        s.functions.push(Function::new(
            vec![value.ty()],
            Some(value.ty()),
            vec![0x20, 0, 0x0b],
        ));
        s.table = Some((1, 1));
        s.elements = vec![(0, vec![1])];
        cases.push(Case {
            bytes: s.bytes(),
            calls: vec![vec![]],
            spans: vec![],
            label: format!("float argument and return {value:?}"),
        });
    }
    eprintln!(
        "table-memory-v3 differential cases matched: {}",
        oracle(cases)
    );
}

#[test]
#[ignore = "development Node oracle; run explicitly"]
fn overlapping_copies_preserve_state_across_calls() {
    let mut spec = Spec::one(
        vec![Type::I32; 3],
        None,
        vec![0x20, 0, 0x20, 1, 0x20, 2, 0xfc, 10, 0, 0, 0x0b],
    );
    spec.memory = Some((1, 1));
    spec.export_memory = true;
    spec.data = vec![(0, (0..=255).collect())];
    let bytes = spec.bytes();

    let cases: Vec<_> = (1_u64..=24)
        .map(|seed| {
            let mut state = seed;
            let mut sample = |upper: i32| {
                state ^= state << 13;
                state ^= state >> 7;
                state ^= state << 17;
                (state % upper as u64) as i32
            };
            let calls = (0..40)
                .map(|step| {
                    let length = 2 + sample(79);
                    let distance = 1 + sample(length - 1);
                    let lower = sample(257 - length - distance);
                    let higher = lower + distance;
                    let (destination, source, count) = match step % 4 {
                        0 => (lower, higher, length),
                        1 => (higher, lower, length),
                        2 => (lower, lower, length),
                        _ => (lower, higher, 0),
                    };
                    [destination, source, count]
                        .into_iter()
                        .map(Value::I32)
                        .collect()
                })
                .collect();
            Case {
                bytes: bytes.clone(),
                calls,
                spans: vec![(0, 256)],
                label: format!("overlap sequence seed {seed}"),
            }
        })
        .collect();
    let sequence_count = cases.len();
    let observations = oracle(cases);
    eprintln!(
        "table-memory-v3 stateful sequences matched: {sequence_count}; observations: {observations}"
    );
}
