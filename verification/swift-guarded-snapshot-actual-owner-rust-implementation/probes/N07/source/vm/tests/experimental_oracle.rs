#![cfg(feature = "experimental-stream-validation")]
mod common;
use common::*;
use mixer_vm::experimental::{validate_spans, ValidationBudget};
use mixer_vm::{Cancellation, Limits, Profile, Type::*};
use std::fmt::Write;
use std::io::Write as IoWrite;
use std::process::{Command, Stdio};
#[test]
#[ignore = "development Node WebAssembly validation oracle; invoke explicitly"]
fn node_validation_of_original_supported_subset_fixtures() {
    let mut cases: Vec<(bool, Vec<u8>)> = vec![];
    for op in 0x45..=0xc4 {
        cases.push((
            true,
            Spec::one(vec![], None, vec![0, op, 0x1a, 0x0b]).bytes(),
        ));
    }
    for sub in 0..8 {
        cases.push((
            true,
            Spec::one(vec![], None, vec![0, 0xfc, sub, 0x1a, 0x0b]).bytes(),
        ));
    }
    for op in 0x28..=0x3e {
        let mut c = vec![0, op, 0, 0];
        if op <= 0x35 {
            c.push(0x1a);
        }
        c.push(0x0b);
        let mut s = Spec::one(vec![], None, c);
        s.memory = Some((1, 1));
        cases.push((true, s.bytes()));
    }
    for code in [
        vec![0x41, 0, 4, 0x7f, 0x41, 1, 5, 0x41, 2, 0x0b, 0x1a, 0x0b],
        vec![
            2, 0x7f, 0x41, 7, 0x41, 0, 0x0e, 2, 0, 0, 0, 0x0b, 0x1a, 0x0b,
        ],
        vec![0, 0x1b, 0x1a, 0x0b],
    ] {
        cases.push((true, Spec::one(vec![], None, code).bytes()));
    }
    for code in [
        vec![0x41, 0, 4, 0x7f, 0x41, 1, 0x0b, 0x1a, 0x0b],
        vec![2, 0x7f, 0x41, 0, 0x0e, 1, 0, 1, 0x0b, 0x1a, 0x0b],
        vec![0, 0x42, 0, 0x6a, 0x1a, 0x0b],
        vec![0x41, 0, 0x0b],
        vec![0, 0x20, 0, 0x0b],
        vec![0x05, 0x0b],
        vec![0, 0x0c, 1, 0x0b],
        vec![2, 0x40, 0x0b],
        vec![0, 0x28, 3, 0, 0x1a, 0x0b],
        vec![0x0b, 1],
        vec![0x41, 0x80, 0x80, 0x80, 0x80, 0x10, 0x1a, 0x0b],
        vec![
            0x42, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 2, 0x1a, 0x0b,
        ],
    ] {
        let mut s = Spec::one(vec![], None, code);
        s.memory = Some((1, 1));
        cases.push((false, s.bytes()));
    }
    let mut s = Spec::one(vec![], None, vec![0x41, 0, 0x11, 0, 0, 0x0b]);
    s.table = Some((1, 1));
    s.elements = vec![(0, vec![0])];
    cases.push((true, s.bytes()));
    s.elements = vec![(0, vec![1])];
    cases.push((false, s.bytes()));
    for sub in [10, 11] {
        let mut c = vec![0, 0xfc, sub, 0];
        if sub == 10 {
            c.push(0);
        }
        c.push(0x0b);
        let mut s = Spec::one(vec![], None, c);
        s.memory = Some((1, 1));
        cases.push((true, s.bytes()));
    }
    let mut json = String::from("[");
    for (i, (expected, bytes)) in cases.iter().enumerate() {
        let l = Limits {
            profile: Profile::TableMemoryV3,
            ..Limits::default()
        };
        let outcome = validate_spans(
            bytes,
            l,
            ValidationBudget::default(),
            &Cancellation::default(),
        );
        assert_eq!(
            outcome.is_ok(),
            *expected,
            "stream fixture {i}: {:?}",
            outcome.err()
        );
        if i != 0 {
            json.push(',');
        }
        write!(json, "[{expected},\"").unwrap();
        for byte in bytes {
            write!(json, "{byte:02x}").unwrap();
        }
        json.push_str("\"]");
    }
    json.push(']');
    let script="let s='';process.stdin.setEncoding('utf8');process.stdin.on('data',x=>s+=x);process.stdin.on('end',()=>{const a=JSON.parse(s);for(let i=0;i<a.length;i++){const [e,h]=a[i];if(WebAssembly.validate(Buffer.from(h,'hex'))!==e){console.error('oracle mismatch at fixture '+i);process.exit(1);}}console.log(JSON.stringify({oracle:'Node WebAssembly.validate',cases:a.length,passed:true}));});";
    let mut child = Command::new("node")
        .args(["-e", script])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Node development oracle required for explicit ignored test");
    child
        .stdin
        .take()
        .unwrap()
        .write_all(json.as_bytes())
        .unwrap();
    let output = child.wait_with_output().unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    print!("{}", String::from_utf8_lossy(&output.stdout));
    // Signature/local typing independent of stack-polymorphic numeric coverage.
    let s = Spec::one(vec![I32, I64, F32, F64], Some(F64), vec![0x20, 3, 0x0b]);
    assert!(validate_spans(
        &s.bytes(),
        Limits {
            profile: Profile::NumericV2,
            ..Limits::default()
        },
        ValidationBudget::default(),
        &Cancellation::default()
    )
    .is_ok());
}
