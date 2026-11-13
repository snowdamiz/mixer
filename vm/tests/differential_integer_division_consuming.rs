#![cfg(feature = "experimental-swift-reactor")]

#[path = "swift_reactor_validation_fixture.rs"]
mod fixture;

use mixer_vm::experimental_swift_reactor::{
    execute_swift_command, validate_swift_command, SwiftRunBudget, SwiftRunFailureKind,
    SwiftValidationBudget,
};
use mixer_vm::experimental_wasi::{WasiBudget, WasiGrants};
use mixer_vm::Cancellation;
use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Output, Stdio};

const TEST: &str = "integer_division_matches_node";
const CASE_ENV: &str = "MIXER_DIFFERENTIAL_INTEGER_DIVISION_CASE";

#[derive(Clone, Copy)]
enum Expected {
    Value(i128),
    ZeroDivisor,
    Overflow,
}

struct Case {
    name: &'static str,
    opcode: u8,
    left: i64,
    right: i64,
    expected: Expected,
}

// Original numerical expectations. Negative operands for unsigned operations
// encode their full-width bit patterns; no host division supplies the oracle.
// All eight instructions are already admitted by the command validation policy.
const CASES: [Case; 24] = [
    Case {
        name: "i32.div_s-truncate-negative",
        opcode: 0x6d,
        left: -23,
        right: 7,
        expected: Expected::Value(-3),
    },
    Case {
        name: "i32.div_s-min-overflow",
        opcode: 0x6d,
        left: -2_147_483_648,
        right: -1,
        expected: Expected::Overflow,
    },
    Case {
        name: "i32.div_s-zero",
        opcode: 0x6d,
        left: 23,
        right: 0,
        expected: Expected::ZeroDivisor,
    },
    Case {
        name: "i32.div_u-max-halved",
        opcode: 0x6e,
        left: -1,
        right: 2,
        expected: Expected::Value(2_147_483_647),
    },
    Case {
        name: "i32.div_u-max-preserved",
        opcode: 0x6e,
        left: -1,
        right: 1,
        expected: Expected::Value(4_294_967_295),
    },
    Case {
        name: "i32.div_u-zero",
        opcode: 0x6e,
        left: -1,
        right: 0,
        expected: Expected::ZeroDivisor,
    },
    Case {
        name: "i32.rem_s-negative-dividend",
        opcode: 0x6f,
        left: -23,
        right: 7,
        expected: Expected::Value(-2),
    },
    Case {
        name: "i32.rem_s-min-minus-one",
        opcode: 0x6f,
        left: -2_147_483_648,
        right: -1,
        expected: Expected::Value(0),
    },
    Case {
        name: "i32.rem_s-zero",
        opcode: 0x6f,
        left: -23,
        right: 0,
        expected: Expected::ZeroDivisor,
    },
    Case {
        name: "i32.rem_u-max-sign-bit-divisor",
        opcode: 0x70,
        left: -1,
        right: -2_147_483_648,
        expected: Expected::Value(2_147_483_647),
    },
    Case {
        name: "i32.rem_u-max-odd",
        opcode: 0x70,
        left: -1,
        right: 2,
        expected: Expected::Value(1),
    },
    Case {
        name: "i32.rem_u-zero",
        opcode: 0x70,
        left: -1,
        right: 0,
        expected: Expected::ZeroDivisor,
    },
    Case {
        name: "i64.div_s-truncate-negative-divisor",
        opcode: 0x7f,
        left: 23,
        right: -7,
        expected: Expected::Value(-3),
    },
    Case {
        name: "i64.div_s-min-overflow",
        opcode: 0x7f,
        left: i64::MIN,
        right: -1,
        expected: Expected::Overflow,
    },
    Case {
        name: "i64.div_s-zero",
        opcode: 0x7f,
        left: 23,
        right: 0,
        expected: Expected::ZeroDivisor,
    },
    Case {
        name: "i64.div_u-max-halved",
        opcode: 0x80,
        left: -1,
        right: 2,
        expected: Expected::Value(9_223_372_036_854_775_807),
    },
    Case {
        name: "i64.div_u-max-preserved",
        opcode: 0x80,
        left: -1,
        right: 1,
        expected: Expected::Value(18_446_744_073_709_551_615),
    },
    Case {
        name: "i64.div_u-zero",
        opcode: 0x80,
        left: -1,
        right: 0,
        expected: Expected::ZeroDivisor,
    },
    Case {
        name: "i64.rem_s-negative-divisor",
        opcode: 0x81,
        left: 23,
        right: -7,
        expected: Expected::Value(2),
    },
    Case {
        name: "i64.rem_s-min-minus-one",
        opcode: 0x81,
        left: i64::MIN,
        right: -1,
        expected: Expected::Value(0),
    },
    Case {
        name: "i64.rem_s-zero",
        opcode: 0x81,
        left: -23,
        right: 0,
        expected: Expected::ZeroDivisor,
    },
    Case {
        name: "i64.rem_u-max-sign-bit-divisor",
        opcode: 0x82,
        left: -1,
        right: i64::MIN,
        expected: Expected::Value(9_223_372_036_854_775_807),
    },
    Case {
        name: "i64.rem_u-max-odd",
        opcode: 0x82,
        left: -1,
        right: 2,
        expected: Expected::Value(1),
    },
    Case {
        name: "i64.rem_u-zero",
        opcode: 0x82,
        left: -1,
        right: 0,
        expected: Expected::ZeroDivisor,
    },
];

fn width(case: &Case) -> usize {
    match case.opcode {
        0x6d..=0x70 => 4,
        0x7f..=0x82 => 8,
        _ => panic!("unsupported integer division case"),
    }
}

fn signed(case: &Case) -> bool {
    matches!(case.opcode, 0x6d | 0x6f | 0x7f | 0x81)
}

fn signed64(mut value: i64) -> Vec<u8> {
    let mut bytes = vec![];
    loop {
        let byte = (value & 127) as u8;
        value >>= 7;
        let done = (value == 0 && byte & 64 == 0) || (value == -1 && byte & 64 != 0);
        bytes.push(if done { byte } else { byte | 128 });
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
        .position(|(_, name, _, _)| name == b"fd_write")
        .unwrap();
    let mut body = vec![0, 0x41, 32];
    for value in [case.left, case.right] {
        if width(case) == 4 {
            body.push(0x41);
            body.extend(fixture::signed(i32::try_from(value).unwrap()));
        } else {
            body.push(0x42);
            body.extend(signed64(value));
        }
    }
    body.extend([
        case.opcode,
        if width(case) == 4 { 0x36 } else { 0x37 },
        0,
        0,
    ]);
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
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

// Node performs only transport and ABI decoding. Its built-in WebAssembly engine
// executes the actual div/rem instruction. BigInt preserves every i64/u64 value.
// RuntimeError has no portable numeric trap category; do not parse its message.
const ORACLE: &str = r#"
const fs = require('node:fs');
const [format, encoded] = fs.readFileSync(0, 'utf8').split('\n');
const [width, signed] = format.split(':');
if (!['4', '8'].includes(width) || !['true', 'false'].includes(signed)) throw new Error('format');
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
  value = (width === '4'
    ? (signed === 'true' ? view.getInt32(32, true) : view.getUint32(32, true))
    : (signed === 'true' ? view.getBigInt64(32, true) : view.getBigUint64(32, true))).toString();
  view.setUint32(written, Number(width), true); return 0;
};
instance = new WebAssembly.Instance(m, {wasi_snapshot_preview1: wasi});
let trapped = false;
try { instance.exports._start(); }
catch (e) { if (!(e instanceof WebAssembly.RuntimeError)) throw e; trapped = true; }
if (trapped) {
  if (value !== null) throw new Error('output before trap');
  console.log('trap');
} else {
  if (value === null) throw new Error('missing output');
  console.log('value:' + value);
}
"#;

fn node_path() -> PathBuf {
    let path = std::env::var_os("MIXER_NODE")
        .map(PathBuf::from)
        .or_else(|| {
            std::env::var_os("PATH").and_then(|paths| {
                std::env::split_paths(&paths)
                    .map(|directory| directory.join("node"))
                    .find(|path| path.is_absolute() && path.is_file())
            })
        })
        .expect("ENVIRONMENT_REJECTED: Node executable required via MIXER_NODE or PATH");
    assert!(
        path.is_absolute() && path.is_file(),
        "ENVIRONMENT_REJECTED: absolute Node executable required"
    );
    path
}

fn numerical_output(case: &Case, bytes: &[u8]) -> i128 {
    assert_eq!(bytes.len(), width(case));
    match (width(case), signed(case)) {
        (4, true) => i32::from_le_bytes(bytes.try_into().unwrap()) as i128,
        (4, false) => u32::from_le_bytes(bytes.try_into().unwrap()) as i128,
        (8, true) => i64::from_le_bytes(bytes.try_into().unwrap()) as i128,
        (8, false) => u64::from_le_bytes(bytes.try_into().unwrap()) as i128,
        _ => unreachable!(),
    }
}

fn isolated_case(index: usize, node: PathBuf) {
    let case = &CASES[index];
    let bytes = module(case);
    println!(
        "MODULE case={index} name={} opcode={:02x} left={} right={} hex={}",
        case.name,
        case.opcode,
        case.left,
        case.right,
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
    let input = format!("{}:{}\n{}", width(case), signed(case), hex(&bytes));
    let write = child.stdin.take().unwrap().write_all(input.as_bytes());
    let output = child.wait_with_output().expect("UNKNOWN Node reap/output");
    write.expect("Node module transport failed");
    assert!(
        output.status.success(),
        "Node failure case={index}: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stderr.is_empty());
    let expected_oracle = match case.expected {
        Expected::Value(value) => format!("value:{value}"),
        Expected::ZeroDivisor | Expected::Overflow => "trap".to_owned(),
    };
    let oracle = String::from_utf8(output.stdout).unwrap();
    assert_eq!(
        oracle,
        format!("{expected_oracle}\n"),
        "independent numerical expectation case={index}"
    );
    println!(
        "ORACLE case={index} pid={pid} reaped=true result={}",
        oracle.trim()
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
    assert_eq!(
        r.live_tickets, 0,
        "UNKNOWN reservation tickets case={index}"
    );
    assert!(
        usage.cleanup_invariant.is_none(),
        "UNKNOWN cleanup invariant case={index}"
    );
    println!("CLEANUP case={index} currents={currents:?} tickets=0 invariant=none");
    let actual = match case.expected {
        Expected::Value(value) => {
            assert!(report.succeeded(), "case={index}: {report:?}");
            assert!(report.terminal.is_none());
            let observed = numerical_output(case, &stdout);
            assert_eq!(observed, value, "case={index} name={}", case.name);
            format!("value:{observed}")
        }
        Expected::ZeroDivisor | Expected::Overflow => {
            let failure = report.terminal.expect("expected execution trap");
            assert_eq!(
                failure.kind,
                SwiftRunFailureKind::GuestTrap,
                "case={index}: {failure:?}"
            );
            // These are Mixer contract checks. Node promises RuntimeError only,
            // so oracle parity deliberately does not assign it a trap category.
            let code = match case.expected {
                Expected::ZeroDivisor => "integer_divide_by_zero",
                Expected::Overflow => "integer_overflow",
                Expected::Value(_) => unreachable!(),
            };
            assert_eq!(failure.code, code, "case={index}: {failure:?}");
            assert!(!report.succeeded());
            assert!(stdout.is_empty());
            println!("TRAP_CONTRACT case={index} mixer_code={code} node_category=RuntimeError");
            "trap".to_owned()
        }
    };
    assert!(!report.output_error);
    assert!(stderr.is_empty());
    assert_eq!(actual, oracle.trim(), "Node numerical parity case={index}");
    assert_eq!(
        report.calls_by_function.iter().sum::<u64>(),
        if actual == "trap" { 0 } else { 1 }
    );
    println!("PARITY case={index} name={} result={actual}", case.name);
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
    assert!(
        !output.status.success(),
        "invalid environment unexpectedly accepted"
    );
    let mut combined = output.stdout;
    combined.extend(output.stderr);
    let text = String::from_utf8_lossy(&combined);
    assert!(
        text.contains("ENVIRONMENT_REJECTED:"),
        "wrong rejection: {text}"
    );
    assert!(
        !text.contains("MODULE case=")
            && !text.contains("WORKER case=")
            && !text.contains("ADMITTED case=")
            && !text.contains("CLEANUP case=")
    );
    println!(
        "ENVIRONMENT_FAIL_CLOSED control={control:?} status={} output={text}",
        output.status
    );
}

// Sole discoverable test: exact and blanket ignored selection both dispatch
// this parent. Its ordinary helper consumes exactly one runtime per child case.
#[test]
#[ignore = "development Node oracle; explicit experimental-swift-reactor corpus"]
fn integer_division_matches_node() {
    let selector = match std::env::var(CASE_ENV) {
        Ok(raw) => {
            let index = raw
                .parse::<usize>()
                .expect("ENVIRONMENT_REJECTED: invalid case index");
            assert!(
                index < CASES.len() && raw == index.to_string(),
                "ENVIRONMENT_REJECTED: case out of range or noncanonical"
            );
            Some(index)
        }
        Err(std::env::VarError::NotPresent) => None,
        Err(_) => panic!("ENVIRONMENT_REJECTED: non-Unicode case index"),
    };
    let node = node_path();
    if let Some(index) = selector {
        isolated_case(index, node);
        return;
    }
    for invalid in ["", "-1", "24", "01", "not-an-index"] {
        rejected(
            invalid,
            worker(invalid)
                .output()
                .expect("UNKNOWN environment-control subprocess"),
        );
    }
    rejected(
        "missing-node",
        worker("0")
            .env_remove("MIXER_NODE")
            .env("PATH", "")
            .output()
            .expect("UNKNOWN missing-Node subprocess"),
    );
    // A present override is authoritative even when PATH can resolve Node.
    for invalid in ["", "relative-node", "/mixer-integer-division-missing-node"] {
        rejected(
            invalid,
            worker("0")
                .env("MIXER_NODE", invalid)
                .output()
                .expect("UNKNOWN invalid-Node subprocess"),
        );
    }
    for index in 0..CASES.len() {
        let output = worker(&index.to_string())
            .output()
            .expect("UNKNOWN integer-division subprocess");
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
    println!("24 original integer division/remainder cases matched Node; each consumed fourteen zero currents and zero tickets; 9 invalid environments rejected");
}
