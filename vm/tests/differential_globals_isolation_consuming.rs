#![cfg(feature = "experimental-swift-reactor")]

#[path = "swift_reactor_validation_fixture.rs"]
mod fixture;

use mixer_vm::experimental_swift_reactor::{
    execute_swift_command, validate_swift_command, SwiftCommandReport, SwiftRunBudget,
    SwiftRunFailureKind, SwiftValidationBudget, ValidatedSwiftCommand,
};
use mixer_vm::experimental_wasi::{WasiBudget, WasiGrants};
use mixer_vm::{Cancellation, Type};
use std::io::{self, Write};
use std::path::PathBuf;
use std::process::{Command, Stdio};

// Original byte construction. Only memory and _start are exported; all typed
// getters, setters, snapshots and mutation chains are internal functions.
const TYPES: [Type; 4] = [Type::I32, Type::I64, Type::F32, Type::F64];
const WIDTHS: [usize; 4] = [4, 8, 4, 8];
const A: [[u64; 4]; 3] = [
    [
        0x1357_9bdf,
        0x0123_4567_89ab_cdef,
        0x8000_0000,
        0x7ff0_1234_5678_9abc,
    ],
    [
        0x8000_0000,
        0xfedc_ba98_7654_3210,
        0x7f81_2345,
        0x8000_0000_0000_0000,
    ],
    [
        0xffff_ffff,
        0x8000_0000_0000_0000,
        0xffc2_3456,
        0xfff9_8765_4321_abcd,
    ],
];
const B: [[u64; 4]; 3] = [
    [
        0x2468_ace0,
        0x7654_3210_fedc_ba98,
        0x7f80_0001,
        0xfff0_2468_1357_9bdf,
    ],
    [
        0x7fff_ffff,
        0x1357_9bdf_2468_ace0,
        0x0000_0001,
        0x0000_0000_0000_0001,
    ],
    [0, u64::MAX, 0xff80_0000, 0x3ff0_0000_0000_0000],
];

fn signed(mut n: i64, out: &mut Vec<u8>) {
    loop {
        let b = (n & 127) as u8;
        n >>= 7;
        let done = (n == 0 && b & 64 == 0) || (n == -1 && b & 64 != 0);
        out.push(b | if done { 0 } else { 128 });
        if done {
            break;
        }
    }
}
fn constant(ty: Type, bits: u64, out: &mut Vec<u8>) {
    match ty {
        Type::I32 => {
            out.push(0x41);
            signed(bits as u32 as i32 as i64, out);
        }
        Type::I64 => {
            out.push(0x42);
            signed(bits as i64, out);
        }
        Type::F32 => {
            out.push(0x43);
            out.extend((bits as u32).to_le_bytes());
        }
        Type::F64 => {
            out.push(0x44);
            out.extend(bits.to_le_bytes());
        }
    }
}
fn call(n: u32, out: &mut Vec<u8>) {
    out.push(0x10);
    out.extend(fixture::uint(n));
}
fn expected(values: &[[u64; 4]; 3]) -> Vec<u8> {
    let mut bytes = Vec::new();
    for stage in values {
        for (bits, width) in stage.iter().zip(WIDTHS) {
            bytes.extend(&bits.to_le_bytes()[..width]);
        }
    }
    bytes
}
fn module(values: &[[u64; 4]; 3], trap: bool) -> Vec<u8> {
    let mut f = fixture::Fixture::default();
    f.types.extend([
        fixture::signature(&[], &[Type::I64]),
        fixture::signature(&[Type::I32], &[]),
        fixture::signature(&[Type::I64], &[]),
    ]);
    f.function_types = vec![34];
    f.bodies = vec![Vec::new()];
    f.memory = vec![1, 1, 1, 1];
    f.table = vec![1, 0x70, 1, 1, 1];
    f.exports = vec![(b"memory".to_vec(), 2, 0), (b"_start".to_vec(), 0, 34)];
    let mut getters = Vec::new();
    let mut setters = Vec::new();
    for (i, ty) in TYPES.into_iter().enumerate() {
        let wide = WIDTHS[i] == 8;
        let mut global = vec![fixture::type_byte(ty), 1];
        constant(ty, values[0][i], &mut global);
        global.push(0x0b);
        f.globals.push(global);
        getters.push(34 + f.bodies.len() as u32);
        let mut get = vec![0, 0x23, i as u8];
        if ty == Type::F32 {
            get.push(0xbc);
        }
        if ty == Type::F64 {
            get.push(0xbd);
        }
        get.push(0x0b);
        f.bodies.push(get);
        f.function_types.push(if wide { 36 } else { 35 });
        setters.push(34 + f.bodies.len() as u32);
        let mut set = vec![0, 0x20, 0];
        if ty == Type::F32 {
            set.push(0xbe);
        }
        if ty == Type::F64 {
            set.push(0xbf);
        }
        set.extend([0x24, i as u8, 0x0b]);
        f.bodies.push(set);
        f.function_types.push(if wide { 38 } else { 37 });
    }
    let snapshot = 34 + f.bodies.len() as u32;
    let mut body = vec![0];
    let mut offset = 0;
    for (i, width) in WIDTHS.into_iter().enumerate() {
        body.extend([0x20, 0]);
        constant(Type::I32, offset, &mut body);
        body.push(0x6a);
        call(getters[i], &mut body);
        body.extend([if width == 8 { 0x37 } else { 0x36 }, 0, 0]);
        offset += width as u64;
    }
    body.push(0x0b);
    f.bodies.push(body);
    f.function_types.push(37);
    let mut mutations = Vec::new();
    for stage in &values[1..] {
        mutations.push(34 + f.bodies.len() as u32);
        let mut body = vec![0];
        for i in 0..4 {
            constant(
                if WIDTHS[i] == 8 { Type::I64 } else { Type::I32 },
                stage[i],
                &mut body,
            );
            call(setters[i], &mut body);
        }
        body.push(0x0b);
        f.bodies.push(body);
        f.function_types.push(34);
    }
    let mut start = vec![0];
    for stage in 0..3 {
        if stage > 0 {
            call(mutations[stage - 1], &mut start);
        }
        constant(Type::I32, 128 + stage as u64 * 24, &mut start);
        call(snapshot, &mut start);
    }
    for n in [1, 0, 1, 16] {
        constant(Type::I32, n, &mut start);
    }
    let fd_write = f
        .imports
        .iter()
        .position(|(_, name, _, _)| name == b"fd_write")
        .unwrap();
    call(fd_write as u32, &mut start);
    start.push(0x1a);
    if trap {
        start.push(0x00);
    }
    start.push(0x0b);
    f.bodies[0] = start;
    let mut iovec = 128u32.to_le_bytes().to_vec();
    iovec.extend(72u32.to_le_bytes());
    f.data = vec![fixture::data_segment(0, &iovec)];
    f.bytes()
}
fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

// The oracle allocates two independent instances and uses the same nesting
// schedule, including a fresh instantiation of exactly the same module bytes.
// https://webassembly.github.io/spec/core/exec/modules.html#alloc-global
const ORACLE: &str = r#"
const fs = require('node:fs');
const lines = fs.readFileSync(0, 'utf8').trim().split('\n');
if (process.versions.node.split('.')[0] !== '22') throw Error('Node22 required');
const modules = lines.map(line => {
  const bytes = Buffer.from(line, 'hex');
  if (!WebAssembly.validate(bytes)) throw Error('invalid Wasm');
  const m = new WebAssembly.Module(bytes);
  const e = WebAssembly.Module.exports(m);
  if (JSON.stringify(e) !== JSON.stringify([{name:'memory',kind:'memory'},{name:'_start',kind:'function'}])) throw Error('exports');
  return m;
});
function make(index, label, nested) {
  const imports = Object.fromEntries(WebAssembly.Module.imports(modules[index]).map(i => [i.name, () => {throw Error('unexpected capability');}]));
  let instance, output = null, called = false;
  imports.fd_write = (fd, ptr, count, written) => {
    if (fd !== 1 || ptr !== 0 || count !== 1 || written !== 16 || output !== null) throw Error('ABI');
    const v = new DataView(instance.exports.memory.buffer);
    if (v.getUint32(0,true) !== 128 || v.getUint32(4,true) !== 72) throw Error('iovec');
    output = Buffer.from(instance.exports.memory.buffer,128,72).toString('hex');
    if (nested) { nested(); called = true; }
    v.setUint32(16,72,true); return 0;
  };
  instance = new WebAssembly.Instance(modules[index],{wasi_snapshot_preview1:imports});
  return () => {
    let trapped = false;
    try { instance.exports._start(); }
    catch(e) { if (!(e instanceof WebAssembly.RuntimeError) || index !== 2) throw e; trapped = true; }
    if (trapped !== (index === 2) || output === null || Boolean(nested) !== called) throw Error('terminal');
    console.log(label + ' ' + (trapped ? 'trap' : 'ok') + ' ' + output);
  };
}
for (const [outer,inner] of [[0,1],[1,0],[0,2]]) {
  const b = make(inner, 'inner-'+inner, null);
  make(outer, 'outer-'+outer, b)();
}
"#;

struct Outcome {
    label: String,
    report: SwiftCommandReport,
    stdout: Vec<u8>,
    stderr: Vec<u8>,
}
struct InnerSink {
    bytes: Vec<u8>,
    writes: usize,
    outer: String,
    inner: String,
}
impl Write for InnerSink {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        self.bytes.extend_from_slice(bytes);
        self.writes += 1;
        println!(
            "OVERLAP outer={} inner={} pid={} outer_sink_active=true inner_sink_active=true",
            self.outer,
            self.inner,
            std::process::id()
        );
        Ok(bytes.len())
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
struct NestedSink {
    outer: String,
    inner_label: String,
    proof: Option<ValidatedSwiftCommand>,
    bytes: Vec<u8>,
    inner: Option<Outcome>,
    overlap_writes: usize,
}
fn run(
    proof: ValidatedSwiftCommand,
    stdout: &mut impl Write,
    stderr: &mut Vec<u8>,
) -> SwiftCommandReport {
    execute_swift_command(
        proof,
        SwiftRunBudget::default(),
        WasiGrants {
            stdout: true,
            ..Default::default()
        },
        WasiBudget::default(),
        Cancellation::default(),
        stdout,
        stderr,
    )
}
impl Write for NestedSink {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        self.bytes.extend_from_slice(bytes);
        if let Some(proof) = self.proof.take() {
            // command.rs writes output before cleanup_owned. The outer owner
            // stays alive on this stack while the inner command is constructed,
            // executed and consumed. No guest instruction can be resumed here.
            println!(
                "NEST_BEGIN outer={} inner={} pid={}",
                self.outer,
                self.inner_label,
                std::process::id()
            );
            let mut sink = InnerSink {
                bytes: Vec::new(),
                writes: 0,
                outer: self.outer.clone(),
                inner: self.inner_label.clone(),
            };
            let mut stderr = Vec::new();
            let report = run(proof, &mut sink, &mut stderr);
            self.overlap_writes = sink.writes;
            self.inner = Some(Outcome {
                label: self.inner_label.clone(),
                report,
                stdout: sink.bytes,
                stderr,
            });
            println!(
                "NEST_END outer={} inner={} pid={}",
                self.outer,
                self.inner_label,
                std::process::id()
            );
        }
        Ok(bytes.len())
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
fn ledger(outcome: &Outcome) -> bool {
    let Some(u) = outcome.report.after_cleanup else {
        println!(
            "UNKNOWN ledger label={} report={:?}",
            outcome.label, outcome.report
        );
        return false;
    };
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
    println!(
        "CLEANUP label={} pid={} completed={} currents={currents:?} tickets={} invariant={:?}",
        outcome.label,
        std::process::id(),
        outcome.report.cleanup_completed,
        r.live_tickets,
        u.cleanup_invariant
    );
    outcome.report.cleanup_completed
        && currents == [0; 14]
        && r.live_tickets == 0
        && u.cleanup_invariant.is_none()
}
fn verify(outcome: &Outcome, bytes: &[u8], trap: bool) {
    assert!(!outcome.report.output_error, "output: {:?}", outcome.report);
    assert!(outcome.stderr.is_empty());
    assert_eq!(
        outcome.stdout, bytes,
        "instance isolation {}",
        outcome.label
    );
    assert_eq!(outcome.report.calls_by_function.iter().sum::<u64>(), 1);
    if trap {
        assert!(!outcome.report.succeeded());
        assert_eq!(
            outcome.report.terminal.map(|f| f.kind),
            Some(SwiftRunFailureKind::GuestTrap)
        );
    } else {
        assert!(
            outcome.report.succeeded() && outcome.report.terminal.is_none(),
            "{:?}",
            outcome.report
        );
    }
    println!(
        "PARITY label={} pid={} terminal={} bytes={}",
        outcome.label,
        std::process::id(),
        if trap { "trap" } else { "ok" },
        hex(&outcome.stdout)
    );
}
fn admit(bytes: &[u8]) -> ValidatedSwiftCommand {
    match validate_swift_command(
        bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    ) {
        Ok(proof) => proof,
        Err(failure) => panic!("command admission: {failure:?}"),
    }
}

#[test]
#[ignore = "bounded Node22 oracle and same-process overlapping consuming runtimes"]
fn globals_instances_isolate_and_consume() {
    let modules = [module(&A, false), module(&B, false), module(&B, true)];
    let expectations = [expected(&A), expected(&B), expected(&B)];
    for (i, bytes) in modules.iter().enumerate() {
        println!("MODULE index={i} hex={}", hex(bytes));
    }
    let node = PathBuf::from(
        std::env::var_os("MIXER_NODE").expect("ENVIRONMENT_REJECTED: explicit Node22 required"),
    );
    assert!(
        node.is_absolute() && node.is_file(),
        "ENVIRONMENT_REJECTED: Node executable"
    );
    let mut child = Command::new(node)
        .args(["-e", ORACLE])
        .env_remove("NODE_OPTIONS")
        .env_remove("NODE_PATH")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("UNKNOWN oracle spawn");
    let input = modules
        .iter()
        .map(|m| hex(m))
        .collect::<Vec<_>>()
        .join("\n")
        + "\n";
    let node_pid = child.id();
    let sent = child.stdin.take().unwrap().write_all(input.as_bytes());
    let oracle = child.wait_with_output().expect("UNKNOWN oracle reap");
    sent.expect("oracle input");
    assert!(
        oracle.status.success(),
        "oracle: {}",
        String::from_utf8_lossy(&oracle.stderr)
    );
    assert!(oracle.stderr.is_empty());
    let schedules = [(0, 1), (1, 0), (0, 2)];
    let mut oracle_expected = String::new();
    for (outer, inner) in schedules {
        for (role, index) in [("inner", inner), ("outer", outer)] {
            oracle_expected.push_str(&format!(
                "{role}-{index} {} {}\n",
                if index == 2 { "trap" } else { "ok" },
                hex(&expectations[index])
            ));
        }
    }
    assert_eq!(String::from_utf8(oracle.stdout).unwrap(), oracle_expected);
    println!(
        "ORACLE_NODE22 node_pid={node_pid} reaped=true parent_pid={} results={} bytes={}",
        std::process::id(),
        6,
        hex(oracle_expected.as_bytes())
    );
    println!("BOUNDARY same_process=true max_live=2 nesting=output-before-cleanup guest_instruction_interleaving=false exports=memory,_start budgets=default grants=stdout-only");
    for (pair, (outer, inner)) in schedules.into_iter().enumerate() {
        let outer_proof = admit(&modules[outer]);
        let inner_proof = admit(&modules[inner]);
        println!(
            "ADMITTED pair={pair} outer={outer} inner={inner} pid={}",
            std::process::id()
        );
        let outer_label = format!("pair{pair}-module{outer}");
        let inner_label = format!("pair{pair}-module{inner}");
        let mut sink = NestedSink {
            outer: outer_label.clone(),
            inner_label,
            proof: Some(inner_proof),
            bytes: Vec::new(),
            inner: None,
            overlap_writes: 0,
        };
        let mut stderr = Vec::new();
        let report = run(outer_proof, &mut sink, &mut stderr);
        // If outer execution fails before producing output, still consume the
        // already admitted inner command; record lack of overlap and fail below.
        if let Some(proof) = sink.proof.take() {
            let mut stdout = Vec::new();
            let mut stderr = Vec::new();
            let report = run(proof, &mut stdout, &mut stderr);
            sink.inner = Some(Outcome {
                label: sink.inner_label.clone(),
                report,
                stdout,
                stderr,
            });
        }
        let inner_outcome = sink.inner.take().expect("inner consumed");
        let outer_outcome = Outcome {
            label: outer_label,
            report,
            stdout: sink.bytes,
            stderr,
        };
        // Both consuming reports are inspected before any parity assertion.
        let inner_clean = ledger(&inner_outcome);
        let outer_clean = ledger(&outer_outcome);
        assert!(
            inner_clean && outer_clean,
            "UNKNOWN consuming ledger; preserve campaign"
        );
        assert_eq!(sink.overlap_writes, 1, "both live runtime sinks required");
        verify(&inner_outcome, &expectations[inner], inner == 2);
        verify(&outer_outcome, &expectations[outer], false);
        println!(
            "PAIR_COMPLETE pair={pair} pid={} fresh_initials=true consumed=2",
            std::process::id()
        );
    }
    println!("ISOLATION_COMPLETE pid={} pairs=3 runtimes=6 cleanups=6 trap_cleanups=1 fresh_reinstantiation=true max_live=2 guest_instruction_interleaving=false", std::process::id());
}
