#![cfg(feature = "experimental-swift-reactor")]

#[path = "common/mod.rs"]
mod common;
#[path = "swift_reactor_validation_fixture.rs"]
mod fixture;

use mixer_vm::experimental_swift_reactor::{
    execute_swift_command, validate_swift_command, SwiftRunBudget, SwiftRunFailureKind,
    SwiftValidationBudget,
};
use mixer_vm::experimental_wasi::{WasiBudget, WasiGrants};
use mixer_vm::{Cancellation, Type, Value};
use std::io::Write;
use std::process::{Command, Stdio};

const SELECTORS: [i32; 8] = [0, 1, 2, 5, -1, 3, 4, i32::MIN];
const TEST: &str = "indirect_calls_match_node";
const CASE_ENV: &str = "MIXER_DIFFERENTIAL_INDIRECT_CASE";

// Original binary modules, following the Core call_indirect execution contract:
// https://webassembly.github.io/spec/core/exec/instructions.html#exec-call-indirect
// A fixed five-slot table has subtract, add, null, wrong-result and wrong-arity
// entries. The caller receives the selector as a parameter, above two operands.
fn module(wide: bool, selector: i32) -> Vec<u8> {
    let ty = if wide { Type::I64 } else { Type::I32 };
    let other = if wide { Type::I32 } else { Type::I64 };
    let mut f = fixture::Fixture::default();
    f.types.extend([
        fixture::signature(&[ty, ty], &[ty]), // 36: actual callee type
        fixture::signature(&[ty, ty], &[ty]), // 37: distinct, structurally equal
        fixture::signature(&[ty, ty], &[other]), // 38: wrong result
        fixture::signature(&[ty], &[ty]),     // 39: wrong parameter count
        fixture::signature(&[Type::I32], &[ty]), // 40: selector -> result
    ]);
    f.function_types = vec![34, 40, 36, 36, 38, 39];
    f.memory = vec![1, 1, 1, 1]; // one fixed page
    f.table = vec![1, 0x70, 1, 5, 5];
    f.exports = vec![(b"memory".to_vec(), 2, 0), (b"_start".to_vec(), 0, 34)];
    f.elements = vec![
        vec![0, 0x41, 0, 0x0b, 2, 36, 37],
        vec![0, 0x41, 3, 0x0b, 2, 38, 39],
    ];

    let value = |n| {
        common::constant(if wide {
            Value::I64(n)
        } else {
            Value::I32(n as i32)
        })
    };
    // The i32 subtraction wraps; both i64 results exceed JS's exact Number range.
    let left = if wide {
        9_007_199_254_740_993
    } else {
        i64::from(i32::MAX)
    };
    let mut dispatch = vec![0];
    dispatch.extend(value(left));
    dispatch.extend(value(-19));
    dispatch.extend([0x20, 0, 0x11, 37, 0, 0x0b]);

    let fd_write = f
        .imports
        .iter()
        .position(|(_, field, _, _)| field == b"fd_write")
        .unwrap();
    let mut start = vec![0, 0x41, 32];
    start.extend(common::constant(Value::I32(selector)));
    start.extend([0x10, 35, if wide { 0x37 } else { 0x36 }, 0, 0]);
    for n in [1, 0, 1, 16] {
        start.extend(common::constant(Value::I32(n)));
    }
    start.push(0x10);
    start.extend(fixture::uint(fd_write as u32));
    start.extend([0x1a, 0x0b]);
    let mut wrong_result = vec![0];
    wrong_result.extend(common::constant(if wide {
        Value::I32(99)
    } else {
        Value::I64(99)
    }));
    wrong_result.push(0x0b);
    f.bodies = vec![
        start,
        dispatch,
        vec![0, 0x20, 0, 0x20, 1, if wide { 0x7d } else { 0x6b }, 0x0b],
        vec![0, 0x20, 0, 0x20, 1, if wide { 0x7c } else { 0x6a }, 0x0b],
        wrong_result,
        vec![0, 0x20, 0, 0x0b],
    ];
    let mut iovec = 32u32.to_le_bytes().to_vec();
    iovec.extend((if wide { 8u32 } else { 4u32 }).to_le_bytes());
    let mut segment = vec![0, 0x41, 0, 0x0b];
    segment.extend(fixture::uint(iovec.len() as u32));
    segment.extend(iovec);
    f.data = vec![segment];
    f.bytes()
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

// Only the output ABI is bridged here. Node executes the original module and
// reports RuntimeError separately from validation/instantiation/host failures.
const ORACLE: &str = r#"
const fs = require('node:fs');
const bytes = Buffer.from(fs.readFileSync(0, 'utf8'), 'hex');
if (!WebAssembly.validate(bytes)) throw new Error('REJECTION stage=node-validation');
const m = new WebAssembly.Module(bytes);
const wasi = Object.fromEntries(WebAssembly.Module.imports(m).map(x =>
  [x.name, () => { throw new Error('unexpected import ' + x.name); }]));
let instance; const output = [];
wasi.fd_write = (fd, ptr, count, written) => {
  if (fd !== 1 || count !== 1) throw new Error('unexpected output ABI');
  const memory = instance.exports.memory.buffer, view = new DataView(memory);
  const begin = view.getUint32(ptr, true), size = view.getUint32(ptr + 4, true);
  output.push(Buffer.from(new Uint8Array(memory, begin, size)));
  view.setUint32(written, size, true); return 0;
};
instance = new WebAssembly.Instance(m, {wasi_snapshot_preview1: wasi});
let terminal = 'value';
try { instance.exports._start(); }
catch (e) { if (!(e instanceof WebAssembly.RuntimeError)) throw e; terminal = 'trap'; }
console.log(terminal + ':' + Buffer.concat(output).toString('hex'));
"#;

fn isolated_indirect_case(case: usize) {
    assert!(case < 16);
    let wide = case >= SELECTORS.len();
    let selector = SELECTORS[case % SELECTORS.len()];
    let bytes = module(wide, selector);
    let trap = match selector {
        0 | 1 => None,
        2 => Some("indirect_call_null"),
        3 | 4 => Some("indirect_call_type_mismatch"),
        _ => Some("table_out_of_bounds"),
    };
    let expected = if trap.is_some() {
        vec![]
    } else if wide {
        (if selector == 0 {
            9_007_199_254_741_012i64
        } else {
            9_007_199_254_740_974i64
        })
        .to_le_bytes()
        .to_vec()
    } else {
        (if selector == 0 {
            -2_147_483_630i32
        } else {
            2_147_483_628i32
        })
        .to_le_bytes()
        .to_vec()
    };
    let mut oracle = Command::new(std::env::var_os("MIXER_NODE").unwrap_or_else(|| "node".into()))
        .current_dir(std::env::current_dir().unwrap())
        .args(["-e", ORACLE])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("explicit development oracle requires Node");
    let write = oracle
        .stdin
        .take()
        .unwrap()
        .write_all(hex(&bytes).as_bytes());
    let output = oracle.wait_with_output().unwrap();
    write.unwrap();
    assert!(
        output.status.success(),
        "Node stage failure case={case}: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let expected_oracle = format!(
        "{}:{}",
        if trap.is_some() { "trap" } else { "value" },
        hex(&expected)
    );
    assert_eq!(
        String::from_utf8(output.stdout).unwrap().trim(),
        expected_oracle,
        "Node case={case}"
    );
    assert!(output.stderr.is_empty());

    let proof = validate_swift_command(
        &bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap_or_else(|failure| panic!("REJECTION stage=mixer-validation case={case}: {failure:?}"));
    println!("ADMITTED case={case} stage=mixer-validation");
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
    // One runtime per process: cleanup uncertainty stops the entire parent corpus.
    assert!(
        report.cleanup_completed,
        "UNKNOWN consuming cleanup case={case}: {report:?}"
    );
    let u = report.after_cleanup.expect("terminal consuming usage");
    let r = u.reservations;
    let l = u.live;
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
    assert_eq!(currents, [0; 14], "UNKNOWN reservation cleanup case={case}");
    assert_eq!(r.live_tickets, 0, "UNKNOWN reservation tickets case={case}");
    assert!(
        u.cleanup_invariant.is_none(),
        "UNKNOWN cleanup invariant case={case}"
    );
    println!("CLEANUP case={case} currents=14x0 tickets=0 invariant=none");
    if let Some(code) = trap {
        let failure = report
            .terminal
            .expect("execution trap, not validation rejection");
        assert_eq!(failure.kind, SwiftRunFailureKind::GuestTrap, "{failure:?}");
        assert_eq!(failure.code, code, "case={case}: {failure:?}");
        assert!(!report.succeeded());
    } else {
        assert!(report.succeeded(), "case={case}: {report:?}");
        assert!(report.terminal.is_none());
    }
    assert!(!report.output_error);
    assert_eq!(
        stdout, expected,
        "case={case} selector={selector} wide={wide}"
    );
    assert!(stderr.is_empty());
    assert_eq!(
        report.calls_by_function.iter().sum::<u64>(),
        if trap.is_some() { 0 } else { 1 }
    );
    println!(
        "PARITY case={case} selector={selector} width={} terminal={} bytes={}",
        if wide { 64 } else { 32 },
        trap.unwrap_or("value"),
        hex(&stdout)
    );
}

#[test]
#[ignore = "development Node oracle; run explicitly with experimental-swift-reactor"]
fn indirect_calls_match_node() {
    match std::env::var(CASE_ENV) {
        Ok(case) => {
            isolated_indirect_case(case.parse().expect("indirect case must be an integer"));
            return;
        }
        Err(std::env::VarError::NotPresent) => {}
        Err(error) => panic!("invalid indirect case: {error}"),
    }
    for case in 0..16 {
        let output = Command::new(std::env::current_exe().unwrap())
            .current_dir(std::env::current_dir().unwrap())
            .args([
                "--ignored",
                "--exact",
                TEST,
                "--nocapture",
                "--test-threads=1",
            ])
            .env(CASE_ENV, case.to_string())
            .output()
            .unwrap();
        print!("{}", String::from_utf8_lossy(&output.stdout));
        assert!(
            output.status.success(),
            "case={case}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
        let stdout = String::from_utf8_lossy(&output.stdout);
        assert!(stdout.contains(&format!("CLEANUP case={case} ")));
        assert!(stdout.contains(&format!("PARITY case={case} ")));
    }
    println!("16 original indirect-call cases matched Node; each consumed fourteen zero currents and zero tickets");
}
