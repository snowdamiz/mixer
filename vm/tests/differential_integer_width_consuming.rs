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

const TEST: &str = "integer_width_conversions_match_node";
const CASE_ENV: &str = "MIXER_DIFFERENTIAL_INTEGER_WIDTH_CASE";

struct Case {
    name: &'static str,
    opcode: u8,
    input: i64,
    expected: u64,
}

// Original literal bit patterns exercise discarded upper bits independently of
// the sign bit of the retained lane. The old nonconsuming generic edge grid
// does not pair these dirty prefixes with the 8/16/32-bit sign thresholds.
// i64 expectations are unsigned output bits, never rounded through JS Number.
const CASES: [Case; 32] = [
    Case {
        name: "i32.wrap_i64-discard-bit63",
        opcode: 0xa7,
        input: i64::MIN,
        expected: 0,
    },
    Case {
        name: "i32.wrap_i64-mixed-upper-and-lower",
        opcode: 0xa7,
        input: 0x1234_5678_8765_4321,
        expected: 0x8765_4321,
    },
    Case {
        name: "i32.wrap_i64-retain-bit31",
        opcode: 0xa7,
        input: 0x7fff_ffff_8000_0000,
        expected: 0x8000_0000,
    },
    Case {
        name: "i32.wrap_i64-negative-input-positive-low",
        opcode: 0xa7,
        input: 0x8000_0000_7fff_ffffu64 as i64,
        expected: 0x7fff_ffff,
    },
    Case {
        name: "i32.wrap_i64-all-ones",
        opcode: 0xa7,
        input: -1,
        expected: 0xffff_ffff,
    },
    Case {
        name: "i64.extend_i32_s-bit31",
        opcode: 0xac,
        input: -2_147_483_648,
        expected: 0xffff_ffff_8000_0000,
    },
    Case {
        name: "i64.extend_i32_s-below-bit31",
        opcode: 0xac,
        input: 2_147_483_647,
        expected: 0x7fff_ffff,
    },
    Case {
        name: "i64.extend_i32_s-all-ones",
        opcode: 0xac,
        input: -1,
        expected: 0xffff_ffff_ffff_ffff,
    },
    Case {
        name: "i64.extend_i32_u-bit31",
        opcode: 0xad,
        input: -2_147_483_648,
        expected: 0x8000_0000,
    },
    Case {
        name: "i64.extend_i32_u-below-bit31",
        opcode: 0xad,
        input: 2_147_483_647,
        expected: 0x7fff_ffff,
    },
    Case {
        name: "i64.extend_i32_u-all-ones",
        opcode: 0xad,
        input: -1,
        expected: 0xffff_ffff,
    },
    Case {
        name: "i64.extend_i32_u-mixed-negative",
        opcode: 0xad,
        input: 0x89ab_cdefu32 as i32 as i64,
        expected: 0x89ab_cdef,
    },
    Case {
        name: "i32.extend8_s-dirty-below-sign",
        opcode: 0xc0,
        input: 0x4567_897f,
        expected: 0x7f,
    },
    Case {
        name: "i32.extend8_s-dirty-at-sign",
        opcode: 0xc0,
        input: 0x4567_8980,
        expected: 0xffff_ff80,
    },
    Case {
        name: "i32.extend8_s-high-bit-low-all-ones",
        opcode: 0xc0,
        input: 0x8000_00ffu32 as i32 as i64,
        expected: 0xffff_ffff,
    },
    Case {
        name: "i32.extend8_s-discard-bit8-and-upper",
        opcode: 0xc0,
        input: 0xffff_0100u32 as i32 as i64,
        expected: 0,
    },
    Case {
        name: "i32.extend16_s-dirty-below-sign",
        opcode: 0xc1,
        input: 0x6543_7fff,
        expected: 0x7fff,
    },
    Case {
        name: "i32.extend16_s-dirty-at-sign",
        opcode: 0xc1,
        input: 0x6543_8000,
        expected: 0xffff_8000,
    },
    Case {
        name: "i32.extend16_s-high-bit-low-all-ones",
        opcode: 0xc1,
        input: 0x8000_ffffu32 as i32 as i64,
        expected: 0xffff_ffff,
    },
    Case {
        name: "i32.extend16_s-discard-upper-half",
        opcode: 0xc1,
        input: -65_536,
        expected: 0,
    },
    Case {
        name: "i64.extend8_s-bit63-dirty-below-sign",
        opcode: 0xc2,
        input: 0x8123_4567_89ab_cd7fu64 as i64,
        expected: 0x7f,
    },
    Case {
        name: "i64.extend8_s-positive-dirty-at-sign",
        opcode: 0xc2,
        input: 0x0123_4567_89ab_cd80,
        expected: 0xffff_ffff_ffff_ff80,
    },
    Case {
        name: "i64.extend8_s-bit63-low-all-ones",
        opcode: 0xc2,
        input: 0x8000_0000_0000_00ffu64 as i64,
        expected: 0xffff_ffff_ffff_ffff,
    },
    Case {
        name: "i64.extend8_s-discard-upper-seven-bytes",
        opcode: 0xc2,
        input: -256,
        expected: 0,
    },
    Case {
        name: "i64.extend16_s-bit63-dirty-below-sign",
        opcode: 0xc3,
        input: 0x8123_4567_89ab_7fffu64 as i64,
        expected: 0x7fff,
    },
    Case {
        name: "i64.extend16_s-positive-dirty-at-sign",
        opcode: 0xc3,
        input: 0x0123_4567_89ab_8000,
        expected: 0xffff_ffff_ffff_8000,
    },
    Case {
        name: "i64.extend16_s-bit63-low-all-ones",
        opcode: 0xc3,
        input: 0x8000_0000_0000_ffffu64 as i64,
        expected: 0xffff_ffff_ffff_ffff,
    },
    Case {
        name: "i64.extend16_s-discard-upper-six-bytes",
        opcode: 0xc3,
        input: -65_536,
        expected: 0,
    },
    Case {
        name: "i64.extend32_s-bit63-dirty-below-sign",
        opcode: 0xc4,
        input: 0x8123_4567_7fff_ffffu64 as i64,
        expected: 0x7fff_ffff,
    },
    Case {
        name: "i64.extend32_s-positive-dirty-at-sign",
        opcode: 0xc4,
        input: 0x0123_4567_8000_0000,
        expected: 0xffff_ffff_8000_0000,
    },
    Case {
        name: "i64.extend32_s-bit63-low-all-ones",
        opcode: 0xc4,
        input: 0x8000_0000_ffff_ffffu64 as i64,
        expected: 0xffff_ffff_ffff_ffff,
    },
    Case {
        name: "i64.extend32_s-discard-upper-half",
        opcode: 0xc4,
        input: -4_294_967_296,
        expected: 0,
    },
];

fn widths(case: &Case) -> (usize, usize) {
    match case.opcode {
        0xa7 => (8, 4),
        0xac | 0xad => (4, 8),
        0xc0 | 0xc1 => (4, 4),
        0xc2..=0xc4 => (8, 8),
        _ => panic!("unsupported integer-width case"),
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
    let (input_width, output_width) = widths(case);
    let mut body = vec![0, 0x41, 32];
    constant(&mut body, input_width, case.input);
    body.extend([
        case.opcode,
        if output_width == 4 { 0x36 } else { 0x37 },
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
    iovec.extend((output_width as u32).to_le_bytes());
    f.data = vec![fixture::data_segment(0, &iovec)];
    f.bytes()
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

// WebAssembly performs every conversion. DataView observes result bits; an i64
// travels directly from BigInt to decimal without a Number conversion.
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
        "MODULE case={index} name={} opcode={:02x} input={} expected={} hex={}",
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
    let input = format!("{}\n{}", widths(case).1, hex(&bytes));
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
    let value = match widths(case).1 {
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
fn integer_width_conversions_match_node() {
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
    for invalid in ["", "relative-node", "/mixer-integer-width-missing-node"] {
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
            .expect("UNKNOWN integer-width subprocess");
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
    println!("32 original integer-width cases matched Node; each consumed fourteen zero currents and zero tickets; 9 invalid environments rejected");
}
