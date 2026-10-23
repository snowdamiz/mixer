#![cfg(feature = "experimental-swift-reactor")]
#[path = "common/allocation_observer.rs"]
#[allow(dead_code)]
mod observer;
mod swift_reactor_validation_fixture;
use mixer_vm::experimental_swift_reactor::*;
use mixer_vm::Cancellation;
use observer::{begin, Ownership, CALLS, LIVE, PEAK, REALLOCATIONS};
use std::alloc::{GlobalAlloc, Layout};
use std::cell::Cell;
use std::sync::atomic::Ordering::SeqCst;
use std::time::{Duration, Instant};
use swift_reactor_validation_fixture::*;

// Only this synchronous test lane can delay an observed allocation. This is a
// native test observation, never a clock/policy hook exposed by the validator.
thread_local! { static DELAY_AT: Cell<usize> = const { Cell::new(0) }; }
fn delay() {
    let at = DELAY_AT.with(Cell::get);
    if at != 0 && CALLS.load(SeqCst) + 1 == at {
        let end = Instant::now() + Duration::from_millis(20);
        while Instant::now() < end {
            std::hint::spin_loop();
        }
    }
}
struct Observed;
unsafe impl GlobalAlloc for Observed {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        delay();
        unsafe { observer::Observed.alloc(layout) }
    }
    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        delay();
        unsafe { observer::Observed.alloc_zeroed(layout) }
    }
    unsafe fn dealloc(&self, pointer: *mut u8, layout: Layout) {
        unsafe { observer::Observed.dealloc(pointer, layout) }
    }
    unsafe fn realloc(&self, pointer: *mut u8, layout: Layout, bytes: usize) -> *mut u8 {
        delay();
        unsafe { observer::Observed.realloc(pointer, layout, bytes) }
    }
}
#[global_allocator]
static ALLOCATOR: Observed = Observed;

#[test]
fn every_allocation_ordinal_failure_cancellation_deadline_and_cleanup_are_observed() {
    let mut fixture = Fixture::default();
    fixture.bodies[0] = Fixture::block_body(511);
    fixture.bodies[27] = Fixture::operand_body(128);
    fixture.globals.resize(40, vec![0x7f, 0, 0x41, 0, 0x0b]);
    fixture.data.push(data_segment(0, &[1, 2, 3]));
    fixture.elements.push(element_segment(0, &[34, 35, 62]));
    let bytes = fixture.bytes();
    let _ownership = Ownership::new();
    let cancellation = Cancellation::default();
    let operation = begin(0, 0, &cancellation);
    let result = validate_swift_reactor(&bytes, SwiftValidationBudget::default(), &cancellation);
    let baseline = operation.finish();
    let p = result.unwrap();
    let allocations = CALLS.load(SeqCst);
    let peak = PEAK.load(SeqCst) - baseline;
    let retained = LIVE.load(SeqCst) - baseline;
    let usage = p.usage();
    assert_eq!(REALLOCATIONS.load(SeqCst), 0);
    assert!(peak <= usage.total_peak_reserved);
    assert!(retained <= usage.source_bytes + usage.metadata_reserved);
    drop(p);
    assert_eq!(LIVE.load(SeqCst), baseline);
    let mut cancellation_body = false;
    let mut deadline_body = false;
    let mut metadata_failure = false;
    for ordinal in 1..=allocations {
        let before = LIVE.load(SeqCst);
        let operation = begin(ordinal, 0, &cancellation);
        let result =
            validate_swift_reactor(&bytes, SwiftValidationBudget::default(), &cancellation);
        operation.finish();
        let error = result.err().unwrap();
        assert_eq!(
            error.kind,
            SwiftValidationFailureKind::AllocationFailure,
            "failure ordinal {ordinal}"
        );
        assert_eq!(
            CALLS.load(SeqCst),
            ordinal,
            "failure cleanup allocated at ordinal {ordinal}"
        );
        assert_eq!(
            LIVE.load(SeqCst),
            before,
            "leak at failure ordinal {ordinal}"
        );
        metadata_failure |= error.function.is_none() && error.offset > 0;
        let token = Cancellation::default();
        let before = LIVE.load(SeqCst);
        let operation = begin(0, ordinal, &token);
        let result = validate_swift_reactor(&bytes, SwiftValidationBudget::default(), &token);
        operation.finish();
        let error = result.err().unwrap();
        assert_eq!(
            error.kind,
            SwiftValidationFailureKind::Cancelled,
            "cancellation ordinal {ordinal}"
        );
        assert_eq!(
            CALLS.load(SeqCst),
            ordinal,
            "cancellation cleanup allocated at ordinal {ordinal}"
        );
        assert_eq!(
            LIVE.load(SeqCst),
            before,
            "leak at cancellation ordinal {ordinal}"
        );
        cancellation_body |= error.function.is_some();
    }
    // Delay representative source, metadata and body allocations past a real
    // cooperative deadline. Use every ordinal so no timing estimate chooses
    // which stage is covered. No validation work or allocation happens in Drop.
    let mut deadline_source = false;
    let mut deadline_metadata = false;
    for ordinal in 1..=allocations {
        let before = LIVE.load(SeqCst);
        DELAY_AT.with(|at| at.set(ordinal));
        let operation = begin(0, 0, &cancellation);
        let result = validate_swift_reactor(
            &bytes,
            SwiftValidationBudget {
                deadline_ms: 10,
                ..SwiftValidationBudget::default()
            },
            &cancellation,
        );
        operation.finish();
        DELAY_AT.with(|at| at.set(0));
        let error = result.err().unwrap();
        assert_eq!(
            error.kind,
            SwiftValidationFailureKind::Deadline,
            "deadline ordinal {ordinal}"
        );
        assert_eq!(
            CALLS.load(SeqCst),
            ordinal,
            "deadline cleanup allocated at ordinal {ordinal}"
        );
        assert_eq!(
            LIVE.load(SeqCst),
            before,
            "leak at deadline ordinal {ordinal}"
        );
        deadline_source |= error.offset == 0 && error.function.is_none();
        deadline_metadata |= error.offset > 0 && error.function.is_none();
        deadline_body |= error.function.is_some();
    }
    assert!(
        metadata_failure
            && cancellation_body
            && deadline_source
            && deadline_metadata
            && deadline_body
    );
    // Invalid budgets are rejected before the first allocation, including an
    // overflowing deadline input. Zero-deadline/cancelled entry cleanup is free.
    for budget in [
        SwiftValidationBudget {
            source_bytes: usize::MAX,
            ..SwiftValidationBudget::default()
        },
        SwiftValidationBudget {
            deadline_ms: u64::MAX,
            ..SwiftValidationBudget::default()
        },
    ] {
        let operation = begin(1, 0, &cancellation);
        let result = validate_swift_reactor(&bytes, budget, &cancellation);
        operation.finish();
        assert_eq!(
            result.err().unwrap().kind,
            SwiftValidationFailureKind::InvalidBudget
        );
        assert_eq!(CALLS.load(SeqCst), 0);
    }
    println!("Swift validation requested-byte observations: allocation_ordinals={allocations}; requested_peak={peak}; retained={retained}; internal_peak_reserved={}; source/metadata/body deadline stages=true; every allocation failure and cancellation ordinal cleaned without allocating; no reallocations; no RSS measurement",usage.total_peak_reserved);
}
