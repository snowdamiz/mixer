//! Independently authored actual-source controls. No producer checker imported.
use super::*;

fn next(seed: &mut u64) -> u64 {
    *seed ^= *seed << 13;
    *seed ^= *seed >> 7;
    *seed ^= *seed << 17;
    *seed
}

fn times(mode: usize, seed: u64) -> [u64; 64] {
    let mut state = seed | 1;
    std::array::from_fn(|i| match mode % 9 {
        0 => i as u64,
        1 => (63 - i) as u64,
        2 => 0,
        3 => u64::MAX,
        4 => if i % 3 == 0 { u64::MAX } else { (i % 5) as u64 },
        5 => (i as u64).reverse_bits() >> 58,
        6 => next(&mut state),
        7 => (i / 2) as u64,
        _ => u64::MAX - (i % 7) as u64,
    })
}

fn sorted(mask: u64, stamps: &[u64; 64]) -> Vec<u8> {
    // This oracle uses the standard library's tuple ordering, not merge code.
    let mut pairs: Vec<_> = (0..64).filter(|i| (mask >> i) & 1 == 1)
        .map(|i| (stamps[i], i as u8)).collect();
    pairs.sort_unstable();
    pairs.into_iter().map(|(_, slot)| slot).collect()
}

fn actual_merge(mask: u64, stamps: [u64; 64], fill: u8) {
    let mut candidate = [fill; 2048];
    for (i, value) in stamps.iter().enumerate() {
        candidate[i * 8..i * 8 + 8].copy_from_slice(&value.to_le_bytes());
    }
    candidate[640..648].copy_from_slice(&mask.to_le_bytes());
    let before = candidate;
    let expected = sorted(mask, &stamps);
    SORT_COMPARISONS.store(0, std::sync::atomic::Ordering::Relaxed);
    SORT_MOVES.store(0, std::sync::atomic::Ordering::Relaxed);
    merge(&mut candidate);
    assert_eq!(&candidate[512..512 + expected.len()], expected.as_slice(), "mask {mask:#018x}");
    assert!(candidate[512 + expected.len()..576].iter().all(|v| *v == 255));
    // Only the two declared byte-index regions are writable by this function.
    for range in [0..512, 576..1024, 1088..2048] {
        assert_eq!(&candidate[range.clone()], &before[range]);
    }
    assert_eq!(SORT_MOVES.load(std::sync::atomic::Ordering::Relaxed), 320);
    assert!(SORT_COMPARISONS.load(std::sync::atomic::Ordering::Relaxed) <= 289);
    let mut observed = 0;
    for &slot in &candidate[512..512 + expected.len()] {
        assert!(slot < 64);
        let bit = 1u64 << slot;
        assert_eq!(observed & bit, 0);
        observed |= bit;
    }
    assert_eq!(observed, mask);
}

#[test]
fn scalar_cursor_independent_merge_extremes_and_singletons() {
    let mut cases = 0;
    for mask in [0, u64::MAX, 0x5555555555555555, 0xaaaaaaaaaaaaaaaa,
        0x8000000000000001, 0x0000000180000000, 0x00000000ffffffff, 0xffffffff00000000] {
        for mode in 0..9 { actual_merge(mask, times(mode, mask), mode as u8 * 17); cases += 1; }
    }
    for slot in 0..64 { for mask in [1u64 << slot, !(1u64 << slot)] {
        for mode in 0..9 { actual_merge(mask, times(mode, slot), 0xd3); cases += 1; }
    }}
    println!("independent_merge_extreme_cases={cases}");
}

#[test]
fn scalar_cursor_independent_merge_every_pair_and_missing_pair() {
    let mut cases = 0;
    for left in 0..64 { for right in left + 1..64 {
        let mask = (1u64 << left) | (1u64 << right);
        for (m, mode) in [(mask, 3), (!mask, 4), (mask, 1), (!mask, 5)] {
            actual_merge(m, times(mode, mask), 0x5e); cases += 1;
        }
    }}
    println!("independent_merge_pair_cases={cases}");
}

#[test]
fn scalar_cursor_independent_merge_window_masks_and_random() {
    let mut cases = 0;
    for offset in [0, 8, 24, 56] { for small in 0..256u64 { for mode in [3, 4, 6] {
        actual_merge(small << offset, times(mode, small + offset), 0xc7); cases += 1;
    }}}
    let mut seed = 0x1756e4caf39082b1;
    for i in 0..4096 {
        let mask = next(&mut seed);
        actual_merge(mask, times(i % 9, seed), (i % 256) as u8); cases += 1;
    }
    println!("independent_merge_window_random_cases={cases}");
}

#[derive(Clone, Copy)]
struct Row { occupied: u64, function: u64, bytes: u64, pins: u64, time: u64, generation: u64, r6: u64, r7: u64 }
impl Row {
    fn empty() -> Self { Self { occupied: 0, function: u64::MAX, bytes: 0, pins: 0, time: u64::MAX, generation: u64::MAX, r6: 0, r7: 0 } }
    fn resident(bytes: u64, time: u64, pins: u64) -> Self { Self { occupied: 1, function: 100, bytes, pins, time, generation: u64::MAX, r6: 0, r7: 0 } }
    fn words(self) -> [u64; 8] { [self.occupied, self.function, self.bytes, self.pins, self.time, self.generation, self.r6, self.r7] }
}

struct State {
    rows: [Row; 64], slots: usize, pin_limit: u64,
    tokens: Vec<(u64, u64)>, prior_count: u64, prior_total: u64, prior_pins: u64, nonce: u64,
    base: u64, request: u64, capacity: u64, entry: u64,
}
impl State {
    fn valid(rows: [Row; 64], slots: usize, base: u64, request: u64, capacity: u64) -> Self {
        let mut tokens = Vec::new();
        let mut count = 0;
        let mut sum = 0u128;
        let mut pins = 0;
        for (slot, row) in rows[..slots].iter().enumerate() { if row.occupied == 1 {
            count += 1; sum += row.bytes as u128; pins += row.pins;
            for _ in 0..row.pins { tokens.push((slot as u64, tokens.len() as u64 + 1)); }
        }}
        assert!(sum <= u64::MAX as u128 && tokens.len() <= 64);
        Self { rows, slots, pin_limit: 64, tokens, prior_count: count, prior_total: sum as u64,
            prior_pins: pins, nonce: 65, base, request, capacity, entry: u64::MAX }
    }
}

fn materialize(arena: &mut [u8], state: &State) {
    arena[RESIDENT.base..PIN.base + 64 * 48].fill(0);
    arena[SCALAR.base..SCALAR.base + 2048].fill(0);
    for slot in 0..64 {
        for (field, word) in state.rows[slot].words().into_iter().enumerate() {
            st(arena, RESIDENT.base + 64 * slot + 8 * field, word);
        }
        st(arena, PIN.base + 48 * slot, u64::MAX);
    }
    for (pin, &(slot, nonce)) in state.tokens.iter().enumerate() {
        st(arena, PIN.base + 48 * pin, slot);
        st(arena, PIN.base + 48 * pin + 8, nonce);
    }
    arena[FUNCTION.base + 7 * 96 + 20..FUNCTION.base + 7 * 96 + 24].copy_from_slice(&1u32.to_le_bytes());
    for (field, word) in [7, 32, 4, 1, 0].into_iter().enumerate() {
        st(arena, PLAN.base + 7 * 40 + 8 * field, word);
    }
}

fn run_semantic(arena: &mut [u8], state: &State) -> (SemanticReply, Candidate2048) {
    let config = Fixture { cap: 1, mask: 33, extent: 1000, types: 2, slots: state.slots as u64,
        pins: state.pin_limit, base: state.base, capacity: state.capacity, entry: state.entry };
    let mut progress = Progress { calls: 5, latch: 0, q: [0; 16] };
    progress.q[3] = 5; progress.q[4] = 1; progress.q[5] = 7;
    progress.q[6] = state.prior_count; progress.q[7] = state.prior_total;
    progress.q[8] = state.prior_pins; progress.q[9] = state.nonce;
    let words = [6, 5, 0, 1, 60, 6, 7, 32, 4, 1, ABSENT, ABSENT, 0,
        state.request, state.base, state.capacity];
    let record = FixtureDecodedRecordV1 { words: &words };
    let loan = Loan { record: &record, config: &config };
    let mut candidate = [0xa9; 2048];
    let mut budget = StepBudget { remaining: 7681, spent: 0 };
    let reply = semantic(arena, &mut candidate, &loan, &progress, &mut budget);
    assert_eq!((budget.remaining, budget.spent), (1, 7680));
    (reply, candidate)
}

fn check_valid(arena: &mut [u8], state: &State) {
    // Compute with u128, independently of G5's ordinary u64 subtraction.
    let mut remaining: u128 = state.rows[..state.slots].iter()
        .filter(|row| row.occupied == 1).map(|row| row.bytes as u128).sum();
    let mut destination = state.rows[..state.slots].iter().position(|row| row.occupied == 0).map(|v| v as u64).unwrap_or(ABSENT);
    let headroom = state.capacity as u128 - state.base as u128 - state.request as u128;
    let mut eligible: Vec<_> = state.rows[..state.slots].iter().enumerate()
        .filter(|(_, row)| row.occupied == 1 && row.pins == 0)
        .map(|(slot, row)| (row.time, slot)).collect();
    eligible.sort_unstable();
    let mut chosen = 0u64;
    for (_, slot) in eligible {
        if remaining <= headroom && destination != ABSENT { break; }
        assert!(remaining >= state.rows[slot].bytes as u128);
        remaining -= state.rows[slot].bytes as u128;
        chosen |= 1 << slot;
        destination = slot as u64;
    }
    let feasible = destination != ABSENT && remaining <= headroom;
    materialize(arena, state);
    let resident_before = arena[RESIDENT.base..PIN.base + 64 * 48].to_vec();
    let (reply, candidate) = run_semantic(arena, state);
    assert_eq!((reply.status, reply.reason, reply.debit), (1, 0, 7680));
    assert_eq!(&arena[RESIDENT.base..PIN.base + 64 * 48], resident_before.as_slice());
    assert_eq!(cq(&candidate, 10), chosen);
    assert_eq!(cq(&candidate, 11), 0);
    assert_eq!(cq(&candidate, 12), 0);
    assert_eq!(cq(&candidate, 13), ABSENT);
    assert_eq!(cq(&candidate, 14), if feasible { destination } else { ABSENT });
    assert_eq!(cq(&candidate, 15), u64::from(feasible));
    assert_eq!(cq(&candidate, 7), state.prior_total);
}

#[test]
fn scalar_cursor_independent_g2_admitted_g5_u64_boundaries() {
    let mut arena = vec![0; ARENA_BYTES];
    let mut rows = [Row::empty(); 64];
    let mut cases = 0;
    rows[0] = Row::resident(u64::MAX, u64::MAX, 0);
    check_valid(&mut arena, &State::valid(rows, 2, 0, 1, u64::MAX)); cases += 1;
    rows[0].pins = 1;
    check_valid(&mut arena, &State::valid(rows, 2, 0, 1, u64::MAX)); cases += 1;
    rows[0] = Row::resident(u64::MAX - 1, u64::MAX, 0);
    rows[1] = Row::resident(1, u64::MAX, 0);
    check_valid(&mut arena, &State::valid(rows, 2, 0, u64::MAX, u64::MAX)); cases += 1;
    rows[0] = Row::resident(2, u64::MAX, 0); rows[1] = Row::resident(3, 0, 0);
    check_valid(&mut arena, &State::valid(rows, 3, u64::MAX - 5, 5, u64::MAX)); cases += 1;
    for pins in [0, 1] {
        let full = [Row::resident(1, u64::MAX, pins); 64];
        check_valid(&mut arena, &State::valid(full, 64, 0, 1, u64::MAX)); cases += 1;
    }
    check_valid(&mut arena, &State::valid([Row::empty(); 64], 64, u64::MAX - 1, 1, u64::MAX)); cases += 1;
    // G2 admits duplicate nonrequested functions, arbitrary generations, and
    // aggregate-consistent token distribution without a per-row bijection.
    rows = [Row::empty(); 64];
    rows[0] = Row::resident(3, u64::MAX, 1); rows[1] = Row::resident(5, 0, 1);
    rows[2] = Row::resident(7, u64::MAX, 0);
    let mut unusual = State::valid(rows, 4, 0, 7, 12);
    unusual.tokens = vec![(0, 1), (0, 1)];
    check_valid(&mut arena, &unusual); cases += 1;
    println!("independent_actual_semantic_u64_and_unusual_cases={cases}");
}

#[test]
fn scalar_cursor_independent_g2_admitted_random_g5_oracle() {
    let mut arena = vec![0; ARENA_BYTES];
    let mut seed = 0xe7eac1c9a3927f65;
    for case in 0..2048 {
        let slots = 1 + next(&mut seed) as usize % 64;
        let mut rows = [Row::empty(); 64];
        for row in &mut rows[..slots] {
            if next(&mut seed) % 4 != 0 {
                *row = Row::resident(1 + next(&mut seed) % 4096,
                    if case % 3 == 0 { u64::MAX } else { next(&mut seed) % 11 },
                    u64::from(next(&mut seed) % 5 == 0));
                row.generation = next(&mut seed);
            }
        }
        let base = next(&mut seed) % 1024;
        let request = 1 + next(&mut seed) % 512;
        let capacity = base + request + next(&mut seed) % 60000;
        check_valid(&mut arena, &State::valid(rows, slots, base, request, capacity));
    }
    println!("independent_actual_semantic_random_cases=2048");
}

#[test]
fn scalar_cursor_independent_malformed_g2_and_request_refuse_without_arena_mutation() {
    let mut arena = vec![0; ARENA_BYTES];
    let mut cases = 0;
    for kind in 0..27 {
        let mut rows = [Row::empty(); 64];
        rows[0] = Row::resident(3, 7, 1); rows[1] = Row::resident(4, u64::MAX, 0);
        let mut state = State::valid(rows, 3, 0, 5, 10);
        let reason = match kind {
            0 => { state.rows[0].occupied = 2; 13 },
            1 => { state.rows[0].pins = 65; 13 },
            2 => { state.rows[0].r6 = 1; 13 },
            3 => { state.rows[0].r7 = 1; 13 },
            4 => { state.rows[0].function = 80000; 13 },
            5 => { state.rows[0].bytes = 0; 13 },
            6 => { state.entry = 2; 13 },
            7 => { state.rows[2].function = 99; 13 },
            8 => { state.rows[2].bytes = 1; 13 },
            9 => { state.rows[2].pins = 1; 13 },
            10 => { state.rows[0].bytes = u64::MAX; 10 },
            11 => { state.prior_total += 1; 13 },
            12 => { state.prior_count += 1; 13 },
            13 => { state.rows[0].function = 7; state.rows[1].function = 7; 7 },
            14 => { state.tokens[0].0 = 3; 13 },
            15 => { state.tokens[0].1 = 0; 13 },
            16 => { state.tokens[0].1 = 65; 13 },
            17 => { state.tokens.push((ABSENT, 1)); 13 },
            18 => { state.tokens[0].0 = 2; 13 },
            19 => { state.tokens[0].0 = 1; 13 },
            20 => { state.prior_pins = 0; 13 },
            21 => { state.tokens.clear(); 13 },
            22 => { state.nonce = 0; 13 },
            23 => { state.base = u64::MAX; state.request = 1; state.capacity = u64::MAX; 10 },
            24 => { state.request = 0; 10 },
            25 => { state.entry = 4; state.request = 5; 10 },
            _ => { state.capacity = 4; 10 },
        };
        materialize(&mut arena, &state);
        let before = arena.clone();
        let (reply, _) = run_semantic(&mut arena, &state);
        assert_eq!((reply.status, reply.reason, reply.debit), (2, reason, 7680), "malformed kind {kind}");
        assert_eq!(arena, before, "malformed kind {kind}");
        cases += 1;
    }
    println!("independent_actual_malformed_cases={cases}");
}

#[test]
fn scalar_cursor_independent_complete_layouts() {
    use std::mem::{align_of, size_of};
    let observed = [size_of::<Candidate2048>(), size_of::<&Candidate2048>(),
        size_of::<&[u8; 64]>(), size_of::<Option<&[u8; 64]>>(), size_of::<&[[u8; 8]; 64]>(),
        size_of::<Option<&[[u8; 8]; 64]>>(), size_of::<&[u8]>(), size_of::<&mut [u8]>(),
        size_of::<Option<&[u8]>>(), size_of::<u8>(), size_of::<u16>(), size_of::<usize>(),
        size_of::<Progress>(), size_of::<Paid>(), size_of::<Loan<'_>>(), size_of::<SemanticReply>(),
        size_of::<Fixture>(), size_of::<Option<Fixture>>(), size_of::<FixtureCacheStateObservationV1>(),
        size_of::<FixtureCacheStateOutcomeV1>(), size_of::<Result<FixtureCacheStateOutcomeV1, AnalyzerError>>()];
    assert_eq!(observed, [2048, 8, 8, 8, 8, 8, 16, 16, 16, 1, 2, 8, 144, 24, 16, 24, 72, 80, 256, 488, 488]);
    assert_eq!(align_of::<FixtureCacheStateOutcomeV1>(), 8);
    println!("independent_complete_layouts={observed:?}");
}
