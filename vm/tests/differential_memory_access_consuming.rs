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
use std::os::unix::{ffi::OsStringExt, fs::PermissionsExt};
use std::path::PathBuf;
use std::process::{Command, Output, Stdio};

const TEST: &str = "scalar_memory_access_matches_node";
const CASE_ENV: &str = "MIXER_DIFFERENTIAL_MEMORY_ACCESS_CASE";

struct Case {
    name: &'static str,
    opcode: u8,
    address: i32,
    offset: u32,
    expected: &'static str,
    traps: bool,
}

const fn value(
    name: &'static str,
    opcode: u8,
    address: i32,
    offset: u32,
    expected: &'static str,
) -> Case {
    Case {
        name,
        opcode,
        address,
        offset,
        expected,
        traps: false,
    }
}
const fn trap(name: &'static str, opcode: u8, address: i32, offset: u32) -> Case {
    Case {
        name,
        opcode,
        address,
        offset,
        expected: "",
        traps: true,
    }
}

// These literal modules complement the generic zero-offset address grid.
// Every successful access uses a nonzero memarg offset. Stores expose both
// neighboring sentinels and all written bytes, rather than a round-trip load
// of the same width that could hide endian or overwrite errors.
const CASES: [Case; 24] = [
    value("i32.load-unaligned-little-endian", 0x28, 125, 4, "81234589"),
    value(
        "i64.load-exact-end-offset",
        0x29,
        65521,
        7,
        "1122334455667788",
    ),
    value("i32.load8_s-negative", 0x2c, 128, 1, "81ffffff"),
    value("i32.load8_u-high-bit", 0x2d, 128, 1, "81000000"),
    value("i32.load16_s-unaligned-negative", 0x2e, 128, 3, "4589ffff"),
    value("i32.load16_u-unaligned-high-bit", 0x2f, 128, 3, "45890000"),
    value("i64.load8_s-negative", 0x30, 128, 1, "81ffffffffffffff"),
    value("i64.load8_u-high-bit", 0x31, 128, 1, "8100000000000000"),
    value(
        "i64.load16_s-unaligned-negative",
        0x32,
        128,
        3,
        "4589ffffffffffff",
    ),
    value(
        "i64.load16_u-unaligned-high-bit",
        0x33,
        128,
        3,
        "4589000000000000",
    ),
    value(
        "i64.load32_s-unaligned-negative",
        0x34,
        125,
        4,
        "81234589ffffffff",
    ),
    value(
        "i64.load32_u-unaligned-high-bit",
        0x35,
        125,
        4,
        "8123458900000000",
    ),
    value(
        "i32.store-unaligned-guarded",
        0x36,
        129,
        4,
        "a581234589a3b4c5d6a5a5a5a5a5a5a5",
    ),
    value(
        "i64.store-unaligned-guarded",
        0x37,
        129,
        4,
        "a5812345898897a6b5c4d3e2f1a5a5a5",
    ),
    value(
        "i32.store8-truncate-dirty-upper",
        0x3a,
        129,
        4,
        "a581234589a3cdef92a5a5a5a5a5a5a5",
    ),
    value(
        "i32.store16-truncate-dirty-upper",
        0x3b,
        129,
        4,
        "a581234589a3b4ef92a5a5a5a5a5a5a5",
    ),
    value(
        "i64.store8-truncate-dirty-upper",
        0x3c,
        129,
        4,
        "a58123458988cdef92a5a5a5a5a5a5a5",
    ),
    value(
        "i64.store16-truncate-dirty-upper",
        0x3d,
        129,
        4,
        "a5812345898897ef92a5a5a5a5a5a5a5",
    ),
    value(
        "i64.store32-truncate-dirty-upper",
        0x3e,
        129,
        4,
        "a5812345898897a6b5a5a5a5a5a5a5a5",
    ),
    trap("i32.load-cross-end-one-byte", 0x28, 65533, 0),
    trap("i64.load-offset-cross-end", 0x29, 65528, 1),
    trap("i32.load8_u-effective-address-no-wrap", 0x2d, -1, 1),
    trap("i32.store8-max-offset-no-wrap", 0x3a, 1, u32::MAX),
    trap("i64.store32-offset-cross-end", 0x3e, 65532, 1),
];

fn constant(body: &mut Vec<u8>, wide: bool, mut value: i64) {
    if !wide {
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
    let store = case.opcode >= 0x36;
    let wide = case.opcode == 0x29 || (0x30..=0x35).contains(&case.opcode);
    let mut body = vec![0];
    if !store {
        constant(&mut body, false, 32);
    }
    constant(&mut body, false, case.address as i64);
    if store {
        let wide_store = case.opcode == 0x37 || case.opcode >= 0x3c;
        constant(
            &mut body,
            wide_store,
            if wide_store {
                0xf1e2_d3c4_b5a6_9788u64 as i64
            } else {
                0xd6c5_b4a3u32 as i32 as i64
            },
        );
    }
    body.extend([case.opcode, 0]); // alignment hint 1 permits unaligned accesses
    body.extend(fixture::uint(case.offset));
    if !store {
        body.extend([if wide { 0x37 } else { 0x36 }, 0, 0]);
    }
    for v in [1, 0, 1, 16] {
        constant(&mut body, false, v);
    }
    body.push(0x10);
    body.extend(fixture::uint(fd_write as u32));
    body.extend([0x1a, 0x0b]);
    f.bodies = vec![body];
    let begin: u32 = if store { 128 } else { 32 };
    let size: u32 = if store {
        16
    } else if wide {
        8
    } else {
        4
    };
    let mut iovec = begin.to_le_bytes().to_vec();
    iovec.extend(size.to_le_bytes());
    f.data = vec![
        fixture::data_segment(0, &iovec),
        fixture::data_segment(
            128,
            &[
                0xa5, 0x81, 0x23, 0x45, 0x89, 0xab, 0xcd, 0xef, 0x92, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5,
                0xa5, 0xa5,
            ],
        ),
        fixture::data_segment(65528, &[0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88]),
    ];
    f.bytes()
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

// Node's WebAssembly engine executes the same bytes; JS only captures fd_write.
// Neither the operation nor an i64 result passes through JS Number arithmetic.
const ORACLE: &str = r#"
const fs = require('node:fs');
const bytes = Buffer.from(fs.readFileSync(0, 'utf8'), 'hex');
if (!WebAssembly.validate(bytes)) throw new Error('REJECTION stage=node-validation');
const m = new WebAssembly.Module(bytes);
const wasi = Object.fromEntries(WebAssembly.Module.imports(m).map(x =>
  [x.name, () => { throw new Error('unexpected import ' + x.name); }]));
let instance; const output = [];
wasi.fd_write = (fd, ptr, count, written) => {
  if (fd !== 1 || ptr !== 0 || count !== 1 || written !== 16 || output.length !== 0)
    throw new Error('unexpected output ABI');
  const memory = instance.exports.memory.buffer, view = new DataView(memory);
  const begin = view.getUint32(ptr, true), size = view.getUint32(ptr + 4, true);
  if (!((begin === 32 && [4, 8].includes(size)) || (begin === 128 && size === 16)))
    throw new Error('unexpected iovec');
  output.push(Buffer.from(new Uint8Array(memory, begin, size)));
  view.setUint32(written, size, true); return 0;
};
instance = new WebAssembly.Instance(m, {wasi_snapshot_preview1: wasi});
let terminal = 'value';
try { instance.exports._start(); }
catch (e) {
  if (!(e instanceof WebAssembly.RuntimeError) || !/out of bounds/i.test(e.message)) throw e;
  terminal = 'memory_out_of_bounds';
}
if (terminal === 'value' && output.length !== 1) throw new Error('missing output');
console.log(terminal + ':' + Buffer.concat(output).toString('hex'));
"#;

fn node_path() -> PathBuf {
    let executable = |p: &PathBuf| {
        p.is_absolute()
            && p.is_file()
            && p.metadata()
                .is_ok_and(|m| m.permissions().mode() & 0o111 != 0)
    };
    let path = match std::env::var_os("MIXER_NODE") {
        Some(explicit) => PathBuf::from(explicit),
        None => std::env::var_os("PATH")
            .and_then(|paths| {
                std::env::split_paths(&paths)
                    .map(|p| p.join("node"))
                    .find(executable)
            })
            .expect("ENVIRONMENT_REJECTED: Node executable required"),
    };
    assert!(
        executable(&path),
        "ENVIRONMENT_REJECTED: absolute executable Node required"
    );
    path
}

fn isolated_case(index: usize, node: PathBuf) {
    let case = &CASES[index];
    let bytes = module(case);
    println!("MODULE case={index} name={} opcode={:02x} address={} offset={} traps={} expected={} hex={}",
        case.name, case.opcode, case.address, case.offset, case.traps, case.expected, hex(&bytes));
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
        "Node case={index}: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stderr.is_empty());
    let oracle = String::from_utf8(output.stdout).unwrap();
    let terminal = if case.traps {
        "memory_out_of_bounds"
    } else {
        "value"
    };
    assert_eq!(
        oracle,
        format!("{terminal}:{}\n", case.expected),
        "independent literal case={index}"
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
    // Consume before any result assertion, including on a semantic mismatch.
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
    if case.traps {
        assert!(!report.succeeded());
        let failure = report.terminal.expect("execution trap required");
        assert_eq!(failure.kind, SwiftRunFailureKind::GuestTrap);
        assert_eq!(failure.code, "memory_out_of_bounds");
    } else {
        assert!(report.succeeded(), "case={index}: {report:?}");
        assert!(report.terminal.is_none());
    }
    assert!(!report.output_error);
    assert!(stderr.is_empty());
    assert_eq!(
        format!("{terminal}:{}\n", hex(&stdout)),
        oracle,
        "Node parity case={index}"
    );
    assert_eq!(
        report.calls_by_function.iter().sum::<u64>(),
        if case.traps { 0 } else { 1 }
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

#[test]
#[ignore = "development Node oracle; explicit experimental-swift-reactor corpus"]
fn scalar_memory_access_matches_node() {
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
        PathBuf::from("/mixer-memory-access-missing-node"),
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
        let output = command.output().expect("UNKNOWN memory-access subprocess");
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
    println!("24 original scalar-memory modules matched Node; 19 successes and 5 bounds traps; 14 zero currents and 0 tickets each; 15 environment controls rejected");
}
