#![cfg(feature = "experimental-swift-reactor")]

#[path = "swift_reactor_validation_fixture.rs"]
mod fixture;

use mixer_vm::experimental_swift_reactor::{
    execute_swift_command, validate_swift_command, SwiftRunBudget, SwiftValidationBudget,
};
use mixer_vm::experimental_wasi::{WasiBudget, WasiGrants};
use mixer_vm::Cancellation;
use std::io::Write;
use std::os::unix::{ffi::OsStringExt, fs::PermissionsExt};
use std::path::PathBuf;
use std::process::{Command, Output, Stdio};

const TEST: &str = "float_comparisons_match_node";
const CASE_ENV: &str = "MIXER_DIFFERENTIAL_FLOAT_COMPARISONS_CASE";

// Independently authored bit patterns. Each ordered pair is significant:
// adjacent positive and negative values run in both directions, while identical
// NaN bit patterns must compare unequal. No host floating operation is an oracle.
const FINITE32: &[(u64, u64)] = &[
    (0, 0x80000000),
    (0x80000000, 0),
    (0x3f800000, 0x3f800000),
    (0x3f800000, 0x3f800001),
    (0x3f800001, 0x3f800000),
    (0xbf800000, 0xbf800001),
    (0xbf800001, 0xbf800000),
    (0x00800000, 0x007fffff),
    (0x007fffff, 0x00800000),
    (1, 0),
    (0x80000001, 0x80000000),
    (0xbf800000, 0x3f800000),
];
const FINITE64: &[(u64, u64)] = &[
    (0, 0x8000000000000000),
    (0x8000000000000000, 0),
    (0x3ff0000000000000, 0x3ff0000000000000),
    (0x3ff0000000000000, 0x3ff0000000000001),
    (0x3ff0000000000001, 0x3ff0000000000000),
    (0xbff0000000000000, 0xbff0000000000001),
    (0xbff0000000000001, 0xbff0000000000000),
    (0x0010000000000000, 0x000fffffffffffff),
    (0x000fffffffffffff, 0x0010000000000000),
    (1, 0),
    (0x8000000000000001, 0x8000000000000000),
    (0xbff0000000000000, 0x3ff0000000000000),
];
const EXCEPTIONAL32: &[(u64, u64)] = &[
    (0x7f800000, 0x7f800000),
    (0xff800000, 0xff800000),
    (0xff800000, 0x7f800000),
    (0x7f800000, 0xff800000),
    (0x7f7fffff, 0x7f800000),
    (0xff800000, 0xff7fffff),
    (0x7fc12345, 0x3f800000),
    (0x3f800000, 0xffc23456),
    (0x7f812345, 0xbf800000),
    (0xbf800000, 0xff823456),
    (0x7fc12345, 0x7fc12345),
    (0x7f812345, 0x7f812345),
    (0x7fc12345, 0xff823456),
    (0x7f812345, 0xffc23456),
    (0x7f800000, 0xffc23456),
    (0xff823456, 0xff800000),
];
const EXCEPTIONAL64: &[(u64, u64)] = &[
    (0x7ff0000000000000, 0x7ff0000000000000),
    (0xfff0000000000000, 0xfff0000000000000),
    (0xfff0000000000000, 0x7ff0000000000000),
    (0x7ff0000000000000, 0xfff0000000000000),
    (0x7fefffffffffffff, 0x7ff0000000000000),
    (0xfff0000000000000, 0xffefffffffffffff),
    (0x7ff8123456789abc, 0x3ff0000000000000),
    (0x3ff0000000000000, 0xfff823456789abcd),
    (0x7ff0123456789abc, 0xbff0000000000000),
    (0xbff0000000000000, 0xfff023456789abcd),
    (0x7ff8123456789abc, 0x7ff8123456789abc),
    (0x7ff0123456789abc, 0x7ff0123456789abc),
    (0x7ff8123456789abc, 0xfff023456789abcd),
    (0x7ff0123456789abc, 0xfff823456789abcd),
    (0x7ff0000000000000, 0xfff823456789abcd),
    (0xfff023456789abcd, 0xfff0000000000000),
];

// Literal i32 results from the official feq/fne/flt/fgt/fle/fge semantics:
// https://webassembly.github.io/spec/core/exec/numerics.html#op-feq
// Opposite signed zeroes are equal. Either NaN makes ne true and all others false.
const EQ_FINITE: &[i32] = &[1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0];
const NE_FINITE: &[i32] = &[0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1];
const LT_FINITE: &[i32] = &[0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1];
const GT_FINITE: &[i32] = &[0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0];
const LE_FINITE: &[i32] = &[1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1];
const GE_FINITE: &[i32] = &[1, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0];
const EQ_EXCEPTIONAL: &[i32] = &[1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
const NE_EXCEPTIONAL: &[i32] = &[0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1];
const LT_EXCEPTIONAL: &[i32] = &[0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
const GT_EXCEPTIONAL: &[i32] = &[0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
const LE_EXCEPTIONAL: &[i32] = &[1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
const GE_EXCEPTIONAL: &[i32] = &[1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];

struct Case {
    name: &'static str,
    opcode: u8,
    inputs: &'static [(u64, u64)],
    expected: &'static [i32],
}
const CASES: [Case; 24] = [
    Case {
        name: "f32.eq-finite",
        opcode: 0x5b,
        inputs: FINITE32,
        expected: EQ_FINITE,
    },
    Case {
        name: "f32.eq-unordered",
        opcode: 0x5b,
        inputs: EXCEPTIONAL32,
        expected: EQ_EXCEPTIONAL,
    },
    Case {
        name: "f32.ne-finite",
        opcode: 0x5c,
        inputs: FINITE32,
        expected: NE_FINITE,
    },
    Case {
        name: "f32.ne-unordered",
        opcode: 0x5c,
        inputs: EXCEPTIONAL32,
        expected: NE_EXCEPTIONAL,
    },
    Case {
        name: "f32.lt-finite",
        opcode: 0x5d,
        inputs: FINITE32,
        expected: LT_FINITE,
    },
    Case {
        name: "f32.lt-unordered",
        opcode: 0x5d,
        inputs: EXCEPTIONAL32,
        expected: LT_EXCEPTIONAL,
    },
    Case {
        name: "f32.gt-finite",
        opcode: 0x5e,
        inputs: FINITE32,
        expected: GT_FINITE,
    },
    Case {
        name: "f32.gt-unordered",
        opcode: 0x5e,
        inputs: EXCEPTIONAL32,
        expected: GT_EXCEPTIONAL,
    },
    Case {
        name: "f32.le-finite",
        opcode: 0x5f,
        inputs: FINITE32,
        expected: LE_FINITE,
    },
    Case {
        name: "f32.le-unordered",
        opcode: 0x5f,
        inputs: EXCEPTIONAL32,
        expected: LE_EXCEPTIONAL,
    },
    Case {
        name: "f32.ge-finite",
        opcode: 0x60,
        inputs: FINITE32,
        expected: GE_FINITE,
    },
    Case {
        name: "f32.ge-unordered",
        opcode: 0x60,
        inputs: EXCEPTIONAL32,
        expected: GE_EXCEPTIONAL,
    },
    Case {
        name: "f64.eq-finite",
        opcode: 0x61,
        inputs: FINITE64,
        expected: EQ_FINITE,
    },
    Case {
        name: "f64.eq-unordered",
        opcode: 0x61,
        inputs: EXCEPTIONAL64,
        expected: EQ_EXCEPTIONAL,
    },
    Case {
        name: "f64.ne-finite",
        opcode: 0x62,
        inputs: FINITE64,
        expected: NE_FINITE,
    },
    Case {
        name: "f64.ne-unordered",
        opcode: 0x62,
        inputs: EXCEPTIONAL64,
        expected: NE_EXCEPTIONAL,
    },
    Case {
        name: "f64.lt-finite",
        opcode: 0x63,
        inputs: FINITE64,
        expected: LT_FINITE,
    },
    Case {
        name: "f64.lt-unordered",
        opcode: 0x63,
        inputs: EXCEPTIONAL64,
        expected: LT_EXCEPTIONAL,
    },
    Case {
        name: "f64.gt-finite",
        opcode: 0x64,
        inputs: FINITE64,
        expected: GT_FINITE,
    },
    Case {
        name: "f64.gt-unordered",
        opcode: 0x64,
        inputs: EXCEPTIONAL64,
        expected: GT_EXCEPTIONAL,
    },
    Case {
        name: "f64.le-finite",
        opcode: 0x65,
        inputs: FINITE64,
        expected: LE_FINITE,
    },
    Case {
        name: "f64.le-unordered",
        opcode: 0x65,
        inputs: EXCEPTIONAL64,
        expected: LE_EXCEPTIONAL,
    },
    Case {
        name: "f64.ge-finite",
        opcode: 0x66,
        inputs: FINITE64,
        expected: GE_FINITE,
    },
    Case {
        name: "f64.ge-unordered",
        opcode: 0x66,
        inputs: EXCEPTIONAL64,
        expected: GE_EXCEPTIONAL,
    },
];

fn width(case: &Case) -> usize {
    match case.opcode {
        0x5b..=0x60 => 4,
        0x61..=0x66 => 8,
        _ => panic!("unsupported comparison instruction"),
    }
}

fn module(case: &Case) -> Vec<u8> {
    assert_eq!(case.inputs.len(), case.expected.len());
    let mut f = fixture::Fixture::default();
    f.function_types = vec![34];
    f.memory = vec![1, 1, 1, 1];
    f.table = vec![1, 0x70, 1, 1, 1];
    f.exports = vec![(b"memory".to_vec(), 2, 0), (b"_start".to_vec(), 0, 34)];
    let fd_write = f
        .imports
        .iter()
        .position(|(_, n, _, _)| n == b"fd_write")
        .unwrap();
    let w = width(case);
    let mut body = vec![0];
    for (i, &(a, b)) in case.inputs.iter().enumerate() {
        body.push(0x41);
        body.extend(fixture::signed((32 + 4 * i) as i32));
        for bits in [a, b] {
            assert!(w == 8 || bits <= u32::MAX as u64);
            body.push(if w == 4 { 0x43 } else { 0x44 });
            body.extend_from_slice(&bits.to_le_bytes()[..w]);
        }
        body.extend([case.opcode, 0x36, 0, 0]); // comparison returns i32
    }
    for value in [1, 0, 1, 16] {
        body.push(0x41);
        body.extend(fixture::signed(value));
    }
    body.push(0x10);
    body.extend(fixture::uint(fd_write as u32));
    body.extend([0x1a, 0x0b]);
    f.bodies = vec![body];
    let mut iovec = 32u32.to_le_bytes().to_vec();
    iovec.extend((4 * case.inputs.len() as u32).to_le_bytes());
    f.data = vec![fixture::data_segment(0, &iovec)];
    f.bytes()
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

// Node executes the exact Wasm, with constants kept in Wasm (including sNaNs).
// JavaScript only supplies fd_write and reads the resulting i32 memory slots.
const ORACLE: &str = r#"
const fs = require('node:fs');
const [countText, encoded] = fs.readFileSync(0, 'utf8').split('\n');
const count = Number(countText);
if (!Number.isInteger(count) || count < 1 || count > 16) throw Error('count');
const bytes = Buffer.from(encoded, 'hex');
if (!WebAssembly.validate(bytes)) throw Error('REJECTION stage=node-validation');
const module = new WebAssembly.Module(bytes);
const wasi = Object.fromEntries(WebAssembly.Module.imports(module).map(x =>
    [x.name, () => { throw Error('unexpected import ' + x.name); }]));
let instance, results;
wasi.fd_write = (fd, ptr, n, written) => {
    if (fd !== 1 || ptr !== 0 || n !== 1 || written !== 16 || results !== undefined)
        throw Error('output ABI');
    const view = new DataView(instance.exports.memory.buffer);
    if (view.getUint32(0, true) !== 32 || view.getUint32(4, true) !== count * 4)
        throw Error('iovec');
    results = Array.from({length: count}, (_, i) => view.getInt32(32 + i * 4, true));
    if (results.some(x => x !== 0 && x !== 1)) throw Error('nonboolean comparison');
    view.setUint32(written, count * 4, true);
    return 0;
};
instance = new WebAssembly.Instance(module, {wasi_snapshot_preview1: wasi});
instance.exports._start();
if (results === undefined) throw Error('missing output');
console.log(results.join(','));
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

fn isolated_case(index: usize, node: PathBuf) {
    let case = &CASES[index];
    let bytes = module(case);
    println!(
        "MODULE case={index} name={} opcode={:02x} inputs={:?} hex={}",
        case.name,
        case.opcode,
        case.inputs,
        hex(&bytes)
    );
    println!(
        "WORKER case={index} pid={} consuming_runtimes=1",
        std::process::id()
    );
    let mut child = Command::new(node)
        .current_dir(std::env::current_dir().unwrap())
        .env_remove("NODE_OPTIONS")
        .env_remove("NODE_PATH")
        .args(["-e", ORACLE])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("ENVIRONMENT_REJECTED: Node launch failed");
    let node_pid = child.id();
    let write = child
        .stdin
        .take()
        .unwrap()
        .write_all(format!("{}\n{}", case.inputs.len(), hex(&bytes)).as_bytes());
    let output = child.wait_with_output().expect("UNKNOWN Node reap/output");
    write.expect("Node transport failed");
    assert!(
        output.status.success(),
        "Node case={index}: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stderr.is_empty());
    let text = String::from_utf8(output.stdout).unwrap();
    let oracle: Vec<i32> = text
        .strip_suffix('\n')
        .unwrap()
        .split(',')
        .map(|s| s.parse().expect("Node i32 comparison result"))
        .collect();
    assert_eq!(
        oracle, case.expected,
        "official semantics versus Node case={index}"
    );
    println!("ORACLE case={index} pid={node_pid} reaped=true i32={oracle:?}");

    let validation = SwiftValidationBudget::default();
    let run = SwiftRunBudget::default();
    let wasi = WasiBudget::default();
    println!(
        "BUDGETS case={index} unchanged=true validation={validation:?} run={run:?} wasi={wasi:?}"
    );
    let proof = validate_swift_command(&bytes, validation, &Cancellation::default())
        .unwrap_or_else(|failure| {
            panic!("REJECTION stage=mixer-validation case={index}: {failure:?}")
        });
    println!("ADMITTED case={index} stage=mixer-validation");
    let mut stdout = vec![];
    let mut stderr = vec![];
    let report = execute_swift_command(
        proof,
        run,
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
    assert_eq!(
        currents, [0; 14],
        "UNKNOWN reservation cleanup case={index}"
    );
    assert_eq!(r.live_tickets, 0, "UNKNOWN tickets case={index}");
    assert!(
        usage.cleanup_invariant.is_none(),
        "UNKNOWN cleanup invariant case={index}"
    );
    println!("CLEANUP case={index} currents={currents:?} tickets=0 invariant=none");
    assert!(report.succeeded(), "case={index}: {report:?}");
    assert!(report.terminal.is_none());
    assert!(!report.output_error);
    assert!(stderr.is_empty());
    assert_eq!(stdout.len(), 4 * case.inputs.len());
    let actual: Vec<i32> = stdout
        .chunks_exact(4)
        .map(|b| i32::from_le_bytes(b.try_into().unwrap()))
        .collect();
    for (item, ((&value, &node_value), &(a, b))) in
        actual.iter().zip(&oracle).zip(case.inputs).enumerate()
    {
        assert_eq!(value, node_value, "Node parity case={index} item={item}");
        assert_eq!(
            value, case.expected[item],
            "official result case={index} item={item}"
        );
        println!("SCALAR case={index} item={item} a={a:016x} b={b:016x} expected={} node={node_value} mixer={value}", case.expected[item]);
    }
    assert_eq!(report.calls_by_function.iter().sum::<u64>(), 1);
    println!(
        "PARITY case={index} name={} results={} bytes={}",
        case.name,
        actual.len(),
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

fn rejected(control: &str, output: Output) {
    assert!(!output.status.success(), "invalid environment accepted");
    let mut combined = output.stdout;
    combined.extend(output.stderr);
    let text = String::from_utf8_lossy(&combined);
    assert!(
        text.contains("ENVIRONMENT_REJECTED:"),
        "wrong rejection: {text}"
    );
    for marker in [
        "MODULE case=",
        "WORKER case=",
        "ADMITTED case=",
        "CLEANUP case=",
    ] {
        assert!(
            !text.contains(marker),
            "environment executed payload: {text}"
        );
    }
    println!(
        "ENVIRONMENT_FAIL_CLOSED control={control:?} status={} output={text}",
        output.status
    );
}

// One discoverable parent; every helper reenters once and consumes one runtime.
#[test]
#[ignore = "development Node oracle; explicit experimental-swift-reactor corpus"]
fn float_comparisons_match_node() {
    let selector = match std::env::var(CASE_ENV) {
        Ok(raw) => {
            let index = raw
                .parse::<usize>()
                .expect("ENVIRONMENT_REJECTED: invalid case index");
            assert!(
                index < CASES.len() && raw == index.to_string(),
                "ENVIRONMENT_REJECTED: noncanonical case index"
            );
            Some(index)
        }
        Err(std::env::VarError::NotPresent) => None,
        Err(_) => panic!("ENVIRONMENT_REJECTED: non-Unicode case index"),
    };
    let node = node_path();
    if let Some(index) = selector {
        println!(
            "NODE_SELECTED case={index} mode={} path={}",
            if std::env::var_os("MIXER_NODE").is_some() {
                "explicit"
            } else {
                "PATH"
            },
            node.display()
        );
        isolated_case(index, node);
        return;
    }
    let mut distinct = std::collections::BTreeSet::new();
    for case in &CASES {
        assert!(distinct.insert(module(case)), "duplicate Wasm module");
    }
    for invalid in [
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
            invalid,
            worker(invalid)
                .output()
                .expect("UNKNOWN selector-control subprocess"),
        );
    }
    rejected(
        "non-Unicode-selector",
        worker("0")
            .env(CASE_ENV, std::ffi::OsString::from_vec(vec![0xff]))
            .output()
            .expect("UNKNOWN selector-control subprocess"),
    );
    rejected(
        "missing-node",
        worker("0")
            .env_remove("MIXER_NODE")
            .env("PATH", "")
            .output()
            .expect("UNKNOWN missing-Node subprocess"),
    );
    for invalid in [
        PathBuf::new(),
        PathBuf::from("relative-node"),
        PathBuf::from("/mixer-float-comparisons-missing-node"),
        PathBuf::from("/"),
        std::env::current_dir().unwrap().join("Cargo.toml"),
    ] {
        rejected(
            "invalid-explicit-node",
            worker("0")
                .env("MIXER_NODE", invalid)
                .env("PATH", node.parent().unwrap())
                .output()
                .expect("UNKNOWN invalid-Node subprocess"),
        );
    }
    for index in 0..CASES.len() {
        let mut command = worker(&index.to_string());
        if index == CASES.len() - 1 {
            command
                .env_remove("MIXER_NODE")
                .env("PATH", node.parent().unwrap());
        } else {
            command.env("MIXER_NODE", &node);
            if index == 0 {
                command.env("PATH", "");
            }
        }
        let output = command
            .output()
            .expect("UNKNOWN float-comparisons subprocess");
        print!("{}", String::from_utf8_lossy(&output.stdout));
        assert!(
            output.status.success(),
            "case={index}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(output.stderr.is_empty());
        let text = String::from_utf8_lossy(&output.stdout);
        assert!(text.contains(&format!("CLEANUP case={index} ")));
        assert!(text.contains(&format!("PARITY case={index} ")));
    }
    println!("24 original float-comparison modules; 336 exact i32 results; 14 zero currents and 0 tickets each; 15 environment controls rejected; explicit override and unset-only PATH discovery exercised");
}
