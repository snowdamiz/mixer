//! Original fully validated same-ABI synthetic modules; no guest instantiation.
use super::cache::*;
use super::control::*;
use super::{validate_swift_reactor, SwiftValidationBudget, ValidatedSwiftReactor};
use crate::experimental::cache::{borrowed::CacheStep, decode};
use crate::experimental_swift_reactor::allocation_tests::{measure, measure_extended};
use crate::experimental_wasi::{
    accounted::AccountedWasi, WasiBudget, WasiFunction, WasiGrants, WasiUsage,
};
use crate::{Cancellation, Type, Value};
use std::cell::Cell;
use std::mem::size_of;
use std::time::{Duration, Instant};
#[derive(Clone, Copy)]
struct Hooks {
    checks: usize,
    cancel: Option<usize>,
    step: CacheStep,
    steps: [usize; 8],
    pause: Option<CacheStep>,
    capacity: Option<usize>,
    capacities: usize,
    cancel_pause: bool,
}
impl Default for Hooks {
    fn default() -> Self {
        Self {
            checks: 0,
            cancel: None,
            step: CacheStep::Constructor,
            steps: [0; 8],
            pause: None,
            capacity: None,
            capacities: 0,
            cancel_pause: false,
        }
    }
}
thread_local! {static HOOKS:Cell<Hooks>=Cell::new(Hooks::default());}
fn hooks(value: Hooks) {
    HOOKS.with(|h| h.set(value));
}
pub(super) fn step(step: CacheStep) {
    HOOKS.with(|h| {
        let mut x = h.get();
        x.step = step;
        h.set(x);
    });
}
pub(super) fn checkpoint(control: &RuntimeControl, _: Cursor) {
    let pause = HOOKS.with(|h| {
        let mut x = h.get();
        let ordinal = x.checks;
        x.checks += 1;
        x.steps[x.step as usize] += 1;
        if x.cancel == Some(ordinal) {
            control.cancellation().cancel();
        }
        let pause = x.pause == Some(x.step);
        if pause {
            if x.cancel_pause {
                control.cancellation().cancel();
            }
            x.pause = None;
        }
        h.set(x);
        pause
    });
    if pause {
        std::thread::sleep(Duration::from_millis(30));
    }
}
pub(super) fn capacity_observation(n: usize) -> usize {
    HOOKS.with(|h| {
        let mut x = h.get();
        let ordinal = x.capacities;
        x.capacities += 1;
        let fail = x.capacity == Some(ordinal);
        h.set(x);
        if fail {
            n.saturating_add(1)
        } else {
            n
        }
    })
}
fn uint(mut n: u32, out: &mut Vec<u8>) {
    loop {
        let byte = (n & 127) as u8;
        n >>= 7;
        out.push(byte | if n == 0 { 0 } else { 128 });
        if n == 0 {
            return;
        }
    }
}
fn text(s: &[u8], out: &mut Vec<u8>) {
    uint(s.len() as u32, out);
    out.extend_from_slice(s);
}
fn section(id: u8, payload: &[u8], out: &mut Vec<u8>) {
    out.push(id);
    uint(payload.len() as u32, out);
    out.extend_from_slice(payload);
}
fn ty(t: Type) -> u8 {
    match t {
        Type::I32 => 0x7f,
        Type::I64 => 0x7e,
        Type::F32 => 0x7d,
        Type::F64 => 0x7c,
    }
}
fn signature(params: &[Type], results: &[Type], out: &mut Vec<u8>) {
    out.push(0x60);
    uint(params.len() as u32, out);
    out.extend(params.iter().copied().map(ty));
    uint(results.len() as u32, out);
    out.extend(results.iter().copied().map(ty));
}
fn fixture(params: usize, helper: &[u8], definitions: usize) -> Vec<u8> {
    assert!(definitions >= 29);
    let mut module = b"\0asm\x01\0\0\0".to_vec();
    let mut types = vec![37];
    for import in WasiFunction::ALL {
        signature(import.parameters(), import.results(), &mut types);
    }
    signature(&[], &[], &mut types);
    signature(&[], &[Type::I32], &mut types);
    signature(&vec![Type::I32; params], &[], &mut types);
    section(1, &types, &mut module);
    let mut imports = vec![34];
    for (index, import) in WasiFunction::ALL.into_iter().enumerate() {
        text(b"wasi_snapshot_preview1", &mut imports);
        text(import.name(), &mut imports);
        imports.push(0);
        uint(index as u32, &mut imports);
    }
    section(2, &imports, &mut module);
    let mut functions = Vec::new();
    uint(definitions as u32, &mut functions);
    for index in 0..definitions {
        uint(
            if index == 0 {
                36
            } else if index == 28 {
                35
            } else {
                34
            },
            &mut functions,
        );
    }
    section(3, &functions, &mut module);
    let mut table = vec![1, 0x70, 1];
    uint(46713, &mut table);
    uint(46713, &mut table);
    section(4, &table, &mut module);
    let mut memory = vec![1, 0];
    uint(584, &mut memory);
    section(5, &memory, &mut module);
    section(6, &[1, 0x7f, 1, 0x41, 0, 0x0b], &mut module);
    let mut exports = vec![3];
    for (name, kind, index) in [
        (b"memory".as_slice(), 2, 0),
        (b"_initialize".as_slice(), 0, 35),
        (b"mixer_fieldlog_corpus_v1".as_slice(), 0, 62),
    ] {
        text(name, &mut exports);
        exports.push(kind);
        uint(index, &mut exports);
    }
    section(7, &exports, &mut module);
    let mut code = Vec::new();
    uint(definitions as u32, &mut code);
    for index in 0..definitions {
        let body: &[u8] = if index == 0 {
            helper
        } else if index == 28 {
            &[0, 0x41, 0, 0x0b]
        } else {
            &[0, 0x0b]
        };
        uint(body.len() as u32, &mut code);
        code.extend_from_slice(body);
    }
    section(10, &code, &mut module);
    module
}
fn body(locals: usize, code: &[u8]) -> Vec<u8> {
    let mut out = Vec::new();
    if locals == 0 {
        out.push(0);
    } else {
        out.push(1);
        uint(locals as u32, &mut out);
        out.push(0x7f);
    }
    out.extend_from_slice(code);
    out
}
fn proof(bytes: &[u8]) -> ValidatedSwiftReactor {
    validate_swift_reactor(
        bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap()
}
fn adopt(bytes: &[u8], budget: SwiftRunBudget) -> (RuntimeControl, AdoptedProof) {
    RuntimeControl::adopt(
        proof(bytes),
        budget,
        Instant::now(),
        Cancellation::default(),
    )
    .unwrap()
}
fn construct(
    control: &mut RuntimeControl,
    adopted: AdoptedProof,
    wasi: Option<&AccountedWasi>,
) -> Result<SwiftFunctionCache, SwiftRunFailure> {
    let failure = match SwiftFunctionCache::prepare(control, wasi, &adopted, cache_cursor()) {
        Ok(mut phase) => {
            let mut returned = Some(phase.construct(adopted));
            // End the original construction Result/error scope; preserve only
            // the final cache owner or a copied foundation-sized diagnostic.
            let result = {
                match returned.take().unwrap() {
                    Ok(cache) => Ok(cache),
                    Err(error) => {
                        assert!(error.rejected_adopted.is_none());
                        Err(error.failure)
                    }
                }
            };
            phase.complete(returned)?;
            return result;
        }
        Err(failure) => failure,
    };
    // Prepare only borrowed the caller's owner. It must still be explicitly
    // destroyed/refunded against its original ledger on rejected preparation.
    control.drop_proof_with_wasi(adopted, wasi.map(AccountedWasi::usage))?;
    Err(failure)
}
fn new(bytes: &[u8], budget: SwiftRunBudget) -> (RuntimeControl, SwiftFunctionCache) {
    let (mut c, p) = adopt(bytes, budget);
    let cache = construct(&mut c, p, None).unwrap();
    (c, cache)
}
fn pin(
    cache: &mut SwiftFunctionCache,
    control: &mut RuntimeControl,
    function: u32,
    wasi: Option<&AccountedWasi>,
) -> Result<SwiftFunctionPin, SwiftRunFailure> {
    let mut phase = cache.prepare_operation(control, wasi, cache_cursor())?;
    let mut returned = Some(phase.pin(cache, function));
    let result = returned.take().unwrap();
    phase.complete(returned)?;
    result
}
fn cleanup(
    cache: SwiftFunctionCache,
    control: &mut RuntimeControl,
    wasi: Option<&AccountedWasi>,
) -> Option<SwiftRunFailure> {
    let mut owned = Some(cache);
    let tail = { SwiftFunctionCache::cleanup(&mut owned, control, wasi).unwrap() };
    let mut result = None;
    tail.complete(owned, &mut result);
    result
}
fn finish(cache: SwiftFunctionCache, mut control: RuntimeControl) {
    cleanup(cache, &mut control, None);
    let final_usage = control.finish_owned_cleanup(None);
    assert_eq!(final_usage.reservations.combined.current, 0);
    assert_eq!(final_usage.reservations.live_tickets, 0);
    assert_eq!(final_usage.live.active_pins.current, 0);
    assert_eq!(final_usage.live.cache_entries.current, 0);
}
fn wasi(control: &mut RuntimeControl) -> AccountedWasi {
    let mut p = AccountedWasi::prepare(control, cache_cursor()).unwrap();
    let w = p
        .construct(
            WasiGrants::default(),
            WasiBudget {
                one_transfer_bytes: 64,
                log_bytes: 64,
                ..WasiBudget::default()
            },
            Instant::now(),
            cache_cursor(),
        )
        .unwrap();
    p.complete().unwrap();
    w
}
#[test]
fn same_abi_descriptors_and_authority() {
    let bytes = fixture(0, &[0, 0x0b], 100);
    let p = proof(&bytes);
    let source = p.source().as_ptr();
    let metadata = p.usage().metadata_reserved;
    let (mut c, a) = RuntimeControl::adopt(
        p,
        SwiftRunBudget::default(),
        Instant::now(),
        Cancellation::default(),
    )
    .unwrap();
    let (cache, alloc) = measure(|| construct(&mut c, a, None).unwrap());
    assert_eq!(cache.proof().source().as_ptr(), source);
    assert_eq!(cache.proof().source(), bytes);
    assert_eq!(cache.proof().execution_imports(), &WasiFunction::ALL);
    assert_eq!(cache.proof().execution_table().unwrap().host_maximum, 46713);
    assert_eq!(cache.proof().execution_memory().unwrap().host_maximum, 768);
    assert!(cache.proof().execution_function(33).is_none());
    assert!(cache.proof().execution_function(134).is_none());
    let u = c.usage(None);
    assert_eq!(u.reservations.retained_source.current, bytes.len());
    assert_eq!(u.reservations.retained_metadata.current, metadata);
    assert_eq!(alloc.allocations, 3);
    assert_eq!(alloc.reallocations, 0);
    finish(cache, c);
}
#[test]
fn decoder_opcode_and_count_build_parity() {
    let mut code = vec![
        0, 1, 0, 0x0c, 0, 0, 0x0d, 0, 0, 0x0e, 3, 0, 0, 0, 0, 0, 0x0f, 0, 0x10, 35, 0, 0x1a, 0,
        0x1b,
    ];
    for opcode in 0x20..=0x24 {
        code.extend([0, opcode, 0]);
    }
    for opcode in 0x28..=0x3e {
        code.extend([0, opcode, 0, 0x80, 1]);
    }
    code.extend([0, 0x3f, 0, 0, 0x40, 0, 0, 0x41, 0x7f, 0, 0x42, 0x80, 0x7f]);
    for opcode in 0x45..=0xc4 {
        if matches!(opcode,0x45..=0x5a|0x67..=0x8a|0xa7|0xac|0xad|0xc0..=0xc4|0x5b..=0x66|0x8b..=0xa6|0xa8..=0xab|0xae..=0xbf)
        {
            code.extend([0, opcode]);
        }
    }
    code.extend([0, 0x43, 1, 0, 0xc0, 0x7f, 0, 0x44, 1, 2, 3, 4, 5, 6, 7, 8]);
    for sub in 0..=7 {
        code.extend([0, 0xfc, sub]);
    }
    code.extend([
        0, 0x11, 34, 0, 0, 0xfc, 10, 0, 0, 0, 0xfc, 11, 0, 0, 2, 0x40, 3, 0x40, 0, 0x0d, 1, 0x0b,
        0x0b, 0, 4, 0x40, 1, 5, 1, 0x0b, 0x0b,
    ]);
    let helper = body(1, &code);
    let bytes = fixture(0, &helper, 100);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let p = pin(&mut cache, &mut c, 34, None).unwrap();
    let view = cache.view(&p, &mut c, None).unwrap();
    assert_eq!(view.locals, &[Type::I32]);
    assert_eq!(view.branch_targets, &[0, 0, 0]);
    assert_eq!(
        view.instructions.last().unwrap().operation,
        crate::experimental::cache::Operation::End
    );
    let source_body = cache.proof().execution_function(34).unwrap();
    assert_eq!(view.body_offset, source_body.body_offset);
    assert!(view
        .instructions
        .iter()
        .all(|i| i.offset >= source_body.body_offset
            && i.offset < source_body.body_offset + helper.len()));
    println!(
        "opcode parity instructions={} targets={} declared_locals={}",
        view.instructions.len(),
        view.branch_targets.len(),
        view.locals.len()
    );
    cache
        .release(p, &mut c, None)
        .map_err(|e| e.failure)
        .unwrap();
    finish(cache, c);
    // Internal invariant injection, not a fabricated Swift validation proof.
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let failure = inspection::count_build_mismatch(&mut cache, &mut c);
    assert_eq!(failure.kind, SwiftRunFailureKind::DecoderMismatch);
    assert_eq!(failure.code, "decode_count_mismatch");
    assert_eq!(c.usage(None).live.cache_entries.current, 0);
    finish(cache, c);
}
#[test]
fn parameters_and_function_inclusive_depth() {
    for (params, locals) in [(128, 128), (1, 255), (0, 256)] {
        let bytes = fixture(params, &body(locals, &[0x0b]), 100);
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
        let p = pin(&mut cache, &mut c, 34, None).unwrap();
        assert_eq!(cache.view(&p, &mut c, None).unwrap().locals.len(), locals);
        finish(cache, c);
    }
    let bytes = fixture(128, &body(129, &[0x0b]), 100);
    assert!(validate_swift_reactor(
        &bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default()
    )
    .is_err());
    for depth in [379, 512] {
        let mut code = vec![];
        for _ in 1..depth {
            code.extend([2, 0x40]);
        }
        code.extend(std::iter::repeat_n(0x0b, depth));
        let bytes = fixture(0, &body(0, &code), 100);
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
        let p = pin(&mut cache, &mut c, 34, None).unwrap();
        assert_eq!(
            cache.view(&p, &mut c, None).unwrap().instructions.len(),
            2 * depth - 1
        );
        finish(cache, c);
    }
    let mut code = vec![];
    for _ in 0..512 {
        code.extend([2, 0x40]);
    }
    code.extend(std::iter::repeat_n(0x0b, 513));
    let bytes = fixture(0, &body(0, &code), 100);
    assert!(validate_swift_reactor(
        &bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default()
    )
    .is_err());
}
#[test]
fn permanent_patch_arena_exact_requests() {
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
    let (cache, s) = measure(|| construct(&mut c, a, None).unwrap());
    assert_eq!(s.allocations, 3);
    println!("permanent fixed requested allocations {:?}", s);
    let expected = 64 * size_of::<super::cache::SwiftSlot>()
        + 64 * size_of::<crate::experimental::cache::PinRecord>()
        + 512 * size_of::<decode::Patch>();
    assert_eq!(s.allocated_bytes, expected);
    assert_eq!(
        c.usage(None).reservations.cache.current,
        cache_header_bytes().unwrap() + expected
    );
    inspection::print_layouts();
    finish(cache, c);
}
#[test]
fn entry_and_combined_admission_precedes_allocation() {
    let bytes = fixture(0, &body(1, &[0, 0x0e, 1, 0, 0, 0x0b]), 100);
    let (mut c, mut cache) = new(
        &bytes,
        SwiftRunBudget {
            cache_entry_bytes: 0,
            ..SwiftRunBudget::default()
        },
    );
    let (result, s) = measure(|| pin(&mut cache, &mut c, 34, None));
    let f = result.unwrap_err();
    println!("entry admission failure {f:?}");
    assert_eq!(f.resource, Some(SwiftRunResource::CacheEntryBytes));
    assert_eq!(s.attempts, 0);
    assert_eq!(cache.usage().resident_bytes, 0);
    assert_eq!(c.usage(None).live.active_pins.current, 0);
    finish(cache, c);
    let bytes = fixture(0, &body(1, &[vec![1; 3000], vec![0x0b]].concat()), 100);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let p = pin(&mut cache, &mut c, 34, None).unwrap();
    let _entry = cache.usage().resident_bytes;
    cache
        .release(p, &mut c, None)
        .map_err(|e| e.failure)
        .unwrap();
    let peak = c.usage(None).reservations.combined.peak;
    finish(cache, c);
    let (mut c, a) = adopt(
        &bytes,
        SwiftRunBudget {
            combined_bytes: peak - 1,
            ..SwiftRunBudget::default()
        },
    );
    let cache = construct(&mut c, a, None).unwrap();
    let mut cache = cache;
    let (result, s) = measure(|| pin(&mut cache, &mut c, 34, None));
    assert!(result.is_err());
    assert_eq!(s.attempts, 0);
    finish(cache, c);
}
#[test]
fn zero_limits_and_exact_narrowing() {
    let bytes = fixture(0, &[0, 0x0b], 100);
    for (entries, pins) in [(0, 64), (64, 0), (0, 0)] {
        let (mut c, mut cache) = new(
            &bytes,
            SwiftRunBudget {
                cache_entries: entries,
                active_pins: pins,
                ..SwiftRunBudget::default()
            },
        );
        assert!(pin(&mut cache, &mut c, 34, None).is_err());
        assert_eq!(cache.usage().active_pins, 0);
        finish(cache, c);
    }
    for budget in [
        SwiftRunBudget {
            cache_bytes: 0,
            ..SwiftRunBudget::default()
        },
        SwiftRunBudget {
            cache_work: 0,
            ..SwiftRunBudget::default()
        },
    ] {
        let (mut c, a) = adopt(&bytes, budget);
        assert!(construct(&mut c, a, None).is_err());
        assert_eq!(c.usage(None).reservations.cache.current, 0);
        assert_eq!(
            c.finish_owned_cleanup(None).reservations.combined.current,
            0
        );
    }
}
#[test]
fn pins_hits_lru_and_eviction() {
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let mut pins = Vec::new();
    for _ in 0..64 {
        pins.push(pin(&mut cache, &mut c, 34, None).unwrap());
    }
    assert_eq!(cache.usage().active_pins, 64);
    assert_eq!(cache.usage().hits, 63);
    assert_eq!(cache.usage().pinned_bytes, cache.usage().resident_bytes);
    let (_, s) = measure(|| {
        for p in pins {
            cache
                .release(p, &mut c, None)
                .map_err(|e| e.failure)
                .unwrap();
        }
    });
    assert_eq!(s.attempts, 0);
    assert_eq!(cache.usage().pinned_bytes, 0);
    finish(cache, c);
    let (mut c, mut cache) = new(
        &bytes,
        SwiftRunBudget {
            cache_entries: 2,
            ..SwiftRunBudget::default()
        },
    );
    for f in [34, 35, 34, 36] {
        let p = pin(&mut cache, &mut c, f, None).unwrap();
        cache
            .release(p, &mut c, None)
            .map_err(|e| e.failure)
            .unwrap();
    }
    assert_eq!(cache.usage().evictions, 1);
    assert_eq!(cache.usage().hits, 1);
    finish(cache, c);
    let (mut c, mut cache) = new(
        &bytes,
        SwiftRunBudget {
            cache_entries: 1,
            ..SwiftRunBudget::default()
        },
    );
    let _p = pin(&mut cache, &mut c, 34, None).unwrap();
    assert_eq!(
        pin(&mut cache, &mut c, 35, None).unwrap_err().code,
        "all_entries_pinned"
    );
    finish(cache, c);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    for function in 34..98 {
        let p = pin(&mut cache, &mut c, function, None).unwrap();
        cache
            .release(p, &mut c, None)
            .map_err(|e| e.failure)
            .unwrap();
    }
    assert_eq!(c.usage(None).live.cache_entries.current, 64);
    assert_eq!(c.usage(None).reservations.live_tickets, 73);
    assert!(c.usage(None).reservations.peak_tickets <= MAX_RESERVATION_TICKETS);
    let p = pin(&mut cache, &mut c, 98, None).unwrap();
    cache
        .release(p, &mut c, None)
        .map_err(|e| e.failure)
        .unwrap();
    assert_eq!(c.usage(None).reservations.live_tickets, 73);
    assert_eq!(cache.usage().evictions, 1);
    finish(cache, c);
    // Actual release is admission/work/cancellation independent, including the
    // last recursive pin's subset-byte transition.
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let p = pin(&mut cache, &mut c, 34, None).unwrap();
    let q = pin(&mut cache, &mut c, 34, None).unwrap();
    let work = c.usage(None).cache_work;
    c.cancellation().cancel();
    let (_, stats) = measure(|| {
        cache
            .release(p, &mut c, None)
            .map_err(|e| e.failure)
            .unwrap();
        cache
            .release(q, &mut c, None)
            .map_err(|e| e.failure)
            .unwrap();
    });
    assert_eq!(stats.attempts, 0);
    assert_eq!(c.usage(None).cache_work, work);
    assert_eq!(cache.usage().pinned_bytes, 0);
    finish(cache, c);
}
#[test]
fn foreign_stale_nonce_and_control_ownership() {
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let p = pin(&mut cache, &mut c, 34, None).unwrap();
    let stale = inspection::stale(&p);
    cache
        .release(p, &mut c, None)
        .map_err(|e| e.failure)
        .unwrap();
    assert_eq!(
        cache.view(&stale, &mut c, None).err().unwrap().code,
        "stale_pin"
    );
    finish(cache, c);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    inspection::set_nonce(&mut cache, u64::MAX);
    assert_eq!(
        pin(&mut cache, &mut c, 34, None).unwrap_err().code,
        "pin_nonce_exhausted"
    );
    finish(cache, c);
    let (mut c, cache) = new(&bytes, SwiftRunBudget::default());
    let (mut foreign, p) = adopt(&bytes, SwiftRunBudget::default());
    let before = c.usage(None).reservations;
    let mut owned = Some(cache);
    let (result, s) = measure(|| SwiftFunctionCache::cleanup(&mut owned, &mut foreign, None));
    assert!(result.is_err());
    drop(result);
    assert!(owned.is_some());
    assert_eq!(s.attempts, 0);
    assert_eq!(c.usage(None).reservations, before);
    let tail = SwiftFunctionCache::cleanup(&mut owned, &mut c, None).unwrap();
    let mut outcome = None;
    tail.complete(owned, &mut outcome);
    assert_eq!(
        c.finish_owned_cleanup(None).reservations.combined.current,
        0
    );
    foreign.drop_proof(p).unwrap();
    assert_eq!(
        foreign
            .finish_owned_cleanup(None)
            .reservations
            .combined
            .current,
        0
    );
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let p = pin(&mut cache, &mut c, 34, None).unwrap();
    let (mut other, mut other_cache) = new(&bytes, SwiftRunBudget::default());
    let before = other.usage(None);
    let (rejected, stats) = measure(|| other_cache.release(p, &mut other, None).err().unwrap());
    assert_eq!(rejected.failure.code, "wrong_cache_owner");
    assert_eq!(stats.attempts, 0);
    assert_eq!(other.usage(None).cache_work, before.cache_work);
    assert_eq!(other.usage(None).live, before.live);
    cache
        .release(rejected.into_pin(), &mut c, None)
        .map_err(|e| e.failure)
        .unwrap();
    assert_eq!(cache.usage().active_pins, 0);
    finish(cache, c);
    finish(other_cache, other);
}
#[test]
fn construction_and_operation_phase_boundaries() {
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
    let previous = c.usage(None).reservations.construction.current;
    let extra = previous + 123;
    c.enlarge_construction(extra, cache_cursor()).unwrap();
    let mut phase = SwiftFunctionCache::prepare(&mut c, None, &a, cache_cursor()).unwrap();
    let cache = phase.construct(a).map_err(|e| e.failure).unwrap();
    phase.complete(()).unwrap();
    assert_eq!(c.usage(None).reservations.construction.current, extra);
    c.end_construction_phase((), previous).unwrap();
    let mut cache = cache;
    let mut op = cache
        .prepare_operation(&mut c, None, cache_cursor())
        .unwrap();
    let p = op.pin(&mut cache, 34).unwrap();
    op.complete(()).unwrap();
    assert_eq!(c.usage(None).reservations.construction.current, previous);
    cache
        .release(p, &mut c, None)
        .map_err(|e| e.failure)
        .unwrap();
    finish(cache, c);
    let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
    let phase = SwiftFunctionCache::prepare(&mut c, None, &a, cache_cursor()).unwrap();
    drop(phase);
    assert!(c.usage(None).reservations.construction.current > previous);
    c.drop_proof(a).unwrap();
    assert!(c.finish_owned_cleanup(None).reservations.combined.current > 0);
    let (mut c, cache) = new(&bytes, SwiftRunBudget::default());
    let floor = c.usage(None).reservations.construction.current;
    let operation = cache
        .prepare_operation(&mut c, None, cache_cursor())
        .unwrap();
    drop(operation);
    assert!(c.usage(None).reservations.construction.current > floor);
    cleanup(cache, &mut c, None);
    assert!(c.finish_owned_cleanup(None).reservations.combined.current > 0);
    let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
    let (mut foreign, b) = adopt(&bytes, SwiftRunBudget::default());
    let mut phase = SwiftFunctionCache::prepare(&mut c, None, &a, cache_cursor()).unwrap();
    let (a, b) = {
        let (error, s) = measure(|| phase.construct(b).err().unwrap());
        assert_eq!(s.attempts, 0);
        let b = error.rejected_adopted.unwrap();
        let again = phase.construct(a).err().unwrap();
        let a = again.rejected_adopted.unwrap();
        (a, b)
    };
    phase.complete(()).unwrap();
    c.drop_proof(a).unwrap();
    foreign.drop_proof(b).unwrap();
    assert_eq!(
        c.finish_owned_cleanup(None).reservations.combined.current,
        0
    );
    assert_eq!(
        foreign
            .finish_owned_cleanup(None)
            .reservations
            .combined
            .current,
        0
    );
}
#[test]
fn every_constructor_allocation_ordinal() {
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
    let (cache, s) = measure(|| construct(&mut c, a, None).unwrap());
    let n = s.attempts;
    assert_eq!(n, 3);
    finish(cache, c);
    let (mut base_control, base_proof) = adopt(&bytes, SwiftRunBudget::default());
    let (_, base_drop) = measure(|| base_control.drop_proof(base_proof).unwrap());
    let _ = base_control.finish_owned_cleanup(None);
    for ordinal in 0..n {
        let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
        let (result, s) = measure_extended(Some(ordinal), || construct(&mut c, a, None));
        assert!(result.is_err());
        assert_eq!(s.injected_failures, 1);
        assert_eq!(
            s.freed_bytes - base_drop.freed_bytes,
            s.allocated_bytes - s.last_size
        );
        assert_eq!(c.usage(None).reservations.cache.current, 0);
        assert_eq!(
            c.finish_owned_cleanup(None).reservations.combined.current,
            0
        );
        println!("constructor allocation ordinal {} observed", ordinal);
    }
    for ordinal in 0..3 {
        hooks(Hooks::default());
        let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
        hooks(Hooks {
            capacity: Some(ordinal),
            ..Hooks::default()
        });
        let f = construct(&mut c, a, None).err().unwrap();
        hooks(Hooks::default());
        assert_eq!(f.resource, Some(SwiftRunResource::ExactCapacity));
        assert_eq!(f.observed_capacity, Some(f.attempted as usize + 1));
        assert_eq!(c.usage(None).reservations.cache.current, 0);
        assert_eq!(
            c.finish_owned_cleanup(None).reservations.combined.current,
            0
        );
    }
}
#[test]
fn every_miss_allocation_ordinal_and_capacity_fault() {
    for helper in [
        body(0, &[0x0b]),
        body(1, &[0x0b]),
        body(1, &[0, 0x0e, 1, 0, 0, 0x0b]),
    ] {
        let bytes = fixture(0, &helper, 100);
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
        let (p, s) = measure(|| pin(&mut cache, &mut c, 34, None).unwrap());
        let n = s.attempts;
        assert!((1..=3).contains(&n));
        cache
            .release(p, &mut c, None)
            .map_err(|e| e.failure)
            .unwrap();
        finish(cache, c);
        for ordinal in 0..n {
            let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
            let (result, s) = measure_extended(Some(ordinal), || pin(&mut cache, &mut c, 34, None));
            assert!(result.is_err());
            assert_eq!(s.injected_failures, 1);
            assert_eq!(c.usage(None).live.cache_entries.current, 0);
            assert_eq!(c.usage(None).live.active_pins.current, 0);
            finish(cache, c);
            println!("miss shape {} allocation {} observed", n, ordinal);
        }
    }
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    hooks(Hooks {
        capacity: Some(0),
        ..Hooks::default()
    });
    let f = pin(&mut cache, &mut c, 34, None).unwrap_err();
    hooks(Hooks::default());
    assert_eq!(f.resource, Some(SwiftRunResource::ExactCapacity));
    assert_eq!(f.observed_capacity, Some(f.attempted as usize + 1));
    finish(cache, c);
    for ordinal in 0..3 {
        hooks(Hooks::default());
        let bytes = fixture(0, &body(1, &[0, 0x0e, 1, 0, 0, 0x0b]), 100);
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
        hooks(Hooks {
            capacity: Some(ordinal),
            ..Hooks::default()
        });
        let f = pin(&mut cache, &mut c, 34, None).unwrap_err();
        hooks(Hooks::default());
        assert_eq!(f.resource, Some(SwiftRunResource::ExactCapacity));
        assert_eq!(c.usage(None).live.cache_entries.current, 0);
        finish(cache, c);
    }
    for ordinal in 0..3 {
        hooks(Hooks::default());
        let bytes = fixture(0, &body(1, &[0, 0x0e, 1, 0, 0, 0x0b]), 100);
        let (mut c, mut cache) = new(
            &bytes,
            SwiftRunBudget {
                cache_entries: 1,
                ..SwiftRunBudget::default()
            },
        );
        let p = pin(&mut cache, &mut c, 35, None).unwrap();
        cache
            .release(p, &mut c, None)
            .map_err(|e| e.failure)
            .unwrap();
        let old = cache.usage().resident_bytes;
        let (result, stats) = measure_extended(Some(ordinal), || pin(&mut cache, &mut c, 34, None));
        assert!(result.is_err());
        assert_eq!(stats.injected_failures, 1);
        assert_eq!(cache.usage().evictions, 1);
        assert_eq!(
            stats.freed_bytes,
            stats.allocated_bytes - stats.last_size + old
        );
        assert_eq!(c.usage(None).live.cache_entries.current, 0);
        finish(cache, c);
    }
}
#[test]
fn every_work_prefix_and_cancellation_boundary() {
    let bytes = fixture(0, &body(1, &[0, 0x0e, 2, 0, 0, 0, 0x0b]), 29);
    hooks(Hooks::default());
    let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
    let mut cache = construct(&mut c, a, None).unwrap();
    let ctor_work = c.usage(None).cache_work;
    let ctor_checks = HOOKS.with(|h| h.get().checks);
    hooks(Hooks::default());
    let p = pin(&mut cache, &mut c, 34, None).unwrap();
    let final_work = c.usage(None).cache_work;
    let miss_checks = HOOKS.with(|h| h.get().checks);
    cache
        .release(p, &mut c, None)
        .map_err(|e| e.failure)
        .unwrap();
    finish(cache, c);
    for credits in 0..final_work {
        hooks(Hooks::default());
        let (mut c, a) = adopt(
            &bytes,
            SwiftRunBudget {
                cache_work: credits,
                ..SwiftRunBudget::default()
            },
        );
        match construct(&mut c, a, None) {
            Ok(mut cache) => {
                assert!(pin(&mut cache, &mut c, 34, None).is_err());
                assert!(c.usage(None).cache_work <= credits);
                finish(cache, c);
            }
            Err(_) => {
                assert!(credits < ctor_work);
                assert!(c.usage(None).cache_work <= credits);
                assert_eq!(
                    c.finish_owned_cleanup(None).reservations.combined.current,
                    0
                );
            }
        }
    }
    for ordinal in 0..ctor_checks {
        hooks(Hooks {
            cancel: Some(ordinal),
            ..Hooks::default()
        });
        let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
        let result = construct(&mut c, a, None);
        hooks(Hooks::default());
        assert!(
            result.is_err(),
            "constructor cancellation ordinal {ordinal}"
        );
        assert_eq!(
            c.finish_owned_cleanup(None).reservations.combined.current,
            0
        );
    }
    for ordinal in 0..miss_checks {
        hooks(Hooks::default());
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
        hooks(Hooks {
            cancel: Some(ordinal),
            ..Hooks::default()
        });
        assert!(
            pin(&mut cache, &mut c, 34, None).is_err(),
            "miss cancellation ordinal {ordinal}"
        );
        hooks(Hooks::default());
        finish(cache, c);
    }
    println!(
        "enumerated constructor_work={} all_work_prefixes={} constructor_checks={} miss_checks={}",
        ctor_work, final_work, ctor_checks, miss_checks
    );
    for target in [34, 35] {
        enumerate_seeded(&bytes, target);
    }
}
fn enumerate_seeded(bytes: &[u8], target: u32) {
    hooks(Hooks::default());
    let (mut c, mut cache) = new(
        bytes,
        SwiftRunBudget {
            cache_entries: 1,
            ..SwiftRunBudget::default()
        },
    );
    let p = pin(&mut cache, &mut c, 34, None).unwrap();
    cache
        .release(p, &mut c, None)
        .map_err(|e| e.failure)
        .unwrap();
    let base = c.usage(None).cache_work;
    hooks(Hooks::default());
    let p = pin(&mut cache, &mut c, target, None).unwrap();
    let credits = c.usage(None).cache_work - base;
    let checks = HOOKS.with(|h| h.get().checks);
    hooks(Hooks::default());
    cache
        .release(p, &mut c, None)
        .map_err(|e| e.failure)
        .unwrap();
    finish(cache, c);
    for prefix in 0..credits {
        hooks(Hooks::default());
        let (mut c, mut cache) = new(
            bytes,
            SwiftRunBudget {
                cache_entries: 1,
                cache_work: base + prefix,
                ..SwiftRunBudget::default()
            },
        );
        let p = pin(&mut cache, &mut c, 34, None).unwrap();
        cache
            .release(p, &mut c, None)
            .map_err(|e| e.failure)
            .unwrap();
        assert!(pin(&mut cache, &mut c, target, None).is_err());
        assert!(c.usage(None).cache_work <= base + prefix);
        assert_eq!(c.usage(None).live.active_pins.current, 0);
        assert_eq!(
            c.usage(None).live.cache_entries.current,
            1 - cache.usage().evictions as usize
        );
        finish(cache, c);
    }
    for ordinal in 0..checks {
        hooks(Hooks::default());
        let (mut c, mut cache) = new(
            bytes,
            SwiftRunBudget {
                cache_entries: 1,
                ..SwiftRunBudget::default()
            },
        );
        let p = pin(&mut cache, &mut c, 34, None).unwrap();
        cache
            .release(p, &mut c, None)
            .map_err(|e| e.failure)
            .unwrap();
        hooks(Hooks {
            cancel: Some(ordinal),
            ..Hooks::default()
        });
        assert!(pin(&mut cache, &mut c, target, None).is_err());
        hooks(Hooks::default());
        assert_eq!(c.usage(None).live.active_pins.current, 0);
        assert_eq!(
            c.usage(None).live.cache_entries.current,
            1 - cache.usage().evictions as usize
        );
        finish(cache, c);
    }
    println!("seeded target={target} credits={credits} checks={checks} all enumerated");
}

#[test]
fn deadline_inside_decode_and_reset() {
    let bytes = fixture(0, &body(1, &[0, 0x0e, 1, 0, 0, 0x0b]), 100);
    for step in [
        CacheStep::ScanReset,
        CacheStep::Scan,
        CacheStep::BuildReset,
        CacheStep::Build,
        CacheStep::Publication,
    ] {
        hooks(Hooks::default());
        let (mut c, mut cache) = new(
            &bytes,
            SwiftRunBudget {
                deadline_ms: 20,
                ..SwiftRunBudget::default()
            },
        );
        hooks(Hooks {
            pause: Some(step),
            ..Hooks::default()
        });
        let f = pin(&mut cache, &mut c, 34, None).unwrap_err();
        let counts = HOOKS.with(|h| h.get().steps);
        hooks(Hooks::default());
        assert_eq!(f.kind, SwiftRunFailureKind::Deadline);
        assert_eq!(f.deadline_origin, SwiftDeadlineOrigin::Run);
        assert!(f.at_failure.deadline_overshoot_micros > 0);
        assert!(counts[step as usize] > 0);
        println!(
            "deadline step={step:?} cursor={:?} overshoot={}",
            f.offset, f.at_failure.deadline_overshoot_micros
        );
        finish(cache, c);
    }
    // The actual carried WASI deadline wins, and cancellation still precedes an
    // expired clock at the exact selected reset/decode boundary.
    for cancel in [false, true] {
        hooks(Hooks::default());
        let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
        let mut phase = AccountedWasi::prepare(&mut c, cache_cursor()).unwrap();
        let w = phase
            .construct(
                WasiGrants::default(),
                WasiBudget {
                    one_transfer_bytes: 64,
                    log_bytes: 64,
                    deadline_ms: 20,
                    ..WasiBudget::default()
                },
                Instant::now(),
                cache_cursor(),
            )
            .unwrap();
        phase.complete().unwrap();
        let mut cache = construct(&mut c, a, Some(&w)).unwrap();
        hooks(Hooks {
            pause: Some(CacheStep::BuildReset),
            cancel_pause: cancel,
            ..Hooks::default()
        });
        let f = pin(&mut cache, &mut c, 34, Some(&w)).unwrap_err();
        hooks(Hooks::default());
        assert_eq!(f.deadline_origin, SwiftDeadlineOrigin::Wasi);
        assert_eq!(
            f.kind,
            if cancel {
                SwiftRunFailureKind::Cancelled
            } else {
                SwiftRunFailureKind::Deadline
            }
        );
        assert_eq!(f.at_failure.wasi, Some(w.usage()));
        assert!(f.at_failure.deadline_overshoot_micros > 0);
        cleanup(cache, &mut c, Some(&w));
        w.cleanup(&mut c).unwrap();
        assert_eq!(
            c.finish_owned_cleanup(None).reservations.combined.current,
            0
        );
    }
}
#[test]
fn first_cause_retains_actual_wasi_usage() {
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, a) = adopt(
        &bytes,
        SwiftRunBudget {
            cache_work: 1,
            ..SwiftRunBudget::default()
        },
    );
    let mut w = wasi(&mut c);
    let earlier = w.usage();
    w.dispatch(
        &mut c,
        WasiFunction::FdClose,
        &[Value::I32(42)],
        &mut [],
        cache_cursor(),
    )
    .unwrap();
    let actual = w.usage();
    assert_ne!(earlier, actual);
    let f = construct(&mut c, a, Some(&w)).err().unwrap();
    println!("first cache failure actual WASI {f:?}");
    assert_eq!(f.at_failure.wasi, Some(actual));
    let f2 = c
        .check_with_wasi(cache_cursor(), Some(w.usage()))
        .unwrap_err();
    assert_eq!(f, f2);
    w.cleanup(&mut c).unwrap();
    assert_eq!(
        c.finish_owned_cleanup(None).reservations.combined.current,
        0
    );
    let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
    let (mut other, p) = adopt(&bytes, SwiftRunBudget::default());
    let w = wasi(&mut other);
    let before = c.usage(None).reservations;
    let f = SwiftFunctionCache::prepare(&mut c, Some(&w), &a, cache_cursor())
        .err()
        .unwrap();
    assert_eq!(f.at_failure.wasi, None);
    assert_eq!(c.usage(None).reservations, before);
    c.drop_proof(a).unwrap();
    w.cleanup(&mut other).unwrap();
    other.drop_proof(p).unwrap();
    assert_eq!(
        c.finish_owned_cleanup(None).reservations.combined.current,
        0
    );
    assert_eq!(
        other
            .finish_owned_cleanup(None)
            .reservations
            .combined
            .current,
        0
    );
    // Exercise every observed cache control path with a real context whose
    // counters advanced through an accepted errno dispatch.
    for case in ["entry", "category", "capacity"] {
        hooks(Hooks::default());
        let budget = match case {
            "entry" => SwiftRunBudget {
                cache_entry_bytes: 0,
                ..SwiftRunBudget::default()
            },
            "category" => SwiftRunBudget {
                cache_bytes: 0,
                ..SwiftRunBudget::default()
            },
            _ => SwiftRunBudget::default(),
        };
        let (mut c, a) = adopt(&bytes, budget);
        let mut w = wasi(&mut c);
        w.dispatch(
            &mut c,
            WasiFunction::FdClose,
            &[Value::I32(80)],
            &mut [],
            cache_cursor(),
        )
        .unwrap();
        let actual = w.usage();
        let failure = if case == "category" {
            construct(&mut c, a, Some(&w)).err().unwrap()
        } else {
            let mut cache = construct(&mut c, a, Some(&w)).unwrap();
            if case == "capacity" {
                hooks(Hooks {
                    capacity: Some(0),
                    ..Hooks::default()
                });
            }
            let failure = pin(&mut cache, &mut c, 34, Some(&w)).unwrap_err();
            hooks(Hooks::default());
            cleanup(cache, &mut c, Some(&w));
            failure
        };
        assert_eq!(failure.at_failure.wasi, Some(actual));
        println!("observed WASI cache case={case} failure={failure:?}");
        w.cleanup(&mut c).unwrap();
        assert_eq!(
            c.finish_owned_cleanup(None).reservations.combined.current,
            0
        );
    }
    let large = fixture(0, &body(1, &[vec![1; 3000], vec![0x0b]].concat()), 100);
    let (mut c, a) = adopt(&large, SwiftRunBudget::default());
    let w = wasi(&mut c);
    let mut cache = construct(&mut c, a, Some(&w)).unwrap();
    let p = pin(&mut cache, &mut c, 34, Some(&w)).unwrap();
    cache
        .release(p, &mut c, Some(&w))
        .map_err(|e| e.failure)
        .unwrap();
    let peak = c.usage(Some(w.usage())).reservations.combined.peak;
    cleanup(cache, &mut c, Some(&w));
    w.cleanup(&mut c).unwrap();
    let _ = c.finish_owned_cleanup(None);
    let (mut c, a) = adopt(
        &large,
        SwiftRunBudget {
            combined_bytes: peak - 1,
            ..SwiftRunBudget::default()
        },
    );
    let mut w = wasi(&mut c);
    w.dispatch(
        &mut c,
        WasiFunction::FdClose,
        &[Value::I32(81)],
        &mut [],
        cache_cursor(),
    )
    .unwrap();
    let mut cache = construct(&mut c, a, Some(&w)).unwrap();
    let failure = pin(&mut cache, &mut c, 34, Some(&w)).unwrap_err();
    assert_eq!(failure.kind, SwiftRunFailureKind::CombinedExhausted);
    assert_eq!(failure.at_failure.wasi, Some(w.usage()));
    cleanup(cache, &mut c, Some(&w));
    w.cleanup(&mut c).unwrap();
    assert_eq!(
        c.finish_owned_cleanup(None).reservations.combined.current,
        0
    );
}
#[test]
fn component_cleanup_and_first_cleanup_invariant() {
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
    let w = wasi(&mut c);
    let mut cache = construct(&mut c, a, Some(&w)).unwrap();
    for f in [34, 35, 34, 36] {
        let _ = pin(&mut cache, &mut c, f, Some(&w)).unwrap();
    }
    let work = c.usage(Some(w.usage())).cache_work;
    c.cancellation().cancel();
    let (mut owned, mut outcome) = (Some(cache), None);
    let (tail, s) = measure(|| SwiftFunctionCache::cleanup(&mut owned, &mut c, Some(&w)).unwrap());
    assert_eq!(s.attempts, 0);
    assert_eq!(
        inspection::tail_construction(&tail),
        foundation_construction_bytes().unwrap()
    );
    let (_, completion) = measure(|| tail.complete(owned, &mut outcome));
    assert_eq!(completion.attempts, 0);
    assert!(outcome.is_none());
    let u = c.usage(Some(w.usage()));
    assert_eq!(u.cache_work, work);
    assert_eq!(u.live.cache_entries.current, 0);
    assert_eq!(u.live.active_pins.current, 0);
    assert_eq!(u.reservations.cache.current, 0);
    assert!(u.reservations.wasi.current > 0);
    w.cleanup(&mut c).unwrap();
    assert_eq!(
        c.finish_owned_cleanup(None).reservations.combined.current,
        0
    );
    let (mut c, cache) = new(&bytes, SwiftRunBudget::default());
    let header = cache_header_bytes().unwrap();
    let mut owner = Some(cache);
    let tail = SwiftFunctionCache::cleanup(&mut owner, &mut c, None).unwrap();
    drop(tail);
    assert!(owner.is_none());
    assert_eq!(c.usage(None).reservations.cache.current, header);
    assert!(c.finish_owned_cleanup(None).reservations.combined.current >= header);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let _ = pin(&mut cache, &mut c, 34, None).unwrap();
    let (mut other, p) = adopt(&bytes, SwiftRunBudget::default());
    let foreign = other
        .admit(SwiftReservationCategory::Cache, 1, cache_cursor())
        .unwrap();
    let original = inspection::replace_entry_ticket(&mut cache, foreign);
    let first = cleanup(cache, &mut c, None).unwrap();
    println!("cleanup first invariant {first:?}");
    assert_eq!(first.stage, SwiftRunStage::Cleanup);
    assert_eq!(first.kind, SwiftRunFailureKind::Invariant);
    assert_eq!(c.usage(None).live.cache_entries.current, 0);
    c.drop_reserved((), original).unwrap();
    other.drop_proof(p).unwrap();
    assert!(
        other
            .finish_owned_cleanup(None)
            .reservations
            .combined
            .current
            > 0
    );
    assert_eq!(
        c.finish_owned_cleanup(None).reservations.combined.current,
        0
    );
    // Foreign WASI preflight must preserve the *exact* caller-owned cache slot.
    let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
    let w = wasi(&mut c);
    let cache = construct(&mut c, a, Some(&w)).unwrap();
    let source = cache.proof().source().as_ptr();
    let (mut other, p) = adopt(&bytes, SwiftRunBudget::default());
    let mut foreign = wasi(&mut other);
    foreign
        .dispatch(
            &mut other,
            WasiFunction::FdClose,
            &[Value::I32(99)],
            &mut [],
            cache_cursor(),
        )
        .unwrap();
    assert_ne!(w.usage(), foreign.usage());
    let mut owner = Some(cache);
    let before = c.usage(Some(w.usage())).reservations;
    {
        let result = SwiftFunctionCache::cleanup(&mut owner, &mut c, Some(&foreign));
        let f = result.err().unwrap();
        assert_eq!(f.at_failure.wasi, None);
    }
    assert_eq!(owner.as_ref().unwrap().proof().source().as_ptr(), source);
    assert_eq!(c.usage(Some(w.usage())).reservations, before);
    let tail = SwiftFunctionCache::cleanup(&mut owner, &mut c, Some(&w)).unwrap();
    let mut outcome = None;
    tail.complete(owner, &mut outcome);
    assert!(outcome.is_some());
    w.cleanup(&mut c).unwrap();
    foreign.cleanup(&mut other).unwrap();
    other.drop_proof(p).unwrap();
    assert_eq!(
        c.finish_owned_cleanup(None).reservations.combined.current,
        0
    );
    assert_eq!(
        other
            .finish_owned_cleanup(None)
            .reservations
            .combined
            .current,
        0
    );
    // A later destructive-cleanup invariant carries this owner's actual usage.
    let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
    let mut w = wasi(&mut c);
    w.dispatch(
        &mut c,
        WasiFunction::FdClose,
        &[Value::I32(17)],
        &mut [],
        cache_cursor(),
    )
    .unwrap();
    let mut cache = construct(&mut c, a, Some(&w)).unwrap();
    let _ = pin(&mut cache, &mut c, 34, Some(&w)).unwrap();
    let (mut other, p) = adopt(&bytes, SwiftRunBudget::default());
    let ticket = other
        .admit(SwiftReservationCategory::Cache, 1, cache_cursor())
        .unwrap();
    let original = inspection::replace_entry_ticket(&mut cache, ticket);
    let first = cleanup(cache, &mut c, Some(&w)).unwrap();
    assert_eq!(first.at_failure.wasi, Some(w.usage()));
    println!("cleanup first invariant {first:?}");
    assert_eq!(first.stage, SwiftRunStage::Cleanup);
    c.drop_reserved_with_wasi((), original, Some(w.usage()))
        .unwrap();
    w.cleanup(&mut c).unwrap();
    other.drop_proof(p).unwrap();
    assert_eq!(
        c.finish_owned_cleanup(None).reservations.combined.current,
        0
    );
    assert!(
        other
            .finish_owned_cleanup(None)
            .reservations
            .combined
            .current
            > 0
    );
}
#[test]
fn sticky_failure_has_no_new_effects() {
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, mut cache) = new(
        &bytes,
        SwiftRunBudget {
            active_pins: 0,
            ..SwiftRunBudget::default()
        },
    );
    let first = pin(&mut cache, &mut c, 34, None).unwrap_err();
    let before = c.usage(None);
    let usage = cache.usage();
    for _ in 0..5 {
        let (f, s) = measure(|| pin(&mut cache, &mut c, 34, None).unwrap_err());
        assert_eq!(f, first);
        assert_eq!(s.attempts, 0);
    }
    let after = c.usage(None);
    assert_eq!(before.reservations, after.reservations);
    assert_eq!(before.cache_work, after.cache_work);
    assert_eq!(usage, cache.usage());
    finish(cache, c);
}
#[test]
fn frozen_layout_allocation_work_error_snapshots() {
    inspection::print_layouts();
    assert_eq!(
        size_of::<Option<SwiftRunFailure>>(),
        size_of::<SwiftRunFailure>()
    );
    assert_eq!(
        size_of::<Result<(), SwiftRunFailure>>(),
        size_of::<SwiftRunFailure>()
    );
    assert!(size_of::<Option<WasiUsage>>() >= size_of::<WasiUsage>());
    let named = 3 * size_of::<ValidatedSwiftReactor>()
        + 3 * size_of::<RuntimeControl>()
        + 3 * size_of::<AdoptedProof>()
        + 4 * size_of::<SwiftRunFailure>()
        + 4 * size_of::<SwiftRunUsage>()
        + 6 * size_of::<ReservationTicket>()
        + 6 * size_of::<Option<WasiUsage>>();
    assert_eq!(foundation_construction_bytes(), Some(named));
    println!("foundation-tail map failure_count=4 usage_count=4 ticket_count=6 optional_wasi_count=6 optional_wasi_bytes={} total={named}",size_of::<Option<WasiUsage>>());
    assert_eq!(
        size_of::<Option<ReservationTicket>>(),
        size_of::<ReservationTicket>()
    );
}
fn external_privacy() {
    use std::process::Command;
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    let cargo = std::env::var_os("CARGO").unwrap_or_else(|| "cargo".into());
    let mut build = Command::new(cargo);
    build.current_dir(root).args([
        "build",
        "--locked",
        "--lib",
        "--features",
        "experimental-swift-reactor,experimental-span-execution",
    ]);
    if !cfg!(debug_assertions) {
        build.arg("--release");
    }
    let output = build.output().unwrap();
    assert!(
        output.status.success(),
        "external current library build: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let deps = std::env::current_exe()
        .unwrap()
        .parent()
        .unwrap()
        .to_path_buf();
    let library = deps.join("libmixer_vm.rlib");
    assert!(library.is_file());
    let folder = std::env::temp_dir().join(format!(
        "mixer-cache-privacy-{}-{}",
        std::process::id(),
        if cfg!(debug_assertions) {
            "debug"
        } else {
            "release"
        }
    ));
    std::fs::create_dir_all(&folder).unwrap();
    let cases=[
        ("positive", "use mixer_vm::experimental::cache::{CacheBudget,FunctionCache};use mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor;fn f(_:CacheBudget,_:Option<FunctionCache>,p:&ValidatedSwiftReactor){let _=p.source();}",None),
        ("private_cache", "use mixer_vm::experimental_swift_reactor::cache::SwiftFunctionCache;",Some("E0603")),
        ("private_parts", "use mixer_vm::experimental::cache::borrowed::{SnapshotView,CacheParts,FrozenMode};",Some("E0603")),
        ("private_control", "use mixer_vm::experimental_swift_reactor::control::RuntimeControl;",Some("E0603")),
        ("proof_forge", "use mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor;fn f(){let _=ValidatedSwiftReactor{};}",Some("private fields")),
        ("proof_clone", "use mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor;fn f(p:ValidatedSwiftReactor){let _=p.clone();}",Some("E0599")),
        ("legacy_conversion", "use mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor;use mixer_vm::experimental::ValidatedSpans;fn f(p:ValidatedSwiftReactor){let _:ValidatedSpans=p;}",Some("E0308")),
        ("mutable_source", "use mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor;fn f(p:ValidatedSwiftReactor){p.source()[0]=1;}",Some("E0594")),
        ("proof_reuse", "use mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor;fn take(_:ValidatedSwiftReactor){}fn f(p:ValidatedSwiftReactor){take(p);take(p);}",Some("E0382")),
        ("view_mutation", "use mixer_vm::{Cancellation};use mixer_vm::experimental::cache::{FunctionCache,FunctionPin};fn f(c:&mut FunctionCache,p:FunctionPin){let v=c.view(&p).unwrap();let _=c.pin(0,&Cancellation::default());let _=v.instructions.len();}",Some("E0502")),
        ("view_release", "use mixer_vm::experimental::cache::{FunctionCache,FunctionPin};fn f(c:&mut FunctionCache,p:FunctionPin){let v=c.view(&p).unwrap();let _=c.release(p);let _=v.instructions.len();}",Some("E0502")),
        ("pin_clone", "use mixer_vm::experimental::cache::FunctionPin;fn f(p:FunctionPin){let _=p.clone();}",Some("E0599")),
        ("pin_forge", "use mixer_vm::experimental::cache::FunctionPin;fn f(){let _=FunctionPin{owner:1,slot:0,nonce:1};}",Some("E0451")),
    ];
    for (name, source, expected) in cases {
        let file = folder.join(format!("{name}.rs"));
        std::fs::write(&file, source).unwrap();
        let output = Command::new("rustc")
            .args([
                "--edition=2021",
                "--crate-type=lib",
                "--emit=metadata",
                "--extern",
            ])
            .arg(format!("mixer_vm={}", library.display()))
            .arg("-L")
            .arg(format!("dependency={}", deps.display()))
            .arg("--out-dir")
            .arg(&folder)
            .arg(&file)
            .output()
            .unwrap();
        let stderr = String::from_utf8_lossy(&output.stderr);
        match expected {
            None => assert!(output.status.success(), "{name}: {stderr}"),
            Some(code) => {
                assert!(!output.status.success(), "{name} unexpectedly compiled");
                assert!(
                    stderr.contains(code),
                    "{name} failed for unexpected reason: {stderr}"
                );
            }
        }
        println!(
            "external privacy {name}: expected={expected:?} exit={}\n{stderr}",
            output.status
        );
    }
}

#[test]
fn external_surface_and_borrow_privacy() {
    external_privacy();
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let p = pin(&mut cache, &mut c, 34, None).unwrap();
    {
        let view = cache.view(&p, &mut c, None).unwrap();
        assert_eq!(view.function, 34);
    }
    cache
        .release(p, &mut c, None)
        .map_err(|e| e.failure)
        .unwrap();
    assert_eq!(cache.identity().policy, "swift-reactor-experiment-v1");
    finish(cache, c);
}
