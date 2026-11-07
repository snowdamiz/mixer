use super::*;
use std::mem::size_of;

fn put(bytes: &mut [u8], at: usize, value: u64) {
    bytes[at..at + 8].copy_from_slice(&value.to_le_bytes());
}
fn state(bytes: &mut [u8], values: &[u64; 12]) {
    for (i, cell) in CELLS.iter().enumerate() { put(bytes, SCALAR.base + 8 * cell, values[i]); }
}
fn initial_state() -> [u64; 12] { [0, 0, 0, 0, 0, 1, 33, 0, 0, 0, 0, 0] }
fn progress() -> FixtureEnvelopeProgressV1 {
    FixtureEnvelopeProgressV1 { reply_valid: 0, debit: 0, reply: FixtureEnvelopeReplyV1 { words: [0; 16] } }
}
fn fixture() -> Fixture {
    Fixture { cap: 1000, mask: 33, extent: 1000, types: 2, slots: 4, pins: 4, base: 16, capacity: 4096, entry: 128 }
}
fn acquire(seq: u64) -> [u64; 16] {
    [seq, 1, 0, seq, seq, seq, 3, ABSENT, ABSENT, ABSENT, ABSENT, ABSENT, 0, 0, 0, 0]
}
fn phase() -> [u64; 16] {
    [1, 13, 5, 0, 1, 1, ABSENT, ABSENT, ABSENT, ABSENT, ABSENT, ABSENT, 0, 5, 0, 0]
}
fn encode(words: &[u64], out: &mut Vec<u8>) {
    for word in words { out.extend_from_slice(&word.to_le_bytes()); }
}
fn stream(records: &[[u64; 16]]) -> Vec<u8> {
    let f = fixture();
    let mut h = [0u64; 64];
    h[..10].copy_from_slice(&[HEADER_MAGIC, 1, 512, 128, 512, f.cap, 80_000, 64, 512, f.mask]);
    let mut out = Vec::new();
    encode(&h, &mut out);
    for words in records { encode(words, &mut out); }
    let mut footer = [0u64; 64];
    let last = records.last().copied().unwrap_or([0; 16]);
    footer[..16].copy_from_slice(&[FOOTER_MAGIC, 1, records.len() as u64, records.len() as u64, 0, records.len() as u64, last[4], last[5], 0, 0, last[4], last[5], 0, 0, ABSENT, 33]);
    footer[33] = 5; footer[34] = 1; footer[35] = f.cap;
    encode(&footer, &mut out);
    out
}
struct Input { bytes: Vec<u8>, cursor: usize, fail_after: Option<usize> }
impl Read for Input {
    fn read(&mut self, out: &mut [u8]) -> io::Result<usize> {
        if self.fail_after.is_some_and(|at| self.cursor >= at) { return Err(io::ErrorKind::PermissionDenied.into()); }
        let n = out.len().min(self.bytes.len() - self.cursor);
        out[..n].copy_from_slice(&self.bytes[self.cursor..self.cursor + n]);
        self.cursor += n;
        Ok(n)
    }
}
impl InputFile for Input {
    fn stamp(&mut self) -> io::Result<Stamp> { Ok(Stamp { fields: [1, 1, 0o100600, self.bytes.len() as u64, 0, 0, 0, 0], regular: 1 }) }
    fn position(&mut self) -> io::Result<u64> { Ok(self.cursor as u64) }
}
fn input(bytes: Vec<u8>) -> Input { Input { bytes, cursor: 0, fail_after: None } }
fn assert_selected_unchanged(before: &[u8], after: &[u8]) {
    for cell in CELLS { let at = SCALAR.base + 8 * cell; assert_eq!(&before[at..at + 8], &after[at..at + 8]); }
}

fn layouts() {
    let actual = [size_of::<Candidate2048>(), size_of::<StepBudget>(), size_of::<CheckedPair>(), size_of::<FixtureEnvelopeReplyV1>(), size_of::<FixtureEnvelopeProgressV1>(), size_of::<FixtureEnvelopeObservationV1>(), size_of::<FixtureEnvelopeOutcomeV1>(), size_of::<Result<FixtureEnvelopeOutcomeV1, AnalyzerError>>(), size_of::<FixtureDecodedRecordV1<'_>>(), size_of::<Option<&[u8]>>(), size_of::<Option<&mut [u8]>>(), size_of::<Option<&[u8; 8]>>(), size_of::<Option<u64>>(), size_of::<std::ops::Range<usize>>(), size_of::<std::ops::RangeInclusive<u64>>(), size_of::<std::ops::RangeFrom<usize>>(), size_of::<Budget>(), size_of::<Framing>(), size_of::<Reader>(), size_of::<ReplayOutcome>(), size_of::<AnalyzerError>(), size_of::<Stamp>(), size_of::<std::fs::Metadata>(), size_of::<io::Result<std::fs::Metadata>>(), size_of::<Result<bool, AnalyzerError>>(), size_of::<Result<(), AnalyzerError>>()];
    assert_eq!(actual, [2048, 16, 16, 128, 144, 128, 232, 232, 8, 16, 16, 8, 16, 16, 24, 8, 56, 80, 48, 104, 32, 72, 144, 152, 40, 40]);
    println!("LAYOUT_VALUES={actual:?}");
}
fn checked_word_edges() {
    let bytes: Vec<u8> = (1..=15).collect();
    for at in [0usize, 7] {
        let r = word_at(&bytes, at);
        assert_eq!(r.status, 1);
        assert_eq!(r.value, u64::from_le_bytes(bytes[at..at + 8].try_into().unwrap()));
    }
    for at in [8, 15, 16, usize::MAX] {
        let r = word_at(&bytes, at); assert_eq!((r.status, r.value), (0, 0));
    }
    println!("CHECKED_WORD_EDGES=6");
}
fn retained_candidate_canaries() {
    let mut arena = vec![0xa5; ARENA_BYTES];
    state(&mut arena, &initial_state());
    let mut candidate = [0u8; 2048];
    let owner = candidate.as_ptr();
    let mut records = [acquire(1), [2, 2, 0, 1, 2, 2, 3, 1, 1, 0, 0, ABSENT, 0, 1, 0, 0], [3, 11, 0, 1, 3, 3, 3, 1, 1, 0, 0, 0, 1, 0, 1, 1], [4, 12, 0, 0, 4, 4, 4, 1, ABSENT, 0, 0, 0, 1, 1, 0, 0], phase()];
    records[4][0] = 5; records[4][4] = 5; records[4][5] = 5;
    for words in records {
        let before = arena.clone();
        let mut steps = StepBudget { remaining: 128, spent: 0 };
        let r = observe_fixture_envelope_v1(&mut arena, &mut candidate, &FixtureDecodedRecordV1 { words: &words }, &mut steps);
        assert_eq!(r.words[0], 1); assert_eq!(r.words[2], words[0]);
        assert_eq!((steps.remaining, steps.spent), (0, 128));
        assert_eq!(candidate.as_ptr(), owner);
        assert!(candidate[..888].iter().all(|b| *b == 0)); assert!(candidate[984..].iter().all(|b| *b == 0));
        let mut cursor = 0;
        for cell in CELLS { let at = SCALAR.base + 8 * cell; assert_eq!(&arena[cursor..at], &before[cursor..at]); cursor = at + 8; }
        assert_eq!(&arena[cursor..], &before[cursor..]);
    }
    let old_arena = arena.clone(); let old_candidate = candidate;
    let mut words = acquire(6); words[4] = 6; words[5] = 6;
    let mut steps = StepBudget { remaining: 128, spent: 0 };
    let r = observe_fixture_envelope_v1(&mut arena, &mut candidate, &FixtureDecodedRecordV1 { words: &words }, &mut steps);
    assert_eq!((r.words[0], r.words[1], r.words[13]), (2, 4, 128));
    assert_eq!(arena, old_arena); assert_eq!(candidate, old_candidate); assert_eq!(candidate.as_ptr(), owner);
    println!("CANARY_CALLS=6 OWNER_STABLE=1 SELECTED_CELLS=12 PAYLOAD_BYTES=96");
}
fn underfunded_guard() {
    let states = [initial_state(), [4, 10, 20, 1, 0, 1, 33, 3, 1, 7, 0, 0]];
    let mut cases = 0;
    for prior in states { for remaining in [0, 1, 127] {
        let mut arena = vec![0x3c; ARENA_BYTES]; state(&mut arena, &prior);
        let mut candidate = [0x5a; 2048]; let before = arena.clone(); let old = candidate;
        let malformed = [0u64; 16]; let mut steps = StepBudget { remaining, spent: 0 };
        let r = observe_fixture_envelope_v1(&mut arena, &mut candidate, &FixtureDecodedRecordV1 { words: &malformed }, &mut steps);
        assert_eq!((r.words[0], r.words[1], r.words[13]), (2, 1, 0));
        assert_eq!(r.words[2], prior[0]); assert_eq!(r.words[3], prior[7]);
        assert_eq!((steps.remaining, steps.spent), (remaining, 0));
        assert_eq!(arena, before); assert_eq!(candidate, old); assert!(reply_debit_valid(&r, &steps));
        let mut p = progress(); p.reply = r; p.reply_valid = 1; assert!(!leaf_pending(&p));
        cases += 1;
    }}
    for remaining in [128, 129] {
        let mut arena = vec![0; ARENA_BYTES]; state(&mut arena, &initial_state()); let mut candidate = [0; 2048];
        let mut steps = StepBudget { remaining, spent: 0 }; let words = acquire(1);
        let r = observe_fixture_envelope_v1(&mut arena, &mut candidate, &FixtureDecodedRecordV1 { words: &words }, &mut steps);
        assert_eq!((r.words[0], r.words[13]), (1, 128)); assert_eq!((steps.remaining, steps.spent), (remaining - 128, 128));
    }
    let mut short = [0u8; 32]; let mut candidate = [0x5a; 2048]; let old = candidate;
    let mut steps = StepBudget { remaining: 0, spent: 0 }; let words = acquire(1);
    let r = observe_fixture_envelope_v1(&mut short, &mut candidate, &FixtureDecodedRecordV1 { words: &words }, &mut steps);
    assert_eq!((r.words[0], r.words[1], r.words[13]), (3, 15, 0)); assert_eq!(candidate, old);
    println!("UNDERFUNDED_UNCHANGED_CASES={cases} FUNDED_EDGES=2 SHORT_ARENA_POISON=1");
}
fn reservation_ordering() {
    for failure in 0..3 {
        let mut arena = Arena { bytes: vec![0; ARENA_BYTES] }; let before = arena.bytes.clone();
        let mut b = Budget::new(STEP_LIMIT).unwrap();
        match failure {
            0 => b.setup_spent = SETUP_CAP - 80 - 533,
            1 => b.report_spent = REPORT_RESERVE - 7,
            2 => b.report_spent = REPORT_RESERVE - 8 - 35,
            _ => unreachable!(),
        }
        let mut src = input(stream(&[])); let mut s = Framing::new(0); let mut p = progress();
        let r = walk_fixture_envelope_v1(&mut src, &mut arena, &mut b, fixture(), 1024, &mut s, &mut p).unwrap_err();
        assert_eq!(r.code, BUDGET); assert_eq!(p.reply_valid, 0); assert_eq!(p.debit, [0, 534, 542][failure]);
        assert!(p.reply.words.iter().all(|w| *w == 0)); assert_selected_unchanged(&before, &arena.bytes);
    }
    println!("RESERVATION_FAILURES_BEFORE_CELL_MUTATION=3 DEBITS=0,534,542");
}
fn preflight_and_atomic_charge() {
    for edge in [8191u64, 8192] {
        let mut arena = Arena { bytes: vec![0; ARENA_BYTES] }; let mut b = Budget::new(STEP_LIMIT).unwrap();
        b.replay_left = 80 + 534 + edge;
        let bytes = stream(&[phase()]); let length = bytes.len() as u64; let mut src = input(bytes);
        let mut s = Framing::new(1); let mut p = progress();
        walk_fixture_envelope_v1(&mut src, &mut arena, &mut b, fixture(), length, &mut s, &mut p).unwrap();
        let n = u64::from(edge == 8192);
        assert_eq!(p.debit, 542 + 128 * n); assert_eq!(p.reply_valid, n); assert_eq!(s.framed, n);
        assert_eq!(s.limited, n == 0); assert_eq!(s.complete, n == 1);
    }
    for available in [COMBINED_RECORD - 1, COMBINED_RECORD, COMBINED_RECORD + 1] {
        let mut b = Budget::new(STEP_LIMIT).unwrap(); b.replay_left = available;
        let r = b.replay(COMBINED_RECORD);
        if available < COMBINED_RECORD { assert!(r.is_err()); assert_eq!((b.replay_left, b.replay_spent), (available, 0)); }
        else { assert!(r.is_ok()); assert_eq!((b.replay_left, b.replay_spent), (available - COMBINED_RECORD, COMBINED_RECORD)); }
    }
    println!("MANDATORY_PREFLIGHT_EDGES=8191,8192 ATOMIC_COMBINED_CHARGE_EDGES=191,192,193");
}
fn paid_decode_failure_and_latched_skips() {
    let records: Vec<[u64; 16]> = (1..=512).map(acquire).collect();
    let bytes = stream(&records); let length = bytes.len() as u64;
    let mut src = input(bytes); src.fail_after = Some(65536);
    let mut arena = Arena { bytes: vec![0; ARENA_BYTES] }; let mut b = Budget::new(STEP_LIMIT).unwrap();
    let mut s = Framing::new(records.len() as u64); let mut p = progress();
    let r = walk_fixture_envelope_v1(&mut src, &mut arena, &mut b, fixture(), length, &mut s, &mut p).unwrap_err();
    assert_eq!(r.code, IO_ERROR); assert_eq!(p.debit, 542 + 128 * 509);
    assert_eq!(s.framed, 508); assert_eq!((p.reply.words[0], p.reply.words[1], p.reply.words[2]), (2, 10, 1));
    assert!(!leaf_pending(&p));
    let projected = finalize(&p, &s, &Err(r), &arena);
    assert_eq!(projected.envelope_debit(), 65694); assert_eq!(projected.observed_records(), 0);
    println!("PAID_RECORDS=509 FRAMED_RECORDS=508 LEAF_LATCH_AT=2 PUBLIC_DEBIT=65694");
}
pub(crate) fn run() {
    layouts(); checked_word_edges(); retained_candidate_canaries(); underfunded_guard();
    reservation_ordering(); preflight_and_atomic_charge(); paid_decode_failure_and_latched_skips();
    println!("ACCOUNTING_PROBES_PASSED=7 PRODUCT_ACCEPTANCE=0");
}
