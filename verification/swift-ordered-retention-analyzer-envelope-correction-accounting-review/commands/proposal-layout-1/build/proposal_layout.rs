use super::*;
use std::mem::size_of;

pub(crate) fn run() {
    let actual = [
        size_of::<Result<(), AnalyzerError>>(), size_of::<Result<bool, AnalyzerError>>(),
        size_of::<Result<u64, AnalyzerError>>(), size_of::<Result<Arena, AnalyzerError>>(),
        size_of::<Result<Budget, AnalyzerError>>(), size_of::<Result<Stamp, AnalyzerError>>(),
        size_of::<Result<Fixture, AnalyzerError>>(), size_of::<FixtureEnvelopeOutcomeV1>(),
        size_of::<Result<FixtureEnvelopeOutcomeV1, AnalyzerError>>(), size_of::<FixtureEnvelopeObservationV1>(),
        size_of::<FixtureEnvelopeProgressV1>(), size_of::<FixtureEnvelopeReplyV1>(),
        size_of::<StepBudget>(), size_of::<CheckedPair>(), size_of::<Candidate2048>(),
        size_of::<&mut Candidate2048>(), size_of::<&[u8]>(), size_of::<&mut [u8]>(),
        size_of::<Option<&[u8]>>(), size_of::<Option<&mut [u8]>>(), size_of::<Option<&[u8; 8]>>(),
        size_of::<Option<u64>>(), size_of::<std::ops::Range<usize>>(), size_of::<std::ops::RangeFrom<usize>>(),
        size_of::<std::ops::RangeInclusive<u64>>(), size_of::<Framing>(), size_of::<Reader>(),
        size_of::<Stamp>(), size_of::<AnalyzerError>(), size_of::<ReplayOutcome>(),
        size_of::<std::fs::Metadata>(), size_of::<io::Result<std::fs::Metadata>>(),
    ];
    assert_eq!(actual, [40, 40, 40, 40, 64, 80, 80, 232, 232, 128, 144, 128, 16, 16, 2048, 8, 16, 16, 16, 16, 8, 16, 16, 8, 24, 80, 48, 72, 32, 104, 144, 152]);
    println!("ACTUAL_COMPLETE_LAYOUTS={actual:?}");
    println!("UNIT_RESULT_BYTES={} PROBE_TYPES=32 COST_DEPENDENT_BEHAVIOR_EXECUTED=0 NUMERIC_SELECTION=0", actual[0]);
}
