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

const TEST: &str = "direct_calls_match_node";
const SELECT: &str = "MIXER_DIFFERENTIAL_DIRECT_CALL_CASE";
const COUNT: usize = 24;

// Independently authored Core direct-call corpus; only _start and memory export.
// Spec: https://webassembly.github.io/spec/core/exec/instructions.html#exec-call
// Mixed parameter order, local-frame isolation, nested return, finite recursion,
// observable internal-call effects and semantic traps use the consuming ABI.
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

fn call(b: &mut Vec<u8>, f: u32) {
    b.push(0x10);
    b.extend(u(f));
}
fn get(b: &mut Vec<u8>, l: u32) {
    b.push(0x20);
    b.extend(u(l));
}
fn set(b: &mut Vec<u8>, l: u32) {
    b.push(0x21);
    b.extend(u(l));
}
fn store(b: &mut Vec<u8>, k: usize) {
    b.extend([[0x36, 0x37, 0x38, 0x39][k], 0, 0]);
}
fn fd_write(b: &mut Vec<u8>) {
    for v in [1, 0, 1, 32] {
        b.extend(constant(0, v));
    }
    call(
        b,
        WasiFunction::ALL
            .iter()
            .position(|f| f.name() == b"fd_write")
            .unwrap() as u32,
    );
    b.push(0x1a);
}
fn trap(k: usize, s: usize) -> Option<&'static str> {
    if s != 5 {
        return None;
    }
    Some(
        [
            "unreachable",
            "integer_divide_by_zero",
            "integer_overflow",
            "memory_out_of_bounds",
        ][k],
    )
}
fn expected(k: usize, s: usize) -> Vec<u8> {
    let values: Vec<u64> = match s {
        0 | 3 => bits(k).to_vec(),
        1 => vec![bits(k)[0], bits(k)[1], bits(k)[2], 0],
        2 => vec![bits(k)[0], bits(k)[2], bits(k)[1]],
        4 => vec![bits(k)[0], bits(k)[1]],
        _ => vec![bits(k)[0]],
    };
    let mut b = vec![];
    for (i, v) in values.into_iter().enumerate() {
        b.extend(&v.to_le_bytes()[..width(k)]);
        if s == 4 {
            b.extend((if i == 0 { 4u32 } else { 11u32 }).to_le_bytes());
        }
    }
    b
}
fn module(case: usize) -> Vec<u8> {
    let k = case / 6;
    let s = case % 6;
    let t = kind(k);
    let all = WasiFunction::ALL;
    let n = all.len() as u32;
    let mut m = b"\0asm\x01\0\0\0".to_vec();
    let mut types = u(n + 5);
    for f in all {
        types.extend(signature(f.parameters(), f.results()));
    }
    types.extend(signature(&[], &[]));
    types.extend(signature(
        &[Type::I32, Type::I64, Type::F32, Type::F64],
        &[t],
    ));
    types.extend(signature(&[t], &[t]));
    types.extend(signature(&[Type::I32, t], &[t]));
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
    let a = n + 1;
    let b = n + 2;
    let c = n + 3;
    let shapes = match s {
        0 => [n, n + 1, n + 2, n + 4],
        1 => [n, n + 2, n + 2, n + 4],
        2 | 3 => [n, n + 3, n + 2, n + 4],
        4 => [n, n + 3, n + 3, n + 4],
        _ => [n, n + 2, n + 2, n + 2],
    };
    let mut functions = vec![4];
    for shape in shapes {
        functions.extend(u(shape));
    }
    section(&mut m, 3, functions);
    // Consuming command ABI requires an internal table even for direct-only calls.
    section(&mut m, 4, vec![1, 0x70, 1, 1, 1]);
    section(&mut m, 5, vec![1, 1, 1, 1]);
    let mut exports = vec![2];
    exports.extend(name(b"memory"));
    exports.extend([2, 0]);
    exports.extend(name(b"_start"));
    exports.push(0);
    exports.extend(u(n));
    section(&mut m, 7, exports);
    let mut start = vec![0];
    let mut fa = vec![0];
    let mut fb = vec![0];
    let mut fc = vec![0];
    match s {
        0 => {
            get(&mut fa, k as u32);
            call(&mut fa, b);
            get(&mut fb, 0);
            fc.extend(constant(k, 0));
            for i in 0..3 {
                start.extend(constant(0, (64 + i * width(k)) as u64));
                for q in 0..4 {
                    start.extend(constant(q, bits(q)[(i + q + 3 - k) % 3]));
                }
                call(&mut start, a);
                store(&mut start, k);
            }
        }
        1 => {
            fa = vec![1, 1, ty(t)];
            get(&mut fa, 0);
            set(&mut fa, 1);
            fa.extend(constant(k, bits(k)[2]));
            call(&mut fa, b);
            fa.push(0x1a);
            get(&mut fa, 1);
            fb = vec![1, 1, ty(t)];
            fb.extend(constant(k, bits(k)[1]));
            set(&mut fb, 0);
            fb.extend(constant(k, bits(k)[2]));
            set(&mut fb, 1);
            get(&mut fb, 1);
            fc = vec![1, 1, ty(t)];
            get(&mut fc, 0);
            for (i, v) in bits(k).into_iter().enumerate() {
                start.extend(constant(0, (64 + i * width(k)) as u64));
                start.extend(constant(k, v));
                call(&mut start, a);
                store(&mut start, k);
            }
            start.extend(constant(0, (64 + 3 * width(k)) as u64));
            call(&mut start, c);
            store(&mut start, k);
        }
        2 => {
            get(&mut fa, 0);
            fa.extend([0x04, 0x40, 0x02, 0x40]);
            fa.extend(constant(1, 0x778899));
            get(&mut fa, 1);
            call(&mut fa, b);
            fa.extend([0x0f, 0x0b, 0x0b]);
            fa.extend(constant(k, bits(k)[2]));
            fb.extend([0x02, 0x40]);
            fb.extend(constant(0, 0x55));
            get(&mut fb, 0);
            fb.extend([0x0f, 0x0b, 0x00]);
            fc.extend(constant(k, 0));
            for (i, (cond, v)) in [(1, bits(k)[0]), (0, bits(k)[1]), (1, bits(k)[1])]
                .into_iter()
                .enumerate()
            {
                start.extend(constant(0, (64 + i * width(k)) as u64));
                start.extend(constant(0, cond));
                start.extend(constant(k, v));
                call(&mut start, a);
                store(&mut start, k);
            }
        }
        3 => {
            fa = vec![1, 1, ty(t)];
            get(&mut fa, 1);
            set(&mut fa, 2);
            get(&mut fa, 0);
            fa.extend([0x45, 0x04, 0x40]);
            get(&mut fa, 2);
            fa.extend([0x0f, 0x0b]);
            get(&mut fa, 0);
            fa.extend(constant(0, 1));
            fa.push(0x6b);
            fa.extend(constant(k, bits(k)[1]));
            call(&mut fa, a);
            fa.push(0x1a);
            get(&mut fa, 2);
            get(&mut fb, 0);
            fc.extend(constant(k, 0));
            for (i, depth) in [0, 1, 11].into_iter().enumerate() {
                start.extend(constant(0, (64 + i * width(k)) as u64));
                start.extend(constant(0, depth));
                start.extend(constant(k, bits(k)[i]));
                call(&mut start, a);
                store(&mut start, k);
            }
        }
        4 => {
            for (body, next) in [(&mut fa, b), (&mut fb, a)] {
                body.extend(constant(0, 128));
                body.extend(constant(0, 128));
                body.extend([0x28, 0, 0]);
                body.extend(constant(0, 1));
                body.push(0x6a);
                store(body, 0);
                get(body, 0);
                body.extend([0x45, 0x04, 0x40]);
                get(body, 1);
                body.extend([0x0f, 0x0b]);
                get(body, 0);
                body.extend(constant(0, 1));
                body.push(0x6b);
                get(body, 1);
                call(body, next);
            }
            fc.extend(constant(k, 0));
            for (i, depth) in [3, 6].into_iter().enumerate() {
                let offset = 64 + i * (width(k) + 4);
                start.extend(constant(0, offset as u64));
                start.extend(constant(0, depth));
                start.extend(constant(k, bits(k)[i]));
                call(&mut start, a);
                store(&mut start, k);
                start.extend(constant(0, (offset + width(k)) as u64));
                start.extend(constant(0, 128));
                start.extend([0x28, 0, 0]);
                store(&mut start, 0);
            }
        }
        _ => {
            start.extend(constant(0, 64));
            start.extend(constant(k, bits(k)[0]));
            store(&mut start, k);
            fd_write(&mut start);
            start.extend(constant(k, bits(k)[1]));
            call(&mut start, a);
            start.push(0x1a);
            // Any incorrectly resumed caller would emit a second observable write.
            get(&mut fa, 0);
            call(&mut fa, b);
            get(&mut fb, 0);
            call(&mut fb, c);
            match k {
                0 => fc.push(0x00),
                1 => {
                    fc.extend(constant(0, 17));
                    fc.extend(constant(0, 0));
                    fc.extend([0x6d, 0x1a]);
                }
                2 => {
                    fc.extend(constant(1, 0x8000000000000000));
                    fc.extend(constant(1, u64::MAX));
                    fc.extend([0x7f, 0x1a]);
                }
                _ => {
                    fc.extend(constant(0, 65533));
                    fc.extend([0x28, 0, 0, 0x1a]);
                }
            }
            fc.extend(constant(k, bits(k)[2]));
        }
    }
    fd_write(&mut start);
    start.push(0x0b);
    fa.push(0x0b);
    fb.push(0x0b);
    fc.push(0x0b);
    let mut code = vec![4];
    for body in [start, fa, fb, fc] {
        code.extend(u(body.len() as u32));
        code.extend(body);
    }
    section(&mut m, 10, code);
    let mut payload = 64u32.to_le_bytes().to_vec();
    payload.extend((expected(k, s).len() as u32).to_le_bytes());
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
const [raw,k]=fs.readFileSync(0,'utf8').trim().split('\n');
if(raw.length>8192)throw Error('module bound');
const bytes=Buffer.from(raw,'hex');if(!WebAssembly.validate(bytes))throw Error('node-validation');
const m=new WebAssembly.Module(bytes);
if(WebAssembly.Module.exports(m).map(x=>x.name).sort().join(',')!=='_start,memory')throw Error('exports');
const wasi=Object.fromEntries(WebAssembly.Module.imports(m).map(x=>[x.name,()=>{throw Error('unexpected import '+x.name)}]));
let instance;const output=[];
wasi.fd_write=(fd,p,n,w)=>{if(fd!==1||n!==1||output.length>=2)throw Error('output ABI');const v=new DataView(instance.exports.memory.buffer);const a=v.getUint32(p,true),z=v.getUint32(p+4,true);if(z>64)throw Error('output bound');output.push(Buffer.from(new Uint8Array(v.buffer,a,z)));v.setUint32(w,z,true);return 0};
instance=new WebAssembly.Instance(m,{wasi_snapshot_preview1:wasi});
let terminal='value';try{instance.exports._start()}catch(e){
 if(!(e instanceof WebAssembly.RuntimeError))throw e;
 const msg=String(e.message);
 if(/unreachable/.test(msg))terminal='unreachable';
 else if(/divide by zero/.test(msg))terminal='integer_divide_by_zero';
 else if(/divide result unrepresentable|integer overflow/.test(msg))terminal='integer_overflow';
 else if(/memory access out of bounds|out of bounds memory access/.test(msg))terminal='memory_out_of_bounds';
 else throw e;
}
console.log(terminal+':'+Buffer.concat(output).toString('hex'));
"#;
fn node_path() -> PathBuf {
    let executable = |p: &PathBuf| {
        p.is_absolute()
            && p.is_file()
            && p.metadata()
                .is_ok_and(|m| m.permissions().mode() & 0o111 != 0)
    };
    let p = PathBuf::from(
        std::env::var_os("MIXER_NODE").expect("ENVIRONMENT_REJECTED: explicit MIXER_NODE required"),
    );
    assert!(
        executable(&p),
        "ENVIRONMENT_REJECTED: absolute executable Node required"
    );
    p
}
fn isolated(case: usize, node: PathBuf) {
    let k = case / 6;
    let s = case % 6;
    let bytes = module(case);
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
    let oracle = format!("{}:{}", trap(k, s).unwrap_or("value"), hex(&expected));
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
        if let Some(code) = trap(k, s) {
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
        assert_eq!(report.calls_by_function.iter().sum::<u64>(), 1);
        println!(
            "PARITY case={case} replay={replay} terminal={} bytes={} typed={}",
            trap(k, s).unwrap_or("value"),
            hex(&stdout),
            hex(&stdout)
        );
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
#[ignore = "original direct calls, local frames, finite recursion and trap unwinding; explicit Node oracle and consuming API"]
fn direct_calls_match_node() {
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
        PathBuf::from("/mixer-r3202-no-node"),
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
        cmd.env("NODE_OPTIONS", "--mixer-invalid-option-r3202")
            .env("NODE_PATH", "/mixer-invalid-r3202");
        cmd.env("MIXER_NODE", &node);
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
    println!("CORPUS_COMPLETE original_modules=24 runtimes=48 success_modules=20 trap_modules=4 environment_controls=15");
}
