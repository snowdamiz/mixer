// Copied cfg(test) diagnostic only. No allocation or output in event callbacks.
const _: () = assert!(std::mem::size_of::<[u64; 1250]>() == 10_000);
pub(super) const ATTRIBUTION_SITES: [&str; 12] = [
    "constructor", "lookup_header", "free_pin_probe", "resident_probe",
    "scan_policy", "scan", "empty_slot_search", "victim_probe",
    "plan_count", "build_policy", "build", "publication",
];
#[derive(Clone, Copy)]
struct AttributionRejected { site: u8, function: Option<u32>, offset: Option<usize>, n: u64, failure: SwiftRunFailure }
#[derive(Clone)]
struct Attribution {
    enabled: bool, invalid: u32, site: u8, function: Option<u32>,
    credits: [u64; 12], calls: [u64; 12], rejected: Option<AttributionRejected>,
    free_histogram: [u64; 65], hit_histogram: [u64; 65],
    free_length: u64, resident_length: u64,
    hits: u64, misses: u64, distinct: u64, repeated: u64,
    seen: [u64; 1250], samples: [u32; 16], sample_len: usize,
    untracked_repeated_occurrences: u64,
}
impl Attribution {
    const fn empty() -> Self { Self {
        enabled: false, invalid: 0, site: 0, function: None,
        credits: [0; 12], calls: [0; 12], rejected: None,
        free_histogram: [0; 65], hit_histogram: [0; 65],
        free_length: 0, resident_length: 0,
        hits: 0, misses: 0, distinct: 0, repeated: 0,
        seen: [0; 1250], samples: [0; 16], sample_len: 0,
        untracked_repeated_occurrences: 0,
    } }
    fn add(invalid: &mut u32, slot: &mut u64, n: u64) {
        if let Some(next) = slot.checked_add(n) { *slot = next; }
        else { *invalid |= 1; *slot = u64::MAX; }
    }
    fn histogram(invalid: &mut u32, bins: &mut [u64; 65], length: u64) {
        if let Some(bin) = bins.get_mut(length as usize).filter(|_| length <= 64) {
            Self::add(invalid, bin, 1);
        } else { *invalid |= 2; }
    }
}
thread_local! {
    static ATTRIBUTION: std::cell::RefCell<Attribution> = const { std::cell::RefCell::new(Attribution::empty()) };
    static ATTRIBUTION_BORROW_INVALID: Cell<bool> = const { Cell::new(false) };
}
fn attribution_mut(f: impl FnOnce(&mut Attribution)) {
    ATTRIBUTION.with(|state| {
        if let Ok(mut state) = state.try_borrow_mut() {
            if state.enabled { f(&mut state); }
        } else { ATTRIBUTION_BORROW_INVALID.with(|flag| flag.set(true)); }
    });
}
pub(super) fn attribution_reset() {
    ATTRIBUTION_BORROW_INVALID.with(|flag| flag.set(false));
    ATTRIBUTION.with(|state| {
        if let Ok(mut state) = state.try_borrow_mut() {
            *state = Attribution::empty(); state.enabled = true;
        } else { ATTRIBUTION_BORROW_INVALID.with(|flag| flag.set(true)); }
    });
}
pub(super) fn attribution_begin(function: u32) {
    attribution_mut(|state| { state.function = Some(function); state.free_length = 0; state.resident_length = 0; });
}
pub(super) fn attribution_site(site: u8) {
    attribution_mut(|state| {
        if site as usize >= ATTRIBUTION_SITES.len() { state.invalid |= 4; return; }
        if site == 3 && state.site == 2 {
            Attribution::histogram(&mut state.invalid, &mut state.free_histogram, state.free_length);
        }
        state.site = site;
        if site == 0 { state.function = None; }
    });
}
pub(super) fn attribution_work(n: u64, cursor: Cursor, result: &Result<(), SwiftRunFailure>) {
    attribution_mut(|state| {
        let site = state.site as usize;
        let Some(calls) = state.calls.get_mut(site) else { state.invalid |= 4; return; };
        Attribution::add(&mut state.invalid, calls, 1);
        match result {
            Ok(()) => {
                Attribution::add(&mut state.invalid, &mut state.credits[site], n);
                if site == 2 { Attribution::add(&mut state.invalid, &mut state.free_length, n); }
                if site == 3 { Attribution::add(&mut state.invalid, &mut state.resident_length, n); }
            }
            Err(failure) => if state.rejected.is_none() {
                state.rejected = Some(AttributionRejected { site: state.site, function: cursor.function,
                    offset: cursor.offset, n, failure: *failure });
            },
        }
    });
}
pub(super) fn attribution_lookup_done(hit: bool) {
    attribution_mut(|state| {
        if hit {
            Attribution::add(&mut state.invalid, &mut state.hits, 1);
            Attribution::histogram(&mut state.invalid, &mut state.hit_histogram, state.resident_length);
        } else { Attribution::add(&mut state.invalid, &mut state.misses, 1); }
    });
}
pub(super) fn attribution_decode_completed(function: u32) {
    attribution_mut(|state| {
        let index = function as usize;
        if index >= 80_000 { state.invalid |= 8; return; }
        let word = index / 64;
        let mask = 1u64 << (index % 64);
        if state.seen[word] & mask == 0 {
            state.seen[word] |= mask;
            Attribution::add(&mut state.invalid, &mut state.distinct, 1);
        } else {
            Attribution::add(&mut state.invalid, &mut state.repeated, 1);
            if !state.samples[..state.sample_len].contains(&function) {
                if state.sample_len < 16 { state.samples[state.sample_len] = function; state.sample_len += 1; }
                else { Attribution::add(&mut state.invalid, &mut state.untracked_repeated_occurrences, 1); }
            }
        }
    });
}
fn attribution_state() -> Attribution {
    ATTRIBUTION.with(|state| match state.try_borrow() {
        Ok(state) => { let mut snapshot = state.clone(); if ATTRIBUTION_BORROW_INVALID.with(Cell::get) { snapshot.invalid |= 16; } snapshot }
        Err(_) => { let mut snapshot = Attribution::empty(); snapshot.invalid = 16; snapshot }
    })
}
pub(super) fn attribution_json(work: u64, cache: Option<&SwiftCacheUsage>) -> (String, bool) {
    // Snapshot serialization is bounded, external test overhead. Never serialize seen words.
    let s = attribution_state();
    let successful = s.credits.iter().try_fold(0u64, |sum, n| sum.checked_add(*n));
    let decodes = s.distinct.checked_add(s.repeated);
    let population: u64 = s.seen.iter().map(|word| word.count_ones() as u64).sum();
    let reconciled = s.invalid == 0 && s.enabled && successful == Some(work) && population == s.distinct
        && cache.is_none_or(|c| s.hits == c.hits && s.misses == c.misses && decodes == Some(c.decodes)
            && c.decodes <= c.misses && c.evictions <= c.decodes
            && c.decodes - c.evictions <= 64);
    let rejected = s.rejected.map(|r| format!("{{\"site\":\"{}\",\"site_index\":{},\"function\":{},\"offset\":{},\"requested\":{},\"code\":\"{}\",\"kind\":\"{:?}\",\"resource\":\"{:?}\",\"attempted\":{},\"limit\":{}}}",
        ATTRIBUTION_SITES.get(r.site as usize).unwrap_or(&"invalid"), r.site,
        r.function.map_or("null".into(), |n| n.to_string()), r.offset.map_or("null".into(), |n| n.to_string()),
        r.n, r.failure.code, r.failure.kind, r.failure.resource, r.failure.attempted, r.failure.limit)).unwrap_or("null".into());
    let authority = cache.map(|c| format!("{{\"hits\":{},\"misses\":{},\"decodes\":{},\"evictions\":{},\"resident_bytes\":{},\"eviction_scope\":\"authoritative total, no independent eviction event\"}}", c.hits,c.misses,c.decodes,c.evictions,c.resident_bytes)).unwrap_or("null".into());
    let result = format!("{{\"enabled\":{},\"invalid_flags\":{},\"successful_credits\":{:?},\"work_calls\":{:?},\"authoritative_cache_work\":{},\"successful_sum\":{},\"free_pin_probe_length_histogram\":{:?},\"resident_hit_probe_length_histogram\":{:?},\"hits\":{},\"misses\":{},\"distinct_completed_decodes\":{},\"repeated_completed_decodes\":{},\"authoritative_cache_totals\":{},\"observer_state_bytes\":{},\"seen_bitmap_bytes\":10000,\"seen_population\":{},\"first_repeated_function_identities\":{:?},\"untracked_repeated_completion_occurrences\":{},\"first_rejected_work\":{},\"reconciled\":{},\"test_only_external_overhead\":true,\"cpu_profile\":false}}",
        s.enabled, s.invalid, s.credits, s.calls, work, successful.map_or("null".into(), |n| n.to_string()), s.free_histogram, s.hit_histogram,
        s.hits, s.misses, s.distinct, s.repeated, authority, std::mem::size_of::<Attribution>(), population, &s.samples[..s.sample_len], s.untracked_repeated_occurrences, rejected, reconciled);
    if result.len() > 16_384 { return ("{\"serialization_invalid\":true,\"reconciled\":false}".into(), false); }
    (result, reconciled)
}
