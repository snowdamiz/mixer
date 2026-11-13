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

const TEST: &str = "float_conversions_match_node";
const CASE_ENV: &str = "MIXER_DIFFERENTIAL_FLOAT_CONVERSION_CASE";

#[derive(Clone, Copy)]
enum Expected {
    Bits(u64),
    Trap(&'static str),
}

struct Case {
    name: &'static str,
    opcode: u8,
    input_bits: u64,
    expected: Expected,
}

// Original cases: exact IEEE inputs and integer bit patterns, not host casts or
// values obtained from the implementation. Unsigned results are observed as
// little-endian bytes, so neither JS Number precision nor signed printing hides
// the upper half of the integer range. The command policy admits these eight
// non-saturating Core instructions; no production profile is selected here.
const CASES: [Case; 24] = [
    Case {
        name: "i32.trunc_f32_s-negative-fraction",
        opcode: 0xa8,
        input_bits: 0xc1bf_0000,
        expected: Expected::Bits(0xffff_ffe9),
    }, // -23.875 -> -23
    Case {
        name: "i32.trunc_f32_s-last-below-upper",
        opcode: 0xa8,
        input_bits: 0x4eff_ffff,
        expected: Expected::Bits(2_147_483_520),
    },
    Case {
        name: "i32.trunc_f32_s-upper-exclusive",
        opcode: 0xa8,
        input_bits: 0x4f00_0000,
        expected: Expected::Trap("integer_overflow"),
    },
    Case {
        name: "i32.trunc_f32_u-negative-fraction",
        opcode: 0xa9,
        input_bits: 0xbf40_0000,
        expected: Expected::Bits(0),
    }, // -0.75 -> 0
    Case {
        name: "i32.trunc_f32_u-last-below-upper",
        opcode: 0xa9,
        input_bits: 0x4f7f_ffff,
        expected: Expected::Bits(4_294_967_040),
    },
    Case {
        name: "i32.trunc_f32_u-negative-one",
        opcode: 0xa9,
        input_bits: 0xbf80_0000,
        expected: Expected::Trap("integer_overflow"),
    },
    Case {
        name: "i32.trunc_f64_s-below-min-fraction",
        opcode: 0xaa,
        input_bits: 0xc1e0_0000_0018_0000,
        expected: Expected::Bits(0x8000_0000),
    }, // -2147483648.75 -> MIN
    Case {
        name: "i32.trunc_f64_s-below-min-integer",
        opcode: 0xaa,
        input_bits: 0xc1e0_0000_0020_0000,
        expected: Expected::Trap("integer_overflow"),
    }, // -2147483649
    Case {
        name: "i32.trunc_f64_s-above-max-fraction",
        opcode: 0xaa,
        input_bits: 0x41df_ffff_fff0_0000,
        expected: Expected::Bits(0x7fff_ffff),
    }, // 2147483647.75 -> MAX
    Case {
        name: "i32.trunc_f64_u-above-max-fraction",
        opcode: 0xab,
        input_bits: 0x41ef_ffff_fff8_0000,
        expected: Expected::Bits(0xffff_ffff),
    }, // 4294967295.75 -> MAX
    Case {
        name: "i32.trunc_f64_u-upper-exclusive",
        opcode: 0xab,
        input_bits: 0x41f0_0000_0000_0000,
        expected: Expected::Trap("integer_overflow"),
    },
    Case {
        name: "i32.trunc_f64_u-payload-nan",
        opcode: 0xab,
        input_bits: 0x7ff8_0000_0000_0042,
        expected: Expected::Trap("invalid_conversion_to_integer"),
    },
    Case {
        name: "i64.trunc_f32_s-min-inclusive",
        opcode: 0xae,
        input_bits: 0xdf00_0000,
        expected: Expected::Bits(0x8000_0000_0000_0000),
    },
    Case {
        name: "i64.trunc_f32_s-next-below-min",
        opcode: 0xae,
        input_bits: 0xdf00_0001,
        expected: Expected::Trap("integer_overflow"),
    },
    Case {
        name: "i64.trunc_f32_s-positive-infinity",
        opcode: 0xae,
        input_bits: 0x7f80_0000,
        expected: Expected::Trap("integer_overflow"),
    },
    Case {
        name: "i64.trunc_f32_u-last-below-upper",
        opcode: 0xaf,
        input_bits: 0x5f7f_ffff,
        expected: Expected::Bits(0xffff_ff00_0000_0000),
    }, // 2^64 - 2^40
    Case {
        name: "i64.trunc_f32_u-upper-exclusive",
        opcode: 0xaf,
        input_bits: 0x5f80_0000,
        expected: Expected::Trap("integer_overflow"),
    },
    Case {
        name: "i64.trunc_f32_u-negative-payload-nan",
        opcode: 0xaf,
        input_bits: 0xffc1_2345,
        expected: Expected::Trap("invalid_conversion_to_integer"),
    },
    Case {
        name: "i64.trunc_f64_s-last-below-upper",
        opcode: 0xb0,
        input_bits: 0x43df_ffff_ffff_ffff,
        expected: Expected::Bits(0x7fff_ffff_ffff_fc00),
    }, // 2^63 - 1024
    Case {
        name: "i64.trunc_f64_s-upper-exclusive",
        opcode: 0xb0,
        input_bits: 0x43e0_0000_0000_0000,
        expected: Expected::Trap("integer_overflow"),
    },
    Case {
        name: "i64.trunc_f64_s-negative-infinity",
        opcode: 0xb0,
        input_bits: 0xfff0_0000_0000_0000,
        expected: Expected::Trap("integer_overflow"),
    },
    Case {
        name: "i64.trunc_f64_u-last-below-upper",
        opcode: 0xb1,
        input_bits: 0x43ef_ffff_ffff_ffff,
        expected: Expected::Bits(0xffff_ffff_ffff_f800),
    }, // 2^64 - 2048
    Case {
        name: "i64.trunc_f64_u-next-above-negative-one",
        opcode: 0xb1,
        input_bits: 0xbfef_ffff_ffff_ffff,
        expected: Expected::Bits(0),
    },
    Case {
        name: "i64.trunc_f64_u-negative-one",
        opcode: 0xb1,
        input_bits: 0xbff0_0000_0000_0000,
        expected: Expected::Trap("integer_overflow"),
    },
];

fn width(case: &Case) -> usize {
    match case.opcode {
        0xa8..=0xab => 4,
        0xae..=0xb1 => 8,
        _ => panic!("unsupported conversion case"),
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
    let mut body = vec![0, 0x41, 32]; // no locals; destination address
    match case.opcode {
        0xa8 | 0xa9 | 0xae | 0xaf => {
            body.push(0x43);
            body.extend((case.input_bits as u32).to_le_bytes());
        }
        0xaa | 0xab | 0xb0 | 0xb1 => {
            body.push(0x44);
            body.extend(case.input_bits.to_le_bytes());
        }
        _ => panic!("unsupported conversion case"),
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
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

// This adapter implements only the output ABI. The built-in WebAssembly engine
// executes the conversion; host arithmetic is never used as a conversion oracle.
const ORACLE: &str = r#"
const fs = require('node:fs');
const bytes = Buffer.from(fs.readFileSync(0, 'utf8'), 'hex');
if (!WebAssembly.validate(bytes)) throw new Error('REJECTION stage=node-validation');
const m = new WebAssembly.Module(bytes);
const wasi = Object.fromEntries(WebAssembly.Module.imports(m).map(x =>
  [x.name, () => { throw new Error('unexpected import ' + x.name); }]));
let instance; const output = [];
wasi.fd_write = (fd, ptr, count, written) => {
  if (fd !== 1 || ptr !== 0 || count !== 1 || written !== 16 || output.length)
    throw new Error('unexpected output ABI');
  const memory = instance.exports.memory.buffer, view = new DataView(memory);
  const begin = view.getUint32(ptr, true), size = view.getUint32(ptr + 4, true);
  if (begin !== 32 || ![4, 8].includes(size)) throw new Error('unexpected iovec');
  output.push(Buffer.from(new Uint8Array(memory, begin, size)));
  view.setUint32(written, size, true); return 0;
};
instance = new WebAssembly.Instance(m, {wasi_snapshot_preview1: wasi});
let terminal = 'value';
try { instance.exports._start(); }
catch (e) { if (!(e instanceof WebAssembly.RuntimeError)) throw e; terminal = 'trap'; }
console.log(terminal + ':' + Buffer.concat(output).toString('hex'));
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
        "MODULE case={index} name={} opcode={:02x} input_bits={:016x} hex={}",
        case.name,
        case.opcode,
        case.input_bits,
        hex(&bytes)
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
        .write_all(hex(&bytes).as_bytes());
    let output = child.wait_with_output().expect("UNKNOWN Node reap/output");
    write.expect("Node module transport failed");
    assert!(
        output.status.success(),
        "Node failure case={index}: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stderr.is_empty());
    let expected = match case.expected {
        Expected::Bits(bits) => bits.to_le_bytes()[..width(case)].to_vec(),
        Expected::Trap(_) => vec![],
    };
    let terminal = if matches!(case.expected, Expected::Trap(_)) {
        "trap"
    } else {
        "value"
    };
    let oracle = String::from_utf8(output.stdout).unwrap();
    assert_eq!(
        oracle,
        format!("{terminal}:{}\n", hex(&expected)),
        "independent expectation case={index}"
    );
    println!(
        "ORACLE case={index} pid={pid} reaped=true result={}",
        oracle.trim()
    );

    let proof = validate_swift_command(
        &bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap_or_else(|failure| panic!("REJECTION stage=mixer-validation case={index}: {failure:?}"));
    println!("ADMITTED case={index} stage=mixer-validation");
    let mut stdout = vec![];
    let mut stderr = vec![];
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
    match case.expected {
        Expected::Trap(code) => {
            let failure = report.terminal.expect("expected execution trap");
            assert_eq!(
                failure.kind,
                SwiftRunFailureKind::GuestTrap,
                "case={index}: {failure:?}"
            );
            assert_eq!(failure.code, code, "case={index}: {failure:?}");
            assert!(!report.succeeded());
        }
        Expected::Bits(_) => {
            assert!(report.succeeded(), "case={index}: {report:?}");
            assert!(report.terminal.is_none());
        }
    }
    assert!(!report.output_error);
    assert_eq!(stdout, expected, "case={index} name={}", case.name);
    assert!(stderr.is_empty());
    assert_eq!(
        report.calls_by_function.iter().sum::<u64>(),
        if terminal == "trap" { 0 } else { 1 }
    );
    println!(
        "PARITY case={index} name={} terminal={terminal} bytes={}",
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

fn rejected(output: Output) {
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
        !text.contains("ADMITTED case=")
            && !text.contains("MODULE case=")
            && !text.contains("CLEANUP case=")
    );
    println!("ENVIRONMENT_FAIL_CLOSED status={}", output.status);
}

// There is deliberately no separately discoverable private-worker test. Both
// exact selection and blanket --ignored run this parent, whose children select
// exactly this test and construct one consuming runtime each.
#[test]
#[ignore = "development Node oracle; explicit experimental-swift-reactor corpus"]
fn float_conversions_match_node() {
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
            worker(invalid)
                .output()
                .expect("UNKNOWN environment-control subprocess"),
        );
    }
    rejected(
        worker("0")
            .env_remove("MIXER_NODE")
            .env("PATH", "")
            .output()
            .expect("UNKNOWN missing-Node subprocess"),
    );
    rejected(
        worker("0")
            .env("MIXER_NODE", "relative-node")
            .output()
            .expect("UNKNOWN relative-Node subprocess"),
    );
    for index in 0..CASES.len() {
        let output = worker(&index.to_string())
            .output()
            .expect("UNKNOWN conversion subprocess");
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
    println!("24 original float-conversion cases matched Node; each consumed fourteen zero currents and zero tickets; 7 invalid environments rejected");
}
