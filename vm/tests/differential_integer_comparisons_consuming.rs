#![cfg(feature = "experimental-swift-reactor")]

#[path = "swift_reactor_validation_fixture.rs"]
mod fixture;

use mixer_vm::experimental_swift_reactor::{
    execute_swift_command, validate_swift_command, SwiftRunBudget, SwiftValidationBudget,
};
use mixer_vm::experimental_wasi::{WasiBudget, WasiGrants};
use mixer_vm::Cancellation;
use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Output, Stdio};

const TEST: &str = "integer_comparisons_match_node";
const CASE_ENV: &str = "MIXER_DIFFERENTIAL_INTEGER_COMPARISONS_CASE";

struct Case {
    name: &'static str,
    opcode: u8,
    left: i64,
    right: Option<i64>,
    expected: i32,
}

// Each literal pair is an original module. Signed/unsigned interpretations
// disagree at the high bit; strict/inclusive predicates meet equality here.
// Adjacent i64 extrema also distinguish values lost through JS Number.
const CASES: [Case; 32] = [
    Case {
        name: "i32.eqz-zero",
        opcode: 0x45,
        left: 0,
        right: None,
        expected: 1,
    },
    Case {
        name: "i32.eqz-min",
        opcode: 0x45,
        left: i32::MIN as i64,
        right: None,
        expected: 0,
    },
    Case {
        name: "i32.eq-highbit-equal",
        opcode: 0x46,
        left: i32::MIN as i64,
        right: Some(i32::MIN as i64),
        expected: 1,
    },
    Case {
        name: "i32.ne-adjacent-max",
        opcode: 0x47,
        left: i32::MAX as i64,
        right: Some(i32::MAX as i64 - 1),
        expected: 1,
    },
    Case {
        name: "i32.lt_s-min-max",
        opcode: 0x48,
        left: i32::MIN as i64,
        right: Some(i32::MAX as i64),
        expected: 1,
    },
    Case {
        name: "i32.lt_u-highbit-max",
        opcode: 0x49,
        left: i32::MIN as i64,
        right: Some(i32::MAX as i64),
        expected: 0,
    },
    Case {
        name: "i32.gt_s-max-min",
        opcode: 0x4a,
        left: i32::MAX as i64,
        right: Some(i32::MIN as i64),
        expected: 1,
    },
    Case {
        name: "i32.gt_u-highbit-max",
        opcode: 0x4b,
        left: i32::MIN as i64,
        right: Some(i32::MAX as i64),
        expected: 1,
    },
    Case {
        name: "i32.le_s-min-equal",
        opcode: 0x4c,
        left: i32::MIN as i64,
        right: Some(i32::MIN as i64),
        expected: 1,
    },
    Case {
        name: "i32.le_u-allones-zero",
        opcode: 0x4d,
        left: -1,
        right: Some(0),
        expected: 0,
    },
    Case {
        name: "i32.ge_s-negative-zero",
        opcode: 0x4e,
        left: -1,
        right: Some(0),
        expected: 0,
    },
    Case {
        name: "i32.ge_u-allones-equal",
        opcode: 0x4f,
        left: -1,
        right: Some(-1),
        expected: 1,
    },
    Case {
        name: "i32.eq-adjacent-max",
        opcode: 0x46,
        left: i32::MAX as i64,
        right: Some(i32::MAX as i64 - 1),
        expected: 0,
    },
    Case {
        name: "i32.ne-zero-equal",
        opcode: 0x47,
        left: 0,
        right: Some(0),
        expected: 0,
    },
    Case {
        name: "i32.lt_s-negative-equal",
        opcode: 0x48,
        left: -1,
        right: Some(-1),
        expected: 0,
    },
    Case {
        name: "i32.gt_u-highbit-equal",
        opcode: 0x4b,
        left: i32::MIN as i64,
        right: Some(i32::MIN as i64),
        expected: 0,
    },
    Case {
        name: "i64.eqz-zero",
        opcode: 0x50,
        left: 0,
        right: None,
        expected: 1,
    },
    Case {
        name: "i64.eqz-min",
        opcode: 0x50,
        left: i64::MIN,
        right: None,
        expected: 0,
    },
    Case {
        name: "i64.eq-highbit-equal",
        opcode: 0x51,
        left: i64::MIN,
        right: Some(i64::MIN),
        expected: 1,
    },
    Case {
        name: "i64.ne-adjacent-max",
        opcode: 0x52,
        left: i64::MAX,
        right: Some(i64::MAX - 1),
        expected: 1,
    },
    Case {
        name: "i64.lt_s-min-max",
        opcode: 0x53,
        left: i64::MIN,
        right: Some(i64::MAX),
        expected: 1,
    },
    Case {
        name: "i64.lt_u-highbit-max",
        opcode: 0x54,
        left: i64::MIN,
        right: Some(i64::MAX),
        expected: 0,
    },
    Case {
        name: "i64.gt_s-max-min",
        opcode: 0x55,
        left: i64::MAX,
        right: Some(i64::MIN),
        expected: 1,
    },
    Case {
        name: "i64.gt_u-highbit-max",
        opcode: 0x56,
        left: i64::MIN,
        right: Some(i64::MAX),
        expected: 1,
    },
    Case {
        name: "i64.le_s-min-equal",
        opcode: 0x57,
        left: i64::MIN,
        right: Some(i64::MIN),
        expected: 1,
    },
    Case {
        name: "i64.le_u-allones-zero",
        opcode: 0x58,
        left: -1,
        right: Some(0),
        expected: 0,
    },
    Case {
        name: "i64.ge_s-negative-zero",
        opcode: 0x59,
        left: -1,
        right: Some(0),
        expected: 0,
    },
    Case {
        name: "i64.ge_u-allones-equal",
        opcode: 0x5a,
        left: -1,
        right: Some(-1),
        expected: 1,
    },
    Case {
        name: "i64.eq-adjacent-max",
        opcode: 0x51,
        left: i64::MAX,
        right: Some(i64::MAX - 1),
        expected: 0,
    },
    Case {
        name: "i64.ne-zero-equal",
        opcode: 0x52,
        left: 0,
        right: Some(0),
        expected: 0,
    },
    Case {
        name: "i64.lt_s-negative-equal",
        opcode: 0x53,
        left: -1,
        right: Some(-1),
        expected: 0,
    },
    Case {
        name: "i64.gt_u-highbit-equal",
        opcode: 0x56,
        left: i64::MIN,
        right: Some(i64::MIN),
        expected: 0,
    },
];

fn width(case: &Case) -> usize {
    match case.opcode {
        0x45..=0x4f => 4,
        0x50..=0x5a => 8,
        _ => panic!("unsupported integer-comparison case"),
    }
}

fn constant(body: &mut Vec<u8>, width: usize, mut value: i64) {
    if width == 4 {
        body.push(0x41);
        body.extend(fixture::signed(i32::try_from(value).unwrap()));
        return;
    }
    body.push(0x42);
    loop {
        let byte = (value & 127) as u8;
        value >>= 7;
        let done = (value == 0 && byte & 64 == 0) || (value == -1 && byte & 64 != 0);
        body.push(if done { byte } else { byte | 128 });
        if done {
            break;
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
    let input_width = width(case);
    assert_eq!(case.right.is_none(), matches!(case.opcode, 0x45 | 0x50));
    assert!(matches!(case.expected, 0 | 1));
    let mut body = vec![0, 0x41, 32];
    constant(&mut body, input_width, case.left);
    if let Some(right) = case.right {
        constant(&mut body, input_width, right);
    }
    body.extend([case.opcode, 0x36, 0, 0]);
    for value in [1, 0, 1, 16] {
        constant(&mut body, 4, value);
    }
    body.push(0x10);
    body.extend(fixture::uint(fd_write as u32));
    body.extend([0x1a, 0x0b]);
    f.bodies = vec![body];
    let mut iovec = 32u32.to_le_bytes().to_vec();
    iovec.extend(4u32.to_le_bytes());
    f.data = vec![fixture::data_segment(0, &iovec)];
    f.bytes()
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

// WebAssembly performs the comparison on encoded integer constants. The oracle
// observes exactly four output bytes, including for i64 input predicates.
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
console.log('value:' + value);
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

fn isolated_case(index: usize, node: PathBuf) {
    let case = &CASES[index];
    let bytes = module(case);
    println!(
        "MODULE case={index} name={} opcode={:02x} left={} right={:?} expected={} hex={}",
        case.name,
        case.opcode,
        case.left,
        case.right,
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
    let input = format!("4\n{}", hex(&bytes));
    let write = child.stdin.take().unwrap().write_all(input.as_bytes());
    let output = child.wait_with_output().expect("UNKNOWN Node reap/output");
    write.expect("Node module transport failed");
    assert!(
        output.status.success(),
        "Node failure case={index}: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stderr.is_empty());
    let oracle = String::from_utf8(output.stdout).unwrap();
    assert_eq!(
        oracle,
        format!("value:{}\n", case.expected),
        "independent literal expectation case={index}"
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
    assert!(report.succeeded(), "case={index}: {report:?}");
    assert!(report.terminal.is_none());
    assert!(!report.output_error);
    assert!(stderr.is_empty());
    let value = i32::from_le_bytes(
        stdout
            .as_slice()
            .try_into()
            .expect("exact i32 output width"),
    );
    assert_eq!(
        format!("value:{value}\n"),
        oracle,
        "Node exact integer parity case={index}"
    );
    assert_eq!(value, case.expected, "case={index} name={}", case.name);
    assert_eq!(report.calls_by_function.iter().sum::<u64>(), 1);
    println!(
        "PARITY case={index} name={} value={value} bytes={}",
        case.name,
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

// One discoverable ignored parent; ordinary helpers cannot be selected as a
// blanket ignored worker. Reentry requires a canonical explicit case selector.
#[test]
#[ignore = "development Node oracle; explicit experimental-swift-reactor corpus"]
fn integer_comparisons_match_node() {
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
    for invalid in ["", "-1", "32", "01", "not-an-index"] {
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
    for invalid in [
        "",
        "relative-node",
        "/mixer-integer-comparison-missing-node",
    ] {
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
            .expect("UNKNOWN integer-comparison subprocess");
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
    println!("32 original integer-comparison cases matched Node; each consumed fourteen zero currents and zero tickets; 9 invalid environments rejected");
}
