//! Independently authored fixed-ABI validation probes. No Wasm execution.
#![allow(dead_code)]
#[path = "allocation_observer.rs"]
mod observer;
use mixer_vm::experimental_swift_reactor::*;
use mixer_vm::Cancellation;
use observer::{begin, Ownership, CALLS, LIVE, REALLOCATIONS};
use std::sync::atomic::Ordering::SeqCst;
#[global_allocator]
static ALLOCATOR: observer::Observed = observer::Observed;
const I: u8 = 0x7f;
const L: u8 = 0x7e;
// Retained descriptors.json ABI, transcribed independently of WasiFunction::ALL
// and of the implementation lane's fixture builder.
const ABI: [(&str, &[u8]); 34] = [
    ("args_get", &[I, I]),
    ("args_sizes_get", &[I, I]),
    ("environ_get", &[I, I]),
    ("environ_sizes_get", &[I, I]),
    ("clock_res_get", &[I, I]),
    ("clock_time_get", &[I, L, I]),
    ("fd_close", &[I]),
    ("fd_fdstat_get", &[I, I]),
    ("fd_fdstat_set_flags", &[I, I]),
    ("fd_filestat_get", &[I, I]),
    ("fd_filestat_set_size", &[I, L]),
    ("fd_filestat_set_times", &[I, L, L, I]),
    ("fd_pread", &[I, I, I, L, I]),
    ("fd_prestat_get", &[I, I]),
    ("fd_prestat_dir_name", &[I, I, I]),
    ("fd_read", &[I, I, I, I]),
    ("fd_readdir", &[I, I, I, L, I]),
    ("fd_seek", &[I, L, I, I]),
    ("fd_sync", &[I]),
    ("fd_tell", &[I, I]),
    ("fd_write", &[I, I, I, I]),
    ("path_create_directory", &[I, I, I]),
    ("path_filestat_get", &[I, I, I, I, I]),
    ("path_filestat_set_times", &[I, I, I, I, L, L, I]),
    ("path_link", &[I, I, I, I, I, I, I]),
    ("path_open", &[I, I, I, I, I, L, L, I, I]),
    ("path_readlink", &[I, I, I, I, I, I]),
    ("path_remove_directory", &[I, I, I]),
    ("path_rename", &[I, I, I, I, I, I]),
    ("path_symlink", &[I, I, I, I, I]),
    ("path_unlink_file", &[I, I, I]),
    ("poll_oneoff", &[I, I, I, I]),
    ("proc_exit", &[I]),
    ("random_get", &[I, I]),
];
fn u(mut n: u32) -> Vec<u8> {
    let mut v = Vec::new();
    loop {
        let b = (n & 127) as u8;
        n >>= 7;
        v.push(b | if n != 0 { 128 } else { 0 });
        if n == 0 {
            return v;
        }
    }
}
fn s(mut n: i32) -> Vec<u8> {
    let mut v = Vec::new();
    loop {
        let b = (n & 127) as u8;
        n >>= 7;
        let end = (n == 0 && b & 64 == 0) || (n == -1 && b & 64 != 0);
        v.push(b | if end { 0 } else { 128 });
        if end {
            return v;
        }
    }
}
fn text(b: &[u8]) -> Vec<u8> {
    let mut v = u(b.len() as u32);
    v.extend(b);
    v
}
fn sec(out: &mut Vec<u8>, id: u8, p: Vec<u8>) {
    out.push(id);
    out.extend(u(p.len() as u32));
    out.extend(p)
}
fn sig(p: &[u8], r: Option<u8>) -> Vec<u8> {
    let mut v = vec![0x60];
    v.extend(u(p.len() as u32));
    v.extend(p);
    v.push(u8::from(r.is_some()));
    v.extend(r);
    v
}
fn segment(offset: i32, payload: &[u8], elements: bool) -> Vec<u8> {
    let mut v = vec![0, 0x41];
    v.extend(s(offset));
    v.push(0x0b);
    v.extend(u(payload.len() as u32));
    if elements {
        for p in payload {
            v.extend(u(u32::from(*p)))
        }
    } else {
        v.extend(payload)
    }
    v
}
#[derive(Clone)]
struct Wire {
    types: Vec<Vec<u8>>,
    imports: Vec<(Vec<u8>, Vec<u8>, u32)>,
    function_types: Vec<u32>,
    bodies: Vec<Vec<u8>>,
    memory: Vec<u8>,
    table: Vec<u8>,
    exports: Vec<(Vec<u8>, u8, u32)>,
    data: Vec<Vec<u8>>,
    elements: Vec<Vec<u8>>,
    start: bool,
    custom: Option<Vec<u8>>,
}
impl Wire {
    fn new() -> Self {
        let mut types: Vec<_> = ABI
            .iter()
            .map(|(n, p)| sig(p, if *n == "proc_exit" { None } else { Some(I) }))
            .collect();
        types.push(sig(&[], None));
        types.push(sig(&[], Some(I)));
        let imports = ABI
            .iter()
            .enumerate()
            .map(|(i, (n, _))| {
                (
                    b"wasi_snapshot_preview1".to_vec(),
                    n.as_bytes().to_vec(),
                    i as u32,
                )
            })
            .collect();
        let mut bodies = vec![vec![0, 0x0b]; 29];
        bodies[28] = vec![0, 0x41, 0, 0x0b];
        let mut function_types = vec![34; 29];
        function_types[28] = 35;
        let mut memory = vec![1, 0];
        memory.extend(u(584));
        let mut table = vec![1, 0x70, 1];
        table.extend(u(46_713));
        table.extend(u(46_713));
        Self {
            types,
            imports,
            function_types,
            bodies,
            memory,
            table,
            exports: vec![
                (b"memory".to_vec(), 2, 0),
                (b"_initialize".to_vec(), 0, 35),
                (b"mixer_fieldlog_corpus_v1".to_vec(), 0, 62),
            ],
            data: vec![],
            elements: vec![],
            start: false,
            custom: None,
        }
    }
    fn bytes(&self) -> Vec<u8> {
        let mut out = b"\0asm\x01\0\0\0".to_vec();
        if let Some(name) = &self.custom {
            sec(&mut out, 0, text(name))
        }
        let mut t = u(self.types.len() as u32);
        for x in &self.types {
            t.extend(x)
        }
        sec(&mut out, 1, t);
        let mut i = u(self.imports.len() as u32);
        for (ns, n, ty) in &self.imports {
            i.extend(text(ns));
            i.extend(text(n));
            i.push(0);
            i.extend(u(*ty))
        }
        sec(&mut out, 2, i);
        let mut f = u(self.function_types.len() as u32);
        for ty in &self.function_types {
            f.extend(u(*ty))
        }
        sec(&mut out, 3, f);
        sec(&mut out, 4, self.table.clone());
        sec(&mut out, 5, self.memory.clone());
        let mut e = u(self.exports.len() as u32);
        for (n, k, index) in &self.exports {
            e.extend(text(n));
            e.push(*k);
            e.extend(u(*index))
        }
        sec(&mut out, 7, e);
        if self.start {
            sec(&mut out, 8, u(35))
        }
        if !self.elements.is_empty() {
            let mut e = u(self.elements.len() as u32);
            for x in &self.elements {
                e.extend(x)
            }
            sec(&mut out, 9, e)
        }
        let mut c = u(self.bodies.len() as u32);
        for b in &self.bodies {
            c.extend(u(b.len() as u32));
            c.extend(b)
        }
        sec(&mut out, 10, c);
        if !self.data.is_empty() {
            let mut d = u(self.data.len() as u32);
            for x in &self.data {
                d.extend(x)
            }
            sec(&mut out, 11, d)
        }
        out
    }
}
fn validate(w: &Wire) -> Result<ValidatedSwiftReactor, SwiftValidationFailure> {
    validate_swift_reactor(
        &w.bytes(),
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
}
fn accepted(w: &Wire) {
    let p = validate(w).unwrap();
    assert_eq!(p.policy_identity(), "swift-reactor-experiment-v1");
    assert_eq!(p.observations().validated_bodies, w.bodies.len());
}
fn rejected(w: &Wire, kind: SwiftValidationFailureKind) {
    let e = validate(w).err().expect("must reject");
    assert_eq!(
        e.kind, kind,
        "code={} function={:?} offset={}",
        e.code, e.function, e.offset
    );
}
fn main() {
    if std::env::args().nth(1).as_deref() == Some("--abi") {
        for (name, params) in ABI {
            println!(
                "{{\"name\":\"{}\",\"parameters\":{:?},\"results\":{:?}}}",
                name,
                params,
                if name == "proc_exit" {
                    &[][..]
                } else {
                    &[I][..]
                }
            );
        }
        return;
    }
    let _ownership = Ownership::new();
    let w = Wire::new();
    accepted(&w);
    let mut input = w.bytes();
    let p = validate_swift_reactor(
        &input,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
    assert_ne!(input.as_ptr(), p.source().as_ptr());
    input[0] = 99;
    drop(input);
    assert_eq!(&p.source()[..8], b"\0asm\x01\0\0\0");
    drop(p);
    let mut cases = 2;
    for index in 0..34 {
        let mut x = w.clone();
        x.types[index] = sig(&[], None);
        rejected(&x, SwiftValidationFailureKind::AbiShape);
        cases += 1;
        let mut x = w.clone();
        x.imports[index].1 = b"unexpected".to_vec();
        rejected(&x, SwiftValidationFailureKind::AbiShape);
        cases += 1;
    }
    let mut x = w.clone();
    x.imports.swap(0, 1);
    rejected(&x, SwiftValidationFailureKind::AbiShape);
    cases += 1;
    let mut x = w.clone();
    x.imports[1] = x.imports[0].clone();
    rejected(&x, SwiftValidationFailureKind::AbiShape);
    cases += 1;
    let mut x = w.clone();
    x.imports[0].0 = b"mixer".to_vec();
    rejected(&x, SwiftValidationFailureKind::AbiShape);
    cases += 1;
    let mut x = w.clone();
    x.imports.push(x.imports[0].clone());
    rejected(&x, SwiftValidationFailureKind::AbiShape);
    cases += 1;
    for declaration in [vec![1, 1, 0xc8, 4, 0x80, 6], vec![1, 0, 0xc7, 4]] {
        let mut x = w.clone();
        x.memory = declaration;
        rejected(&x, SwiftValidationFailureKind::AbiShape);
        cases += 1;
    }
    let mut x = w.clone();
    x.table = vec![1, 0x70, 0];
    x.table.extend(u(46_713));
    rejected(&x, SwiftValidationFailureKind::AbiShape);
    cases += 1;
    for export in 0..3 {
        let mut x = w.clone();
        x.exports[export].0.push(b'x');
        rejected(&x, SwiftValidationFailureKind::AbiShape);
        cases += 1;
    }
    let mut x = w.clone();
    x.function_types[1] = 35;
    x.bodies[1] = vec![0, 0x41, 0, 0x0b];
    rejected(&x, SwiftValidationFailureKind::AbiShape);
    cases += 1;
    let mut x = w.clone();
    x.start = true;
    rejected(&x, SwiftValidationFailureKind::Unsupported);
    cases += 1;
    let mut x = w.clone();
    x.custom = Some(vec![0xc0, 0xaf]);
    rejected(&x, SwiftValidationFailureKind::Malformed);
    cases += 1;
    for index in 0..29 {
        let mut x = w.clone();
        x.bodies[index] = vec![0, 0, 0x41, 0, 0x42, 0, 0x6a, 0x1a, 0x0b];
        let e = validate(&x).err().unwrap();
        assert_eq!(e.kind, SwiftValidationFailureKind::Validation);
        assert_eq!(e.function, Some(34 + index as u32));
        cases += 1;
    }
    for body in [
        vec![0, 0, 0x20, 127, 0x1a, 0x0b],
        vec![0, 0, 0x0c, 1, 0x0b],
        vec![0, 0, 0x10, 127, 0x0b],
        vec![0, 0, 0x41, 0, 0x28, 3, 0, 0x1a, 0x0b],
    ] {
        let mut x = w.clone();
        x.bodies[0] = body;
        rejected(&x, SwiftValidationFailureKind::Validation);
        cases += 1;
    }
    let mut x = w.clone();
    x.bodies[0] = vec![0, 0, 0xfd, 0, 0x0b];
    rejected(&x, SwiftValidationFailureKind::Unsupported);
    cases += 1;
    let mut x = w.clone();
    x.bodies[0] = vec![0, 0, 0x0b];
    accepted(&x);
    cases += 1;
    let mem = 584 * 65_536;
    for (offset, payload, ok) in [
        (mem - 1, vec![1], true),
        (mem, vec![], true),
        (mem, vec![1], false),
        (mem + 1, vec![], false),
        (-1, vec![], false),
        (-1, vec![1, 2], false),
    ] {
        let mut x = w.clone();
        x.data = vec![segment(offset, &payload, false)];
        if ok {
            accepted(&x)
        } else {
            rejected(&x, SwiftValidationFailureKind::Validation)
        }
        cases += 1;
    }
    for (offset, payload, ok) in [
        (46_712, vec![34], true),
        (46_713, vec![], true),
        (46_713, vec![34], false),
        (46_714, vec![], false),
        (-1, vec![], false),
        (-1, vec![34, 35], false),
    ] {
        let mut x = w.clone();
        x.elements = vec![segment(offset, &payload, true)];
        if ok {
            accepted(&x)
        } else {
            rejected(&x, SwiftValidationFailureKind::Validation)
        }
        cases += 1;
    }
    let mut x = w.clone();
    x.data = vec![segment(0, &[1, 2], false), segment(1, &[3], false)];
    let p = validate(&x).unwrap();
    assert_eq!(p.data_segment(0).unwrap().encoded_payload, [1, 2]);
    assert_eq!(p.data_segment(1).unwrap().encoded_payload, [3]);
    drop(p);
    cases += 1;
    let bytes = w.bytes();
    let token = Cancellation::default();
    let p = validate_swift_reactor(&bytes, SwiftValidationBudget::default(), &token).unwrap();
    let usage = p.usage();
    drop(p);
    let exact = SwiftValidationBudget {
        source_bytes: bytes.len(),
        metadata_bytes: usage.metadata_peak_reserved,
        scratch_bytes: usage.scratch_peak_reserved,
        work_credits: usage.work_used,
        ..SwiftValidationBudget::default()
    };
    validate_swift_reactor(&bytes, exact, &token).unwrap();
    cases += 1;
    for dimension in 0..4 {
        let mut b = exact;
        match dimension {
            0 => b.source_bytes -= 1,
            1 => b.metadata_bytes -= 1,
            2 => b.scratch_bytes -= 1,
            _ => b.work_credits -= 1,
        }
        let e = validate_swift_reactor(&bytes, b, &token).err().unwrap();
        assert_eq!(e.kind, SwiftValidationFailureKind::ResourceExhausted);
        assert_eq!(
            e.resource,
            Some(match dimension {
                0 => SwiftValidationResource::Source,
                1 => SwiftValidationResource::Metadata,
                2 => SwiftValidationResource::Scratch,
                _ => SwiftValidationResource::Work,
            })
        );
        cases += 1;
    }
    let cancelled = Cancellation::default();
    cancelled.cancel();
    let operation = begin(1, 0, &cancelled);
    let early = validate_swift_reactor(&bytes, SwiftValidationBudget::default(), &cancelled);
    operation.finish();
    assert_eq!(
        early.err().unwrap().kind,
        SwiftValidationFailureKind::Cancelled
    );
    assert_eq!(CALLS.load(SeqCst), 0);
    cases += 1;
    for dimension in 0..5 {
        let mut b = SwiftValidationBudget::default();
        match dimension {
            0 => b.source_bytes += 1,
            1 => b.metadata_bytes += 1,
            2 => b.scratch_bytes += 1,
            3 => b.work_credits += 1,
            _ => b.deadline_ms = u64::MAX,
        }
        let operation = begin(1, 0, &token);
        let e = validate_swift_reactor(&bytes, b, &token).err().unwrap();
        operation.finish();
        assert_eq!(CALLS.load(SeqCst), 0);
        assert_eq!(e.kind, SwiftValidationFailureKind::InvalidBudget);
        cases += 1;
    }
    for dimension in 0..5 {
        let mut b = SwiftValidationBudget::default();
        match dimension {
            0 => b.source_bytes = 0,
            1 => b.metadata_bytes = 0,
            2 => b.scratch_bytes = 0,
            3 => b.work_credits = 0,
            _ => b.deadline_ms = 0,
        }
        let e = validate_swift_reactor(&bytes, b, &token).err().unwrap();
        assert_eq!(
            e.kind,
            if dimension == 4 {
                SwiftValidationFailureKind::Deadline
            } else {
                SwiftValidationFailureKind::ResourceExhausted
            }
        );
        cases += 1;
    }
    let operation = begin(0, 0, &token);
    let result = validate_swift_reactor(&bytes, SwiftValidationBudget::default(), &token);
    let baseline = operation.finish();
    let allocations = CALLS.load(SeqCst);
    assert_eq!(REALLOCATIONS.load(SeqCst), 0);
    drop(result.unwrap());
    assert_eq!(LIVE.load(SeqCst), baseline);
    for ordinal in 1..=allocations {
        let before = LIVE.load(SeqCst);
        let operation = begin(ordinal, 0, &token);
        let result = validate_swift_reactor(&bytes, SwiftValidationBudget::default(), &token);
        operation.finish();
        assert_eq!(
            result.err().unwrap().kind,
            SwiftValidationFailureKind::AllocationFailure
        );
        assert_eq!(CALLS.load(SeqCst), ordinal);
        assert_eq!(LIVE.load(SeqCst), before);
        let cancel = Cancellation::default();
        let before = LIVE.load(SeqCst);
        let operation = begin(0, ordinal, &cancel);
        let result = validate_swift_reactor(&bytes, SwiftValidationBudget::default(), &cancel);
        operation.finish();
        assert_eq!(
            result.err().unwrap().kind,
            SwiftValidationFailureKind::Cancelled
        );
        assert_eq!(CALLS.load(SeqCst), ordinal);
        assert_eq!(LIVE.load(SeqCst), before);
    }
    println!("independent_probe_cases={cases} allocation_failure_ordinals={allocations} cancellation_ordinals={allocations} all_passed=true target_executed=false");
}
