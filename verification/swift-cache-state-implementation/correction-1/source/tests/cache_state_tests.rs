use super::*;
use std::fs::{self, OpenOptions};
use std::sync::atomic::{AtomicU64, Ordering};
static ID: AtomicU64 = AtomicU64::new(0);
fn put(b: &mut [u8], i: usize, n: u64) {
    b[i * 8..i * 8 + 8].copy_from_slice(&n.to_le_bytes());
}
fn encode(w: &[u64]) -> Vec<u8> {
    w.iter().flat_map(|v| v.to_le_bytes()).collect()
}
fn body(function: u64) -> (u64, u64, u64) {
    match function {
        1 => (32, 4, 1),
        2 => (48, 5, 0),
        513 => (128, 7, 1),
        3 => (64, 6, 1),
        _ => (0, 0, 0),
    }
}
fn event(k: u64, op: u64, function: u64) -> [u64; 16] {
    let (off, len, ty) = body(function);
    let mut w = [
        0, k, 0, op, 0, 0, function, off, len, ty, ABSENT, ABSENT, 0, 0, 0, 0,
    ];
    match k {
        1 => w[7..10].fill(ABSENT),
        2 => {}
        3 => w[15] = function & 511,
        4 => {
            w[14] = ABSENT;
            w[15] = function & 511;
        }
        5 => {
            w[13] = 3;
            w[15] = 10;
        }
        6..=8 => {
            w[10] = 0;
            w[13] = 3;
        }
        9 | 10 => w[13] = 3,
        11 => {
            w[10..16].copy_from_slice(&[0, 0, 1, 1, 3, 1]);
        }
        12 => {
            w[3] = 0;
            w[8] = ABSENT;
            w[10..16].copy_from_slice(&[0, 0, 1, 3, 0, 0]);
        }
        13 => {
            w[2] = 5;
            w[3] = 0;
            w[6..10].fill(ABSENT);
            w[13] = 5;
        }
        14 => {
            w[6..10].fill(ABSENT);
            w[13..16].copy_from_slice(&[10, 3, 2]);
        }
        _ => panic!(),
    };
    w
}
fn miss(op: u64, function: u64, slot: u64, pin: u64, nonce: u64, bytes: u64) -> Vec<[u64; 16]> {
    let mut v: Vec<_> = [1, 2, 3, 4, 5, 9, 10, 11]
        .into_iter()
        .map(|k| event(k, op, function))
        .collect();
    for w in &mut v {
        if matches!(w[1], 5 | 9 | 10) {
            w[13] = bytes;
        }
        if w[1] == 11 {
            w[10..16].copy_from_slice(&[slot, pin, nonce, 1, bytes, 1]);
        }
    }
    v
}
fn ordered(v: &mut [[u64; 16]]) {
    for (i, w) in v.iter_mut().enumerate() {
        w[0] = i as u64 + 1;
        w[4] = w[0] * 10;
        w[5] = w[0];
    }
}
fn bytes(v: &[[u64; 16]], cap: bool, slots: u64, pins: u64) -> [Vec<u8>; 3] {
    let capn = if cap { v.len() as u64 } else { 2048 };
    let mut context = vec![0; 8192];
    for (i, n) in [
        FIXTURE_MAGIC,
        1,
        8192,
        1,
        capn,
        33,
        1000,
        2,
        slots,
        pins,
        1,
        0,
        10,
        10,
        0,
        0,
    ]
    .into_iter()
    .enumerate()
    {
        put(&mut context, i, n);
    }
    let mut profile = vec![0; PROFILE_BYTES as usize];
    for (i, n) in [
        PROFILE_MAGIC,
        1,
        512,
        32,
        80000,
        1000,
        2,
        slots,
        pins,
        1,
        0,
        10,
        10,
        0,
        0,
        0,
    ]
    .into_iter()
    .enumerate()
    {
        put(&mut profile, i, n);
    }
    for row in 0..80000 {
        put(&mut profile, 64 + row * 4, (u32::MAX as u64) << 32);
        put(&mut profile, 65 + row * 4, ABSENT);
    }
    for function in [1, 2, 3, 513] {
        let (off, len, ty) = body(function);
        put(&mut profile, 64 + function as usize * 4, 1 | (ty << 32));
        put(&mut profile, 65 + function as usize * 4, off);
        put(&mut profile, 66 + function as usize * 4, len);
    }
    let mut h = [0; 64];
    h[..10].copy_from_slice(&[HEADER_MAGIC, 1, 512, 128, 512, capn, 80000, 64, 512, 33]);
    let mut stream = encode(&h);
    let mut operation = 0;
    let mut last = [0; 16];
    for w in v {
        if w[1] == 1 {
            operation = w[3];
        }
        stream.extend(encode(w));
        last = *w;
    }
    let mut ft = [0; 64];
    ft[..16].copy_from_slice(&[
        FOOTER_MAGIC,
        1,
        v.len() as u64,
        v.len() as u64 + u64::from(cap),
        u64::from(cap),
        v.len() as u64,
        last[4],
        last[5],
        operation,
        u64::from(cap),
        last[4],
        last[5],
        0,
        0,
        ABSENT,
        33,
    ]);
    ft[33] = 5;
    ft[34] = 1;
    ft[35] = capn;
    stream.extend(encode(&ft));
    [stream, profile, context]
}
struct Files {
    dir: std::path::PathBuf,
    files: [File; 4],
    case: u64,
}
impl Files {
    fn new(input: [Vec<u8>; 3]) -> Self {
        let case = ID.fetch_add(1, Ordering::Relaxed);
        let dir =
            std::env::temp_dir().join(format!("mixer-cache-state-{}-{}", std::process::id(), case));
        fs::create_dir(&dir).unwrap();
        for (i, b) in input.iter().enumerate() {
            fs::write(dir.join(i.to_string()), b).unwrap();
        }
        let files = std::array::from_fn(|i| {
            OpenOptions::new()
                .read(true)
                .write(true)
                .create_new(i == 3)
                .open(dir.join(i.to_string()))
                .unwrap()
        });
        Self { dir, files, case }
    }
    fn run(&mut self) -> Result<FixtureCacheStateOutcomeV1, AnalyzerError> {
        let before: Vec<_> = self.files[..3]
            .iter()
            .map(|f| file_stamp(f).unwrap())
            .collect();
        let source: Vec<_> = (0..3)
            .map(|i| fs::read(self.dir.join(i.to_string())).unwrap())
            .collect();
        let [a, b, c, d] = &mut self.files;
        let result = analyze_fixture_cache_state_v1(a, b, c, d);
        for i in 0..3 {
            assert_eq!(file_stamp(&self.files[i]).unwrap(), before[i]);
            assert_eq!(fs::read(self.dir.join(i.to_string())).unwrap(), source[i]);
        }
        if let Some(root) = std::env::var_os("MIXER_CACHE_FIXTURE_EVIDENCE") {
            let dest = std::path::PathBuf::from(root).join(format!("case-{:03}", self.case));
            fs::create_dir_all(&dest).unwrap();
            for (i, raw) in source.iter().enumerate() {
                fs::write(dest.join(format!("input-{i}.bin")), raw).unwrap();
            }
            fs::write(dest.join("report.bin"), self.report()).unwrap();
            fs::write(
                dest.join("result.txt"),
                format!("{result:?}\ninput_stamps_before_and_after={before:?}\n"),
            )
            .unwrap();
        }
        result
    }
    fn report(&self) -> Vec<u8> {
        fs::read(self.dir.join("3")).unwrap()
    }
}
impl Drop for Files {
    fn drop(&mut self) {
        fs::remove_dir_all(&self.dir).unwrap();
    }
}
fn full(o: &FixtureCacheStateObservationV1) -> [u64; 32] {
    let mut w = [0; 32];
    w[0] = match o.boundary() {
        FixtureCacheStateBoundaryV1::Unavailable => 0,
        FixtureCacheStateBoundaryV1::ClosedFixtureObserved => 1,
        FixtureCacheStateBoundaryV1::CapCutUnknownTail => 2,
        FixtureCacheStateBoundaryV1::Refused => 3,
        FixtureCacheStateBoundaryV1::AnalysisLimited => 4,
        FixtureCacheStateBoundaryV1::InternalPoisoned => 5,
        FixtureCacheStateBoundaryV1::ApplicabilityUnavailable => 6,
    };
    w[1] = match o.reason() {
        FixtureCacheStateReasonV1::Observed => 0,
        FixtureCacheStateReasonV1::Steps => 1,
        FixtureCacheStateReasonV1::FramingUnavailable => 2,
        FixtureCacheStateReasonV1::FramingInvalid => 3,
        FixtureCacheStateReasonV1::EnvelopeRefused => 4,
        FixtureCacheStateReasonV1::EnvelopeUnavailable => 5,
        FixtureCacheStateReasonV1::Identity => 6,
        FixtureCacheStateReasonV1::Resident => 7,
        FixtureCacheStateReasonV1::Plan => 8,
        FixtureCacheStateReasonV1::Victim => 9,
        FixtureCacheStateReasonV1::Bytes => 10,
        FixtureCacheStateReasonV1::Token => 11,
        FixtureCacheStateReasonV1::Nonce => 12,
        FixtureCacheStateReasonV1::Invariant => 13,
        FixtureCacheStateReasonV1::FailureApplicability => 14,
        FixtureCacheStateReasonV1::IncompleteBoundary => 15,
        FixtureCacheStateReasonV1::InternalPoison => 16,
        FixtureCacheStateReasonV1::OutputUnavailable => 17,
    };
    w[2..].copy_from_slice(&o.extent);
    assert!(
        !o.stored_prefix_validated()
            && !o.full_replay_accepted()
            && !o.semantic_metrics_valid()
            && !o.real_binding_verified()
    );
    assert_eq!(&w[26..], [0; 6]);
    w
}
fn observed(boundary: u64, n: u64, m: u64) -> [u64; 32] {
    let mut w = [0; 32];
    w[0] = boundary;
    w[2] = n;
    w[3] = m;
    w[5] = m;
    w[6] = m * 10;
    w[7] = m;
    w[9] = ABSENT;
    w[13] = 1;
    w[14] = ABSENT;
    w[18] = ABSENT;
    w[19] = ABSENT;
    w[21] = 768 + 7680 * n;
    w[22] = 1;
    w[23] = 1;
    w[24] = 1;
    w[25] = u64::from(boundary != 1);
    w
}
#[test]
fn actual_files_build_hit_release_full32() {
    let mut v = miss(1, 1, 0, 0, 1, 3);
    v.extend([
        event(1, 2, 1),
        event(2, 2, 1),
        event(11, 2, 1),
        event(12, 0, 1),
        event(13, 0, 1),
    ]);
    v[9][10] = 0;
    v[9][13] = 1;
    v[10][10..16].copy_from_slice(&[0, 1, 2, 0, 3, 2]);
    v[11][15] = 1;
    ordered(&mut v);
    let input = bytes(&v, false, 3, 3);
    let saved = input.clone();
    let mut f = Files::new(input);
    let out = f.run().unwrap();
    let mut expected = observed(1, 13, 13);
    expected[10] = 1;
    expected[11] = 3;
    expected[12] = 1;
    expected[13] = 3;
    assert_eq!(full(out.cache_state()), expected);
    assert_eq!(out.envelope().envelope_debit(), 534 + 47 + 425 * 13);
    let report = f.report();
    assert_eq!(report.len(), 49152);
    assert_eq!(&report[..8], b"MIXANL01");
    assert!(report[512..].iter().all(|b| *b == 0));
    for i in 0..3 {
        assert_eq!(fs::read(f.dir.join(i.to_string())).unwrap(), saved[i]);
    }
}
#[test]
fn actual_files_cap_at_each_success_stage() {
    let mut all = miss(1, 1, 0, 0, 1, 3);
    ordered(&mut all);
    for end in 1..=all.len() {
        let v = &all[..end];
        let mut f = Files::new(bytes(v, true, 3, 3));
        let out = f.run().unwrap();
        let w = full(out.cache_state());
        assert_eq!(
            (w[0], w[1], w[2], w[3], w[25]),
            (2, 0, end as u64, end as u64, 1)
        );
        assert_eq!(w[13], if end == 8 { 2 } else { 1 });
        assert_eq!(w[10], u64::from(end == 8));
        assert_eq!(w[12], u64::from(end == 8));
    }
}
#[test]
fn actual_files_cannot_learn_fabricated_hit() {
    let mut v = vec![event(1, 1, 1), event(2, 1, 1)];
    v[1][10] = 0;
    v[1][13] = 1;
    ordered(&mut v);
    let mut f = Files::new(bytes(&v, true, 3, 3));
    let out = f.run().unwrap();
    let mut e = observed(3, 2, 1);
    e[1] = 7;
    e[4] = 2;
    e[8] = 1;
    e[9] = 1;
    assert_eq!(full(out.cache_state()), e);
}
#[test]
fn actual_files_duplicate_release_is_absorbing() {
    let mut v = miss(1, 1, 0, 0, 1, 3);
    v.extend([event(12, 0, 1), event(12, 0, 1), event(13, 0, 1)]);
    ordered(&mut v);
    let mut f = Files::new(bytes(&v, false, 3, 3));
    let o = f.run().unwrap();
    let mut e = observed(3, 11, 9);
    e[1] = 11;
    e[4] = 10;
    e[10] = 1;
    e[11] = 3;
    e[13] = 2;
    assert_eq!(full(o.cache_state()), e);
}
#[test]
fn actual_files_direct_map_collision_and_retained_bytes() {
    let mut v = miss(1, 1, 0, 0, 1, 3);
    v.push(event(12, 0, 1));
    v.extend(miss(2, 513, 1, 0, 2, 4));
    let end = v.len();
    v[end - 5][13] = 1;
    v[end - 5][14] = 1;
    v.push(event(13, 0, 1));
    ordered(&mut v);
    let mut f = Files::new(bytes(&v, false, 3, 3));
    let o = f.run().unwrap();
    let w = full(o.cache_state());
    assert_eq!((w[0], w[1], w[10], w[11], w[12], w[13]), (1, 0, 2, 7, 1, 3));
}
#[test]
fn actual_files_failure_never_creates_or_refunds() {
    for end in 1..8 {
        let mut v = miss(1, 1, 0, 0, 1, 3);
        v.truncate(end);
        v.push(event(14, 1, 79999));
        ordered(&mut v);
        let mut f = Files::new(bytes(&v, true, 3, 3));
        let o = f.run().unwrap();
        let w = full(o.cache_state());
        assert_eq!(
            (w[0], w[1], w[3], w[4], w[20]),
            (6, 14, end as u64, end as u64 + 1, end as u64 + 1)
        );
        assert_eq!((w[10], w[11], w[12], w[13]), (0, 0, 0, 1));
    }
}
#[test]
fn actual_files_late_footer_suppresses_prior_failure() {
    let mut v = vec![event(1, 1, 1), event(14, 1, 1)];
    ordered(&mut v);
    let mut input = bytes(&v, true, 3, 3);
    let at = input[0].len() - 8;
    input[0][at] = 1;
    let mut f = Files::new(input);
    let o = f.run().unwrap();
    let mut expected = [0; 32];
    expected[1] = 3;
    expected[21] = 768 + 7680 * 2;
    expected[22] = 1;
    expected[23] = 1;
    assert_eq!(full(o.cache_state()), expected);
    assert_eq!(o.framing().observation, error(SCHEMA, FOOTER_STAGE, 768, 0));
}
#[test]
fn actual_files_outer_errors_have_no_aggregate() {
    let mut v = miss(1, 1, 0, 0, 1, 3);
    v.push(event(13, 0, 1));
    ordered(&mut v);
    let mut f = Files::new(bytes(&v, false, 3, 3));
    f.files[3] = File::open(f.dir.join("3")).unwrap();
    assert_eq!(f.run().unwrap_err(), error(IO_ERROR, OUTPUT_STAGE, 0, 0));
    let mut f = Files::new(bytes(&v, false, 3, 3));
    f.files[3] = f.files[0].try_clone().unwrap();
    assert_eq!(f.run().unwrap_err(), error(OUTPUT, OUTPUT_STAGE, 0, 0));
}
#[test]
fn fresh_compiler_layouts() {
    use std::mem::{align_of, size_of};
    assert_eq!(size_of::<ReplayOutcome>(), 104);
    assert_eq!(size_of::<FixtureEnvelopeObservationV1>(), 128);
    assert_eq!(size_of::<FixtureEnvelopeOutcomeV1>(), 232);
    assert_eq!(size_of::<FixtureCacheStateObservationV1>(), 256);
    assert_eq!(size_of::<FixtureCacheStateOutcomeV1>(), 488);
    assert!(size_of::<Result<FixtureCacheStateOutcomeV1, AnalyzerError>>() <= 512);
    assert_eq!(align_of::<FixtureCacheStateOutcomeV1>(), 8);
    assert_eq!(size_of::<Progress>(), 144);
    assert_eq!(size_of::<SemanticReply>(), 24);
    assert_eq!(size_of::<Paid>(), 24);
    assert_eq!(size_of::<Loan<'_>>(), 16);
    assert_eq!(size_of::<Option<Fixture>>(), 80);
    assert_eq!(size_of::<Option<u64>>(), 16);
    assert_eq!(size_of::<Result<bool, AnalyzerError>>(), 40);
    println!("helper-layout Loan={} OptionFixture={} OptionU64={} Range={} Array8={} Snapshot={} Candidate={} bool={} ResultBool={} ObsResult={} aligns Loan={} Progress={} Paid={} Reply={}",size_of::<Loan<'_>>(),size_of::<Option<Fixture>>(),size_of::<Option<u64>>(),size_of::<std::ops::Range<usize>>(),size_of::<[u8;8]>(),size_of::<[u64;16]>(),size_of::<Candidate2048>(),size_of::<bool>(),size_of::<Result<bool,AnalyzerError>>(),size_of::<Result<FixtureCacheStateObservationV1,AnalyzerError>>(),align_of::<Loan<'_>>(),align_of::<Progress>(),align_of::<Paid>(),align_of::<SemanticReply>());
    println!("layout Replay=104 envelope=128 old=232 observation=256 aggregate=488 Result={} Progress=144 Reply=24 Paid=24",size_of::<Result<FixtureCacheStateOutcomeV1,AnalyzerError>>());
}
#[test]
fn private_merge_maximum_timestamp_and_all64_slots() {
    let mut c = [0; 2048];
    for i in 0..64 {
        st(
            &mut c,
            i * 8,
            if i % 3 == 0 { ABSENT } else { (63 - i) as u64 },
        );
        st(
            &mut c,
            512 + i * 8,
            if i % 7 == 0 { ABSENT } else { i as u64 },
        );
    }
    let mut independent: Vec<_> = (0..64).filter(|i| i % 7 != 0).collect();
    independent.sort_by_key(|i| (ld(&c, i * 8), *i));
    merge(&mut c);
    for (i, slot) in independent.iter().enumerate() {
        assert_eq!(ld(&c, 512 + i * 8), *slot as u64);
    }
    for i in independent.len()..64 {
        assert_eq!(ld(&c, 512 + i * 8), ABSENT);
    }
}
#[test]
fn private_semantic_guard_neighbors_and_cleanup() {
    let mut b = vec![0; ARENA_BYTES];
    let f = Fixture {
        cap: 1,
        mask: 33,
        extent: 1000,
        types: 2,
        slots: 3,
        pins: 3,
        base: 0,
        capacity: 10,
        entry: 10,
    };
    let p = Progress {
        calls: 0,
        latch: 0,
        q: [0; 16],
    };
    let w = event(14, 0, 1);
    let r = FixtureDecodedRecordV1 { words: &w };
    let loan = Loan {
        record: &r,
        config: &f,
    };
    for amount in [7679, 7680, 7681] {
        let mut c = [91; 2048];
        let before = c;
        let mut steps = StepBudget {
            remaining: amount,
            spent: 0,
        };
        let got = semantic(&mut b, &mut c, &loan, &p, &mut steps);
        assert_eq!(got.reason, if amount < 7680 { 1 } else { 14 });
        assert_eq!(steps.spent, if amount < 7680 { 0 } else { 7680 });
        assert_eq!(c, before);
        cleanup(&b, &mut c);
        assert!(c.iter().all(|v| *v == 0));
    }
    let mut c = [19; 2048];
    let before = c;
    let mut steps = StepBudget {
        remaining: 7680,
        spent: 0,
    };
    let got = semantic(&mut b[..100], &mut c, &loan, &p, &mut steps);
    assert_eq!(got.status, 3);
    assert_eq!(c, before);
}
#[test]
fn private_budget_exact_neighbors() {
    for amount in [8191, 8192, 8193] {
        let mut b = Budget::new(STEP_LIMIT).unwrap();
        b.replay_left = amount;
        if b.replay_left >= 8192 {
            b.replay(CACHE_COMBINED).unwrap();
            assert_eq!(b.replay_left, amount - 8151);
        } else {
            assert_eq!(b.replay_spent, 0);
        }
    }
    for amount in [511, 512, 513] {
        let mut b = Budget::new(STEP_LIMIT).unwrap();
        b.replay_left = amount;
        assert_eq!(b.setup(512).is_ok(), amount >= 512);
    }
    for amount in [255, 256, 257] {
        let mut b = Budget::new(STEP_LIMIT).unwrap();
        b.report_spent = REPORT_RESERVE - amount;
        assert_eq!(b.report(256).is_ok(), amount >= 256);
    }
    for amount in [127, 128, 129] {
        let mut b = Budget::new(STEP_LIMIT).unwrap();
        b.report_spent = REPORT_RESERVE - amount;
        assert_eq!(b.report(128).is_ok(), amount >= 128);
    }
}

fn release(function: u64, slot: u64, pin: u64, nonce: u64, bytes: u64) -> [u64; 16] {
    let mut w = event(12, 0, function);
    w[10..16].copy_from_slice(&[slot, pin, nonce, bytes, 0, 0]);
    w
}
fn evict_miss(
    op: u64,
    function: u64,
    bytes: u64,
    prior: u64,
    victims: &[(u64, u64)],
    destination: u64,
    nonce: u64,
) -> Vec<[u64; 16]> {
    let mut v = miss(op, function, destination, 0, nonce, bytes);
    let mut tail = v.split_off(5);
    if prior != ABSENT {
        v[3][13] = 1;
        v[3][14] = prior;
    }
    for &(slot, size) in victims {
        for kind in [6, 7, 8] {
            let mut w = event(kind, op, function);
            w[10] = slot;
            w[13] = size;
            v.push(w);
        }
    }
    v.append(&mut tail);
    v
}
fn occupied_three() -> Vec<[u64; 16]> {
    let mut v = Vec::new();
    for (slot, function) in [1, 2, 513].into_iter().enumerate() {
        let mut one = miss(
            slot as u64 + 1,
            function,
            slot as u64,
            0,
            slot as u64 + 1,
            3,
        );
        if function == 513 {
            one[3][13] = 1;
            one[3][14] = 1;
        }
        v.extend(one);
        v.push(release(function, slot as u64, 0, slot as u64 + 1, 3));
    }
    v
}
#[test]
fn actual_files_victim_order_differs_from_destination_and_emission() {
    let mut v = occupied_three();
    v.extend(evict_miss(4, 3, 6, ABSENT, &[(0, 3), (1, 3)], 1, 4));
    v.push(release(3, 1, 0, 4, 6));
    let start = v.len();
    v.extend(evict_miss(5, 1, 8, 513, &[(1, 6), (2, 3)], 1, 5));
    v.push(event(13, 0, 1));
    ordered(&mut v);
    let mut f = Files::new(bytes(&v, false, 3, 3));
    let o = f.run().unwrap();
    let w = full(o.cache_state());
    assert_eq!((w[0], w[1], w[10], w[11], w[12], w[13]), (1, 0, 1, 8, 1, 6));
    let end = start + 5;
    let mut f = Files::new(bytes(&v[..end], true, 3, 3));
    let o = f.run().unwrap();
    let w = full(o.cache_state());
    assert_eq!((w[15], w[16], w[17], w[19]), (6, 0, 0, 1));
}
#[test]
fn actual_files_failure_after_take_preserves_removal() {
    let mut v = occupied_three();
    let mut next = evict_miss(4, 3, 6, ABSENT, &[(0, 3), (1, 3)], 1, 4);
    next.truncate(7);
    v.extend(next);
    let m = v.len() as u64;
    v.push(event(14, 4, 2));
    ordered(&mut v);
    let mut f = Files::new(bytes(&v, true, 3, 3));
    let o = f.run().unwrap();
    let w = full(o.cache_state());
    assert_eq!((w[0], w[1], w[3], w[10], w[11], w[12]), (6, 14, m, 2, 6, 0));
    assert_eq!(
        (w[15], w[16], w[17], w[18], w[19], w[20]),
        (3, 1, 0, 0, 1, m + 1)
    );
}
#[test]
fn actual_files_wrong_victim_refuses_atomically() {
    let mut v = occupied_three();
    let start = v.len();
    let mut next = evict_miss(4, 3, 6, ABSENT, &[(0, 3), (1, 3)], 1, 4);
    next.truncate(6);
    next[5][10] = 2;
    v.extend(next);
    ordered(&mut v);
    let mut f = Files::new(bytes(&v, true, 3, 3));
    let o = f.run().unwrap();
    let w = full(o.cache_state());
    assert_eq!(
        (w[0], w[1], w[3], w[10], w[11]),
        (3, 9, start as u64 + 5, 3, 9)
    );
    assert_eq!((w[15], w[16], w[17], w[18], w[19]), (3, 0, 0, ABSENT, 1));
}
#[test]
fn actual_files_obstructed_plan_all_pinned_cannot_build() {
    let mut v = miss(1, 1, 0, 0, 1, 8);
    v.extend(miss(2, 2, 1, 1, 2, 3).into_iter().take(6));
    ordered(&mut v);
    let mut f = Files::new(bytes(&v, true, 3, 3));
    let o = f.run().unwrap();
    let w = full(o.cache_state());
    assert_eq!((w[0], w[1], w[10], w[11], w[12]), (3, 9, 1, 8, 1));
    assert_eq!(w[19], ABSENT);
}
#[test]
fn actual_files_64_live_tokens_and_first_freed_slot() {
    let mut v = miss(1, 1, 0, 0, 1, 3);
    for n in 2..=64 {
        let mut lookup = event(2, n, 1);
        lookup[10] = 0;
        lookup[13] = 1;
        let mut publish = event(11, n, 1);
        publish[10..16].copy_from_slice(&[0, n - 1, n, 0, 3, n]);
        v.extend([event(1, n, 1), lookup, publish]);
    }
    v.push(release(1, 0, 20, 21, 3));
    let last = v.len() - 1;
    v[last][15] = 63;
    let mut lookup = event(2, 65, 1);
    lookup[10] = 0;
    lookup[13] = 1;
    let mut publish = event(11, 65, 1);
    publish[10..16].copy_from_slice(&[0, 20, 65, 0, 3, 64]);
    v.extend([event(1, 65, 1), lookup, publish, event(13, 0, 1)]);
    ordered(&mut v);
    let mut f = Files::new(bytes(&v, false, 64, 64));
    let o = f.run().unwrap();
    let w = full(o.cache_state());
    assert_eq!(
        (w[0], w[1], w[10], w[11], w[12], w[13]),
        (1, 0, 1, 3, 64, 66)
    );
}
fn env_observation(
    boundary: FixtureEnvelopeBoundaryV1,
    reason: FixtureEnvelopeReasonV1,
) -> FixtureEnvelopeObservationV1 {
    let e = FixtureEnvelopeProgressV1 {
        reply_valid: 1,
        debit: 581,
        reply: FixtureEnvelopeReplyV1 {
            words: [1, 0, 1, 0, 5, 33, 0, 0, 0, 0, 0, 10, 1, 425, 0, 0],
        },
    };
    project(&e, boundary, reason, true)
}
#[test]
fn private_terminal_precedence_full32() {
    use FixtureEnvelopeBoundaryV1 as E;
    use FixtureEnvelopeReasonV1 as R;
    let f = Fixture {
        cap: 1,
        mask: 33,
        extent: 1000,
        types: 2,
        slots: 3,
        pins: 3,
        base: 0,
        capacity: 10,
        entry: 10,
    };
    let paid = Paid {
        setup: 1,
        finish: 1,
        records: 1,
    };
    let mut s = Framing::new(1);
    s.framed = 1;
    s.complete = true;
    s.phase = 5;
    s.mask = 33;
    let mut p = Progress {
        calls: 1,
        latch: 0,
        q: [0; 16],
    };
    p.q[0] = 1;
    p.q[1] = 10;
    p.q[2] = 1;
    p.q[5] = ABSENT;
    p.q[9] = 1;
    p.q[13] = ABSENT;
    p.q[14] = ABSENT;
    let closed = env_observation(E::ClosedEnvelopeObserved, R::Observed);
    let cap = env_observation(E::CapCutUnknownTail, R::Observed);
    let refused = env_observation(E::Refused, R::Stage);
    let unavailable = env_observation(E::Unavailable, R::EnvelopeUnavailable);
    let poisoned = env_observation(E::InternalPoisoned, R::InternalPoisoned);
    let expected = observed(1, 1, 1);
    assert_eq!(
        full(&projection(&p, &paid, &s, &Ok(true), &closed, Some(&f))),
        expected
    );
    for (code, boundary, reason) in [(BINDING, 0, 2), (BUDGET, 4, 1), (IO_ERROR, 0, 3)] {
        p.latch_terminal(16);
        let mut z = [0; 32];
        z[0] = boundary;
        z[1] = reason;
        z[21] = 8448;
        z[22] = 1;
        z[23] = 1;
        assert_eq!(
            full(&projection(
                &p,
                &paid,
                &s,
                &Err(error(code, 2, 0, 0)),
                &poisoned,
                Some(&f)
            )),
            z
        );
    }
    p.latch = 0;
    let mut z = [0; 32];
    z[0] = 5;
    z[1] = 16;
    z[21] = 8448;
    z[22] = 1;
    z[23] = 1;
    assert_eq!(
        full(&projection(&p, &paid, &s, &Ok(true), &poisoned, Some(&f))),
        z
    );
    for malformed_header in [4u64, 65] {
        p.latch = malformed_header << 8;
        assert_eq!(
            full(&projection(&p, &paid, &s, &Ok(true), &refused, Some(&f))),
            z
        );
    }
    p.latch = 0;
    z[0] = 0;
    z[1] = 5;
    assert_eq!(
        full(&projection(
            &p,
            &paid,
            &s,
            &Ok(true),
            &unavailable,
            Some(&f)
        )),
        z
    );
    z[0] = 3;
    z[1] = 4;
    assert_eq!(
        full(&projection(&p, &paid, &s, &Ok(true), &refused, Some(&f))),
        z
    );
    p.calls = 0;
    z[0] = 0;
    z[1] = 5;
    assert_eq!(
        full(&projection(&p, &paid, &s, &Ok(true), &closed, Some(&f))),
        z
    );
    p.calls = 1;
    p.q[9] = 0;
    z[0] = 5;
    z[1] = 16;
    assert_eq!(
        full(&projection(&p, &paid, &s, &Ok(true), &closed, Some(&f))),
        z
    );
    p.q[9] = 1;
    for (latch, boundary) in [(6, 3), (14, 6), (1, 4)] {
        p.q[0] = 0;
        p.q[1] = 0;
        p.q[2] = 0;
        p.latch_terminal(latch);
        let mut v = observed(boundary, 1, 0);
        v[1] = latch;
        v[4] = 1;
        v[20] = u64::from(latch == 14);
        assert_eq!(
            full(&projection(&p, &paid, &s, &Ok(true), &closed, Some(&f))),
            v
        );
    }
    p.q[0] = 1;
    p.q[1] = 10;
    p.q[2] = 1;
    p.latch = 0;
    s.flags = 1;
    let mut v = observed(2, 1, 1);
    assert_eq!(
        full(&projection(&p, &paid, &s, &Ok(true), &cap, Some(&f))),
        v
    );
    s.flags = 0;
    s.complete = false;
    s.limited = true;
    let limited = env_observation(E::AnalysisLimited, R::FramingLimited);
    v[0] = 4;
    v[1] = 1;
    v[4] = 2;
    assert_eq!(
        full(&projection(&p, &paid, &s, &Ok(false), &limited, Some(&f))),
        v
    );
}
#[test]
fn private_original_budget_error_and_partial_paid_exclusions() {
    let mut v = miss(1, 1, 0, 0, 1, 3);
    v.push(event(13, 0, 1));
    ordered(&mut v);
    let mut files = Files::new(bytes(&v, false, 3, 3));
    let [a, b, c, d] = &mut files.files;
    assert_eq!(
        cache_core(a, b, c, d, REPORT_RESERVE + IO_RESERVE + 41).unwrap_err(),
        error(BUDGET, RECORD_STAGE, 0, 0)
    );
    let mut files = Files::new(bytes(&v, false, 3, 3));
    let [a, b, c, d] = &mut files.files;
    assert_eq!(
        cache_core(a, b, c, d, REPORT_RESERVE + IO_RESERVE + 42 + 511).unwrap_err(),
        error(BUDGET, RECORD_STAGE, 0, 0)
    );
    println!("SS/SF00,01,10 exclusions are source-return unconstructibility claims, zero runtime-pass credit");
}

#[test]
fn private_actual_merge_exact_worst_case_counts() {
    for mode in 0..4 {
        let mut c = [0; 2048];
        for i in 0..64u64 {
            let key = match mode {
                0 => i.reverse_bits() >> 58,
                1 => 0,
                2 => 63 - i,
                _ => ABSENT,
            };
            st(&mut c, i as usize * 8, key);
            st(&mut c, 512 + i as usize * 8, i);
        }
        SORT_COMPARISONS.store(0, Ordering::Relaxed);
        SORT_MOVES.store(0, Ordering::Relaxed);
        merge(&mut c);
        let comparisons = SORT_COMPARISONS.load(Ordering::Relaxed);
        let moves = SORT_MOVES.load(Ordering::Relaxed);
        assert!(comparisons <= 321);
        assert_eq!(moves, 384);
        if mode == 0 {
            assert_eq!(comparisons, 321);
        }
        println!("actual_merge mode={mode} comparisons={comparisons} moves={moves}");
    }
}
#[test]
fn actual_files_report_schema_and_old_paths_remain_exact() {
    let mut v = miss(1, 1, 0, 0, 1, 3);
    v.push(event(13, 0, 1));
    ordered(&mut v);
    let input = bytes(&v, false, 3, 3);
    let mut framing_files = Files::new(input.clone());
    let [a, b, c, d] = &mut framing_files.files;
    let original = analyze_fixture(a, b, c, d).unwrap();
    let mut envelope_files = Files::new(input.clone());
    let [a, b, c, d] = &mut envelope_files.files;
    let old = analyze_fixture_envelope_v1(a, b, c, d).unwrap();
    let mut new_files = Files::new(input);
    let new = new_files.run().unwrap();
    assert_eq!(new.framing().framed_records, original.framed_records);
    assert_eq!(
        format!("{:?}", new.envelope()),
        format!("{:?}", old.envelope())
    );
    let mut first = framing_files.report();
    let mut second = envelope_files.report();
    let mut third = new_files.report();
    for b in [&mut first, &mut second, &mut third] {
        b[72..80].fill(0);
    }
    assert_eq!(first, second);
    assert_eq!(second, third);
    assert!(
        !new.stored_prefix_validated()
            && !new.full_replay_accepted()
            && !new.semantic_metrics_valid()
            && !new.real_binding_verified()
    );
}

#[test]
fn private_injected_partial_commit_or_cleanup_disables_both_leaves() {
    for mode in 0..2 {
        let mut v = miss(1, 1, 0, 0, 1, 3);
        let mut lookup = event(2, 2, 1);
        lookup[10] = 0;
        lookup[13] = 1;
        let mut publish = event(11, 2, 1);
        publish[10..16].copy_from_slice(&[0, 1, 2, 0, 3, 2]);
        v.extend([event(1, 2, 1), lookup, publish, event(13, 0, 1)]);
        ordered(&mut v);
        ENVELOPE_CALLS.store(0, Ordering::Relaxed);
        SEMANTIC_CALLS.store(0, Ordering::Relaxed);
        if mode == 0 {
            COMMIT_FAULT.store(true, Ordering::Relaxed);
        } else {
            CLEANUP_FAULT.store(true, Ordering::Relaxed);
        }
        let mut f = Files::new(bytes(&v, false, 3, 3));
        let o = f.run().unwrap();
        let mut z = [0; 32];
        z[0] = 5;
        z[1] = 16;
        z[21] = 768 + 7680 * 12;
        z[22] = 1;
        z[23] = 1;
        assert_eq!(full(o.cache_state()), z);
        let expected = if mode == 0 { 8 } else { 1 };
        assert_eq!(ENVELOPE_CALLS.load(Ordering::Relaxed), expected);
        assert_eq!(SEMANTIC_CALLS.load(Ordering::Relaxed), expected);
    }
}

#[path = "guard_correction_tests.rs"]
mod guard_correction;
