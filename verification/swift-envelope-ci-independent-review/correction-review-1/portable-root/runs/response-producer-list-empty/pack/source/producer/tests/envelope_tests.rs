use super::*;
use std::mem::size_of;

fn put(b: &mut [u8], i: usize, n: u64) { b[i * 8..i * 8 + 8].copy_from_slice(&n.to_le_bytes()); }
fn word(b: &[u8], i: usize) -> u64 { u64::from_le_bytes(b[i * 8..i * 8 + 8].try_into().unwrap()) }
fn encoding(w: &[u64]) -> Vec<u8> { w.iter().flat_map(|n| n.to_le_bytes()).collect() }
fn event(k: u64) -> [u64; 16] {
    let mut w = [0, k, 0, 1, 0, 0, 7, 20, 8, 1, ABSENT, ABSENT, 0, 0, 0, 0];
    match k {
        1 => w[7..10].fill(ABSENT),
        2 => {}, 3 => w[15] = 7,
        4 => { w[14] = ABSENT; w[15] = 7; },
        5 => w[13..16].copy_from_slice(&[64, 16, 4096]),
        6..=8 => { w[10] = 0; w[13] = 64; },
        9 | 10 => w[13] = 64,
        11 => w[10..16].copy_from_slice(&[0, 0, 1, 1, 64, 1]),
        12 => { w[3] = 0; w[8] = ABSENT; w[10..16].copy_from_slice(&[0, 0, 1, 64, 0, 0]); },
        13 => { w[2] = 5; w[3] = 0; w[6..10].fill(ABSENT); w[13] = 5; },
        14 => { w[3] = 0; w[6..10].fill(ABSENT); w[13..16].copy_from_slice(&[2, 1, 2]); },
        _ => unreachable!(),
    } w
}
fn ordered(mut records: Vec<[u64; 16]>) -> Vec<[u64; 16]> {
    for (i, w) in records.iter_mut().enumerate() { w[0] = i as u64 + 1; w[4] = i as u64 * 10; w[5] = i as u64 * 2; } records
}
fn miss() -> Vec<[u64; 16]> { ordered([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13].into_iter().map(event).collect()) }
fn hit() -> Vec<[u64; 16]> {
    let mut v = vec![event(1), event(2), event(11), event(12), event(13)];
    v[1][10] = 0; v[1][13] = 1; v[2][13] = 0;
    v[3][6] = 8; v[3][7] = 28; ordered(v)
}
struct Transport {
    bytes: Vec<u8>, position: usize, identity: u64, declared: Option<usize>,
    stamps: usize, drift_at: usize, fail_stamp_at: usize, read_calls: usize,
    fail_read_at: usize, quantum: usize, writes: usize, fail_write: bool,
}
impl Transport {
    fn new(bytes: Vec<u8>, identity: u64) -> Self { Self { bytes, position: 0, identity, declared: None, stamps: 0, drift_at: usize::MAX, fail_stamp_at: usize::MAX, read_calls: 0, fail_read_at: usize::MAX, quantum: usize::MAX, writes: 0, fail_write: false } }
    fn stamp_value(&mut self) -> io::Result<Stamp> {
        self.stamps += 1;
        if self.stamps == self.fail_stamp_at { return Err(io::ErrorKind::Other.into()); }
        Ok(Stamp { fields: [9, self.identity + u64::from(self.stamps >= self.drift_at), 0o100600, self.declared.unwrap_or(self.bytes.len()) as u64, 0, 0, 0, 0], regular: 1 })
    }
}
impl Read for Transport {
    fn read(&mut self, b: &mut [u8]) -> io::Result<usize> {
        self.read_calls += 1;
        if self.read_calls == self.fail_read_at { return Err(io::ErrorKind::PermissionDenied.into()); }
        let n = b.len().min(self.quantum).min(self.bytes.len().saturating_sub(self.position));
        b[..n].copy_from_slice(&self.bytes[self.position..self.position + n]); self.position += n; Ok(n)
    }
}
impl Write for Transport {
    fn write(&mut self, b: &[u8]) -> io::Result<usize> {
        self.writes += 1;
        if self.fail_write { return Err(io::ErrorKind::BrokenPipe.into()); }
        let n = b.len().min(self.quantum); self.bytes.extend_from_slice(&b[..n]); self.position += n; Ok(n)
    }
    fn flush(&mut self) -> io::Result<()> { Ok(()) }
}
impl InputFile for Transport { fn stamp(&mut self) -> io::Result<Stamp> { self.stamp_value() } fn position(&mut self) -> io::Result<u64> { Ok(self.position as u64) } }
impl OutputFile for Transport { fn stamp(&mut self) -> io::Result<Stamp> { self.stamp_value() } fn position(&mut self) -> io::Result<u64> { Ok(self.position as u64) } }
fn inputs(records: &[[u64; 16]], cap: bool) -> [Transport; 4] {
    let cap_limit = if cap { records.len() as u64 } else { 5000 };
    let mut context = vec![0; 8192];
    for (i, n) in [FIXTURE_MAGIC, 1, 8192, 1, cap_limit, 33, 1000, 2, 4, 4, 1, 16, 4096, 512, 0, 0].into_iter().enumerate() { put(&mut context, i, n); }
    let mut profile = vec![0; PROFILE_BYTES as usize];
    for (i, n) in [PROFILE_MAGIC, 1, 512, 32, 80_000, 1000, 2, 4, 4, 1, 16, 4096, 512, 0, 0, 0].into_iter().enumerate() { put(&mut profile, i, n); }
    for i in 0..80_000 { put(&mut profile, 64 + 4 * i, (u32::MAX as u64) << 32); put(&mut profile, 65 + 4 * i, ABSENT); }
    for (i, offset) in [(7, 20), (8, 28)] { put(&mut profile, 64 + 4 * i, (1u64 << 32) | 1); put(&mut profile, 65 + 4 * i, offset); put(&mut profile, 66 + 4 * i, 8); }
    let mut h = [0; 64]; h[..10].copy_from_slice(&[HEADER_MAGIC, 1, 512, 128, 512, cap_limit, 80_000, 64, 512, 33]);
    let mut stream = encoding(&h); for w in records { stream.extend(encoding(w)); }
    let last = records.last().copied().unwrap_or([0; 16]);
    let operation = records.iter().filter(|w| w[1] == 1).map(|w| w[3]).next_back().unwrap_or(0);
    let mut ft = [0; 64]; ft[..16].copy_from_slice(&[FOOTER_MAGIC, 1, records.len() as u64, records.len() as u64 + u64::from(cap), u64::from(cap), records.len() as u64, last[4], last[5], operation, u64::from(cap), last[4], last[5], 0, 0, ABSENT, 33]);
    ft[33] = 5; ft[34] = 1; ft[35] = cap_limit; stream.extend(encoding(&ft));
    [Transport::new(stream, 101), Transport::new(profile, 102), Transport::new(context, 103), Transport::new(vec![], 104)]
}
fn invoke(x: &mut [Transport; 4], limit: u64) -> Result<FixtureEnvelopeOutcomeV1, AnalyzerError> {
    let [s, p, c, o] = x; analyze_fixture_envelope_core(s, p, c, o, limit)
}
fn assert_unaccepted(x: &FixtureEnvelopeOutcomeV1, output: &Transport) {
    assert!(!x.stored_prefix_validated()); assert!(!x.full_replay_accepted()); assert!(!x.envelope().semantic_metrics_valid());
    assert!(!x.framing().stored_prefix_validated()); assert!(!x.framing().full_replay_accepted());
    assert_eq!(output.bytes.len(), REPORT_BYTES); assert_eq!(word(&output.bytes, 1), 1);
    assert_eq!(word(&output.bytes, 4), 0); assert_eq!(word(&output.bytes, 5), 0);
    assert_eq!(word(&output.bytes, 15), u64::from(x.framing().fixture_framing_observed()));
    assert!(output.bytes[512..].iter().all(|b| *b == 0));
}
fn zero_extent(x: &FixtureEnvelopeObservationV1) {
    assert_eq!([x.observed_records(), x.state(), x.phase(), x.mask(), x.last_operation(), x.active_operation(), x.requested_function(), x.pin_failure(), x.terminal_failure(), x.last_work(), x.last_instructions()], [0; 11]);
}
fn arena_state(arena: &mut Arena, s: &[u64; 12]) { for i in 0..12 { put(&mut arena.bytes, SCALAR.base / 8 + CELLS[i], s[i]); } }
fn blank_progress() -> FixtureEnvelopeProgressV1 { FixtureEnvelopeProgressV1 { reply_valid: 0, debit: 581, reply: FixtureEnvelopeReplyV1 { words: [0; 16] } } }
fn initial_state() -> [u64; 12] { [0, 0, 0, 0, 0, 1, 33, 0, 0, 0, 0, 0] }

#[test]
fn separate_public_types_complete_value_layouts() {
    println!("ENVELOPE_LAYOUT Observation={} Outcome={} Result={} Progress={} Reply={} StepBudget={} CheckedPair={} DecodedRecord={} ObservationResult={} OptionalError={} OptionalU64={} SliceOption={} MutableSliceOption={} Slice={} Candidate={} CandidateBorrow={}", size_of::<FixtureEnvelopeObservationV1>(), size_of::<FixtureEnvelopeOutcomeV1>(), size_of::<Result<FixtureEnvelopeOutcomeV1, AnalyzerError>>(), size_of::<FixtureEnvelopeProgressV1>(), size_of::<FixtureEnvelopeReplyV1>(), size_of::<StepBudget>(), size_of::<CheckedPair>(), size_of::<FixtureDecodedRecordV1>(), size_of::<Result<FixtureEnvelopeObservationV1, AnalyzerError>>(), size_of::<Option<AnalyzerError>>(), size_of::<Option<u64>>(), size_of::<Option<&[u8]>>(), size_of::<Option<&mut [u8]>>(), size_of::<&mut [u8]>() , size_of::<Candidate2048>(), size_of::<&mut Candidate2048>());
    assert_eq!((size_of::<FixtureEnvelopeObservationV1>(), size_of::<FixtureEnvelopeOutcomeV1>(), size_of::<Result<FixtureEnvelopeOutcomeV1, AnalyzerError>>()), (128, 232, 232));
    assert_eq!((size_of::<FixtureEnvelopeProgressV1>(), size_of::<FixtureEnvelopeReplyV1>(), size_of::<StepBudget>(), size_of::<CheckedPair>(), size_of::<FixtureDecodedRecordV1>()), (144, 128, 16, 16, 8));
    println!("CHECKED_ARRAY_LAYOUT OptionArrayBorrow={} ArrayBorrow={} Array8={} Pair={}", size_of::<Option<&[u8; 8]>>(), size_of::<&[u8; 8]>(), size_of::<[u8; 8]>(), size_of::<CheckedPair>());
    assert_eq!((size_of::<Option<&[u8; 8]>>(), size_of::<&[u8; 8]>(), size_of::<[u8; 8]>()), (8, 8, 8));
    assert_eq!(WRAPPER_GROUPS.iter().sum::<u64>(), WRAPPER_STEPS); assert_eq!(COMBINED_RECORD, 471); assert!(COMBINED_RECORD <= RECORD_PREFLIGHT);
}
#[test]
fn complete_hit_miss_eviction_release_and_phases_have_fixture_observations_only() {
    for events in [hit(), miss(), ordered(vec![event(13)])] {
        let mut x = inputs(&events, false); let out = invoke(&mut x, STEP_LIMIT).unwrap();
        assert_eq!(out.envelope().boundary(), &FixtureEnvelopeBoundaryV1::ClosedEnvelopeObserved);
        assert_eq!(out.envelope().observed_records(), events.len() as u64); assert_eq!(out.envelope().envelope_debit(), 581 + 425 * events.len() as u64);
        assert_eq!(out.framing().decision, Decision::Unavailable); assert!(out.framing().fixture_framing_observed()); assert_unaccepted(&out, &x[3]);
    }
}
#[test]
fn cap_at_every_legal_path_position_preserves_actual_open_state() {
    let events = miss();
    for n in 1..=events.len() { let mut x = inputs(&events[..n], true); let out = invoke(&mut x, STEP_LIMIT).unwrap();
        assert_eq!(out.envelope().boundary(), &FixtureEnvelopeBoundaryV1::CapCutUnknownTail, "cut {n}");
        assert_eq!(out.envelope().observed_records(), n as u64); assert_eq!(out.envelope().envelope_debit(), 581 + 425 * n as u64); assert_unaccepted(&out, &x[3]); }
}
#[test]
fn impossible_stages_refuse_but_preserve_framing_and_pay_skipped_leaf_subdivisions() {
    let events = ordered(vec![event(1), event(10), event(9), event(13)]);
    let mut x = inputs(&events, false); let out = invoke(&mut x, STEP_LIMIT).unwrap();
    assert!(out.framing().fixture_framing_observed()); assert_eq!(out.framing().framed_records, 4);
    assert_eq!(out.envelope().boundary(), &FixtureEnvelopeBoundaryV1::Refused); assert_eq!(out.envelope().reason(), &FixtureEnvelopeReasonV1::Stage);
    assert_eq!(out.envelope().observed_records(), 1); assert_eq!(out.envelope().state(), 1); assert_eq!(out.envelope().envelope_debit(), 2281); assert_unaccepted(&out, &x[3]);
}
#[test]
fn failure_cursor_may_be_absent_or_independent_and_idle_release_after_failures() {
    for cursor in [ABSENT, 8] {
        let mut failure = event(14); failure[3] = 1; failure[6] = cursor;
        let mut release = event(12); release[6] = 8; release[7] = 28;
        let events = ordered(vec![event(1), failure, release, event(14), event(13)]);
        let mut x = inputs(&events, false); let out = invoke(&mut x, STEP_LIMIT).unwrap();
        assert_eq!(out.envelope().boundary(), &FixtureEnvelopeBoundaryV1::ClosedEnvelopeObserved); assert_eq!(out.envelope().pin_failure(), 1); assert_eq!(out.envelope().terminal_failure(), 1); assert_unaccepted(&out, &x[3]);
    }
}
#[test]
fn later_footer_eof_and_each_input_metadata_error_suppress_previous_leaf_results() {
    for records in [miss(), ordered(vec![event(1), event(10), event(13)])] { for mode in 0..5 {
        let mut x = inputs(&records, false);
        match mode { 0 => { let last = x[0].bytes.len() / 8 - 1; put(&mut x[0].bytes, last, 1); }, 1 => { x[0].declared = Some(x[0].bytes.len()); x[0].bytes.push(1); }, 2..=4 => x[mode - 2].drift_at = 3, _ => unreachable!() }
        let out = invoke(&mut x, STEP_LIMIT).unwrap(); assert_eq!(out.framing().decision, Decision::Invalid);
        assert_eq!(out.envelope().boundary(), &FixtureEnvelopeBoundaryV1::Unavailable); assert_eq!(out.envelope().reason(), &FixtureEnvelopeReasonV1::FramingInvalid);
        zero_extent(out.envelope()); assert_eq!(out.envelope().envelope_debit(), 581 + 425 * records.len() as u64); assert_unaccepted(&out, &x[3]);
    }}
}
#[test]
fn all_early_input_domains_refuse_without_fabricated_reply() {
    for mode in 0..5 { let mut x = inputs(&ordered(vec![event(13)]), false);
        match mode { 0 => put(&mut x[2].bytes, 0, 0), 1 => put(&mut x[2].bytes, 1, 2), 2 => put(&mut x[1].bytes, 0, 0), 3 => put(&mut x[0].bytes, 0, 0), 4 => x[0].fail_read_at = 1, _ => unreachable!() }
        let out = invoke(&mut x, STEP_LIMIT).unwrap(); assert_eq!(out.envelope().boundary(), &FixtureEnvelopeBoundaryV1::Unavailable); zero_extent(out.envelope()); assert_eq!(out.envelope().envelope_debit(), 0);
        assert_eq!(out.envelope().reason(), if mode == 0 { &FixtureEnvelopeReasonV1::FramingUnavailable } else { &FixtureEnvelopeReasonV1::FramingInvalid }); assert_unaccepted(&out, &x[3]);
    }
}
#[test]
fn invalid_record_is_prepaid_before_decode_and_error_suppresses_extent() {
    let mut events = miss(); events[0][9] = 1;
    let mut x = inputs(&events, false); let out = invoke(&mut x, STEP_LIMIT).unwrap();
    assert_eq!(out.envelope().envelope_debit(), 1006); zero_extent(out.envelope()); assert_eq!(out.envelope().reason(), &FixtureEnvelopeReasonV1::FramingInvalid);
}
#[test]
fn limited_zero_call_is_absent_and_exact_preflight_never_calls_normal_finish() {
    let events = miss();
    let baseline = REPORT_RESERVE + IO_RESERVE + ARENA_BYTES as u64 / 8 + 640_000;
    let mut complete = baseline + 65_536;
    let mut low = baseline; let mut high = complete;
    while low < high { let mid = low + (high - low) / 2; let mut x = inputs(&events, false); let yes = invoke(&mut x, mid).is_ok_and(|x| x.framing().fixture_framing_observed()); if yes { high = mid; } else { low = mid + 1; } }
    complete = low;
    let mut x = inputs(&events, false); let out = invoke(&mut x, complete - 1).unwrap();
    assert_eq!(out.framing().decision, Decision::AnalysisLimited); assert_eq!(out.envelope().boundary(), &FixtureEnvelopeBoundaryV1::AnalysisLimited); assert_eq!(out.envelope().observed_records(), 11); assert_eq!(out.envelope().envelope_debit(), 581 + 11 * 425); assert_unaccepted(&out, &x[3]);
    let zero_limit = complete - COMBINED_RECORD * 12;
    let mut x = inputs(&events, false); let zero = invoke(&mut x, zero_limit).unwrap();
    assert_eq!(zero.framing().decision, Decision::AnalysisLimited); assert_eq!(zero.envelope().boundary(), &FixtureEnvelopeBoundaryV1::Unavailable); assert_eq!(zero.envelope().reason(), &FixtureEnvelopeReasonV1::EnvelopeUnavailable); zero_extent(zero.envelope()); assert_eq!(zero.envelope().envelope_debit(), 581);
    println!("ENVELOPE_BUDGET_COMPLETE={complete} PRIOR_COUNT={} ZERO_LIMIT={zero_limit}", out.envelope().observed_records());
}
#[test]
fn finalization_truth_table_complete_limited_absent_refused_poison_and_input_errors() {
    let mut arena = Arena { bytes: vec![0; ARENA_BYTES] }; arena_state(&mut arena, &initial_state());
    for limited in [false, true] { for status in 0..=3 {
        let mut p = blank_progress(); p.reply_valid = u64::from(status != 0); p.debit = 1431;
        p.reply.words = [status, if status == 2 { 12 } else if status == 3 { 15 } else { 0 }, 2, 1, 0, 1, 1, 1, 7, 0, 0, 10, 2, 425, 0, 0];
        let mut s = Framing::new(2); s.complete = !limited; s.limited = limited;
        let out = finalize(&p, &s, &Ok(!limited), &arena);
        let expected = match (limited, status) { (_, 0) => FixtureEnvelopeBoundaryV1::Unavailable, (true, _) => FixtureEnvelopeBoundaryV1::AnalysisLimited, (false, 1 | 2) => FixtureEnvelopeBoundaryV1::Refused, (false, 3) => FixtureEnvelopeBoundaryV1::InternalPoisoned, _ => unreachable!() };
        assert_eq!(out.boundary(), &expected); assert_eq!(out.envelope_debit(), 1431); if status == 0 || status == 3 { zero_extent(&out); }
        for code in [BINDING, BUDGET, IO_ERROR, SCHEMA, DRIFT] { let error = Err(error(code, RECORD_STAGE, 512, 3)); let refused = finalize(&p, &s, &error, &arena); assert_eq!(refused.boundary(), &FixtureEnvelopeBoundaryV1::Unavailable); zero_extent(&refused); assert_eq!(refused.envelope_debit(), 1431); assert_eq!(refused.reason(), if code == BINDING { &FixtureEnvelopeReasonV1::FramingUnavailable } else if code == BUDGET { &FixtureEnvelopeReasonV1::FramingLimited } else { &FixtureEnvelopeReasonV1::FramingInvalid }); }
    }}
}
#[test]
fn zero_reply_and_unsupported_values_never_become_observed_even_for_cap() {
    let arena = Arena { bytes: vec![0; ARENA_BYTES] };
    for limited in [false, true] { for flags in [0, 1] { let mut s = Framing::new(0); s.complete = !limited; s.limited = limited; s.flags = flags;
        let p = blank_progress(); let x = finalize(&p, &s, &Ok(!limited), &arena); assert_eq!(x.boundary(), &FixtureEnvelopeBoundaryV1::Unavailable); zero_extent(&x); assert_eq!(x.envelope_debit(), 581);
        for (index, value) in [(0, 0), (0, 2), (0, 99), (1, 12), (1, 99), (3, 11), (4, 6), (5, 64), (9, 2), (10, 2)] { let mut p = blank_progress(); p.reply_valid = 1; p.reply.words[0] = 1; p.reply.words[index] = value; let x = finalize(&p, &s, &Ok(!limited), &arena); assert_eq!(x.reason(), &FixtureEnvelopeReasonV1::UnavailableState); zero_extent(&x); }
    }}
}
#[test]
fn poison_precedes_cap_and_stale_state_and_does_not_resume() {
    let arena = Arena { bytes: vec![0; ARENA_BYTES] }; let mut p = blank_progress(); p.reply_valid = 1; p.reply = poisoned(425);
    for status in [1, 3] { p.reply.words[0] = status; p.reply.words[1] = 15; p.reply.words[3] = 99;
        for flags in [0, 1] { for limited in [false, true] { let mut s = Framing::new(1); s.complete = !limited; s.limited = limited; s.flags = flags; let out = finalize(&p, &s, &Ok(!limited), &arena); assert_eq!(out.reason(), &FixtureEnvelopeReasonV1::InternalPoisoned); zero_extent(&out); assert_eq!(out.boundary(), if limited { &FixtureEnvelopeBoundaryV1::AnalysisLimited } else { &FixtureEnvelopeBoundaryV1::InternalPoisoned }); }}
    }
}
#[test]
fn leaf_uses_one_candidate_and_only_twelve_cells_and_refusal_is_atomic() {
    let mut arena = Arena { bytes: vec![0; ARENA_BYTES] }; arena_state(&mut arena, &initial_state()); let before = arena.bytes.clone();
    let mut candidate = [0; 2048]; let address = candidate.as_ptr();
    for w in miss() { let mut steps = StepBudget { remaining: 425, spent: 0 }; let result = observe_fixture_envelope_v1(&mut arena.bytes, &mut candidate, &FixtureDecodedRecordV1 { words: &w }, &mut steps); assert_eq!(result.words[0], 1); assert_eq!(candidate.as_ptr(), address); assert!(candidate[..888].iter().all(|b| *b == 0)); assert!(candidate[984..].iter().all(|b| *b == 0)); assert_eq!((steps.remaining, steps.spent), (0, 425)); }
    for (i, b) in arena.bytes.iter().enumerate() { if !CELLS.iter().any(|cell| (SCALAR.base + cell * 8..SCALAR.base + cell * 8 + 8).contains(&i)) { assert_eq!(*b, before[i]); } }
    let unchanged = arena.bytes.clone(); let candidate_before = candidate; let w = ordered(vec![event(1)])[0]; let mut steps = StepBudget { remaining: 425, spent: 0 };
    let result = observe_fixture_envelope_v1(&mut arena.bytes, &mut candidate, &FixtureDecodedRecordV1 { words: &w }, &mut steps); assert_eq!(result.words[0], 2); assert_eq!(arena.bytes, unchanged); assert_eq!(candidate, candidate_before);
}
#[test]
fn malformed_private_borrow_and_budget_fail_closed_without_state_claim() {
    let mut bytes = [0; 32]; let mut candidate = [0; 2048]; let w = ordered(vec![event(1)])[0];
    for remaining in [0, 424, 425, 426] { let mut steps = StepBudget { remaining, spent: 0 }; let r = observe_fixture_envelope_v1(&mut bytes, &mut candidate, &FixtureDecodedRecordV1 { words: &w }, &mut steps); assert_eq!(r.words[0], 3); assert!(r.words[2..13].iter().all(|n| *n == 0)); }
}
#[test]
fn prepaid_underfunded_guard_retains_first_and_later_prior_state_and_latches_once() {
    for state in [initial_state(), [4, 10, 20, 1, 0, 1, 33, 3, 1, 7, 0, 0]] {
        let mut arena = Arena { bytes: vec![0; ARENA_BYTES] }; arena_state(&mut arena, &state);
        let mut candidate = [0u8; 2048]; for i in 0..12 { put(&mut candidate, PAYLOAD / 8 + i, state[i]); }
        let old = candidate; let mut p = blank_progress(); p.reply_valid = 0;
        let mut main = Budget::new(STEP_LIMIT).unwrap(); main.report(UNDERFUNDED_GUARD).unwrap();
        let mut calls = 0;
        for _ in 0..3 {
            main.replay(COMBINED_RECORD).unwrap(); p.debit += 425;
            if leaf_pending(&p) {
                let mut w = event(2); w[0] = state[0] + 1; let mut steps = StepBudget { remaining: 424, spent: 0 };
                p.reply = observe_fixture_envelope_v1(&mut arena.bytes, &mut candidate, &FixtureDecodedRecordV1 { words: &w }, &mut steps); p.reply_valid = 1; calls += 1;
                assert_eq!((steps.remaining, steps.spent), (424, 0)); assert_eq!(p.reply.words[0..2], [2, 1]); assert_eq!(p.reply.words[13], 0);
                assert!(reply_debit_valid(&p.reply, &steps));
            }
        }
        assert_eq!(calls, 1); assert!(!leaf_pending(&p)); assert_eq!(p.debit, 1856); assert_eq!(candidate, old);
        for i in 0..12 { assert_eq!(word(&arena.bytes, SCALAR.base / 8 + CELLS[i]), state[i]); }
        let mut s = Framing::new(3); s.complete = true;
        let observed = finalize(&p, &s, &Ok(true), &arena); assert_eq!(observed.boundary(), &FixtureEnvelopeBoundaryV1::Refused); assert_eq!(observed.reason(), &FixtureEnvelopeReasonV1::Steps); assert_eq!(observed.observed_records(), state[0]); assert_eq!(observed.envelope_debit(), 1856);
    }
}
#[test]
fn setup_and_finish_reservation_failures_leave_reply_absent_with_exact_paid_debit() {
    for failed_phase in 0..3 {
        let mut arena = Arena { bytes: vec![0; ARENA_BYTES] }; let mut b = Budget::new(STEP_LIMIT).unwrap();
        if failed_phase == 1 { b.report_spent = REPORT_RESERVE - 46; } else if failed_phase == 2 { b.report_spent = REPORT_RESERVE - 47 - 111; } else { b.setup_spent = SETUP_CAP - 80 - 533; }
        let mut x = inputs(&[], false); let mut s = Framing::new(0); let mut p = blank_progress(); p.debit = 0;
        let f = Fixture { cap: 5000, mask: 33, extent: 1000, types: 2, slots: 4, pins: 4, base: 16, capacity: 4096, entry: 512 };
        let err = walk_fixture_envelope_v1(&mut x[0], &mut arena, &mut b, f, 1024, &mut s, &mut p).unwrap_err();
        assert_eq!(err.code, BUDGET); assert_eq!(p.reply_valid, 0); assert_eq!(p.debit, [0, 534, 581][failed_phase]); assert!(p.reply.words.iter().all(|w| *w == 0));
        for cell in CELLS { assert_eq!(word(&arena.bytes, SCALAR.base / 8 + cell), 0); }
    }
}
#[test]
fn read_failure_after_prepaid_record_and_failed_limited_drain_are_distinct() {
    let mut records = Vec::new(); for i in 0..600 { let mut w = event(1); w[3] = i + 1; records.push(w); } records.push(event(13)); let records = ordered(records);
    let mut x = inputs(&records, false); x[0].fail_read_at = 2; let out = invoke(&mut x, STEP_LIMIT).unwrap();
    assert_eq!(out.envelope().envelope_debit(), 581 + 425 * 509); assert_eq!(out.framing().decision, Decision::Invalid); zero_extent(out.envelope()); assert_eq!(out.envelope().reason(), &FixtureEnvelopeReasonV1::FramingInvalid);
    let mut x = inputs(&records, false); x[0].fail_read_at = 2;
    let low = REPORT_RESERVE + IO_RESERVE + ARENA_BYTES as u64 / 8 + 640_000 + 6000;
    let out = invoke(&mut x, low).unwrap(); assert_eq!(out.envelope().envelope_debit(), 581); assert_eq!(out.framing().decision, Decision::Invalid); assert_eq!(out.envelope().boundary(), &FixtureEnvelopeBoundaryV1::Unavailable); zero_extent(out.envelope()); assert_eq!(out.envelope().reason(), &FixtureEnvelopeReasonV1::FramingInvalid);
}
#[test]
fn copied_finite_model_oracle_covers_all_stages_fields_and_u32_boundaries() {
    let raw = include_bytes!("../inputs/oracle-425.bin"); assert_eq!(raw.len() % (44 * 8), 0);
    let mut arena = Arena { bytes: vec![0; ARENA_BYTES] }; let mut candidate = [0; 2048];
    for (index, case) in raw.chunks_exact(44 * 8).enumerate() {
        let mut s = [0; 12]; let mut w = [0; 16]; let mut expected = [0; 16];
        for i in 0..12 { s[i] = word(case, i); } for i in 0..16 { w[i] = word(case, 12 + i); expected[i] = word(case, 28 + i); }
        arena_state(&mut arena, &s); let mut steps = StepBudget { remaining: 425, spent: 0 };
        let actual = observe_fixture_envelope_v1(&mut arena.bytes, &mut candidate, &FixtureDecodedRecordV1 { words: &w }, &mut steps);
        assert_eq!(actual.words, expected, "oracle case {index}");
        if actual.words[0] == 2 { for i in 0..12 { assert_eq!(word(&arena.bytes, SCALAR.base / 8 + CELLS[i]), s[i]); } }
    }
    println!("ENVELOPE_ORACLE_CASES={}", raw.len() / (44 * 8));
}
#[test]
fn output_failure_partial_write_postwrite_error_and_alias_return_outer_error() {
    for mode in 0..4 { let mut x = inputs(&miss(), false);
        match mode { 0 => x[3].fail_write = true, 1 => x[3].quantum = 1, 2 => x[3].drift_at = 3, 3 => x[3].identity = 101, _ => unreachable!() }
        let error = invoke(&mut x, STEP_LIMIT).unwrap_err(); assert!(matches!(error.code, IO_ERROR | IO_EXHAUSTED | DRIFT | BINDING)); assert_eq!(x[3].bytes.len(), [0, 32, REPORT_BYTES, 0][mode]);
    }
}
#[test]
fn public_safe_file_entry_keeps_files_owned_and_reports_no_semantic_values() {
    let scratch = std::path::PathBuf::from(std::env::var_os("MIXER_ENVELOPE_SCRATCH").unwrap());
    let bytes = inputs(&hit(), false); let mut files = Vec::new();
    for (name, b) in ["envelope-stream", "envelope-profile", "envelope-context", "envelope-report"].into_iter().zip(bytes) { let mut f = std::fs::OpenOptions::new().read(true).write(true).create_new(true).open(scratch.join(name)).unwrap(); f.write_all(&b.bytes).unwrap(); f.rewind().unwrap(); files.push(f); }
    let mut output = files.pop().unwrap(); let mut context = files.pop().unwrap(); let mut profile = files.pop().unwrap(); let mut stream = files.pop().unwrap();
    let outcome = analyze_fixture_envelope_v1(&mut stream, &mut profile, &mut context, &mut output).unwrap(); assert_eq!(outcome.envelope().boundary(), &FixtureEnvelopeBoundaryV1::ClosedEnvelopeObserved); assert_eq!(output.metadata().unwrap().len(), REPORT_BYTES as u64); stream.rewind().unwrap(); profile.rewind().unwrap(); context.rewind().unwrap();
}

#[path = "selected_tests.rs"]
mod selected_contract;

#[path = "../focused_controls.rs"]
mod absence_controls;
