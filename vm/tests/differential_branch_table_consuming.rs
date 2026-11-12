#![cfg(feature = "experimental-swift-reactor")]

#[path = "common/mod.rs"]
mod common;
#[path = "swift_reactor_validation_fixture.rs"]
mod fixture;

use mixer_vm::experimental_swift_reactor::{
    execute_swift_command, validate_swift_command, SwiftRunBudget, SwiftValidationBudget,
};
use mixer_vm::experimental_wasi::{WasiBudget, WasiGrants};
use mixer_vm::{Cancellation, Type, Value};
use std::io::Write;
use std::process::{Command, Stdio};

const SELECTORS: [i32; 8] = [0, 1, 2, 3, 4, i32::MAX, i32::MIN, -1];

fn module(wide: bool, selector: i32) -> Vec<u8> {
    let ty = if wide { Type::I64 } else { Type::I32 };
    let mut f = fixture::Fixture::default();
    let helper_type = if wide {
        f.types.push(fixture::signature(&[], &[ty]));
        36
    } else {
        35
    };
    f.function_types = vec![34, helper_type];
    f.memory = vec![1, 1, 1, 1]; // one page, fixed maximum
    f.table = vec![1, 0x70, 1, 0, 0];
    f.exports = vec![(b"memory".to_vec(), 2, 0), (b"_start".to_vec(), 0, 34)];

    let value = |n: i64| {
        common::constant(if wide {
            Value::I64(n)
        } else {
            Value::I32(n as i32)
        })
    };
    let add = if wide { 0x7c } else { 0x6a };
    let mut helper = vec![0]; // no locals
    for discarded in [11, 22, 33] {
        helper.extend([0x02, fixture::type_byte(ty)]);
        helper.extend(value(discarded));
    }
    helper.extend(value(-7));
    helper.extend(common::constant(Value::I32(selector)));
    // Targets: inner block, middle block, outer block, function; default: middle.
    // Each branch must retain -7 and discard the correct intermediate values.
    helper.extend([0x0e, 4, 0, 1, 2, 3, 1, 0x00, 0x0b, add]);
    helper.extend(value(100));
    helper.extend([add, 0x0b, add]);
    helper.extend(value(1000));
    helper.extend([add, 0x0b]);
    helper.extend(value(10000));
    helper.extend([add, 0x0b]);

    let fd_write = f
        .imports
        .iter()
        .position(|(_, field, _, _)| field == b"fd_write")
        .unwrap();
    let mut start = vec![0, 0x41, 32, 0x10, 35, if wide { 0x37 } else { 0x36 }, 0, 0];
    for n in [1, 0, 1, 16] {
        start.extend(common::constant(Value::I32(n)));
    }
    start.push(0x10);
    start.extend(fixture::uint(fd_write as u32));
    start.extend([0x1a, 0x0b]);
    f.bodies = vec![start, helper];
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

// Only fd_write bridges guest bytes to the oracle observer. No interpreter is
// implemented here; every instruction runs in Node's built-in WebAssembly engine.
const ORACLE: &str = r#"
const fs = require('node:fs');
const bytes = Buffer.from(fs.readFileSync(0, 'utf8'), 'hex');
if (!WebAssembly.validate(bytes)) throw new Error('invalid original module');
const m = new WebAssembly.Module(bytes);
const wasi = Object.fromEntries(WebAssembly.Module.imports(m).map(x =>
  [x.name, () => { throw new Error('unexpected import ' + x.name); }]));
let instance; const output = [];
wasi.fd_write = (fd, ptr, count, written) => {
  if (fd !== 1 || count !== 1) throw new Error('unexpected output ABI');
  const memory = instance.exports.memory.buffer;
  const view = new DataView(memory);
  const begin = view.getUint32(ptr, true), size = view.getUint32(ptr + 4, true);
  output.push(Buffer.from(new Uint8Array(memory, begin, size)));
  view.setUint32(written, size, true); return 0;
};
instance = new WebAssembly.Instance(m, {wasi_snapshot_preview1: wasi});
instance.exports._start();
console.log(Buffer.concat(output).toString('hex'));
"#;

fn isolated_branch_table_case(case: usize) {
    assert!(case < 16);
    let wide = case >= SELECTORS.len();
    let selector = SELECTORS[case % SELECTORS.len()];
    let bytes = module(wide, selector);
    let expected: i64 = match selector {
        0 => 11126, // -7 + 22 + 100 + 11 + 1000 + 10000
        2 => 9993,  // -7 + 10000
        3 => -7,    // branch directly out of the function
        _ => 11004, // -7 + 11 + 1000 + 10000
    };
    let expected = if wide {
        expected.to_le_bytes().to_vec()
    } else {
        (expected as i32).to_le_bytes().to_vec()
    };
    let mut oracle = Command::new(std::env::var_os("MIXER_NODE").unwrap_or_else(|| "node".into()))
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
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert_eq!(
        String::from_utf8(output.stdout).unwrap().trim(),
        hex(&expected),
        "Node case {case}"
    );

    let proof = validate_swift_command(
        &bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
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
    // Assert the consuming receipt before checking semantics. An absent/incomplete
    // receipt stops this process; the corpus never constructs a second runtime.
    assert!(
        report.cleanup_completed,
        "UNKNOWN consuming cleanup: {report:?}"
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
    assert_eq!(currents, [0; 14], "UNKNOWN reservation cleanup");
    assert_eq!(r.live_tickets, 0, "UNKNOWN reservation tickets");
    assert!(u.cleanup_invariant.is_none());
    println!("CLEANUP case={case} currents=14x0 tickets=0 invariant=none");
    assert!(report.succeeded(), "{report:?}");
    assert_eq!(
        stdout, expected,
        "owned case={case} selector={selector} wide={wide}"
    );
    assert!(stderr.is_empty());
    assert_eq!(report.calls_by_function.iter().sum::<u64>(), 1);
    println!(
        "PARITY case={case} selector={selector} width={} bytes={}",
        if wide { 64 } else { 32 },
        hex(&stdout)
    );
}

#[test]
#[ignore = "development Node oracle; run explicitly with experimental-swift-reactor"]
fn nested_branch_table_matches_node() {
    match std::env::var("MIXER_DIFFERENTIAL_BRANCH_CASE") {
        Ok(case) => {
            let case = case.parse().expect("branch-table case must be an integer");
            isolated_branch_table_case(case);
            return;
        }
        Err(std::env::VarError::NotPresent) => {}
        Err(error) => panic!("invalid branch-table case: {error}"),
    }
    for case in 0..16 {
        let output = Command::new(std::env::current_exe().unwrap())
            .args([
                "--ignored",
                "--exact",
                "nested_branch_table_matches_node",
                "--nocapture",
                "--test-threads=1",
            ])
            .env("MIXER_DIFFERENTIAL_BRANCH_CASE", case.to_string())
            .output()
            .unwrap();
        print!("{}", String::from_utf8_lossy(&output.stdout));
        assert!(
            output.status.success(),
            "case {case}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(String::from_utf8_lossy(&output.stdout).contains(&format!("CLEANUP case={case} ")));
    }
    println!("16 original branch-table cases matched Node and consumed fourteen zero currents / zero tickets each");
}
