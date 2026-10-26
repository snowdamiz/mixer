//! Independent caller protocol. Candidate source is admitted separately.
//! No raw-record/state injection, public serializer, casts of API enums, or unsafe.
#![forbid(unsafe_code)]
extern crate mixer_fixture_cache_state as api;

use std::fs::{File, OpenOptions};
use std::io::Seek;
use std::os::unix::fs::MetadataExt;

fn boundary(v: &api::FixtureCacheStateBoundaryV1) -> u64 {
    use api::FixtureCacheStateBoundaryV1 as B;
    match v {
        B::Unavailable => 0, B::ClosedFixtureObserved => 1,
        B::CapCutUnknownTail => 2, B::Refused => 3,
        B::AnalysisLimited => 4, B::InternalPoisoned => 5,
        B::ApplicabilityUnavailable => 6,
    }
}
fn reason(v: &api::FixtureCacheStateReasonV1) -> u64 {
    use api::FixtureCacheStateReasonV1 as R;
    match v {
        R::Observed => 0, R::Steps => 1, R::FramingUnavailable => 2,
        R::FramingInvalid => 3, R::EnvelopeRefused => 4,
        R::EnvelopeUnavailable => 5, R::Identity => 6, R::Resident => 7,
        R::Plan => 8, R::Victim => 9, R::Bytes => 10, R::Token => 11,
        R::Nonce => 12, R::Invariant => 13, R::FailureApplicability => 14,
        R::IncompleteBoundary => 15, R::InternalPoison => 16,
        R::OutputUnavailable => 17,
    }
}
fn envelope_boundary(v: &api::FixtureEnvelopeBoundaryV1) -> u64 {
    use api::FixtureEnvelopeBoundaryV1 as B;
    match v {
        B::Unavailable => 0, B::ClosedEnvelopeObserved => 1,
        B::CapCutUnknownTail => 2, B::Refused => 3,
        B::AnalysisLimited => 4, B::InternalPoisoned => 5,
    }
}
fn envelope_reason(v: &api::FixtureEnvelopeReasonV1) -> u64 {
    use api::FixtureEnvelopeReasonV1 as R;
    match v {
        R::Observed => 0, R::Steps => 1, R::Shape => 2, R::Coordinate => 3,
        R::TerminalPhase => 4, R::Phase => 5, R::ReleaseOpen => 6,
        R::TerminalFailure => 7, R::PinFailure => 8, R::ForbiddenResume => 9,
        R::Acquire => 10, R::Identity => 11, R::Stage => 12,
        R::PublicationForm => 13, R::CheckedAccess => 14,
        R::InternalPoisoned => 15, R::FramingUnavailable => 16,
        R::FramingInvalid => 17, R::FramingLimited => 18,
        R::EnvelopeUnavailable => 19, R::UnavailableState => 20,
        R::IncompleteBoundary => 21,
    }
}
fn decision(v: &api::Decision) -> u64 {
    match v { api::Decision::Invalid => 3, api::Decision::AnalysisLimited => 4,
        api::Decision::Unavailable => 5 }
}
fn error(v: &api::AnalyzerError) -> [u64; 5] {
    [u64::from(v.code), u64::from(v.stage), v.offset, v.record, v.reserved]
}
fn cache_words(v: &api::FixtureCacheStateObservationV1) -> [u64; 32] {
    [boundary(v.boundary()), reason(v.reason()), v.observed_records(),
        v.cache_state_records(), v.stop_record(), v.last_sequence(),
        v.last_work(), v.last_instructions(), v.active_operation(),
        v.requested_function(), v.resident_count(), v.resident_bytes(),
        v.held_pins(), v.next_nonce(), v.active_plan_cell(), v.selected_mask(),
        v.taken_mask(), v.committed_mask(), v.pending_victim(), v.destination(),
        v.failure_coordinate(), v.semantic_debit(), v.semantic_setup_paid(),
        v.semantic_finish_paid(), v.fixture_state_observed(), v.tail_unknown(),
        u64::from(v.stored_prefix_validated()), u64::from(v.full_replay_accepted()),
        u64::from(v.semantic_metrics_valid()), u64::from(v.real_binding_verified()),
        v.reserved0(), v.reserved1()]
}
fn framing_words(v: &api::ReplayOutcome) -> [u64; 16] {
    [decision(&v.decision), v.framed_records, v.physical_records, v.report_bytes,
        v.steps_used, v.input_bytes_read, v.input_attempts, v.output_attempts,
        u64::from(v.observation.code), u64::from(v.observation.stage),
        v.observation.offset, v.observation.record, v.observation.reserved,
        u64::from(v.fixture_framing_observed()),
        u64::from(v.stored_prefix_validated()), u64::from(v.full_replay_accepted())]
}
fn envelope_words(v: &api::FixtureEnvelopeObservationV1) -> [u64; 16] {
    [envelope_boundary(v.boundary()), envelope_reason(v.reason()),
        v.observed_records(), v.state(), v.phase(), v.mask(), v.last_operation(),
        v.active_operation(), v.requested_function(), v.pin_failure(),
        v.terminal_failure(), v.last_work(), v.last_instructions(),
        v.envelope_debit(), u64::from(v.full_replay_accepted()),
        u64::from(v.stored_prefix_validated())]
}
fn stamp(v: &File) -> std::io::Result<[u64; 8]> {
    let m = v.metadata()?;
    if !m.is_file() { return Err(std::io::ErrorKind::InvalidInput.into()); }
    Ok([m.dev(), m.ino(), u64::from(m.mode()), m.len(), m.mtime() as u64,
        m.mtime_nsec() as u64, m.ctime() as u64, m.ctime_nsec() as u64])
}
fn optional<const N: usize>(v: Option<[u64; N]>) -> String {
    match v { Some(values) => format!("{values:?}"), None => "null".to_owned() }
}
fn driver() -> Result<(), &'static str> {
    let args: Vec<_> = std::env::args_os().collect();
    if args.len() != 5 { return Err("driver expects stream profile context output paths"); }
    let mut stream = File::open(&args[1]).map_err(|_| "driver stream open")?;
    let mut profile = File::open(&args[2]).map_err(|_| "driver profile open")?;
    let mut context = File::open(&args[3]).map_err(|_| "driver context open")?;
    let before = [stamp(&stream).map_err(|_| "driver stream regular File")?,
        stamp(&profile).map_err(|_| "driver profile regular File")?,
        stamp(&context).map_err(|_| "driver context regular File")?];
    for i in 0..3 {
        if before[i][1] == 0 { return Err("driver unavailable inode"); }
        for j in i + 1..3 {
            if before[i][..2] == before[j][..2] { return Err("driver input alias"); }
        }
    }
    if stream.stream_position().ok() != Some(0) || profile.stream_position().ok() != Some(0)
        || context.stream_position().ok() != Some(0) { return Err("driver input offset"); }
    let mut output = OpenOptions::new().read(true).write(true).create_new(true)
        .open(&args[4]).map_err(|_| "driver exclusive output create")?;
    let out_before = stamp(&output).map_err(|_| "driver output regular File")?;
    if out_before[3] != 0 || output.stream_position().ok() != Some(0) {
        return Err("driver output not empty at offset zero");
    }
    if before.iter().any(|s| s[..2] == out_before[..2]) { return Err("driver output alias"); }

    // The sole API invocation receives ordinary safe borrows. The harness
    // owns/quiesces these files; no raw descriptor, record or state is supplied.
    let result = api::analyze_fixture_cache_state_v1(
        &mut stream, &mut profile, &mut context, &mut output);
    // Post-call diagnostics never replace or normalize the actual API Result.
    let after = [optional(stamp(&stream).ok()), optional(stamp(&profile).ok()),
        optional(stamp(&context).ok())];
    let positions = [stream.stream_position().ok(), profile.stream_position().ok(),
        context.stream_position().ok()];
    let positions = positions.map(|v| v.map_or("null".to_owned(), |n| n.to_string()));
    let output_after = optional(stamp(&output).ok());
    let output_position = output.stream_position().ok().map_or("null".to_owned(), |n| n.to_string());
    let layouts = [std::mem::size_of::<api::ReplayOutcome>(),
        std::mem::size_of::<api::FixtureEnvelopeObservationV1>(),
        std::mem::size_of::<api::FixtureEnvelopeOutcomeV1>(),
        std::mem::size_of::<api::FixtureCacheStateObservationV1>(),
        std::mem::size_of::<api::FixtureCacheStateOutcomeV1>(),
        std::mem::size_of::<Result<api::FixtureCacheStateOutcomeV1, api::AnalyzerError>>()];
    match result {
        Ok(value) => {
            let authority = [u64::from(value.stored_prefix_validated()),
                u64::from(value.full_replay_accepted()),
                u64::from(value.semantic_metrics_valid()),
                u64::from(value.real_binding_verified())];
            println!("{{\"protocol\":1,\"api_result\":\"Ok\",\"cache_state_words\":{:?},\"framing_words\":{:?},\"envelope_words\":{:?},\"aggregate_authority\":{:?},\"envelope_metrics\":{},\"error\":null,\"input_before\":{:?},\"input_after\":[{},{},{}],\"input_positions_after\":[{},{},{}],\"output_after\":{},\"output_position\":{},\"layouts\":{:?}}}",
                cache_words(value.cache_state()), framing_words(value.framing()),
                envelope_words(value.envelope()), authority,
                u64::from(value.envelope().semantic_metrics_valid()), before,
                after[0], after[1], after[2], positions[0], positions[1], positions[2],
                output_after, output_position, layouts);
        }
        Err(value) => {
            println!("{{\"protocol\":1,\"api_result\":\"Err\",\"cache_state_words\":null,\"framing_words\":null,\"envelope_words\":null,\"aggregate_authority\":null,\"envelope_metrics\":null,\"error\":{:?},\"input_before\":{:?},\"input_after\":[{},{},{}],\"input_positions_after\":[{},{},{}],\"output_after\":{},\"output_position\":{},\"layouts\":{:?}}}",
                error(&value), before, after[0], after[1], after[2],
                positions[0], positions[1], positions[2], output_after, output_position, layouts);
        }
    }
    Ok(())
}
fn main() {
    if let Err(message) = driver() {
        eprintln!("{message}");
        std::process::exit(64);
    }
}
