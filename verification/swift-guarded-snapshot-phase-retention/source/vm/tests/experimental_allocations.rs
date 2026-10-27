#![cfg(feature = "experimental-stream-validation")]
mod common;
use common::*;
use mixer_vm::experimental::{validate_spans, FailureKind, ValidationBudget};
use mixer_vm::{Cancellation, Limits, Profile};
#[path = "common/legacy_allocation_observer.rs"]
mod allocation_observer;
use allocation_observer::{
    Lane, Observed, CALLS, LIVE, MAX_SLOTS, PEAK, REACHED, REALLOCS, RELEASE, SOURCE_HITS,
};
use std::sync::atomic::{AtomicBool, Ordering::SeqCst};
static READY: AtomicBool = AtomicBool::new(false);
#[global_allocator]
static ALLOCATOR: Observed = Observed;
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
fn observe_owned(
    observer: &Lane,
    label: &str,
    source: &[u8],
    limits: Limits,
) -> (usize, usize, usize) {
    let cancellation = Cancellation::default();
    let operation = observer.begin(source.len(), 0);
    let baseline = operation.baseline();
    let result = validate_spans(source, limits, ValidationBudget::default(), &cancellation);
    operation.finish();
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
    let observer = Lane::new();
    let mut spec = Spec::one(vec![], None, vec![0x0b]);
    spec.functions[0].locals = vec![mixer_vm::Type::I32; 100];
    spec.memory = Some((1, 1));
    spec.data = vec![(5, vec![0xab; 997])];
    let source = spec.bytes();
    let cancellation = Cancellation::default();
    let operation = observer.begin(source.len(), 0);
    let baseline = operation.baseline();
    let result = validate_spans(
        &source,
        Limits::default(),
        ValidationBudget::default(),
        &cancellation,
    );
    operation.finish();
    let calls = CALLS.load(SeqCst);
    let actual = PEAK.load(SeqCst) - baseline;
    let sealed = result.unwrap();
    assert!(actual <= sealed.usage().total_peak_reserved);
    assert_eq!(SOURCE_HITS.load(SeqCst), 1);
    assert_eq!(REALLOCS.load(SeqCst), 0);
    drop(sealed);
    assert_eq!(LIVE.load(SeqCst), baseline);
    for fail in 1..=calls {
        let operation = observer.begin(source.len(), fail);
        let baseline = operation.baseline();
        let result = validate_spans(
            &source,
            Limits::default(),
            ValidationBudget::default(),
            &cancellation,
        );
        operation.finish();
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
    let operation = observer.begin(source.len(), 1);
    let baseline = operation.baseline();
    let result = validate_spans(&source, narrow, ValidationBudget::default(), &cancellation);
    operation.finish();
    assert_eq!(result.err().unwrap().kind, FailureKind::ResourceExhausted);
    assert_eq!(CALLS.load(SeqCst), 0);
    assert_eq!(LIVE.load(SeqCst), baseline);
    let invalid = Limits {
        call_depth: 0,
        ..Limits::default()
    };
    let operation = observer.begin(source.len(), 1);
    let baseline = operation.baseline();
    let result = validate_spans(&source, invalid, ValidationBudget::default(), &cancellation);
    operation.finish();
    assert_eq!(result.err().unwrap().kind, FailureKind::InvalidLimits);
    assert_eq!(CALLS.load(SeqCst), 0);
    assert_eq!(LIVE.load(SeqCst), baseline);
    // Gate source, metadata and body-scratch allocation boundaries. The helper
    // cancels before returning to parser/type traversal, without production hooks.
    for ordinal in [1, 2, 5, calls] {
        let cancellation = Cancellation::default();
        allocation_observer::gate(ordinal);
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
        let operation = observer.begin(source.len(), 0);
        let result = validate_spans(
            &source,
            Limits::default(),
            ValidationBudget::default(),
            &cancellation,
        );
        operation.finish();
        allocation_observer::ungate();
        assert!(
            worker.join().unwrap(),
            "allocation gate {ordinal} was not reached"
        );
        assert_eq!(result.err().unwrap().kind, FailureKind::Cancelled);
    }
    println!("all {calls} allocation ordinals failed closed, no retained allocation after each failure; four gated source/metadata/body cancellations returned no proof");
    let small = large_table(10);
    let large = large_table(200_000);
    let (_, _, a) = observe_owned(&observer, "branch-labels-10", &small, Limits::default());
    let (_, _, b) = observe_owned(&observer, "branch-labels-200000", &large, Limits::default());
    assert_eq!(a, b, "branch target count must not allocate labels");
    let source = large_metadata();
    observe_owned(
        &observer,
        "512-types-each-4096-parameters",
        &source,
        Limits::default(),
    );
    let mut code = vec![1; 199_999];
    code.push(0x0b);
    let source = Spec::one(vec![], None, code).bytes();
    observe_owned(&observer, "200000-instructions", &source, Limits::default());
    let mut source = b"\0asm\x01\0\0\0".to_vec();
    let mut custom = vec![0];
    custom.extend(vec![0; 4 * 1024 * 1024 - 14]);
    section(&mut source, 0, custom);
    assert_eq!(source.len(), 4 * 1024 * 1024);
    observe_owned(&observer, "exact-4MiB-source", &source, Limits::default());
    let mut code = vec![];
    for _ in 0..127 {
        code.extend([2, 0x40]);
    }
    code.extend(vec![0x0b; 128]);
    let source = Spec::one(vec![], None, code).bytes();
    observe_owned(&observer, "128-controls", &source, Limits::default());
    let mut code = vec![];
    for _ in 0..4096 {
        code.extend([0x41, 0]);
    }
    code.extend(vec![0x1a; 4096]);
    code.push(0x0b);
    let source = Spec::one(vec![], None, code).bytes();
    observe_owned(&observer, "4096-operands", &source, Limits::default());
    // Different profiles are measured separately; table data stays encoded.
    let mut s = Spec::one(vec![], None, vec![0x0b]);
    s.table = Some((65_536, 65_536));
    s.elements = vec![(0, vec![0; 65_536])];
    let source = s.bytes();
    observe_owned(
        &observer,
        "v3-65536-elements",
        &source,
        Limits {
            profile: Profile::TableMemoryV3,
            ..Limits::default()
        },
    );
    println!(
        "observer maximum ownership slots={} capacity=4096 background_noise={}",
        MAX_SLOTS.load(SeqCst),
        std::env::var_os("MIXER_ALLOCATOR_NOISE").is_some()
    );
}
