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

const TEST: &str = "integer_arithmetic_matches_node";
const CASE_ENV: &str = "MIXER_DIFFERENTIAL_INTEGER_ARITHMETIC_CASE";

struct Case {
    name: &'static str,
    opcode: u8,
    left: i64,
    right: Option<i64>,
    expected: u64,
}

// Independently authored arithmetic inputs, not copied conformance fixtures.
// Wasm integer arithmetic is modulo 2^N; and/or/xor act on each bit.
// Normative semantics: https://webassembly.github.io/spec/core/exec/numerics.html
// Literal bit patterns supplement Node WebAssembly as the primary oracle.
const CASES: [Case; 32] = [
    Case {
        name: "i32.add-zero-min",
        opcode: 0x6a,
        left: 0,
        right: Some(i32::MIN as i64),
        expected: 0x8000_0000,
    },
    Case {
        name: "i32.add-signed-overflow",
        opcode: 0x6a,
        left: i32::MAX as i64,
        right: Some(1),
        expected: 0x8000_0000,
    },
    Case {
        name: "i32.add-carry-out",
        opcode: 0x6a,
        left: -1,
        right: Some(1),
        expected: 0,
    },
    Case {
        name: "i32.sub-zero-borrow",
        opcode: 0x6b,
        left: 0,
        right: Some(1),
        expected: 0xffff_ffff,
    },
    Case {
        name: "i32.sub-signed-underflow",
        opcode: 0x6b,
        left: i32::MIN as i64,
        right: Some(1),
        expected: 0x7fff_ffff,
    },
    Case {
        name: "i32.sub-limb-borrow",
        opcode: 0x6b,
        left: 0x0001_0000,
        right: Some(1),
        expected: 0x0000_ffff,
    },
    Case {
        name: "i32.mul-zero",
        opcode: 0x6c,
        left: 0,
        right: Some(-0x1234_567),
        expected: 0,
    },
    Case {
        name: "i32.mul-min-negation",
        opcode: 0x6c,
        left: i32::MIN as i64,
        right: Some(-1),
        expected: 0x8000_0000,
    },
    Case {
        name: "i32.mul-high-bits-discarded",
        opcode: 0x6c,
        left: 0x0001_0001,
        right: Some(0x0001_0001),
        expected: 0x0002_0001,
    },
    Case {
        name: "i32.mul-full-width-wrap",
        opcode: 0x6c,
        left: -1,
        right: Some(3),
        expected: 0xffff_fffd,
    },
    Case {
        name: "i32.and-complementary-masks",
        opcode: 0x71,
        left: 0xaaaa_aaaau32 as i32 as i64,
        right: Some(0x5555_5555),
        expected: 0,
    },
    Case {
        name: "i32.and-mask-preserved",
        opcode: 0x71,
        left: 0xaaaa_aaaau32 as i32 as i64,
        right: Some(-1),
        expected: 0xaaaa_aaaa,
    },
    Case {
        name: "i32.or-complementary-masks",
        opcode: 0x72,
        left: 0xaaaa_aaaau32 as i32 as i64,
        right: Some(0x5555_5555),
        expected: 0xffff_ffff,
    },
    Case {
        name: "i32.or-sign-and-low-bits",
        opcode: 0x72,
        left: i32::MIN as i64,
        right: Some(0x0101),
        expected: 0x8000_0101,
    },
    Case {
        name: "i32.xor-self",
        opcode: 0x73,
        left: 0x0123_4567,
        right: Some(0x0123_4567),
        expected: 0,
    },
    Case {
        name: "i32.xor-alternating-masks",
        opcode: 0x73,
        left: 0xaaaa_aaaau32 as i32 as i64,
        right: Some(0x0f0f_0f0f),
        expected: 0xa5a5_a5a5,
    },
    Case {
        name: "i64.add-zero-min",
        opcode: 0x7c,
        left: 0,
        right: Some(i64::MIN),
        expected: 0x8000_0000_0000_0000,
    },
    Case {
        name: "i64.add-signed-overflow",
        opcode: 0x7c,
        left: i64::MAX,
        right: Some(1),
        expected: 0x8000_0000_0000_0000,
    },
    Case {
        name: "i64.add-carry-out",
        opcode: 0x7c,
        left: -1,
        right: Some(1),
        expected: 0,
    },
    Case {
        name: "i64.sub-zero-borrow",
        opcode: 0x7d,
        left: 0,
        right: Some(1),
        expected: 0xffff_ffff_ffff_ffff,
    },
    Case {
        name: "i64.sub-signed-underflow",
        opcode: 0x7d,
        left: i64::MIN,
        right: Some(1),
        expected: 0x7fff_ffff_ffff_ffff,
    },
    Case {
        name: "i64.sub-limb-borrow",
        opcode: 0x7d,
        left: 0x0000_0001_0000_0000,
        right: Some(1),
        expected: 0x0000_0000_ffff_ffff,
    },
    Case {
        name: "i64.mul-zero",
        opcode: 0x7e,
        left: 0,
        right: Some(-0x0123_4567_89ab_cdef),
        expected: 0,
    },
    Case {
        name: "i64.mul-min-negation",
        opcode: 0x7e,
        left: i64::MIN,
        right: Some(-1),
        expected: 0x8000_0000_0000_0000,
    },
    Case {
        name: "i64.mul-high-bits-discarded",
        opcode: 0x7e,
        left: 0x0000_0001_0000_0001,
        right: Some(0x0000_0001_0000_0001),
        expected: 0x0000_0002_0000_0001,
    },
    Case {
        name: "i64.mul-full-width-wrap",
        opcode: 0x7e,
        left: -1,
        right: Some(3),
        expected: 0xffff_ffff_ffff_fffd,
    },
    Case {
        name: "i64.and-complementary-masks",
        opcode: 0x83,
        left: 0xaaaa_aaaa_aaaa_aaaau64 as i64,
        right: Some(0x5555_5555_5555_5555),
        expected: 0,
    },
    Case {
        name: "i64.and-mask-preserved",
        opcode: 0x83,
        left: 0xaaaa_aaaa_aaaa_aaaau64 as i64,
        right: Some(-1),
        expected: 0xaaaa_aaaa_aaaa_aaaa,
    },
    Case {
        name: "i64.or-complementary-masks",
        opcode: 0x84,
        left: 0xaaaa_aaaa_aaaa_aaaau64 as i64,
        right: Some(0x5555_5555_5555_5555),
        expected: 0xffff_ffff_ffff_ffff,
    },
    Case {
        name: "i64.or-sign-and-low-bits",
        opcode: 0x84,
        left: i64::MIN,
        right: Some(0x0101),
        expected: 0x8000_0000_0000_0101,
    },
    Case {
        name: "i64.xor-self",
        opcode: 0x85,
        left: 0x0123_4567_89ab_cdef,
        right: Some(0x0123_4567_89ab_cdef),
        expected: 0,
    },
    Case {
        name: "i64.xor-alternating-masks",
        opcode: 0x85,
        left: 0xaaaa_aaaa_aaaa_aaaau64 as i64,
        right: Some(0x0f0f_0f0f_0f0f_0f0f),
        expected: 0xa5a5_a5a5_a5a5_a5a5,
    },
];

fn width(case: &Case) -> usize {
    match case.opcode {
        0x6a..=0x6c | 0x71..=0x73 => 4,
        0x7c..=0x7e | 0x83..=0x85 => 8,
        _ => panic!("unsupported integer-arithmetic case"),
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
    assert!(
        case.right.is_some(),
        "binary arithmetic requires two operands"
    );
    let mut body = vec![0, 0x41, 32];
    constant(&mut body, width(case), case.left);
    if let Some(right) = case.right {
        constant(&mut body, width(case), right);
    }
    body.extend([
        case.opcode,
        if width(case) == 4 { 0x36 } else { 0x37 },
        0,
        0,
    ]);
    for value in [1, 0, 1, 16] {
        constant(&mut body, 4, value);
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

// No JS arithmetic models the operations. WebAssembly executes the module;
// DataView decodes unsigned bits, and i64 goes directly from BigInt to decimal.
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
    let input = format!("{}\n{}", width(case), hex(&bytes));
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
    let expected = format!("value:{}\n", case.expected);
    assert_eq!(
        oracle, expected,
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
    // Consumption is checked before status/output, including an unexpected trap.
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
    let value = match width(case) {
        4 => u32::from_le_bytes(stdout.as_slice().try_into().expect("i32 output width")) as u64,
        8 => u64::from_le_bytes(stdout.as_slice().try_into().expect("i64 output width")),
        _ => unreachable!(),
    };
    assert_eq!(
        format!("value:{value}\n"),
        oracle,
        "Node exact integer parity case={index}"
    );
    assert_eq!(value, case.expected, "case={index} name={}", case.name);
    assert_eq!(report.calls_by_function.iter().sum::<u64>(), 1);
    println!(
        "SCALAR case={index} name={} value={value} bytes={}",
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

// This sole ignored test handles both discovery modes. Ordinary helpers cannot
// be selected as an ignored worker without an explicit canonical case selector.
#[test]
#[ignore = "development Node oracle; explicit experimental-swift-reactor corpus"]
fn integer_arithmetic_matches_node() {
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
        "/mixer-integer-arithmetic-missing-node",
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
            .expect("UNKNOWN integer-arithmetic subprocess");
        print!("{}", String::from_utf8_lossy(&output.stdout));
        assert!(
            output.status.success(),
            "case={index}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(output.stderr.is_empty());
        let text = String::from_utf8_lossy(&output.stdout);
        assert!(text.contains(&format!("CLEANUP case={index} ")));
        assert!(text.contains(&format!("SCALAR case={index} ")));
    }
    println!("32 original integer-arithmetic cases matched Node; each consumed fourteen zero currents and zero tickets; 9 invalid environments rejected");
}
