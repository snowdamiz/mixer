#![cfg(feature = "experimental-span-execution")]
mod common;
use common::*;
use mixer_vm::experimental::{cache::*, execution::*, validate_spans, ValidationBudget};
use mixer_vm::{Cancellation, Instance, Limits, Module, Profile, Type, Value};
use std::io::Write;
use std::process::{Command, Stdio};
struct Case {
    spec: Spec,
    result: Option<Type>,
}
fn outcome(value: Result<Option<Value>, ()>) -> String {
    match value {
        Err(()) => "trap".into(),
        Ok(None) => "none".into(),
        Ok(Some(Value::I32(n))) => format!("i32:{n}"),
        Ok(Some(Value::I64(n))) => format!("i64:{n}"),
        Ok(Some(Value::F32(n))) => {
            if f32::from_bits(n).is_nan() {
                "nan32".into()
            } else {
                format!("f32:{n}")
            }
        }
        Ok(Some(Value::F64(n))) => {
            if f64::from_bits(n).is_nan() {
                "nan64".into()
            } else {
                format!("f64:{n}")
            }
        }
    }
}
#[test]
fn original_probes_match_development_node_values_traps_and_memory() {
    let mut cases = vec![];
    for (left, right, op, result) in [
        (Value::I32(i32::MAX), Value::I32(1), 0x6a, Type::I32),
        (Value::I32(i32::MIN), Value::I32(-1), 0x6d, Type::I32),
        (Value::I32(-1), Value::I32(33), 0x76, Type::I32),
        (Value::I64(i64::MAX), Value::I64(1), 0x7c, Type::I64),
        (Value::I64(i64::MIN), Value::I64(-1), 0x7f, Type::I64),
        (Value::I64(7), Value::I64(0), 0x80, Type::I64),
        (Value::F32(0x80000000), Value::F32(0), 0x96, Type::F32),
        (
            Value::F64(0x8000000000000000),
            Value::F64(0),
            0xa5,
            Type::F64,
        ),
        (Value::F32(0x7fa00001), Value::F32(0), 0x92, Type::F32),
        (
            Value::F64(0x7ff0000000000001),
            Value::F64(0),
            0xa0,
            Type::F64,
        ),
    ] {
        let mut code = constant(left);
        code.extend(constant(right));
        code.extend([op, 0x0b]);
        cases.push(Case {
            spec: Spec::one(vec![], Some(result), code),
            result: Some(result),
        });
    }
    for sub in 0..8 {
        for number in [
            f64::NAN,
            f64::INFINITY,
            f64::NEG_INFINITY,
            -1.5,
            0.0,
            1.0e30,
        ] {
            let value = if sub % 4 < 2 {
                Value::F32((number as f32).to_bits())
            } else {
                Value::F64(number.to_bits())
            };
            let result = if sub < 4 { Type::I32 } else { Type::I64 };
            let mut code = constant(value);
            code.extend([0xfc, sub, 0x0b]);
            cases.push(Case {
                spec: Spec::one(vec![], Some(result), code),
                result: Some(result),
            });
        }
    }
    for copy in [false, true] {
        for (dst, src, len) in [
            (3, 0, 12000),
            (0, 3, 12000),
            (65536, 65536, 0),
            (65535, 0, 2),
        ] {
            let mut code = constant(Value::I32(dst));
            code.extend(constant(Value::I32(src)));
            code.extend(constant(Value::I32(len)));
            code.extend([0xfc, if copy { 10 } else { 11 }, 0]);
            if copy {
                code.push(0);
            }
            code.push(0x0b);
            let mut spec = Spec::one(vec![], None, code);
            spec.memory = Some((1, 1));
            spec.export_memory = true;
            spec.data = vec![(0, (0..128).collect())];
            cases.push(Case { spec, result: None });
        }
    }
    for selector in [0, 1, 2] {
        let mut spec = Spec::one(
            vec![],
            Some(Type::I32),
            vec![0x41, selector, 0x11, 1, 0, 0x0b],
        );
        spec.functions
            .push(Function::new(vec![], Some(Type::I32), vec![0x41, 42, 0x0b]));
        spec.table = Some((2, 2));
        spec.elements = vec![(1, vec![1])];
        cases.push(Case {
            spec,
            result: Some(Type::I32),
        });
    }
    let mut input = String::from("[");
    let mut expected = vec![];
    for (index, case) in cases.iter().enumerate() {
        let bytes = case.spec.bytes();
        let limits = Limits {
            profile: Profile::TableMemoryV3,
            ..Limits::default()
        };
        let token = Cancellation::default();
        let proof =
            validate_spans(&bytes, limits.clone(), ValidationBudget::default(), &token).unwrap();
        let cache = FunctionCache::new(proof, CacheBudget::default(), &token).unwrap();
        let mut span = SpanInstance::new(cache, ExecutionBudget::default(), token).unwrap();
        let mut eager = Instance::new(Module::decode(&bytes, &limits).unwrap(), limits).unwrap();
        let a = outcome(span.invoke("run", &[]).map_err(|_| ()));
        let b = outcome(eager.invoke("run", &[]).map_err(|_| ()));
        assert_eq!(a, b);
        assert_eq!(span.memory(), eager.memory());
        assert_eq!(span.cache_usage().active_pins, 0);
        let hash = span
            .memory()
            .iter()
            .fold(2166136261u32, |n, b| (n ^ *b as u32).wrapping_mul(16777619));
        expected.push(format!("{a}/{hash}/{}", span.memory().len()));
        if index > 0 {
            input.push(',');
        }
        let hex = bytes.iter().map(|b| format!("{b:02x}")).collect::<String>();
        let ty = case.result.map_or("none", Type::name);
        input.push_str(&format!("{{\"hex\":\"{hex}\",\"ty\":\"{ty}\"}}"));
    }
    input.push(']');
    let script = r#"
const fs = require('node:fs');
for (const c of JSON.parse(fs.readFileSync(0, 'utf8'))) {
  const i = new WebAssembly.Instance(new WebAssembly.Module(Buffer.from(c.hex, 'hex')));
  let result;
  try {
    const v = i.exports.run();
    if (c.ty === 'none') result = 'none';
    else if (c.ty === 'i32' || c.ty === 'i64') result = c.ty + ':' + v;
    else if (Number.isNaN(v)) result = c.ty === 'f32' ? 'nan32' : 'nan64';
    else { const d = new DataView(new ArrayBuffer(8)); if (c.ty === 'f32') { d.setFloat32(0, v, true); result = 'f32:' + d.getUint32(0, true); } else { d.setFloat64(0, v, true); result = 'f64:' + d.getBigUint64(0, true); } }
  } catch (e) { if (!(e instanceof WebAssembly.RuntimeError)) throw e; result = 'trap'; }
  const memory = i.exports.memory ? new Uint8Array(i.exports.memory.buffer) : [];
  let hash = 2166136261; for (const b of memory) hash = Math.imul(hash ^ b, 16777619) >>> 0;
  console.log(result + '/' + hash + '/' + memory.length);
}
"#;
    let mut child = Command::new("node")
        .args(["-e", script])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("development Node oracle must be installed");
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
    assert_eq!(
        text.lines().collect::<Vec<_>>(),
        expected.iter().map(String::as_str).collect::<Vec<_>>()
    );
    println!("development Node parity: {} original probes; values, permitted NaNs, traps, full-memory hash and memory length",cases.len());
}
