//! Producer-authored private byte-transfer controls, never public reachability.
use super::*;
#[test]
fn private_literal_restores_preserve_every_byte_and_clear_the_remaining_candidate() {
    let mut arena = vec![0x83; ARENA_BYTES];
    let cells = [7usize, 9, 10, 11, 12, 13, 14, 64, 65, 66, 160, 161];
    for (i, cell) in cells.into_iter().enumerate() {
        let value = 0x0102_0304_0506_0708u64.wrapping_mul(i as u64 + 1);
        let at = SCALAR.base + cell * 8;
        arena[at..at + 8].copy_from_slice(&value.to_le_bytes());
    }
    let before = arena.clone();
    for fill in [0u8, 0x51, 0xff] {
        let mut candidate = [fill; 2048];
        assert!(cleanup(&arena, &mut candidate));
        for at in 0..2048 {
            let expected = if (888..984).contains(&at) {
                let i = (at - 888) / 8;
                arena[SCALAR.base + cells[i] * 8 + (at - 888) % 8]
            } else {
                0
            };
            assert_eq!(candidate[at], expected, "candidate byte {at}");
        }
        assert_eq!(arena, before);
    }
    println!("LITERAL_RESTORE_PRIVATE_BYTES=6144 PUBLIC_REACHABILITY_CREDIT=0");
}
#[test]
fn private_phase_commits_exact_twelve_scalar_cells_in_order_without_other_mutation() {
    let mut arena = vec![0u8; ARENA_BYTES];
    arena[RESIDENT.base + 8..RESIDENT.base + 16].copy_from_slice(&ABSENT.to_le_bytes());
    arena[PIN.base..PIN.base + 8].copy_from_slice(&ABSENT.to_le_bytes());
    let prior = [
        0, 0, 0, 0, 0, ABSENT, 0, 0, 0, 1, 0x8123, 0x4567, 0x89ab, ABSENT, 0xdead, 0xbabe,
    ];
    let progress = Progress {
        calls: 0,
        latch: 0,
        q: prior,
    };
    let fixture = Fixture {
        cap: 1,
        mask: 33,
        extent: 1000,
        types: 2,
        slots: 1,
        pins: 1,
        base: 0,
        capacity: 10,
        entry: 10,
    };
    let mut record = event(13, 0, 0);
    record[0] = 1;
    record[4] = 10;
    record[5] = 1;
    for (cell, value) in [
        (71usize, 0x1234_5678_90ab_cdefu64),
        (78, 0xfedc_ba09_8765_4321),
    ] {
        arena[SCALAR.base + cell * 8..SCALAR.base + cell * 8 + 8]
            .copy_from_slice(&value.to_le_bytes());
    }
    let before = arena.clone();
    let mut candidate = [0u8; 2048];
    let loan = Loan {
        record: &FixtureDecodedRecordV1 { words: &record },
        config: &fixture,
    };
    let mut steps = StepBudget {
        remaining: 7680,
        spent: 0,
    };
    let reply = semantic(&mut arena, &mut candidate, &loan, &progress, &mut steps);
    assert_eq!((reply.status, reply.reason, reply.debit), (1, 0, 7680));
    assert_eq!((steps.remaining, steps.spent), (0, 7680));
    let cells = [21usize, 22, 23, 17, 128, 130, 131, 137, 84, 141, 71, 78];
    let values = [
        0,
        0,
        0,
        1,
        0x8123,
        0x4567,
        0x89ab,
        ABSENT,
        0xdead,
        0xbabe,
        0x1234_5678_90ab_cdef,
        0xfedc_ba09_8765_4321,
    ];
    let mut expected = before;
    for (cell, value) in cells.into_iter().zip(values) {
        expected[SCALAR.base + cell * 8..SCALAR.base + cell * 8 + 8]
            .copy_from_slice(&value.to_le_bytes());
    }
    assert_eq!(arena, expected);
    for (cell, value) in cells.into_iter().zip(values) {
        let at = SCALAR.base + cell * 8;
        assert_eq!(&arena[at..at + 8], &value.to_le_bytes());
    }
    assert!(cleanup(&arena, &mut candidate));
    println!(
        "LITERAL_COMMIT_PRIVATE_CELLS=12 FULL_ARENA_BYTES={} PUBLIC_REACHABILITY_CREDIT=0",
        ARENA_BYTES
    );
}
#[test]
fn complete_helper_option_iterator_and_public_result_layouts_are_recorded() {
    use std::mem::{align_of, size_of};
    macro_rules! record {
        ($t:ty) => {
            println!(
                "ACCOUNTING_LAYOUT {} size={} align={}",
                stringify!($t),
                size_of::<$t>(),
                align_of::<$t>()
            );
            assert!(size_of::<$t>() <= 512);
        };
    }
    record!(Progress);
    record!(Paid);
    record!(Loan<'static>);
    record!(StepBudget);
    record!(SemanticReply);
    record!(Fixture);
    record!(Option<Fixture>);
    record!(Result<Fixture,AnalyzerError>);
    record!(Option<u64>);
    record!(Option<usize>);
    record!(Result<bool,AnalyzerError>);
    record!([u8; 8]);
    record!([u64; 16]);
    record!(std::ops::Range<usize>);
    record!(Option<std::ops::Range<usize>>);
    record!(&[u8]);
    record!(&mut [u8]);
    record!(Option<&[u8; 8]>);
    record!(&[u8; 8]);
    record!(FixtureCacheStateObservationV1);
    record!(FixtureCacheStateOutcomeV1);
    record!(Result<FixtureCacheStateOutcomeV1,AnalyzerError>);
    record!(AnalyzerError);
    assert_eq!(size_of::<FixtureCacheStateOutcomeV1>(), 488);
    assert_eq!(
        size_of::<Result<FixtureCacheStateOutcomeV1, AnalyzerError>>(),
        488
    );
    assert_eq!(size_of::<Candidate2048>(), 2048);
}
