#![cfg(feature = "experimental-swift-reactor")]
#[path = "swift_reactor_validation_fixture.rs"]
mod fixture;
use mixer_vm::experimental_swift_reactor::{
    execute_swift_command, validate_swift_command, SwiftRunBudget, SwiftValidationBudget,
};
use mixer_vm::experimental_wasi::{WasiBudget, WasiGrants};
use mixer_vm::{Cancellation, Type};
use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};

const SELECT: &str = "MIXER_STRUCTURED_CONTROL_CASE";
#[derive(Clone, Copy)]
enum Bits {
    I32(i32),
    I64(i64),
    F32(u32),
    F64(u64),
}
impl Bits {
    fn ty(self) -> Type {
        match self {
            Self::I32(_) => Type::I32,
            Self::I64(_) => Type::I64,
            Self::F32(_) => Type::F32,
            Self::F64(_) => Type::F64,
        }
    }
    fn bytes(self) -> Vec<u8> {
        match self {
            Self::I32(n) => n.to_le_bytes().to_vec(),
            Self::I64(n) => n.to_le_bytes().to_vec(),
            Self::F32(n) => n.to_le_bytes().to_vec(),
            Self::F64(n) => n.to_le_bytes().to_vec(),
        }
    }
    fn code(self) -> Vec<u8> {
        match self {
            Self::I32(n) => [vec![0x41], signed(n as i64)].concat(),
            Self::I64(n) => [vec![0x42], signed(n)].concat(),
            Self::F32(n) => [vec![0x43], n.to_le_bytes().to_vec()].concat(),
            Self::F64(n) => [vec![0x44], n.to_le_bytes().to_vec()].concat(),
        }
    }
}
fn signed(mut n: i64) -> Vec<u8> {
    let mut v = vec![];
    loop {
        let byte = (n & 127) as u8;
        n >>= 7;
        let done = (n == 0 && byte & 64 == 0) || (n == -1 && byte & 64 != 0);
        v.push(byte | if done { 0 } else { 128 });
        if done {
            return v;
        }
    }
}
struct Case {
    name: String,
    expected: Bits,
    locals: Vec<Type>,
    code: Vec<u8>,
}
fn cases() -> Vec<Case> {
    let mut cases = vec![];
    let values = [
        ("i32", Bits::I32(-129), Bits::I32(127)),
        ("i64", Bits::I64(-8_589_934_593), Bits::I64(8_589_934_591)),
        ("f32", Bits::F32(0x80000000), Bits::F32(0x7fc12345)),
        (
            "f64",
            Bits::F64(0x8000000000000000),
            Bits::F64(0x7ff8123456789abc),
        ),
    ];
    for (name, yes, no) in values {
        for condition in [0, -1] {
            let mut c = Bits::I32(condition).code();
            c.extend([0x04, fixture::type_byte(yes.ty())]);
            c.extend(yes.code());
            c.push(0x05);
            c.extend(no.code());
            c.extend([0x0b, 0x0b]);
            cases.push(Case {
                name: format!("if_{name}_{}", if condition == 0 { "else" } else { "then" }),
                expected: if condition == 0 { no } else { yes },
                locals: vec![],
                code: c,
            });
        }
        // A branch carries the typed operand and discards mixed-width stack slots.
        for outcome in ["outer", "inner", "fallthrough"] {
            let t = fixture::type_byte(yes.ty());
            let mut c = vec![0x02, t];
            c.extend(Bits::I64(777).code());
            c.extend([0x02, t]);
            c.extend(Bits::F64(0x4008000000000000).code());
            c.extend(yes.code());
            c.extend(Bits::I32(i32::from(outcome == "outer")).code());
            c.extend([0x0d, 1, 0x1a]);
            c.extend(no.code());
            c.extend(Bits::I32(i32::from(outcome == "inner")).code());
            c.extend([0x0d, 0, 0x1a, 0x1a]);
            c.extend((if outcome == "outer" { no } else { yes }).code());
            c.extend([0x0b, 0x21, 0, 0x1a, 0x20, 0, 0x0b, 0x0b]);
            cases.push(Case {
                name: format!("br_if_{name}_{outcome}"),
                expected: if outcome == "inner" { no } else { yes },
                locals: vec![yes.ty()],
                code: c,
            });
        }
        let returned = match yes {
            Bits::F32(_) => Bits::F32(0xffc23456),
            Bits::F64(_) => Bits::F64(0xfff8fedcba987654),
            _ => yes,
        };
        let mut c = vec![0x02, 0x40];
        c.extend(Bits::I32(91).code());
        c.extend([0x02, 0x40]);
        c.extend(Bits::I64(-513).code());
        c.extend([0x02, 0x40]);
        c.extend(Bits::F32(0x3f800000).code());
        c.extend(returned.code());
        c.extend([0x0f, 0x00, 0x0b, 0x1a, 0x0b, 0x1a, 0x0b]);
        c.extend(no.code());
        c.push(0x0b);
        cases.push(Case {
            name: format!("return_{name}_three_labels"),
            expected: returned,
            locals: vec![],
            code: c,
        });
    }
    for wide in [false, true] {
        for count in [0, 1, 5] {
            let value = |n| {
                if wide {
                    Bits::I64(n)
                } else {
                    Bits::I32(n as i32)
                }
            };
            let mut c = Bits::I32(count).code();
            c.extend([0x21, 0]);
            c.extend(value(-129).code());
            c.extend([
                0x21, 1, 0x02, 0x40, 0x03, 0x40, 0x20, 0, 0x45, 0x0d, 1, 0x20, 1,
            ]);
            c.extend(value(17).code());
            c.extend([if wide { 0x7c } else { 0x6a }, 0x21, 1, 0x20, 0]);
            c.extend(Bits::I32(1).code());
            c.extend([0x6b, 0x21, 0, 0x0c, 0, 0x0b, 0x0b, 0x20, 1, 0x0b]);
            cases.push(Case {
                name: format!(
                    "loop_{}_iterations_{count}",
                    if wide { "i64" } else { "i32" }
                ),
                expected: value(-129 + 17 * count as i64),
                locals: vec![Type::I32, value(0).ty()],
                code: c,
            });
        }
    }
    assert_eq!(cases.len(), 30);
    cases
}
fn module(c: &Case) -> Vec<u8> {
    let mut f = fixture::Fixture::default();
    let result_type = f.types.len() as u32;
    f.types.push(fixture::signature(&[], &[c.expected.ty()]));
    f.function_types = vec![34, result_type];
    f.memory = vec![1, 1, 1, 1];
    f.table = vec![1, 0x70, 1, 0, 0];
    f.exports = vec![(b"memory".to_vec(), 2, 0), (b"_start".to_vec(), 0, 34)];
    let store = match c.expected {
        Bits::I32(_) => 0x36,
        Bits::I64(_) => 0x37,
        Bits::F32(_) => 0x38,
        Bits::F64(_) => 0x39,
    };
    let mut start = vec![0];
    start.extend(Bits::I32(32).code());
    start.extend([0x10, 35, store, 0, 0]);
    for n in [1, 0, 1, 16] {
        start.extend(Bits::I32(n).code());
    }
    start.push(0x10);
    start.extend(fixture::uint(
        f.imports
            .iter()
            .position(|(_, field, _, _)| field == b"fd_write")
            .unwrap() as u32,
    ));
    start.extend([0x1a, 0x0b]);
    let mut helper = fixture::uint(c.locals.len() as u32);
    for t in &c.locals {
        helper.extend([1, fixture::type_byte(*t)]);
    }
    helper.extend(&c.code);
    f.bodies = vec![start, helper];
    let mut iovec = 32u32.to_le_bytes().to_vec();
    iovec.extend((c.expected.bytes().len() as u32).to_le_bytes());
    let mut data = vec![0, 0x41, 0, 0x0b];
    data.extend(fixture::uint(iovec.len() as u32));
    data.extend(iovec);
    f.data = vec![data];
    f.bytes()
}
fn hex(v: &[u8]) -> String {
    v.iter().map(|n| format!("{n:02x}")).collect()
}
const ORACLE: &str = r#"
if(process.version!=='v22.23.3')throw Error('oracle version mismatch');
const bytes=Buffer.from(require('node:fs').readFileSync(0,'utf8'),'hex');
if(!WebAssembly.validate(bytes))throw Error('invalid original module');
const m=new WebAssembly.Module(bytes);
const wasi=Object.fromEntries(WebAssembly.Module.imports(m).map(x=>[x.name,()=>{throw Error('unexpected import '+x.name)}]));
let instance;const output=[];
wasi.fd_write=(fd,p,n,w)=>{
 if(fd!==1||n!==1)throw Error('unsupported observer ABI');
 const b=instance.exports.memory.buffer,d=new DataView(b),size=d.getUint32(p+4,true);
 output.push(Buffer.from(new Uint8Array(b,d.getUint32(p,true),size)));d.setUint32(w,size,true);return 0;
};
instance=new WebAssembly.Instance(m,{wasi_snapshot_preview1:wasi});
instance.exports._start();console.log(Buffer.concat(output).toString('hex'));
"#;
fn selected(raw: Option<&str>, len: usize) -> Result<Option<usize>, String> {
    match raw {
        None => Ok(None),
        Some(s) if !s.is_empty() && s.bytes().all(|b| b.is_ascii_digit()) => {
            let n = s.parse::<usize>().map_err(|_| "case overflow")?;
            if n < len {
                Ok(Some(n))
            } else {
                Err("case out of range".into())
            }
        }
        Some(_) => Err("case must be unsigned ASCII decimal".into()),
    }
}
fn isolated(c: &Case, index: usize, node: &std::ffi::OsStr) {
    let bytes = module(c);
    if let Some(dir) = std::env::var_os("MIXER_STRUCTURED_CONTROL_ARTIFACTS") {
        std::fs::write(
            PathBuf::from(dir).join(format!("{index:02}-{}.wasm", c.name)),
            &bytes,
        )
        .unwrap();
    }
    let mut oracle = Command::new(node)
        .args(["-e", ORACLE])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let write = oracle
        .stdin
        .take()
        .unwrap()
        .write_all(hex(&bytes).as_bytes());
    let output = oracle.wait_with_output().unwrap();
    write.unwrap();
    assert!(
        output.status.success(),
        "Node {}: {}",
        c.name,
        String::from_utf8_lossy(&output.stderr)
    );
    assert_eq!(
        String::from_utf8(output.stdout).unwrap().trim(),
        hex(&c.expected.bytes()),
        "Node {}",
        c.name
    );
    println!(
        "ORACLE case={index} name={} bits={}",
        c.name,
        hex(&c.expected.bytes())
    );
    let proof = validate_swift_command(
        &bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
    let (mut stdout, mut stderr) = (vec![], vec![]);
    let report = execute_swift_command(
        proof,
        SwiftRunBudget::default(),
        WasiGrants {
            stdout: true,
            ..Default::default()
        },
        WasiBudget::default(),
        Cancellation::default(),
        &mut stdout,
        &mut stderr,
    );
    assert!(
        report.cleanup_completed,
        "UNKNOWN consuming cleanup: {report:?}"
    );
    let u = report.after_cleanup.expect("consuming owner returned");
    let (r, l) = (u.reservations, u.live);
    let currents = [
        r.retained_source.current,
        r.retained_metadata.current,
        r.cache.current,
        r.state.current,
        r.wasi.current,
        r.shared.current,
        r.construction.current,
        r.combined.current,
        l.cache_entries.current,
        l.active_pins.current,
        l.frames.current,
        l.values.current,
        l.controls.current,
        l.memory_pages.current,
    ];
    assert_eq!(currents, [0; 14], "UNKNOWN reservation cleanup");
    assert_eq!(r.live_tickets, 0, "UNKNOWN ticket cleanup");
    assert!(u.cleanup_invariant.is_none(), "UNKNOWN cleanup invariant");
    println!(
        "CLEANUP case={index} name={} currents=14x0 tickets=0 invariant=none",
        c.name
    );
    assert!(report.succeeded(), "{}: {report:?}", c.name);
    assert_eq!(stdout, c.expected.bytes(), "Mixer {}", c.name);
    assert!(stderr.is_empty());
    println!("PARITY case={index} name={} bits={}", c.name, hex(&stdout));
}
#[test]
#[ignore = "explicit pinned Node development oracle; consuming experimental command ABI"]
fn structured_control_matches_node_consuming() {
    let corpus = cases();
    let raw = std::env::var(SELECT);
    let selection = match raw {
        Ok(ref s) => selected(Some(s), corpus.len()),
        Err(std::env::VarError::NotPresent) => selected(None, corpus.len()),
        Err(_) => Err("non Unicode case selector".into()),
    }
    .expect("invalid structured-control environment");
    let node = std::env::var_os("MIXER_NODE").expect("MIXER_NODE must explicitly name pinned Node");
    if let Some(i) = selection {
        isolated(&corpus[i], i, &node);
        return;
    }
    // Exercise the same parser before constructing any runtime.
    for invalid in [
        "",
        "-1",
        "+1",
        "1x",
        " 1",
        "30",
        "184467440737095516160",
        "１",
    ] {
        assert!(selected(Some(invalid), corpus.len()).is_err());
        println!("ENV_REJECT raw={invalid:?} runtimes=0 payloads=0");
    }
    let version = Command::new(&node).arg("--version").output().unwrap();
    assert!(version.status.success());
    assert_eq!(
        String::from_utf8(version.stdout).unwrap().trim(),
        "v22.23.3"
    );
    for (index, c) in corpus.iter().enumerate() {
        let output = Command::new(std::env::current_exe().unwrap())
            .args([
                "--ignored",
                "--exact",
                "structured_control_matches_node_consuming",
                "--nocapture",
                "--test-threads=1",
            ])
            .env(SELECT, index.to_string())
            .output()
            .unwrap();
        let text = String::from_utf8_lossy(&output.stdout);
        print!("{text}");
        assert!(
            output.status.success(),
            "{}: {}",
            c.name,
            String::from_utf8_lossy(&output.stderr)
        );
        for marker in ["ORACLE", "CLEANUP", "PARITY"] {
            assert!(
                text.contains(&format!("{marker} case={index} name={} ", c.name)),
                "missing {marker}: {}",
                c.name
            );
        }
    }
    println!("SUMMARY cases=30 node_comparisons=30 mixer_executions=30 runtime_objects=30 cleanups=30 env_rejections=8 currents=14x0 tickets=0");
}
