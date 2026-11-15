#![cfg(feature = "experimental-swift-reactor")]

use mixer_vm::experimental_swift_reactor::{
    execute_swift_command, validate_swift_command, SwiftRunBudget, SwiftRunFailureKind,
    SwiftValidationBudget,
};
use mixer_vm::experimental_wasi::{WasiBudget, WasiFunction, WasiGrants};
use mixer_vm::{Cancellation, Type};
use std::io::Write;
use std::os::unix::{ffi::OsStringExt, fs::PermissionsExt};
use std::path::PathBuf;
use std::process::{Command, Output, Stdio};

const TEST: &str = "indirect_calls_match_node";
const SELECT: &str = "MIXER_DIFFERENTIAL_INDIRECT_TYPED_CASE";
const COUNT: usize = 24;

// Original Core binary encoding; no WAT assembler, inherited module or fixture.
// Internal unary functions preserve exact integer/float representations. Only
// memory and the void _start are exported through the admitted command ABI.
fn u(mut n: u32) -> Vec<u8> {
    let mut b = Vec::new();
    loop {
        let x = (n & 127) as u8;
        n >>= 7;
        b.push(x | if n == 0 { 0 } else { 128 });
        if n == 0 {
            return b;
        }
    }
}
fn signed(mut n: i64) -> Vec<u8> {
    let mut b = Vec::new();
    loop {
        let x = (n & 127) as u8;
        n >>= 7;
        let done = (n == 0 && x & 64 == 0) || (n == -1 && x & 64 != 0);
        b.push(x | if done { 0 } else { 128 });
        if done {
            return b;
        }
    }
}
fn name(s: &[u8]) -> Vec<u8> {
    let mut b = u(s.len() as u32);
    b.extend(s);
    b
}
fn section(m: &mut Vec<u8>, id: u8, b: Vec<u8>) {
    m.push(id);
    m.extend(u(b.len() as u32));
    m.extend(b);
}
fn ty(t: Type) -> u8 {
    match t {
        Type::I32 => 0x7f,
        Type::I64 => 0x7e,
        Type::F32 => 0x7d,
        Type::F64 => 0x7c,
    }
}
fn signature(p: &[Type], r: &[Type]) -> Vec<u8> {
    let mut b = vec![0x60];
    b.extend(u(p.len() as u32));
    b.extend(p.iter().copied().map(ty));
    b.extend(u(r.len() as u32));
    b.extend(r.iter().copied().map(ty));
    b
}
fn kind(k: usize) -> Type {
    [Type::I32, Type::I64, Type::F32, Type::F64][k]
}
fn width(k: usize) -> usize {
    if k == 0 || k == 2 {
        4
    } else {
        8
    }
}
fn bits(k: usize) -> [u64; 3] {
    match k {
        0 => [0x8000_0001, 0x7fff_fffe, 0xdead_beef],
        1 => [
            0x0020_0000_0000_0001,
            0x8000_0000_0000_0001,
            0x7fff_ffff_ffff_fffe,
        ],
        2 => [0x8000_0000, 0x0000_0001, 0x7fc1_2345],
        _ => [
            0x8000_0000_0000_0000,
            0x0000_0000_0000_0001,
            0x7ff8_1234_5678_9abc,
        ],
    }
}
fn constant(k: usize, n: u64) -> Vec<u8> {
    let mut b = vec![[0x41, 0x42, 0x43, 0x44][k]];
    match k {
        0 => b.extend(signed(n as i32 as i64)),
        1 => b.extend(signed(n as i64)),
        _ => b.extend(&n.to_le_bytes()[..width(k)]),
    };
    b
}
fn element(offset: i32, functions: &[u32], explicit: bool) -> Vec<u8> {
    let mut b = if explicit { vec![2, 0] } else { vec![0] };
    b.push(0x41);
    b.extend(signed(offset as i64));
    b.push(0x0b);
    if explicit {
        b.push(0);
    }
    b.extend(u(functions.len() as u32));
    for f in functions {
        b.extend(u(*f));
    }
    b
}
fn selectors(s: usize) -> Vec<i32> {
    match s {
        0 => vec![0, 1, 2, 0],
        1 => vec![2, 0, 1, 2],
        2 => vec![3],
        3 => vec![i32::MIN],
        4 => vec![4],
        _ => vec![5],
    }
}
fn trap(s: usize) -> Option<&'static str> {
    match s {
        0 | 1 => None,
        2 => Some("indirect_call_null"),
        3 => Some("table_out_of_bounds"),
        _ => Some("indirect_call_type_mismatch"),
    }
}
fn expected(k: usize, s: usize) -> Vec<u8> {
    if trap(s).is_some() {
        return vec![];
    }
    let order = if s == 0 { [1, 0, 2, 1] } else { [0, 2, 1, 0] };
    let mut b = Vec::new();
    for i in order {
        b.extend(&bits(k)[i].to_le_bytes()[..width(k)]);
    }
    b
}
fn module(case: usize, rejected_opcode: Option<u8>) -> Vec<u8> {
    let k = case / 6;
    let s = case % 6;
    let t = kind(k);
    let other = kind((k + 1) % 4);
    let all = WasiFunction::ALL;
    let n = all.len() as u32;
    let mut m = b"\0asm\x01\0\0\0".to_vec();
    let mut types = u(n + 5);
    for f in all {
        types.extend(signature(f.parameters(), f.results()));
    }
    types.extend(signature(&[], &[]));
    types.extend(signature(&[t], &[t]));
    types.extend(signature(&[t], &[t])); // distinct index, structural equality
    types.extend(signature(&[t], &[other]));
    types.extend(signature(&[], &[t]));
    section(&mut m, 1, types);
    let mut imports = u(n);
    for (i, f) in all.into_iter().enumerate() {
        imports.extend(name(b"wasi_snapshot_preview1"));
        imports.extend(name(f.name()));
        imports.push(0);
        imports.extend(u(i as u32));
    }
    section(&mut m, 2, imports);
    let mut functions = u(6);
    for i in [n, n + 1, n + 1, n + 1, n + 3, n + 4] {
        functions.extend(u(i));
    }
    section(&mut m, 3, functions);
    section(&mut m, 4, vec![1, 0x70, 1, 6, 6]);
    section(&mut m, 5, vec![1, 1, 1, 1]);
    let mut exports = vec![2];
    exports.extend(name(b"memory"));
    exports.extend([2, 0]);
    exports.extend(name(b"_start"));
    exports.push(0);
    exports.extend(u(n));
    section(&mut m, 7, exports);
    let mut elements = vec![4];
    elements.extend(element(0, &[n + 1, n + 2, n + 3], false));
    elements.extend(if s == 1 {
        element(0, &[n + 3, n + 2, n + 1], true)
    } else {
        element(0, &[n + 2, n + 1], true)
    });
    elements.extend(element(4, &[n + 4, n + 5], false));
    elements.extend(element(6, &[], true)); // empty segment at exact end
    section(&mut m, 9, elements);
    let mut start = vec![0];
    if let Some(op) = rejected_opcode {
        // table.get/set are well-formed Core instructions but outside this
        // executable profile; they are never counted as executed semantics.
        start.extend([0x41, 0, op, 0]);
        if op == 0x25 {
            start.push(0x1a);
        }
    } else {
        for (i, slot) in selectors(s).into_iter().enumerate() {
            start.extend(constant(0, (64 + i * width(k)) as u64));
            start.extend(constant(k, bits(k)[0]));
            start.extend(constant(0, slot as u32 as u64));
            start.push(0x11);
            start.extend(u(n + 2));
            start.push(0);
            start.extend([[0x36, 0x37, 0x38, 0x39][k], 0, 0]);
        }
        for v in [1, 0, 1, 32] {
            start.extend(constant(0, v));
        }
        start.push(0x10);
        start.extend(u(
            all.iter().position(|f| f.name() == b"fd_write").unwrap() as u32
        ));
        start.push(0x1a);
    }
    start.push(0x0b);
    let mut b = vec![0];
    b.extend(constant(k, bits(k)[1]));
    b.push(0x0b);
    let mut c = vec![0];
    c.extend(constant(k, bits(k)[2]));
    c.push(0x0b);
    let mut wrong = vec![0];
    wrong.extend(constant((k + 1) % 4, 0));
    wrong.push(0x0b);
    let mut noarg = vec![0];
    noarg.extend(constant(k, 7));
    noarg.push(0x0b);
    let mut code = vec![6];
    for body in [start, vec![0, 0x20, 0, 0x0b], b, c, wrong, noarg] {
        code.extend(u(body.len() as u32));
        code.extend(body);
    }
    section(&mut m, 10, code);
    let mut payload = 64u32.to_le_bytes().to_vec();
    payload.extend((selectors(s).len() as u32 * width(k) as u32).to_le_bytes());
    let mut data = vec![1, 0, 0x41, 0, 0x0b];
    data.extend(u(payload.len() as u32));
    data.extend(payload);
    section(&mut m, 11, data);
    m
}
fn hex(b: &[u8]) -> String {
    b.iter().map(|v| format!("{v:02x}")).collect()
}
const ORACLE: &str = r#"
const fs=require('node:fs');
const [raw,kind]=fs.readFileSync(0,'utf8').trim().split('\n');
const bytes=Buffer.from(raw,'hex');
if(!WebAssembly.validate(bytes))throw Error('node-validation');
const module_=new WebAssembly.Module(bytes);
if(WebAssembly.Module.exports(module_).map(x=>x.name).sort().join(',')!=='_start,memory')throw Error('exports');
const wasi=Object.fromEntries(WebAssembly.Module.imports(module_).map(x=>[x.name,()=>{throw Error('unexpected import '+x.name)}]));
let instance;const output=[];
wasi.fd_write=(fd,p,n,w)=>{if(fd!==1||n!==1)throw Error('output ABI');const v=new DataView(instance.exports.memory.buffer);const a=v.getUint32(p,true),z=v.getUint32(p+4,true);output.push(Buffer.from(new Uint8Array(v.buffer,a,z)));v.setUint32(w,z,true);return 0};
instance=new WebAssembly.Instance(module_,{wasi_snapshot_preview1:wasi});
let terminal='value';try{instance.exports._start()}catch(e){if(!(e instanceof WebAssembly.RuntimeError))throw e;terminal='trap'}
const output_=Buffer.concat(output),v=new DataView(output_.buffer,output_.byteOffset,output_.byteLength),values=[];
const wide=kind==='1'||kind==='3';
for(let i=0;i<output_.length;i+=wide?8:4){
 if(kind==='1')values.push(v.getBigInt64(i,true).toString());
 else if(wide)values.push(v.getBigUint64(i,true).toString(16).padStart(16,'0'));
 else values.push(v.getUint32(i,true).toString(16).padStart(8,'0'));
}
console.log(terminal+':'+output_.toString('hex')+':'+values.join(','));
"#;
fn typed(k: usize, b: &[u8]) -> String {
    b.chunks_exact(width(k))
        .map(|v| {
            if width(k) == 4 {
                format!("{:08x}", u32::from_le_bytes(v.try_into().unwrap()))
            } else if k == 1 {
                i64::from_le_bytes(v.try_into().unwrap()).to_string()
            } else {
                format!("{:016x}", u64::from_le_bytes(v.try_into().unwrap()))
            }
        })
        .collect::<Vec<_>>()
        .join(",")
}
fn node_path() -> PathBuf {
    let executable = |p: &PathBuf| {
        p.is_absolute()
            && p.is_file()
            && p.metadata()
                .is_ok_and(|m| m.permissions().mode() & 0o111 != 0)
    };
    let p = match std::env::var_os("MIXER_NODE") {
        Some(p) => PathBuf::from(p),
        None => std::env::var_os("PATH")
            .and_then(|paths| {
                std::env::split_paths(&paths)
                    .map(|p| p.join("node"))
                    .find(executable)
            })
            .expect("ENVIRONMENT_REJECTED: Node required"),
    };
    assert!(
        executable(&p),
        "ENVIRONMENT_REJECTED: absolute executable Node required"
    );
    p
}
fn isolated(case: usize, node: PathBuf) {
    let k = case / 6;
    let s = case % 6;
    let bytes = module(case, None);
    let expected = expected(k, s);
    println!(
        "MODULE case={case} kind={k} boundary={s} hex={}",
        hex(&bytes)
    );
    println!("WORKER case={case} pid={}", std::process::id());
    let mut child = Command::new(node)
        .current_dir(std::env::current_dir().unwrap())
        .env_remove("NODE_OPTIONS")
        .env_remove("NODE_PATH")
        .args(["-e", ORACLE])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("UNKNOWN Node spawn");
    let input = child
        .stdin
        .take()
        .unwrap()
        .write_all(format!("{}\n{k}\n", hex(&bytes)).as_bytes());
    let output = child.wait_with_output().expect("UNKNOWN Node reap");
    input.expect("Node input");
    assert!(
        output.status.success(),
        "Node case={case}: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stderr.is_empty());
    let oracle = format!(
        "{}:{}:{}",
        if trap(s).is_some() { "trap" } else { "value" },
        hex(&expected),
        typed(k, &expected)
    );
    assert_eq!(
        String::from_utf8(output.stdout).unwrap().trim(),
        oracle,
        "independent Node result case={case}"
    );
    println!("ORACLE case={case} {oracle}");
    for replay in 0..2 {
        let proof = validate_swift_command(
            &bytes,
            SwiftValidationBudget::default(),
            &Cancellation::default(),
        )
        .unwrap_or_else(|e| panic!("REJECTION case={case} stage=validation {e:?}"));
        println!("ADMITTED case={case} replay={replay}");
        let mut stdout = vec![];
        let mut stderr = vec![];
        // The consuming entry owns construction through cleanup, including traps.
        // No assertion runs while a successfully constructed Runtime is live.
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
            "UNKNOWN consuming cleanup case={case}: {report:?}"
        );
        let usage = report
            .after_cleanup
            .expect("UNKNOWN missing consuming usage");
        let r = usage.reservations;
        let l = usage.live;
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
        assert_eq!(currents, [0; 14], "UNKNOWN currents case={case}");
        assert_eq!(r.live_tickets, 0, "UNKNOWN tickets case={case}");
        assert!(
            usage.cleanup_invariant.is_none(),
            "UNKNOWN invariant case={case}"
        );
        println!("CLEANUP case={case} replay={replay} currents=14x0 tickets=0 invariant=none");
        if let Some(code) = trap(s) {
            let e = report.terminal.as_ref().expect("guest trap required");
            assert_eq!(e.kind, SwiftRunFailureKind::GuestTrap);
            assert_eq!(e.code, code);
            assert!(!report.succeeded());
        } else {
            assert!(report.succeeded(), "case={case}: {report:?}");
            assert!(report.terminal.is_none());
        }
        assert!(!report.output_error);
        assert!(stderr.is_empty());
        assert_eq!(stdout, expected, "case={case} replay={replay}");
        assert_eq!(
            report.calls_by_function.iter().sum::<u64>(),
            if trap(s).is_some() { 0 } else { 1 }
        );
        println!(
            "PARITY case={case} replay={replay} terminal={} bytes={} typed={}",
            trap(s).unwrap_or("value"),
            hex(&stdout),
            typed(k, &stdout)
        );
    }
    // Separate unsupported-feature admission check, with no Runtime creation.
    if case == 0 {
        let rejected = module(0, Some(0x25));
        println!("REJECTED_MODULE feature=table.get hex={}", hex(&rejected));
        let failure = validate_swift_command(
            &rejected,
            SwiftValidationBudget::default(),
            &Cancellation::default(),
        )
        .err()
        .expect("table.get outside profile");
        println!("UNSUPPORTED_REJECTED feature=table.get failure={failure:?}");
    }
}
fn worker(selector: &str) -> Command {
    let mut c = Command::new(std::env::current_exe().unwrap());
    c.current_dir(std::env::current_dir().unwrap())
        .args([
            "--ignored",
            "--exact",
            TEST,
            "--nocapture",
            "--test-threads=1",
        ])
        .env(SELECT, selector);
    c
}
fn rejected(label: &str, o: Output) {
    assert!(!o.status.success());
    let mut b = o.stdout;
    b.extend(o.stderr);
    let t = String::from_utf8_lossy(&b);
    assert!(t.contains("ENVIRONMENT_REJECTED:"), "{t}");
    for marker in [
        "MODULE case=",
        "WORKER case=",
        "ORACLE case=",
        "ADMITTED case=",
        "CLEANUP case=",
    ] {
        assert!(!t.contains(marker), "environment reached payload");
    }
    println!("ENVIRONMENT_FAIL_CLOSED control={label}");
}
#[test]
#[ignore = "original typed table identity corpus; explicit Node oracle and consuming API"]
fn indirect_calls_match_node() {
    let selected = match std::env::var(SELECT) {
        Ok(raw) => {
            let n = raw
                .parse::<usize>()
                .expect("ENVIRONMENT_REJECTED: invalid selector");
            assert!(
                n < COUNT && raw == n.to_string(),
                "ENVIRONMENT_REJECTED: noncanonical selector"
            );
            Some(n)
        }
        Err(std::env::VarError::NotPresent) => None,
        Err(_) => panic!("ENVIRONMENT_REJECTED: non-Unicode selector"),
    };
    let node = node_path();
    if let Some(case) = selected {
        isolated(case, node);
        return;
    }
    for s in [
        "",
        "-1",
        "24",
        "01",
        "+1",
        " 1",
        "not-an-index",
        "184467440737095516160",
    ] {
        rejected(
            "selector",
            worker(s).output().expect("UNKNOWN environment child"),
        );
    }
    rejected(
        "non-Unicode",
        worker("0")
            .env(SELECT, std::ffi::OsString::from_vec(vec![0xff]))
            .output()
            .expect("UNKNOWN environment child"),
    );
    rejected(
        "missing-node",
        worker("0")
            .env_remove("MIXER_NODE")
            .env("PATH", "")
            .output()
            .expect("UNKNOWN environment child"),
    );
    for p in [
        PathBuf::new(),
        PathBuf::from("relative-node"),
        PathBuf::from("/mixer-r3036-no-node"),
        PathBuf::from("/"),
        std::env::current_dir().unwrap().join("Cargo.toml"),
    ] {
        rejected(
            "explicit-node",
            worker("0")
                .env("MIXER_NODE", p)
                .env("PATH", node.parent().unwrap())
                .output()
                .expect("UNKNOWN environment child"),
        );
    }
    for case in 0..COUNT {
        let mut cmd = worker(&case.to_string());
        cmd.env("NODE_OPTIONS", "--mixer-invalid-option-r3036")
            .env("NODE_PATH", "/mixer-invalid-r3036");
        if case == COUNT - 1 {
            cmd.env_remove("MIXER_NODE")
                .env("PATH", node.parent().unwrap());
        } else {
            cmd.env("MIXER_NODE", &node);
        }
        let output = cmd.output().expect("UNKNOWN case child");
        print!("{}", String::from_utf8_lossy(&output.stdout));
        assert!(
            output.status.success(),
            "case={case}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(output.stderr.is_empty());
        let text = String::from_utf8_lossy(&output.stdout);
        assert_eq!(text.matches("CLEANUP case=").count(), 2);
        assert_eq!(text.matches("PARITY case=").count(), 2);
    }
    println!("CORPUS_COMPLETE original_modules=24 runtimes=48 typed_values=32 environment_controls=15 unsupported_rejections=1");
}
