mod common;
use common::*;
use mixer_vm::{Instance, Limits, Module, Type, Value};
use std::{
    io::Write,
    process::{Command, Stdio},
};
struct Case {
    bytes: Vec<u8>,
    args: Vec<Value>,
    label: String,
}
fn numeric_shape(op: u8) -> (Type, usize, Type) {
    use Type::*;
    match op {
        0x45 => (I32, 1, I32),
        0x46..=0x4f => (I32, 2, I32),
        0x50 => (I64, 1, I32),
        0x51..=0x5a => (I64, 2, I32),
        0x67..=0x69 | 0xc0 | 0xc1 => (I32, 1, I32),
        0x6a..=0x78 => (I32, 2, I32),
        0x79..=0x7b | 0xc2..=0xc4 => (I64, 1, I64),
        0x7c..=0x8a => (I64, 2, I64),
        0xa7 => (I64, 1, I32),
        0xac | 0xad => (I32, 1, I64),
        _ => panic!("test opcode"),
    }
}
fn expected(case: &Case) -> String {
    let mut i = Instance::new(
        Module::decode(&case.bytes, &Limits::default()).unwrap(),
        Limits::default(),
    )
    .unwrap();
    match i.invoke("run", &case.args) {
        Ok(Some(Value::I32(v))) => v.to_string(),
        Ok(Some(Value::I64(v))) => v.to_string(),
        Ok(None) => "void".into(),
        Err(_) => "trap".into(),
        Ok(Some(Value::F32(_) | Value::F64(_))) => unreachable!("integer oracle cases"),
    }
}
fn assert_node(cases: Vec<Case>) {
    let mut input = String::from("[");
    for (i, c) in cases.iter().enumerate() {
        if i > 0 {
            input.push(',');
        }
        let hex = c
            .bytes
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect::<String>();
        let args = c
            .args
            .iter()
            .map(|v| match v {
                Value::I32(x) => format!("[32,\"{x}\"]"),
                Value::I64(x) => format!("[64,\"{x}\"]"),
                Value::F32(_) | Value::F64(_) => unreachable!("integer oracle cases"),
            })
            .collect::<Vec<_>>()
            .join(",");
        input.push_str(&format!("{{\"hex\":\"{hex}\",\"args\":[{args}]}}"));
    }
    input.push(']');
    // Official Node's WebAssembly API is an external development oracle only.
    // No oracle code or package is linked into MixerVM or production artifacts.
    let script = r#"const fs=require('node:fs');for(const c of JSON.parse(fs.readFileSync(0,'utf8'))){const b=Buffer.from(c.hex,'hex');if(!WebAssembly.validate(b)){console.log('invalid');continue;}const i=new WebAssembly.Instance(new WebAssembly.Module(b));try{const v=i.exports.run(...c.args.map(([t,v])=>t===64?BigInt(v):Number(v)));console.log(v===undefined?'void':String(v));}catch(e){if(e instanceof WebAssembly.RuntimeError)console.log('trap');else throw e;}}"#;
    let node = std::env::var("MIXER_NODE").unwrap_or_else(|_| "node".into());
    let mut child = Command::new(node)
        .arg("-e")
        .arg(script)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Node is required for this explicitly enabled differential test");
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
    let lines = String::from_utf8(output.stdout).unwrap();
    let lines = lines.lines().collect::<Vec<_>>();
    assert_eq!(lines.len(), cases.len());
    for (c, line) in cases.iter().zip(lines) {
        assert_eq!(expected(c), line, "{}", c.label);
    }
    eprintln!("differential cases matched: {}", cases.len());
}
#[test]
#[ignore = "development oracle; run cargo test --test differential -- --ignored --nocapture with Node available"]
fn every_integer_opcode_matches_node() {
    let mut cases = vec![];
    let mut ops = (0x45..=0x5a).collect::<Vec<_>>();
    ops.extend(0x67..=0x8a);
    ops.extend([0xa7, 0xac, 0xad, 0xc0, 0xc1, 0xc2, 0xc3, 0xc4]);
    let edges = [
        i64::MIN,
        i64::MAX,
        i32::MIN as i64,
        i32::MAX as i64,
        -129,
        -65,
        -1,
        0,
        1,
        31,
        32,
        63,
        64,
        127,
        128,
        65536,
    ];
    for op in ops {
        let (ty, count, out) = numeric_shape(op);
        for a in edges {
            for b in if count == 2 { edges.to_vec() } else { vec![0] } {
                let mut code = vec![0x20, 0];
                if count == 2 {
                    code.extend([0x20, 1]);
                }
                code.extend([op, 0x0b]);
                let args = if count == 2 { vec![a, b] } else { vec![a] }
                    .into_iter()
                    .map(|v| {
                        if ty == Type::I32 {
                            Value::I32(v as i32)
                        } else {
                            Value::I64(v)
                        }
                    })
                    .collect();
                cases.push(Case {
                    bytes: Spec::one(vec![ty; count], Some(out), code).bytes(),
                    args,
                    label: format!("opcode0x{op:02x} a={a} b={b}"),
                });
            }
        }
    }
    assert_node(cases);
}
#[test]
#[ignore = "development oracle; run explicitly with Node"]
fn structured_control_and_memory_match_node() {
    let mut cases = vec![];
    for n in 0..100 {
        let mut s = Spec::one(
            vec![Type::I32],
            Some(Type::I32),
            vec![
                2, 0x40, 3, 0x40, 0x20, 0, 0x45, 0x0d, 1, 0x20, 1, 0x20, 0, 0x6a, 0x21, 1, 0x20, 0,
                0x41, 1, 0x6b, 0x21, 0, 0x0c, 0, 0x0b, 0x0b, 0x20, 1, 0x0b,
            ],
        );
        s.functions[0].locals = vec![Type::I32];
        cases.push(Case {
            bytes: s.bytes(),
            args: vec![Value::I32(n)],
            label: format!("loop n={n}"),
        });
    }
    for op in [
        0x28, 0x29, 0x2c, 0x2d, 0x2e, 0x2f, 0x30, 0x31, 0x32, 0x33, 0x34, 0x35,
    ] {
        for addr in [0, 1, 65528, 65529, 65535, 65536, -1] {
            let result = if op == 0x29 || op >= 0x30 {
                Type::I64
            } else {
                Type::I32
            };
            let mut s = Spec::one(vec![Type::I32], Some(result), vec![0x20, 0, op, 0, 0, 0x0b]);
            s.memory = Some((1, 2));
            s.data = vec![(0, vec![0xff, 0x80, 0x7f, 0x01, 0x23, 0x45, 0x67, 0x89])];
            cases.push(Case {
                bytes: s.bytes(),
                args: vec![Value::I32(addr)],
                label: format!("load{op:02x} addr={addr}"),
            });
        }
    }
    for store in [0x36, 0x37, 0x3a, 0x3b, 0x3c, 0x3d, 0x3e] {
        for addr in [0, 1, 65528, 65529, 65535, 65536, -1] {
            let val = if store == 0x37 || store >= 0x3c {
                Value::I64(-123456789)
            } else {
                Value::I32(-123456789)
            };
            let mut code = vec![0x20, 0];
            code.extend(constant(val));
            code.extend([store, 0, 0, 0x41, 0, 0x29, 0, 0, 0x0b]);
            let mut s = Spec::one(vec![Type::I32], Some(Type::I64), code);
            s.memory = Some((1, 2));
            cases.push(Case {
                bytes: s.bytes(),
                args: vec![Value::I32(addr)],
                label: format!("store{store:02x} addr={addr}"),
            });
        }
    }
    assert_node(cases);
}

#[test]
#[ignore = "development validation oracle; run explicitly with Node"]
fn accepted_mutations_are_also_valid_webassembly_in_node() {
    let originals = [
        single(vec![0x41, 42, 0x0b], Some(Type::I32)),
        single(vec![2, 0x40, 3, 0x40, 0x0c, 1, 0x0b, 0x0b, 0x0b], None),
    ];
    let mut candidates = vec![];
    for original in originals {
        for end in 0..original.len() {
            candidates.push(original[..end].to_vec());
        }
        for index in 0..original.len() {
            for bit in 0..8 {
                let mut bytes = original.clone();
                bytes[index] ^= 1 << bit;
                candidates.push(bytes);
            }
        }
    }
    let mut seed = 0x2468ace1u32;
    for n in 0..2000 {
        let mut code = vec![];
        for _ in 0..(n % 48) {
            seed ^= seed << 13;
            seed ^= seed >> 17;
            seed ^= seed << 5;
            code.push(seed as u8);
        }
        code.push(0x0b);
        candidates.push(single(code, None));
    }
    let input = format!(
        "[{}]",
        candidates
            .iter()
            .map(|bytes| format!(
                "\"{}\"",
                bytes.iter().map(|b| format!("{b:02x}")).collect::<String>()
            ))
            .collect::<Vec<_>>()
            .join(",")
    );
    let script="const fs=require('node:fs');for(const h of JSON.parse(fs.readFileSync(0,'utf8')))console.log(WebAssembly.validate(Buffer.from(h,'hex'))?'1':'0');";
    let mut child = Command::new(std::env::var("MIXER_NODE").unwrap_or_else(|_| "node".into()))
        .arg("-e")
        .arg(script)
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
    assert!(output.status.success());
    let text = String::from_utf8(output.stdout).unwrap();
    let lines = text.lines().collect::<Vec<_>>();
    assert_eq!(lines.len(), candidates.len());
    let mut accepted = 0;
    for (index, (bytes, node)) in candidates.iter().zip(lines).enumerate() {
        if Module::decode(bytes, &Limits::default()).is_ok() {
            accepted += 1;
            assert_eq!(
                node, "1",
                "owned validator accepted a Node-invalid module candidate{index}: {bytes:?}"
            );
        }
    }
    eprintln!(
        "validation differential candidates: {}; owned-profile accepted: {accepted}",
        candidates.len()
    );
}
