//! Standalone fixture-only successful cache transitions. No release authority.
use super::*;
const SEMANTIC_RECORD: u64 = 7680;
const CACHE_COMBINED: u64 = 8151;
const SEMANTIC_SETUP: u64 = 512;
const SEMANTIC_FINISH: u64 = 256;
const SEMANTIC_GUARD: u64 = 128;
const SC: usize = 1688;
// Snapshot words M,work,instructions,stage,operation,function,count,bytes,pins,
// nonce,selected,taken,committed,pending,destination,feasible. Additional staged
// words free_pin,lookup_slot,requested_bytes occupy 16..18. All other words zero.
const EXTRA_CELLS: [usize; 2] = [71, 78];
const ROW_CELLS: [usize; 10] = [21, 22, 23, 17, 128, 130, 131, 137, 84, 141];
#[derive(Debug, PartialEq, Eq)]
#[repr(u64)]
pub enum FixtureCacheStateBoundaryV1 {
    Unavailable = 0,
    ClosedFixtureObserved = 1,
    CapCutUnknownTail = 2,
    Refused = 3,
    AnalysisLimited = 4,
    InternalPoisoned = 5,
    ApplicabilityUnavailable = 6,
}
#[derive(Debug, PartialEq, Eq)]
#[repr(u64)]
pub enum FixtureCacheStateReasonV1 {
    Observed = 0,
    Steps = 1,
    FramingUnavailable = 2,
    FramingInvalid = 3,
    EnvelopeRefused = 4,
    EnvelopeUnavailable = 5,
    Identity = 6,
    Resident = 7,
    Plan = 8,
    Victim = 9,
    Bytes = 10,
    Token = 11,
    Nonce = 12,
    Invariant = 13,
    FailureApplicability = 14,
    IncompleteBoundary = 15,
    InternalPoison = 16,
    OutputUnavailable = 17,
}
#[derive(Debug)]
#[repr(C)]
pub struct FixtureCacheStateObservationV1 {
    boundary: FixtureCacheStateBoundaryV1,
    reason: FixtureCacheStateReasonV1,
    extent: [u64; 30],
}
impl FixtureCacheStateObservationV1 {
    pub fn boundary(&self) -> &FixtureCacheStateBoundaryV1 {
        &self.boundary
    }
    pub fn reason(&self) -> &FixtureCacheStateReasonV1 {
        &self.reason
    }
    pub const fn stored_prefix_validated(&self) -> bool {
        false
    }
    pub const fn full_replay_accepted(&self) -> bool {
        false
    }
    pub const fn semantic_metrics_valid(&self) -> bool {
        false
    }
    pub const fn real_binding_verified(&self) -> bool {
        false
    }
}
#[derive(Debug)]
#[repr(C)]
pub struct FixtureCacheStateOutcomeV1 {
    framing: ReplayOutcome,
    envelope: FixtureEnvelopeObservationV1,
    cache_state: FixtureCacheStateObservationV1,
}
impl FixtureCacheStateOutcomeV1 {
    pub fn framing(&self) -> &ReplayOutcome {
        &self.framing
    }
    pub fn envelope(&self) -> &FixtureEnvelopeObservationV1 {
        &self.envelope
    }
    pub fn cache_state(&self) -> &FixtureCacheStateObservationV1 {
        &self.cache_state
    }
    pub const fn stored_prefix_validated(&self) -> bool {
        false
    }
    pub const fn full_replay_accepted(&self) -> bool {
        false
    }
    pub const fn semantic_metrics_valid(&self) -> bool {
        false
    }
    pub const fn real_binding_verified(&self) -> bool {
        false
    }
}
#[repr(C)]
struct Progress {
    calls: u64,
    latch: u64,
    q: [u64; 16],
}
impl Progress {
    // Low byte is the absorbing terminal tag. Bits8..14 retain the first-free
    // pin as slot+1;0means absent. Remaining bits are a malformed header.
    fn terminal(&self) -> u64 {
        self.latch & 255
    }
    fn first_pin(&self) -> u64 {
        let n = self.latch >> 8;
        if n == 0 {
            ABSENT
        } else {
            n - 1
        }
    }
    fn latch_terminal(&mut self, n: u64) {
        self.latch = (self.latch & !255) | n;
    }
    fn remember_pin(&mut self, n: u64) {
        self.latch = (self.latch & 255) | if n == ABSENT { 0 } else { (n + 1) << 8 };
    }
}
#[repr(C)]
struct Paid {
    setup: u64,
    finish: u64,
    records: u64,
}
#[repr(C)]
struct SemanticReply {
    status: u64,
    reason: u64,
    debit: u64,
}
// A loan exists only after actual wire/profile checks and audited envelope
// success. The immutable config borrow and exclusive arena slice cannot resize.
struct Loan<'a> {
    record: &'a FixtureDecodedRecordV1<'a>,
    config: &'a Fixture,
}
fn ld(b: &[u8], at: usize) -> u64 {
    u64::from_le_bytes(
        *b[at..at + 8]
            .first_chunk::<8>()
            .expect("proved eight-byte range"),
    )
}
fn st(b: &mut [u8], at: usize, n: u64) {
    b[at..at + 8].copy_from_slice(&n.to_le_bytes());
}
fn cq(c: &Candidate2048, i: usize) -> u64 {
    ld(c, SC + 8 * i)
}
fn sq(c: &mut Candidate2048, i: usize, n: u64) {
    st(c, SC + 8 * i, n);
}
fn rr(b: &[u8], row: usize, field: usize) -> u64 {
    ld(b, RESIDENT.base + 64 * row + 8 * field)
}
fn pr(b: &[u8], row: usize, field: usize) -> u64 {
    ld(b, PIN.base + 48 * row + 8 * field)
}
fn pl(b: &[u8], row: usize, field: usize) -> u64 {
    ld(b, PLAN.base + 40 * row + 8 * field)
}
fn reject(reason: u64) -> SemanticReply {
    SemanticReply {
        status: 2,
        reason,
        debit: SEMANTIC_RECORD,
    }
}
fn poison(debit: u64) -> SemanticReply {
    SemanticReply {
        status: 3,
        reason: 16,
        debit,
    }
}
fn selected_mask(slots: u64) -> u64 {
    if slots == 64 {
        ABSENT
    } else {
        (1u64 << slots) - 1
    }
}
fn shape_q(q: &[u64; 16], calls: u64, latch: u64, n: u64, f: &Fixture) -> bool {
    if q[0] > n
        || calls > n
        || q[3] > 10
        || q[6] > f.slots
        || q[8] > f.pins
        || q[9] == 0
        || (q[6] == 0) != (q[7] == 0)
        || (q[8] > 0 && q[6] == 0)
    {
        return false;
    }
    if q[3] != 0 && (q[4] == 0 || q[5] >= 80000) {
        return false;
    }
    // Q7/Q8/Q9/Q10: planned-only fields are not read outside stages6..10.
    // Within pending stages7/8, feasibility must hold before pending is read.
    if (6..=10).contains(&q[3]) {
        if (q[10] | q[11] | q[12]) & !selected_mask(f.slots) != 0
            || q[11] & !q[10] != 0
            || q[12] & !q[11] != 0
        {
            return false;
        }
        if q[15] > 1 || (q[15] == 1 && q[14] >= f.slots) {
            return false;
        }
        if (q[3] == 7 || q[3] == 8) && (q[15] != 1 || q[13] >= f.slots || q[10] & (1 << q[13]) == 0)
        {
            return false;
        }
    }
    if q[0] == 0
        && (q[1] != 0 || q[2] != 0 || q[3] != 0 || q[6] != 0 || q[7] != 0 || q[8] != 0 || q[9] != 1)
    {
        return false;
    }
    if latch == 0 {
        calls == q[0] && q[0] == n && calls > 0
    } else {
        (latch == 1 || (6..=14).contains(&latch)) && calls == q[0] + 1 && calls <= n
    }
}
// Eligibility uses index MAX, never timestamp MAX. Every timestamp is read once
// during the resident probe. Stable left preference resolves equal timestamps
// by the initial ascending slot order. Six fixed passes emit exactly384 moves;
// merge comparisons <=32+48+56+60+62+63=321, including tail MAX comparisons.
#[cfg(test)]
static SORT_COMPARISONS: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
#[cfg(test)]
static SORT_MOVES: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
// UNSELECTED SOURCE-ONLY SEEDED WIDTH1 PROPOSAL. Never compiled or run.
// All load/emit blocks are source-written: no helper or macro call boundary.
fn merge(c: &mut Candidate2048) {
    let eligibility = ld(c, 640);
    let (time_bytes, indices) = c.split_at_mut(512);
    let (timestamp_chunks, _) = time_bytes.as_chunks::<8>();
    let timestamps: &[[u8; 8]; 64] = timestamp_chunks.first_chunk::<64>().expect("timestamp64");
    {
        let output = {
            let mut second = u8::MAX;
            [
                {
                    // width1 pair0; literals are actual source operands.
                    let left = if eligibility & 0x0000000000000001u64 != 0 { 0u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000000000000002u64 != 0 { 1u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[0usize]);
                    let rt = u64::from_le_bytes(timestamps[1usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair1; literals are actual source operands.
                    let left = if eligibility & 0x0000000000000004u64 != 0 { 2u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000000000000008u64 != 0 { 3u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[2usize]);
                    let rt = u64::from_le_bytes(timestamps[3usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair2; literals are actual source operands.
                    let left = if eligibility & 0x0000000000000010u64 != 0 { 4u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000000000000020u64 != 0 { 5u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[4usize]);
                    let rt = u64::from_le_bytes(timestamps[5usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair3; literals are actual source operands.
                    let left = if eligibility & 0x0000000000000040u64 != 0 { 6u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000000000000080u64 != 0 { 7u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[6usize]);
                    let rt = u64::from_le_bytes(timestamps[7usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair4; literals are actual source operands.
                    let left = if eligibility & 0x0000000000000100u64 != 0 { 8u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000000000000200u64 != 0 { 9u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[8usize]);
                    let rt = u64::from_le_bytes(timestamps[9usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair5; literals are actual source operands.
                    let left = if eligibility & 0x0000000000000400u64 != 0 { 10u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000000000000800u64 != 0 { 11u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[10usize]);
                    let rt = u64::from_le_bytes(timestamps[11usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair6; literals are actual source operands.
                    let left = if eligibility & 0x0000000000001000u64 != 0 { 12u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000000000002000u64 != 0 { 13u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[12usize]);
                    let rt = u64::from_le_bytes(timestamps[13usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair7; literals are actual source operands.
                    let left = if eligibility & 0x0000000000004000u64 != 0 { 14u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000000000008000u64 != 0 { 15u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[14usize]);
                    let rt = u64::from_le_bytes(timestamps[15usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair8; literals are actual source operands.
                    let left = if eligibility & 0x0000000000010000u64 != 0 { 16u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000000000020000u64 != 0 { 17u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[16usize]);
                    let rt = u64::from_le_bytes(timestamps[17usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair9; literals are actual source operands.
                    let left = if eligibility & 0x0000000000040000u64 != 0 { 18u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000000000080000u64 != 0 { 19u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[18usize]);
                    let rt = u64::from_le_bytes(timestamps[19usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair10; literals are actual source operands.
                    let left = if eligibility & 0x0000000000100000u64 != 0 { 20u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000000000200000u64 != 0 { 21u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[20usize]);
                    let rt = u64::from_le_bytes(timestamps[21usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair11; literals are actual source operands.
                    let left = if eligibility & 0x0000000000400000u64 != 0 { 22u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000000000800000u64 != 0 { 23u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[22usize]);
                    let rt = u64::from_le_bytes(timestamps[23usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair12; literals are actual source operands.
                    let left = if eligibility & 0x0000000001000000u64 != 0 { 24u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000000002000000u64 != 0 { 25u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[24usize]);
                    let rt = u64::from_le_bytes(timestamps[25usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair13; literals are actual source operands.
                    let left = if eligibility & 0x0000000004000000u64 != 0 { 26u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000000008000000u64 != 0 { 27u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[26usize]);
                    let rt = u64::from_le_bytes(timestamps[27usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair14; literals are actual source operands.
                    let left = if eligibility & 0x0000000010000000u64 != 0 { 28u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000000020000000u64 != 0 { 29u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[28usize]);
                    let rt = u64::from_le_bytes(timestamps[29usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair15; literals are actual source operands.
                    let left = if eligibility & 0x0000000040000000u64 != 0 { 30u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000000080000000u64 != 0 { 31u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[30usize]);
                    let rt = u64::from_le_bytes(timestamps[31usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair16; literals are actual source operands.
                    let left = if eligibility & 0x0000000100000000u64 != 0 { 32u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000000200000000u64 != 0 { 33u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[32usize]);
                    let rt = u64::from_le_bytes(timestamps[33usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair17; literals are actual source operands.
                    let left = if eligibility & 0x0000000400000000u64 != 0 { 34u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000000800000000u64 != 0 { 35u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[34usize]);
                    let rt = u64::from_le_bytes(timestamps[35usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair18; literals are actual source operands.
                    let left = if eligibility & 0x0000001000000000u64 != 0 { 36u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000002000000000u64 != 0 { 37u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[36usize]);
                    let rt = u64::from_le_bytes(timestamps[37usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair19; literals are actual source operands.
                    let left = if eligibility & 0x0000004000000000u64 != 0 { 38u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000008000000000u64 != 0 { 39u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[38usize]);
                    let rt = u64::from_le_bytes(timestamps[39usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair20; literals are actual source operands.
                    let left = if eligibility & 0x0000010000000000u64 != 0 { 40u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000020000000000u64 != 0 { 41u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[40usize]);
                    let rt = u64::from_le_bytes(timestamps[41usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair21; literals are actual source operands.
                    let left = if eligibility & 0x0000040000000000u64 != 0 { 42u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000080000000000u64 != 0 { 43u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[42usize]);
                    let rt = u64::from_le_bytes(timestamps[43usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair22; literals are actual source operands.
                    let left = if eligibility & 0x0000100000000000u64 != 0 { 44u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000200000000000u64 != 0 { 45u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[44usize]);
                    let rt = u64::from_le_bytes(timestamps[45usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair23; literals are actual source operands.
                    let left = if eligibility & 0x0000400000000000u64 != 0 { 46u8 } else { u8::MAX };
                    let right = if eligibility & 0x0000800000000000u64 != 0 { 47u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[46usize]);
                    let rt = u64::from_le_bytes(timestamps[47usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair24; literals are actual source operands.
                    let left = if eligibility & 0x0001000000000000u64 != 0 { 48u8 } else { u8::MAX };
                    let right = if eligibility & 0x0002000000000000u64 != 0 { 49u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[48usize]);
                    let rt = u64::from_le_bytes(timestamps[49usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair25; literals are actual source operands.
                    let left = if eligibility & 0x0004000000000000u64 != 0 { 50u8 } else { u8::MAX };
                    let right = if eligibility & 0x0008000000000000u64 != 0 { 51u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[50usize]);
                    let rt = u64::from_le_bytes(timestamps[51usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair26; literals are actual source operands.
                    let left = if eligibility & 0x0010000000000000u64 != 0 { 52u8 } else { u8::MAX };
                    let right = if eligibility & 0x0020000000000000u64 != 0 { 53u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[52usize]);
                    let rt = u64::from_le_bytes(timestamps[53usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair27; literals are actual source operands.
                    let left = if eligibility & 0x0040000000000000u64 != 0 { 54u8 } else { u8::MAX };
                    let right = if eligibility & 0x0080000000000000u64 != 0 { 55u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[54usize]);
                    let rt = u64::from_le_bytes(timestamps[55usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair28; literals are actual source operands.
                    let left = if eligibility & 0x0100000000000000u64 != 0 { 56u8 } else { u8::MAX };
                    let right = if eligibility & 0x0200000000000000u64 != 0 { 57u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[56usize]);
                    let rt = u64::from_le_bytes(timestamps[57usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair29; literals are actual source operands.
                    let left = if eligibility & 0x0400000000000000u64 != 0 { 58u8 } else { u8::MAX };
                    let right = if eligibility & 0x0800000000000000u64 != 0 { 59u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[58usize]);
                    let rt = u64::from_le_bytes(timestamps[59usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair30; literals are actual source operands.
                    let left = if eligibility & 0x1000000000000000u64 != 0 { 60u8 } else { u8::MAX };
                    let right = if eligibility & 0x2000000000000000u64 != 0 { 61u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[60usize]);
                    let rt = u64::from_le_bytes(timestamps[61usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
                {
                    // width1 pair31; literals are actual source operands.
                    let left = if eligibility & 0x4000000000000000u64 != 0 { 62u8 } else { u8::MAX };
                    let right = if eligibility & 0x8000000000000000u64 != 0 { 63u8 } else { u8::MAX };
                    let lt = u64::from_le_bytes(timestamps[62usize]);
                    let rt = u64::from_le_bytes(timestamps[63usize]);
                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };
                    if take_left { second = right; left } else { second = left; right }
                },
                { second },
            ]
        };
        indices[512..576].copy_from_slice(&output);
    }
    {
        let output = {
            let source: &[u8; 64] = indices[512..576].first_chunk::<64>().expect("index64");
            let mut lp: usize = 0;
            let mut le: usize = 2;
            let mut rp: usize = 2;
            let mut re: usize = 4;
            let mut li: u16 = 256;
            let mut ri: u16 = 256;
            let mut lt: u64 = 0;
            let mut rt: u64 = 0;
            // p1: inline initial heads.
            {
                let index = source[lp];
                li = index as u16;
                if index != u8::MAX {
                    lt = u64::from_le_bytes(timestamps[index as usize]);
                }
                let index = source[rp];
                ri = index as u16;
                if index != u8::MAX {
                    rt = u64::from_le_bytes(timestamps[index as usize]);
                }
            }
            [
                {
                    // p1.out0: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out1: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out2: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out3: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out4: fully expanded emit expression.
                    lp = 4; le = 6;
                    rp = 6; re = 8;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out5: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out6: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out7: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out8: fully expanded emit expression.
                    lp = 8; le = 10;
                    rp = 10; re = 12;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out9: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out10: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out11: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out12: fully expanded emit expression.
                    lp = 12; le = 14;
                    rp = 14; re = 16;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out13: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out14: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out15: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out16: fully expanded emit expression.
                    lp = 16; le = 18;
                    rp = 18; re = 20;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out17: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out18: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out19: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out20: fully expanded emit expression.
                    lp = 20; le = 22;
                    rp = 22; re = 24;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out21: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out22: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out23: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out24: fully expanded emit expression.
                    lp = 24; le = 26;
                    rp = 26; re = 28;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out25: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out26: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out27: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out28: fully expanded emit expression.
                    lp = 28; le = 30;
                    rp = 30; re = 32;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out29: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out30: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out31: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out32: fully expanded emit expression.
                    lp = 32; le = 34;
                    rp = 34; re = 36;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out33: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out34: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out35: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out36: fully expanded emit expression.
                    lp = 36; le = 38;
                    rp = 38; re = 40;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out37: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out38: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out39: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out40: fully expanded emit expression.
                    lp = 40; le = 42;
                    rp = 42; re = 44;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out41: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out42: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out43: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out44: fully expanded emit expression.
                    lp = 44; le = 46;
                    rp = 46; re = 48;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out45: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out46: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out47: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out48: fully expanded emit expression.
                    lp = 48; le = 50;
                    rp = 50; re = 52;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out49: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out50: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out51: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out52: fully expanded emit expression.
                    lp = 52; le = 54;
                    rp = 54; re = 56;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out53: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out54: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out55: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out56: fully expanded emit expression.
                    lp = 56; le = 58;
                    rp = 58; re = 60;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out57: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out58: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out59: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out60: fully expanded emit expression.
                    lp = 60; le = 62;
                    rp = 62; re = 64;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out61: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out62: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p1.out63: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
            ]
        };
        indices[0..64].copy_from_slice(&output);
    }
    {
        let output = {
            let source: &[u8; 64] = indices[0..64].first_chunk::<64>().expect("index64");
            let mut lp: usize = 0;
            let mut le: usize = 4;
            let mut rp: usize = 4;
            let mut re: usize = 8;
            let mut li: u16 = 256;
            let mut ri: u16 = 256;
            let mut lt: u64 = 0;
            let mut rt: u64 = 0;
            // p2: inline initial heads.
            {
                let index = source[lp];
                li = index as u16;
                if index != u8::MAX {
                    lt = u64::from_le_bytes(timestamps[index as usize]);
                }
                let index = source[rp];
                ri = index as u16;
                if index != u8::MAX {
                    rt = u64::from_le_bytes(timestamps[index as usize]);
                }
            }
            [
                {
                    // p2.out0: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out1: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out2: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out3: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out4: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out5: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out6: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out7: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out8: fully expanded emit expression.
                    lp = 8; le = 12;
                    rp = 12; re = 16;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out9: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out10: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out11: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out12: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out13: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out14: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out15: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out16: fully expanded emit expression.
                    lp = 16; le = 20;
                    rp = 20; re = 24;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out17: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out18: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out19: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out20: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out21: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out22: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out23: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out24: fully expanded emit expression.
                    lp = 24; le = 28;
                    rp = 28; re = 32;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out25: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out26: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out27: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out28: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out29: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out30: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out31: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out32: fully expanded emit expression.
                    lp = 32; le = 36;
                    rp = 36; re = 40;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out33: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out34: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out35: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out36: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out37: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out38: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out39: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out40: fully expanded emit expression.
                    lp = 40; le = 44;
                    rp = 44; re = 48;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out41: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out42: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out43: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out44: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out45: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out46: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out47: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out48: fully expanded emit expression.
                    lp = 48; le = 52;
                    rp = 52; re = 56;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out49: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out50: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out51: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out52: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out53: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out54: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out55: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out56: fully expanded emit expression.
                    lp = 56; le = 60;
                    rp = 60; re = 64;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out57: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out58: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out59: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out60: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out61: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out62: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p2.out63: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
            ]
        };
        indices[512..576].copy_from_slice(&output);
    }
    {
        let output = {
            let source: &[u8; 64] = indices[512..576].first_chunk::<64>().expect("index64");
            let mut lp: usize = 0;
            let mut le: usize = 8;
            let mut rp: usize = 8;
            let mut re: usize = 16;
            let mut li: u16 = 256;
            let mut ri: u16 = 256;
            let mut lt: u64 = 0;
            let mut rt: u64 = 0;
            // p3: inline initial heads.
            {
                let index = source[lp];
                li = index as u16;
                if index != u8::MAX {
                    lt = u64::from_le_bytes(timestamps[index as usize]);
                }
                let index = source[rp];
                ri = index as u16;
                if index != u8::MAX {
                    rt = u64::from_le_bytes(timestamps[index as usize]);
                }
            }
            [
                {
                    // p3.out0: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out1: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out2: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out3: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out4: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out5: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out6: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out7: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out8: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out9: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out10: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out11: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out12: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out13: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out14: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out15: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out16: fully expanded emit expression.
                    lp = 16; le = 24;
                    rp = 24; re = 32;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out17: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out18: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out19: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out20: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out21: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out22: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out23: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out24: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out25: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out26: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out27: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out28: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out29: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out30: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out31: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out32: fully expanded emit expression.
                    lp = 32; le = 40;
                    rp = 40; re = 48;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out33: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out34: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out35: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out36: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out37: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out38: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out39: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out40: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out41: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out42: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out43: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out44: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out45: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out46: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out47: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out48: fully expanded emit expression.
                    lp = 48; le = 56;
                    rp = 56; re = 64;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out49: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out50: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out51: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out52: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out53: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out54: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out55: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out56: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out57: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out58: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out59: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out60: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out61: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out62: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p3.out63: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
            ]
        };
        indices[0..64].copy_from_slice(&output);
    }
    {
        let output = {
            let source: &[u8; 64] = indices[0..64].first_chunk::<64>().expect("index64");
            let mut lp: usize = 0;
            let mut le: usize = 16;
            let mut rp: usize = 16;
            let mut re: usize = 32;
            let mut li: u16 = 256;
            let mut ri: u16 = 256;
            let mut lt: u64 = 0;
            let mut rt: u64 = 0;
            // p4: inline initial heads.
            {
                let index = source[lp];
                li = index as u16;
                if index != u8::MAX {
                    lt = u64::from_le_bytes(timestamps[index as usize]);
                }
                let index = source[rp];
                ri = index as u16;
                if index != u8::MAX {
                    rt = u64::from_le_bytes(timestamps[index as usize]);
                }
            }
            [
                {
                    // p4.out0: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out1: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out2: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out3: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out4: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out5: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out6: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out7: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out8: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out9: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out10: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out11: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out12: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out13: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out14: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out15: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out16: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out17: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out18: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out19: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out20: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out21: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out22: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out23: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out24: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out25: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out26: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out27: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out28: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out29: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out30: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out31: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out32: fully expanded emit expression.
                    lp = 32; le = 48;
                    rp = 48; re = 64;
                    {
                        let index = source[lp];
                        li = index as u16;
                        if index != u8::MAX {
                            lt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                        let index = source[rp];
                        ri = index as u16;
                        if index != u8::MAX {
                            rt = u64::from_le_bytes(timestamps[index as usize]);
                        }
                    }
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out33: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out34: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out35: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out36: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out37: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out38: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out39: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out40: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out41: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out42: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out43: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out44: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out45: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out46: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out47: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out48: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out49: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out50: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out51: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out52: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out53: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out54: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out55: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out56: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out57: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out58: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out59: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out60: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out61: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out62: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p4.out63: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
            ]
        };
        indices[512..576].copy_from_slice(&output);
    }
    {
        let output = {
            let source: &[u8; 64] = indices[512..576].first_chunk::<64>().expect("index64");
            let mut lp: usize = 0;
            let mut le: usize = 32;
            let mut rp: usize = 32;
            let mut re: usize = 64;
            let mut li: u16 = 256;
            let mut ri: u16 = 256;
            let mut lt: u64 = 0;
            let mut rt: u64 = 0;
            // p5: inline initial heads.
            {
                let index = source[lp];
                li = index as u16;
                if index != u8::MAX {
                    lt = u64::from_le_bytes(timestamps[index as usize]);
                }
                let index = source[rp];
                ri = index as u16;
                if index != u8::MAX {
                    rt = u64::from_le_bytes(timestamps[index as usize]);
                }
            }
            [
                {
                    // p5.out0: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out1: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out2: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out3: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out4: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out5: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out6: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out7: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out8: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out9: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out10: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out11: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out12: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out13: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out14: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out15: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out16: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out17: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out18: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out19: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out20: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out21: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out22: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out23: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out24: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out25: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out26: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out27: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out28: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out29: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out30: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out31: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out32: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out33: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out34: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out35: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out36: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out37: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out38: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out39: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out40: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out41: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out42: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out43: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out44: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out45: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out46: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out47: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out48: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out49: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out50: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out51: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out52: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out53: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out54: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out55: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out56: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out57: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out58: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out59: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out60: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out61: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out62: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
                {
                    // p5.out63: fully expanded emit expression.
                    #[cfg(test)]
                    {
                        if li != 256 && ri != 256 {
                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        }
                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    }
                    let take_left = if ri >= 255 {
                        li != 256
                    } else {
                        li < 255 && lt <= rt
                    };
                    if take_left {
                        let out = li as u8;
                        lp += 1;
                        if lp < le {
                            let index = source[lp];
                            li = index as u16;
                            if index != u8::MAX {
                                lt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            li = 256;
                        }
                        out
                    } else {
                        let out = ri as u8;
                        rp += 1;
                        if rp < re {
                            let index = source[rp];
                            ri = index as u16;
                            if index != u8::MAX {
                                rt = u64::from_le_bytes(timestamps[index as usize]);
                            }
                        } else {
                            ri = 256;
                        }
                        out
                    }
                },
            ]
        };
        indices[0..64].copy_from_slice(&output);
    }
}
#[cfg(test)]
static COMMIT_FAULT: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);
#[cfg(test)]
static CLEANUP_FAULT: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);
#[cfg(test)]
static ENVELOPE_CALLS: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
#[cfg(test)]
static SEMANTIC_CALLS: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
fn commit_succeeded() -> bool {
    #[cfg(test)]
    {
        return !COMMIT_FAULT.swap(false, std::sync::atomic::Ordering::Relaxed);
    }
    #[cfg(not(test))]
    {
        true
    }
}
fn semantic(
    b: &mut [u8],
    c: &mut Candidate2048,
    loan: &Loan<'_>,
    p: &Progress,
    steps: &mut StepBudget,
) -> SemanticReply {
    // G128 owns these zero-debit terminal paths. Scratch remains untouched.
    if b.len() != ARENA_BYTES || steps.spent != 0 {
        return poison(0);
    }
    if steps.remaining < SEMANTIC_RECORD {
        return SemanticReply {
            status: 2,
            reason: 1,
            debit: 0,
        };
    }
    steps.remaining -= SEMANTIC_RECORD;
    steps.spent = SEMANTIC_RECORD;
    let w = loan.record.words;
    let f = loan.config;
    if f.slots == 0
        || f.slots > 64
        || f.pins == 0
        || f.pins > 64
        || p.terminal() != 0
        || p.latch >> 8 > f.pins
        || p.q[3] > 10
    {
        return poison(SEMANTIC_RECORD);
    }
    if w[1] == 14 {
        return reject(14);
    }
    // Fixed scratch preflight and complete snapshot staging. No arena mutation
    // occurs until every branch predicate and checked arithmetic has succeeded.
    for i in 0..16 {
        sq(c, i, p.q[i]);
    }
    sq(c, 16, p.first_pin());
    for i in 0..2 {
        sq(c, 17 + i, ld(b, SCALAR.base + EXTRA_CELLS[i] * 8));
    }
    let mut resident_delta = ABSENT;
    let mut pin_delta = ABSENT;
    let mut plan_delta = ABSENT;
    let mut total = 0u64;
    let mut count = 0u64;
    let mut found = ABSENT;
    let mut first_empty = ABSENT;
    let mut first_pin = ABSENT;
    let mut resident_pins = 0u64;
    let mut live_tokens = 0u64;
    let mut release_nonce_matches = 0u64;
    // G2. Unselected typed-row proposal; every arena loan ends at this block.
    {
        let (arena_words, _) = b.as_chunks::<8>();
        let (resident_chunks, _) = arena_words[RESIDENT.base / 8..RESIDENT.base / 8 + 512].as_chunks::<8>();
        let resident_rows: &[[[u8; 8]; 8]; 64] = resident_chunks.first_chunk::<64>().expect("resident64");
        let (pin_chunks, _) = arena_words[PIN.base / 8..PIN.base / 8 + 384].as_chunks::<6>();
        let pin_rows: &[[[u8; 8]; 6]; 64] = pin_chunks.first_chunk::<64>().expect("pin64");
        let (time_bytes, index_bytes) = c.split_at_mut(512);
        let (timestamp_chunks, _) = time_bytes.as_chunks_mut::<8>();
        let timestamp_words: &mut [[u8; 8]; 64] = timestamp_chunks.first_chunk_mut::<64>().expect("timestamp64");
        let [_, record_kind, _, _, _, _, requested_function, _, _, _, _, _, release_nonce, _, _, _] = w;
        let [_, _, _, _, _, _, prior_count, prior_total, prior_pins, next_nonce, _, _, _, _, _, _] = &p.q;
        let configured_slots = f.slots;
        let configured_pins = f.pins;
        let configured_entry = f.entry;
        let resident_limit = configured_slots as usize;
        let pin_limit = configured_pins as usize;
        let mut eligibility = 0u64;
        let mut slot = 0;
        while slot < resident_limit {
            let row = &resident_rows[slot];
            let [occupied_le, function_le, bytes_le, pins_le, last_used_le, _, reserved6_le, reserved7_le] = row;
            let occupied = u64::from_le_bytes(*occupied_le);
            let function = u64::from_le_bytes(*function_le);
            let bytes = u64::from_le_bytes(*bytes_le);
            let pins = u64::from_le_bytes(*pins_le);
            if occupied > 1 || pins > configured_pins
                || u64::from_le_bytes(*reserved6_le) != 0
                || u64::from_le_bytes(*reserved7_le) != 0
            {
                return reject(13);
            }
            if occupied == 1 {
                resident_pins += pins;
                if function >= 80000 || bytes == 0 || bytes > configured_entry {
                    return reject(13);
                }
                let Some(sum) = total.checked_add(bytes) else {
                    return reject(10);
                };
                total = sum;
                count += 1;
                if function == *requested_function {
                    if found != ABSENT {
                        return reject(7);
                    }
                    found = slot as u64;
                }
            } else if function != ABSENT || bytes != 0 || pins != 0 {
                return reject(13);
            } else if first_empty == ABSENT {
                first_empty = slot as u64;
            }
            // Decode/encode is the identity on all eight-byte LE words.
            // Preserve the required timestamp read as one complete byte copy.
            timestamp_words[slot] = *last_used_le;
            if occupied == 1 && pins == 0 { eligibility |= 1u64 << slot; }
            slot += 1;
        }
        while slot < 64 {
            timestamp_words[slot] = 0u64.to_le_bytes();
            slot += 1;
        }
        let mut pin = 0;
        while pin < pin_limit {
            let row = &pin_rows[pin];
            let [entry_le, nonce_le, _, _, _, _] = row;
            let entry = u64::from_le_bytes(*entry_le);
            let nonce = u64::from_le_bytes(*nonce_le);
            if entry == ABSENT {
                if nonce != 0 { return reject(13); }
                if first_pin == ABSENT { first_pin = pin as u64; }
            } else {
                if entry >= configured_slots || nonce == 0 || nonce >= *next_nonce {
                    return reject(13);
                }
                let back_row = &resident_rows[entry as usize];
                let [back_occupied_le, _, _, back_pins_le, _, _, _, _] = back_row;
                if u64::from_le_bytes(*back_occupied_le) != 1
                    || u64::from_le_bytes(*back_pins_le) == 0
                { return reject(13); }
                live_tokens += 1;
                if *record_kind == 12 && nonce == *release_nonce { release_nonce_matches += 1; }
            }
            pin += 1;
        }
        // Retains the unselected seeded proposal's bytes640..648 amendment.
        index_bytes[128..136].copy_from_slice(&eligibility.to_le_bytes());
        if release_nonce_matches > 1 { return reject(11); }
        if resident_pins != *prior_pins || live_tokens != *prior_pins { return reject(13); }
        if count != *prior_count || total != *prior_total || *prior_pins > configured_pins || *next_nonce == 0 {
            return reject(13);
        }
    }
    let body = w[6] as usize;
    if !matches!(w[1], 1 | 13)
        && (body >= 80000
            || u32::from_le_bytes(
                *b[FUNCTION.base + body * 96 + 20..FUNCTION.base + body * 96 + 24]
                    .first_chunk::<4>()
                    .unwrap(),
            ) != 1)
    {
        return reject(6);
    }
    match w[1] {
        1 => {
            sq(c, 16, ABSENT);
            sq(c, 17, ABSENT);
            sq(c, 18, 0);
            sq(c, 10, 0);
            sq(c, 11, 0);
            sq(c, 12, 0);
            sq(c, 13, ABSENT);
            sq(c, 14, ABSENT);
            sq(c, 15, 0);
        }
        2 => {
            if p.q[9] == ABSENT {
                return reject(12);
            }
            if first_pin == ABSENT {
                return reject(11);
            }
            if (w[13] == 0 && found != ABSENT) || (w[13] == 1 && found != w[10]) {
                return reject(7);
            }
            sq(c, 16, first_pin);
            sq(c, 17, found);
        }
        3 | 4 => {
            let cell = (w[6] & 511) as usize;
            let prior = pl(b, cell, 0);
            let outcome = if prior == ABSENT {
                0
            } else if prior == w[6] {
                2
            } else {
                1
            };
            if outcome == 2
                && (pl(b, cell, 1) != w[7] || pl(b, cell, 2) != w[8] || pl(b, cell, 3) != w[9])
            {
                return reject(8);
            }
            if w[1] == 4 {
                if w[13] != outcome || w[14] != (if outcome == 1 { prior } else { ABSENT }) {
                    return reject(8);
                }
                if outcome != 2 {
                    for i in 0..5 {
                        st(
                            c,
                            1648 + i * 8,
                            if i == 0 {
                                w[6]
                            } else if i < 4 {
                                w[6 + i]
                            } else {
                                0
                            },
                        );
                    }
                    plan_delta = cell as u64;
                }
            }
        }
        5 => {
            let cell = (w[6] & 511) as usize;
            if pl(b, cell, 0) != w[6]
                || pl(b, cell, 1) != w[7]
                || pl(b, cell, 2) != w[8]
                || pl(b, cell, 3) != w[9]
            {
                return reject(8);
            }
            if pl(b, cell, 4) != 0 && pl(b, cell, 4) != w[13] {
                return reject(10);
            }
            if w[13] == 0
                || w[13] > f.entry
                || w[14] != f.base
                || w[15] != f.capacity
                || f.base.checked_add(w[13]).is_none_or(|v| v > f.capacity)
            {
                return reject(10);
            }
            c[1648..1688].copy_from_slice(&b[PLAN.base + 40 * cell..PLAN.base + 40 * cell + 40]);
            st(c, 1680, w[13]);
            plan_delta = cell as u64;
            sq(c, 18, w[13]);
            merge(c);
            // G5. Exact prior successful base+request guard proves subtraction.
            let headroom = f.capacity - f.base - w[13];
            let mut remaining = total;
            let mut mask = 0;
            let mut destination = first_empty;
            {
                let (arena_words, _) = b.as_chunks::<8>();
                let resident_word_base = RESIDENT.base / 8;
                let mut i = 0;
                while i < 64 {
                    if remaining <= headroom && destination != ABSENT { break; }
                    let slot_byte = c[512 + i];
                    if slot_byte == u8::MAX { break; }
                    // 255 never reaches this zero extension. No signed value.
                    let slot = slot_byte as u64;
                    let bytes = u64::from_le_bytes(
                        arena_words[resident_word_base + slot as usize * 8 + 2]
                    );
                    remaining -= bytes;
                    mask |= 1 << slot;
                    destination = slot;
                    i += 1;
                }
            }
            let feasible = destination != ABSENT && remaining <= headroom;
            sq(c, 10, mask);
            sq(c, 11, 0);
            sq(c, 12, 0);
            sq(c, 13, ABSENT);
            sq(c, 14, if feasible { destination } else { ABSENT });
            sq(c, 15, u64::from(feasible));
        }
        6..=8 => {
            if p.q[15] != 1 {
                return reject(9);
            }
            let outstanding = p.q[10] & !p.q[12];
            let expected = if outstanding == 0 {
                ABSENT
            } else {
                outstanding.trailing_zeros() as u64
            };
            if w[10] != expected || expected >= f.slots {
                return reject(9);
            }
            let slot = expected as usize;
            if w[1] == 6 {
                if rr(b, slot, 0) != 1 || rr(b, slot, 3) != 0 || rr(b, slot, 2) != w[13] {
                    return reject(9);
                }
                sq(c, 13, expected);
            } else if w[1] == 7 {
                if p.q[13] != expected
                    || rr(b, slot, 0) != 1
                    || rr(b, slot, 3) != 0
                    || rr(b, slot, 2) != w[13]
                {
                    return reject(9);
                }
                c.copy_within(1944..2008, 1536);
                st(c, 1544, ABSENT);
                resident_delta = expected;
                sq(c, 6, count - 1);
                sq(c, 7, total - w[13]);
                sq(c, 11, p.q[11] | (1 << expected));
            } else {
                if p.q[13] != expected || p.q[11] & (1 << expected) == 0 || rr(b, slot, 0) != 0 {
                    return reject(9);
                }
                // Begin's byte count survives Taken in the pending staging cell.
                if w[13] != ld(b, SCALAR.base + 138 * 8) {
                    return reject(9);
                }
                sq(c, 12, p.q[12] | (1 << expected));
                sq(c, 13, ABSENT);
            }
        }
        9 | 10 => {
            if p.q[15] != 1 || p.q[12] != p.q[10] || w[13] != cq(c, 18) {
                return reject(if w[13] != cq(c, 18) { 10 } else { 9 });
            }
        }
        11 => {
            if w[12] != p.q[9] || p.q[9] == ABSENT {
                return reject(12);
            }
            if first_pin != cq(c, 16) || w[11] != first_pin || first_pin >= f.pins {
                return reject(11);
            }
            let slot = if w[13] == 0 { cq(c, 17) } else { p.q[14] };
            if slot >= f.slots || w[10] != slot {
                return reject(7);
            }
            let slot = slot as usize;
            if w[13] == 0 {
                if rr(b, slot, 0) != 1 || rr(b, slot, 1) != w[6] || rr(b, slot, 2) != w[14] {
                    return reject(7);
                }
                c[1536..1600]
                    .copy_from_slice(&b[RESIDENT.base + slot * 64..RESIDENT.base + slot * 64 + 64]);
            } else {
                if p.q[15] != 1 || p.q[10] != p.q[12] || rr(b, slot, 0) != 0 || w[14] != cq(c, 18) {
                    return reject(9);
                }
                // Reserved tail is zero by Candidate construction/cleanup induction.
                c.copy_within(1944..2008, 1536);
                st(c, 1536, 1);
                st(c, 1544, w[6]);
                st(c, 1552, w[14]);
                st(c, 1576, w[3]);
                sq(c, 6, count + 1);
                let Some(sum) = total.checked_add(w[14]) else {
                    return reject(10);
                };
                sq(c, 7, sum);
            }
            let prior_pins = ld(c, 1560);
            let Some(pins) = prior_pins.checked_add(1) else {
                return reject(11);
            };
            if w[15] != pins || pins > f.pins || p.q[8] == f.pins {
                return reject(11);
            }
            st(c, 1560, pins);
            st(c, 1568, w[4]);
            st(c, 1600, slot as u64);
            st(c, 1608, w[12]);
            st(c, 1616, w[3]);
            st(c, 1624, w[3]);
            st(c, 1632, w[4]);
            st(c, 1640, w[5]);
            resident_delta = slot as u64;
            pin_delta = first_pin;
            sq(c, 8, p.q[8] + 1);
            sq(c, 9, p.q[9] + 1);
        }
        12 => {
            let slot = w[10] as usize;
            let pin = w[11] as usize;
            if slot >= f.slots as usize
                || pin >= f.pins as usize
                || pr(b, pin, 0) != w[10]
                || pr(b, pin, 1) != w[12]
            {
                return reject(11);
            }
            if rr(b, slot, 0) != 1
                || rr(b, slot, 1) != w[6]
                || rr(b, slot, 2) != w[13]
                || rr(b, slot, 3) == 0
                || p.q[8] == 0
                || w[15] != rr(b, slot, 3) - 1
            {
                return reject(11);
            }
            c[1536..1600]
                .copy_from_slice(&b[RESIDENT.base + slot * 64..RESIDENT.base + slot * 64 + 64]);
            st(c, 1560, w[15]);
            for i in 0..6 {
                st(c, 1600 + i * 8, if i == 0 { ABSENT } else { 0 });
            }
            resident_delta = w[10];
            pin_delta = w[11];
            sq(c, 8, p.q[8] - 1);
        }
        13 => {}
        _ => return poison(SEMANTIC_RECORD),
    }
    // Mirror only the already audited envelope successor. Semantic reply itself
    // is installed by the caller after cleanup; refusal never installs scratch.
    sq(c, 0, w[0]);
    sq(c, 1, w[4]);
    sq(c, 2, w[5]);
    let stage = match w[1] {
        1 => 1,
        2 => {
            if w[13] == 1 {
                2
            } else {
                3
            }
        }
        3 => 4,
        4 => 5,
        5 | 8 => 6,
        6 => 7,
        7 => 8,
        9 => 9,
        10 => 10,
        _ => 0,
    };
    sq(c, 3, stage);
    sq(c, 4, if stage == 0 { 0 } else { w[3] });
    sq(c, 5, if stage == 0 { ABSENT } else { w[6] });
    // Every destination and fixed width was established by exact arena length,
    // validated rows, constant cell indices and the candidate's array type.
    // No callback, allocation, Result or fallible range follows first mutation.
    if resident_delta != ABSENT {
        let at = RESIDENT.base + resident_delta as usize * 64;
        b[at..at + 64].copy_from_slice(&c[1536..1600]);
        if !commit_succeeded() {
            return SemanticReply {
                status: 3,
                reason: 16,
                debit: SEMANTIC_RECORD,
            };
        }
    }
    if pin_delta != ABSENT {
        let at = PIN.base + pin_delta as usize * 48;
        b[at..at + 48].copy_from_slice(&c[1600..1648]);
    }
    if plan_delta != ABSENT {
        let at = PLAN.base + plan_delta as usize * 40;
        b[at..at + 40].copy_from_slice(&c[1648..1688]);
    }
    b[7729928..7729936].copy_from_slice(&c[1736..1744]);
    b[7729936..7729944].copy_from_slice(&c[1744..1752]);
    b[7729944..7729952].copy_from_slice(&c[1752..1760]);
    b[7729896..7729904].copy_from_slice(&c[1760..1768]);
    b[7730784..7730792].copy_from_slice(&c[1768..1776]);
    b[7730800..7730808].copy_from_slice(&c[1776..1784]);
    b[7730808..7730816].copy_from_slice(&c[1784..1792]);
    b[7730856..7730864].copy_from_slice(&c[1792..1800]);
    b[7730432..7730440].copy_from_slice(&c[1800..1808]);
    b[7730888..7730896].copy_from_slice(&c[1808..1816]);
    b[7730328..7730336].copy_from_slice(&c[1824..1832]);
    b[7730384..7730392].copy_from_slice(&c[1832..1840]);
    if w[1] == 6 {
        st(b, SCALAR.base + 138 * 8, w[13]);
    }
    SemanticReply {
        status: 1,
        reason: 0,
        debit: SEMANTIC_RECORD,
    }
}
// This sole cleanup block follows every loan return. Length/ranges are checked
// before the loan and the exact same exclusive slice survives through here.
// Explicit zero-word stores avoid a second2048-byte temporary source owner.
fn cleanup(b: &[u8], c: &mut Candidate2048) -> bool {
    if b.len() != ARENA_BYTES {
        return false;
    }
    c[0..128].copy_from_slice(&[0u8; 128]);
    c[128..256].copy_from_slice(&[0u8; 128]);
    c[256..384].copy_from_slice(&[0u8; 128]);
    c[384..512].copy_from_slice(&[0u8; 128]);
    c[512..640].copy_from_slice(&[0u8; 128]);
    c[640..768].copy_from_slice(&[0u8; 128]);
    c[768..896].copy_from_slice(&[0u8; 128]);
    c[896..1024].copy_from_slice(&[0u8; 128]);
    c[1024..1152].copy_from_slice(&[0u8; 128]);
    c[1152..1280].copy_from_slice(&[0u8; 128]);
    c[1280..1408].copy_from_slice(&[0u8; 128]);
    c[1408..1536].copy_from_slice(&[0u8; 128]);
    c[1536..1664].copy_from_slice(&[0u8; 128]);
    c[1664..1792].copy_from_slice(&[0u8; 128]);
    c[1792..1920].copy_from_slice(&[0u8; 128]);
    c[1920..2048].copy_from_slice(&[0u8; 128]);
    c[888..896].copy_from_slice(&b[7729816..7729824]);
    c[896..904].copy_from_slice(&b[7729832..7729840]);
    c[904..912].copy_from_slice(&b[7729840..7729848]);
    c[912..920].copy_from_slice(&b[7729848..7729856]);
    c[920..928].copy_from_slice(&b[7729856..7729864]);
    c[928..936].copy_from_slice(&b[7729864..7729872]);
    c[936..944].copy_from_slice(&b[7729872..7729880]);
    c[944..952].copy_from_slice(&b[7730272..7730280]);
    c[952..960].copy_from_slice(&b[7730280..7730288]);
    c[960..968].copy_from_slice(&b[7730288..7730296]);
    c[968..976].copy_from_slice(&b[7731040..7731048]);
    c[976..984].copy_from_slice(&b[7731048..7731056]);
    #[cfg(test)]
    if CLEANUP_FAULT.swap(false, std::sync::atomic::Ordering::Relaxed) {
        c[0] = 0x51;
        return false;
    }
    true
}
impl FixtureCacheStateObservationV1 {
    pub fn observed_records(&self) -> u64 {
        self.extent[0]
    }
    pub fn cache_state_records(&self) -> u64 {
        self.extent[1]
    }
    pub fn stop_record(&self) -> u64 {
        self.extent[2]
    }
    pub fn last_sequence(&self) -> u64 {
        self.extent[3]
    }
    pub fn last_work(&self) -> u64 {
        self.extent[4]
    }
    pub fn last_instructions(&self) -> u64 {
        self.extent[5]
    }
    pub fn active_operation(&self) -> u64 {
        self.extent[6]
    }
    pub fn requested_function(&self) -> u64 {
        self.extent[7]
    }
    pub fn resident_count(&self) -> u64 {
        self.extent[8]
    }
    pub fn resident_bytes(&self) -> u64 {
        self.extent[9]
    }
    pub fn held_pins(&self) -> u64 {
        self.extent[10]
    }
    pub fn next_nonce(&self) -> u64 {
        self.extent[11]
    }
    pub fn active_plan_cell(&self) -> u64 {
        self.extent[12]
    }
    pub fn selected_mask(&self) -> u64 {
        self.extent[13]
    }
    pub fn taken_mask(&self) -> u64 {
        self.extent[14]
    }
    pub fn committed_mask(&self) -> u64 {
        self.extent[15]
    }
    pub fn pending_victim(&self) -> u64 {
        self.extent[16]
    }
    pub fn destination(&self) -> u64 {
        self.extent[17]
    }
    pub fn failure_coordinate(&self) -> u64 {
        self.extent[18]
    }
    pub fn semantic_debit(&self) -> u64 {
        self.extent[19]
    }
    pub fn semantic_setup_paid(&self) -> u64 {
        self.extent[20]
    }
    pub fn semantic_finish_paid(&self) -> u64 {
        self.extent[21]
    }
    pub fn fixture_state_observed(&self) -> u64 {
        self.extent[22]
    }
    pub fn tail_unknown(&self) -> u64 {
        self.extent[23]
    }
    pub fn reserved0(&self) -> u64 {
        self.extent[28]
    }
    pub fn reserved1(&self) -> u64 {
        self.extent[29]
    }
}
fn why(n: u64) -> FixtureCacheStateReasonV1 {
    use FixtureCacheStateReasonV1::*;
    match n {
        0 => Observed,
        1 => Steps,
        2 => FramingUnavailable,
        3 => FramingInvalid,
        4 => EnvelopeRefused,
        5 => EnvelopeUnavailable,
        6 => Identity,
        7 => Resident,
        8 => Plan,
        9 => Victim,
        10 => Bytes,
        11 => Token,
        12 => Nonce,
        13 => Invariant,
        14 => FailureApplicability,
        15 => IncompleteBoundary,
        16 => InternalPoison,
        _ => OutputUnavailable,
    }
}
fn projection(
    p: &Progress,
    paid: &Paid,
    s: &Framing,
    input: &Result<bool, AnalyzerError>,
    env: &FixtureEnvelopeObservationV1,
    f: Option<&Fixture>,
) -> FixtureCacheStateObservationV1 {
    use FixtureCacheStateBoundaryV1 as B;
    let mut z = FixtureCacheStateObservationV1 {
        boundary: B::Unavailable,
        reason: why(5),
        extent: [0; 30],
    };
    z.extent[19] = 512 * paid.setup + 256 * paid.finish + 7680 * paid.records;
    z.extent[20] = paid.setup;
    z.extent[21] = paid.finish;
    // Ordered T01..T09. T00 is exclusively the actual outer Result path.
    if let Err(e) = input {
        z.boundary = if e.code == BUDGET {
            B::AnalysisLimited
        } else {
            B::Unavailable
        };
        z.reason = why(if e.code == BINDING {
            2
        } else if e.code == BUDGET {
            1
        } else {
            3
        });
        return z;
    }
    if matches!(env.reason(), FixtureEnvelopeReasonV1::InternalPoisoned) || p.terminal() == 16 {
        z.boundary = B::InternalPoisoned;
        z.reason = why(16);
        return z;
    }
    if p.latch >> 8 > 64
        || f.is_some_and(|v| p.latch >> 8 > v.pins)
        || p.calls > paid.records
        || (p.calls == 0 && p.terminal() != 0)
        || (p.terminal() != 0 && p.terminal() != 1 && !(6..=14).contains(&p.terminal()))
    {
        z.boundary = B::InternalPoisoned;
        z.reason = why(16);
        return z;
    }
    let child =
        match (env.boundary(), env.reason()) {
            (
                FixtureEnvelopeBoundaryV1::Unavailable,
                FixtureEnvelopeReasonV1::EnvelopeUnavailable
                | FixtureEnvelopeReasonV1::UnavailableState,
            ) => 0,
            (FixtureEnvelopeBoundaryV1::Refused, _) => 1,
            (
                FixtureEnvelopeBoundaryV1::AnalysisLimited,
                FixtureEnvelopeReasonV1::Steps
                | FixtureEnvelopeReasonV1::Shape
                | FixtureEnvelopeReasonV1::Coordinate
                | FixtureEnvelopeReasonV1::TerminalPhase
                | FixtureEnvelopeReasonV1::Phase
                | FixtureEnvelopeReasonV1::ReleaseOpen
                | FixtureEnvelopeReasonV1::TerminalFailure
                | FixtureEnvelopeReasonV1::PinFailure
                | FixtureEnvelopeReasonV1::ForbiddenResume
                | FixtureEnvelopeReasonV1::Acquire
                | FixtureEnvelopeReasonV1::Identity
                | FixtureEnvelopeReasonV1::Stage
                | FixtureEnvelopeReasonV1::PublicationForm
                | FixtureEnvelopeReasonV1::CheckedAccess,
            ) => 1,
            (
                FixtureEnvelopeBoundaryV1::AnalysisLimited,
                FixtureEnvelopeReasonV1::FramingLimited,
            ) if matches!(input, Ok(false)) && s.limited && !s.complete => 2,
            (FixtureEnvelopeBoundaryV1::CapCutUnknownTail, FixtureEnvelopeReasonV1::Observed)
                if matches!(input, Ok(true)) && s.complete && !s.limited && s.flags == 1 =>
            {
                3
            }
            (
                FixtureEnvelopeBoundaryV1::ClosedEnvelopeObserved,
                FixtureEnvelopeReasonV1::Observed,
            ) if matches!(input, Ok(true)) && s.complete && !s.limited && s.flags == 0 => 4,
            _ => 0,
        };
    if child == 0 {
        return z;
    }
    if child == 1 {
        z.boundary = B::Refused;
        z.reason = why(4);
        return z;
    }
    if p.calls == 0 && p.terminal() == 0 {
        return z;
    }
    let Some(f) = f else {
        z.boundary = B::InternalPoisoned;
        z.reason = why(16);
        return z;
    };
    if p.calls > paid.records
        || s.framed > paid.records
        || !shape_q(&p.q, p.calls, p.terminal(), s.framed, f)
        || (p.terminal() == 0 && child == 4 && p.q[3] != 0)
    {
        z.boundary = B::InternalPoisoned;
        z.reason = why(16);
        return z;
    }
    let q = &p.q;
    let stage = q[3];
    let active = stage != 0;
    let planned = (6..=10).contains(&stage);
    let pending = stage == 7 || stage == 8;
    z.boundary = if p.terminal() == 14 {
        B::ApplicabilityUnavailable
    } else if p.terminal() == 1 {
        B::AnalysisLimited
    } else if p.terminal() != 0 {
        B::Refused
    } else if child == 2 {
        B::AnalysisLimited
    } else if child == 3 {
        B::CapCutUnknownTail
    } else {
        B::ClosedFixtureObserved
    };
    z.reason = why(if p.terminal() != 0 {
        p.terminal()
    } else if child == 2 {
        1
    } else {
        0
    });
    z.extent[0] = s.framed;
    z.extent[1] = q[0];
    z.extent[2] = if p.terminal() != 0 {
        q[0] + 1
    } else if child == 2 {
        s.framed + 1
    } else {
        0
    };
    z.extent[3] = q[0];
    z.extent[4] = q[1];
    z.extent[5] = q[2];
    z.extent[6] = if active { q[4] } else { 0 };
    z.extent[7] = if active { q[5] } else { ABSENT };
    z.extent[8] = q[6];
    z.extent[9] = q[7];
    z.extent[10] = q[8];
    z.extent[11] = q[9];
    z.extent[12] = if (3..=10).contains(&stage) {
        q[5] & 511
    } else {
        ABSENT
    };
    z.extent[13] = if planned { q[10] } else { 0 };
    z.extent[14] = if planned { q[11] } else { 0 };
    z.extent[15] = if planned { q[12] } else { 0 };
    z.extent[16] = if pending { q[13] } else { ABSENT };
    z.extent[17] = if planned && q[15] == 1 { q[14] } else { ABSENT };
    z.extent[18] = if p.terminal() == 14 { q[0] + 1 } else { 0 };
    z.extent[22] = 1;
    z.extent[23] = u64::from(p.terminal() != 0 || child != 4);
    z
}
fn cache_walk<T: InputFile>(
    input: &mut T,
    arena: &mut Arena,
    budget: &mut Budget,
    f: &Fixture,
    length: u64,
    s: &mut Framing,
    e: &mut FixtureEnvelopeProgressV1,
    p: &mut Progress,
    paid: &mut Paid,
) -> Result<(), AnalyzerError> {
    let mut reader = Reader::new(length, HEADER_STAGE);
    let mut h = [0; 64];
    reader.words(input, arena, budget, &mut h)?;
    header(arena, &h, *f, budget)?;
    budget.setup(SETUP_ENVELOPE)?;
    e.debit += SETUP_ENVELOPE;
    budget.report(FINISH_ENVELOPE)?;
    e.debit += FINISH_ENVELOPE;
    budget.report(UNDERFUNDED_GUARD)?;
    budget.report(SEMANTIC_GUARD)?;
    if arena.bytes.len() != ARENA_BYTES {
        return Err(error(INTERNAL, ARENA_STAGE, 0, 0));
    }
    // The sole Candidate is constructed only after all guards are reserved.
    let mut candidate: Candidate2048 = [0; 2048];
    for i in 0..12 {
        let at = SCALAR.base + CELLS[i] * 8;
        st(
            &mut arena.bytes,
            at,
            if i == 5 {
                1
            } else if i == 6 {
                f.mask
            } else {
                0
            },
        );
    }
    p.q[5] = ABSENT;
    p.q[9] = 1;
    p.q[13] = ABSENT;
    p.q[14] = ABSENT;
    st(&mut arena.bytes, SCALAR.base + 17 * 8, 1);
    st(&mut arena.bytes, SCALAR.base + 24 * 8, f.slots);
    st(&mut arena.bytes, SCALAR.base + 25 * 8, f.pins);
    st(&mut arena.bytes, SCALAR.base + 26 * 8, f.base);
    st(&mut arena.bytes, SCALAR.base + 27 * 8, f.capacity);
    st(&mut arena.bytes, SCALAR.base + 28 * 8, f.entry);
    reader.stage = RECORD_STAGE;
    for index in 0..s.physical {
        if budget.replay_left < RECORD_PREFLIGHT {
            s.limited = true;
            break;
        }
        budget.replay(CACHE_COMBINED)?;
        e.debit += RECORD_ENVELOPE;
        paid.records += 1;
        let mut w = [0; 16];
        reader.words(input, arena, budget, &mut w)?;
        let offset = 512 + index * 128;
        if !record_fields(arena, &w, *f) {
            return Err(error(SCHEMA, RECORD_STAGE, offset, index + 1));
        }
        if !s.coordinate(&w) {
            return Err(error(COORDINATE, RECORD_STAGE, offset, index + 1));
        }
        if p.terminal() != 16 && leaf_pending(e) {
            let record = FixtureDecodedRecordV1 { words: &w };
            let mut steps = StepBudget {
                remaining: RECORD_ENVELOPE,
                spent: 0,
            };
            #[cfg(test)]
            ENVELOPE_CALLS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            let received =
                observe_fixture_envelope_v1(&mut arena.bytes, &mut candidate, &record, &mut steps);
            e.reply = received;
            e.reply_valid = 1;
            if !reply_debit_valid(&e.reply, &steps) {
                e.reply = poisoned(RECORD_ENVELOPE);
                p.latch_terminal(16);
            }
            if e.reply.words[0] == 3 || e.reply.words[1] == 15 {
                p.latch_terminal(16);
            }
            if p.terminal() == 0 && e.reply.words[0] == 1 && e.reply.words[1] == 0 {
                // Before loan, exact exclusive arena length proves every region
                // and all12restore ranges. No scratch access precedes this check.
                if arena.bytes.len() != ARENA_BYTES {
                    p.latch_terminal(16);
                } else {
                    let loan = Loan {
                        record: &record,
                        config: f,
                    };
                    let mut semantic_steps = StepBudget {
                        remaining: SEMANTIC_RECORD,
                        spent: 0,
                    };
                    #[cfg(test)]
                    SEMANTIC_CALLS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    let received = semantic(
                        &mut arena.bytes,
                        &mut candidate,
                        &loan,
                        p,
                        &mut semantic_steps,
                    );
                    p.calls += 1;
                    // Capture committed fixed snapshot before sole cleanup. The
                    // leaf cannot export a partially staged successor on refusal.
                    if received.status == 1
                        && received.reason == 0
                        && received.debit == SEMANTIC_RECORD
                        && semantic_steps.spent == SEMANTIC_RECORD
                        && semantic_steps.remaining == 0
                    {
                        for i in 0..16 {
                            p.q[i] = cq(&candidate, i);
                        }
                        p.remember_pin(cq(&candidate, 16));
                    } else if received.status == 2
                        && (received.reason == 1 || (6..=14).contains(&received.reason))
                        && ((received.debit == SEMANTIC_RECORD
                            && semantic_steps.spent == SEMANTIC_RECORD
                            && semantic_steps.remaining == 0)
                            || (received.reason == 1
                                && received.debit == 0
                                && semantic_steps.spent == 0
                                && semantic_steps.remaining < SEMANTIC_RECORD))
                    {
                        p.latch_terminal(received.reason);
                    } else {
                        p.latch_terminal(16);
                    }
                    if !cleanup(&arena.bytes, &mut candidate) {
                        p.latch_terminal(16);
                    }
                }
            }
        }
    }
    if s.limited {
        let target = length - 512;
        while reader.consumed < target {
            budget.setup(1)?;
            let available = (reader.used - reader.cursor) as u64;
            let n = available.min(target - reader.consumed);
            reader.cursor += n as usize;
            reader.consumed += n;
            if reader.consumed == target {
                break;
            }
            if reader.cursor != reader.used {
                return Err(error(INTERNAL, RECORD_STAGE, reader.consumed, 0));
            }
            let count = (reader.length - reader.loaded).min(65536) as usize;
            bounded_read(
                input,
                &mut arena.bytes[BLOCK.base..BLOCK.base + count],
                budget,
                RECORD_STAGE,
                reader.loaded,
            )?;
            reader.loaded += count as u64;
            reader.used = count;
            reader.cursor = 0;
        }
    }
    reader.stage = FOOTER_STAGE;
    let mut foot = [0; 64];
    reader.words(input, arena, budget, &mut foot)?;
    footer(&h, &foot, length, s, budget)?;
    eof(input, budget, FOOTER_STAGE, length)?;
    s.complete = !s.limited;
    Ok(())
}
fn cache_inputs<S: InputFile, P: InputFile, C: InputFile>(
    stream: &mut S,
    profile_file: &mut P,
    context: &mut C,
    arena: &mut Arena,
    budget: &mut Budget,
    s: &mut Framing,
    e: &mut FixtureEnvelopeProgressV1,
    p: &mut Progress,
    paid: &mut Paid,
    config: &mut Option<Fixture>,
) -> Result<bool, AnalyzerError> {
    let before_s = initial(stream, budget)?;
    let before_p = initial(profile_file, budget)?;
    let before_c = initial(context, budget)?;
    if before_s.len() < 1024
        || before_s.len() > STREAM_CAP
        || (before_s.len() - 1024) % 128 != 0
        || before_p.len() != PROFILE_BYTES
        || before_c.len() != CONTEXT_BYTES
    {
        return Err(error(INPUT, ADMISSION_STAGE, 0, 0));
    }
    s.physical = (before_s.len() - 1024) / 128;
    let f = fixture_context(context, arena, budget)?;
    profile(profile_file, arena, budget, f)?;
    *config = Some(f);
    cache_walk(stream, arena, budget, &f, before_s.len(), s, e, p, paid)?;
    stable(stream, before_s, budget)?;
    stable(profile_file, before_p, budget)?;
    stable(context, before_c, budget)?;
    Ok(s.complete)
}
macro_rules! cache_body {
    ($input_s:ident,$input_p:ident,$input_c:ident,$output_f:ident,$limit:expr) => {{
        let stream = $input_s;
        let profile_file = $input_p;
        let context = $input_c;
        let output = $output_f;
        let limit = $limit;
        let mut budget = Budget::new(limit)?;
        budget.setup(SETUP_WRAPPER)?;
        budget.report(FINAL_WRAPPER)?;
        // SF then SS must both succeed before *any* new semantic aggregate/progress
        // owner exists. The only eventual Ok is below these two propagating calls.
        budget.report(SEMANTIC_FINISH)?;
        budget.setup(SEMANTIC_SETUP)?;
        let mut paid = Paid {
            setup: 1,
            finish: 1,
            records: 0,
        };
        let output_initial = output_safety(stream, profile_file, context, output, &mut budget)?;
        let mut arena = Arena::new(&mut budget)?;
        let mut s = Framing::new(0);
        let mut e = FixtureEnvelopeProgressV1 {
            reply_valid: 0,
            debit: 0,
            reply: FixtureEnvelopeReplyV1 { words: [0; 16] },
        };
        let mut p = Progress {
            calls: 0,
            latch: 0,
            q: [0; 16],
        };
        let mut config = None;
        let result = cache_inputs(
            stream,
            profile_file,
            context,
            &mut arena,
            &mut budget,
            &mut s,
            &mut e,
            &mut p,
            &mut paid,
            &mut config,
        );
        let mut observation = error(BINDING, CONTEXT_STAGE, 0, 0);
        let mut decision = Decision::Unavailable;
        let mut framed = false;
        if let Err(err) = result {
            observation = err;
            decision = if err.code == BINDING {
                Decision::Unavailable
            } else if err.code == BUDGET {
                Decision::AnalysisLimited
            } else {
                Decision::Invalid
            };
        } else if s.limited {
            observation = error(BUDGET, RECORD_STAGE, 512 + s.framed * 128, s.framed + 1);
            decision = Decision::AnalysisLimited;
        } else {
            framed = result.unwrap_or(false);
        }
        let envelope = finalize(&e, &s, &result, &arena);
        let cache_state = projection(&p, &paid, &s, &result, &envelope, config.as_ref());
        let mut framing = ReplayOutcome {
            decision,
            framed_records: s.framed,
            physical_records: s.physical,
            report_bytes: 0,
            steps_used: 0,
            input_bytes_read: budget.read_bytes,
            input_attempts: budget.io_spent,
            output_attempts: 0,
            observation,
            fixture_framing: u64::from(framed),
        };
        write_report(
            output,
            output_initial,
            &mut arena,
            &mut budget,
            &mut framing,
            s,
        )?;
        if budget.used() > budget.limit {
            return Err(error(BUDGET, OUTPUT_STAGE, 0, 0));
        }
        Ok(FixtureCacheStateOutcomeV1 {
            framing,
            envelope,
            cache_state,
        })
    }};
}
#[cfg(test)]
fn cache_core<S: InputFile, P: InputFile, C: InputFile, O: OutputFile>(
    stream: &mut S,
    profile_file: &mut P,
    context: &mut C,
    output: &mut O,
    limit: u64,
) -> Result<FixtureCacheStateOutcomeV1, AnalyzerError> {
    cache_body!(stream, profile_file, context, output, limit)
}
/// Four distinct, quiescent regular Files at offset0; empty exclusive output.
/// Only parsed synthetic MIXFIX01/MIXPRF01 identity is observed.
pub fn analyze_fixture_cache_state_v1(
    stream: &mut File,
    profile_file: &mut File,
    context: &mut File,
    output: &mut File,
) -> Result<FixtureCacheStateOutcomeV1, AnalyzerError> {
    cache_body!(stream, profile_file, context, output, STEP_LIMIT)
}
#[cfg(test)]
#[path = "../tests/cache_state_tests.rs"]
mod tests;

#[cfg(test)]
#[path = "../scalar_cursor_independent.rs"]
mod scalar_cursor_independent;
