#![cfg(feature = "experimental-swift-reactor")]

#[path = "swift_reactor_validation_fixture.rs"]
mod fixture;

use mixer_vm::experimental_swift_reactor::{
    execute_swift_command, validate_swift_command, SwiftRunBudget, SwiftValidationBudget,
};
use mixer_vm::experimental_wasi::{WasiBudget, WasiGrants};
use mixer_vm::{Cancellation, Type};
use std::io::Write;
use std::os::unix::{ffi::OsStringExt, fs::PermissionsExt};
use std::path::PathBuf;
use std::process::{Command, Output, Stdio};

const TEST: &str = "globals_match_node";
const CASE_ENV: &str = "MIXER_DIFFERENTIAL_GLOBALS_CASE";

#[derive(Clone, Copy, Debug)]
enum Kind {
    I32,
    I64,
    F32,
    F64,
}
impl Kind {
    fn ty(self) -> Type {
        match self {
            Self::I32 => Type::I32,
            Self::I64 => Type::I64,
            Self::F32 => Type::F32,
            Self::F64 => Type::F64,
        }
    }
    fn wide(self) -> bool {
        matches!(self, Self::I64 | Self::F64)
    }
    fn constant(self, bits: u64, body: &mut Vec<u8>) {
        match self {
            Self::I32 => {
                body.push(0x41);
                signed(bits as u32 as i32 as i64, body);
            }
            Self::I64 => {
                body.push(0x42);
                signed(bits as i64, body);
            }
            Self::F32 => {
                body.push(0x43);
                body.extend_from_slice(&(bits as u32).to_le_bytes());
            }
            Self::F64 => {
                body.push(0x44);
                body.extend_from_slice(&bits.to_le_bytes());
            }
        }
    }
    fn to_integer(self, body: &mut Vec<u8>) {
        match self {
            Self::F32 => body.push(0xbc),
            Self::F64 => body.push(0xbd),
            _ => (),
        }
    }
    fn from_integer(self, body: &mut Vec<u8>) {
        match self {
            Self::F32 => body.push(0xbe),
            Self::F64 => body.push(0xbf),
            _ => (),
        }
    }
}
#[derive(Clone, Copy)]
struct Global {
    kind: Kind,
    mutable: bool,
    bits: u64,
}
struct Case {
    name: String,
    globals: Vec<Global>,
    writes: Vec<(usize, u64)>,
    exported_accessors: bool,
}

fn baseline_shapes() -> Vec<Case> {
    let mut cases = Vec::new();
    // These four structural controls use the currently admitted command ABI.
    // They establish actual consuming execution separately from multi-export failures.
    for (kind, bits) in [
        (Kind::I32, 0x89ab_cdef),
        (Kind::I64, 0x8ace_0246_1357_9bdf),
        (Kind::F32, 0xffc2_195b),
        (Kind::F64, 0xfff9_1357_2468_abcd),
    ] {
        cases.push(Case {
            name: format!("command-control-{kind:?}"),
            globals: vec![Global {
                kind,
                mutable: false,
                bits,
            }],
            writes: vec![],
            exported_accessors: false,
        });
    }
    for (kind, values) in [
        (Kind::I32, [0x8000_0000, 0xffff_ffff]),
        (Kind::I64, [0x8000_0000_0000_0000, 0xffff_ffff_ffff_ffff]),
        (Kind::F32, [0x8000_0000, 0x7f81_2345]),
        (Kind::F64, [0x8000_0000_0000_0000, 0x7ff0_1234_5678_9abc]),
    ] {
        for bits in values {
            cases.push(Case {
                name: format!("immutable-{kind:?}-{bits:016x}"),
                globals: vec![Global {
                    kind,
                    mutable: false,
                    bits,
                }],
                writes: vec![],
                exported_accessors: true,
            });
        }
    }
    for (kind, triples) in [
        (
            Kind::I32,
            [
                [0, 0x8000_0000, 0xffff_ffff],
                [127, 128, 0x7fff_ffff],
                [0x1357_9bdf, 0x2468_ace0, 0],
            ],
        ),
        (
            Kind::I64,
            [
                [0, 0x8000_0000_0000_0000, u64::MAX],
                [127, 128, 0x7fff_ffff_ffff_ffff],
                [0x1357_9bdf_2468_ace0, 0xfedc_ba98_7654_3210, 0],
            ],
        ),
        (
            Kind::F32,
            [
                [0, 0x8000_0000, 0x0000_0001],
                [0x7f80_0000, 0xff80_0000, 0x7fc1_872b],
                [0xff81_3579, 0x3f80_0000, 0x7f80_0001],
            ],
        ),
        (
            Kind::F64,
            [
                [0, 0x8000_0000_0000_0000, 1],
                [
                    0x7ff0_0000_0000_0000,
                    0xfff0_0000_0000_0000,
                    0x7ff8_2468_1357_9bdf,
                ],
                [
                    0xfff0_2468_1357_9bdf,
                    0x3ff0_0000_0000_0000,
                    0x7ff0_0000_0000_0001,
                ],
            ],
        ),
    ] {
        for [initial, first, last] in triples {
            cases.push(Case {
                name: format!("persistent-{kind:?}-{initial:016x}"),
                globals: vec![Global {
                    kind,
                    mutable: true,
                    bits: initial,
                }],
                writes: vec![(0, first), (0, last)],
                exported_accessors: true,
            });
        }
    }
    for (kind, initial, first, second) in [
        (Kind::I32, 0x1020_3040, 0x89ab_cdef, 0x7654_3210),
        (
            Kind::I64,
            0x1020_3040_5060_7080,
            0x89ab_cdef_0123_4567,
            0x7654_3210_fedc_ba98,
        ),
        (Kind::F32, 0x7f80_1234, 0xffc5_4321, 0x8000_0000),
        (
            Kind::F64,
            0x7ff0_1234_9876_5abc,
            0xfffa_bcde_7654_3210,
            0x8000_0000_0000_0000,
        ),
    ] {
        cases.push(Case {
            name: format!("isolation-{kind:?}"),
            globals: vec![
                Global {
                    kind: Kind::I32,
                    mutable: false,
                    bits: 0x51a7_c3e9,
                },
                Global {
                    kind,
                    mutable: true,
                    bits: initial,
                },
                Global {
                    kind,
                    mutable: true,
                    bits: second,
                },
                Global {
                    kind: Kind::F64,
                    mutable: false,
                    bits: 0xfff8_7654_3210_abcd,
                },
            ],
            writes: vec![(1, first), (2, initial), (1, second)],
            exported_accessors: true,
        });
    }
    assert_eq!(cases.len(), 28);
    cases
}

fn cases() -> Vec<Case> {
    // Exact original multi-export modules stay unsupported, before any runtime.
    let mut controls: Vec<Case> = baseline_shapes()
        .into_iter()
        .filter(|case| case.exported_accessors)
        .collect();
    assert_eq!(controls.len(), 24);
    // One exported function invokes private accessors across every state transition.
    let positives = baseline_shapes().into_iter().map(|mut case| {
        case.name = format!("single-entry-{}", case.name);
        case.exported_accessors = false;
        case
    });
    controls.extend(positives);
    assert_eq!(controls.len(), 52);
    controls
}

fn signed(mut value: i64, out: &mut Vec<u8>) {
    loop {
        let byte = (value & 0x7f) as u8;
        value >>= 7;
        let done = (value == 0 && byte & 0x40 == 0) || (value == -1 && byte & 0x40 != 0);
        out.push(byte | if done { 0 } else { 0x80 });
        if done {
            break;
        }
    }
}
fn i32_const(value: i32, out: &mut Vec<u8>) {
    out.push(0x41);
    signed(value as i64, out);
}
fn call(index: u32, out: &mut Vec<u8>) {
    out.push(0x10);
    out.extend(fixture::uint(index));
}
fn expected(case: &Case) -> Vec<u8> {
    let mut state: Vec<u64> = case.globals.iter().map(|g| g.bits).collect();
    let mut out = Vec::new();
    for step in 0..=case.writes.len() {
        if step > 0 {
            let (index, bits) = case.writes[step - 1];
            state[index] = bits;
        }
        for (g, bits) in case.globals.iter().zip(&state) {
            out.extend_from_slice(&bits.to_le_bytes()[..if g.kind.wide() { 8 } else { 4 }]);
        }
    }
    out
}
fn module(case: &Case) -> Vec<u8> {
    let mut f = fixture::Fixture::default();
    f.types.extend([
        fixture::signature(&[], &[Type::I64]),
        fixture::signature(&[Type::I32], &[]),
        fixture::signature(&[Type::I64], &[]),
    ]);
    f.function_types = vec![34];
    f.bodies = vec![Vec::new()];
    f.memory = vec![1, 1, 1, 1];
    f.table = vec![1, 0x70, 1, 1, 1];
    f.exports = vec![(b"memory".to_vec(), 2, 0), (b"_start".to_vec(), 0, 34)];
    let mut accessors = Vec::new();
    for (index, g) in case.globals.iter().enumerate() {
        let mut global = vec![fixture::type_byte(g.kind.ty()), u8::from(g.mutable)];
        g.kind.constant(g.bits, &mut global);
        global.push(0x0b);
        f.globals.push(global);
        let getter = 34 + f.bodies.len() as u32;
        let mut body = vec![0, 0x23];
        body.extend(fixture::uint(index as u32));
        g.kind.to_integer(&mut body);
        body.push(0x0b);
        f.bodies.push(body);
        f.function_types.push(if g.kind.wide() { 36 } else { 35 });
        if case.exported_accessors {
            f.exports
                .push((format!("read{index}").into_bytes(), 0, getter));
        }
        let setter = if g.mutable {
            let setter = 34 + f.bodies.len() as u32;
            let mut body = vec![0, 0x20, 0];
            g.kind.from_integer(&mut body);
            body.push(0x24);
            body.extend(fixture::uint(index as u32));
            body.push(0x0b);
            f.bodies.push(body);
            f.function_types.push(if g.kind.wide() { 38 } else { 37 });
            if case.exported_accessors {
                f.exports
                    .push((format!("write{index}").into_bytes(), 0, setter));
            }
            Some(setter)
        } else {
            None
        };
        accessors.push((getter, setter));
    }
    let mut driver = vec![0];
    let mut offset = 128;
    for step in 0..=case.writes.len() {
        if step > 0 {
            let (index, bits) = case.writes[step - 1];
            let kind = if case.globals[index].kind.wide() {
                Kind::I64
            } else {
                Kind::I32
            };
            kind.constant(bits, &mut driver);
            call(accessors[index].1.unwrap(), &mut driver);
        }
        for (g, (getter, _)) in case.globals.iter().zip(&accessors) {
            i32_const(offset, &mut driver);
            call(*getter, &mut driver);
            driver.extend([if g.kind.wide() { 0x37 } else { 0x36 }, 0, 0]);
            offset += if g.kind.wide() { 8 } else { 4 };
        }
    }
    for value in [1, 0, 1, 16] {
        i32_const(value, &mut driver);
    }
    let fd_write = f
        .imports
        .iter()
        .position(|(_, n, _, _)| n == b"fd_write")
        .unwrap();
    call(fd_write as u32, &mut driver);
    driver.extend([0x1a, 0x0b]);
    f.bodies[0] = driver;
    let mut iovec = 128u32.to_le_bytes().to_vec();
    iovec.extend(((offset - 128) as u32).to_le_bytes());
    f.data = vec![fixture::data_segment(0, &iovec)];
    f.bytes()
}
fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

// Only WebAssembly execution produces observations. Floats cross the JS boundary
// as reinterpreted integer values, preserving even signaling NaN payloads.
// https://webassembly.github.io/spec/core/exec/instructions.html#exec-global-get
// https://webassembly.github.io/spec/core/exec/instructions.html#exec-global-set
const ORACLE: &str = r#"
const fs = require('node:fs');
const [encoded, mode, widths, ...writes] = fs.readFileSync(0, 'utf8').trimEnd().split('\n');
const bytes = Buffer.from(encoded, 'hex');
if (!WebAssembly.validate(bytes)) throw new Error('node validation rejected');
const module_ = new WebAssembly.Module(bytes);
const wasi = Object.fromEntries(WebAssembly.Module.imports(module_).map(x => [x.name, () => { throw new Error('unexpected capability ' + x.name); }]));
let instance, output = null;
wasi.fd_write = (fd, ptr, count, written) => {
  if (fd !== 1 || ptr !== 0 || count !== 1 || written !== 16 || output !== null) throw new Error('ABI');
  const v = new DataView(instance.exports.memory.buffer);
  const start = v.getUint32(0, true), size = v.getUint32(4, true);
  if (start !== 128 || size > 512) throw new Error('output bounds');
  output = Buffer.from(instance.exports.memory.buffer, start, size).toString('hex');
  v.setUint32(16, size, true); return 0;
};
instance = new WebAssembly.Instance(module_, {wasi_snapshot_preview1: wasi});
if (mode === 'command') {
  instance.exports._start();
} else if (mode === 'exports') {
  const sizes = widths.split(',').map(Number), pieces = [];
  const snapshot = () => sizes.forEach((size, i) => {
    const value = instance.exports['read' + i]();
    const b = Buffer.alloc(size);
    if (size === 4) b.writeUInt32LE(value >>> 0); else b.writeBigUInt64LE(BigInt.asUintN(64, value));
    pieces.push(b);
  });
  snapshot();
  for (const line of writes) {
    const [index, raw] = line.split(':');
    const bits = BigInt('0x' + raw);
    instance.exports['write' + index](sizes[Number(index)] === 4 ? Number(BigInt.asIntN(32, bits)) : BigInt.asIntN(64, bits));
    snapshot();
  }
  output = Buffer.concat(pieces).toString('hex');
} else throw new Error('mode');
if (output === null) throw new Error('missing output');
console.log(output);
"#;

fn node_path() -> PathBuf {
    let path = match std::env::var_os("MIXER_NODE") {
        Some(explicit) => PathBuf::from(explicit),
        None => std::env::var_os("PATH")
            .and_then(|paths| {
                std::env::split_paths(&paths)
                    .map(|p| p.join("node"))
                    .find(|p| {
                        p.is_absolute()
                            && p.is_file()
                            && p.metadata()
                                .is_ok_and(|m| m.permissions().mode() & 0o111 != 0)
                    })
            })
            .expect("ENVIRONMENT_REJECTED: Node executable required"),
    };
    assert!(
        path.is_absolute()
            && path.is_file()
            && path
                .metadata()
                .is_ok_and(|m| m.permissions().mode() & 0o111 != 0),
        "ENVIRONMENT_REJECTED: explicit Node must be an absolute executable file"
    );
    path
}
fn isolated_case(index: usize, node: PathBuf, cases: &[Case]) {
    let case = &cases[index];
    let bytes = module(case);
    println!(
        "MODULE case={index} name={} exports={} hex={}",
        case.name,
        case.exported_accessors,
        hex(&bytes)
    );
    println!("WORKER case={index} pid={}", std::process::id());
    let widths = case
        .globals
        .iter()
        .map(|g| if g.kind.wide() { "8" } else { "4" })
        .collect::<Vec<_>>()
        .join(",");
    let mut input = format!(
        "{}\n{}\n{widths}\n",
        hex(&bytes),
        if case.exported_accessors {
            "exports"
        } else {
            "command"
        }
    );
    for (i, bits) in &case.writes {
        input.push_str(&format!("{i}:{bits:016x}\n"));
    }
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
    let pid = child.id();
    let written = child.stdin.take().unwrap().write_all(input.as_bytes());
    let output = child.wait_with_output().expect("UNKNOWN Node reap");
    written.expect("Node input");
    assert!(
        output.status.success(),
        "Node case={index}: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stderr.is_empty());
    let expected = expected(case);
    let oracle = String::from_utf8(output.stdout).unwrap();
    assert_eq!(
        oracle,
        format!("{}\n", hex(&expected)),
        "independent Node expectation case={index}"
    );
    println!(
        "ORACLE case={index} pid={pid} reaped=true observations={} bytes={}",
        (case.writes.len() + 1) * case.globals.len(),
        hex(&expected)
    );
    let validation = SwiftValidationBudget::default();
    let budget = SwiftRunBudget::default();
    let wasi = WasiBudget::default();
    println!("BUDGETS case={index} unchanged=true validation={validation:?} run={budget:?} wasi={wasi:?}");
    if case.exported_accessors {
        let failure = match validate_swift_command(&bytes, validation, &Cancellation::default()) {
            Ok(_) => panic!("unsupported multi-export ABI unexpectedly admitted"),
            Err(failure) => failure,
        };
        assert!(
            format!("{failure:?}").contains("code: \"swift_command_export_count\""),
            "wrong unsupported ABI diagnostic: {failure:?}"
        );
        println!("UNSUPPORTED_ABI case={index} stage=mixer-validation runtime_created=false diagnostic={failure:?}");
        return;
    }
    let proof = match validate_swift_command(&bytes, validation, &Cancellation::default()) {
        Ok(proof) => proof,
        Err(failure) => {
            println!("PRODUCT_FAILURE case={index} stage=mixer-validation runtime_created=false diagnostic={failure:?}");
            panic!("valid Node module rejected by consuming product case={index}: {failure:?}");
        }
    };
    println!("ADMITTED case={index}");
    let mut stdout = Vec::new();
    let mut stderr = Vec::new();
    let report = execute_swift_command(
        proof,
        budget,
        WasiGrants {
            stdout: true,
            ..Default::default()
        },
        wasi,
        Cancellation::default(),
        &mut stdout,
        &mut stderr,
    );
    assert!(
        report.cleanup_completed,
        "UNKNOWN consuming cleanup case={index}: {report:?}"
    );
    let usage = report.after_cleanup.expect("UNKNOWN terminal usage");
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
    assert_eq!(currents, [0; 14], "UNKNOWN ledger currents case={index}");
    assert_eq!(r.live_tickets, 0, "UNKNOWN ledger tickets case={index}");
    assert!(
        usage.cleanup_invariant.is_none(),
        "UNKNOWN ledger invariant case={index}"
    );
    println!("CLEANUP case={index} currents={currents:?} tickets=0 invariant=none");
    assert!(
        report.succeeded() && report.terminal.is_none() && !report.output_error,
        "product execution case={index}: {report:?}"
    );
    assert!(stderr.is_empty());
    assert_eq!(stdout, expected, "product bits case={index}");
    assert_eq!(report.calls_by_function.iter().sum::<u64>(), 1);
    println!(
        "PARITY case={index} observations={} bytes={}",
        (case.writes.len() + 1) * case.globals.len(),
        hex(&stdout)
    );
}
fn worker(selector: &str) -> Command {
    let mut command = Command::new(std::env::current_exe().unwrap());
    command
        .current_dir(std::env::current_dir().unwrap())
        .args([
            "--ignored",
            "--exact",
            TEST,
            "--nocapture",
            "--test-threads=1",
        ])
        .env(CASE_ENV, selector);
    command
}
fn rejected(label: &str, output: Output) {
    assert!(!output.status.success(), "invalid environment accepted");
    let mut bytes = output.stdout;
    bytes.extend(output.stderr);
    let text = String::from_utf8_lossy(&bytes);
    assert!(
        text.contains("ENVIRONMENT_REJECTED:"),
        "incorrect environment denial: {text}"
    );
    for marker in [
        "MODULE case=",
        "WORKER case=",
        "ORACLE case=",
        "ADMITTED case=",
        "CLEANUP case=",
    ] {
        assert!(
            !text.contains(marker),
            "environment reached payload: {text}"
        );
    }
    println!(
        "ENVIRONMENT_FAIL_CLOSED control={label} status={}",
        output.status
    );
}

#[test]
#[ignore = "development Node oracle; explicit experimental-swift-reactor corpus"]
fn globals_match_node() {
    let cases = cases();
    let selected = match std::env::var(CASE_ENV) {
        Ok(raw) => {
            let index = raw
                .parse::<usize>()
                .expect("ENVIRONMENT_REJECTED: invalid selector");
            assert!(
                index < cases.len() && raw == index.to_string(),
                "ENVIRONMENT_REJECTED: noncanonical selector"
            );
            Some(index)
        }
        Err(std::env::VarError::NotPresent) => None,
        Err(_) => panic!("ENVIRONMENT_REJECTED: non-Unicode selector"),
    };
    let node = node_path();
    if let Some(index) = selected {
        isolated_case(index, node, &cases);
        return;
    }
    for invalid in [
        "",
        "-1",
        "52",
        "01",
        "+1",
        " 1",
        "not-an-index",
        "184467440737095516160",
    ] {
        rejected(
            "selector",
            worker(invalid).output().expect("UNKNOWN environment child"),
        );
    }
    rejected(
        "non-Unicode",
        worker("0")
            .env(CASE_ENV, std::ffi::OsString::from_vec(vec![0xff]))
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
    for invalid in [
        PathBuf::new(),
        PathBuf::from("relative-node"),
        PathBuf::from("/mixer-globals-r2846-missing-node"),
        PathBuf::from("/"),
        std::env::current_dir().unwrap().join("Cargo.toml"),
    ] {
        rejected(
            "explicit-node",
            worker("0")
                .env("MIXER_NODE", invalid)
                .env("PATH", node.parent().unwrap())
                .output()
                .expect("UNKNOWN environment child"),
        );
    }
    let mut failures = 0;
    for index in 0..cases.len() {
        let mut command = worker(&index.to_string());
        // Exercise fallback only when the override is unset. Poisoned Node env
        // must be removed by the oracle command, never inherited into Node.
        command
            .env("NODE_OPTIONS", "--mixer-invalid-option-r2846")
            .env("NODE_PATH", "/mixer-invalid-node-path-r2846");
        if index == cases.len() - 1 {
            command
                .env_remove("MIXER_NODE")
                .env("PATH", node.parent().unwrap());
        } else {
            command.env("MIXER_NODE", &node);
        }
        let pid;
        let output = {
            let child = command
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .spawn()
                .expect("UNKNOWN worker spawn");
            pid = child.id();
            child.wait_with_output().expect("UNKNOWN worker reap")
        };
        print!("{}", String::from_utf8_lossy(&output.stdout));
        let diagnostics = String::from_utf8_lossy(&output.stderr);
        println!(
            "WORKER_TERMINAL case={index} pid={pid} reaped=true status={}",
            output.status
        );
        assert!(
            !diagnostics.contains("UNKNOWN"),
            "UNKNOWN worker ledger or custody case={index}: {diagnostics}"
        );
        if !output.status.success() {
            eprint!("{diagnostics}");
            failures += 1;
        } else {
            assert!(output.stderr.is_empty());
            let text = String::from_utf8_lossy(&output.stdout);
            if cases[index].exported_accessors {
                assert!(text.contains(&format!("UNSUPPORTED_ABI case={index} ")));
                assert!(!text.contains("ADMITTED case="));
                assert!(!text.contains("CLEANUP case="));
            } else {
                assert!(text.contains(&format!("CLEANUP case={index} ")));
                assert!(text.contains(&format!("PARITY case={index} ")));
            }
        }
    }
    println!(
        "CORPUS modules={} unsupported_abi=24 positives=28 product_failures={failures} environment_denials=15",
        cases.len()
    );
    assert_eq!(
        failures, 0,
        "valid globals corpus has product failures; no assertion relaxed"
    );
}
