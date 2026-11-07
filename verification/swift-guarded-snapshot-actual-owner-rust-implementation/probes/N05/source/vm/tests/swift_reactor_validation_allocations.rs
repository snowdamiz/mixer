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
thread_local! {
    static DELAY_AT: Cell<usize> = const { Cell::new(0) };
    static DELAY_MS: Cell<u64> = const { Cell::new(0) };
    static DELAY_REACHED: Cell<bool> = const { Cell::new(false) };
}
fn delay() {
    let at = DELAY_AT.with(Cell::get);
    if at != 0 && CALLS.load(SeqCst) + 1 == at {
        DELAY_REACHED.with(|reached| reached.set(true));
        let end = Instant::now() + Duration::from_millis(DELAY_MS.with(Cell::get));
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

// A busy host can exhaust a real deadline before the selected allocation. Such
// an attempt proves early cleanup, but cannot count as ordinal coverage. Retry
// with a bounded larger budget; only the actual delayed ordinal can pass.
fn deadline_at(
    bytes: &[u8],
    cancellation: &Cancellation,
    ordinal: usize,
    budgets_ms: &[u64],
) -> Result<(SwiftValidationFailure, usize), usize> {
    assert!(ordinal > 0);
    for (attempt, &deadline_ms) in budgets_ms.iter().enumerate() {
        let before = LIVE.load(SeqCst);
        DELAY_MS.with(|delay| delay.set(deadline_ms.checked_add(10).unwrap()));
        DELAY_REACHED.with(|reached| reached.set(false));
        DELAY_AT.with(|at| at.set(ordinal));
        let operation = begin(0, 0, cancellation);
        let result = validate_swift_reactor(
            bytes,
            SwiftValidationBudget {
                deadline_ms,
                ..SwiftValidationBudget::default()
            },
            cancellation,
        );
        operation.finish();
        DELAY_AT.with(|at| at.set(0));
        let reached = DELAY_REACHED.with(Cell::get);
        let calls = CALLS.load(SeqCst);
        let error = result.err().unwrap();
        assert_eq!(
            error.kind,
            SwiftValidationFailureKind::Deadline,
            "deadline ordinal {ordinal}, attempt {attempt}, budget {deadline_ms} ms"
        );
        assert_eq!(
            LIVE.load(SeqCst),
            before,
            "leak at deadline ordinal {ordinal}, attempt {attempt}"
        );
        assert_eq!(REALLOCATIONS.load(SeqCst), 0);
        if reached {
            assert_eq!(
                calls, ordinal,
                "deadline cleanup allocated at ordinal {ordinal}, attempt {attempt}"
            );
            return Ok((error, attempt));
        }
        assert!(calls < ordinal, "unobserved delay at ordinal {ordinal}");
        println!(
            "Deadline ordinal {ordinal}: early expiry at {calls} allocations with {deadline_ms} ms; ordinal coverage not accepted"
        );
    }
    Err(budgets_ms.len())
}

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
    // Exercise both retry and exhaustion deterministically through the real
    // zero-deadline entry path, within this observer's single test lane.
    let (_, retries) = deadline_at(&bytes, &cancellation, 2, &[0, 10, 40, 160, 640])
        .expect("the exact ordinal must be reached within the bounded retries");
    assert!(retries >= 1);
    assert!(matches!(
        deadline_at(&bytes, &cancellation, 2, &[0, 0]),
        Err(2)
    ));
    for ordinal in 1..=allocations {
        let (error, _) = deadline_at(&bytes, &cancellation, ordinal, &[10, 40, 160, 640])
            .unwrap_or_else(|attempts| {
                panic!("deadline ordinal {ordinal} was not reached after {attempts} attempts")
            });
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
