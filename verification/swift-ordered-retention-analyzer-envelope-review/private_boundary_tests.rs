//! Independent actual-Rust controls appended only to an owned frozen copy.
use super::*;

fn put(bytes: &mut [u8], word: usize, value: u64) {
    bytes[word * 8..word * 8 + 8].copy_from_slice(&value.to_le_bytes());
}
fn raw_word(bytes: &[u8], word: usize) -> u64 {
    u64::from_le_bytes(bytes[word * 8..word * 8 + 8].try_into().unwrap())
}
fn state() -> [u64; 12] { [0, 0, 0, 0, 0, 1, 33, 0, 0, 0, 0, 0] }
fn arena() -> Arena {
    let mut result = Arena { bytes: vec![0; ARENA_BYTES] };
    for (index, value) in state().iter().enumerate() { put(&mut result.bytes, SCALAR.base / 8 + CELLS[index], *value); }
    result
}
fn progress(status: u64, reason: u64) -> FixtureEnvelopeProgressV1 {
    let mut result = FixtureEnvelopeProgressV1 { reply_valid: 1, debit: 1054, reply: reply(status, reason, &state(), 128) };
    result.reply.words[2] = 4;
    result.reply.words[3] = 1;
    result.reply.words[6] = 1;
    result.reply.words[7] = 1;
    result.reply.words[8] = 17;
    result.reply.words[11] = 122;
    result.reply.words[12] = 250;
    result
}
fn frame(limited: bool, cap: bool) -> Framing {
    let mut result = Framing::new(5);
    result.complete = !limited; result.limited = limited; result.flags = u64::from(cap);
    result
}
fn zero(value: &FixtureEnvelopeObservationV1) {
    assert_eq!([value.observed_records(), value.state(), value.phase(), value.mask(), value.last_operation(),
        value.active_operation(), value.requested_function(), value.pin_failure(), value.terminal_failure(),
        value.last_work(), value.last_instructions()], [0; 11]);
    assert!(!value.stored_prefix_validated()); assert!(!value.full_replay_accepted()); assert!(!value.semantic_metrics_valid());
}

#[test]
fn review_absent_backing_never_becomes_observed() {
    let a = arena();
    for limited in [false, true] { for cap in [false, true] {
        let mut p = progress(1, 0); p.reply_valid = 0; p.debit = 542;
        p.reply.words[3] = 999; // Inaccessible stale backing must not be projected.
        let result = finalize(&p, &frame(limited, cap), &Ok(!limited), &a);
        assert_eq!(result.boundary(), &FixtureEnvelopeBoundaryV1::Unavailable);
        assert_eq!(result.reason(), &FixtureEnvelopeReasonV1::EnvelopeUnavailable);
        assert_eq!(result.envelope_debit(), 542); zero(&result);
    }}
}

#[test]
fn review_late_error_precedence_preserves_debit_and_clears_all_extent() {
    let a = arena();
    for (status, reason) in [(1, 0), (2, 12), (3, 15)] {
        let p = progress(status, reason);
        for limited in [false, true] { for cap in [false, true] { for code in [BINDING, BUDGET, SCHEMA, IO_ERROR, DRIFT] {
            let result = finalize(&p, &frame(limited, cap), &Err(error(code, FOOTER_STAGE, 1024, 5)), &a);
            assert_eq!(result.boundary(), &FixtureEnvelopeBoundaryV1::Unavailable);
            assert_eq!(result.reason(), if code == BINDING { &FixtureEnvelopeReasonV1::FramingUnavailable }
                else if code == BUDGET { &FixtureEnvelopeReasonV1::FramingLimited } else { &FixtureEnvelopeReasonV1::FramingInvalid });
            assert_eq!(result.envelope_debit(), 1054); zero(&result);
        }}}
    }
}

#[test]
fn review_actual_partial_complete_and_cap_result_table() {
    let a = arena();
    for (status, reason) in [(1, 0), (2, 12), (3, 15)] { for cap in [false, true] {
        let p = progress(status, reason);
        let partial = finalize(&p, &frame(true, cap), &Ok(false), &a);
        assert_eq!(partial.boundary(), &FixtureEnvelopeBoundaryV1::AnalysisLimited);
        assert_eq!(partial.reason(), match status { 1 => &FixtureEnvelopeReasonV1::FramingLimited,
            2 => &FixtureEnvelopeReasonV1::Stage, _ => &FixtureEnvelopeReasonV1::InternalPoisoned });
        if status == 3 { zero(&partial); } else { assert_eq!(partial.observed_records(), 4); assert_eq!(partial.state(), 1); }
        let complete = finalize(&p, &frame(false, cap), &Ok(true), &a);
        assert_eq!(complete.boundary(), match status { 3 => &FixtureEnvelopeBoundaryV1::InternalPoisoned,
            2 => &FixtureEnvelopeBoundaryV1::Refused, _ => if cap { &FixtureEnvelopeBoundaryV1::CapCutUnknownTail } else { &FixtureEnvelopeBoundaryV1::Refused } });
        if status == 3 { zero(&complete); } else { assert_eq!(complete.observed_records(), 4); }
    }}
    let mut closed = progress(1, 0); closed.reply.words[3] = 0; closed.reply.words[4] = 5; closed.reply.words[5] = 33;
    let result = finalize(&closed, &frame(false, false), &Ok(true), &a);
    assert_eq!(result.boundary(), &FixtureEnvelopeBoundaryV1::ClosedEnvelopeObserved);
}

#[test]
fn review_inconsistent_private_values_and_flags_fail_closed() {
    let a = arena();
    for (index, value) in [(0, 0), (0, 4), (1, 99), (1, 2), (3, 11), (4, 6), (5, 64), (9, 2), (10, 2)] {
        let mut p = progress(1, 0); p.reply.words[index] = value;
        for limited in [false, true] { for cap in [false, true] {
            let result = finalize(&p, &frame(limited, cap), &Ok(!limited), &a);
            assert_eq!(result.boundary(), &FixtureEnvelopeBoundaryV1::Unavailable);
            assert_eq!(result.reason(), &FixtureEnvelopeReasonV1::UnavailableState); zero(&result);
        }}
    }
    for flags in [2, 99] {
        let mut f = frame(false, false); f.flags = flags;
        let result = finalize(&progress(1, 0), &f, &Ok(true), &a);
        assert_eq!(result.reason(), &FixtureEnvelopeReasonV1::UnavailableState); zero(&result);
    }
    for (complete, limited, returned) in [(false, false, true), (true, true, true), (true, false, false), (false, true, true)] {
        let mut f = frame(false, false); f.complete = complete; f.limited = limited;
        let result = finalize(&progress(1, 0), &f, &Ok(returned), &a);
        assert_eq!(result.reason(), &FixtureEnvelopeReasonV1::UnavailableState); zero(&result);
    }
}

#[test]
fn review_poison_marker_prevents_any_later_leaf_call() {
    let a = arena();
    for status in [1, 3] {
        let mut p = progress(status, 15); p.reply.words[3] = 999;
        let result = finalize(&p, &frame(false, true), &Ok(true), &a);
        assert_eq!(result.reason(), &FixtureEnvelopeReasonV1::InternalPoisoned); zero(&result);
        assert!(!leaf_pending(&p), "same retained poison recognized by finish must not resume a leaf call; status={status}");
    }
}

fn acquire() -> [u64; 16] { [1, 1, 0, 1, 101, 211, 17, ABSENT, ABSENT, ABSENT, ABSENT, ABSENT, 0, 0, 0, 0] }

#[test]
fn review_underfunded_first_and_later_guard_is_atomic_steps_refusal() {
    for advanced in [false, true] { for remaining in [0, 1, 127] {
        let mut a = arena(); let mut candidate = [0u8; 2048];
        if advanced {
            let mut budget = StepBudget { remaining: 128, spent: 0 };
            let first = observe_fixture_envelope_v1(&mut a.bytes, &mut candidate, &FixtureDecodedRecordV1 { words: &acquire() }, &mut budget);
            assert_eq!(first.words[0], 1);
        }
        let before = a.bytes.clone(); let candidate_before = candidate;
        let mut budget = StepBudget { remaining, spent: 0 };
        let refused = observe_fixture_envelope_v1(&mut a.bytes, &mut candidate, &FixtureDecodedRecordV1 { words: &acquire() }, &mut budget);
        assert_eq!(&refused.words[..2], &[2, 1]); assert_eq!(refused.words[13], 0);
        assert_eq!((budget.remaining, budget.spent), (remaining, 0));
        assert_eq!(a.bytes, before); assert_eq!(candidate, candidate_before);
        assert_eq!(refused.words[2], u64::from(advanced));
        let p = FixtureEnvelopeProgressV1 { reply_valid: 1, debit: 670, reply: refused };
        assert!(!leaf_pending(&p)); assert!(reply_debit_valid(&p.reply, &budget));
        let result = finalize(&p, &frame(false, true), &Ok(true), &a);
        assert_eq!(result.boundary(), &FixtureEnvelopeBoundaryV1::Refused);
        assert_eq!(result.reason(), &FixtureEnvelopeReasonV1::Steps); assert_eq!(result.envelope_debit(), 670);
    }}
}

#[test]
fn review_last_checked_cell_refusal_precedes_every_candidate_or_arena_write() {
    let mut a = arena(); let before = a.bytes.clone(); let mut candidate = [0u8; 2048]; let candidate_before = candidate;
    let truncated = SCALAR.base + 8 * 161 + 7;
    let mut budget = StepBudget { remaining: 128, spent: 0 };
    let result = observe_fixture_envelope_v1(&mut a.bytes[..truncated], &mut candidate, &FixtureDecodedRecordV1 { words: &acquire() }, &mut budget);
    assert_eq!(&result.words[..2], &[3, 15]); assert_eq!(result.words[13], 128);
    assert_eq!(a.bytes, before); assert_eq!(candidate, candidate_before);
}

struct Source { bytes: Vec<u8>, position: usize, identity: u64, stamps: usize, drift: bool, eof_error: bool, fail_read: usize, reads: usize }
impl Source {
    fn new(bytes: Vec<u8>, identity: u64) -> Self { Self { bytes, position: 0, identity, stamps: 0, drift: false, eof_error: false, fail_read: usize::MAX, reads: 0 } }
}
impl Read for Source {
    fn read(&mut self, output: &mut [u8]) -> io::Result<usize> {
        self.reads += 1;
        if self.reads == self.fail_read || (self.position == self.bytes.len() && self.eof_error) { return Err(io::ErrorKind::Other.into()); }
        let count = output.len().min(self.bytes.len() - self.position);
        output[..count].copy_from_slice(&self.bytes[self.position..self.position + count]); self.position += count; Ok(count)
    }
}
impl InputFile for Source {
    fn stamp(&mut self) -> io::Result<Stamp> {
        self.stamps += 1;
        Ok(Stamp { fields: [31, self.identity + u64::from(self.drift && self.stamps >= 3), 0o100600, self.bytes.len() as u64, 0, 0, 0, 0], regular: 1 })
    }
    fn position(&mut self) -> io::Result<u64> { Ok(self.position as u64) }
}
struct Sink { bytes: Vec<u8>, stamps: usize, fail_write: bool, drift: bool }
impl Sink { fn new() -> Self { Self { bytes: Vec::new(), stamps: 0, fail_write: false, drift: false } } }
impl Write for Sink {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        if self.fail_write { return Err(io::ErrorKind::BrokenPipe.into()); }
        self.bytes.extend_from_slice(bytes); Ok(bytes.len())
    }
    fn flush(&mut self) -> io::Result<()> { Ok(()) }
}
impl OutputFile for Sink {
    fn stamp(&mut self) -> io::Result<Stamp> { self.stamps += 1; Ok(Stamp { fields: [31, 94 + u64::from(self.drift && self.stamps >= 3), 0o100600, self.bytes.len() as u64, 0, 0, 0, 0], regular: 1 }) }
    fn position(&mut self) -> io::Result<u64> { Ok(self.bytes.len() as u64) }
}
fn files() -> (Source, Source, Source, Sink) {
    let base = std::path::PathBuf::from(std::env::var_os("MIXER_ENVELOPE_REVIEW_VECTORS").unwrap());
    (Source::new(std::fs::read(base.join("closed-hit.stream.bin")).unwrap(), 91),
     Source::new(std::fs::read(base.join("profile.bin")).unwrap(), 92),
     Source::new(std::fs::read(base.join("closed-hit.context.bin")).unwrap(), 93), Sink::new())
}
fn invoke(x: &mut (Source, Source, Source, Sink), limit: u64) -> Result<FixtureEnvelopeOutcomeV1, AnalyzerError> {
    analyze_fixture_envelope_core(&mut x.0, &mut x.1, &mut x.2, &mut x.3, limit)
}

#[test]
fn review_new_core_late_eof_metadata_and_output_errors_suppress_success() {
    for variant in 0..4 {
        let mut x = files();
        match variant { 0 => x.0.eof_error = true, 1 => x.0.drift = true, 2 => x.1.drift = true, _ => x.2.drift = true }
        let result = invoke(&mut x, STEP_LIMIT).unwrap();
        assert_eq!(result.framing().decision, Decision::Invalid);
        assert_eq!(result.envelope().reason(), &FixtureEnvelopeReasonV1::FramingInvalid);
        assert_eq!(result.envelope().envelope_debit(), 1182); zero(result.envelope());
    }
    for late in [false, true] {
        let mut x = files(); x.3.fail_write = !late; x.3.drift = late;
        let result = invoke(&mut x, STEP_LIMIT);
        match result { Err(error) => assert_eq!(error.code, if late { DRIFT } else { IO_ERROR }), Ok(_) => panic!("failed output returned an aggregate") }
        assert_eq!(x.3.bytes.len(), if late { 49152 } else { 0 });
    }
}

fn complete_limit() -> u64 {
    let mut low = REPORT_RESERVE + IO_RESERVE + ARENA_BYTES as u64 / 8 + 640000;
    let mut high = low + 65536 + 8192;
    while low < high {
        let mid = low + (high - low) / 2; let mut x = files();
        let complete = invoke(&mut x, mid).is_ok_and(|value| value.framing().fixture_framing_observed());
        if complete { high = mid; } else { low = mid + 1; }
    }
    low
}

#[test]
fn review_actual_preflight_edges_and_zero_call_absence() {
    let limit = complete_limit();
    let mut x = files(); let whole = invoke(&mut x, limit).unwrap();
    assert!(whole.framing().fixture_framing_observed()); assert_eq!(whole.envelope().observed_records(), 5);
    let mut x = files(); let prior = invoke(&mut x, limit - 1).unwrap();
    assert_eq!(prior.framing().decision, Decision::AnalysisLimited);
    assert_eq!(prior.envelope().boundary(), &FixtureEnvelopeBoundaryV1::AnalysisLimited);
    assert_eq!(prior.envelope().observed_records(), 4); assert_eq!(prior.envelope().envelope_debit(), 1054);
    let mut x = files(); let absent = invoke(&mut x, limit - COMBINED_RECORD * 5).unwrap();
    assert_eq!(absent.framing().decision, Decision::AnalysisLimited);
    assert_eq!(absent.envelope().reason(), &FixtureEnvelopeReasonV1::EnvelopeUnavailable);
    assert_eq!(absent.envelope().envelope_debit(), 542); zero(absent.envelope());
    println!("REVIEW_COMPLETE_LIMIT={limit} PRIOR=4 ZERO_DEBIT=542");
}

#[test]
fn review_failed_limited_drain_is_unavailable_and_retains_actual_error() {
    let limit = complete_limit(); let mut x = files();
    let header = x.0.bytes[..512].to_vec(); let mut footer = x.0.bytes[x.0.bytes.len() - 512..].to_vec();
    let mut bytes = header;
    for index in 0..600u64 { let mut record = acquire(); record[0] = index + 1; record[3] = index + 1; record[4] = 101 + index * 7; record[5] = 211 + index * 13; for value in record { bytes.extend_from_slice(&value.to_le_bytes()); } }
    let mut phase = [601, 13, 5, 0, 4301, 8011, ABSENT, ABSENT, ABSENT, ABSENT, ABSENT, ABSENT, 0, 5, 0, 0];
    // Keep exact monotonic final coordinates in the footer.
    phase[4] = 101 + 600 * 7; phase[5] = 211 + 600 * 13;
    for value in phase { bytes.extend_from_slice(&value.to_le_bytes()); }
    for (word, value) in [(2, 601), (3, 601), (4, 0), (5, 601), (6, phase[4]), (7, phase[5]), (8, 600), (10, phase[4]), (11, phase[5])] { put(&mut footer, word, value); }
    bytes.extend_from_slice(&footer); x.0.bytes = bytes; x.0.fail_read = 2;
    let result = invoke(&mut x, limit - COMBINED_RECORD * 5).unwrap();
    assert_eq!(result.framing().decision, Decision::Invalid);
    assert_eq!(result.framing().observation.code, IO_ERROR);
    assert_eq!(result.envelope().boundary(), &FixtureEnvelopeBoundaryV1::Unavailable);
    assert_eq!(result.envelope().reason(), &FixtureEnvelopeReasonV1::FramingInvalid);
    assert_eq!(result.envelope().envelope_debit(), 542); zero(result.envelope());
    assert_eq!(x.0.reads, 2);
    assert_eq!(raw_word(&x.3.bytes, 15), 0);
}
