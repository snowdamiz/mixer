//! Separate safe-File fixture envelope. No replay, binding or release authority.
use super::*;

const SETUP_ENVELOPE: u64 = 534;
const FINISH_ENVELOPE: u64 = 47;
const RECORD_ENVELOPE: u64 = 425;
const SETUP_WRAPPER: u64 = 42;
const FINAL_WRAPPER: u64 = 42;
const UNDERFUNDED_GUARD: u64 = 112;
// Selected operation-ledger partition W01..W09; outer F42 includes early-error13.
const WRAPPER_GROUPS: [u64; 9] = [1, 3, 1, 2, 3, 2, 1, 5, 6];
const WRAPPER_STEPS: u64 = WRAPPER_GROUPS[0] + WRAPPER_GROUPS[1] + WRAPPER_GROUPS[2] + WRAPPER_GROUPS[3]
    + WRAPPER_GROUPS[4] + WRAPPER_GROUPS[5] + WRAPPER_GROUPS[6] + WRAPPER_GROUPS[7]
    + WRAPPER_GROUPS[8];
const COMBINED_RECORD: u64 = RECORD_STEPS + RECORD_ENVELOPE + WRAPPER_STEPS;
const CELLS: [usize; 12] = [7, 9, 10, 11, 12, 13, 14, 64, 65, 66, 160, 161];
const PAYLOAD: usize = 888;
type Candidate2048 = [u8; 2048];
const _: () = assert!(COMBINED_RECORD <= RECORD_PREFLIGHT && SCALAR.base + 161 * 8 + 8 <= ARENA_BYTES && PAYLOAD + 12 * 8 <= 2048);

#[derive(Debug, PartialEq, Eq)]
#[repr(u64)]
pub enum FixtureEnvelopeBoundaryV1 {
    Unavailable = 0, ClosedEnvelopeObserved = 1, CapCutUnknownTail = 2,
    Refused = 3, AnalysisLimited = 4, InternalPoisoned = 5,
}
#[derive(Debug, PartialEq, Eq)]
#[repr(u64)]
pub enum FixtureEnvelopeReasonV1 {
    Observed = 0, Steps = 1, Shape = 2, Coordinate = 3, TerminalPhase = 4,
    Phase = 5, ReleaseOpen = 6, TerminalFailure = 7, PinFailure = 8,
    ForbiddenResume = 9, Acquire = 10, Identity = 11, Stage = 12,
    PublicationForm = 13, CheckedAccess = 14, InternalPoisoned = 15,
    FramingUnavailable = 16, FramingInvalid = 17, FramingLimited = 18,
    EnvelopeUnavailable = 19, UnavailableState = 20, IncompleteBoundary = 21,
}
#[derive(Debug)]
#[repr(C)]
pub struct FixtureEnvelopeObservationV1 {
    boundary: FixtureEnvelopeBoundaryV1, reason: FixtureEnvelopeReasonV1,
    observed_records: u64, state: u64, phase: u64, mask: u64,
    last_operation: u64, active_operation: u64, requested_function: u64,
    pin_failure: u64, terminal_failure: u64,
    last_work: u64, last_instructions: u64, envelope_debit: u64,
    full_replay_accepted: u64, stored_prefix_validated: u64,
}
impl FixtureEnvelopeObservationV1 {
    pub fn boundary(&self) -> &FixtureEnvelopeBoundaryV1 { &self.boundary }
    pub fn reason(&self) -> &FixtureEnvelopeReasonV1 { &self.reason }
    pub fn observed_records(&self) -> u64 { self.observed_records }
    pub fn state(&self) -> u64 { self.state }
    pub fn phase(&self) -> u64 { self.phase }
    pub fn mask(&self) -> u64 { self.mask }
    pub fn last_operation(&self) -> u64 { self.last_operation }
    pub fn active_operation(&self) -> u64 { self.active_operation }
    pub fn requested_function(&self) -> u64 { self.requested_function }
    pub fn pin_failure(&self) -> u64 { self.pin_failure }
    pub fn terminal_failure(&self) -> u64 { self.terminal_failure }
    pub fn last_work(&self) -> u64 { self.last_work }
    pub fn last_instructions(&self) -> u64 { self.last_instructions }
    /// Cumulative prepaid envelope credits; never a leaf execution count.
    pub fn envelope_debit(&self) -> u64 { self.envelope_debit }
    pub const fn stored_prefix_validated(&self) -> bool { false }
    pub const fn full_replay_accepted(&self) -> bool { false }
    pub const fn semantic_metrics_valid(&self) -> bool { false }
}
#[derive(Debug)]
#[repr(C)]
pub struct FixtureEnvelopeOutcomeV1 {
    framing: ReplayOutcome, envelope: FixtureEnvelopeObservationV1,
}
impl FixtureEnvelopeOutcomeV1 {
    pub fn framing(&self) -> &ReplayOutcome { &self.framing }
    pub fn envelope(&self) -> &FixtureEnvelopeObservationV1 { &self.envelope }
    pub const fn stored_prefix_validated(&self) -> bool { false }
    pub const fn full_replay_accepted(&self) -> bool { false }
}

#[repr(C)]
struct StepBudget { remaining: u64, spent: u64 }
#[repr(C)]
struct CheckedPair { status: u64, value: u64 }
#[repr(C)]
struct FixtureEnvelopeReplyV1 { words: [u64; 16] }
#[repr(C)]
struct FixtureEnvelopeProgressV1 {
    reply_valid: u64, debit: u64, reply: FixtureEnvelopeReplyV1,
}
// Only the framing walk constructs a production record, after its own checks.
struct FixtureDecodedRecordV1<'a> { words: &'a [u64; 16] }

fn word_at(bytes: &[u8], offset: usize) -> CheckedPair {
    let Some(tail) = bytes.get(offset..) else { return CheckedPair { status: 0, value: 0 }; };
    let Some(array) = tail.first_chunk::<8>() else { return CheckedPair { status: 0, value: 0 }; };
    // No end addition or array initializer. One exact8-byte copy, established
    // by the checked tail and fixed first_chunk, feeds the scalar LE decode.
    CheckedPair { status: 1, value: u64::from_le_bytes(*array) }
}
fn reply(status: u64, reason: u64, s: &[u64; 12], debit: u64) -> FixtureEnvelopeReplyV1 {
    FixtureEnvelopeReplyV1 { words: [status, reason, s[0], s[7], s[4], s[5], s[3], s[8], s[9], s[11], s[10], s[1], s[2], debit, 0, 0] }
}
fn poisoned(debit: u64) -> FixtureEnvelopeReplyV1 {
    FixtureEnvelopeReplyV1 { words: [3, 15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, debit, 0, 0] }
}
fn shape(w: &[u64; 16]) -> bool {
    let k = w[1]; let f = w[6];
    if k == 0 || k > 14 || w[2] > 5 { return false; }
    let absent = w[7] == ABSENT && w[8] == ABSENT && w[9] == ABSENT;
    let no_slots = w[10] == ABSENT && w[11] == ABSENT && w[12] == 0;
    let full = f < 80_000 && w[7] != ABSENT && w[8] != ABSENT && w[9] <= u32::MAX as u64 && w[7] <= ABSENT - w[8];
    match k {
        1 => w[3] > 0 && f < 80_000 && absent && no_slots && w[13] == 0 && w[14] == 0 && w[15] == 0,
        2 => w[3] > 0 && full && w[11] == ABSENT && w[12] == 0 && w[14] == 0 && w[15] == 0 && ((w[13] == 0 && w[10] == ABSENT) || (w[13] == 1 && w[10] < 64)),
        3 => w[3] > 0 && full && no_slots && w[13] == 0 && w[14] == 0 && w[15] == (f & 511),
        4 => w[3] > 0 && full && no_slots && w[15] == (f & 511) && (((w[13] == 0 || w[13] == 2) && w[14] == ABSENT) || (w[13] == 1 && w[14] < 80_000 && w[14] != f)),
        5 => w[3] > 0 && full && no_slots && w[13] > 0 && w[14] <= w[15] && w[13] <= w[15] - w[14],
        6..=8 => w[3] > 0 && full && w[10] < 64 && w[11] == ABSENT && w[12] == 0 && w[13] > 0 && w[14] == 0 && w[15] == 0,
        9 | 10 => w[3] > 0 && full && no_slots && w[13] > 0 && w[14] == 0 && w[15] == 0,
        11 => w[3] > 0 && full && w[10] < 64 && w[11] < 64 && w[12] > 0 && w[13] <= 1 && w[14] > 0 && w[15] > 0 && w[15] <= 64,
        12 => w[3] == 0 && f < 80_000 && w[7] != ABSENT && w[8] == ABSENT && w[9] <= u32::MAX as u64 && w[10] < 64 && w[11] < 64 && w[12] > 0 && w[13] > 0 && w[14] == 0 && w[15] < 64,
        13 => w[3] == 0 && f == ABSENT && absent && no_slots && w[13] == w[2] && w[14] == 0 && w[15] == 0,
        14 => absent && (f == ABSENT || f < 80_000) && no_slots && w[13] > 0 && w[13] <= 21 && w[14] > 0 && w[14] <= 24 && w[15] > 0 && w[15] <= 6,
        _ => false,
    }
}

fn observe_fixture_envelope_v1(arena: &mut [u8], candidate: &mut Candidate2048, record: &FixtureDecodedRecordV1<'_>, steps: &mut StepBudget) -> FixtureEnvelopeReplyV1 {
    // The separately prepaid112 guard owns terminal absent-state/invalid-budget
    // poison0 and present-state Steps0. Main B471/public425 remains paid.
    // Its complete terminal reply latches before any later orchestrated leaf.
    // Check readability before any private budget access, prior read or mutation.
    // This same exclusive slice and length survive through every commit write.
    if arena.len() < 7_731_056 { return poisoned(0); }
    if steps.spent != 0 { return poisoned(0); }
    let underfunded = steps.remaining < RECORD_ENVELOPE;
    if !underfunded { steps.remaining -= RECORD_ENVELOPE; steps.spent = RECORD_ENVELOPE; }
    let mut prior = [0u64; 12];
    let mut word = [0u8; 8];
    word.copy_from_slice(&arena[7_729_816..7_729_824]); prior[0] = u64::from_le_bytes(word);
    word.copy_from_slice(&arena[7_729_832..7_729_840]); prior[1] = u64::from_le_bytes(word);
    word.copy_from_slice(&arena[7_729_840..7_729_848]); prior[2] = u64::from_le_bytes(word);
    word.copy_from_slice(&arena[7_729_848..7_729_856]); prior[3] = u64::from_le_bytes(word);
    word.copy_from_slice(&arena[7_729_856..7_729_864]); prior[4] = u64::from_le_bytes(word);
    word.copy_from_slice(&arena[7_729_864..7_729_872]); prior[5] = u64::from_le_bytes(word);
    word.copy_from_slice(&arena[7_729_872..7_729_880]); prior[6] = u64::from_le_bytes(word);
    word.copy_from_slice(&arena[7_730_272..7_730_280]); prior[7] = u64::from_le_bytes(word);
    word.copy_from_slice(&arena[7_730_280..7_730_288]); prior[8] = u64::from_le_bytes(word);
    word.copy_from_slice(&arena[7_730_288..7_730_296]); prior[9] = u64::from_le_bytes(word);
    word.copy_from_slice(&arena[7_731_040..7_731_048]); prior[10] = u64::from_le_bytes(word);
    word.copy_from_slice(&arena[7_731_048..7_731_056]); prior[11] = u64::from_le_bytes(word);
    if underfunded { return reply(2, 1, &prior, 0); }
    if prior[7] > 10 || prior[4] > 5 || prior[5] >= 64 || prior[6] >= 64 || prior[10] > 1 || prior[11] > 1 { return poisoned(RECORD_ENVELOPE); }
    let w = record.words;
    if !shape(w) { return reply(2, 2, &prior, RECORD_ENVELOPE); }
    if prior[0] == ABSENT || w[0] != prior[0] + 1 || w[4] < prior[1] || w[5] < prior[2] { return reply(2, 3, &prior, RECORD_ENVELOPE); }
    if prior[4] == 5 { return reply(2, 4, &prior, RECORD_ENVELOPE); }
    let mut next = prior;
    if w[1] == 13 {
        if prior[7] != 0 || w[2] <= prior[4] || prior[5] & (1 << w[2]) != 0 { return reply(2, 5, &prior, RECORD_ENVELOPE); }
        next[4] = w[2]; next[5] |= 1 << w[2];
    } else {
        if w[2] != prior[4] { return reply(2, 5, &prior, RECORD_ENVELOPE); }
        if w[1] == 12 {
            if prior[7] != 0 { return reply(2, 6, &prior, RECORD_ENVELOPE); }
        } else if w[1] == 14 {
            if w[3] == 0 {
                if prior[7] != 0 || prior[10] != 0 { return reply(2, 7, &prior, RECORD_ENVELOPE); }
                next[10] = 1;
            } else {
                if prior[7] == 0 || prior[11] != 0 || prior[10] != 0 || w[3] != prior[8] { return reply(2, 8, &prior, RECORD_ENVELOPE); }
                next[7] = 0; next[11] = 1;
            }
        } else {
            if prior[10] != 0 || prior[11] != 0 { return reply(2, 9, &prior, RECORD_ENVELOPE); }
            if w[1] == 1 {
                if prior[7] != 0 || prior[4] >= 4 || prior[3] == ABSENT || w[3] != prior[3] + 1 { return reply(2, 10, &prior, RECORD_ENVELOPE); }
                next[7] = 1; next[3] = w[3]; next[8] = w[3]; next[9] = w[6];
            } else {
                if w[3] != prior[8] || w[6] != prior[9] { return reply(2, 11, &prior, RECORD_ENVELOPE); }
                if w[1] == 2 {
                    if prior[7] != 1 { return reply(2, 12, &prior, RECORD_ENVELOPE); }
                    next[7] = if w[13] == 1 { 2 } else { 3 };
                } else if w[1] == 11 {
                    if !((prior[7] == 2 && w[13] == 0) || (prior[7] == 10 && w[13] == 1)) { return reply(2, 13, &prior, RECORD_ENVELOPE); }
                    next[7] = 0;
                } else {
                    let (before, after) = match w[1] { 3 => (3, 4), 4 => (4, 5), 5 => (5, 6), 6 => (6, 7), 7 => (7, 8), 8 => (8, 6), 9 => (6, 9), 10 => (9, 10), _ => return poisoned(RECORD_ENVELOPE) };
                    if prior[7] != before { return reply(2, 12, &prior, RECORD_ENVELOPE); }
                    next[7] = after;
                }
            }
        }
    }
    next[0] = w[0]; next[1] = w[4]; next[2] = w[5];
    // All12destination ranges were proved by the fixed length check before mutation.
    // The exclusive slice owner/length cannot change before commit. The sized
    // candidate and compile-checked PAYLOAD/range bounds prove every staging
    // destination before these fixed copies; no second fallible range helper is needed.
    candidate[888..896].copy_from_slice(&next[0].to_le_bytes());
    candidate[896..904].copy_from_slice(&next[1].to_le_bytes());
    candidate[904..912].copy_from_slice(&next[2].to_le_bytes());
    candidate[912..920].copy_from_slice(&next[3].to_le_bytes());
    candidate[920..928].copy_from_slice(&next[4].to_le_bytes());
    candidate[928..936].copy_from_slice(&next[5].to_le_bytes());
    candidate[936..944].copy_from_slice(&next[6].to_le_bytes());
    candidate[944..952].copy_from_slice(&next[7].to_le_bytes());
    candidate[952..960].copy_from_slice(&next[8].to_le_bytes());
    candidate[960..968].copy_from_slice(&next[9].to_le_bytes());
    candidate[968..976].copy_from_slice(&next[10].to_le_bytes());
    candidate[976..984].copy_from_slice(&next[11].to_le_bytes());
    // No fallible function, I/O, allocator or callback after the first write.
    arena[7_729_816..7_729_824].copy_from_slice(&candidate[888..896]);
    arena[7_729_832..7_729_840].copy_from_slice(&candidate[896..904]);
    arena[7_729_840..7_729_848].copy_from_slice(&candidate[904..912]);
    arena[7_729_848..7_729_856].copy_from_slice(&candidate[912..920]);
    arena[7_729_856..7_729_864].copy_from_slice(&candidate[920..928]);
    arena[7_729_864..7_729_872].copy_from_slice(&candidate[928..936]);
    arena[7_729_872..7_729_880].copy_from_slice(&candidate[936..944]);
    arena[7_730_272..7_730_280].copy_from_slice(&candidate[944..952]);
    arena[7_730_280..7_730_288].copy_from_slice(&candidate[952..960]);
    arena[7_730_288..7_730_296].copy_from_slice(&candidate[960..968]);
    arena[7_731_040..7_731_048].copy_from_slice(&candidate[968..976]);
    arena[7_731_048..7_731_056].copy_from_slice(&candidate[976..984]);
    reply(1, 0, &next, RECORD_ENVELOPE)
}

fn reason_from_leaf(value: u64) -> FixtureEnvelopeReasonV1 {
    match value {
        0 => FixtureEnvelopeReasonV1::Observed, 1 => FixtureEnvelopeReasonV1::Steps,
        2 => FixtureEnvelopeReasonV1::Shape, 3 => FixtureEnvelopeReasonV1::Coordinate,
        4 => FixtureEnvelopeReasonV1::TerminalPhase, 5 => FixtureEnvelopeReasonV1::Phase,
        6 => FixtureEnvelopeReasonV1::ReleaseOpen, 7 => FixtureEnvelopeReasonV1::TerminalFailure,
        8 => FixtureEnvelopeReasonV1::PinFailure, 9 => FixtureEnvelopeReasonV1::ForbiddenResume,
        10 => FixtureEnvelopeReasonV1::Acquire, 11 => FixtureEnvelopeReasonV1::Identity,
        12 => FixtureEnvelopeReasonV1::Stage, 13 => FixtureEnvelopeReasonV1::PublicationForm,
        14 => FixtureEnvelopeReasonV1::CheckedAccess, 15 => FixtureEnvelopeReasonV1::InternalPoisoned,
        _ => FixtureEnvelopeReasonV1::UnavailableState,
    }
}
fn project(p: &FixtureEnvelopeProgressV1, boundary: FixtureEnvelopeBoundaryV1, reason: FixtureEnvelopeReasonV1, extent: bool) -> FixtureEnvelopeObservationV1 {
    let w = &p.reply.words;
    FixtureEnvelopeObservationV1 {
        boundary, reason, observed_records: if extent { w[2] } else { 0 },
        state: if extent { w[3] } else { 0 }, phase: if extent { w[4] } else { 0 }, mask: if extent { w[5] } else { 0 },
        last_operation: if extent { w[6] } else { 0 }, active_operation: if extent { w[7] } else { 0 },
        requested_function: if extent { w[8] } else { 0 }, pin_failure: if extent { w[9] } else { 0 },
        terminal_failure: if extent { w[10] } else { 0 }, last_work: if extent { w[11] } else { 0 },
        last_instructions: if extent { w[12] } else { 0 }, envelope_debit: p.debit,
        full_replay_accepted: 0, stored_prefix_validated: 0,
    }
}
fn finalize(p: &FixtureEnvelopeProgressV1, s: &Framing, input: &Result<bool, AnalyzerError>, arena: &Arena) -> FixtureEnvelopeObservationV1 {
    use FixtureEnvelopeBoundaryV1 as B;
    use FixtureEnvelopeReasonV1 as R;
    if let Err(e) = input {
        let reason = if e.code == BINDING { R::FramingUnavailable } else if e.code == BUDGET { R::FramingLimited } else { R::FramingInvalid };
        return project(p, B::Unavailable, reason, false);
    }
    if s.flags > 1 || !((s.complete && !s.limited && matches!(input, Ok(true))) || (s.limited && !s.complete && matches!(input, Ok(false)))) {
        return project(p, B::Unavailable, R::UnavailableState, false);
    }
    if p.reply_valid == 0 { return project(p, B::Unavailable, R::EnvelopeUnavailable, false); }
    if p.reply_valid != 1 { return project(p, B::Unavailable, R::UnavailableState, false); }
    // Poison precedes CAP and any state dereference, including stale state.
    if p.reply.words[0] == 3 || p.reply.words[1] == 15 {
        return project(p, if s.limited { B::AnalysisLimited } else { B::InternalPoisoned }, R::InternalPoisoned, false);
    }
    if !(1..=2).contains(&p.reply.words[0]) || p.reply.words[1] > 14
        || (p.reply.words[0] == 1 && p.reply.words[1] != 0) || (p.reply.words[0] == 2 && p.reply.words[1] == 0)
        || p.reply.words[3] > 10 || p.reply.words[4] > 5 || p.reply.words[5] >= 64
        || p.reply.words[9] > 1 || p.reply.words[10] > 1 {
        return project(p, B::Unavailable, R::UnavailableState, false);
    }
    if s.limited {
        return project(p, B::AnalysisLimited, if p.reply.words[0] == 2 { reason_from_leaf(p.reply.words[1]) } else { R::FramingLimited }, true);
    }
    if p.reply.words[0] == 2 { return project(p, B::Refused, reason_from_leaf(p.reply.words[1]), true); }
    if s.flags == 1 { return project(p, B::CapCutUnknownTail, R::Observed, true); }
    let expected = word_at(&arena.bytes, SCALAR.base + 8 * CELLS[6]);
    if expected.status != 1 { return project(p, B::InternalPoisoned, R::InternalPoisoned, false); }
    if p.reply.words[3] == 0 && p.reply.words[4] == 5 && p.reply.words[5] == expected.value { project(p, B::ClosedEnvelopeObserved, R::Observed, true) }
    else { project(p, B::Refused, R::IncompleteBoundary, true) }
}
fn leaf_pending(p: &FixtureEnvelopeProgressV1) -> bool {
    if p.reply_valid == 0 { return true; }
    if p.reply_valid != 1 || p.reply.words[0] == 3 || p.reply.words[1] == 15 { return false; }
    p.reply.words[0] == 1
}
fn reply_debit_valid(reply: &FixtureEnvelopeReplyV1, steps: &StepBudget) -> bool {
    if steps.spent == RECORD_ENVELOPE {
        return steps.remaining == 0 && reply.words[13] == RECORD_ENVELOPE;
    }
    if steps.spent != 0 || reply.words[13] != 0 { return false; }
    if reply.words[1] == 15 { return reply.words[0] == 3; }
    reply.words[1] == 1 && reply.words[0] == 2 && steps.remaining < RECORD_ENVELOPE
}

fn walk_fixture_envelope_v1<T: InputFile>(input: &mut T, arena: &mut Arena, budget: &mut Budget, f: Fixture, length: u64, s: &mut Framing, p: &mut FixtureEnvelopeProgressV1) -> Result<(), AnalyzerError> {
    let mut reader = Reader::new(length, HEADER_STAGE);
    let mut h = [0; 64]; reader.words(input, arena, budget, &mut h)?;
    header(arena, &h, f, budget)?;
    budget.setup(SETUP_ENVELOPE)?; p.debit += SETUP_ENVELOPE;
    budget.report(FINISH_ENVELOPE)?; p.debit += FINISH_ENVELOPE;
    budget.report(UNDERFUNDED_GUARD)?;
    let mut candidate: Candidate2048 = [0u8; 2048];
    // Complete candidate source/destination setup is prepaid; no reply exists.
    if arena.bytes.len() != ARENA_BYTES { return Err(error(INTERNAL, ARENA_STAGE, 0, 0)); }
    for i in 0..12 {
        let value = if i == 5 { 1 } else if i == 6 { f.mask } else { 0 };
        let at = SCALAR.base + CELLS[i] * 8;
        arena.bytes[at..at + 8].copy_from_slice(&value.to_le_bytes());
    }
    reader.stage = RECORD_STAGE;
    for index in 0..s.physical {
        if budget.replay_left < RECORD_PREFLIGHT { s.limited = true; break; }
        budget.replay(COMBINED_RECORD)?; p.debit += RECORD_ENVELOPE;
        let mut w = [0; 16]; reader.words(input, arena, budget, &mut w)?;
        let offset = 512 + index * 128;
        if !record_fields(arena, &w, f) { return Err(error(SCHEMA, RECORD_STAGE, offset, index + 1)); }
        if !s.coordinate(&w) { return Err(error(COORDINATE, RECORD_STAGE, offset, index + 1)); }
        if leaf_pending(p) {
            let record = FixtureDecodedRecordV1 { words: &w };
            let mut steps = StepBudget { remaining: RECORD_ENVELOPE, spent: 0 };
            let received = observe_fixture_envelope_v1(&mut arena.bytes, &mut candidate, &record, &mut steps);
            p.reply = received; p.reply_valid = 1;
            if !reply_debit_valid(&p.reply, &steps) { p.reply = poisoned(RECORD_ENVELOPE); }
        }
    }
    if s.limited {
        let target = length - 512;
        while reader.consumed < target {
            budget.setup(1)?;
            let available = (reader.used - reader.cursor) as u64;
            let n = available.min(target - reader.consumed);
            reader.cursor += n as usize; reader.consumed += n;
            if reader.consumed == target { break; }
            if reader.cursor != reader.used { return Err(error(INTERNAL, RECORD_STAGE, reader.consumed, 0)); }
            let count = (reader.length - reader.loaded).min(65_536) as usize;
            bounded_read(input, &mut arena.bytes[BLOCK.base..BLOCK.base + count], budget, RECORD_STAGE, reader.loaded)?;
            reader.loaded += count as u64; reader.used = count; reader.cursor = 0;
        }
    }
    reader.stage = FOOTER_STAGE;
    let mut foot = [0; 64]; reader.words(input, arena, budget, &mut foot)?;
    footer(&h, &foot, length, s, budget)?;
    eof(input, budget, FOOTER_STAGE, length)?;
    s.complete = !s.limited;
    Ok(())
}
fn observe_inputs_fixture_envelope_v1<S: InputFile, P: InputFile, C: InputFile>(stream: &mut S, profile_file: &mut P, context: &mut C, arena: &mut Arena, budget: &mut Budget, s: &mut Framing, p: &mut FixtureEnvelopeProgressV1) -> Result<bool, AnalyzerError> {
    let before_s = initial(stream, budget)?; let before_p = initial(profile_file, budget)?; let before_c = initial(context, budget)?;
    if before_s.len() < 1024 || before_s.len() > STREAM_CAP || (before_s.len() - 1024) % 128 != 0 || before_p.len() != PROFILE_BYTES || before_c.len() != CONTEXT_BYTES { return Err(error(INPUT, ADMISSION_STAGE, 0, 0)); }
    s.physical = (before_s.len() - 1024) / 128;
    let f = fixture_context(context, arena, budget)?;
    profile(profile_file, arena, budget, f)?;
    walk_fixture_envelope_v1(stream, arena, budget, f, before_s.len(), s, p)?;
    stable(stream, before_s, budget)?; stable(profile_file, before_p, budget)?; stable(context, before_c, budget)?;
    Ok(s.complete)
}
fn analyze_fixture_envelope_core<S: InputFile, P: InputFile, C: InputFile, O: OutputFile>(stream: &mut S, profile_file: &mut P, context: &mut C, output: &mut O, limit: u64) -> Result<FixtureEnvelopeOutcomeV1, AnalyzerError> {
    let mut budget = Budget::new(limit)?;
    // Named fixed wrapper construction/projection/move work is prepaid even
    // when later input observation fails. No envelope debit is invented here.
    budget.setup(SETUP_WRAPPER)?; budget.report(FINAL_WRAPPER)?;
    let output_initial = output_safety(stream, profile_file, context, output, &mut budget)?;
    let mut arena = Arena::new(&mut budget)?;
    let mut s = Framing::new(0);
    let mut p = FixtureEnvelopeProgressV1 { reply_valid: 0, debit: 0, reply: FixtureEnvelopeReplyV1 { words: [0; 16] } };
    let result = observe_inputs_fixture_envelope_v1(stream, profile_file, context, &mut arena, &mut budget, &mut s, &mut p);
    let mut observation = error(BINDING, CONTEXT_STAGE, 0, 0);
    let mut decision = Decision::Unavailable;
    let mut framed = false;
    if let Err(e) = result {
        observation = e;
        decision = if e.code == BINDING { Decision::Unavailable } else if e.code == BUDGET { Decision::AnalysisLimited } else { Decision::Invalid };
    } else if s.limited { observation = error(BUDGET, RECORD_STAGE, 512 + s.framed * 128, s.framed + 1); decision = Decision::AnalysisLimited; }
    else { framed = result.unwrap_or(false); }
    let envelope = finalize(&p, &s, &result, &arena);
    let mut framing = ReplayOutcome { decision, framed_records: s.framed, physical_records: s.physical, report_bytes: 0, steps_used: 0, input_bytes_read: budget.read_bytes, input_attempts: budget.io_spent, output_attempts: 0, observation, fixture_framing: u64::from(framed) };
    write_report(output, output_initial, &mut arena, &mut budget, &mut framing, s)?;
    if budget.used() > budget.limit { return Err(error(BUDGET, OUTPUT_STAGE, 0, 0)); }
    Ok(FixtureEnvelopeOutcomeV1 { framing, envelope })
}
/// Separate fixture-only safe-File boundary. Caller owns distinct, quiescent
/// regular Files at offset0 and empty exclusive output, as in analyze_fixture.
pub fn analyze_fixture_envelope_v1(stream: &mut File, profile_file: &mut File, context: &mut File, output: &mut File) -> Result<FixtureEnvelopeOutcomeV1, AnalyzerError> {
    analyze_fixture_envelope_core(stream, profile_file, context, output, STEP_LIMIT)
}

#[cfg(test)]
#[path = "../tests/envelope_tests.rs"]
mod tests;
#[cfg(test)]
#[path = "../tests/correction_tests.rs"]
mod correction_tests;
