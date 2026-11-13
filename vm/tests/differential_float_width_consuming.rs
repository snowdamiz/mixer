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

const TEST: &str = "float_width_and_reinterpret_matches_node";
const CASE_ENV: &str = "MIXER_DIFFERENTIAL_FLOAT_WIDTH_CASE";
#[derive(Clone, Copy, Debug)]
enum Expected {
    Bits(u64),
    CanonicalNaN,
    ArithmeticNaN,
}
struct Case {
    name: &'static str,
    opcode: u8,
    input: u64,
    expected: Expected,
}
// Original Core modules and exact literals. Demotion uses nearest ties-to-even;
// canonical NaNs remain canonical (either sign); other conversion NaNs may be
// any arithmetic NaN. Reinterpretation always preserves every payload/sign bit.
// https://webassembly.github.io/spec/core/exec/numerics.html#op-demote
// https://webassembly.github.io/spec/core/exec/numerics.html#op-promote
// https://webassembly.github.io/spec/core/exec/numerics.html#op-reinterpret
const CASES: [Case; 32] = [
    Case {
        name: "demote-positive-zero",
        opcode: 0xb6,
        input: 0x0000000000000000,
        expected: Expected::Bits(0),
    },
    Case {
        name: "demote-negative-zero",
        opcode: 0xb6,
        input: 0x8000000000000000,
        expected: Expected::Bits(0x80000000),
    },
    Case {
        name: "demote-exact-min-subnormal",
        opcode: 0xb6,
        input: 0x36a0000000000000,
        expected: Expected::Bits(1),
    },
    Case {
        name: "demote-negative-half-subnormal-tie-even",
        opcode: 0xb6,
        input: 0xb690000000000000,
        expected: Expected::Bits(0x80000000),
    },
    Case {
        name: "demote-normal-tie-even-lower",
        opcode: 0xb6,
        input: 0x3ff0000010000000,
        expected: Expected::Bits(0x3f800000),
    },
    Case {
        name: "demote-normal-tie-even-upper",
        opcode: 0xb6,
        input: 0x3ff0000030000000,
        expected: Expected::Bits(0x3f800002),
    },
    Case {
        name: "demote-positive-infinity",
        opcode: 0xb6,
        input: 0x7ff0000000000000,
        expected: Expected::Bits(0x7f800000),
    },
    Case {
        name: "demote-negative-canonical-nan",
        opcode: 0xb6,
        input: 0xfff8000000000000,
        expected: Expected::CanonicalNaN,
    },
    Case {
        name: "demote-signalling-payload-nan",
        opcode: 0xb6,
        input: 0x7ff0000000000042,
        expected: Expected::ArithmeticNaN,
    },
    Case {
        name: "promote-positive-zero",
        opcode: 0xbb,
        input: 0,
        expected: Expected::Bits(0),
    },
    Case {
        name: "promote-negative-zero",
        opcode: 0xbb,
        input: 0x80000000,
        expected: Expected::Bits(0x8000000000000000),
    },
    Case {
        name: "promote-min-subnormal",
        opcode: 0xbb,
        input: 1,
        expected: Expected::Bits(0x36a0000000000000),
    },
    Case {
        name: "promote-negative-normal",
        opcode: 0xbb,
        input: 0xc1200000,
        expected: Expected::Bits(0xc024000000000000),
    },
    Case {
        name: "promote-negative-infinity",
        opcode: 0xbb,
        input: 0xff800000,
        expected: Expected::Bits(0xfff0000000000000),
    },
    Case {
        name: "promote-canonical-nan",
        opcode: 0xbb,
        input: 0x7fc00000,
        expected: Expected::CanonicalNaN,
    },
    Case {
        name: "promote-negative-signalling-payload-nan",
        opcode: 0xbb,
        input: 0xff812345,
        expected: Expected::ArithmeticNaN,
    },
    Case {
        name: "i32-reinterpret-negative-zero",
        opcode: 0xbc,
        input: 0x80000000,
        expected: Expected::Bits(0x80000000),
    },
    Case {
        name: "i32-reinterpret-min-subnormal",
        opcode: 0xbc,
        input: 1,
        expected: Expected::Bits(1),
    },
    Case {
        name: "i32-reinterpret-positive-signalling-nan",
        opcode: 0xbc,
        input: 0x7f812345,
        expected: Expected::Bits(0x7f812345),
    },
    Case {
        name: "i32-reinterpret-negative-quiet-nan",
        opcode: 0xbc,
        input: 0xffc54321,
        expected: Expected::Bits(0xffc54321),
    },
    Case {
        name: "i64-reinterpret-negative-zero",
        opcode: 0xbd,
        input: 0x8000000000000000,
        expected: Expected::Bits(0x8000000000000000),
    },
    Case {
        name: "i64-reinterpret-min-subnormal",
        opcode: 0xbd,
        input: 1,
        expected: Expected::Bits(1),
    },
    Case {
        name: "i64-reinterpret-positive-signalling-nan",
        opcode: 0xbd,
        input: 0x7ff0123456789abc,
        expected: Expected::Bits(0x7ff0123456789abc),
    },
    Case {
        name: "i64-reinterpret-negative-quiet-nan",
        opcode: 0xbd,
        input: 0xfff8fedcba987654,
        expected: Expected::Bits(0xfff8fedcba987654),
    },
    Case {
        name: "f32-reinterpret-negative-zero",
        opcode: 0xbe,
        input: 0x80000000,
        expected: Expected::Bits(0x80000000),
    },
    Case {
        name: "f32-reinterpret-min-subnormal",
        opcode: 0xbe,
        input: 1,
        expected: Expected::Bits(1),
    },
    Case {
        name: "f32-reinterpret-positive-signalling-nan",
        opcode: 0xbe,
        input: 0x7f854321,
        expected: Expected::Bits(0x7f854321),
    },
    Case {
        name: "f32-reinterpret-negative-quiet-nan",
        opcode: 0xbe,
        input: 0xffc12345,
        expected: Expected::Bits(0xffc12345),
    },
    Case {
        name: "f64-reinterpret-negative-zero",
        opcode: 0xbf,
        input: 0x8000000000000000,
        expected: Expected::Bits(0x8000000000000000),
    },
    Case {
        name: "f64-reinterpret-min-subnormal",
        opcode: 0xbf,
        input: 1,
        expected: Expected::Bits(1),
    },
    Case {
        name: "f64-reinterpret-positive-signalling-nan",
        opcode: 0xbf,
        input: 0x7ff0fedcba987654,
        expected: Expected::Bits(0x7ff0fedcba987654),
    },
    Case {
        name: "f64-reinterpret-negative-quiet-nan",
        opcode: 0xbf,
        input: 0xfff8123456789abc,
        expected: Expected::Bits(0xfff8123456789abc),
    },
];
fn width(case: &Case) -> usize {
    match case.opcode {
        0xb6 | 0xbc | 0xbe => 4,
        0xbb | 0xbd | 0xbf => 8,
        _ => panic!("unsupported width/reinterpret opcode"),
    }
}
// Signed LEB for the full i64.const domain; the shared fixture helper is i32-only.
fn signed_i64(mut value: i64) -> Vec<u8> {
    let mut bytes = Vec::new();
    loop {
        let byte = (value as u8) & 0x7f;
        value >>= 7;
        let done = (value == 0 && byte & 0x40 == 0) || (value == -1 && byte & 0x40 != 0);
        bytes.push(if done { byte } else { byte | 0x80 });
        if done {
            return bytes;
        }
    }
}

fn module(case: &Case) -> Vec<u8> {
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
    let mut body = vec![0, 0x41, 32];
    match case.opcode {
        0xb6 | 0xbd => {
            body.push(0x44);
            body.extend(case.input.to_le_bytes());
        }
        0xbb | 0xbc => {
            body.push(0x43);
            body.extend((case.input as u32).to_le_bytes());
        }
        0xbe => {
            body.push(0x41);
            body.extend(fixture::signed(case.input as u32 as i32));
        }
        0xbf => {
            body.push(0x42);
            body.extend(signed_i64(case.input as i64));
        }
        _ => unreachable!(),
    }
    let store = match case.opcode {
        0xb6 | 0xbe => 0x38,
        0xbb | 0xbf => 0x39,
        0xbc => 0x36,
        0xbd => 0x37,
        _ => unreachable!(),
    };
    body.extend([case.opcode, store, 0, 0]);
    for value in [1, 0, 1, 16] {
        body.push(0x41);
        body.extend(fixture::signed(value));
    }
    body.push(0x10);
    body.extend(fixture::uint(fd_write as u32));
    body.extend([0x1a, 0x0b]);
    f.bodies = vec![body];
    let mut iovec = 32u32.to_le_bytes().to_vec();
    iovec.extend((width(case) as u32).to_le_bytes());
    f.data = vec![fixture::data_segment(0, &iovec)];
    f.bytes()
}
fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

// Node's WebAssembly engine executes the module; DataView reads memory bits.
// No JS floating arithmetic or test-derived interpreter supplies the oracle.
const ORACLE: &str = r#"
const fs = require('node:fs');
const [width, encoded] = fs.readFileSync(0, 'utf8').split('\n');
if (!['4', '8'].includes(width)) throw new Error('format');
const bytes = Buffer.from(encoded, 'hex');
if (!WebAssembly.validate(bytes)) throw new Error('REJECTION stage=node-validation');
const m = new WebAssembly.Module(bytes);
const wasi = Object.fromEntries(WebAssembly.Module.imports(m).map(x =>
  [x.name, () => { throw new Error('unexpected import ' + x.name); }]));
let instance, value = null;
wasi.fd_write = (fd, ptr, count, written) => {
  if (fd !== 1 || ptr !== 0 || count !== 1 || written !== 16 || value !== null)
    throw new Error('unexpected output ABI');
  const view = new DataView(instance.exports.memory.buffer);
  if (view.getUint32(ptr, true) !== 32 || view.getUint32(ptr + 4, true) !== Number(width))
    throw new Error('unexpected iovec');
  value = (width === '4' ? view.getUint32(32, true) : view.getBigUint64(32, true)).toString();
  view.setUint32(written, Number(width), true); return 0;
};
instance = new WebAssembly.Instance(m, {wasi_snapshot_preview1: wasi});
instance.exports._start();
if (value === null) throw new Error('missing output');
console.log(value);
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

fn classified(case: &Case, bits: u64) -> String {
    let (signless, exponent, fraction, quiet) = if width(case) == 4 {
        assert!(bits <= u32::MAX as u64);
        (bits & 0x7fffffff, 0x7f800000, 0x007fffff, 0x00400000)
    } else {
        (
            bits & 0x7fffffffffffffff,
            0x7ff0000000000000,
            0x000fffffffffffff,
            0x0008000000000000,
        )
    };
    match case.expected {
        Expected::Bits(expected) => {
            assert_eq!(bits, expected, "{} bit-exact result", case.name);
            format!("bits:{bits:016x}")
        }
        Expected::CanonicalNaN => {
            assert_eq!(
                signless,
                exponent | quiet,
                "{} canonical NaN class",
                case.name
            );
            "canonical-nan".into()
        }
        Expected::ArithmeticNaN => {
            assert_eq!(signless & exponent, exponent, "{} NaN exponent", case.name);
            assert_ne!(
                signless & fraction & quiet,
                0,
                "{} arithmetic NaN quiet bit",
                case.name
            );
            "arithmetic-nan".into()
        }
    }
}

fn isolated_case(index: usize, node: PathBuf) {
    let case = &CASES[index];
    let bytes = module(case);
    println!(
        "MODULE case={index} name={} opcode={:02x} input={:016x} expected={:?} hex={}",
        case.name,
        case.opcode,
        case.input,
        case.expected,
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
    let pid = child.id();
    let write = child
        .stdin
        .take()
        .unwrap()
        .write_all(format!("{}\n{}", width(case), hex(&bytes)).as_bytes());
    let output = child.wait_with_output().expect("UNKNOWN Node reap/output");
    write.expect("Node module transport failed");
    assert!(
        output.status.success(),
        "Node case={index}: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stderr.is_empty());
    let oracle = String::from_utf8(output.stdout).unwrap();
    let oracle_bits: u64 = oracle
        .strip_suffix('\n')
        .unwrap()
        .parse()
        .expect("Node bit result");
    let oracle_class = classified(case, oracle_bits);
    println!(
        "ORACLE case={index} pid={pid} reaped=true bits={oracle_bits:016x} class={oracle_class}"
    );

    let validation_budget = SwiftValidationBudget::default();
    let run_budget = SwiftRunBudget::default();
    let wasi_budget = WasiBudget::default();
    println!("BUDGETS case={index} unchanged=true validation={validation_budget:?} run={run_budget:?} wasi={wasi_budget:?}");
    let proof = validate_swift_command(&bytes, validation_budget, &Cancellation::default())
        .unwrap_or_else(|failure| {
            panic!("REJECTION stage=mixer-validation case={index}: {failure:?}")
        });
    println!("ADMITTED case={index} stage=mixer-validation");
    let mut stdout = vec![];
    let mut stderr = vec![];
    let report = execute_swift_command(
        proof,
        run_budget,
        WasiGrants {
            stdout: true,
            ..Default::default()
        },
        wasi_budget,
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
    let bits = match width(case) {
        4 => u32::from_le_bytes(stdout.as_slice().try_into().expect("f32 result width")) as u64,
        8 => u64::from_le_bytes(stdout.as_slice().try_into().expect("f64 result width")),
        _ => unreachable!(),
    };
    assert_eq!(
        classified(case, bits),
        oracle_class,
        "Node parity case={index}"
    );
    assert_eq!(report.calls_by_function.iter().sum::<u64>(), 1);
    println!("PARITY case={index} name={} node={oracle_bits:016x} mixer={bits:016x} class={oracle_class} bytes={}", case.name, hex(&stdout));
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
        .env(CASE_ENV, selector)
        .env_remove("NODE_OPTIONS")
        .env_remove("NODE_PATH");
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

// Only this parent is discoverable; each ordinary helper reenters this exact
// test, with one canonical selector and one consuming runtime in that process.
#[test]
#[ignore = "development Node oracle; explicit experimental-swift-reactor corpus"]
fn float_width_and_reinterpret_matches_node() {
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
        let args: Vec<_> = std::env::args_os().skip(1).collect();
        let expected: Vec<std::ffi::OsString> = [
            "--ignored",
            "--exact",
            TEST,
            "--nocapture",
            "--test-threads=1",
        ]
        .into_iter()
        .map(Into::into)
        .collect();
        assert_eq!(args, expected, "ENVIRONMENT_REJECTED: worker argv mismatch");
        isolated_case(index, node);
        return;
    }
    for invalid in [
        "",
        "-1",
        "32",
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
        PathBuf::from("/mixer-float-width-missing-node"),
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
    rejected(
        "worker-argv-reentry",
        worker("0")
            .arg("--show-output")
            .output()
            .expect("UNKNOWN argv-control subprocess"),
    );
    for index in 0..CASES.len() {
        let mut command = worker(&index.to_string());
        if index == CASES.len() - 1 {
            command
                .env_remove("MIXER_NODE")
                .env("PATH", node.parent().unwrap());
        } else {
            command.env("MIXER_NODE", &node);
        }
        let output = command.output().expect("UNKNOWN float-width subprocess");
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
    println!("32 original float-width cases matched Node; 28 bit-exact and 4 allowed-NaN; 14 zero currents and 0 tickets each; 16 environment controls rejected; unset-only PATH discovery exercised");
}
