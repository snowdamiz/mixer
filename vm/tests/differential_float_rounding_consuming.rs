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

const TEST: &str = "float_rounding_matches_node";
const CASE_ENV: &str = "MIXER_DIFFERENTIAL_FLOAT_ROUNDING_CASE";

#[derive(Clone, Copy, Debug)]
enum Expected {
    Bits(u64),
    CanonicalNaN,
    ArithmeticNaN,
}
struct Case {
    name: &'static str,
    opcode: u8,
    inputs: &'static [u64],
    expected: &'static [Expected],
}

// Original IEEE literals: no host rounding computes the expected values.
// Each operation/width has four modules: zeros, fractions, large integral values
// and infinities, then canonical/quiet/signaling NaNs. All finite results are
// exact output bits; NaNs use the Core permitted classes independently in Node.
const ZERO32: &[u64] = &[0, 0x80000000];
const ZERO64: &[u64] = &[0, 0x8000000000000000];
const FRAC32: &[u64] = &[
    0x3f000000, 0xbf000000, // +/-0.5
    0x3fc00000, 0xbfc00000, // +/-1.5
    0x40200000, 0xc0200000, // +/-2.5
    0x3e800000, 0xbe800000, // +/-0.25
    0x40300000, 0xc0300000, // +/-2.75
    0x00000001, 0x80000001, // smallest +/-subnormal
];
const FRAC64: &[u64] = &[
    0x3fe0000000000000,
    0xbfe0000000000000,
    0x3ff8000000000000,
    0xbff8000000000000,
    0x4004000000000000,
    0xc004000000000000,
    0x3fd0000000000000,
    0xbfd0000000000000,
    0x4006000000000000,
    0xc006000000000000,
    0x0000000000000001,
    0x8000000000000001,
];
const LARGE32: &[u64] = &[0x7f7fffff, 0xff7fffff, 0x7f800000, 0xff800000];
const LARGE64: &[u64] = &[
    0x7fefffffffffffff,
    0xffefffffffffffff,
    0x7ff0000000000000,
    0xfff0000000000000,
];
const NAN32: &[u64] = &[0x7fc00000, 0xffc00000, 0x7fe57239, 0xff800123];
const NAN64: &[u64] = &[
    0x7ff8000000000000,
    0xfff8000000000000,
    0x7ffb572913a64c81,
    0xfff0000000000123,
];
use Expected::{ArithmeticNaN as A, Bits as B, CanonicalNaN as C};
const CASES: [Case; 32] = [
    Case {
        name: "f32.ceil-zeros",
        opcode: 0x8d,
        inputs: ZERO32,
        expected: &[B(0), B(0x80000000)],
    },
    Case {
        name: "f32.ceil-fractions",
        opcode: 0x8d,
        inputs: FRAC32,
        expected: &[
            B(0x3f800000),
            B(0x80000000),
            B(0x40000000),
            B(0xbf800000),
            B(0x40400000),
            B(0xc0000000),
            B(0x3f800000),
            B(0x80000000),
            B(0x40400000),
            B(0xc0000000),
            B(0x3f800000),
            B(0x80000000),
        ],
    },
    Case {
        name: "f32.ceil-large-infinities",
        opcode: 0x8d,
        inputs: LARGE32,
        expected: &[B(0x7f7fffff), B(0xff7fffff), B(0x7f800000), B(0xff800000)],
    },
    Case {
        name: "f32.ceil-nans",
        opcode: 0x8d,
        inputs: NAN32,
        expected: &[C, C, A, A],
    },
    Case {
        name: "f32.floor-zeros",
        opcode: 0x8e,
        inputs: ZERO32,
        expected: &[B(0), B(0x80000000)],
    },
    Case {
        name: "f32.floor-fractions",
        opcode: 0x8e,
        inputs: FRAC32,
        expected: &[
            B(0),
            B(0xbf800000),
            B(0x3f800000),
            B(0xc0000000),
            B(0x40000000),
            B(0xc0400000),
            B(0),
            B(0xbf800000),
            B(0x40000000),
            B(0xc0400000),
            B(0),
            B(0xbf800000),
        ],
    },
    Case {
        name: "f32.floor-large-infinities",
        opcode: 0x8e,
        inputs: LARGE32,
        expected: &[B(0x7f7fffff), B(0xff7fffff), B(0x7f800000), B(0xff800000)],
    },
    Case {
        name: "f32.floor-nans",
        opcode: 0x8e,
        inputs: NAN32,
        expected: &[C, C, A, A],
    },
    Case {
        name: "f32.trunc-zeros",
        opcode: 0x8f,
        inputs: ZERO32,
        expected: &[B(0), B(0x80000000)],
    },
    Case {
        name: "f32.trunc-fractions",
        opcode: 0x8f,
        inputs: FRAC32,
        expected: &[
            B(0),
            B(0x80000000),
            B(0x3f800000),
            B(0xbf800000),
            B(0x40000000),
            B(0xc0000000),
            B(0),
            B(0x80000000),
            B(0x40000000),
            B(0xc0000000),
            B(0),
            B(0x80000000),
        ],
    },
    Case {
        name: "f32.trunc-large-infinities",
        opcode: 0x8f,
        inputs: LARGE32,
        expected: &[B(0x7f7fffff), B(0xff7fffff), B(0x7f800000), B(0xff800000)],
    },
    Case {
        name: "f32.trunc-nans",
        opcode: 0x8f,
        inputs: NAN32,
        expected: &[C, C, A, A],
    },
    Case {
        name: "f32.nearest-zeros",
        opcode: 0x90,
        inputs: ZERO32,
        expected: &[B(0), B(0x80000000)],
    },
    Case {
        name: "f32.nearest-fractions",
        opcode: 0x90,
        inputs: FRAC32,
        expected: &[
            B(0),
            B(0x80000000),
            B(0x40000000),
            B(0xc0000000),
            B(0x40000000),
            B(0xc0000000),
            B(0),
            B(0x80000000),
            B(0x40400000),
            B(0xc0400000),
            B(0),
            B(0x80000000),
        ],
    },
    Case {
        name: "f32.nearest-large-infinities",
        opcode: 0x90,
        inputs: LARGE32,
        expected: &[B(0x7f7fffff), B(0xff7fffff), B(0x7f800000), B(0xff800000)],
    },
    Case {
        name: "f32.nearest-nans",
        opcode: 0x90,
        inputs: NAN32,
        expected: &[C, C, A, A],
    },
    Case {
        name: "f64.ceil-zeros",
        opcode: 0x9b,
        inputs: ZERO64,
        expected: &[B(0), B(0x8000000000000000)],
    },
    Case {
        name: "f64.ceil-fractions",
        opcode: 0x9b,
        inputs: FRAC64,
        expected: &[
            B(0x3ff0000000000000),
            B(0x8000000000000000),
            B(0x4000000000000000),
            B(0xbff0000000000000),
            B(0x4008000000000000),
            B(0xc000000000000000),
            B(0x3ff0000000000000),
            B(0x8000000000000000),
            B(0x4008000000000000),
            B(0xc000000000000000),
            B(0x3ff0000000000000),
            B(0x8000000000000000),
        ],
    },
    Case {
        name: "f64.ceil-large-infinities",
        opcode: 0x9b,
        inputs: LARGE64,
        expected: &[
            B(0x7fefffffffffffff),
            B(0xffefffffffffffff),
            B(0x7ff0000000000000),
            B(0xfff0000000000000),
        ],
    },
    Case {
        name: "f64.ceil-nans",
        opcode: 0x9b,
        inputs: NAN64,
        expected: &[C, C, A, A],
    },
    Case {
        name: "f64.floor-zeros",
        opcode: 0x9c,
        inputs: ZERO64,
        expected: &[B(0), B(0x8000000000000000)],
    },
    Case {
        name: "f64.floor-fractions",
        opcode: 0x9c,
        inputs: FRAC64,
        expected: &[
            B(0),
            B(0xbff0000000000000),
            B(0x3ff0000000000000),
            B(0xc000000000000000),
            B(0x4000000000000000),
            B(0xc008000000000000),
            B(0),
            B(0xbff0000000000000),
            B(0x4000000000000000),
            B(0xc008000000000000),
            B(0),
            B(0xbff0000000000000),
        ],
    },
    Case {
        name: "f64.floor-large-infinities",
        opcode: 0x9c,
        inputs: LARGE64,
        expected: &[
            B(0x7fefffffffffffff),
            B(0xffefffffffffffff),
            B(0x7ff0000000000000),
            B(0xfff0000000000000),
        ],
    },
    Case {
        name: "f64.floor-nans",
        opcode: 0x9c,
        inputs: NAN64,
        expected: &[C, C, A, A],
    },
    Case {
        name: "f64.trunc-zeros",
        opcode: 0x9d,
        inputs: ZERO64,
        expected: &[B(0), B(0x8000000000000000)],
    },
    Case {
        name: "f64.trunc-fractions",
        opcode: 0x9d,
        inputs: FRAC64,
        expected: &[
            B(0),
            B(0x8000000000000000),
            B(0x3ff0000000000000),
            B(0xbff0000000000000),
            B(0x4000000000000000),
            B(0xc000000000000000),
            B(0),
            B(0x8000000000000000),
            B(0x4000000000000000),
            B(0xc000000000000000),
            B(0),
            B(0x8000000000000000),
        ],
    },
    Case {
        name: "f64.trunc-large-infinities",
        opcode: 0x9d,
        inputs: LARGE64,
        expected: &[
            B(0x7fefffffffffffff),
            B(0xffefffffffffffff),
            B(0x7ff0000000000000),
            B(0xfff0000000000000),
        ],
    },
    Case {
        name: "f64.trunc-nans",
        opcode: 0x9d,
        inputs: NAN64,
        expected: &[C, C, A, A],
    },
    Case {
        name: "f64.nearest-zeros",
        opcode: 0x9e,
        inputs: ZERO64,
        expected: &[B(0), B(0x8000000000000000)],
    },
    Case {
        name: "f64.nearest-fractions",
        opcode: 0x9e,
        inputs: FRAC64,
        expected: &[
            B(0),
            B(0x8000000000000000),
            B(0x4000000000000000),
            B(0xc000000000000000),
            B(0x4000000000000000),
            B(0xc000000000000000),
            B(0),
            B(0x8000000000000000),
            B(0x4008000000000000),
            B(0xc008000000000000),
            B(0),
            B(0x8000000000000000),
        ],
    },
    Case {
        name: "f64.nearest-large-infinities",
        opcode: 0x9e,
        inputs: LARGE64,
        expected: &[
            B(0x7fefffffffffffff),
            B(0xffefffffffffffff),
            B(0x7ff0000000000000),
            B(0xfff0000000000000),
        ],
    },
    Case {
        name: "f64.nearest-nans",
        opcode: 0x9e,
        inputs: NAN64,
        expected: &[C, C, A, A],
    },
];

fn width(case: &Case) -> usize {
    match case.opcode {
        0x8d..=0x90 => 4,
        0x9b..=0x9e => 8,
        _ => panic!("unsupported float-rounding opcode"),
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
    let w = width(case);
    assert_eq!(case.inputs.len(), case.expected.len());
    let mut body = vec![0];
    for (index, bits) in case.inputs.iter().enumerate() {
        body.push(0x41);
        body.extend(fixture::signed((32 + index * w) as i32));
        body.push(if w == 4 { 0x43 } else { 0x44 });
        body.extend_from_slice(&bits.to_le_bytes()[..w]);
        body.extend([case.opcode, if w == 4 { 0x38 } else { 0x39 }, 0, 0]);
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
    iovec.extend(((w * case.inputs.len()) as u32).to_le_bytes());
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
const [width, countText, encoded] = fs.readFileSync(0, 'utf8').split('\n');
const resultCount = Number(countText);
if (!Number.isInteger(resultCount) || resultCount < 1 || resultCount > 12) throw new Error('count');
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
  if (view.getUint32(ptr, true) !== 32 || view.getUint32(ptr + 4, true) !== Number(width) * resultCount)
    throw new Error('unexpected iovec');
  value = Array.from({length: resultCount}, (_, i) =>
    (width === '4' ? view.getUint32(32 + i * 4, true) : view.getBigUint64(32 + i * 8, true)).toString()).join(',');
  view.setUint32(written, Number(width) * resultCount, true); return 0;
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

fn classified(case: &Case, expected: Expected, bits: u64) -> String {
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
    match expected {
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
        "MODULE case={index} name={} opcode={:02x} inputs={:x?} expected={:?} hex={}",
        case.name,
        case.opcode,
        case.inputs,
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
    let write =
        child.stdin.take().unwrap().write_all(
            format!("{}\n{}\n{}", width(case), case.inputs.len(), hex(&bytes)).as_bytes(),
        );
    let output = child.wait_with_output().expect("UNKNOWN Node reap/output");
    write.expect("Node module transport failed");
    assert!(
        output.status.success(),
        "Node case={index}: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stderr.is_empty());
    let oracle = String::from_utf8(output.stdout).unwrap();
    let oracle_bits: Vec<u64> = oracle
        .strip_suffix('\n')
        .unwrap()
        .split(',')
        .map(|raw| raw.parse().expect("Node bit result"))
        .collect();
    assert_eq!(oracle_bits.len(), case.expected.len());
    let oracle_classes: Vec<_> = case
        .expected
        .iter()
        .zip(&oracle_bits)
        .map(|(&expected, &bits)| classified(case, expected, bits))
        .collect();
    println!("ORACLE case={index} pid={pid} reaped=true bits={oracle_bits:x?} classes={oracle_classes:?}");

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
    assert_eq!(stdout.len(), width(case) * case.expected.len());
    let bits: Vec<u64> = stdout
        .chunks_exact(width(case))
        .map(|bytes| match width(case) {
            4 => u32::from_le_bytes(bytes.try_into().unwrap()) as u64,
            8 => u64::from_le_bytes(bytes.try_into().unwrap()),
            _ => unreachable!(),
        })
        .collect();
    for (item, ((&bits, &expected), oracle_class)) in bits
        .iter()
        .zip(case.expected)
        .zip(&oracle_classes)
        .enumerate()
    {
        assert_eq!(
            classified(case, expected, bits),
            *oracle_class,
            "Node parity case={index} item={item}"
        );
        if !matches!(expected, Expected::Bits(_)) {
            assert_eq!(
                bits,
                if width(case) == 4 {
                    0x7fc00000
                } else {
                    0x7ff8000000000000
                },
                "Mixer canonical NaN contract case={index} item={item}"
            );
        }
    }
    assert_eq!(report.calls_by_function.iter().sum::<u64>(), 1);
    println!("PARITY case={index} name={} node={oracle_bits:x?} mixer={bits:x?} classes={oracle_classes:?} bytes={}", case.name, hex(&stdout));
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

// Only this parent is discoverable; each ordinary helper reenters this exact
// test, with one canonical selector and one consuming runtime in that process.
#[test]
#[ignore = "development Node oracle; explicit experimental-swift-reactor corpus"]
fn float_rounding_matches_node() {
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
        PathBuf::from("/mixer-float-rounding-missing-node"),
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
        }
        let output = command.output().expect("UNKNOWN float-rounding subprocess");
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
    println!("32 original float-rounding modules matched Node; 144 bit-exact and 32 allowed-NaN results; 14 zero currents and 0 tickets each; 15 environment controls rejected; unset-only PATH discovery exercised");
}
