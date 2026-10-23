#![cfg(feature = "experimental-stream-validation")]
mod common;
use common::*;
use mixer_vm::experimental::{validate_spans, FailureKind, ValidationBudget};
use mixer_vm::{Cancellation, Limits, Profile};
use std::alloc::{GlobalAlloc, Layout, System};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering::SeqCst};
// Separate single-test process: no other test can contaminate gated observations.
struct Observed;
static ACTIVE: AtomicBool = AtomicBool::new(false);
static LIVE: AtomicUsize = AtomicUsize::new(0);
static PEAK: AtomicUsize = AtomicUsize::new(0);
static CALLS: AtomicUsize = AtomicUsize::new(0);
static REALLOCS: AtomicUsize = AtomicUsize::new(0);
static FAIL: AtomicUsize = AtomicUsize::new(0);
static SOURCE_SIZE: AtomicUsize = AtomicUsize::new(0);
static SOURCE_HITS: AtomicUsize = AtomicUsize::new(0);
static GATE_CALL: AtomicUsize = AtomicUsize::new(0);
static READY: AtomicBool = AtomicBool::new(false);
static GATE: AtomicBool = AtomicBool::new(false);
static REACHED: AtomicBool = AtomicBool::new(false);
static RELEASE: AtomicBool = AtomicBool::new(false);
fn allocation(size: usize) -> bool {
    if !ACTIVE.load(SeqCst) {
        return true;
    }
    let call = CALLS.fetch_add(1, SeqCst) + 1;
    if size == SOURCE_SIZE.load(SeqCst) {
        SOURCE_HITS.fetch_add(1, SeqCst);
    }
    if GATE.load(SeqCst) && call == GATE_CALL.load(SeqCst) {
        REACHED.store(true, SeqCst);
        while !RELEASE.load(SeqCst) {
            std::hint::spin_loop();
        }
    }
    call != FAIL.load(SeqCst)
}
fn added(bytes: usize) {
    let n = LIVE.fetch_add(bytes, SeqCst) + bytes;
    if ACTIVE.load(SeqCst) {
        PEAK.fetch_max(n, SeqCst);
    }
}
unsafe impl GlobalAlloc for Observed {
    unsafe fn alloc(&self, l: Layout) -> *mut u8 {
        if !allocation(l.size()) {
            return std::ptr::null_mut();
        }
        let p = System.alloc(l);
        if !p.is_null() {
            added(l.size());
        }
        p
    }
    unsafe fn alloc_zeroed(&self, l: Layout) -> *mut u8 {
        if !allocation(l.size()) {
            return std::ptr::null_mut();
        }
        let p = System.alloc_zeroed(l);
        if !p.is_null() {
            added(l.size());
        }
        p
    }
    unsafe fn dealloc(&self, p: *mut u8, l: Layout) {
        System.dealloc(p, l);
        LIVE.fetch_sub(l.size(), SeqCst);
    }
    unsafe fn realloc(&self, p: *mut u8, l: Layout, n: usize) -> *mut u8 {
        if ACTIVE.load(SeqCst) {
            REALLOCS.fetch_add(1, SeqCst);
        }
        if !allocation(n) {
            return std::ptr::null_mut();
        }
        let q = System.realloc(p, l, n);
        if !q.is_null() {
            LIVE.fetch_sub(l.size(), SeqCst);
            added(n);
        }
        q
    }
}
#[global_allocator]
static ALLOCATOR: Observed = Observed;
fn begin(source: usize, fail: usize) -> usize {
    let baseline = LIVE.load(SeqCst);
    PEAK.store(baseline, SeqCst);
    CALLS.store(0, SeqCst);
    REALLOCS.store(0, SeqCst);
    SOURCE_SIZE.store(source, SeqCst);
    SOURCE_HITS.store(0, SeqCst);
    FAIL.store(fail, SeqCst);
    ACTIVE.store(true, SeqCst);
    baseline
}
fn end() {
    ACTIVE.store(false, SeqCst);
    FAIL.store(0, SeqCst);
}
fn large_metadata() -> Vec<u8> {
    let mut m = b"\0asm\x01\0\0\0".to_vec();
    let mut t = u32leb(512);
    for _ in 0..512 {
        t.push(0x60);
        t.extend(u32leb(4096));
        t.extend(vec![0x7f; 4096]);
        t.push(0);
    }
    section(&mut m, 1, t);
    section(&mut m, 3, vec![1, 0]);
    section(&mut m, 10, vec![1, 2, 0, 0x0b]);
    m
}
fn large_table(labels: u32) -> Vec<u8> {
    let mut code = vec![2, 0x40, 0x41, 0, 0x0e];
    code.extend(u32leb(labels));
    code.extend(vec![0; labels as usize + 1]);
    code.extend([0x0b, 0x0b]);
    Spec::one(vec![], None, code).bytes()
}
fn observe_owned(label: &str, source: &[u8], limits: Limits) -> (usize, usize, usize) {
    let cancellation = Cancellation::default();
    let baseline = begin(source.len(), 0);
    let result = validate_spans(source, limits, ValidationBudget::default(), &cancellation);
    end();
    let sealed = result.unwrap();
    let actual = PEAK.load(SeqCst) - baseline;
    let calls = CALLS.load(SeqCst);
    let retained = LIVE.load(SeqCst) - baseline;
    assert!(
        actual <= sealed.usage().total_peak_reserved,
        "direct peak exceeds reservation"
    );
    assert_eq!(
        REALLOCS.load(SeqCst),
        0,
        "source Box conversion or buffer growth used realloc"
    );
    assert_eq!(
        SOURCE_HITS.load(SeqCst),
        1,
        "source copied into more than one allocation of exact size"
    );
    let u = sealed.usage();
    drop(sealed);
    assert_eq!(LIVE.load(SeqCst), baseline);
    println!("observation {label}: source={} requested_peak={actual} retained={retained} allocations={calls} total_peak_reserved={} metadata_peak_reserved={} scratch_peak_reserved={} work={}",source.len(),u.total_peak_reserved,u.metadata_peak_reserved,u.scratch_peak_reserved,u.work_used);
    (actual, retained, u.scratch_peak_reserved)
}
#[test]
fn requested_allocations_failure_drop_and_copy_cancellation() {
    let mut spec = Spec::one(vec![], None, vec![0x0b]);
    spec.functions[0].locals = vec![mixer_vm::Type::I32; 100];
    spec.memory = Some((1, 1));
    spec.data = vec![(5, vec![0xab; 997])];
    let source = spec.bytes();
    let cancellation = Cancellation::default();
    let baseline = begin(source.len(), 0);
    let result = validate_spans(
        &source,
        Limits::default(),
        ValidationBudget::default(),
        &cancellation,
    );
    end();
    let calls = CALLS.load(SeqCst);
    let actual = PEAK.load(SeqCst) - baseline;
    let sealed = result.unwrap();
    assert!(actual <= sealed.usage().total_peak_reserved);
    assert_eq!(SOURCE_HITS.load(SeqCst), 1);
    assert_eq!(REALLOCS.load(SeqCst), 0);
    drop(sealed);
    assert_eq!(LIVE.load(SeqCst), baseline);
    for fail in 1..=calls {
        let baseline = begin(source.len(), fail);
        let result = validate_spans(
            &source,
            Limits::default(),
            ValidationBudget::default(),
            &cancellation,
        );
        end();
        let error = result.err().expect("injected allocation must fail closed");
        assert_eq!(
            error.kind,
            FailureKind::AllocationFailure,
            "allocation ordinal {fail}"
        );
        assert_eq!(
            LIVE.load(SeqCst),
            baseline,
            "allocation ordinal {fail} leaked"
        );
    }
    let narrow = Limits {
        module_bytes: source.len() - 1,
        ..Limits::default()
    };
    let baseline = begin(source.len(), 1);
    let result = validate_spans(&source, narrow, ValidationBudget::default(), &cancellation);
    end();
    assert_eq!(result.err().unwrap().kind, FailureKind::ResourceExhausted);
    assert_eq!(CALLS.load(SeqCst), 0);
    assert_eq!(LIVE.load(SeqCst), baseline);
    let invalid = Limits {
        call_depth: 0,
        ..Limits::default()
    };
    let baseline = begin(source.len(), 1);
    let result = validate_spans(&source, invalid, ValidationBudget::default(), &cancellation);
    end();
    assert_eq!(result.err().unwrap().kind, FailureKind::InvalidLimits);
    assert_eq!(CALLS.load(SeqCst), 0);
    assert_eq!(LIVE.load(SeqCst), baseline);
    // Gate source, metadata and body-scratch allocation boundaries. The helper
    // cancels before returning to parser/type traversal, without production hooks.
    for ordinal in [1, 2, 5, calls] {
        let cancellation = Cancellation::default();
        GATE_CALL.store(ordinal, SeqCst);
        GATE.store(true, SeqCst);
        READY.store(false, SeqCst);
        REACHED.store(false, SeqCst);
        RELEASE.store(false, SeqCst);
        let canceller = cancellation.clone();
        let worker = std::thread::spawn(move || {
            READY.store(true, SeqCst);
            let deadline = std::time::Instant::now() + std::time::Duration::from_secs(10);
            while !REACHED.load(SeqCst) && std::time::Instant::now() < deadline {
                std::hint::spin_loop();
            }
            let reached = REACHED.load(SeqCst);
            canceller.cancel();
            RELEASE.store(true, SeqCst);
            reached
        });
        while !READY.load(SeqCst) {
            std::hint::spin_loop();
        }
        begin(source.len(), 0);
        let result = validate_spans(
            &source,
            Limits::default(),
            ValidationBudget::default(),
            &cancellation,
        );
        end();
        GATE.store(false, SeqCst);
        assert!(
            worker.join().unwrap(),
            "allocation gate {ordinal} was not reached"
        );
        assert_eq!(result.err().unwrap().kind, FailureKind::Cancelled);
    }
    println!("all {calls} allocation ordinals failed closed, no retained allocation after each failure; four gated source/metadata/body cancellations returned no proof");
    let small = large_table(10);
    let large = large_table(200_000);
    let (_, _, a) = observe_owned("branch-labels-10", &small, Limits::default());
    let (_, _, b) = observe_owned("branch-labels-200000", &large, Limits::default());
    assert_eq!(a, b, "branch target count must not allocate labels");
    let source = large_metadata();
    observe_owned("512-types-each-4096-parameters", &source, Limits::default());
    let mut code = vec![1; 199_999];
    code.push(0x0b);
    let source = Spec::one(vec![], None, code).bytes();
    observe_owned("200000-instructions", &source, Limits::default());
    let mut source = b"\0asm\x01\0\0\0".to_vec();
    let mut custom = vec![0];
    custom.extend(vec![0; 4 * 1024 * 1024 - 14]);
    section(&mut source, 0, custom);
    assert_eq!(source.len(), 4 * 1024 * 1024);
    observe_owned("exact-4MiB-source", &source, Limits::default());
    let mut code = vec![];
    for _ in 0..127 {
        code.extend([2, 0x40]);
    }
    code.extend(vec![0x0b; 128]);
    let source = Spec::one(vec![], None, code).bytes();
    observe_owned("128-controls", &source, Limits::default());
    let mut code = vec![];
    for _ in 0..4096 {
        code.extend([0x41, 0]);
    }
    code.extend(vec![0x1a; 4096]);
    code.push(0x0b);
    let source = Spec::one(vec![], None, code).bytes();
    observe_owned("4096-operands", &source, Limits::default());
    // Different profiles are measured separately; table data stays encoded.
    let mut s = Spec::one(vec![], None, vec![0x0b]);
    s.table = Some((65_536, 65_536));
    s.elements = vec![(0, vec![0; 65_536])];
    let source = s.bytes();
    observe_owned(
        "v3-65536-elements",
        &source,
        Limits {
            profile: Profile::TableMemoryV3,
            ..Limits::default()
        },
    );
}
