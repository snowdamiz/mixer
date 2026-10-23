#![cfg(feature = "experimental-stream-validation")]
// This integration executable contains one test and runs with one test thread.
use mixer_vm::experimental::{validate_spans, FailureKind, Resource, ValidationBudget};
use mixer_vm::{Cancellation, Limits};
use std::alloc::{GlobalAlloc, Layout, System};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering::SeqCst};

struct CheckedAllocator;
static ACTIVE: AtomicBool = AtomicBool::new(false);
static LIVE: AtomicUsize = AtomicUsize::new(0);
static PEAK: AtomicUsize = AtomicUsize::new(0);
static ORDINAL: AtomicUsize = AtomicUsize::new(0);
static FAIL: AtomicUsize = AtomicUsize::new(0);
static REALLOC: AtomicUsize = AtomicUsize::new(0);
static SOURCE_BYTES: AtomicUsize = AtomicUsize::new(0);
static SOURCE_COPIES: AtomicUsize = AtomicUsize::new(0);
static CANCEL_AT: AtomicUsize = AtomicUsize::new(0);
static CANCEL_READY: AtomicBool = AtomicBool::new(false);
static CANCEL_RELEASE: AtomicBool = AtomicBool::new(false);
fn before(size: usize) -> bool {
    if !ACTIVE.load(SeqCst) {
        return true;
    }
    let ordinal = ORDINAL.fetch_add(1, SeqCst) + 1;
    if size == SOURCE_BYTES.load(SeqCst) {
        SOURCE_COPIES.fetch_add(1, SeqCst);
    }
    if ordinal == CANCEL_AT.load(SeqCst) {
        CANCEL_READY.store(true, SeqCst);
        while !CANCEL_RELEASE.load(SeqCst) {
            std::hint::spin_loop();
        }
    }
    ordinal != FAIL.load(SeqCst)
}
fn added(bytes: usize) {
    let n = LIVE.fetch_add(bytes, SeqCst) + bytes;
    if ACTIVE.load(SeqCst) {
        PEAK.fetch_max(n, SeqCst);
    }
}
unsafe impl GlobalAlloc for CheckedAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        if !before(layout.size()) {
            return std::ptr::null_mut();
        }
        let p = System.alloc(layout);
        if !p.is_null() {
            added(layout.size());
        }
        p
    }
    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        if !before(layout.size()) {
            return std::ptr::null_mut();
        }
        let p = System.alloc_zeroed(layout);
        if !p.is_null() {
            added(layout.size());
        }
        p
    }
    unsafe fn dealloc(&self, p: *mut u8, layout: Layout) {
        System.dealloc(p, layout);
        LIVE.fetch_sub(layout.size(), SeqCst);
    }
    unsafe fn realloc(&self, p: *mut u8, layout: Layout, bytes: usize) -> *mut u8 {
        if ACTIVE.load(SeqCst) {
            REALLOC.fetch_add(1, SeqCst);
        }
        if !before(bytes) {
            return std::ptr::null_mut();
        }
        let q = System.realloc(p, layout, bytes);
        if !q.is_null() {
            LIVE.fetch_sub(layout.size(), SeqCst);
            added(bytes);
        }
        q
    }
}
#[global_allocator]
static ALLOCATOR: CheckedAllocator = CheckedAllocator;
fn uint(mut n: usize) -> Vec<u8> {
    let mut b = vec![];
    loop {
        let v = (n & 127) as u8;
        n >>= 7;
        b.push(v | if n == 0 { 0 } else { 128 });
        if n == 0 {
            return b;
        }
    }
}
fn section(m: &mut Vec<u8>, id: u8, b: &[u8]) {
    m.push(id);
    m.extend(uint(b.len()));
    m.extend(b);
}
fn fixture() -> Vec<u8> {
    let mut m = b"\0asm\x01\0\0\0".to_vec();
    let mut types = uint(96);
    for n in 0..96 {
        types.push(0x60);
        types.extend(uint(n));
        types.extend(vec![0x7f; n]);
        types.push(0);
    }
    section(&mut m, 1, &types);
    section(&mut m, 3, &[2, 0, 0]);
    let mut exports = uint(333);
    for i in (0..333).rev() {
        let n = format!("independent_shared_prefix_{i:04}");
        exports.extend(uint(n.len()));
        exports.extend(n.bytes());
        exports.extend([0, 0]);
    }
    section(&mut m, 7, &exports);
    let mut body = vec![1];
    body.extend(uint(513));
    body.push(0x7e);
    for _ in 0..100 {
        body.extend([2, 0x40]);
    }
    for _ in 0..257 {
        body.extend([0x41, 0]);
    }
    body.extend(vec![0x1a; 257]);
    body.extend(vec![0x0b; 101]);
    let mut code = vec![2];
    code.extend(uint(body.len()));
    code.extend(body);
    code.extend([2, 0, 0x0b]);
    section(&mut m, 10, &code);
    m
}
fn begin(source: usize, fail: usize) -> usize {
    let base = LIVE.load(SeqCst);
    PEAK.store(base, SeqCst);
    ORDINAL.store(0, SeqCst);
    FAIL.store(fail, SeqCst);
    REALLOC.store(0, SeqCst);
    SOURCE_BYTES.store(source, SeqCst);
    SOURCE_COPIES.store(0, SeqCst);
    ACTIVE.store(true, SeqCst);
    base
}
fn end() {
    ACTIVE.store(false, SeqCst);
    FAIL.store(0, SeqCst);
}

#[test]
fn every_growth_failure_and_cancellation_gate_releases_owned_buffers() {
    let input = fixture();
    let cancellation = Cancellation::default();
    let base = begin(input.len(), 0);
    let result = validate_spans(
        &input,
        Limits::default(),
        ValidationBudget::default(),
        &cancellation,
    );
    let usage = result.as_ref().unwrap().usage();
    let calls = ORDINAL.load(SeqCst);
    drop(result);
    let peak = PEAK.load(SeqCst) - base;
    end();
    assert_eq!(LIVE.load(SeqCst), base);
    assert!(peak <= usage.total_peak_reserved);
    assert_eq!(REALLOC.load(SeqCst), 0);
    assert_eq!(SOURCE_COPIES.load(SeqCst), 1);
    for ordinal in 1..=calls {
        let base = begin(input.len(), ordinal);
        let result = validate_spans(
            &input,
            Limits::default(),
            ValidationBudget::default(),
            &cancellation,
        );
        let kind = result.err().map(|e| e.kind);
        end();
        assert_eq!(
            kind,
            Some(FailureKind::AllocationFailure),
            "ordinal {ordinal}"
        );
        assert_eq!(LIVE.load(SeqCst), base, "leak at ordinal {ordinal}");
        assert_eq!(REALLOC.load(SeqCst), 0);
    }
    // A separate thread cancels while each exact validator allocation is paused.
    // All harness/thread allocations finish before ACTIVE is set; join happens after end().
    for gate in 1..=calls {
        let cancellation = Cancellation::default();
        let child_cancel = cancellation.clone();
        CANCEL_READY.store(false, SeqCst);
        CANCEL_RELEASE.store(false, SeqCst);
        let ready = std::sync::Arc::new(AtomicBool::new(false));
        let child_ready = ready.clone();
        let child = std::thread::spawn(move || {
            child_ready.store(true, SeqCst);
            while !CANCEL_READY.load(SeqCst) {
                std::hint::spin_loop();
            }
            child_cancel.cancel();
            CANCEL_RELEASE.store(true, SeqCst);
            while ACTIVE.load(SeqCst) {
                std::hint::spin_loop();
            }
        });
        while !ready.load(SeqCst) {
            std::hint::spin_loop();
        }
        CANCEL_AT.store(gate, SeqCst);
        let base = begin(input.len(), 0);
        let result = validate_spans(
            &input,
            Limits::default(),
            ValidationBudget::default(),
            &cancellation,
        );
        let kind = result.err().map(|e| e.kind);
        end();
        CANCEL_AT.store(0, SeqCst);
        let after = LIVE.load(SeqCst);
        child.join().unwrap();
        assert_eq!(kind, Some(FailureKind::Cancelled), "cancel gate {gate}");
        // The child's thread local teardown can race this read by freeing only.
        assert!(
            after <= base,
            "buffer leak at cancellation gate {gate}: {after}>{base}"
        );
    }
    println!("independent allocation boundaries: calls={calls} failed_ordinals={calls} cancellation_gates={calls} measured_peak={peak} reserved_peak={}",usage.total_peak_reserved);

    // Only the last flat-parameter growth dominates this fixture's metadata
    // peak: old 8192 plus new 16384 slots overlap, despite only 8256 live types.
    let mut growth = b"\0asm\x01\0\0\0".to_vec();
    let mut types = uint(129);
    for _ in 0..129 {
        types.extend([0x60, 64]);
        types.extend([0x7f; 64]);
        types.push(0);
    }
    section(&mut growth, 1, &types);
    let base = begin(growth.len(), 0);
    let result = validate_spans(
        &growth,
        Limits::default(),
        ValidationBudget::default(),
        &cancellation,
    );
    let full_usage = result.as_ref().unwrap().usage();
    let full_calls = ORDINAL.load(SeqCst);
    drop(result);
    end();
    assert_eq!(LIVE.load(SeqCst), base);
    assert!(full_usage.metadata_peak_reserved > full_usage.metadata_reserved);
    let budget = ValidationBudget {
        metadata_bytes: full_usage.metadata_reserved,
        ..ValidationBudget::default()
    };
    let base = begin(growth.len(), 0);
    let result = validate_spans(&growth, Limits::default(), budget, &cancellation);
    let error = result.err().unwrap();
    let rejected_calls = ORDINAL.load(SeqCst);
    end();
    assert_eq!(LIVE.load(SeqCst), base);
    assert_eq!(
        (error.kind, error.resource),
        (FailureKind::ResourceExhausted, Some(Resource::Metadata))
    );
    assert_eq!(error.limit as usize, full_usage.metadata_reserved);
    assert_eq!(error.attempted as usize, full_usage.metadata_peak_reserved);
    assert_eq!(
        rejected_calls + 1,
        full_calls,
        "overlap rejected before allocation"
    );
    println!("independent growth overlap: retained={} peak={} full_calls={full_calls} rejected_calls={rejected_calls}", full_usage.metadata_reserved, full_usage.metadata_peak_reserved);
}
