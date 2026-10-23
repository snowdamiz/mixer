//! Independently authored public API review probes; no guest execution occurs.
use mixer_vm::experimental::cache::{
    CacheBudget, CacheFailureKind, DecodedInstruction, FunctionCache, FunctionPin, Operation,
};
use mixer_vm::experimental::{validate_spans, ValidationBudget};
use mixer_vm::{Cancellation, Limits, Type};
use std::alloc::{GlobalAlloc, Layout, System};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering::SeqCst};

struct Allocator;
static LIVE: AtomicUsize = AtomicUsize::new(0);
static CALLS: AtomicUsize = AtomicUsize::new(0);
static REALLOCATIONS: AtomicUsize = AtomicUsize::new(0);
static OBSERVE: AtomicBool = AtomicBool::new(false);
static FAIL_ORDINAL: AtomicUsize = AtomicUsize::new(0);
static FAIL_ALL: AtomicBool = AtomicBool::new(false);
fn permit() -> bool {
    if !OBSERVE.load(SeqCst) {
        return true;
    }
    let ordinal = CALLS.fetch_add(1, SeqCst) + 1;
    !FAIL_ALL.load(SeqCst) && ordinal != FAIL_ORDINAL.load(SeqCst)
}
unsafe impl GlobalAlloc for Allocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        if !permit() {
            return std::ptr::null_mut();
        }
        let result = System.alloc(layout);
        if !result.is_null() {
            LIVE.fetch_add(layout.size(), SeqCst);
        }
        result
    }
    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        if !permit() {
            return std::ptr::null_mut();
        }
        let result = System.alloc_zeroed(layout);
        if !result.is_null() {
            LIVE.fetch_add(layout.size(), SeqCst);
        }
        result
    }
    unsafe fn dealloc(&self, pointer: *mut u8, layout: Layout) {
        System.dealloc(pointer, layout);
        LIVE.fetch_sub(layout.size(), SeqCst);
    }
    unsafe fn realloc(&self, pointer: *mut u8, layout: Layout, bytes: usize) -> *mut u8 {
        if OBSERVE.load(SeqCst) {
            REALLOCATIONS.fetch_add(1, SeqCst);
        }
        if !permit() {
            return std::ptr::null_mut();
        }
        let result = System.realloc(pointer, layout, bytes);
        if !result.is_null() {
            LIVE.fetch_sub(layout.size(), SeqCst);
            LIVE.fetch_add(bytes, SeqCst);
        }
        result
    }
}
#[global_allocator]
static ALLOCATOR: Allocator = Allocator;
fn begin(ordinal: usize, all: bool) -> usize {
    CALLS.store(0, SeqCst);
    REALLOCATIONS.store(0, SeqCst);
    FAIL_ORDINAL.store(ordinal, SeqCst);
    FAIL_ALL.store(all, SeqCst);
    OBSERVE.store(true, SeqCst);
    LIVE.load(SeqCst)
}
fn end() -> (usize, usize) {
    OBSERVE.store(false, SeqCst);
    FAIL_ORDINAL.store(0, SeqCst);
    FAIL_ALL.store(false, SeqCst);
    (CALLS.load(SeqCst), REALLOCATIONS.load(SeqCst))
}

// Original, minimal Wasm assembly helpers. These do not import owner test helpers.
fn uint(mut n: u32, to: &mut Vec<u8>) {
    loop {
        let next = (n & 127) as u8;
        n >>= 7;
        to.push(next | if n == 0 { 0 } else { 128 });
        if n == 0 {
            break;
        }
    }
}
fn section(to: &mut Vec<u8>, tag: u8, payload: &[u8]) {
    to.push(tag);
    uint(payload.len() as u32, to);
    to.extend_from_slice(payload);
}
fn module(bodies: &[&[u8]], imported_checkpoint: bool) -> Vec<u8> {
    let mut result = b"\0asm\x01\0\0\0".to_vec();
    section(&mut result, 1, &[1, 0x60, 0, 0]);
    if imported_checkpoint {
        section(&mut result, 2, b"\x01\x05mixer\x0acheckpoint\0\0");
    }
    let mut functions = Vec::new();
    uint(bodies.len() as u32, &mut functions);
    functions.resize(functions.len() + bodies.len(), 0);
    section(&mut result, 3, &functions);
    let mut code = Vec::new();
    uint(bodies.len() as u32, &mut code);
    for body in bodies {
        uint(body.len() as u32, &mut code);
        code.extend_from_slice(body);
    }
    section(&mut result, 10, &code);
    result
}
fn make(bytes: &[u8], budget: CacheBudget, cancel: &Cancellation) -> FunctionCache {
    let spans = validate_spans(
        bytes,
        Limits::default(),
        ValidationBudget::default(),
        cancel,
    )
    .expect("independent legal fixture must validate");
    FunctionCache::new(spans, budget, cancel).expect("cache constructor")
}
fn pressure_fixture() -> Vec<u8> {
    module(
        &[
            &[0, 1, 0x0b],
            &[0, 1, 0x0b],
            &[0, 1, 0x0b],
            &[1, 1, 0x7e, 2, 0x40, 0x41, 0, 0x0e, 1, 0, 0, 0x0b, 0x0b],
        ],
        false,
    )
}
fn pressure_budget(bytes: &[u8], cancel: &Cancellation) -> (CacheBudget, usize, usize) {
    let budget = CacheBudget {
        max_entries: 3,
        max_pins: 4,
        ..CacheBudget::default()
    };
    let probe = make(bytes, budget, cancel);
    let base = probe.usage().peak_cache_reserved;
    let small = 2 * std::mem::size_of::<DecodedInstruction>();
    let large = 5 * std::mem::size_of::<DecodedInstruction>()
        + std::mem::size_of::<Type>()
        + std::mem::size_of::<u32>();
    assert!(small < large && large < 3 * small);
    (
        CacheBudget {
            capacity_bytes: base + small + large,
            ..budget
        },
        small,
        large,
    )
}
fn seed(bytes: &[u8], budget: CacheBudget, cancel: &Cancellation) -> (FunctionCache, FunctionPin) {
    let mut cache = make(bytes, budget, cancel);
    let keep = cache.pin(0, cancel).unwrap();
    for function in [1, 2] {
        let pin = cache.pin(function, cancel).unwrap();
        cache.release(pin).unwrap();
    }
    (cache, keep)
}
fn pressure_and_work_transaction() {
    let cancel = Cancellation::default();
    let bytes = pressure_fixture();
    let (budget, small, large) = pressure_budget(&bytes, &cancel);
    let (mut cache, keep) = seed(&bytes, budget, &cancel);
    let before_work = cache.usage().work_used;
    let large_pin = cache.pin(3, &cancel).unwrap();
    let after_work = cache.usage().work_used;
    assert_eq!(cache.usage().evictions, 2);
    assert_eq!(cache.usage().resident_bytes, small + large);
    assert_eq!(cache.usage().pinned_bytes, small + large);
    assert_eq!(cache.view(&keep).unwrap().function, 0);
    cache.release(keep).unwrap();
    cache.release(large_pin).unwrap();
    // All lifetime work cuts through planning and construction must retain the
    // pinned neighbor and apply either both planned evictions or neither.
    let mut planned_failures = 0;
    let mut constructed_failures = 0;
    for credits in before_work..after_work {
        let limited = CacheBudget {
            work_credits: credits,
            ..budget
        };
        let (mut cache, keep) = seed(&bytes, limited, &cancel);
        let failure = cache.pin(3, &cancel).unwrap_err();
        assert_eq!(failure.kind, CacheFailureKind::WorkExhausted);
        let usage = cache.usage();
        assert_eq!(
            (
                usage.active_pins,
                usage.pinned_bytes,
                usage.construction_bytes
            ),
            (1, small, 0)
        );
        match usage.evictions {
            0 => {
                assert_eq!(usage.resident_bytes, 3 * small);
                planned_failures += 1;
            }
            2 => {
                assert_eq!(usage.resident_bytes, small);
                constructed_failures += 1;
            }
            other => panic!("partial destructive plan: {other}"),
        }
        assert_eq!(cache.view(&keep).unwrap().function, 0);
        cache.release(keep).unwrap();
    }
    assert!(planned_failures > 0 && constructed_failures > 0);
    println!("PASS multi-victim byte-pressure: small={small} large={large}; work cuts={} pre-eviction={planned_failures} post-eviction={constructed_failures}", after_work - before_work);
}
fn allocation_failure_with_pinned_neighbor() {
    let cancel = Cancellation::default();
    let bytes = pressure_fixture();
    let (budget, small, large) = pressure_budget(&bytes, &cancel);
    for ordinal in 1..=3 {
        let before = LIVE.load(SeqCst);
        let (mut cache, keep) = seed(&bytes, budget, &cancel);
        let baseline = begin(ordinal, false);
        let failed = cache.pin(3, &cancel);
        let (calls, reallocations) = end();
        assert_eq!(
            failed.unwrap_err().kind,
            CacheFailureKind::AllocationFailure
        );
        assert_eq!(calls, ordinal);
        assert_eq!(reallocations, 0);
        assert_eq!(LIVE.load(SeqCst), baseline - 2 * small);
        let usage = cache.usage();
        assert_eq!(
            (usage.evictions, usage.resident_bytes, usage.pinned_bytes),
            (2, small, small)
        );
        assert_eq!((usage.construction_bytes, usage.active_pins), (0, 1));
        assert_eq!(cache.view(&keep).unwrap().function, 0);
        let retry = cache.pin(3, &cancel).unwrap();
        assert_eq!(cache.usage().resident_bytes, small + large);
        assert_eq!(cache.usage().evictions, 2);
        cache.release(retry).unwrap();
        cache.release(keep).unwrap();
        drop(cache);
        assert_eq!(LIVE.load(SeqCst), before);
    }
    println!("PASS three replacement allocation failures: pinned neighbor retained, complete payload cleanup, retries succeed, no reallocations");
}
fn fail_all_cleanup_routes() {
    let cancel = Cancellation::default();
    let cancelled = Cancellation::default();
    cancelled.cancel();
    let bytes = pressure_fixture();
    let (budget, _, _) = pressure_budget(&bytes, &cancel);
    let (mut cache, keep) = seed(&bytes, budget, &cancel);
    let mut wrong = make(&bytes, budget, &cancel);
    let baseline = begin(0, true);
    let rejected = wrong.release(keep).unwrap_err();
    let kind = rejected.failure.kind;
    let keep = rejected.into_pin();
    let visible = cache.view(&keep).unwrap().function;
    let hit = cache.pin(0, &cancel).unwrap();
    let cancelled_hit = cache.pin(0, &cancelled).unwrap_err().kind;
    cache.release(keep).unwrap();
    cache.release(hit).unwrap();
    let (calls, reallocations) = end();
    assert_eq!(kind, CacheFailureKind::InvalidPin);
    assert_eq!(visible, 0);
    assert_eq!(cancelled_hit, CacheFailureKind::Cancelled);
    assert_eq!((calls, reallocations), (0, 0));
    assert_eq!(LIVE.load(SeqCst), baseline);
    assert_eq!(
        (cache.usage().active_pins, cache.usage().pinned_bytes),
        (0, 0)
    );
    println!("PASS fail-all allocator: wrong-owner recovery, view, cache hit, canceled hit and release make zero allocation attempts");
}
fn absolute_import_identity_and_flat_targets() {
    let cancel = Cancellation::default();
    // The first br_table has two labels and the second has none. Its default
    // must not consume a flat target slot. Both occur after unreachable.
    let body = [
        0, 0, 2, 0x40, 0, 0x0e, 2, 0, 1, 1, 0, 0x0e, 0, 0, 0x0b, 0x0b,
    ];
    let bytes = module(&[&body], true);
    let mut cache = make(&bytes, CacheBudget::default(), &cancel);
    assert_eq!(cache.spans().function_count(), 2);
    assert_eq!(cache.spans().defined_function_count(), 1);
    let imported = cache.pin(0, &cancel).unwrap_err();
    assert_eq!(imported.kind, CacheFailureKind::InvalidFunction);
    let pin = cache.pin(1, &cancel).unwrap();
    let view = cache.view(&pin).unwrap();
    assert_eq!(view.function, 1);
    assert_eq!(view.branch_targets, &[0, 1]);
    let instructions = view.instructions;
    assert_eq!(
        instructions[3].operation,
        Operation::BrTable {
            first: 0,
            count: 2,
            default: 1
        }
    );
    assert_eq!(
        instructions[5].operation,
        Operation::BrTable {
            first: 2,
            count: 0,
            default: 0
        }
    );
    assert_eq!(
        instructions[1].operation,
        Operation::Block {
            kind: mixer_vm::experimental::cache::ControlKind::Block,
            result: None,
            end: 6,
            alternative: None,
        }
    );
    for instruction in instructions {
        assert_eq!(
            bytes[instruction.offset],
            body[instruction.offset - view.body_offset]
        );
    }
    cache.release(pin).unwrap();
    println!("PASS absolute imported-function indexing, multiple flat branch tables and absolute source positions");
}
fn concurrent_owner_and_cross_thread_move() {
    let bytes = std::sync::Arc::new(module(&[&[0, 0x0b]], false));
    let barrier = std::sync::Arc::new(std::sync::Barrier::new(8));
    let mut workers = Vec::new();
    for _ in 0..8 {
        let bytes = bytes.clone();
        let barrier = barrier.clone();
        workers.push(std::thread::spawn(move || {
            let cancel = Cancellation::default();
            let mut owners = Vec::new();
            barrier.wait();
            for _ in 0..32 {
                let cache = make(
                    &bytes,
                    CacheBudget {
                        max_entries: 1,
                        max_pins: 1,
                        ..CacheBudget::default()
                    },
                    &cancel,
                );
                owners.push(cache.identity().owner);
            }
            owners
        }));
    }
    let mut owners = Vec::new();
    for worker in workers {
        owners.extend(worker.join().unwrap());
    }
    owners.sort_unstable();
    assert_eq!(owners.len(), 256);
    assert!(owners[0] > 0);
    assert!(owners.windows(2).all(|pair| pair[0] < pair[1]));
    let cancel = Cancellation::default();
    let mut cache = make(&bytes, CacheBudget::default(), &cancel);
    let owner = cache.identity().owner;
    let pin = cache.pin(0, &cancel).unwrap();
    std::thread::spawn(move || {
        assert_eq!(cache.identity().owner, owner);
        assert_eq!(cache.view(&pin).unwrap().function, 0);
        cache.release(pin).unwrap();
        assert_eq!(cache.usage().active_pins, 0);
    })
    .join()
    .unwrap();
    println!(
        "PASS 256 concurrent owner identities across 8 threads, and cache/pin cross-thread move"
    );
}
fn main() {
    pressure_and_work_transaction();
    allocation_failure_with_pinned_neighbor();
    fail_all_cleanup_routes();
    absolute_import_identity_and_flat_targets();
    concurrent_owner_and_cross_thread_move();
    println!("PASS all independent public API review probes; decode/cache semantics only");
}
