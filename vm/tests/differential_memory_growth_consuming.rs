#![cfg(feature = "experimental-swift-reactor")]

#[path = "swift_reactor_validation_fixture.rs"]
mod fixture;

use mixer_vm::experimental_swift_reactor::{
    execute_swift_command, validate_swift_command, SwiftRunBudget, SwiftValidationBudget,
};
use mixer_vm::experimental_wasi::{WasiBudget, WasiGrants};
use mixer_vm::{Cancellation, Type};
use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Output, Stdio};

const TEST: &str = "memory_growth_matches_node";
const CASE_ENV: &str = "MIXER_DIFFERENTIAL_MEMORY_GROWTH_CASE";
const PAGE: i32 = 65_536;
const PAYLOAD: i32 = 64;
const PATTERN: i32 = 0xa7a7_a7a7u32 as i32;

// (delta, returned previous size or -1, resulting size). These expectations
// are authored independently of both engines, including unsigned negative deltas.
struct Case {
    name: &'static str,
    initial: i32,
    maximum: i32,
    steps: &'static [(i32, i32, i32)],
}

const CASES: [Case; 12] = [
    Case {
        name: "grow-zero",
        initial: 1,
        maximum: 3,
        steps: &[(0, 1, 1)],
    },
    Case {
        name: "grow-one",
        initial: 1,
        maximum: 3,
        steps: &[(1, 1, 2)],
    },
    Case {
        name: "exact-declared-maximum",
        initial: 1,
        maximum: 3,
        steps: &[(2, 1, 3)],
    },
    Case {
        name: "grow-zero-at-maximum",
        initial: 2,
        maximum: 2,
        steps: &[(0, 2, 2)],
    },
    Case {
        name: "denied-at-maximum-then-zero",
        initial: 2,
        maximum: 2,
        steps: &[(1, -1, 2), (0, 2, 2)],
    },
    Case {
        name: "oversize-then-one",
        initial: 1,
        maximum: 3,
        steps: &[(3, -1, 1), (1, 1, 2)],
    },
    Case {
        name: "huge-positive-then-exact",
        initial: 1,
        maximum: 3,
        steps: &[(i32::MAX, -1, 1), (2, 1, 3)],
    },
    Case {
        name: "unsigned-minus-one-then-one",
        initial: 1,
        maximum: 3,
        steps: &[(-1, -1, 1), (1, 1, 2)],
    },
    Case {
        name: "unsigned-sign-bit-then-exact",
        initial: 1,
        maximum: 3,
        steps: &[(i32::MIN, -1, 1), (2, 1, 3)],
    },
    Case {
        name: "success-denial-zero",
        initial: 1,
        maximum: 3,
        steps: &[(1, 1, 2), (1, 2, 3), (1, -1, 3), (0, 3, 3)],
    },
    Case {
        name: "two-denials-then-two-successes",
        initial: 1,
        maximum: 4,
        steps: &[(-1, -1, 1), (4, -1, 1), (1, 1, 2), (2, 2, 4)],
    },
    Case {
        name: "two-initial-pages-then-denial",
        initial: 2,
        maximum: 3,
        steps: &[(1, 2, 3), (1, -1, 3)],
    },
];

fn constant(body: &mut Vec<u8>, value: i32) {
    body.push(0x41);
    body.extend(fixture::signed(value));
}

fn fill(body: &mut Vec<u8>, begin: i32, end: i32) {
    for value in [begin, 0xa7, end - begin] {
        constant(body, value);
    }
    body.extend([0xfc, 11, 0]);
}

fn scan(body: &mut Vec<u8>, destination: i32, begin: i32, end: i32, expected: i32) {
    constant(body, destination);
    for value in [begin, end, expected] {
        constant(body, value);
    }
    body.extend([0x10, 35, 0x36, 2, 0]);
}

fn module(case: &Case) -> Vec<u8> {
    let mut f = fixture::Fixture::default();
    f.types
        .push(fixture::signature(&[Type::I32; 3], &[Type::I32]));
    f.function_types = vec![34, 36];
    f.memory = vec![1, 1];
    f.memory.extend(fixture::uint(case.initial as u32));
    f.memory.extend(fixture::uint(case.maximum as u32));
    f.table = vec![1, 0x70, 1, 1, 1];
    f.exports = vec![(b"memory".to_vec(), 2, 0), (b"_start".to_vec(), 0, 34)];
    let fd_write = f
        .imports
        .iter()
        .position(|(_, name, _, _)| name == b"fd_write")
        .unwrap();
    let mut body = vec![0];
    fill(&mut body, PAYLOAD, case.initial * PAGE);
    let mut before = case.initial;
    for &(delta, _, after) in case.steps {
        constant(&mut body, 32);
        body.extend([0x3f, 0, 0x36, 2, 0]);
        constant(&mut body, 36);
        constant(&mut body, delta);
        body.extend([0x40, 0, 0x36, 2, 0]);
        constant(&mut body, 40);
        body.extend([0x3f, 0, 0x36, 2, 0]);
        scan(&mut body, 44, PAYLOAD, before * PAGE, PATTERN);
        scan(&mut body, 48, before * PAGE, after * PAGE, 0);
        for value in [1, 0, 1, 16] {
            constant(&mut body, value);
        }
        body.push(0x10);
        body.extend(fixture::uint(fd_write as u32));
        body.push(0x1a);
        // Dirty every newly admitted byte only after observing its initial zero
        // value. A later grow must preserve that page as well as initial pages.
        if after > before {
            fill(&mut body, before * PAGE, after * PAGE);
        }
        before = after;
    }
    body.push(0x0b);
    // scan(begin, end, expected) ORs every word's XOR into a local accumulator.
    // Four-byte strides cover every payload byte; the first 64 bytes are ABI
    // scratch. Empty new ranges on denial/grow0 still yield a zero accumulator.
    let scanner = vec![
        1, 1, 0x7f, // one i32 local, after three i32 parameters
        0x02, 0x40, 0x03, 0x40, // block; loop
        0x20, 0, 0x20, 1, 0x4f, 0x0d, 1, // begin >= end: break
        0x20, 3, 0x20, 0, 0x28, 2, 0, 0x20, 2, 0x73, 0x72, 0x21, 3, 0x20, 0, 0x41, 4, 0x6a, 0x21,
        0, 0x0c, 0, 0x0b, 0x0b, 0x20, 3, 0x0b,
    ];
    f.bodies = vec![body, scanner];
    let mut iovec = 32u32.to_le_bytes().to_vec();
    iovec.extend(20u32.to_le_bytes());
    f.data = vec![fixture::data_segment(0, &iovec)];
    f.bytes()
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

// This adapter observes only the output ABI. Node's built-in Wasm engine runs
// the original module, including memory.size/grow and the full payload scans.
const ORACLE: &str = r#"
const fs = require('node:fs');
const bytes = Buffer.from(fs.readFileSync(0, 'utf8'), 'hex');
if (!WebAssembly.validate(bytes)) throw new Error('REJECTION stage=node-validation');
const wasmModule = new WebAssembly.Module(bytes);
const wasi = Object.fromEntries(WebAssembly.Module.imports(wasmModule).map(x =>
  [x.name, () => { throw new Error('unexpected import ' + x.name); }]));
let instance; const output = [];
wasi.fd_write = (fd, ptr, count, written) => {
  if (fd !== 1 || ptr !== 0 || count !== 1 || written !== 16 || output.length >= 4)
    throw new Error('unexpected output ABI');
  const memory = instance.exports.memory.buffer, view = new DataView(memory);
  const begin = view.getUint32(ptr, true), size = view.getUint32(ptr + 4, true);
  if (begin !== 32 || size !== 20) throw new Error('unexpected iovec');
  output.push(Buffer.from(new Uint8Array(memory, begin, size)));
  view.setUint32(written, size, true); return 0;
};
instance = new WebAssembly.Instance(wasmModule, {wasi_snapshot_preview1: wasi});
instance.exports._start();
console.log(Buffer.concat(output).toString('hex'));
"#;

fn node_path() -> PathBuf {
    let path = PathBuf::from(
        std::env::var_os("MIXER_NODE").expect("ENVIRONMENT_REJECTED: MIXER_NODE required"),
    );
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
        "MODULE case={index} name={} initial={} declared_maximum={} steps={:?} hex={}",
        case.name,
        case.initial,
        case.maximum,
        case.steps,
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
        .write_all(hex(&bytes).as_bytes());
    let output = child.wait_with_output().expect("UNKNOWN Node reap/output");
    write.expect("Node module transport failed");
    assert!(
        output.status.success(),
        "Node failure case={index}: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stderr.is_empty());
    let mut expected = vec![];
    let mut before = case.initial;
    for &(_, previous, after) in case.steps {
        for value in [before, previous, after, 0, 0] {
            expected.extend(value.to_le_bytes());
        }
        before = after;
    }
    let oracle = String::from_utf8(output.stdout).unwrap();
    assert_eq!(
        oracle,
        format!("{}\n", hex(&expected)),
        "independent expectation case={index}"
    );
    println!(
        "ORACLE case={index} pid={pid} reaped=true bytes={}",
        oracle.trim()
    );

    let validation_budget = SwiftValidationBudget::default();
    let run_budget = SwiftRunBudget::default();
    let wasi_budget = WasiBudget::default();
    assert!((case.maximum as u32) < run_budget.memory_pages);
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
    assert_eq!(stdout, expected, "case={index} name={}", case.name);
    assert_eq!(hex(&stdout), oracle.trim(), "Node parity case={index}");
    assert_eq!(
        report.calls_by_function.iter().sum::<u64>(),
        case.steps.len() as u64
    );
    println!(
        "PARITY case={index} name={} steps={} bytes={}",
        case.name,
        case.steps.len(),
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

// Exact and blanket discovery both reach this sole test. Its selected children
// each execute one case with one consuming runtime; rejection controls use none.
#[test]
#[ignore = "development Node oracle; explicit experimental-swift-reactor corpus"]
fn memory_growth_matches_node() {
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
    for invalid in ["", "-1", "12", "01", "not-an-index"] {
        rejected(
            worker(invalid)
                .output()
                .expect("UNKNOWN environment-control subprocess"),
        );
    }
    rejected(
        worker("0")
            .env_remove("MIXER_NODE")
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
            .expect("UNKNOWN memory-growth subprocess");
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
    println!("12 original memory-growth cases matched Node; each consumed fourteen zero currents and zero tickets; 7 invalid environments rejected");
}
