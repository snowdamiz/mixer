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
    elision_observe_checkpoint(control);
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
    let before_cleanup_work = control.usage(None).cache_work;
    cleanup(cache, &mut control, None);
    let final_usage = control.finish_owned_cleanup(None);
    assert_eq!(
        final_usage.cache_work, before_cleanup_work,
        "consuming cleanup must add no work"
    );
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
fn borrowed_owner_preflight_preserves_storage_and_ignores_ordinary_checks() {
    let bytes = fixture(0, &[0, 0x0b], 29);
    for rejected_owner in 0..3 {
        let (mut control, adopted) = adopt(&bytes, SwiftRunBudget::default());
        let context = wasi(&mut control);
        let cache = construct(&mut control, adopted, Some(&context)).unwrap();
        let (mut other, other_adopted) = adopt(&bytes, SwiftRunBudget::default());
        let other_context = wasi(&mut other);
        let other_cache = construct(&mut other, other_adopted, Some(&other_context)).unwrap();
        let source = cache.proof().source().as_ptr();
        let identity = cache.identity();
        let before = control.usage(Some(context.usage()));
        control.cancellation().cancel();
        hooks(Hooks::default());
        let (result, allocations) = measure(|| match rejected_owner {
            0 => cache.check_owner(&mut control, Some(&context), cache_cursor()),
            1 => cache.check_owner(&mut control, Some(&other_context), cache_cursor()),
            _ => other_cache.check_owner(&mut control, Some(&context), cache_cursor()),
        });
        assert_eq!(allocations.attempts, 0);
        assert_eq!(allocations.deallocations, 0);
        assert_eq!(HOOKS.with(|h| h.get().checks), 0);
        assert_eq!(cache.proof().source().as_ptr(), source);
        assert_eq!(cache.identity(), identity);
        let after = control.usage(Some(context.usage()));
        assert_eq!(before.reservations, after.reservations);
        assert_eq!(before.live, after.live);
        assert_eq!(before.cache_work, after.cache_work);
        assert_eq!(before.execution_work, after.execution_work);
        assert_eq!(before.host_calls, after.host_calls);
        assert_eq!(before.instruction_fuel, after.instruction_fuel);
        assert_eq!(before.instructions, after.instructions);
        if rejected_owner == 0 {
            result.unwrap();
            let terminal = control.fail(
                cache_cursor(),
                Fault::new(SwiftRunFailureKind::GuestTrap, "owner_preflight_prior_trap"),
                Some(context.usage()),
            );
            let (result, allocations) =
                measure(|| cache.check_owner(&mut control, Some(&context), cache_cursor()));
            result.unwrap();
            assert_eq!(allocations.attempts, 0);
            assert_eq!(HOOKS.with(|h| h.get().checks), 0);
            assert_eq!(terminal.code, "owner_preflight_prior_trap");
        } else {
            let failure = result.unwrap_err();
            assert_eq!(failure.kind, SwiftRunFailureKind::Invariant);
            assert_eq!(failure.code, "swift_run_reservation_owner");
            assert_eq!(
                failure.at_failure.wasi,
                if rejected_owner == 1 {
                    None
                } else {
                    Some(context.usage())
                }
            );
        }
        cleanup(cache, &mut control, Some(&context));
        context.cleanup(&mut control).unwrap();
        cleanup(other_cache, &mut other, Some(&other_context));
        other_context.cleanup(&mut other).unwrap();
        assert_eq!(
            control
                .finish_owned_cleanup(None)
                .reservations
                .combined
                .current,
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
    }
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
    assert_eq!(alloc.allocations, 5);
    assert_eq!(alloc.reallocations, 0);
    finish(cache, c);
}
#[test]
fn decoder_opcode_and_count_build_parity() {
    review_every_decoded_instruction_matches_independent_owned_ir();
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
    review_parameter_and_group_boundaries();
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
    assert_eq!(s.allocations, 5);
    println!("permanent fixed requested allocations {:?}", s);
    let expected = 64 * size_of::<super::cache::SwiftSlot>()
        + 64 * size_of::<crate::experimental::cache::PinRecord>()
        + 512 * size_of::<decode::Patch>()
        + 192
        + 28_672; // Measured 512 optional scan-plan cells, grouped under the header.
    assert_eq!(s.allocated_bytes, expected);
    assert_eq!(
        c.usage(None).reservations.cache.current,
        cache_header_bytes().unwrap() + expected - 192 - 28_672
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
    review_64_distinct_live_pins_then_65th_and_terminal_release();
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
    review_owner_allocator_exhaustion();
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
    review_exact_phase_and_header_admission_boundaries();
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
    assert_eq!(n, 5);
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
    for ordinal in 0..5 {
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
    review_final_header_refund_fault_actual_wasi_and_prior_cause();
    review_cleanup_expired_deadline_exact_work_and_latched_terminal();
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
    // This matrix tests propagation after an explicit control terminal latch.
    // Natural failure-origin coverage remains in the other named tests.
    let kinds = [
        SwiftRunFailureKind::InvalidBudget,
        SwiftRunFailureKind::Cancelled,
        SwiftRunFailureKind::Deadline,
        SwiftRunFailureKind::Allocation,
        SwiftRunFailureKind::Adoption,
        SwiftRunFailureKind::CategoryExhausted,
        SwiftRunFailureKind::CombinedExhausted,
        SwiftRunFailureKind::ResourceExhausted,
        SwiftRunFailureKind::FuelExhausted,
        SwiftRunFailureKind::WorkExhausted,
        SwiftRunFailureKind::HostCallLimit,
        SwiftRunFailureKind::PinLimit,
        SwiftRunFailureKind::FrameLimit,
        SwiftRunFailureKind::ValueLimit,
        SwiftRunFailureKind::ControlLimit,
        SwiftRunFailureKind::DecoderMismatch,
        SwiftRunFailureKind::UnsupportedEnvironment,
        SwiftRunFailureKind::GuestTrap,
        SwiftRunFailureKind::GuestExit,
        SwiftRunFailureKind::Wasi,
        SwiftRunFailureKind::Invariant,
    ];
    let bytes = fixture(0, &[0, 0x0b], 100);
    for kind in kinds {
        hooks(Hooks::default());
        let (mut c, adopted) = adopt(&bytes, SwiftRunBudget::default());
        let mut w = wasi(&mut c);
        w.dispatch(
            &mut c,
            WasiFunction::FdClose,
            &[Value::I32(97)],
            &mut [],
            cache_cursor(),
        )
        .unwrap();
        let actual_wasi = w.usage();
        let mut cache = construct(&mut c, adopted, Some(&w)).unwrap();
        let p = pin(&mut cache, &mut c, 34, Some(&w)).unwrap();
        assert_eq!(cache.usage().decodes, 1);
        let first = {
            let mut phase = cache
                .prepare_operation(&mut c, Some(&w), cache_cursor())
                .unwrap();
            let first = inspection::latch_terminal(&mut phase, kind);
            assert_eq!(first.kind, kind);
            assert_eq!(first.at_failure.wasi, Some(actual_wasi));
            let before = inspection::operation_usage(&phase);
            let cached = cache.usage();
            let steps = HOOKS.with(|h| h.get().steps);
            assert_eq!(before.live.active_pins.current, 1);
            assert_eq!(before.live.cache_entries.current, 1);
            // Hit, fresh miss and invalid function must all retain the first
            // terminal cause before decoding or validating another request.
            for function in [34, 35, 0, 35, 34] {
                let (failure, allocations) =
                    measure(|| phase.pin(&mut cache, function).unwrap_err());
                assert_eq!(failure, first);
                review_assert_no_allocator_effects(allocations);
                assert_eq!(cache.usage(), cached);
                assert_eq!(w.usage(), actual_wasi);
                review_assert_same_control_effects(before, inspection::operation_usage(&phase));
                review_assert_no_decoder_steps(steps);
            }
            phase.complete((before, cached, steps)).unwrap();
            first
        };
        let before = c.usage(Some(actual_wasi));
        let cached = cache.usage();
        let steps = HOOKS.with(|h| h.get().steps);
        for function in [34, 35, 0, 35, 34] {
            let (failure, allocations) =
                measure(|| pin(&mut cache, &mut c, function, Some(&w)).unwrap_err());
            assert_eq!(failure, first);
            review_assert_no_allocator_effects(allocations);
            let (failure, allocations) = measure(|| {
                cache
                    .prepare_operation(&mut c, Some(&w), cache_cursor())
                    .err()
                    .unwrap()
            });
            assert_eq!(failure, first);
            review_assert_no_allocator_effects(allocations);
            assert_eq!(cache.usage(), cached);
            assert_eq!(w.usage(), actual_wasi);
            review_assert_same_control_effects(before, c.usage(Some(actual_wasi)));
            review_assert_no_decoder_steps(steps);
        }
        // Destroy the external token without release; only terminal cache drain
        // may reclaim its still-live pin/entry counts.
        #[allow(clippy::drop_non_drop)]
        drop(p);
        let (outcome, allocations) = measure(|| cleanup(cache, &mut c, Some(&w)).unwrap());
        review_assert_no_allocator_requests(allocations);
        assert_eq!(outcome.kind, first.kind);
        assert_eq!(outcome.code, first.code);
        assert_eq!(outcome.at_failure, first.at_failure);
        assert!(outcome.after_cleanup.is_some());
        let after = outcome.after_cleanup.unwrap();
        assert_eq!(after.wasi, Some(actual_wasi));
        assert_eq!(after.live.active_pins.current, 0);
        assert_eq!(after.live.cache_entries.current, 0);
        assert_eq!(after.cleanup_invariant, None);
        assert!(
            after.reservations.combined.current < first.at_failure.reservations.combined.current
        );
        assert!(after.reservations.combined.peak >= first.at_failure.reservations.combined.peak);
        assert_eq!(w.usage(), actual_wasi);
        w.cleanup(&mut c).unwrap();
        let final_usage = c.finish_owned_cleanup(Some(actual_wasi));
        assert_eq!(final_usage.reservations.combined.current, 0);
        assert_eq!(final_usage.reservations.live_tickets, 0);
        assert_eq!(final_usage.live.active_pins.current, 0);
        assert_eq!(final_usage.live.cache_entries.current, 0);
        assert_eq!(final_usage.cleanup_invariant, None);
        println!("sticky terminal kind={kind:?} phase_repeats=5 full_pin_repeats=5 prepare_repeats=5 decode_delta=0 service_delta=0 allocation_requests=0 work_delta=0 honest_cleanup=true");
    }
}
fn review_assert_same_control_effects(before: SwiftRunUsage, mut after: SwiftRunUsage) {
    // Native elapsed time may advance while every authoritative effect stays equal.
    after.elapsed_micros = before.elapsed_micros;
    after.deadline_overshoot_micros = before.deadline_overshoot_micros;
    assert_eq!(after, before);
}
fn review_assert_no_decoder_steps(before: [usize; 8]) {
    let after = HOOKS.with(|h| h.get().steps);
    for step in [
        CacheStep::Planning,
        CacheStep::ScanReset,
        CacheStep::Scan,
        CacheStep::BuildReset,
        CacheStep::Build,
        CacheStep::Publication,
    ] {
        assert_eq!(after[step as usize], before[step as usize]);
    }
}
fn review_assert_no_allocator_requests(stats: super::allocation_tests::AllocationStats) {
    assert_eq!(stats.attempts, 0);
    assert_eq!(stats.allocations, 0);
    assert_eq!(stats.reallocations, 0);
    assert_eq!(stats.allocated_bytes, 0);
}
fn review_assert_no_allocator_effects(stats: super::allocation_tests::AllocationStats) {
    review_assert_no_allocator_requests(stats);
    assert_eq!(stats.deallocations, 0);
    assert_eq!(stats.freed_bytes, 0);
}

#[test]
fn frozen_layout_allocation_work_error_snapshots() {
    inspection::assert_preflight_inventory();
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
        + 6 * size_of::<Option<WasiUsage>>()
        + FOUNDATION_FINAL_BOUNDARY_BYTES
        + super::execution::CONSTRUCTION_BOOTSTRAP_BYTES;
    assert_eq!(foundation_construction_bytes(), Some(named));
    println!("foundation-tail map failure_count=4 usage_count=4 ticket_count=6 optional_wasi_count=6 optional_wasi_bytes={} final_boundary={} total={named}",size_of::<Option<WasiUsage>>(), FOUNDATION_FINAL_BOUNDARY_BYTES);
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

// Project-authored independent review assertions promoted into the original named tests.
fn review_assert_category_sum(u: SwiftRunUsage) {
    let r = u.reservations;
    assert_eq!(
        r.combined.current,
        r.retained_source.current
            + r.retained_metadata.current
            + r.cache.current
            + r.state.current
            + r.wasi.current
            + r.shared.current
            + r.construction.current
    );
}

fn review_64_distinct_live_pins_then_65th_and_terminal_release() {
    hooks(Hooks::default());
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let mut pins = Vec::with_capacity(64);
    for function in 34..98 {
        let p = pin(&mut cache, &mut c, function, None).unwrap();
        assert_eq!(cache.view(&p, &mut c, None).unwrap().function, function);
        pins.push(p);
        review_assert_category_sum(c.usage(None));
    }
    let before = cache.usage();
    let ledger = c.usage(None);
    assert_eq!(ledger.live.active_pins.current, 64);
    assert_eq!(ledger.live.cache_entries.current, 64);
    assert_eq!(ledger.reservations.live_tickets, 73);
    assert_eq!(before.pinned_bytes, before.resident_bytes);
    let (failure, stats) = measure(|| pin(&mut cache, &mut c, 98, None).unwrap_err());
    assert_eq!(failure.code, "pin_slots_exhausted");
    assert_eq!(stats.attempts, 0);
    assert_eq!(cache.usage(), before);
    assert_eq!(c.usage(None).live, ledger.live);
    let work = c.usage(None).cache_work;
    let (_, stats) = measure(|| {
        for p in pins {
            cache
                .release(p, &mut c, None)
                .map_err(|e| e.failure)
                .unwrap();
        }
    });
    assert_eq!(stats.attempts, 0);
    assert_eq!(c.usage(None).cache_work, work);
    assert_eq!(cache.usage().pinned_bytes, 0);
    assert_eq!(cache.usage().resident_bytes, before.resident_bytes);
    finish(cache, c);
}

fn review_parameter_and_group_boundaries() {
    for (params, locals, accepted) in [
        (128, 128, true),
        (129, 0, false),
        (128, 129, false),
        (0, 256, true),
        (0, 257, false),
    ] {
        let bytes = fixture(params, &body(locals, &[0x0b]), 100);
        let p = validate_swift_reactor(
            &bytes,
            SwiftValidationBudget::default(),
            &Cancellation::default(),
        );
        assert_eq!(p.is_ok(), accepted, "params={params} locals={locals}");
        if accepted {
            let (mut c, a) = RuntimeControl::adopt(
                p.unwrap(),
                SwiftRunBudget::default(),
                Instant::now(),
                Cancellation::default(),
            )
            .unwrap();
            let mut cache = construct(&mut c, a, None).unwrap();
            let p = pin(&mut cache, &mut c, 34, None).unwrap();
            assert_eq!(cache.view(&p, &mut c, None).unwrap().locals.len(), locals);
            finish(cache, c);
        }
    }
    for groups in [256, 257] {
        let mut helper = Vec::new();
        uint(groups, &mut helper);
        for _ in 0..groups {
            helper.extend([0, 0x7f]);
        }
        helper.push(0x0b);
        let bytes = fixture(0, &helper, 100);
        let p = validate_swift_reactor(
            &bytes,
            SwiftValidationBudget::default(),
            &Cancellation::default(),
        );
        assert_eq!(p.is_ok(), groups == 256);
        if groups == 256 {
            let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
            let p = pin(&mut cache, &mut c, 34, None).unwrap();
            assert!(cache.view(&p, &mut c, None).unwrap().locals.is_empty());
            finish(cache, c);
        }
    }
}

fn review_owned_fixture(helper: &[u8]) -> Vec<u8> {
    let mut module = b"\0asm\x01\0\0\0".to_vec();
    let mut types = vec![37];
    for _ in 0..37 {
        signature(&[], &[], &mut types);
    }
    section(1, &types, &mut module);
    let mut functions = vec![100];
    functions.extend([0; 100]);
    section(3, &functions, &mut module);
    section(4, &[1, 0x70, 1, 1, 1], &mut module);
    section(5, &[1, 0, 1], &mut module);
    section(6, &[1, 0x7f, 1, 0x41, 0, 0x0b], &mut module);
    let mut code = vec![100];
    for index in 0..100 {
        let helper = if index == 0 { helper } else { &[0, 0x0b] };
        uint(helper.len() as u32, &mut code);
        code.extend_from_slice(helper);
    }
    section(10, &code, &mut module);
    module
}

fn review_operation(
    op: &crate::Op,
    targets: &mut Vec<u32>,
) -> crate::experimental::cache::Operation {
    use crate::experimental::cache::{ControlKind as K, Operation as C};
    use crate::{BlockKind as B, Op as O};
    match op {
        O::Unreachable => C::Unreachable,
        O::Nop => C::Nop,
        O::Block {
            kind,
            result,
            end,
            alternative,
        } => C::Block {
            kind: match kind {
                B::Block => K::Block,
                B::Loop => K::Loop,
                B::If => K::If,
                B::Function => panic!("no synthetic owned Function opcode"),
            },
            result: *result,
            end: *end,
            alternative: *alternative,
        },
        O::Else { end } => C::Else { end: *end },
        O::End => C::End,
        O::Br(n) => C::Br(*n),
        O::BrIf(n) => C::BrIf(*n),
        O::BrTable(values, default) => {
            let first = targets.len();
            targets.extend_from_slice(values);
            C::BrTable {
                first,
                count: values.len(),
                default: *default,
            }
        }
        O::Return => C::Return,
        O::Call(n) => C::Call(*n),
        O::CallIndirect(n) => C::CallIndirect(*n),
        O::MemoryCopy => C::MemoryCopy,
        O::MemoryFill => C::MemoryFill,
        O::Drop => C::Drop,
        O::Select => C::Select,
        O::LocalGet(n) => C::LocalGet(*n),
        O::LocalSet(n) => C::LocalSet(*n),
        O::LocalTee(n) => C::LocalTee(*n),
        O::GlobalGet(n) => C::GlobalGet(*n),
        O::GlobalSet(n) => C::GlobalSet(*n),
        O::Load { opcode, offset } => C::Load {
            opcode: *opcode,
            offset: *offset,
        },
        O::Store { opcode, offset } => C::Store {
            opcode: *opcode,
            offset: *offset,
        },
        O::MemorySize => C::MemorySize,
        O::MemoryGrow => C::MemoryGrow,
        O::Const(v) => C::Const(*v),
        O::Numeric(n) => C::Numeric(*n),
        O::Saturating(n) => C::Saturating(*n),
    }
}

fn review_every_decoded_instruction_matches_independent_owned_ir() {
    // Unreachable stack permits every admitted instruction to be decoded and
    // type-validated. Absolute module offsets differ; relative offsets must not.
    let mut code = vec![
        0, 1, 0, 0x0c, 0, 0, 0x0d, 0, 0, 0x0e, 3, 0, 0, 0, 0, 0, 0x0f, 0, 0x10, 35, 0, 0x1a, 0,
        0x1b,
    ];
    for opcode in 0x20..=0x24 {
        code.extend([0, opcode, 0x80, 0]);
    }
    for opcode in 0x28..=0x3e {
        code.extend([0, opcode, 0, 0x80, 1]);
    }
    code.extend([
        0, 0x3f, 0, 0, 0x40, 0, 0, 0x41, 0x80, 0x80, 0x80, 0x80, 0x78, 0, 0x42, 0xff, 0xff, 0xff,
        0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0,
    ]);
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
    let owned_bytes = review_owned_fixture(&helper);
    let limits = crate::Limits {
        profile: crate::Profile::TableMemoryV3,
        ..crate::Limits::default()
    };
    let owned = crate::Module::decode(&owned_bytes, &limits).unwrap();
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let p = pin(&mut cache, &mut c, 34, None).unwrap();
    let view = cache.view(&p, &mut c, None).unwrap();
    let expected = &owned.functions[0];
    assert_eq!(view.locals, expected.locals);
    assert_eq!(view.instructions.len(), expected.code.len());
    let mut targets = Vec::new();
    for (index, (actual, original)) in view.instructions.iter().zip(&expected.code).enumerate() {
        assert_eq!(
            actual.operation,
            review_operation(&original.op, &mut targets),
            "instruction{index}"
        );
        assert_eq!(
            actual.offset - view.body_offset,
            original.offset - expected.offset,
            "offset{index}"
        );
    }
    assert_eq!(view.branch_targets, targets);
    println!(
        "review compared exact owned IR instructions={} targets={}",
        view.instructions.len(),
        targets.len()
    );
    finish(cache, c);
}

fn review_final_header_refund_fault_actual_wasi_and_prior_cause() {
    for prior in [false, true] {
        hooks(Hooks::default());
        let bytes = fixture(0, &[0, 0x0b], 100);
        let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
        let mut w = wasi(&mut c);
        w.dispatch(
            &mut c,
            WasiFunction::FdClose,
            &[Value::I32(47)],
            &mut [],
            cache_cursor(),
        )
        .unwrap();
        let actual = w.usage();
        let mut cache = construct(&mut c, a, Some(&w)).unwrap();
        for f in [34, 34, 35, 36] {
            let _ = pin(&mut cache, &mut c, f, Some(&w)).unwrap();
        }
        let first = if prior {
            c.cancellation().cancel();
            Some(c.check_with_wasi(cache_cursor(), Some(actual)).unwrap_err())
        } else {
            None
        };
        let (mut foreign, foreign_proof) = adopt(&bytes, SwiftRunBudget::default());
        let foreign_ticket = foreign
            .admit(SwiftReservationCategory::Cache, 1, cache_cursor())
            .unwrap();
        let before = c.usage(Some(actual));
        let mut owner = Some(cache);
        let (mut tail, drops) =
            measure(|| SwiftFunctionCache::cleanup(&mut owner, &mut c, Some(&w)).unwrap());
        assert_eq!(drops.attempts, 0);
        assert!(owner.is_none());
        let original = inspection::replace_tail_header(&mut tail, foreign_ticket);
        let mut outcome = None;
        let (_, completion) = measure(|| tail.complete(owner, &mut outcome));
        assert_eq!(completion.attempts, 0);
        let failure = outcome.unwrap();
        assert_eq!(failure.at_failure.wasi, Some(actual));
        if let Some(first) = first {
            assert_eq!(failure.code, first.code);
            assert_eq!(failure.at_failure, first.at_failure);
        } else {
            assert_eq!(failure.code, "swift_run_release_owner");
            assert_eq!(failure.stage, SwiftRunStage::Cleanup);
            assert_eq!(
                failure.at_failure.reservations.cache.current,
                cache_header_bytes().unwrap()
            );
            assert_eq!(failure.at_failure.reservations.retained_source.current, 0);
            assert_eq!(failure.at_failure.reservations.retained_metadata.current, 0);
        }
        let after = failure.after_cleanup.unwrap();
        assert_eq!(
            after.cleanup_invariant,
            Some(SwiftCleanupInvariant::ReservationOwner)
        );
        assert_eq!(after.wasi, Some(actual));
        assert_eq!(
            after.reservations.cache.current,
            cache_header_bytes().unwrap()
        );
        assert_eq!(
            after.reservations.construction.current,
            foundation_construction_bytes().unwrap()
        );
        assert_eq!(after.live.active_pins.current, 0);
        assert_eq!(after.live.cache_entries.current, 0);
        assert_eq!(c.usage(Some(actual)).cache_work, before.cache_work);
        assert_eq!(
            c.usage(Some(actual)).reservations.wasi,
            before.reservations.wasi
        );
        c.drop_reserved_with_wasi((), original, Some(actual))
            .unwrap();
        w.cleanup(&mut c).unwrap();
        let final_usage = c.finish_owned_cleanup(None);
        assert_eq!(final_usage.reservations.combined.current, 0);
        assert_eq!(final_usage.reservations.live_tickets, 0);
        foreign.drop_proof(foreign_proof).unwrap();
        let corrupted = foreign.finish_owned_cleanup(None);
        assert_eq!(corrupted.reservations.combined.current, 1);
        assert_eq!(corrupted.reservations.live_tickets, 1);
        println!("review final refund fault prior={prior}; original owner drained; corrupted foreign1-byte charge retained");
    }
}

fn review_cleanup_expired_deadline_exact_work_and_latched_terminal() {
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let _ = pin(&mut cache, &mut c, 34, None).unwrap();
    let exact_work = c.usage(None).cache_work;
    finish(cache, c);
    for case in ["deadline", "work", "terminal"] {
        let budget = SwiftRunBudget {
            deadline_ms: if case == "deadline" { 1_000 } else { 30_000 },
            cache_work: if case == "work" {
                exact_work
            } else {
                64_000_000
            },
            ..SwiftRunBudget::default()
        };
        let (mut c, mut cache) = new(&bytes, budget);
        let _ = pin(&mut cache, &mut c, 34, None).unwrap();
        if case == "deadline" {
            std::thread::sleep(
                c.deadline().saturating_duration_since(Instant::now()) + Duration::from_millis(1),
            );
        }
        if case == "work" {
            assert_eq!(c.usage(None).cache_work, exact_work);
        }
        let first = if case == "terminal" {
            c.cancellation().cancel();
            Some(c.check(cache_cursor()).unwrap_err())
        } else {
            None
        };
        let before = c.usage(None);
        let mut owner = Some(cache);
        let mut outcome = None;
        let (_, stats) = measure(|| {
            let tail = SwiftFunctionCache::cleanup(&mut owner, &mut c, None).unwrap();
            tail.complete(owner, &mut outcome);
        });
        assert_eq!(stats.attempts, 0);
        assert_eq!(c.usage(None).cache_work, before.cache_work);
        assert_eq!(
            c.usage(None).reservations.construction.current,
            foundation_construction_bytes().unwrap()
        );
        assert_eq!(c.usage(None).reservations.cache.current, 0);
        match first {
            Some(f) => assert_eq!(outcome.unwrap().at_failure, f.at_failure),
            None => assert!(outcome.is_none()),
        }
        let final_usage = c.finish_owned_cleanup(None);
        assert_eq!(final_usage.reservations.combined.current, 0);
        assert_eq!(final_usage.reservations.live_tickets, 0);
    }
}

// Admission probes use actual current ledger totals and the measured formulas;
// each exact-minus-one denial occurs before any payload allocation.
fn review_exact_phase_and_header_admission_boundaries() {
    hooks(Hooks::default());
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut baseline, proof) = adopt(&bytes, SwiftRunBudget::default());
    let adopted = baseline.usage(None).reservations.combined.current;
    baseline.drop_proof(proof).unwrap();
    assert_eq!(
        baseline
            .finish_owned_cleanup(None)
            .reservations
            .combined
            .current,
        0
    );
    for exact in [false, true] {
        let extra = cache_construction_bytes().unwrap();
        let (mut c, a) = adopt(
            &bytes,
            SwiftRunBudget {
                combined_bytes: adopted + extra - usize::from(!exact),
                ..SwiftRunBudget::default()
            },
        );
        if exact {
            let (phase, stats) =
                measure(|| SwiftFunctionCache::prepare(&mut c, None, &a, cache_cursor()).unwrap());
            assert_eq!(stats.attempts, 0);
            assert_eq!(
                inspection::construction_current(&phase),
                foundation_construction_bytes().unwrap() + extra
            );
            phase.complete(()).unwrap();
        } else {
            let (failure, stats) = measure(|| {
                SwiftFunctionCache::prepare(&mut c, None, &a, cache_cursor())
                    .err()
                    .unwrap()
            });
            assert_eq!(stats.attempts, 0);
            assert_eq!(failure.kind, SwiftRunFailureKind::CombinedExhausted);
        }
        c.drop_proof(a).unwrap();
        assert_eq!(
            c.finish_owned_cleanup(None).reservations.combined.current,
            0
        );
    }
    let (baseline, cache) = new(&bytes, SwiftRunBudget::default());
    let resident_base = baseline.usage(None).reservations.combined.current;
    finish(cache, baseline);
    for exact in [false, true] {
        let extra = cache_operation_bytes().unwrap();
        let (mut c, cache) = new(
            &bytes,
            SwiftRunBudget {
                combined_bytes: resident_base + extra - usize::from(!exact),
                ..SwiftRunBudget::default()
            },
        );
        if exact {
            let (phase, stats) = measure(|| {
                cache
                    .prepare_operation(&mut c, None, cache_cursor())
                    .unwrap()
            });
            assert_eq!(stats.attempts, 0);
            assert_eq!(
                inspection::operation_current(&phase),
                foundation_construction_bytes().unwrap() + extra
            );
            phase.complete(()).unwrap();
        } else {
            let (failure, stats) = measure(|| {
                cache
                    .prepare_operation(&mut c, None, cache_cursor())
                    .err()
                    .unwrap()
            });
            assert_eq!(stats.attempts, 0);
            assert_eq!(failure.kind, SwiftRunFailureKind::CombinedExhausted);
        }
        finish(cache, c);
    }
    let header = cache_header_bytes().unwrap();
    let patch_bytes = 512 * size_of::<decode::Patch>();
    for ceiling in [
        header - 1,
        header,
        header + patch_bytes - 1,
        header + patch_bytes,
    ] {
        let (mut c, a) = adopt(
            &bytes,
            SwiftRunBudget {
                cache_bytes: ceiling,
                cache_entries: 0,
                active_pins: 0,
                ..SwiftRunBudget::default()
            },
        );
        let (result, stats) = measure(|| construct(&mut c, a, None));
        if ceiling == header + patch_bytes {
            assert_eq!(stats.attempts, 3);
            let cache = result.unwrap();
            assert_eq!(c.usage(None).reservations.cache.current, ceiling);
            finish(cache, c);
        } else {
            assert_eq!(stats.attempts, usize::from(ceiling >= header + patch_bytes));
            let failure = result.err().unwrap();
            assert_eq!(failure.kind, SwiftRunFailureKind::CategoryExhausted);
            assert_eq!(
                c.usage(None).reservations.cache.peak,
                if ceiling < header {
                    0
                } else if ceiling < header + patch_bytes {
                    header
                } else {
                    header + patch_bytes
                }
            );
            assert_eq!(c.usage(None).reservations.cache.current, 0);
            assert_eq!(
                c.finish_owned_cleanup(None).reservations.combined.current,
                0
            );
        }
    }
}

// Exercises the actual constructor failure/partial-drain branch with a private
// per-test-thread counter. No store to the production NEXT_OWNER occurs.
fn review_owner_allocator_exhaustion() {
    hooks(Hooks::default());
    let bytes = fixture(0, &[0, 0x0b], 100);
    let original_test_counter = inspection::owner_counter();
    inspection::with_owner_counter(u64::MAX - 1, || {
        let (c, cache) = new(&bytes, SwiftRunBudget::default());
        assert_eq!(cache.identity().owner, u64::MAX - 1);
        assert_eq!(inspection::owner_counter(), u64::MAX);
        finish(cache, c);
        let (mut baseline, adopted) = adopt(&bytes, SwiftRunBudget::default());
        let (_, proof_drop) = measure(|| baseline.drop_proof(adopted).unwrap());
        assert_eq!(
            baseline
                .finish_owned_cleanup(None)
                .reservations
                .combined
                .current,
            0
        );
        for attempt in 0..3 {
            let (mut c, adopted) = adopt(&bytes, SwiftRunBudget::default());
            let (failure, allocations) =
                measure(|| construct(&mut c, adopted, None).err().unwrap());
            assert_eq!(failure.kind, SwiftRunFailureKind::Invariant);
            assert_eq!(failure.code, "swift_cache_owner_exhausted");
            assert_eq!(allocations.attempts, 5);
            assert_eq!(allocations.injected_failures, 0);
            assert_eq!(allocations.allocations, 5);
            assert_eq!(allocations.reallocations, 0);
            assert_eq!(
                allocations.deallocations,
                allocations.allocations + proof_drop.deallocations
            );
            assert_eq!(
                allocations.freed_bytes,
                allocations.allocated_bytes + proof_drop.freed_bytes
            );
            assert_eq!(inspection::owner_counter(), u64::MAX);
            let after = c.usage(None);
            assert_eq!(after.reservations.cache.current, 0);
            assert_eq!(after.reservations.retained_source.current, 0);
            assert_eq!(after.reservations.retained_metadata.current, 0);
            assert_eq!(after.live.active_pins.current, 0);
            assert_eq!(after.live.cache_entries.current, 0);
            assert_eq!(after.cleanup_invariant, None);
            assert!(failure.at_failure.reservations.cache.current > 0);
            assert!(
                after.reservations.combined.current
                    < failure.at_failure.reservations.combined.current
            );
            let final_usage = c.finish_owned_cleanup(None);
            assert_eq!(final_usage.reservations.combined.current, 0);
            assert_eq!(final_usage.reservations.live_tickets, 0);
            println!("owner allocator exhaustion attempt={attempt} private_counter=MAX actual_constructor_allocations=5 partial_drained=true no_duplicate_authority=true");
        }
    });
    assert!(!inspection::owner_override_active());
    assert_eq!(inspection::owner_counter(), original_test_counter);
    let unwind = std::panic::catch_unwind(|| {
        inspection::with_owner_counter(u64::MAX, || panic!("owner test scope unwind"));
    });
    assert!(unwind.is_err());
    assert!(!inspection::owner_override_active());
    assert_eq!(inspection::owner_counter(), original_test_counter);
    // A normal construction uses the untouched global allocator after both
    // ordinary scope completion and unwinding of the private-counter scope.
    let (c, cache) = new(&bytes, SwiftRunBudget::default());
    assert_ne!(cache.identity().owner, 0);
    assert!(cache.identity().owner < u64::MAX - 1);
    finish(cache, c);
}

// Test-only setup for the lifecycle composition's actual cache checkpoints.
pub(super) fn lifecycle_cancel_at_step(step: CacheStep) {
    hooks(Hooks {
        pause: Some(step),
        cancel_pause: true,
        ..Hooks::default()
    });
}
pub(super) fn lifecycle_reset_hooks() {
    hooks(Hooks::default());
}
// Reset-elision tests: all hooks are test-only; no runtime-control replacement.
#[derive(Clone, Copy)]
struct ElisionObservation {
    enabled: bool,
    dirty: bool,
    dirty_passes: [usize; 2],
    stage_work: [u64; 8],
    previous_work: u64,
    previous_step: CacheStep,
    boundaries: [Option<(usize, u64)>; 2],
}
impl Default for ElisionObservation {
    fn default() -> Self {
        Self {
            enabled: false,
            dirty: false,
            dirty_passes: [0; 2],
            stage_work: [0; 8],
            previous_work: 0,
            previous_step: CacheStep::Constructor,
            boundaries: [None; 2],
        }
    }
}
thread_local! { static ELISION: Cell<ElisionObservation> = Cell::new(ElisionObservation::default()); }
fn elision_observe_checkpoint(control: &RuntimeControl) {
    ELISION.with(|state| {
        let mut x = state.get();
        if x.enabled {
            let work = control.usage(None).cache_work;
            x.stage_work[x.previous_step as usize] += work - x.previous_work;
            x.previous_work = work;
            x.previous_step = HOOKS.with(|h| h.get().step);
            let boundary = match x.previous_step {
                CacheStep::ScanReset => Some(0),
                CacheStep::BuildReset => Some(1),
                _ => None,
            };
            if let Some(index) = boundary {
                x.boundaries[index].get_or_insert((HOOKS.with(|h| h.get().checks), work));
            }
            state.set(x);
        }
    });
}
fn elision_enable(control: &RuntimeControl, dirty: bool) {
    ELISION.with(|s| {
        s.set(ElisionObservation {
            enabled: true,
            dirty,
            previous_work: control.usage(None).cache_work,
            ..ElisionObservation::default()
        })
    });
}
fn elision_finish_observation(control: &RuntimeControl) -> ElisionObservation {
    elision_observe_checkpoint(control);
    ELISION.with(|s| {
        let x = s.get();
        s.set(ElisionObservation::default());
        x
    })
}
// A test-only ordinary decoder meter. It seeds finite initialized scratch and
// checks malformed syntax; it never authorizes a cache entry or substitutes for
// the real RuntimeControl used by every actual-owner cache operation below.
pub(super) struct ElisionScratchMeter;
impl crate::experimental::cache::borrowed::sealed::Meter for ElisionScratchMeter {}
impl crate::experimental::cache::borrowed::DecodeMeter for ElisionScratchMeter {
    type Failure = &'static str;
    fn error(
        &mut self,
        _: crate::experimental::cache::CacheFailureKind,
        code: &'static str,
    ) -> Self::Failure {
        code
    }
    fn check(&mut self) -> Result<(), Self::Failure> {
        Ok(())
    }
    fn work(&mut self, _: u64) -> Result<(), Self::Failure> {
        Ok(())
    }
    fn set_offset(&mut self, _: usize) {}
    fn exact_capacity(&mut self, requested: usize, observed: usize) -> Result<(), Self::Failure> {
        assert_eq!(requested, observed);
        Ok(())
    }
}
pub(super) fn elision_seed_patches(patches: &mut [decode::Patch]) {
    use crate::experimental::cache::borrowed::FrozenPolicy;
    // Each independent one-slot pass writes start=17, alternative=Some(19),
    // kind=If through the unchanged decoder. These are all nonempty fields and
    // hostile for the much shorter bodies below. No raw or uninitialized memory.
    const SEED: &[u8] = &[
        0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 4, 0x40, 1, 5, 1, 0x0b, 0x0b,
    ];
    let limits = crate::Limits::default();
    let policy = FrozenPolicy {
        limits: &limits,
        extent: SEED.len(),
    };
    for patch in patches {
        let mut depth = 0;
        let mut counts = decode::Counts::default();
        decode::scan_borrowed(
            SEED,
            0,
            &policy,
            &mut ElisionScratchMeter,
            decode::PassParts {
                controls: std::slice::from_mut(patch),
                depth: &mut depth,
                counts: &mut counts,
            },
            None,
        )
        .unwrap();
        assert_eq!(depth, 0);
    }
}
pub(super) fn elision_dirty_before_boundary(patches: &mut [decode::Patch]) {
    if !ELISION.with(|s| s.get().dirty) {
        return;
    }
    assert_eq!(patches.len(), 512);
    elision_seed_patches(patches);
    let index = match HOOKS.with(|h| h.get().step) {
        CacheStep::ScanReset => 0,
        CacheStep::BuildReset => 1,
        other => panic!("unexpected reset {other:?}"),
    };
    ELISION.with(|s| {
        let mut x = s.get();
        x.dirty_passes[index] += 1;
        s.set(x);
    });
}
#[test]
fn reset_elision_observation_fixture() {
    use crate::experimental::cache::{ControlKind as K, Operation as O};
    for (label, helper, expected) in [
        ("flat", body(0, &[0x0b]), vec![O::End]),
        (
            "nested",
            body(
                0,
                &[
                    2, 0x40, 3, 0x40, 1, 0x0b, 0x0b, 0x41, 0, 4, 0x40, 1, 5, 1, 0x0b, 0x0b,
                ],
            ),
            vec![
                O::Block {
                    kind: K::Block,
                    result: None,
                    end: 4,
                    alternative: None,
                },
                O::Block {
                    kind: K::Loop,
                    result: None,
                    end: 3,
                    alternative: None,
                },
                O::Nop,
                O::End,
                O::End,
                O::Const(Value::I32(0)),
                O::Block {
                    kind: K::If,
                    result: None,
                    end: 10,
                    alternative: Some(8),
                },
                O::Nop,
                O::Else { end: 10 },
                O::Nop,
                O::End,
                O::End,
            ],
        ),
    ] {
        hooks(Hooks::default());
        let bytes = fixture(0, &helper, 100);
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
        assert_eq!(c.usage(None).cache_work, 4_928);
        elision_enable(&c, false);
        let before = c.usage(None).cache_work;
        let p = pin(&mut cache, &mut c, 34, None).unwrap();
        let view = cache.view(&p, &mut c, None).unwrap();
        assert_eq!(
            view.instructions
                .iter()
                .map(|i| i.operation.clone())
                .collect::<Vec<_>>(),
            expected
        );
        cache
            .release(p, &mut c, None)
            .map_err(|e| e.failure)
            .unwrap();
        let cold = elision_finish_observation(&c);
        assert_eq!(
            cold.stage_work.iter().sum::<u64>(),
            c.usage(None).cache_work - before
        );
        elision_enable(&c, false);
        let (hit, stats) = measure(|| pin(&mut cache, &mut c, 34, None).unwrap());
        let (_, release_stats) = measure(|| {
            cache
                .release(hit, &mut c, None)
                .map_err(|e| e.failure)
                .unwrap()
        });
        assert_eq!(stats.attempts, 0);
        assert_eq!(release_stats.attempts, 0);
        let hit = elision_finish_observation(&c);
        assert_eq!(hit.stage_work.iter().sum::<u64>(), 8);
        println!("ELISION {{\"case\":\"{label}\",\"constructorWork\":4928,\"coldWork\":{},\"coldStages\":{:?},\"hitWork\":8,\"hitStages\":{:?},\"fixedReserved\":{},\"residentBytes\":{}}}",cold.stage_work.iter().sum::<u64>(),cold.stage_work,hit.stage_work,cache.usage().fixed_reserved,cache.usage().resident_bytes);
        finish(cache, c);
    }
    hooks(Hooks::default());
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, mut cache) = new(
        &bytes,
        SwiftRunBudget {
            cache_entries: 3,
            ..SwiftRunBudget::default()
        },
    );
    let mut held = None;
    for (index, function) in [34, 35, 36, 35, 37, 34, 38, 37].into_iter().enumerate() {
        let p = pin(&mut cache, &mut c, function, None).unwrap();
        let parts = inspection::elision_pin_parts(&p);
        let times = inspection::elision_times(&cache);
        let newest = times.iter().max().copied().unwrap();
        assert_eq!(newest, c.usage(None).cache_work);
        assert!(times.iter().all(|t| *t == 0 || *t <= newest));
        if index == 0 {
            held = Some(p);
        } else {
            cache
                .release(p, &mut c, None)
                .map_err(|e| e.failure)
                .unwrap();
        }
        if index == 4 {
            cache
                .release(held.take().unwrap(), &mut c, None)
                .map_err(|e| e.failure)
                .unwrap();
        }
        println!("ELISION {{\"case\":\"lru\",\"access\":{index},\"function\":{function},\"pin\":{:?},\"slots\":{:?},\"timestamps\":{:?},\"hits\":{},\"misses\":{},\"evictions\":{},\"residentBytes\":{},\"pinnedBytes\":{}}}",parts,inspection::elision_slots(&cache),times,cache.usage().hits,cache.usage().misses,cache.usage().evictions,cache.usage().resident_bytes,cache.usage().pinned_bytes);
    }
    assert_eq!(cache.usage().hits, 3);
    assert_eq!(cache.usage().misses, 5);
    assert_eq!(cache.usage().evictions, 2);
    finish(cache, c);
    println!("ELISION {{\"case\":\"cleanup\",\"ownersDrained\":3,\"cacheAndCombinedReservations\":0,\"livePinsAndEntries\":0}}");
}
#[test]
fn reset_elision_dirty_actual_owner_both_passes_and_reuse() {
    use crate::experimental::cache::{ControlKind as K, Operation as O};
    let cases = [
        ("flat", body(0, &[1, 0x0b]), vec![O::Nop, O::End], vec![]),
        (
            "siblings",
            body(0, &[2, 0x40, 1, 0x0b, 3, 0x40, 1, 0x0b, 0x0b]),
            vec![
                O::Block {
                    kind: K::Block,
                    result: None,
                    end: 2,
                    alternative: None,
                },
                O::Nop,
                O::End,
                O::Block {
                    kind: K::Loop,
                    result: None,
                    end: 5,
                    alternative: None,
                },
                O::Nop,
                O::End,
                O::End,
            ],
            vec![],
        ),
        (
            "nested",
            body(
                0,
                &[
                    2, 0x40, 3, 0x40, 0x41, 0, 4, 0x40, 1, 5, 1, 0x0b, 0x0b, 0x0b, 0x0b,
                ],
            ),
            vec![
                O::Block {
                    kind: K::Block,
                    result: None,
                    end: 9,
                    alternative: None,
                },
                O::Block {
                    kind: K::Loop,
                    result: None,
                    end: 8,
                    alternative: None,
                },
                O::Const(Value::I32(0)),
                O::Block {
                    kind: K::If,
                    result: None,
                    end: 7,
                    alternative: Some(5),
                },
                O::Nop,
                O::Else { end: 7 },
                O::Nop,
                O::End,
                O::End,
                O::End,
                O::End,
            ],
            vec![],
        ),
        (
            "br_table",
            body(
                1,
                &[
                    2, 0x40, 3, 0x40, 0x41, 0, 0x0e, 3, 0, 1, 2, 2, 0x0b, 0x0b, 0x0b,
                ],
            ),
            vec![
                O::Block {
                    kind: K::Block,
                    result: None,
                    end: 5,
                    alternative: None,
                },
                O::Block {
                    kind: K::Loop,
                    result: None,
                    end: 4,
                    alternative: None,
                },
                O::Const(Value::I32(0)),
                O::BrTable {
                    first: 0,
                    count: 3,
                    default: 2,
                },
                O::End,
                O::End,
                O::End,
            ],
            vec![0, 1, 2],
        ),
    ];
    for (label, helper, expected, targets) in cases {
        hooks(Hooks::default());
        let bytes = fixture(0, &helper, 100);
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
        elision_enable(&c, true);
        let p = pin(&mut cache, &mut c, 34, None).unwrap();
        let view = cache.view(&p, &mut c, None).unwrap();
        assert_eq!(
            view.instructions
                .iter()
                .map(|i| i.operation.clone())
                .collect::<Vec<_>>(),
            expected,
            "{label}"
        );
        assert_eq!(view.branch_targets, targets);
        assert_eq!(view.locals.len(), usize::from(label == "br_table"));
        cache
            .release(p, &mut c, None)
            .map_err(|e| e.failure)
            .unwrap();
        let o = elision_finish_observation(&c);
        assert_eq!(o.dirty_passes, [1, 1]);
        assert_eq!(o.stage_work[CacheStep::ScanReset as usize], 0);
        assert_eq!(o.stage_work[CacheStep::BuildReset as usize], 0);
        println!(
            "ELISION_DIRTY case={label} dirtied_slots_per_pass=512 passes={:?} reset_credits=[0,0]",
            o.dirty_passes
        );
        finish(cache, c);
    }
    for depth in [379, 512] {
        hooks(Hooks::default());
        let mut code = Vec::new();
        for _ in 1..depth {
            code.extend([2, 0x40]);
        }
        code.extend(std::iter::repeat_n(0x0b, depth));
        let helper = body(0, &code);
        let bytes = fixture(0, &helper, 100);
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
        elision_enable(&c, true);
        let p = pin(&mut cache, &mut c, 34, None).unwrap();
        let view = cache.view(&p, &mut c, None).unwrap();
        assert_eq!(view.instructions.len(), 2 * depth - 1);
        for i in 0..depth - 1 {
            assert_eq!(
                view.instructions[i].operation,
                O::Block {
                    kind: K::Block,
                    result: None,
                    end: 2 * depth - 3 - i,
                    alternative: None
                }
            );
        }
        assert!(view.instructions[depth - 1..]
            .iter()
            .all(|i| i.operation == O::End));
        cache
            .release(p, &mut c, None)
            .map_err(|e| e.failure)
            .unwrap();
        let o = elision_finish_observation(&c);
        assert_eq!(o.dirty_passes, [1, 1]);
        // Reuse the very same owner and deep stale arena for an ordinary flat
        // miss. Do not redirty here: this specifically tests deep-to-shallow reuse.
        let p = pin(&mut cache, &mut c, 35, None).unwrap();
        let view = cache.view(&p, &mut c, None).unwrap();
        assert_eq!(view.instructions.len(), 1);
        assert_eq!(view.instructions[0].operation, O::End);
        cache
            .release(p, &mut c, None)
            .map_err(|e| e.failure)
            .unwrap();
        println!("ELISION_DIRTY depth={depth} inclusive=true deep_to_shallow_same_owner=true");
        finish(cache, c);
    }
    let mut code = Vec::new();
    for _ in 0..512 {
        code.extend([2, 0x40]);
    }
    code.extend(std::iter::repeat_n(0x0b, 513));
    let rejected = validate_swift_reactor(
        &fixture(0, &body(0, &code), 100),
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .err()
    .expect("depth513 rejected by complete validation");
    println!("ELISION_DIRTY depth=513 validation_rejection={rejected:?}");
}
#[test]
fn reset_elision_hostile_inactive_malformed_controls() {
    hooks(Hooks::default());
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (c, mut cache) = new(&bytes, SwiftRunBudget::default());
    for (body, expected) in [
        (&[0, 5, 0x0b][..], "decode_else"),
        (&[0, 4, 0x40, 5, 5, 0x0b, 0x0b][..], "decode_else"),
        (&[0, 2, 0x40][..], "decode_end"),
        (&[0, 2, 0x40, 1][..], "decode_end"),
        (&[0, 0x0b, 1][..], "decode_trailing"),
    ] {
        assert_eq!(
            inspection::elision_malformed(&mut cache, body),
            [expected; 2]
        );
    }
    inspection::elision_dirty_owner(&mut cache);
    finish(cache, c);
    println!(
        "ELISION_MALFORMED cases=5 passes_per_case=2 actual_owner_slots=512 typed_failures=true"
    );
}

#[test]
fn reset_elision_boundary_precedence_and_sticky() {
    hooks(Hooks::default());
    let bytes = fixture(0, &body(1, &[0, 0x0e, 2, 0, 0, 0, 0x0b]), 29);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    hooks(Hooks::default());
    elision_enable(&c, false);
    let p = pin(&mut cache, &mut c, 34, None).unwrap();
    let observed = elision_finish_observation(&c);
    cache
        .release(p, &mut c, None)
        .map_err(|e| e.failure)
        .unwrap();
    finish(cache, c);
    for (index, step) in [CacheStep::ScanReset, CacheStep::BuildReset]
        .into_iter()
        .enumerate()
    {
        let (ordinal, credits) = observed.boundaries[index].expect("ordinary boundary observed");
        for expired in [false, true] {
            for cancelled in [false, true] {
                hooks(Hooks::default());
                let (mut c, mut cache) = new(
                    &bytes,
                    SwiftRunBudget {
                        cache_work: credits,
                        deadline_ms: if expired {
                            20
                        } else {
                            SwiftRunBudget::default().deadline_ms
                        },
                        ..SwiftRunBudget::default()
                    },
                );
                hooks(Hooks {
                    cancel: cancelled.then_some(ordinal),
                    pause: expired.then_some(step),
                    ..Hooks::default()
                });
                let f = pin(&mut cache, &mut c, 34, None).unwrap_err();
                hooks(Hooks::default());
                assert_eq!(
                    f.kind,
                    if cancelled {
                        SwiftRunFailureKind::Cancelled
                    } else if expired {
                        SwiftRunFailureKind::Deadline
                    } else {
                        SwiftRunFailureKind::WorkExhausted
                    }
                );
                assert_eq!(c.usage(None).cache_work, credits);
                assert_eq!(c.usage(None).live.active_pins.current, 0);
                assert_eq!(c.usage(None).live.cache_entries.current, 0);
                assert_eq!(cache.usage().decodes, 0);
                assert_eq!(c.check_with_wasi(cache_cursor(), None).unwrap_err(), f);
                let before = c.usage(None);
                let (again, stats) = measure(|| pin(&mut cache, &mut c, 34, None));
                assert_eq!(again.unwrap_err(), f);
                assert_eq!(stats.attempts, 0);
                assert_eq!(c.usage(None).cache_work, before.cache_work);
                assert_eq!(c.usage(None).reservations, before.reservations);
                println!("ELISION_PRECEDENCE boundary={step:?} credits={credits} expired={expired} cancelled={cancelled} first={:?} sticky=true publication=0",f.kind);
                finish(cache, c);
            }
        }
    }
}

// Selected bounded resident-index controls. The oracle walks actual owner slots
// independently and compares every chain membership with the resident set.
fn resident_assert_index(cache: &SwiftFunctionCache) {
    let index = inspection::resident_index(cache);
    assert_eq!(index.len(), 192);
    let slots = inspection::elision_slots(cache);
    let mut seen = [false; 64];
    for bucket in 0..128 {
        let mut node = index[bucket];
        let mut count = 0;
        while node != 0 {
            assert!(count < 64, "unbounded or cyclic chain");
            let slot = usize::from(node - 1);
            assert!(slot < slots.len());
            assert!(!seen[slot]);
            seen[slot] = true;
            let function = slots[slot][1];
            assert_ne!(function, u64::MAX);
            assert_eq!(
                (((function * 0x9e37_79b9) & 0xffff_ffff) >> 25) as usize,
                bucket
            );
            node = index[128 + slot];
            count += 1;
        }
    }
    for (slot, actual) in slots.iter().enumerate() {
        assert_eq!(seen[slot], actual[1] != u64::MAX);
        if !seen[slot] {
            assert_eq!(index[128 + slot], 0);
        }
    }
    assert!(index[128 + slots.len()..].iter().all(|link| *link == 0));
}
fn resident_seed(c: &mut RuntimeControl, cache: &mut SwiftFunctionCache) {
    for function in [34, 178, 267] {
        let p = pin(cache, c, function, None).unwrap();
        cache.release(p, c, None).map_err(|e| e.failure).unwrap();
        resident_assert_index(cache);
    }
}
#[test]
fn resident_index_collision_delete_head_middle_tail_and_reinsert() {
    // These four independently calculated identities share bucket1.
    for victim in [267, 178, 34] {
        hooks(Hooks::default());
        let bytes = fixture(0, &[0, 0x0b], 500);
        let (mut c, mut cache) = new(
            &bytes,
            SwiftRunBudget {
                cache_entries: 3,
                ..SwiftRunBudget::default()
            },
        );
        resident_seed(&mut c, &mut cache);
        let victim_slot = inspection::elision_slots(&cache)
            .iter()
            .find(|s| s[1] == victim)
            .unwrap()[0];
        for function in [34, 178, 267]
            .into_iter()
            .filter(|f| u64::from(*f) != victim)
        {
            let (p, allocations) = measure(|| pin(&mut cache, &mut c, function, None).unwrap());
            assert_eq!(allocations.attempts, 0);
            cache
                .release(p, &mut c, None)
                .map_err(|e| e.failure)
                .unwrap();
        }
        let p = pin(&mut cache, &mut c, 411, None).unwrap();
        assert_eq!(cache.view(&p, &mut c, None).unwrap().function, 411);
        assert_eq!(cache.usage().evictions, 1);
        assert_eq!(
            inspection::elision_slots(&cache)[victim_slot as usize][1],
            411
        );
        resident_assert_index(&cache);
        cache
            .release(p, &mut c, None)
            .map_err(|e| e.failure)
            .unwrap();
        let p = pin(&mut cache, &mut c, victim as u32, None).unwrap();
        assert_eq!(
            cache.view(&p, &mut c, None).unwrap().function,
            victim as u32
        );
        resident_assert_index(&cache);
        cache
            .release(p, &mut c, None)
            .map_err(|e| e.failure)
            .unwrap();
        finish(cache, c);
        println!("RESIDENT collision victim={victim} removed/reused/reinserted cleanup=zero");
    }
}
#[test]
fn resident_index_every_collision_replacement_work_and_cancel_boundary() {
    for victim in [34, 178, 267] {
        hooks(Hooks::default());
        let bytes = fixture(0, &[0, 0x0b], 500);
        let budget = SwiftRunBudget {
            cache_entries: 3,
            ..SwiftRunBudget::default()
        };
        let (mut c, mut cache) = new(&bytes, budget);
        resident_seed(&mut c, &mut cache);
        for function in [34, 178, 267].into_iter().filter(|f| *f != victim) {
            let p = pin(&mut cache, &mut c, function, None).unwrap();
            cache
                .release(p, &mut c, None)
                .map_err(|e| e.failure)
                .unwrap();
        }
        let base = c.usage(None).cache_work;
        hooks(Hooks::default());
        let p = pin(&mut cache, &mut c, 411, None).unwrap();
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
                &bytes,
                SwiftRunBudget {
                    cache_work: base + prefix,
                    ..budget
                },
            );
            resident_seed(&mut c, &mut cache);
            for function in [34, 178, 267].into_iter().filter(|f| *f != victim) {
                let p = pin(&mut cache, &mut c, function, None).unwrap();
                cache
                    .release(p, &mut c, None)
                    .map_err(|e| e.failure)
                    .unwrap();
            }
            let failure = pin(&mut cache, &mut c, 411, None).unwrap_err();
            assert_eq!(failure.resource, Some(SwiftRunResource::CacheWork));
            assert_eq!(c.usage(None).live.active_pins.current, 0);
            resident_assert_index(&cache);
            let before = c.usage(None);
            assert_eq!(
                pin(&mut cache, &mut c, 411, None).unwrap_err().kind,
                failure.kind
            );
            review_assert_same_control_effects(before, c.usage(None));
            finish(cache, c);
        }
        for ordinal in 0..checks {
            hooks(Hooks::default());
            let (mut c, mut cache) = new(&bytes, budget);
            resident_seed(&mut c, &mut cache);
            for function in [34, 178, 267].into_iter().filter(|f| *f != victim) {
                let p = pin(&mut cache, &mut c, function, None).unwrap();
                cache
                    .release(p, &mut c, None)
                    .map_err(|e| e.failure)
                    .unwrap();
            }
            hooks(Hooks {
                cancel: Some(ordinal),
                ..Hooks::default()
            });
            assert_eq!(
                pin(&mut cache, &mut c, 411, None).unwrap_err().kind,
                SwiftRunFailureKind::Cancelled
            );
            hooks(Hooks::default());
            assert_eq!(c.usage(None).live.active_pins.current, 0);
            resident_assert_index(&cache);
            finish(cache, c);
        }
        println!("RESIDENT every replacement victim={victim} work_prefixes={credits} cancellation_checks={checks} original_failure_sticky=true cleanup=zero");
    }
}

#[test]
fn resident_index_invalid_slot_empty_link_wrong_bucket_cycle_fail_closed() {
    for case in 0..4 {
        hooks(Hooks::default());
        let bytes = fixture(0, &[0, 0x0b], 500);
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
        resident_seed(&mut c, &mut cache);
        let bucket = (((34u64 * 0x9e37_79b9) & 0xffff_ffff) >> 25) as usize;
        let head = inspection::resident_index(&cache)[bucket];
        match case {
            0 => inspection::corrupt_index(&mut cache, bucket, 255),
            1 => inspection::corrupt_index(&mut cache, 128 + usize::from(head - 1), 64),
            2 => {
                let p = pin(&mut cache, &mut c, 35, None).unwrap();
                cache
                    .release(p, &mut c, None)
                    .map_err(|e| e.failure)
                    .unwrap();
                inspection::corrupt_index(&mut cache, bucket, 4);
            }
            _ => inspection::corrupt_index(&mut cache, 128 + usize::from(head - 1), head),
        }
        let failure = pin(&mut cache, &mut c, 34, None).unwrap_err();
        assert_eq!(failure.kind, SwiftRunFailureKind::DecoderMismatch);
        assert_eq!(cache.usage().decodes, if case == 2 { 4 } else { 3 });
        assert_eq!(c.usage(None).live.active_pins.current, 0);
        finish(cache, c);
        println!(
            "RESIDENT corrupt case={case} code={} failclosed cleanup=zero",
            failure.code
        );
    }
}
#[test]
fn resident_index_all_pinned_exact_capacity_and_empty_links() {
    hooks(Hooks::default());
    let bytes = fixture(0, &[0, 0x0b], 500);
    let (mut c, mut cache) = new(
        &bytes,
        SwiftRunBudget {
            cache_entries: 3,
            ..SwiftRunBudget::default()
        },
    );
    let a = pin(&mut cache, &mut c, 34, None).unwrap();
    let b = pin(&mut cache, &mut c, 178, None).unwrap();
    let d = pin(&mut cache, &mut c, 267, None).unwrap();
    let before = inspection::resident_index(&cache).to_vec();
    assert_eq!(
        pin(&mut cache, &mut c, 411, None).unwrap_err().code,
        "all_entries_pinned"
    );
    assert_eq!(inspection::resident_index(&cache), before);
    resident_assert_index(&cache);
    for p in [a, b, d] {
        cache
            .release(p, &mut c, None)
            .map_err(|e| e.failure)
            .unwrap();
    }
    finish(cache, c);
    println!("RESIDENT all_pinned original_index_retained=true terminal_release=true cleanup=zero");
}

#[test]
fn resident_index_inclusive_64_node_chain_and_cycle_bound() {
    hooks(Hooks::default());
    let functions: Vec<u32> = (34..12034)
        .filter(|f| {
            ((u64::from(*f) * 0x9e37_79b9) & 0xffff_ffff) >> 25
                == ((34u64 * 0x9e37_79b9) & 0xffff_ffff) >> 25
        })
        .take(64)
        .collect();
    assert_eq!(functions.len(), 64);
    let bytes = fixture(0, &[0, 0x0b], 12000);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    for function in &functions {
        let p = pin(&mut cache, &mut c, *function, None).unwrap();
        cache
            .release(p, &mut c, None)
            .map_err(|e| e.failure)
            .unwrap();
    }
    resident_assert_index(&cache);
    let before = c.usage(None).cache_work;
    let p = pin(&mut cache, &mut c, functions[0], None).unwrap();
    assert_eq!(cache.view(&p, &mut c, None).unwrap().function, functions[0]);
    let hit_work = c.usage(None).cache_work - before;
    assert_eq!(hit_work, 260); // two ordinary headers plus hash/head plus4*64 nodes.
    cache
        .release(p, &mut c, None)
        .map_err(|e| e.failure)
        .unwrap();
    let bucket = (((34u64 * 0x9e37_79b9) & 0xffff_ffff) >> 25) as usize;
    let head = inspection::resident_index(&cache)[bucket];
    inspection::corrupt_index(&mut cache, 128, head); // tail slot0 now closes a64-node cycle.
    assert_eq!(
        pin(&mut cache, &mut c, functions[0], None)
            .unwrap_err()
            .code,
        "swift_cache_index_cycle"
    );
    finish(cache, c);
    println!("RESIDENT chain64 inclusive=true full_chain_hit_work={hit_work} adversarial_cost_not_discounted=true cycle_failclosed=true cleanup=zero");
}

#[test]
fn resident_index_finite_cost_fixture() {
    hooks(Hooks::default());
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
    let constructor = c.usage(None).cache_work;
    for function in 34..98 {
        let p = pin(&mut cache, &mut c, function, None).unwrap();
        cache
            .release(p, &mut c, None)
            .map_err(|e| e.failure)
            .unwrap();
    }
    let cold = c.usage(None).cache_work - constructor;
    let before = c.usage(None).cache_work;
    let (_, allocations) = measure(|| {
        for _ in 0..4 {
            for function in 34..98 {
                let p = pin(&mut cache, &mut c, function, None).unwrap();
                assert_eq!(cache.view(&p, &mut c, None).unwrap().function, function);
                cache
                    .release(p, &mut c, None)
                    .map_err(|e| e.failure)
                    .unwrap();
            }
        }
    });
    assert_eq!(allocations.attempts, 0);
    assert_eq!(cache.usage().hits, 256);
    assert_eq!(cache.usage().misses, 64);
    assert_eq!(cache.usage().evictions, 0);
    let hits = c.usage(None).cache_work - before;
    println!("RESIDENT_COST {{\"constructorWork\":{constructor},\"cold64Work\":{cold},\"hit256Work\":{hits},\"fixedReserved\":{},\"residentBytes\":{},\"hitAllocatorRequests\":{},\"slots\":{:?}}}",cache.usage().fixed_reserved,cache.usage().resident_bytes,allocations.attempts,inspection::elision_slots(&cache));
    finish(cache, c);
}

#[test]
fn plan_reuse_observation() {
    use crate::experimental::cache::Operation as O;
    for wide in [false, true] {
        let helper = body(1, &[0x41, 7, 0x21, 0, 0x20, 0, 0x1a, 0x0b]);
        let bytes = if wide {
            plan_reuse_wide_fixture(&helper, 600)
        } else {
            fixture(0, &helper, 600)
        };
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget::default());
        let fixed = cache.usage().fixed_reserved;
        let start = c.usage(None).cache_work;
        let mut credits = vec![];
        for sweep in 0..3 {
            let begin = c.usage(None).cache_work;
            for f in 34..130 {
                let p = pin(&mut cache, &mut c, f, None).unwrap();
                let v = cache.view(&p, &mut c, None).unwrap();
                if f == 34 {
                    let operations: Vec<_> =
                        v.instructions.iter().map(|x| x.operation.clone()).collect();
                    assert_eq!(v.locals, &[Type::I32]);
                    assert_eq!(
                        operations,
                        vec![
                            O::Const(Value::I32(7)),
                            O::LocalSet(0),
                            O::LocalGet(0),
                            O::Drop,
                            O::End
                        ]
                    );
                    assert!(v.branch_targets.is_empty());
                    println!(
                        "PLAN_IR wide={wide} sweep={sweep} operations={operations:?} offsets={:?}",
                        v.instructions
                            .iter()
                            .map(|x| x.offset - v.body_offset)
                            .collect::<Vec<_>>()
                    );
                }
                cache
                    .release(p, &mut c, None)
                    .map_err(|e| e.failure)
                    .unwrap();
            }
            credits.push(c.usage(None).cache_work - begin);
        }
        assert_eq!(cache.usage().decodes, 288);
        assert_eq!(cache.usage().evictions, 224);
        assert!(c.usage(None).reservations.peak_tickets <= 86);
        println!("PLAN_COST wide={wide} fixed={fixed} constructor_work={start} sweeps={credits:?} usage={:?} tickets={}/{}",cache.usage(),c.usage(None).reservations.live_tickets,c.usage(None).reservations.peak_tickets);
        println!(
            "PLAN_LRU wide={wide} slots={:?}",
            inspection::elision_slots(&cache)
        );
        finish(cache, c);
    }
}

use super::cache::plan_inspection as pi;
fn plan_reuse_release(cache: &mut SwiftFunctionCache, c: &mut RuntimeControl, f: u32) {
    let p = pin(cache, c, f, None).unwrap();
    cache.release(p, c, None).map_err(|e| e.failure).unwrap();
}
fn plan_reuse_seed(bytes: &[u8], budget: SwiftRunBudget) -> (RuntimeControl, SwiftFunctionCache) {
    let (mut c, mut cache) = new(bytes, budget);
    plan_reuse_release(&mut cache, &mut c, 34);
    plan_reuse_release(&mut cache, &mut c, 35);
    assert_eq!(pi::key(&cache, 34), Some(34));
    (c, cache)
}
fn plan_reuse_primary(a: SwiftRunFailure, b: SwiftRunFailure) {
    assert_eq!(
        (
            a.kind,
            a.code,
            a.function,
            a.offset,
            a.resource,
            a.attempted,
            a.limit
        ),
        (
            b.kind,
            b.code,
            b.function,
            b.offset,
            b.resource,
            b.attempted,
            b.limit
        )
    );
}
#[test]
fn plan_reuse_shapes_and_admission() {
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
    let (result, stats) = measure(|| construct(&mut c, a, None));
    let cache = result.unwrap();
    assert_eq!(stats.attempts, 5);
    assert_eq!(c.budget(), SwiftRunBudget::default());
    assert_eq!(c.usage(None).reservations.live_tickets, 9);
    println!(
        "PLAN_SHAPE {:?} constructor_allocations={stats:?} fixed={} cleanup={:?}",
        pi::shape(),
        cache.usage().fixed_reserved,
        cache_cleanup_temporary_bytes()
    );
    assert_eq!(pi::count(&cache), 0);
    finish(cache, c);
}
#[test]
fn plan_reuse_collisions_and_independent_identity() {
    let bytes = fixture(0, &body(1, &[0x0b]), 600);
    let budget = SwiftRunBudget {
        cache_entries: 1,
        ..SwiftRunBudget::default()
    };
    let (mut c, mut cache) = new(&bytes, budget);
    plan_reuse_release(&mut cache, &mut c, 34);
    assert_eq!(pi::key(&cache, 34), Some(34));
    plan_reuse_release(&mut cache, &mut c, 546);
    assert_eq!(pi::key(&cache, 34), Some(546));
    plan_reuse_release(&mut cache, &mut c, 34);
    assert_eq!(pi::key(&cache, 546), Some(34));
    plan_reuse_release(&mut cache, &mut c, 35);
    let ((r, scans), stats) = measure(|| {
        hooks(Hooks::default());
        let r = pin(&mut cache, &mut c, 34, None).unwrap();
        (r, HOOKS.with(|h| h.get().steps[CacheStep::Scan as usize]))
    });
    assert_eq!(scans, 0);
    assert_eq!(stats.attempts, 2);
    cache
        .release(r, &mut c, None)
        .map_err(|e| e.failure)
        .unwrap();
    finish(cache, c);
    let (c, cache) = new(&bytes, budget);
    assert_eq!(pi::count(&cache), 0);
    finish(cache, c);
    for field in 0..4 {
        let (mut c, mut cache) = plan_reuse_seed(&bytes, budget);
        pi::corrupt(&mut cache, 34, field);
        let f = pin(&mut cache, &mut c, 34, None).unwrap_err();
        assert_eq!(f.kind, SwiftRunFailureKind::DecoderMismatch);
        assert_eq!(
            f.code,
            if field < 3 {
                "swift_plan_identity"
            } else {
                "decode_count_mismatch"
            }
        );
        let work = c.usage(None).cache_work;
        let second = pin(&mut cache, &mut c, 35, None).unwrap_err();
        plan_reuse_primary(f, second);
        assert_eq!(c.usage(None).cache_work, work);
        assert_eq!(c.usage(None).live.active_pins.current, 0);
        finish(cache, c);
    }
    let (c, mut cache) = plan_reuse_seed(&bytes, budget);
    let (mut other, other_cache) = new(&bytes, budget);
    let before = pi::count(&cache);
    let (r, stats) = measure(|| pin(&mut cache, &mut other, 34, None));
    assert!(r.is_err());
    assert_eq!(stats.attempts, 0);
    assert_eq!(pi::count(&cache), before);
    finish(other_cache, other);
    finish(cache, c);
}
#[test]
fn plan_reuse_constructor_all_boundaries() {
    let bytes = fixture(0, &[0, 0x0b], 29);
    hooks(Hooks::default());
    let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
    hooks(Hooks::default());
    let cache = construct(&mut c, a, None).unwrap();
    let checks = HOOKS.with(|h| h.get().checks);
    let credits = c.usage(None).cache_work;
    hooks(Hooks::default());
    finish(cache, c);
    for ordinal in 0..5 {
        let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
        let (r, s) = measure_extended(Some(ordinal), || construct(&mut c, a, None));
        assert!(r.is_err());
        assert_eq!(s.injected_failures, 1);
        assert_eq!(c.usage(None).reservations.cache.current, 0);
        assert_eq!(
            c.finish_owned_cleanup(None).reservations.combined.current,
            0
        );
        let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
        hooks(Hooks {
            capacity: Some(ordinal),
            ..Hooks::default()
        });
        let f = construct(&mut c, a, None).err().unwrap();
        hooks(Hooks::default());
        assert_eq!(f.resource, Some(SwiftRunResource::ExactCapacity));
        assert_eq!(c.usage(None).reservations.cache.current, 0);
        assert_eq!(
            c.finish_owned_cleanup(None).reservations.combined.current,
            0
        );
    }
    for work in 0..credits {
        let (mut c, a) = adopt(
            &bytes,
            SwiftRunBudget {
                cache_work: work,
                ..SwiftRunBudget::default()
            },
        );
        let r = construct(&mut c, a, None);
        assert!(r.is_err(), "work {work}");
        assert_eq!(c.usage(None).reservations.cache.current, 0);
        assert_eq!(
            c.finish_owned_cleanup(None).reservations.combined.current,
            0
        );
    }
    for ordinal in 0..checks {
        let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
        hooks(Hooks {
            cancel: Some(ordinal),
            ..Hooks::default()
        });
        let r = construct(&mut c, a, None);
        hooks(Hooks::default());
        assert!(r.is_err(), "check {ordinal}");
        assert_eq!(c.usage(None).reservations.cache.current, 0);
        assert_eq!(
            c.finish_owned_cleanup(None).reservations.combined.current,
            0
        );
    }
    println!("PLAN_CONSTRUCTOR allocation=5 capacity=5 shorter_work={credits} cancellation_checks={checks} cleanup_zero=true");
}
#[test]
fn plan_reuse_cold_cached_all_boundaries() {
    let bytes = fixture(0, &body(1, &[0, 0x0e, 1, 0, 0, 0x0b]), 100);
    let base = SwiftRunBudget {
        cache_entries: 1,
        ..SwiftRunBudget::default()
    };
    for cached in [false, true] {
        hooks(Hooks::default());
        let (mut c, mut cache) = if cached {
            plan_reuse_seed(&bytes, base)
        } else {
            new(&bytes, base)
        };
        let before = c.usage(None).cache_work;
        hooks(Hooks::default());
        let p = pin(&mut cache, &mut c, 34, None).unwrap();
        let checks = HOOKS.with(|h| h.get().checks);
        let work = c.usage(None).cache_work - before;
        hooks(Hooks::default());
        cache
            .release(p, &mut c, None)
            .map_err(|e| e.failure)
            .unwrap();
        finish(cache, c);
        for shorter in 0..work {
            hooks(Hooks::default());
            let (mut c, mut cache) = if cached {
                plan_reuse_seed(
                    &bytes,
                    SwiftRunBudget {
                        cache_work: before + shorter,
                        ..base
                    },
                )
            } else {
                new(
                    &bytes,
                    SwiftRunBudget {
                        cache_work: before + shorter,
                        ..base
                    },
                )
            };
            let f = pin(&mut cache, &mut c, 34, None).unwrap_err();
            assert_eq!(f.resource, Some(SwiftRunResource::CacheWork));
            let retained = pi::key(&cache, 34);
            assert!(retained.is_none() || retained == Some(34));
            let stopped = c.usage(None).cache_work;
            plan_reuse_primary(f, pin(&mut cache, &mut c, 34, None).unwrap_err());
            assert_eq!(c.usage(None).cache_work, stopped);
            finish(cache, c);
        }
        for ordinal in 0..checks {
            let (mut c, mut cache) = if cached {
                plan_reuse_seed(&bytes, base)
            } else {
                new(&bytes, base)
            };
            hooks(Hooks {
                cancel: Some(ordinal),
                ..Hooks::default()
            });
            let f = pin(&mut cache, &mut c, 34, None).unwrap_err();
            hooks(Hooks::default());
            assert_eq!(f.kind, SwiftRunFailureKind::Cancelled);
            assert_eq!(c.usage(None).live.active_pins.current, 0);
            plan_reuse_primary(f, pin(&mut cache, &mut c, 34, None).unwrap_err());
            finish(cache, c);
        }
        for ordinal in 0..3 {
            let (mut c, mut cache) = if cached {
                plan_reuse_seed(&bytes, base)
            } else {
                new(&bytes, base)
            };
            let (r, s) = measure_extended(Some(ordinal), || pin(&mut cache, &mut c, 34, None));
            assert!(r.is_err());
            assert_eq!(s.injected_failures, 1);
            assert_eq!(pi::key(&cache, 34), Some(34));
            assert_eq!(c.usage(None).live.active_pins.current, 0);
            finish(cache, c);
        }
        println!("PLAN_OPERATION cached={cached} shorter_work={work} cancellation_checks={checks} allocations=3 cleanup_zero=true");
    }
}

// Test-only section builder: every body is admitted by the real complete validator.
fn plan_reuse_wide_fixture(helper: &[u8], definitions: usize) -> Vec<u8> {
    let mut module = fixture(0, helper, definitions);
    let mut cursor = 8;
    loop {
        let start = cursor;
        let id = module[cursor];
        cursor += 1;
        let mut size = 0usize;
        let mut shift = 0;
        loop {
            let b = module[cursor];
            cursor += 1;
            size |= ((b & 127) as usize) << shift;
            if b & 128 == 0 {
                break;
            }
            shift += 7;
        }
        if id == 10 {
            module.truncate(start);
            let mut code = vec![];
            uint(definitions as u32, &mut code);
            let mut rich = vec![0, 0x01];
            rich.extend(std::iter::repeat_n(0x01, 511));
            rich.push(0x0b);
            for index in 0..definitions {
                let b = if index == 28 {
                    &[0, 0x41, 0, 0x0b][..]
                } else if index == 0 {
                    helper
                } else {
                    &rich
                };
                uint(b.len() as u32, &mut code);
                code.extend_from_slice(b);
            }
            section(10, &code, &mut module);
            return module;
        }
        cursor += size;
    }
}

#[test]
fn plan_reuse_header_lifetime_and_narrow_admission() {
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, cache) = new(&bytes, SwiftRunBudget::default());
    let mut owned = Some(cache);
    let (tail, s) = measure(|| SwiftFunctionCache::cleanup(&mut owned, &mut c, None).unwrap());
    assert!(owned.is_none());
    assert!(s.freed_bytes >= pi::shape().1);
    assert_eq!(
        pi::tail_usage(&tail).reservations.cache.current,
        cache_header_bytes().unwrap()
    );
    let mut result = None;
    tail.complete(owned, &mut result);
    assert_eq!(c.usage(None).reservations.cache.current, 0);
    assert_eq!(
        c.finish_owned_cleanup(None).reservations.combined.current,
        0
    );
    // The additional table cannot silently outgrow a narrowed cache ceiling.
    for limit in [0, pi::shape().1 - 1, cache_header_bytes().unwrap() - 1] {
        let (mut c, a) = adopt(
            &bytes,
            SwiftRunBudget {
                cache_bytes: limit,
                ..SwiftRunBudget::default()
            },
        );
        assert!(construct(&mut c, a, None).is_err());
        assert_eq!(c.usage(None).reservations.cache.current, 0);
        assert_eq!(
            c.finish_owned_cleanup(None).reservations.combined.current,
            0
        );
    }
    println!("PLAN_HEADER payload_dropped_before_header=true narrowed_limits=3 cleanup_zero=true");
}
#[test]
fn plan_reuse_collision_publish_boundaries() {
    let bytes = fixture(0, &body(1, &[0x0b]), 600);
    let base = SwiftRunBudget {
        cache_entries: 1,
        ..SwiftRunBudget::default()
    };
    let (mut c, mut cache) = new(&bytes, base);
    plan_reuse_release(&mut cache, &mut c, 34);
    let begin = c.usage(None).cache_work;
    hooks(Hooks::default());
    plan_reuse_release(&mut cache, &mut c, 546);
    let checks = HOOKS.with(|h| h.get().checks);
    let credits = c.usage(None).cache_work - begin;
    let published = pi::summary(&cache, 546).unwrap();
    hooks(Hooks::default());
    finish(cache, c);
    for (is_cancel, n) in [(false, credits as usize), (true, checks)] {
        for ordinal in 0..n {
            let (mut c, mut cache) = new(
                &bytes,
                if is_cancel {
                    base
                } else {
                    SwiftRunBudget {
                        cache_work: begin + ordinal as u64,
                        ..base
                    }
                },
            );
            plan_reuse_release(&mut cache, &mut c, 34);
            let old = pi::summary(&cache, 34).unwrap();
            if is_cancel {
                hooks(Hooks {
                    cancel: Some(ordinal),
                    ..Hooks::default()
                });
            }
            let f = pin(&mut cache, &mut c, 546, None).unwrap_err();
            hooks(Hooks::default());
            let actual = pi::summary(&cache, 546).unwrap();
            assert!(
                actual == old || actual == published,
                "atomic metadata publish ordinal {ordinal}"
            );
            plan_reuse_primary(f, pin(&mut cache, &mut c, 34, None).unwrap_err());
            finish(cache, c);
        }
    }
    println!("PLAN_COLLISION shorter_work={credits} cancellation_checks={checks} atomic=true cleanup_zero=true");
}

#[test]
fn plan_reuse_cached_deadline_and_precedence() {
    let bytes = fixture(0, &body(1, &[0, 0x0e, 1, 0, 0, 0x0b]), 100);
    for step in [
        CacheStep::Lookup,
        CacheStep::BuildReset,
        CacheStep::Build,
        CacheStep::Publication,
    ] {
        for cancel in [false, true] {
            hooks(Hooks::default());
            let (mut c, mut cache) = plan_reuse_seed(
                &bytes,
                SwiftRunBudget {
                    cache_entries: 1,
                    deadline_ms: 20,
                    ..SwiftRunBudget::default()
                },
            );
            hooks(Hooks {
                pause: Some(step),
                cancel_pause: cancel,
                ..Hooks::default()
            });
            let f = pin(&mut cache, &mut c, 34, None).unwrap_err();
            hooks(Hooks::default());
            assert_eq!(
                f.kind,
                if cancel {
                    SwiftRunFailureKind::Cancelled
                } else {
                    SwiftRunFailureKind::Deadline
                }
            );
            assert_eq!(c.usage(None).live.active_pins.current, 0);
            plan_reuse_primary(f, pin(&mut cache, &mut c, 34, None).unwrap_err());
            finish(cache, c);
        }
    }
    println!("PLAN_CACHED_DEADLINE boundaries=4 precedence_pairs=4 cleanup_zero=true");
}

#[test]
fn plan_reuse_profile_envelopes_without_guest_execution() {
    use super::execution::{self,SwiftReactorInstance};
    use super::execution::frame_operations::{FrameOperationStorage,FrameCompletion};
    use crate::experimental_wasi::accounted::accounted_header_bytes;
    let bytes=fixture(0,&[0,0x0b],100);
    let max=SwiftRunBudget::default();
    let mut pair=Some(adopt(&bytes,max));
    let mut returned=Some(SwiftReactorInstance::construct(&mut pair,WasiGrants::default(),WasiBudget::default(),Instant::now(),cache_cursor()));
    let mut owner=returned.take().unwrap().unwrap();assert!(pair.is_none());drop((pair,returned));
    let constructed=owner.control.as_ref().unwrap().usage(owner.wasi.as_ref().map(AccountedWasi::usage));
    assert_eq!(constructed.reservations.live_tickets,21);
    for f in 34..98 {
        let cache=owner.cache.as_mut().unwrap();let control=owner.control.as_mut().unwrap();let wasi=owner.wasi.as_ref();
        let p=pin(cache,control,f,wasi).unwrap();cache.release(p,control,wasi).map_err(|e|e.failure).unwrap();
    }
    let resident=owner.control.as_ref().unwrap().usage(owner.wasi.as_ref().map(AccountedWasi::usage));
    assert_eq!(resident.live.cache_entries.current,64);assert_eq!(resident.reservations.live_tickets,85);
    let mut preparation=Some(owner.prepare_frames(cache_cursor()));
    let mut phase=preparation.take().unwrap().unwrap();let report=phase.drain();
    let bound=report.bound.unwrap();assert_eq!(report.usage.instructions,0);assert_eq!(report.usage.instruction_fuel,0);
    let frame_bytes=bound.admitted-bound.previous;
    assert!(matches!(phase.complete(FrameOperationStorage{preparation,entry:None,returned:None,drained:Some(report),controlled:None}),FrameCompletion::Completed));
    let floor=foundation_construction_bytes().unwrap();
    let construction=execution::construction_bytes().unwrap();
    let execution_header=execution::execution_header_bytes().unwrap();
    // A conservative simultaneous ceiling calculation, not a claim that every
    // independent category ceiling is reachable in a valid module.
    let categories=max.source_bytes+max.metadata_bytes+max.cache_bytes+max.state_bytes;
    let wasi=accounted_header_bytes().unwrap()+4*65536;
    let shared=constructed.reservations.shared.current;
    let phase_peak=floor+construction.max(frame_bytes+cache_operation_bytes().unwrap());
    let maximum_envelope=categories+wasi+shared+phase_peak;
    println!("PLAN_PROFILE floor={floor} execution_header={execution_header} execution_construction={construction} frame_operation={frame_bytes} category_ceiling_sum={categories} wasi_max={wasi} shared={shared} conservative_combined={maximum_envelope} combined_limit={} constructed_current={} constructed_peak={} resident_current={} resident_peak={} frame_peak={} tickets={}/{}",max.combined_bytes,constructed.reservations.combined.current,constructed.reservations.combined.peak,resident.reservations.combined.current,resident.reservations.combined.peak,report.usage.reservations.combined.peak,report.usage.reservations.live_tickets,report.usage.reservations.peak_tickets);
    assert!(maximum_envelope<=max.combined_bytes);
    assert!(execution_header<=max.state_bytes);assert!(report.usage.reservations.peak_tickets<=86);
    assert_eq!(owner.control.as_ref().unwrap().budget(),max);
    let mut owned=Some(owner);let mut cleanup=Some(SwiftReactorInstance::cleanup_owned(&mut owned));
    let tail=cleanup.take().unwrap().unwrap();let mut failure=None;let mut usage=None;
    tail.complete((owned,cleanup),&mut failure,&mut usage);
    let final_usage=usage.unwrap();assert_eq!(final_usage.reservations.combined.current,0);assert_eq!(final_usage.reservations.live_tickets,0);assert!(failure.is_none());
    println!("PLAN_PROFILE cleanup_zero=true guest_instructions=0 initializes=0 invokes=0");
}

#[test]
fn full_regression_observe_cache_fixture_shapes() {
    let bytes = fixture(0, &[0, 0x0b], 100);
    let (mut c, a) = adopt(&bytes, SwiftRunBudget::default());
    let (cache, stats) = measure(|| construct(&mut c, a, None).unwrap());
    println!(
        "REGRESSION_CACHE stats={stats:?} header={} fixed={} work={}",
        cache_header_bytes().unwrap(),
        c.usage(None).reservations.cache.current,
        c.usage(None).cache_work
    );
    assert_eq!(stats.reallocations, 0);
    finish(cache, c);
}

mod ordered_wire {
// Independently authored finite diagnostic writer; never product authority.
use std::io::{self, Write};
pub const ABSENT:u64=u64::MAX;
pub const MAX_RECORDS:u64=4_194_304;
pub const CAP:u32=1; pub const IO:u32=2; pub const CONTEXT:u32=4;
pub const BORROW:u32=8; pub const RANGE:u32=16; pub const OVERFLOW:u32=32;
pub const LIFECYCLE:u32=64; pub const CODE:u32=128; pub const GATE:u32=256;
pub const HEADER_MAGIC:u64=0x315244524f58494d;
pub const FOOTER_MAGIC:u64=0x31444e454f58494d;
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub struct Record(pub [u64;16]);
impl Record {
    pub fn new(kind:u64,phase:u64,operation:u64,function:u64)->Self {
        Self([0,kind,phase,operation,0,0,function,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,0,0,0])
    }
    pub fn encode(&self,out:&mut [u8;128]) {
        for (i,n) in self.0.iter().enumerate(){out[8*i..8*i+8].copy_from_slice(&n.to_le_bytes());}
    }
    pub fn decode(raw:&[u8;128])->Self {
        let mut words=[0;16];for (i,n) in words.iter_mut().enumerate(){*n=u64::from_le_bytes(raw[8*i..8*i+8].try_into().unwrap());}Self(words)
    }
    pub fn valid(&self,code_count:u64)->bool {
        let w=&self.0;
        if !(1..=14).contains(&w[1])||w[2]>5||w[0]==0{return false;}
        let full=w[6]<80000&&w[7]!=ABSENT&&w[8]!=ABSENT&&w[9]!=ABSENT&&w[7].checked_add(w[8]).is_some();
        let absent_body=w[7..10]==[ABSENT;3];
        let no_slots=w[10]==ABSENT&&w[11]==ABSENT&&w[12]==0;
        match w[1] {
            1=>w[3]>0&&w[6]<80000&&absent_body&&no_slots&&w[13..16]==[0;3],
            2=>w[3]>0&&full&&w[11]==ABSENT&&w[12]==0&&w[13]<=1&&w[14]==0&&w[15]==0&&if w[13]==0{w[10]==ABSENT}else{w[10]<64},
            3=>w[3]>0&&full&&no_slots&&w[13]==0&&w[14]==0&&w[15]==w[6]&511,
            4=>w[3]>0&&full&&no_slots&&w[13]<=2&&(if w[13]==1{w[14]<80000&&w[14]!=w[6]}else{w[14]==ABSENT})&&w[15]==w[6]&511,
            5=>w[3]>0&&full&&no_slots&&w[13]>0&&w[14].checked_add(w[13]).is_some_and(|n|n<=w[15]),
            6..=8=>w[3]>0&&full&&w[10]<64&&w[11]==ABSENT&&w[12]==0&&w[13]>0&&w[14..16]==[0;2],
            9|10=>w[3]>0&&full&&no_slots&&w[13]>0&&w[14..16]==[0;2],
            11=>w[3]>0&&full&&w[10]<64&&w[11]<64&&w[12]>0&&w[13]<=1&&w[14]>0&&(1..=64).contains(&w[15]),
            12=>w[3]==0&&w[6]<80000&&w[7]!=ABSENT&&w[8]==ABSENT&&w[9]!=ABSENT&&w[10]<64&&w[11]<64&&w[12]>0&&w[13]>0&&w[14]==0&&w[15]<64,
            13=>w[3]==0&&w[6]==ABSENT&&absent_body&&no_slots&&w[13]==w[2]&&w[14..16]==[0;2],
            14=>absent_body&&(w[6]==ABSENT||w[6]<80000)&&no_slots&&(1..=21).contains(&w[13])&&(1..=code_count).contains(&w[14])&&(1..=6).contains(&w[15]),
            _=>false,
        }
    }
}
pub fn encode_frame(words:&[u64;64])->[u8;512] {
    let mut bytes=[0;512];for (i,n) in words.iter().enumerate(){bytes[i*8..i*8+8].copy_from_slice(&n.to_le_bytes());}bytes
}
pub fn header(cap:u64,mask:u64,digests:[[u8;32];4])->Option<[u8;512]> {
    if cap==0||cap>MAX_RECORDS||mask==0||mask>=64||mask&33!=33{return None;}
    let mut w=[0;64]; w[..10].copy_from_slice(&[HEADER_MAGIC,1,512,128,512,cap,80000,64,512,mask]);
    let mut out=encode_frame(&w);for(i,d)in digests.iter().enumerate(){out[128+32*i..160+32*i].copy_from_slice(d);}Some(out)
}
pub fn valid_header(raw:&[u8;512])->bool {
    let word=|i:usize|u64::from_le_bytes(raw[i*8..i*8+8].try_into().unwrap());
    word(0)==HEADER_MAGIC&&word(1)==1&&word(2)==512&&word(3)==128&&word(4)==512&&
    (1..=MAX_RECORDS).contains(&word(5))&&word(6)==80000&&word(7)==64&&word(8)==512&&
    word(9)<64&&word(9)&33==33&&raw[80..128].iter().all(|b|*b==0)&&raw[256..].iter().all(|b|*b==0)
}
#[derive(Debug)]
#[repr(C)]
pub struct Writer<W:Write> {
    pub buffer:[u8;4096],pub record:[u8;128],pub stored:u64,pub attempted:u64,pub dropped:u64,
    pub used:usize,pub cap:u64,pub last_work:u64,pub last_instructions:u64,pub operation:u64,
    pub phase:u64,pub observed_mask:u64,pub expected_mask:u64,pub attempts:u64,pub code_count:u64,
    pub bindings:[u64;8],pub pin_failed:bool,pub terminal_failed:bool,pub ended:bool,pub flags:u32,pub sink:W,
}
// Every loop body executes at most 32 times, including Interrupted/short writes.
pub fn bounded_write<W:Write>(sink:&mut W,bytes:&[u8],attempts:&mut u64)->bool {
    let mut offset=0usize;
    for _ in 0..32 {
        let Some(n)=attempts.checked_add(1)else{return false;};*attempts=n;
        let result:io::Result<usize>=sink.write(&bytes[offset..]);
        match result {Ok(0)=>return false,Ok(n)=>{if n>bytes.len()-offset{return false;}offset+=n;if offset==bytes.len(){return true;}},Err(e)=>{if e.kind()!=io::ErrorKind::Interrupted{return false;}}}
    }false
}
impl<W:Write> Writer<W> {
    pub fn new(sink:W,cap:u64,mask:u64,code_count:u64,head:&[u8;512])->Option<Self> {
        if !valid_header(head)||u64::from_le_bytes(head[40..48].try_into().unwrap())!=cap||u64::from_le_bytes(head[72..80].try_into().unwrap())!=mask||code_count!=24{return None;}
        let mut out=Self {buffer:[0;4096],record:[0;128],stored:0,attempted:0,dropped:0,used:0,cap,last_work:0,last_instructions:0,operation:0,phase:0,observed_mask:1,expected_mask:mask,attempts:0,code_count,bindings:[0;8],pin_failed:false,terminal_failed:false,ended:false,flags:0,sink};
        for (i,n) in out.bindings.iter_mut().enumerate(){*n=u64::from_le_bytes(head[128+8*i..136+8*i].try_into().unwrap());}
        if !bounded_write(&mut out.sink,head,&mut out.attempts){out.flags|=IO;}Some(out)
    }
    pub fn freeze(&mut self,flags:u32){self.flags|=flags;}
    pub fn push(&mut self,mut event:Record) {
        if self.ended {return;}
        match self.attempted.checked_add(1){Some(n)=>self.attempted=n,None=>{self.flags|=OVERFLOW;return;}}
        // Actual lifecycle scalars continue after truncation; no missing Phase
        // record is invented and stored-stream coordinates stay unchanged.
        if event.0[1]==13 {
            if event.0[2]>5||event.0[13]!=event.0[2]||event.0[2]<=self.phase{self.flags|=LIFECYCLE;}
            else {self.phase=event.0[2];self.observed_mask|=1<<self.phase;}
        }
        if self.flags!=0||self.stored==self.cap {
            if self.stored==self.cap {self.flags|=CAP;}
            match self.dropped.checked_add(1){Some(n)=>self.dropped=n,None=>self.flags|=OVERFLOW};return;
        }
        event.0[0]=self.stored+1;
        let w=&event.0;
        if !event.valid(self.code_count){self.flags|=RANGE;self.dropped+=1;return;}
        if w[4]<self.last_work||w[5]<self.last_instructions||w[2]<self.phase {
            self.flags|=LIFECYCLE;self.dropped+=1;return;
        }
        if w[2]!=self.phase {self.flags|=LIFECYCLE;self.dropped+=1;return;}
        if w[1]==1 {if self.pin_failed||self.terminal_failed||w[3]!=self.operation+1 {self.flags|=LIFECYCLE;self.dropped+=1;return;}self.operation=w[3];}
        else if w[1]!=12&&w[1]!=13&&w[1]!=14&&w[3]!=self.operation {self.flags|=LIFECYCLE;self.dropped+=1;return;}
        if w[1]==14 {if w[3]==0{if self.terminal_failed{self.flags|=LIFECYCLE;self.dropped+=1;return;}self.terminal_failed=true;}else {if w[3]!=self.operation||self.pin_failed{self.flags|=LIFECYCLE;self.dropped+=1;return;}self.pin_failed=true;}}
        event.encode(&mut self.record);
        self.buffer[self.used..self.used+128].copy_from_slice(&self.record);self.used+=128;
        self.stored+=1;self.last_work=w[4];self.last_instructions=w[5];
        if self.used==4096 {self.flush_records();}
    }
    pub fn flush_records(&mut self) {
        if self.used==0||self.flags&!CAP!=0{return;}
        if !bounded_write(&mut self.sink,&self.buffer[..self.used],&mut self.attempts){self.flags|=IO;}
        self.used=0;
    }
    // Caller supplies original terminal and final-consuming ledger words only.
    pub fn finish(&mut self,mut footer:[u64;64])->[u64;64] {
        if self.ended {footer[9]|=LIFECYCLE as u64;return footer;}
        self.ended=true;self.flush_records();
        footer[0]=FOOTER_MAGIC;footer[1]=1;footer[2]=self.stored;footer[3]=self.attempted;footer[4]=self.dropped;
        footer[5]=self.stored;footer[6]=self.last_work;footer[7]=self.last_instructions;footer[8]=self.operation;
        footer[9]|=self.flags as u64;footer[15]=self.observed_mask;footer[33]=self.phase;footer[35]=self.cap;
        // attempts includes the actual terminal block after the write; wire word
        // stores the attempts before that block (closed finite bound definition).
        footer[34]=self.attempts;footer[36..44].copy_from_slice(&self.bindings);
        let bytes=encode_frame(&footer);
        if !bounded_write(&mut self.sink,&bytes,&mut self.attempts){self.flags|=IO;}
        footer
    }
}
pub fn valid_footer_fields(head:&[u8;512],raw:&[u8;512],file_bytes:u64)->bool{
    if !valid_header(head){return false;}
    let word=|i:usize|u64::from_le_bytes(raw[i*8..i*8+8].try_into().unwrap());
    let cap=u64::from_le_bytes(head[40..48].try_into().unwrap());
    let expected=u64::from_le_bytes(head[72..80].try_into().unwrap());
    let flags=word(9);
    if word(0)!=FOOTER_MAGIC||word(1)!=1||word(2)>cap||word(5)!=word(2)||word(3).checked_sub(word(2))!=Some(word(4))||flags>=512||word(35)!=cap||word(34)>4_194_336||word(10)<word(6)||word(11)<word(7)||word(15)>=64||word(33)>5||word(31)>5||word(32)>1||raw[352..].iter().any(|b|*b!=0)||raw[288..352]!=head[128..192]{return false;}
    if word(2).checked_mul(128).and_then(|n|n.checked_add(1024))!=Some(file_bytes){return false;}
    if word(12)==0 {if word(13)!=0||word(14)!=ABSENT||word(32)!=0{return false;}}
    else if word(12)>21||word(13)>24||(word(13)==0&&flags&CODE as u64==0)||!(1..=6).contains(&word(14))||word(32)!=1{return false;}
    if flags==0 {if word(4)!=0||word(15)!=expected||word(33)!=5{return false;}}
    if flags==CAP as u64&&(word(2)!=cap||word(3)<=word(2)||word(4)==0||word(15)!=expected||word(33)!=5){return false;}
    true
}
#[cfg(test)] mod tests {
    use super::*;
    #[derive(Debug)] struct Sink{bytes:[u8;16384],used:usize,quantum:usize,interrupts:usize,zero:bool,error:bool,calls:usize}
    impl Sink{fn new()->Self{Self{bytes:[0;16384],used:0,quantum:usize::MAX,interrupts:0,zero:false,error:false,calls:0}}}
    impl Write for Sink{fn write(&mut self,b:&[u8])->io::Result<usize>{self.calls+=1;if self.interrupts>0{self.interrupts-=1;return Err(io::ErrorKind::Interrupted.into());}if self.zero{return Ok(0);}if self.error{return Err(io::ErrorKind::BrokenPipe.into());}let n=b.len().min(self.quantum);self.bytes[self.used..self.used+n].copy_from_slice(&b[..n]);self.used+=n;Ok(n)}fn flush(&mut self)->io::Result<()>{Ok(())}}
    fn writer(cap:u64)->Writer<Sink>{let h=header(cap,33,[[7;32];4]).unwrap();Writer::new(Sink::new(),cap,33,24,&h).unwrap()}
    fn event()->Record{Record::new(1,0,1,40)}
    #[test]fn wire_roundtrip_closed_fields(){let mut r=event();r.0[0]=1;assert!(r.valid(24));let mut b=[0;128];r.encode(&mut b);assert_eq!(Record::decode(&b),r);for i in 7..10{let mut x=r;x.0[i]=0;assert!(!x.valid(24));}let mut x=r;x.0[15]=1;assert!(!x.valid(24));}
    #[test]fn header_closed_mutations(){let h=header(32,33,[[7;32];4]).unwrap();assert!(valid_header(&h));for i in [80,127,256,511]{let mut x=h;x[i]=1;assert!(!valid_header(&x));}for cap in [0,MAX_RECORDS+1]{assert!(header(cap,33,[[0;32];4]).is_none());}}
    #[test]fn bounded_short_write_interrupted_zero_error(){let mut s=Sink::new();s.quantum=4;s.interrupts=2;let mut a=0;assert!(bounded_write(&mut s,&[1;120],&mut a));assert_eq!(a,32);assert_eq!(s.used,120);let mut s=Sink::new();s.interrupts=33;let mut a=0;assert!(!bounded_write(&mut s,&[1;1],&mut a));assert_eq!(a,32);for zero in [false,true]{let mut s=Sink::new();s.zero=zero;s.error=!zero;let mut a=0;assert!(!bounded_write(&mut s,&[1;1],&mut a));assert_eq!(a,1);}}
    #[test]fn cap_prefix_tiny_positions(){for cap in 1..=32{let mut w=writer(cap);for n in 1..=cap+4{let mut r=event();r.0[3]=n;w.push(r);}let f=w.finish([0;64]);assert_eq!(f[2],cap);assert_eq!(f[3],cap+4);assert_eq!(f[4],4);assert_eq!(f[9],CAP as u64);assert_eq!(w.sink.used,1024+128*cap as usize);assert_eq!(w.attempts,3);}}
    #[test]fn sticky_io_never_resumes(){let mut w=writer(64);w.sink.zero=true;for n in 1..=33{let mut r=event();r.0[3]=n;w.push(r);}assert_eq!(w.flags,IO);let used=w.sink.used;w.sink.zero=false;let mut r=event();r.0[3]=34;w.push(r);assert_eq!(w.stored,32);assert_eq!(w.dropped,2);assert_eq!(w.sink.used,used);}
    #[test]fn range_lifecycle_and_overflow_sticky(){let mut w=writer(32);let mut r=event();r.0[6]=80000;w.push(r);assert_eq!(w.flags,RANGE);assert_eq!(w.attempted,w.stored+w.dropped);let mut w=writer(32);let mut r=event();r.0[3]=2;w.push(r);assert_eq!(w.flags,LIFECYCLE);let mut w=writer(32);w.attempted=u64::MAX;w.push(event());assert_eq!(w.flags,OVERFLOW);}
    #[test]fn duplicate_finish_no_second_frame(){let mut w=writer(32);w.push(event());w.finish([0;64]);let used=w.sink.used;let f=w.finish([0;64]);assert_ne!(f[9]&LIFECYCLE as u64,0);assert_eq!(w.sink.used,used);}
    #[test]fn footer_closed_fields_and_cap_lifecycle(){
        let mut w=writer(1);w.push(event());let mut p=Record::new(13,5,0,ABSENT);p.0[13]=5;w.push(p);
        let mut original=[0;64];original[14]=ABSENT;let f=w.finish(original);let h=header(1,33,[[7;32];4]).unwrap();let raw=encode_frame(&f);assert_eq!(f[9],CAP as u64);assert!(valid_footer_fields(&h,&raw,w.sink.used as u64));
        for i in [0,8,352,511]{let mut x=raw;x[i]^=1;assert!(!valid_footer_fields(&h,&x,w.sink.used as u64));}
        let mut x=f;x[2]=0;x[5]=0;assert!(!valid_footer_fields(&h,&encode_frame(&x),1024));
        let mut x=f;x[13]=1;assert!(!valid_footer_fields(&h,&encode_frame(&x),w.sink.used as u64));
    }

}

}
// Finite test-only owner. No field in RuntimeControl/cache/meter funds this.
pub(super) mod ordered_observer {
    use super::ordered_wire::*;
    use super::super::control::*;
    use std::cell::{Cell,RefCell};
    use std::fs::File;
    use std::os::unix::fs::MetadataExt;
    use std::marker::PhantomData;
    use std::rc::Rc;
    use std::sync::atomic::{AtomicU32,AtomicU64,Ordering};
    const ACTIVE:u64=1<<63;const CLOSED:u64=1<<62;const INIT:u64=1<<61;
    const COUNTS:u64=(1<<32)-1;
    static GATE_STATE:AtomicU64=AtomicU64::new(CLOSED);
    static FLAGS:AtomicU32=AtomicU32::new(0);
    static NEXT:AtomicU64=AtomicU64::new(1);
    static CURRENT:AtomicU64=AtomicU64::new(0);
    thread_local!{
        static OWNER:Cell<u64>=const{Cell::new(0)};
        static WRITER:RefCell<Option<Writer<File>>>=const{RefCell::new(None)};
    }
    pub struct DispatchGuard{coordinate:u64,dispatches:u64,ended:bool,_single:PhantomData<Rc<()>>}
    #[derive(Debug,Clone,Copy)]
    pub struct EndReceipt{pub custody:Option<Custody>,pub finalized:bool,pub flags:u32,pub stored:u64,pub attempted:u64,pub attempts_before:u64,pub attempts_after:u64,pub dispatches:u64,pub gate:u64}
    #[derive(Debug,Clone,Copy)]
    pub struct Custody{pub dev:u64,pub ino:u64,pub mode:u64,pub len:u64,pub mtime_sec:i64,pub mtime_nsec:i64,pub ctime_sec:i64,pub ctime_nsec:i64}
    impl Custody{pub fn from_metadata(m:&std::fs::Metadata)->Self{Self{dev:m.dev(),ino:m.ino(),mode:m.mode() as u64,len:m.len(),mtime_sec:m.mtime(),mtime_nsec:m.mtime_nsec(),ctime_sec:m.ctime(),ctime_nsec:m.ctime_nsec()}}}
    // Source contract: one synchronous owning thread. Only negative tests create
    // callback threads, at most 64, and join them. Thus count is <=64, never near
    // the 32-bit count carry. No CAS loop, spin, wait or overflow speculation.
    fn enter()->bool {
        let before=GATE_STATE.fetch_add(1,Ordering::AcqRel);
        if before&ACTIVE==0||before&CLOSED!=0 {GATE_STATE.fetch_sub(1,Ordering::Release);return false;}
        if before&COUNTS>=64 {FLAGS.fetch_or(GATE,Ordering::Relaxed);GATE_STATE.fetch_sub(1,Ordering::Release);return false;}
        true
    }
    fn leave(){GATE_STATE.fetch_sub(1,Ordering::Release);}
    fn owner()->bool {let expected=CURRENT.load(Ordering::Acquire);OWNER.with(|o|o.get()!=0&&o.get()==expected)}
    fn invalidate(flag:u32){FLAGS.fetch_or(flag,Ordering::Relaxed);}
    pub fn begin(writer:Writer<File>)->Option<DispatchGuard>{
        let old=GATE_STATE.load(Ordering::Acquire);
        if old!=CLOSED {if enter(){invalidate(LIFECYCLE);leave();}return None;}
        if GATE_STATE.compare_exchange(CLOSED,INIT,Ordering::AcqRel,Ordering::Acquire).is_err(){return None;}
        let coordinate=NEXT.load(Ordering::Relaxed);
        if coordinate==u64::MAX||NEXT.compare_exchange(coordinate,coordinate+1,Ordering::AcqRel,Ordering::Acquire).is_err(){GATE_STATE.fetch_or(CLOSED,Ordering::AcqRel);return None;}
        FLAGS.store(0,Ordering::Relaxed);CURRENT.store(coordinate,Ordering::Release);
        OWNER.with(|o|o.set(coordinate));WRITER.with(|w|{*w.borrow_mut()=Some(writer);});
        if GATE_STATE.compare_exchange(INIT,ACTIVE,Ordering::AcqRel,Ordering::Acquire).is_err(){GATE_STATE.fetch_or(CLOSED,Ordering::AcqRel);return None;}
        Some(DispatchGuard{coordinate,dispatches:0,ended:false,_single:PhantomData})
    }
    impl Drop for DispatchGuard {
        fn drop(&mut self){if !self.ended&&self.coordinate==CURRENT.load(Ordering::Acquire)&&OWNER.with(Cell::get)==self.coordinate{let before=GATE_STATE.fetch_or(CLOSED,Ordering::AcqRel);if before&COUNTS==0&&owner(){WRITER.with(|w|drop(w.borrow_mut().take()));OWNER.with(|o|o.set(0));GATE_STATE.store(CLOSED,Ordering::Release);}}}
    }
    impl DispatchGuard {
        pub fn dispatch<T>(&mut self,call:impl FnOnce()->T)->T {
            assert_eq!(OWNER.with(Cell::get),self.coordinate);
            assert_eq!(GATE_STATE.load(Ordering::Acquire),ACTIVE);
            self.dispatches=self.dispatches.checked_add(1).unwrap();call()
        }
        pub fn end(mut self,footer:[u64;64])->EndReceipt {
            self.ended=true;
            if self.coordinate!=CURRENT.load(Ordering::Acquire)||OWNER.with(Cell::get)!=self.coordinate{return EndReceipt{custody:None,finalized:false,flags:0,stored:0,attempted:0,attempts_before:0,attempts_after:0,dispatches:self.dispatches,gate:0};}
            let previous=GATE_STATE.fetch_or(CLOSED,Ordering::AcqRel);
            let mut receipt=EndReceipt{custody:None,finalized:false,flags:FLAGS.load(Ordering::Acquire),stored:0,attempted:0,attempts_before:0,attempts_after:0,dispatches:self.dispatches,gate:previous|CLOSED};
            // Never access WRITER if any admitted callback can still use it.
            if previous&ACTIVE==0||previous&CLOSED!=0||previous&COUNTS!=0||!owner(){return receipt;}
            WRITER.with(|cell|{
                let Ok(mut state)=cell.try_borrow_mut()else{receipt.flags|=BORROW;return;};
                let Some(writer)=state.as_mut()else{return;};
                writer.freeze(receipt.flags);
                if writer.observed_mask!=writer.expected_mask||writer.phase!=5{writer.freeze(LIFECYCLE);}
                receipt.attempts_before=writer.attempts;
                writer.finish(footer);
                receipt.stored=writer.stored;receipt.attempted=writer.attempted;
                receipt.flags=writer.flags;receipt.attempts_after=writer.attempts;receipt.finalized=true;
                match writer.sink.metadata(){Ok(meta)=>receipt.custody=Some(Custody::from_metadata(&meta)),Err(_)=>receipt.flags|=IO}
            });receipt
        }
    }
    pub fn retire_after_quiescence(){
        let now=GATE_STATE.load(Ordering::Acquire);assert_ne!(now&CLOSED,0);assert_eq!(now&COUNTS,0);
        WRITER.with(|w|drop(w.borrow_mut().take()));OWNER.with(|o|o.set(0));
        GATE_STATE.store(CLOSED,Ordering::Release);
    }
    pub fn observe(payload:[u64;11],coordinates:(u64,u64))->bool {
        if !enter(){return false;}
        if !owner(){invalidate(CONTEXT);leave();return false;}
        let accepted=WRITER.with(|cell|{
            let Ok(mut state)=cell.try_borrow_mut()else{invalidate(BORROW);return false;};
            let Some(writer)=state.as_mut()else{invalidate(LIFECYCLE);return false;};
            writer.freeze(FLAGS.load(Ordering::Acquire));
            let operation=match payload[0]{1=>match writer.operation.checked_add(1){Some(n)=>n,None=>{writer.freeze(OVERFLOW);return false;}},12|13=>0,14=>if payload[5]==ABSENT{writer.operation}else{0},_=>writer.operation};
            let mut event=Record([0,payload[0],writer.phase,operation,coordinates.0,coordinates.1,payload[1],payload[2],payload[3],payload[4],payload[5],payload[6],payload[7],payload[8],payload[9],payload[10]]);
            if payload[0]==13{event.0[2]=payload[8];}
            if payload[0]==14{event.0[10]=ABSENT;}
            writer.push(event);true
        });leave();accepted
    }
    pub fn acquire(function:u32,coordinates:(u64,u64)){observe([1,function as u64,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,0,0,0],coordinates);}
    pub fn phase(phase:u64,coordinates:(u64,u64)){observe([13,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,phase,0,0],coordinates);}
    pub fn failure(f:&SwiftRunFailure,terminal:bool){
        let code=source_code(f.code);
        if code==0 {if enter(){invalidate(CODE);leave();}return;}
        let operation=if terminal{0}else{ABSENT};
        observe([14,f.function.map_or(ABSENT,|n|n as u64),ABSENT,ABSENT,ABSENT,operation,ABSENT,0,kind(f.kind),code,stage(f.stage)],(f.at_failure.cache_work,f.at_failure.instructions));
    }
    pub fn stage(s:SwiftRunStage)->u64{match s{SwiftRunStage::Adoption=>1,SwiftRunStage::Cache=>2,SwiftRunStage::Initialization=>3,SwiftRunStage::Invocation=>4,SwiftRunStage::Wasi=>5,SwiftRunStage::Cleanup=>6}}
    pub fn kind(k:SwiftRunFailureKind)->u64{match k{SwiftRunFailureKind::InvalidBudget=>1,SwiftRunFailureKind::Cancelled=>2,SwiftRunFailureKind::Deadline=>3,SwiftRunFailureKind::Allocation=>4,SwiftRunFailureKind::Adoption=>5,SwiftRunFailureKind::CategoryExhausted=>6,SwiftRunFailureKind::CombinedExhausted=>7,SwiftRunFailureKind::ResourceExhausted=>8,SwiftRunFailureKind::FuelExhausted=>9,SwiftRunFailureKind::WorkExhausted=>10,SwiftRunFailureKind::HostCallLimit=>11,SwiftRunFailureKind::PinLimit=>12,SwiftRunFailureKind::FrameLimit=>13,SwiftRunFailureKind::ValueLimit=>14,SwiftRunFailureKind::ControlLimit=>15,SwiftRunFailureKind::DecoderMismatch=>16,SwiftRunFailureKind::UnsupportedEnvironment=>17,SwiftRunFailureKind::GuestTrap=>18,SwiftRunFailureKind::GuestExit=>19,SwiftRunFailureKind::Wasi=>20,SwiftRunFailureKind::Invariant=>21}}
    pub fn cleanup(k:Option<SwiftCleanupInvariant>)->u64{match k{None=>0,Some(SwiftCleanupInvariant::ReservationOwner)=>1,Some(SwiftCleanupInvariant::ReservationUnderflow)=>2,Some(SwiftCleanupInvariant::MissingConstruction)=>3,Some(SwiftCleanupInvariant::ConstructionBound)=>4,Some(SwiftCleanupInvariant::LiveUnderflow)=>5}}
    pub fn source_code(code:&str)->u64{match code{
        "swift_run_cancelled"=>1,
        "swift_run_deadline"=>2,
        "swift_run_work"=>3,
        "swift_run_invalid_budget"=>4,
        "swift_run_category_capacity"=>5,
        "swift_run_combined_capacity"=>6,
        "swift_run_cache_entry_capacity"=>7,
        "swift_run_unexpected_capacity"=>8,
        "swift_cache_allocation"=>9,
        "not_defined_function"=>10,
        "pin_nonce_exhausted"=>11,
        "pin_slots_exhausted"=>12,
        "all_entries_pinned"=>13,
        "swift_plan_identity"=>14,
        "swift_plan_layout"=>15,
        "swift_cache_layout_overflow"=>16,
        "swift_run_live_limit"=>17,
        "swift_run_fuel"=>18,
        "entry_bytes"=>19,
        "entry_cannot_fit"=>20,
        "entry_size_overflow"=>21,
        "swift_cache_index_victim"=>22,
        "swift_cache_index_missing"=>23,
        "swift_cache_index_insert"=>24,
        _=>0,
    }}
    pub fn footer(usage:&SwiftRunUsage,failure:Option<&SwiftRunFailure>)->[u64;64]{
        let mut w=[0;64];w[10]=usage.cache_work;w[11]=usage.instructions;w[14]=ABSENT;
        if let Some(f)=failure{w[12]=kind(f.kind);w[13]=source_code(f.code);w[14]=stage(f.stage);w[32]=1;}
        let r=&usage.reservations;
        w[16..25].copy_from_slice(&[r.retained_source.current as u64,r.retained_metadata.current as u64,r.cache.current as u64,r.state.current as u64,r.wasi.current as u64,r.shared.current as u64,r.construction.current as u64,r.combined.current as u64,r.live_tickets as u64]);
        let l=&usage.live;w[25..31].copy_from_slice(&[l.cache_entries.current as u64,l.active_pins.current as u64,l.frames.current as u64,l.values.current as u64,l.controls.current as u64,l.memory_pages.current as u64]);w[31]=cleanup(usage.cleanup_invariant);w
    }
    pub fn with_borrowed(call:impl FnOnce()){WRITER.with(|w|{let _held=w.borrow_mut();call();});}
    pub fn hold_entry_for_fixture()->bool{enter()}
    pub fn leave_for_fixture(){leave();}
    pub fn stored_for_fixture()->u64{WRITER.with(|w|w.borrow().as_ref().unwrap().stored)}
    pub fn flags()->u32{FLAGS.load(Ordering::Acquire)}
    pub fn state()->u64{GATE_STATE.load(Ordering::Acquire)}
}
mod ordered_finite_tests {
    use super::*;use super::ordered_observer::*;use super::ordered_wire::*;
    use crate::experimental::cache::borrowed::PinToken;
    use std::fs::{File,OpenOptions};use std::io::Read;use std::os::unix::fs::OpenOptionsExt;use std::path::PathBuf;
    static FILE_ID:std::sync::atomic::AtomicU64=std::sync::atomic::AtomicU64::new(0);
    fn owned()->(DispatchGuard,PathBuf){owned_cap(4096)}
    fn owned_cap(cap:u64)->(DispatchGuard,PathBuf){
        let id=FILE_ID.fetch_add(1,std::sync::atomic::Ordering::Relaxed);
        let path=PathBuf::from(std::env::var_os("TMPDIR").unwrap()).join(format!("ordered-{id}.bin"));
        let file=OpenOptions::new().write(true).create_new(true).custom_flags(0x100).open(&path).unwrap();
        let initial=file.metadata().unwrap();assert!(initial.is_file());assert_eq!(initial.len(),0);
        persist(&path.with_extension("initial.json"),custody_json(Custody::from_metadata(&initial)).as_bytes());
        let h=header(cap,49,[[7;32];4]).unwrap();
        let writer=Writer::new(file,cap,49,24,&h).unwrap();(begin(writer).unwrap(),path)
    }
    fn persist(path:&PathBuf,bytes:&[u8]){
        assert!(bytes.len()<=8192);let mut file=OpenOptions::new().write(true).create_new(true).custom_flags(0x100).open(path).unwrap();let mut attempts=0;assert!(bounded_write(&mut file,bytes,&mut attempts));
    }
    fn custody_json(c:Custody)->String{format!("{{\"dev\":{},\"ino\":{},\"mode\":{},\"len\":{},\"mtime_sec\":{},\"mtime_nsec\":{},\"ctime_sec\":{},\"ctime_nsec\":{}}}",c.dev,c.ino,c.mode,c.len,c.mtime_sec,c.mtime_nsec,c.ctime_sec,c.ctime_nsec)}
    fn persist_original(path:&PathBuf,failure:Option<&SwiftRunFailure>,usage:&SwiftRunUsage){
        // Exact original borrowed objects, persisted before End or any stream
        // classification. Debug text is a finite receipt, not the later target
        // driver's transport schema. No observer classification is substituted.
        let text=format!("original_failure={failure:?}\noriginal_final_usage={usage:?}\n");persist(&path.with_extension("original.txt"),text.as_bytes());
    }
    fn read(path:&PathBuf)->Vec<Record>{let mut raw=Vec::new();File::open(path).unwrap().read_to_end(&mut raw).unwrap();assert!(raw.len()>=1024);assert_eq!((raw.len()-1024)%128,0);raw[512..raw.len()-512].chunks_exact(128).map(|r|Record::decode(r.try_into().unwrap())).collect()}
    fn terminal(mut guard:DispatchGuard,path:&PathBuf,cache:SwiftFunctionCache,mut c:RuntimeControl,failure:Option<SwiftRunFailure>)->EndReceipt {
        if let Some(ref f)=failure{failure_observe(f);}
        let coords=c.ordered_coordinates();phase(4,coords);
        let cleanup_result=guard.dispatch(||super::cleanup(cache,&mut c,None));
        if let Some(ref actual)=cleanup_result{let original=failure.as_ref().expect("cleanup failure needs actual original failure");assert_eq!(actual.kind,original.kind);assert_eq!(actual.code,original.code);}
        let usage=c.finish_owned_cleanup(None);assert_eq!(usage.reservations.combined.current,0);assert_eq!(usage.reservations.live_tickets,0);assert_eq!(usage.live.cache_entries.current,0);assert_eq!(usage.live.active_pins.current,0);
        persist_original(path,failure.as_ref(),&usage);
        phase(5,(usage.cache_work,usage.instructions));let f=footer(&usage,failure.as_ref());
        let receipt=guard.end(f);if let Some(custody)=receipt.custody{persist(&path.with_extension("final.json"),custody_json(custody).as_bytes());}retire_after_quiescence();receipt
    }
    fn failure_observe(f:&SwiftRunFailure){ordered_observer::failure(f,true);}
    #[test]fn ordered_finite_success_nonce_release_evict_and_allocation_parity(){
        let bytes=fixture(0,&[0,0x0b],100);
        let run=|on:bool|{
            let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_entries:2,..SwiftRunBudget::default()});
            let mut enabled=if on{Some(owned())}else{None};
            let (result,stats)=measure(||{
                let mut invoke=||{
                    let p=pin(&mut cache,&mut c,34,None).unwrap();let old_nonce=p.nonce();
                    let q=pin(&mut cache,&mut c,35,None).unwrap();cache.release(q,&mut c,None).map_err(|e|e.failure).unwrap();
                    let q=pin(&mut cache,&mut c,36,None).unwrap();cache.release(q,&mut c,None).map_err(|e|e.failure).unwrap();
                    let view=cache.view(&p,&mut c,None).unwrap();assert_eq!(view.function,34);cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();old_nonce
                };
                if let Some((ref mut g,_))=enabled{g.dispatch(invoke)}else{invoke()}
            });
            let u=c.usage(None);
            let out=(result,u.cache_work,u.live,u.reservations,cache.usage(),stats.attempts,stats.allocated_bytes);
            if let Some((g,path))=enabled{
                let receipt=terminal(g,&path,cache,c,None);assert!(receipt.finalized);assert_eq!(receipt.flags,0);assert_eq!(receipt.gate&((1<<32)-1),0);
                let rows=read(&path);let pubs:Vec<_>=rows.iter().filter(|r|r.0[1]==11).collect();let releases:Vec<_>=rows.iter().filter(|r|r.0[1]==12).collect();
                assert_eq!(pubs[0].0[12],result);assert_eq!(releases.last().unwrap().0[12],result);assert_ne!(pubs[1].0[12],result);
                for release in releases{assert_eq!(release.0[8],ABSENT);let p=pubs.iter().find(|p|p.0[11..13]==release.0[11..13]).unwrap();assert_eq!(p.0[6],release.0[6]);assert_eq!(p.0[7],release.0[7]);assert_eq!(p.0[9..13],release.0[9..13]);}
                assert_eq!(rows.iter().filter(|r|r.0[1]==6).count(),1);assert_eq!(rows.iter().filter(|r|r.0[1]==7).count(),1);assert_eq!(rows.iter().filter(|r|r.0[1]==8).count(),1);
                assert!(!observe([1,34,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,0,0,0],(0,0)));assert_eq!(flags(),0);
                println!("ORDERED_SUCCESS file={} events={} attempts_before={} attempts_after={} dispatches={} flags=0 actual_nonce={result}",path.display(),rows.len(),receipt.attempts_before,receipt.attempts_after,receipt.dispatches);
            }else{finish(cache,c);}
            out
        };assert_eq!(run(false),run(true));
    }
    #[test]fn ordered_finite_cache_work_partial_and_cancellation(){
        for cancel in [false,true]{
            let bytes=fixture(0,&[0,0x41,1,0x1a,0x0b],100);let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
            let (mut guard,path)=owned();
            if cancel{hooks(Hooks{cancel:Some(3),..Hooks::default()});}else{
                // The original control budget is immutable; construct a separate
                // finite owner with its original narrower authored budget.
                let used=c.usage(None).cache_work;finish(cache,c);
                let pair=new(&bytes,SwiftRunBudget{cache_work:used+15,..SwiftRunBudget::default()});c=pair.0;cache=pair.1;
            }
            let original=guard.dispatch(||pin(&mut cache,&mut c,34,None)).unwrap_err();hooks(Hooks::default());
            assert!(matches!(original.kind,SwiftRunFailureKind::Cancelled|SwiftRunFailureKind::WorkExhausted));
            let original_kind=original.kind;let receipt=terminal(guard,&path,cache,c,Some(original));assert!(receipt.finalized);assert_eq!(receipt.flags,0);assert_eq!(receipt.gate&((1<<32)-1),0);
            let rows=read(&path);assert_eq!(rows.iter().filter(|r|r.0[1]==14&&r.0[3]>0).count(),1);assert_eq!(rows.iter().filter(|r|r.0[1]==14&&r.0[3]==0).count(),1);assert!(!rows.iter().any(|r|r.0[1]==11));
            println!("ORDERED_FAILURE original={original_kind:?} file={} events={} attempts={}",path.display(),rows.len(),receipt.attempts_after);
        }
    }
    #[test]fn ordered_finite_gate_wrong_thread_borrow_duplicate_and_after_end(){
        let (guard,_path)=owned();assert!(begin(Writer::new(OpenOptions::new().write(true).create_new(true).custom_flags(0x100).open(PathBuf::from(std::env::var_os("TMPDIR").unwrap()).join(format!("ordered-duplicate-{}.bin",FILE_ID.fetch_add(1,std::sync::atomic::Ordering::Relaxed)))).unwrap(),1,33,24,&header(1,33,[[0;32];4]).unwrap()).unwrap()).is_none());
        // Duplicate begin intentionally invalidates the active lifetime.
        assert_ne!(flags()&LIFECYCLE,0);
        std::thread::spawn(||{assert!(!observe([1,34,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,0,0,0],(0,0)));}).join().unwrap();
        assert_ne!(flags()&CONTEXT,0);
        assert!(observe([1,34,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,0,0,0],(0,0)));
        // Owner callback is admitted but never resumes ordinary records after
        // the independent latch became invalid. Checked from actual TLS writer.
        assert_eq!(ordered_observer::stored_for_fixture(),0);
        with_borrowed(||{assert!(!observe([1,34,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,0,0,0],(0,0)));});assert_ne!(flags()&BORROW,0);
        assert!(hold_entry_for_fixture());let receipt=guard.end([0;64]);assert!(!receipt.finalized);leave_for_fixture();assert!(!observe([1,34,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,0,0,0],(0,0)));
        assert_eq!(state()&((1<<32)-1),0);retire_after_quiescence();
    }

    #[test]fn ordered_finite_all_pinned_retains_real_replay_pins(){
        let bytes=fixture(0,&[0,0x0b],100);let(mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_entries:2,..SwiftRunBudget::default()});let(mut g,path)=owned();
        let (p,q)=g.dispatch(||(pin(&mut cache,&mut c,34,None).unwrap(),pin(&mut cache,&mut c,35,None).unwrap()));
        let original=g.dispatch(||pin(&mut cache,&mut c,36,None)).unwrap_err();assert_eq!(original.code,"all_entries_pinned");
        drop((p,q));let receipt=terminal(g,&path,cache,c,Some(original));assert_eq!(receipt.flags,0);
        let rows=read(&path);assert_eq!(rows.iter().filter(|r|r.0[1]==11).count(),2);assert!(!rows.iter().any(|r|r.0[1]==12||r.0[1]==6||r.0[1]==7||r.0[1]==8));
        println!("ORDERED_ALL_PINNED file={} retained_stream_pins=2 consuming_zero=true",path.display());
    }
    #[test]fn ordered_finite_terminal_absent_and_independent_cursor(){
        let bytes=fixture(0,&[0,0x0b],100);
        // Actual original construction rejection, with no pin operation.
        let(mut c,p)=adopt(&bytes,SwiftRunBudget{cache_bytes:0,..SwiftRunBudget::default()});let(mut g,path)=owned();
        let original=g.dispatch(||construct(&mut c,p,None)).err().unwrap();assert!(original.function.is_none());failure_observe(&original);phase(4,c.ordered_coordinates());
        let usage=c.finish_owned_cleanup(None);persist_original(&path,Some(&original),&usage);phase(5,(usage.cache_work,usage.instructions));let r=g.end(footer(&usage,Some(&original)));if let Some(custody)=r.custody{persist(&path.with_extension("final.json"),custody_json(custody).as_bytes());}assert_eq!(r.flags,0);retire_after_quiescence();let rows=read(&path);assert_eq!(rows.iter().filter(|r|r.0[1]==14&&r.0[3]==0&&r.0[6]==ABSENT).count(),1);assert!(!rows.iter().any(|r|r.0[1]==1));
        println!("ORDERED_CONSTRUCTION file={} original={}",path.display(),original.code);
        // Original non-cache work failure with an independent actual cursor.
        let(mut c,cache)=new(&bytes,SwiftRunBudget::default());let(mut g,path)=owned();
        let original=g.dispatch(||c.work(Work::Execution,u64::MAX,Cursor{stage:SwiftRunStage::Invocation,function:Some(62),offset:Some(9)})).unwrap_err();
        assert_eq!(original.function,Some(62));let r=terminal(g,&path,cache,c,Some(original));assert_eq!(r.flags,0);let rows=read(&path);assert_eq!(rows.iter().filter(|r|r.0[1]==14&&r.0[3]==0&&r.0[6]==62).count(),1);assert!(!rows.iter().any(|r|r.0[1]==1));println!("ORDERED_TERMINAL file={} cursor=62",path.display());
    }
    #[test]fn ordered_finite_allocation_ordinals_original_result_parity(){
        let bytes=fixture(0,&[0,0x41,1,0x1a,0x0b],100);
        for ordinal in 0..=1 {
            let run=|on:bool|{
                let(mut c,mut cache)=new(&bytes,SwiftRunBudget::default());let mut enabled=if on{Some(owned())}else{None};
                let(result,stats)=measure_extended(Some(ordinal),||{let mut invoke=||pin(&mut cache,&mut c,34,None);if let Some((ref mut g,_))=enabled{g.dispatch(invoke)}else{invoke()}});
                let original=match result{Ok(p)=>{cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();None},Err(e)=>Some(e)};
                let u=c.usage(None);let summary=(original.map(|f|(f.kind,f.code,f.at_failure.cache_work)),u.cache_work,u.live,u.reservations,cache.usage(),stats.attempts,stats.injected_failures,stats.allocated_bytes);
                if let Some((g,path))=enabled{let receipt=terminal(g,&path,cache,c,original);if original.is_some_and(|f|source_code(f.code)==0){assert_ne!(receipt.flags&CODE,0);}else{assert_eq!(receipt.flags,0);}println!("ORDERED_ALLOC ordinal={ordinal} file={} attempts={} injected={} flags={}",path.display(),stats.attempts,stats.injected_failures,receipt.flags);}else{finish(cache,c);}summary
            };assert_eq!(run(false),run(true));
        }
    }
    #[test]fn ordered_finite_cap_only_actual_lifecycle_and_prefix(){
        let bytes=fixture(0,&[0,0x0b],100);let(mut c,mut cache)=new(&bytes,SwiftRunBudget::default());let(mut g,path)=owned_cap(2);
        let p=g.dispatch(||pin(&mut cache,&mut c,34,None)).unwrap();cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();let receipt=terminal(g,&path,cache,c,None);assert_eq!(receipt.flags,CAP);assert_eq!(receipt.stored,2);assert!(receipt.attempted>2);
        let raw=std::fs::read(&path).unwrap();assert_eq!(raw.len(),1280);assert!(valid_footer_fields(raw[..512].try_into().unwrap(),raw[768..].try_into().unwrap(),1280));
        let before=raw.clone();assert!(!observe([1,34,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,0,0,0],(0,0)));assert_eq!(before,std::fs::read(&path).unwrap());
        println!("ORDERED_CAP file={} stored=2 attempted={} flags=1 actual_phase_mask=49",path.display(),receipt.attempted);
    }
    #[allow(dead_code)]
    struct CallbackInventory {
        payload:[u64;11],coordinates:(u64,u64),record:Record,body:crate::experimental::descriptors::FunctionSpanView<'static>,
        gate_before:u64,lifetime:u64,operation:Option<u64>,sticky:u32,
        gate:&'static std::sync::atomic::AtomicU64,latch:&'static std::sync::atomic::AtomicU32,owner:&'static Cell<u64>,
        cell:&'static std::cell::RefCell<Option<Writer<File>>>,
        borrow_result:Result<std::cell::RefMut<'static,Option<Writer<File>>>,std::cell::BorrowMutError>,
        borrow:std::cell::RefMut<'static,Option<Writer<File>>>,writer:&'static mut Writer<File>,
        file:&'static mut File,bytes:&'static [u8],offset:usize,retry:std::ops::Range<usize>,
        result:std::io::Result<usize>,error:std::io::Error,error_kind:std::io::ErrorKind,
        encode_words:std::slice::Iter<'static,u64>,encode_byte:[u8;8],encode_index:usize,
        record_borrow:&'static Record,encode_output:&'static mut [u8;128],
        checked:Option<u64>,slice:&'static [u8],attempts:&'static mut u64,
        failure:&'static SwiftRunFailure,source_code:&'static str,source_id:u64,
        closure_self:&'static mut CacheOperationPhase<'static>,closure_cache:&'static mut SwiftFunctionCache,
    }
    #[allow(dead_code)]
    struct FrameInventory {header:[u8;512],footer_words:[u64;64],footer_parameter:[u64;64],encoded_footer:[u8;512],frame_return:[u8;512],digests:[[u8;32];4],frame_borrow:&'static[u64;64],receipt:EndReceipt,writer_option:&'static mut Option<Writer<File>>,owner_coordinate:u64,closed:u64,flags:u32,mask:u64}
    #[allow(dead_code)]
    struct WholeOutputInventory {pin_result:Result<SwiftFunctionPin,SwiftRunFailure>,usage:SwiftRunUsage,wasi:Option<WasiUsage>,failure_borrow:Option<&'static SwiftRunFailure>,footer_borrow:&'static SwiftRunUsage,release_result:Result<(),SwiftReleaseFailure>,retained_failure:Option<SwiftRunFailure>,cleanup_result:Option<SwiftRunFailure>}
    #[test]fn ordered_finite_layout_inventory(){
        use std::cell::RefCell;use std::sync::atomic::{AtomicU64,AtomicU32};
        let owner=size_of::<RefCell<Option<Writer<File>>>>();
        let atomics=3*size_of::<AtomicU64>()+size_of::<AtomicU32>()+size_of::<Cell<u64>>();
        let helper=size_of::<CallbackInventory>();let frames=size_of::<FrameInventory>();let outputs=size_of::<WholeOutputInventory>();
        let guard=size_of::<DispatchGuard>();let literal_bytes=502usize;
        let retirement=size_of::<Option<Writer<File>>>();
        let metadata=size_of::<std::fs::Metadata>()+2*size_of::<std::io::Result<std::fs::Metadata>>()+size_of::<&std::fs::Metadata>();
        let drop_locals=7*size_of::<usize>();let persistent=owner+atomics+guard+literal_bytes;
        // Admission is closed and callbacks have returned before End; End and
        // encode_frame frames return before retirement's take/Drop owner move.
        // Whole original/cleanup/release Results remain conservatively charged
        // in all three phases even where their lexical scopes do not overlap.
        let callback_peak=persistent+3*helper+outputs+metadata+drop_locals;
        let footer_peak=persistent+frames+outputs+metadata+drop_locals;
        let retirement_peak=persistent+retirement+outputs+metadata+drop_locals+size_of::<[u64;64]>()+size_of::<EndReceipt>();
        let total=callback_peak.max(footer_peak).max(retirement_peak);
        let subtotal=persistent+3*helper+frames+outputs+metadata+drop_locals;
        println!("ORDERED_PHASE_LAYOUT callback={callback_peak} footer={footer_peak} retirement={retirement_peak} metadata={metadata} drop_locals={drop_locals} all_phase_union={}",subtotal+retirement);
        println!("ORDERED_LAYOUT writer={} writer_align={} tls={} atomics_tls={} helper={} helper_copies=3 frames={} whole_outputs={} guard={} literals={} retirement={} subtotal={} total={} cap=16384 result_pin={} result_release={} failure={} usage={} option_wasi={} io_result={} io_error={}",size_of::<Writer<File>>(),std::mem::align_of::<Writer<File>>(),owner,atomics,helper,frames,outputs,guard,literal_bytes,retirement,subtotal,total,size_of::<Result<SwiftFunctionPin,SwiftRunFailure>>(),size_of::<Result<(),SwiftReleaseFailure>>(),size_of::<SwiftRunFailure>(),size_of::<SwiftRunUsage>(),size_of::<Option<WasiUsage>>(),size_of::<std::io::Result<usize>>(),size_of::<std::io::Error>());
        assert!(total<=16384,"complete conservative external logical inventory exceeds hard ceiling");
    }

}

// Independently authored completion controls. The product operation bodies are unchanged.
mod ordered_completion_tests {
    use super::*;
    use super::ordered_observer::{DispatchGuard,EndReceipt,Custody,begin,phase,footer,retire_after_quiescence,stored_for_fixture,flags,state};
    use super::ordered_wire::*;
    use super::super::allocation_tests::AllocationStats;
    use std::fs::{File,OpenOptions};
    use std::io::{Read,Seek,SeekFrom};
    use std::fmt::Write as FmtWrite;
    use std::os::unix::fs::OpenOptionsExt;
    use std::path::{Path,PathBuf};
    use std::sync::atomic::{AtomicU64,Ordering};
    static CASE:AtomicU64=AtomicU64::new(0);

    // A bounded synchronous formatter, rather than an allocated format! buffer.
    // Each fill uses at most 32 writes, and the entire receipt is <=8192 bytes.
    struct ReceiptWriter {file:File,buffer:[u8;512],used:usize,total:usize,attempts:u64}
    impl ReceiptWriter {
        fn create(path:&Path)->Self {
            Self{file:OpenOptions::new().write(true).create_new(true).custom_flags(0x100).open(path).unwrap(),buffer:[0;512],used:0,total:0,attempts:0}
        }
        fn drain(&mut self)->std::fmt::Result {
            if self.used!=0 {
                if !bounded_write(&mut self.file,&self.buffer[..self.used],&mut self.attempts){return Err(std::fmt::Error);}
                self.used=0;
            } Ok(())
        }
        fn finish(mut self){self.drain().unwrap();assert!(self.total<=8192);}
    }
    impl std::fmt::Write for ReceiptWriter {
        fn write_str(&mut self,text:&str)->std::fmt::Result {
            let next=self.total.checked_add(text.len()).ok_or(std::fmt::Error)?;
            if next>8192{return Err(std::fmt::Error);}
            self.total=next;let mut bytes=text.as_bytes();
            while !bytes.is_empty(){let n=(512-self.used).min(bytes.len());self.buffer[self.used..self.used+n].copy_from_slice(&bytes[..n]);self.used+=n;bytes=&bytes[n..];if self.used==512{self.drain()?;}}
            Ok(())
        }
    }
    fn path()->PathBuf {
        let id=CASE.fetch_add(1,Ordering::Relaxed);
        let name=format!("completion-{id}.bin");assert!(name.capacity()<=128);
        let p=PathBuf::from(std::env::var_os("TMPDIR").unwrap()).join(name);assert!(p.capacity()<=512);p
    }
    fn receipt_path(path:&Path,extension:&str)->PathBuf{let p=path.with_extension(extension);assert!(p.capacity()<=512);p}
    fn custody(path:&Path,c:Custody){
        let mut out=ReceiptWriter::create(path);
        write!(out,"{{\"dev\":{},\"ino\":{},\"mode\":{},\"len\":{},\"mtime_sec\":{},\"mtime_nsec\":{},\"ctime_sec\":{},\"ctime_nsec\":{}}}\n",c.dev,c.ino,c.mode,c.len,c.mtime_sec,c.mtime_nsec,c.ctime_sec,c.ctime_nsec).unwrap();out.finish();
    }
    fn start(path:&Path)->DispatchGuard {
        let file=OpenOptions::new().write(true).create_new(true).custom_flags(0x100).open(path).unwrap();
        {let m=file.metadata().unwrap();assert!(m.is_file());assert_eq!(m.len(),0);custody(&receipt_path(path,"initial.json"),Custody::from_metadata(&m));}
        let h=header(4096,49,[[7;32];4]).unwrap();
        let writer=Writer::new(file,4096,49,24,&h).unwrap();begin(writer).unwrap()
    }
    #[derive(Default)]struct Rows {count:u64,kinds:u64,published:u64,pin_fail:bool,terminal_fail:bool,taken_index:Option<u64>,taken_prior:u64,forbidden_after_taken:bool}
    fn rows(path:&Path)->Rows{
        let mut file=File::open(path).unwrap();let bytes=file.metadata().unwrap().len();assert!((1024..=16384).contains(&bytes));assert_eq!((bytes-1024)%128,0);file.seek(SeekFrom::Start(512)).unwrap();
        let mut out=Rows::default();let mut raw=[0;128];let mut prior=0;
        for index in 0..(bytes-1024)/128{file.read_exact(&mut raw).unwrap();let r=Record::decode(&raw);let w=r.0;out.count+=1;out.kinds|=1<<w[1];if w[1]==11{out.published+=1;}
            if w[1]==14{if w[3]>0&&w[13..16]==[2,1,2]{out.pin_fail=true;}if w[3]==0{out.terminal_fail=true;}}
            if out.taken_index.is_some()&&[8,9,10,11,14].contains(&w[1]){out.forbidden_after_taken=true;}
            if w[1]==7{assert!(out.taken_index.is_none());out.taken_index=Some(index);out.taken_prior=prior;}prior=w[1];}
        out
    }
    fn usage_keys(out:&mut ReceiptWriter,u:&SwiftRunUsage){
        write!(out,"{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}\n",
            u.reservations,u.live,u.cache_work,u.execution_work,u.instruction_fuel,u.instructions,u.host_calls,u.cleanup_invariant,u.deadline_ms,u.deadline_origin,u.deadline_overshoot_micros,
            u.validation.input_visible_bytes,u.validation.source_bytes,u.validation.metadata_reserved,u.validation.scratch_reserved,u.validation.metadata_peak_reserved,u.validation.scratch_peak_reserved,u.validation.total_peak_reserved,u.validation.work_used,u.validation.deadline_ms).unwrap();
        assert!(u.wasi.is_none());
    }
    fn failure_keys(out:&mut ReceiptWriter,f:&SwiftRunFailure){
        write!(out,"{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}\n",f.stage,f.kind,f.code,f.function,f.offset,f.resource,f.attempted,f.limit,f.observed_capacity,f.deadline_origin,f.wasi_failure,f.guest_exit).unwrap();
        usage_keys(out,&f.at_failure);if let Some(ref u)=f.after_cleanup{usage_keys(out,u);}
    }
    struct Outcome {
        original:Option<SwiftRunFailure>,before:SwiftRunUsage,final_usage:SwiftRunUsage,
        cache:SwiftCacheUsage,cleanup:Option<SwiftRunFailure>,foreign:Option<SwiftRunUsage>,
        stats:AllocationStats,token:[u64;2],
    }
    fn persist(path:&Path,o:&Outcome){
        // Called only after End and quiescent retirement. TLS Option storage is
        // still fully charged; no formatter or receipt buffer escapes its scope.
        {let mut out=ReceiptWriter::create(&receipt_path(path,"original.txt"));write!(out,"original_failure={:?}\noriginal_final_usage={:?}\n",o.original,o.final_usage).unwrap();out.finish();}
        {let mut out=ReceiptWriter::create(&receipt_path(path,"details.txt"));write!(out,"before={:?}\ncache={:?}\ncleanup={:?}\nforeign={:?}\nallocations={:?}\ntoken={:?}\n",o.before,o.cache,o.cleanup,o.foreign,o.stats,o.token).unwrap();out.finish();}
        {let mut out=ReceiptWriter::create(&receipt_path(path,"semantic.txt"));
            if let Some(ref f)=o.original{failure_keys(&mut out,f);}usage_keys(&mut out,&o.before);usage_keys(&mut out,&o.final_usage);
            if let Some(ref f)=o.cleanup{failure_keys(&mut out,f);}if let Some(ref u)=o.foreign{usage_keys(&mut out,u);}
            write!(out,"{:?}|{:?}|{:?}\n",o.cache,o.stats,o.token).unwrap();out.finish();}
    }
    fn close(enabled:Option<DispatchGuard>,path:&Path,u:&SwiftRunUsage,f:Option<&SwiftRunFailure>)->Option<EndReceipt>{
        enabled.map(|g|{phase(5,(u.cache_work,u.instructions));let receipt=g.end(footer(u,f));retire_after_quiescence();if let Some(m)=receipt.custody{custody(&receipt_path(path,"final.json"),m);}receipt})
    }
    fn consume(mut enabled:Option<DispatchGuard>,cache:SwiftFunctionCache,mut c:RuntimeControl,f:&SwiftRunFailure)->(SwiftRunUsage,Option<SwiftRunFailure>,Option<DispatchGuard>){
        if enabled.is_some(){ordered_observer::failure(f,true);phase(4,c.ordered_coordinates());}
        let call=||super::cleanup(cache,&mut c,None);
        let cleanup=if let Some(g)=enabled.as_mut(){g.dispatch(call)}else{call()};
        let u=c.finish_owned_cleanup(None);assert_eq!(u.reservations.combined.current,0);assert_eq!(u.reservations.live_tickets,0);assert_eq!(u.live.cache_entries.current,0);assert_eq!(u.live.active_pins.current,0);
        (u,cleanup,enabled)
    }
    fn parity(a:&Path,b:&Path){
        let mut a=File::open(receipt_path(a,"semantic.txt")).unwrap();let mut b=File::open(receipt_path(b,"semantic.txt")).unwrap();let n=a.metadata().unwrap().len();assert!(n<=8192);assert_eq!(n,b.metadata().unwrap().len());
        let(mut first,mut second)=([0;512],[0;512]);let mut position=0;
        while position<n{let count=(n-position).min(512)as usize;a.read_exact(&mut first[..count]).unwrap();b.read_exact(&mut second[..count]).unwrap();assert_eq!(first[..count],second[..count]);position+=count as u64;}
    }
    fn header_only(path:&Path)->[u8;512]{let mut file=File::open(path).unwrap();assert_eq!(file.metadata().unwrap().len(),512);let mut bytes=[0;512];file.read_exact(&mut bytes).unwrap();bytes}

    #[test]fn ordered_completion_publication_cancel_actual_result_and_prefix(){
        fn run(on:bool)->PathBuf{
            let path=path();let (outcome,receipt)={let bytes=fixture(0,&[0,0x0b],100);let(mut c,mut cache)=new(&bytes,SwiftRunBudget::default());let mut enabled=on.then(||start(&path));
            hooks(Hooks{pause:Some(CacheStep::Publication),cancel_pause:true,..Hooks::default()});
            let (actual,stats)=measure(||{let mut call=||pin(&mut cache,&mut c,34,None);if let Some(g)=enabled.as_mut(){g.dispatch(call)}else{call()}});
            let f=actual.err().unwrap();hooks(Hooks::default());assert_eq!(f.kind,SwiftRunFailureKind::Cancelled);assert_eq!(f.code,"swift_run_cancelled");assert_eq!(f.stage,SwiftRunStage::Cache);assert_eq!(f.function,Some(34));
            let before=c.usage(None);let snapshot=cache.usage();assert_eq!(snapshot.decodes,0);assert_eq!(snapshot.active_pins,0);
            let(final_usage,cleanup,enabled)=consume(enabled,cache,c,&f);let receipt=close(enabled,&path,&final_usage,Some(&f));
            (Outcome{original:Some(f),before,final_usage,cache:snapshot,cleanup,foreign:None,stats,token:[0;2]},receipt)};persist(&path,&outcome);
            if let Some(r)=receipt{assert_eq!(r.flags,0);let records=rows(&path);assert_ne!(records.kinds&(1<<10),0);assert_eq!(records.published,0);assert!(records.pin_fail&&records.terminal_fail);}
            path
        }let off=run(false);let on=run(true);parity(&off,&on);println!("COMPLETION publication originalParity=true stream={} fullReplayAccepted=false",on.display());
    }

    #[test]fn ordered_completion_release_wrong_owner_and_stale_original_errors(){
        fn run(on:bool,stale:bool)->PathBuf{
            let path=path();let (outcome,receipt)={let bytes=fixture(0,&[0,0x0b],100);let(mut c,mut cache)=new(&bytes,SwiftRunBudget::default());let mut enabled=on.then(||start(&path));
            let p=if let Some(g)=enabled.as_mut(){g.dispatch(||pin(&mut cache,&mut c,34,None).unwrap())}else{pin(&mut cache,&mut c,34,None).unwrap()};let token=inspection::elision_pin_parts(&p);
            let (f,before,snapshot,stats,cleanup,final_usage,enabled)=if stale{
                let duplicate=inspection::stale(&p);cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();
                let count=on.then(stored_for_fixture);
                let(actual,stats)=measure(||cache.release(duplicate,&mut c,None));if let Some(n)=count{assert_eq!(stored_for_fixture(),n);}let err=actual.err().unwrap();let f=err.failure;let returned=err.into_pin();assert_eq!(inspection::elision_pin_parts(&returned),token);drop(returned);
                assert_eq!(f.code,"stale_pin");let before=c.usage(None);let snapshot=cache.usage();assert_eq!(snapshot.active_pins,0);
                let(u,cleanup,enabled)=consume(enabled,cache,c,&f);(f,before,snapshot,stats,cleanup,u,enabled)
            }else{
                let(mut foreign,mut other)=new(&bytes,SwiftRunBudget::default());let baseline=other.usage();
                let count=on.then(stored_for_fixture);
                let(actual,stats)=measure(||other.release(p,&mut foreign,None));if let Some(n)=count{assert_eq!(stored_for_fixture(),n);}let err=actual.err().unwrap();let f=err.failure;let returned=err.into_pin();assert_eq!(inspection::elision_pin_parts(&returned),token);assert_eq!(other.usage(),baseline);
                assert_eq!(f.code,"wrong_cache_owner");let before=foreign.usage(None);let snapshot=other.usage();
                // The original valid token is returned intact and released only
                // against its own original cache/control. No stale authority is reused.
                cache.release(returned,&mut c,None).map_err(|e|e.failure).unwrap();if let Some(n)=count{assert_eq!(stored_for_fixture(),n+1);}finish(cache,c);
                let(u,cleanup,enabled)=consume(enabled,other,foreign,&f);(f,before,snapshot,stats,cleanup,u,enabled)
            };
            assert_eq!(f.kind,SwiftRunFailureKind::Invariant);assert_eq!(f.stage,SwiftRunStage::Cache);assert!(f.function.is_none());assert!(f.offset.is_none());
            let receipt=close(enabled,&path,&final_usage,Some(&f));(Outcome{original:Some(f),before,final_usage,cache:snapshot,cleanup,foreign:None,stats,token},receipt)};persist(&path,&outcome);
            if let Some(r)=receipt{assert_eq!(r.flags,CODE);assert!(r.stored>=8);let records=rows(&path);assert_eq!(records.count,0);assert_eq!(std::fs::metadata(&path).unwrap().len(),1024);println!("COMPLETION releaseInvalid bufferedStored={} serializedRecords=0 partialBufferDiscarded=true footerStoredMismatch=true",r.stored);}
            path
        }for stale in [false,true]{let off=run(false,stale);let on=run(true,stale);parity(&off,&on);println!("COMPLETION release stale={stale} originalParity=true stream={} flags=CODE fullReplayAccepted=false",on.display());}
    }

    #[test]fn ordered_completion_evict_taken_foreign_ticket_actual_refund_failure(){
        fn run(on:bool)->PathBuf{
            let path=path();let (outcome,receipt)={let bytes=fixture(0,&[0,0x0b],100);let(mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_entries:1,..SwiftRunBudget::default()});let mut enabled=on.then(||start(&path));
            let p=if let Some(g)=enabled.as_mut(){g.dispatch(||pin(&mut cache,&mut c,34,None).unwrap())}else{pin(&mut cache,&mut c,34,None).unwrap()};let token=inspection::elision_pin_parts(&p);cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();
            // Four real warm hits/releases place EvictTaken at record32, which
            // naturally flushes before the later unknown refund code latches.
            for _ in 0..4{let q=if let Some(g)=enabled.as_mut(){g.dispatch(||pin(&mut cache,&mut c,34,None).unwrap())}else{pin(&mut cache,&mut c,34,None).unwrap()};cache.release(q,&mut c,None).map_err(|e|e.failure).unwrap();}
            if on{assert_eq!(stored_for_fixture(),25);assert_eq!(std::fs::metadata(&path).unwrap().len(),512);}
            let(mut foreign,proof)=adopt(&bytes,SwiftRunBudget::default());let foreign_ticket=foreign.admit(SwiftReservationCategory::Cache,1,cache_cursor()).unwrap();let displaced=inspection::replace_entry_ticket(&mut cache,foreign_ticket);
            let(actual,stats)=measure(||{let mut call=||pin(&mut cache,&mut c,35,None);if let Some(g)=enabled.as_mut(){g.dispatch(call)}else{call()}});let f=actual.err().unwrap();
            assert_eq!(f.code,"swift_run_release_owner");assert_eq!(f.kind,SwiftRunFailureKind::Invariant);assert_eq!(f.stage,SwiftRunStage::Cleanup);assert!(f.function.is_none());assert!(f.offset.is_none());
            let snapshot=cache.usage();assert_eq!(snapshot.evictions,0);assert_eq!(snapshot.decodes,1);assert_eq!(snapshot.active_pins,0);let before=c.usage(None);
            if enabled.is_some(){ordered_observer::failure(&f,true);phase(4,c.ordered_coordinates());}
            // Original decoded storage was destroyed by drop_reserved before
            // foreign-owner rejection. Consume the displaced valid ticket once.
            c.drop_reserved((),displaced).unwrap();
            let call=||super::cleanup(cache,&mut c,None);let cleanup=if let Some(g)=enabled.as_mut(){g.dispatch(call)}else{call()};let final_usage=c.finish_owned_cleanup(None);assert_eq!(final_usage.reservations.combined.current,0);assert_eq!(final_usage.reservations.live_tickets,0);assert_eq!(final_usage.live.cache_entries.current,0);assert_eq!(final_usage.live.active_pins.current,0);
            foreign.drop_proof(proof).unwrap();let quarantine=foreign.finish_owned_cleanup(None);assert_eq!(quarantine.reservations.cache.current,1);assert_eq!(quarantine.reservations.combined.current,1);assert_eq!(quarantine.reservations.live_tickets,1);
            let receipt=close(enabled,&path,&final_usage,Some(&f));(Outcome{original:Some(f),before,final_usage,cache:snapshot,cleanup,foreign:Some(quarantine),stats,token},receipt)};persist(&path,&outcome);
            if let Some(r)=receipt{assert_eq!(r.flags,CODE);assert_eq!(r.stored,32);let records=rows(&path);assert_eq!(records.count,32);assert_eq!(std::fs::metadata(&path).unwrap().len(),5120);assert_eq!(records.taken_index,Some(31));assert_eq!(records.taken_prior,6);assert!(!records.forbidden_after_taken);assert_eq!(records.published,5);}
            path
        }let off=run(false);let on=run(true);parity(&off,&on);println!("COMPLETION evictTaken originalParity=true stream={} flags=CODE foreign_quarantine_bytes=1 foreign_quarantine_tickets=1 fullReplayAccepted=false",on.display());
    }

    #[test]fn ordered_completion_guard_drop_actual_hook_refusal(){
        let path=path();let bytes=fixture(0,&[0,0x0b],100);let(mut c,mut cache)=new(&bytes,SwiftRunBudget::default());let mut g=start(&path);
        let p=g.dispatch(||pin(&mut cache,&mut c,34,None).unwrap());drop(g);let before=header_only(&path);let latched=flags();
        cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();assert_eq!(before,header_only(&path));assert_eq!(flags(),latched);assert_eq!(state()&((1<<32)-1),0);finish(cache,c);
        println!("COMPLETION guardDrop noFooter=true actualReleaseRefused=true stream={}",path.display());
    }

    #[allow(dead_code)]
    struct CallbackValues {
        payload:[u64;11],coordinates:(u64,u64),record:Record,body:crate::experimental::descriptors::FunctionSpanView<'static>,
        gate_before:u64,lifetime:u64,operation:Option<u64>,sticky:u32,
        gate:&'static AtomicU64,latch:&'static std::sync::atomic::AtomicU32,owner:&'static Cell<u64>,
        cell:&'static std::cell::RefCell<Option<Writer<File>>>,
        borrow_result:Result<std::cell::RefMut<'static,Option<Writer<File>>>,std::cell::BorrowMutError>,
        borrow:std::cell::RefMut<'static,Option<Writer<File>>>,writer:&'static mut Writer<File>,
        file:&'static mut File,bytes:&'static[u8],offset:usize,retry:std::ops::Range<usize>,
        result:std::io::Result<usize>,error:std::io::Error,error_kind:std::io::ErrorKind,
        words:std::slice::Iter<'static,u64>,encoded_word:[u8;8],index:usize,
        record_borrow:&'static Record,encode_output:&'static mut[u8;128],checked:Option<u64>,
        slice:&'static[u8],attempts:&'static mut u64,failure:&'static SwiftRunFailure,
        source_code:&'static str,source_id:u64,phase:&'static mut CacheOperationPhase<'static>,cache:&'static mut SwiftFunctionCache,
    }
    #[allow(dead_code)]
    struct BeginValues {references:[usize;16],results:[Option<u64>;4],scalars:[u64;8],guard_return:Option<DispatchGuard>}
    #[allow(dead_code)]
    struct FormatterValues {
        arguments:std::fmt::Arguments<'static>,twenty_argument_roles:[(usize,usize);20],scalars:[usize;16],borrows:[usize;8],
        formatter:std::fmt::Formatter<'static>,write_result:std::io::Result<usize>,write_error:std::io::Error,
        error_kind:std::io::ErrorKind,range:std::ops::Range<usize>,checked:Option<u64>,
        receiver:&'static mut ReceiptWriter,text:&'static str,bytes:&'static[u8],format_result:std::fmt::Result,
    }
    #[allow(dead_code)]
    struct DebugValues {
        structs:[std::fmt::DebugStruct<'static,'static>;8],lists:[std::fmt::DebugList<'static,'static>;8],
        tuples:[std::fmt::DebugTuple<'static,'static>;8],maps:[std::fmt::DebugMap<'static,'static>;8],sets:[std::fmt::DebugSet<'static,'static>;8],
    }
    #[test]fn ordered_completion_complete_logical_phase_inventory(){
        use std::mem::{size_of,align_of,offset_of};
        let tls=size_of::<std::cell::RefCell<Option<Writer<File>>>>();
        let atomics=3*size_of::<AtomicU64>()+size_of::<std::sync::atomic::AtomicU32>()+size_of::<Cell<u64>>()+2*size_of::<AtomicU64>();
        let common=tls+atomics+502;
        let writer=size_of::<Writer<File>>();let moved=size_of::<Option<Writer<File>>>();let guard=size_of::<DispatchGuard>();let receipt=size_of::<EndReceipt>();
        let metadata=size_of::<std::fs::Metadata>()+2*size_of::<std::io::Result<std::fs::Metadata>>()+size_of::<&std::fs::Metadata>();
        // 1024 conservatively covers the finite receipt format literals. The
        // packet's independent literal scanner checks actual UTF8 bytes <=1024.
        let literals=1024usize;let path=512usize;let callback=size_of::<CallbackValues>();let outputs=size_of::<Outcome>();
        let phases=[
            ("path-construction",common+4*path+128+size_of::<BeginValues>()+literals),
            ("initial-metadata-receipt",common+2*path+metadata+3*size_of::<ReceiptWriter>()+3*size_of::<FormatterValues>()+literals),
            ("header-construction",common+path+4*512+128+size_of::<BeginValues>()+literals),
            // Charge both complete local/return or argument/Some-move owners,
            // in addition to complete TLS storage even when its value is None.
            ("writer-new-and-return",common+path+512+writer+moved+size_of::<BeginValues>()+literals),
            ("begin-and-failed-begin-disposal",common+path+512+writer+moved+size_of::<BeginValues>()+literals),
            ("callback",common+path+guard+3*callback+2*size_of::<Result<SwiftFunctionPin,SwiftRunFailure>>()+size_of::<SwiftRunFailure>()+size_of::<SwiftCacheUsage>()+size_of::<AllocationStats>()+size_of::<ReservationTicket>()+literals),
            ("release-result-and-returned-error",common+path+guard+3*callback+2*size_of::<Result<(),SwiftReleaseFailure>>()+size_of::<SwiftRunFailure>()+size_of::<SwiftFunctionPin>()+size_of::<SwiftCacheUsage>()+size_of::<AllocationStats>()+literals),
            ("consuming-cleanup-return",common+path+guard+3*size_of::<Option<SwiftRunFailure>>()+3*size_of::<SwiftRunUsage>()+size_of::<SwiftRunFailure>()+size_of::<SwiftCacheUsage>()+size_of::<AllocationStats>()+literals),
            ("footer",common+path+guard+outputs+5*512+128+receipt+metadata+7*size_of::<usize>()+literals),
            ("retirement",common+path+guard+outputs+moved+512+receipt+metadata+23*size_of::<usize>()+literals),
            // Each actual run assembles Outcome inside an explicit block, ends
            // all original Copy-output bindings, then calls persist. Charge
            // both copies during assembly, before any formatter is created.
            ("output-assembly",common+path+2*outputs+2*receipt+literals),
            ("final-custody-serialization",common+2*path+outputs+3*size_of::<ReceiptWriter>()+3*size_of::<FormatterValues>()+2*receipt+metadata+literals),
            ("serialization",common+2*path+outputs+3*size_of::<ReceiptWriter>()+3*size_of::<FormatterValues>()+size_of::<DebugValues>()+2*receipt+literals),
            ("formatter-boundary-control",common+2*path+4096+3*size_of::<ReceiptWriter>()+3*size_of::<FormatterValues>()+literals),
            ("abnormal-guard-drop",common+path+guard+moved+size_of::<BeginValues>()+size_of::<Result<SwiftFunctionPin,SwiftRunFailure>>()+literals),
            ("after-drop-refusal-and-file-comparison",common+path+4*512+guard+size_of::<SwiftFunctionPin>()+size_of::<BeginValues>()+literals),
            ("post-retirement-row-reader",common+2*path+outputs+4*128+size_of::<Rows>()+3*callback+metadata+receipt+literals),
            ("post-retirement-parity-reader",common+4*path+2*512+3*callback+metadata+2*size_of::<std::io::Result<File>>()+literals),
        ];
        println!("COMPLETION_LAYOUT writer={writer} writer_option={moved} writer_align={} writer_buffer_offset={} writer_sink_offset={} tls={tls} atomics={atomics} callback={callback} outputs={outputs} begin={} formatter={} debug_helpers={} receipt={receipt} metadata={metadata} receipt_writer={} pin_result={} release_result={} failure={} usage={} option_wasi={} supported_code_literals=502 receipt_literal_cap=1024",align_of::<Writer<File>>(),offset_of!(Writer<File>,buffer),offset_of!(Writer<File>,sink),size_of::<BeginValues>(),size_of::<FormatterValues>(),size_of::<DebugValues>(),size_of::<ReceiptWriter>(),size_of::<Result<SwiftFunctionPin,SwiftRunFailure>>(),size_of::<Result<(),SwiftReleaseFailure>>(),size_of::<SwiftRunFailure>(),size_of::<SwiftRunUsage>(),size_of::<Option<WasiUsage>>());
        for(name,total)in phases{println!("COMPLETION_PHASE {name}={total} cap=16384");assert!(total<=16384,"{name} exceeds unchanged logical ceiling: {total}");}
    }
    #[test]fn ordered_completion_receipt_formatter_exact_cap_refuses_one_more_byte(){
        let path=path();let text=[b'x';4096];let text=std::str::from_utf8(&text).unwrap();let mut out=ReceiptWriter::create(&path);
        out.write_str(text).unwrap();out.write_str(text).unwrap();assert_eq!(out.total,8192);assert_eq!(out.attempts,16);
        assert!(out.write_str("x").is_err());assert_eq!(out.total,8192);out.finish();assert_eq!(std::fs::metadata(&path).unwrap().len(),8192);
    }
}
