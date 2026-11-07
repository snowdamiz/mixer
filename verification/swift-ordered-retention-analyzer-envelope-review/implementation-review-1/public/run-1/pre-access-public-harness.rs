//! Prepared from the selected interface, before implementation access.
//! Tests are unexecuted until root supplies an exact implementation freeze.
#![forbid(unsafe_code)]
extern crate mixer_fixture_envelope;

use mixer_fixture_envelope::{analyze_fixture, analyze_fixture_envelope_v1, Decision, ReplayOutcome};
use std::fs::{self, File, OpenOptions};
use std::path::{Path, PathBuf};

struct Expected {
    id: &'static str,
    boundary: u64,
    reason: u64,
    coordinate: u64,
    state: Option<u64>,
    phase: Option<u64>,
    mask: Option<u64>,
    framed: bool,
    physical_records: u64,
}

fn roots() -> (PathBuf, PathBuf) {
    let vectors = PathBuf::from(std::env::var_os("MIXER_ENVELOPE_REVIEW_VECTORS").expect("owned vectors path"));
    let output = PathBuf::from(std::env::var_os("MIXER_ENVELOPE_REVIEW_OUTPUT").expect("owned output path"));
    (vectors, output)
}

fn inputs(vectors: &Path, id: &str) -> (File, File, File) {
    (File::open(vectors.join(format!("{id}.stream.bin"))).unwrap(),
     File::open(vectors.join("profile.bin")).unwrap(),
     File::open(vectors.join(format!("{id}.context.bin"))).unwrap())
}

fn empty_output(path: &Path) -> File {
    OpenOptions::new().read(true).write(true).create_new(true).open(path).unwrap()
}

fn word(report: &[u8], index: usize) -> u64 {
    u64::from_le_bytes(report[index * 8..index * 8 + 8].try_into().unwrap())
}

fn report_contract(path: &Path, outcome: &ReplayOutcome, expected_framing: bool) -> Vec<u8> {
    let bytes = fs::read(path).unwrap();
    assert_eq!(bytes.len(), 49152);
    assert_eq!(word(&bytes, 0), u64::from_le_bytes(*b"MIXANL01"));
    assert_eq!(word(&bytes, 1), 1);
    assert_eq!(word(&bytes, 2), 49152);
    assert_eq!(word(&bytes, 3), outcome.decision as u64);
    assert_eq!(word(&bytes, 4), 0, "no semantic accepted records");
    assert_eq!(word(&bytes, 5), 0, "no semantic prefix coordinate");
    assert_eq!(word(&bytes, 9), outcome.steps_used);
    assert_eq!(word(&bytes, 15), u64::from(expected_framing));
    assert_eq!(word(&bytes, 22), u64::MAX, "original failure stage unavailable");
    assert!(bytes[512..].iter().all(|byte| *byte == 0), "all semantic/reserved regions stay zero");
    assert_eq!(outcome.report_bytes, 49152);
    assert!(!outcome.stored_prefix_validated());
    assert!(!outcome.full_replay_accepted());
    bytes
}

fn check_fixture(expected: Expected) {
    let (vectors, output) = roots();
    let owned = output.join(expected.id);
    fs::create_dir(&owned).unwrap();
    let (mut stream, mut profile, mut context) = inputs(&vectors, expected.id);
    let new_path = owned.join("envelope.report.bin");
    let mut new_output = empty_output(&new_path);
    let result = analyze_fixture_envelope_v1(&mut stream, &mut profile, &mut context, &mut new_output).unwrap();
    let framing = result.framing();
    let envelope = result.envelope();
    assert_eq!(framing.fixture_framing_observed(), expected.framed, "{} framing", expected.id);
    assert_eq!(framing.decision, if expected.framed { Decision::Unavailable } else { Decision::Invalid });
    assert_eq!(framing.physical_records, expected.physical_records);
    assert_eq!(envelope.boundary() as u64, expected.boundary, "{} boundary", expected.id);
    assert_eq!(envelope.reason() as u64, expected.reason, "{} reason", expected.id);
    assert_eq!(envelope.observed_records(), expected.coordinate, "{} fixture coordinate", expected.id);
    if let Some(state) = expected.state { assert_eq!(envelope.state(), state, "{} state", expected.id); }
    if let Some(phase) = expected.phase { assert_eq!(envelope.phase(), phase, "{} phase", expected.id); }
    if let Some(mask) = expected.mask { assert_eq!(envelope.mask(), mask, "{} mask", expected.id); }
    assert_eq!(envelope.envelope_debit(), 534 + 8 + 128 * expected.physical_records,
               "{} paid record subdivisions include skipped/refused/suppressed leaf work", expected.id);
    assert!(!envelope.full_replay_accepted());
    assert!(!envelope.stored_prefix_validated());
    if !expected.framed {
        assert_eq!(envelope.last_operation(), 0);
        assert_eq!(envelope.active_operation(), 0);
        assert_eq!(envelope.requested_function(), 0);
        assert_eq!(envelope.pin_failure(), 0);
        assert_eq!(envelope.terminal_failure(), 0);
        assert_eq!(envelope.last_work(), 0);
        assert_eq!(envelope.last_instructions(), 0);
    } else if expected.coordinate > 0 {
        assert_eq!(envelope.last_work(), 101 + 7 * (expected.coordinate - 1));
        assert_eq!(envelope.last_instructions(), 211 + 13 * (expected.coordinate - 1));
    }
    let new_report = report_contract(&new_path, framing, expected.framed);

    // Reopen the same immutable synthetic inputs at offset0 for the old entry.
    // The separate output is fresh. This tests unchanged observable framing,
    // including its intentionally arbitrary-stage acceptance as grammar only.
    let (mut old_stream, mut old_profile, mut old_context) = inputs(&vectors, expected.id);
    let old_path = owned.join("framing.report.bin");
    let mut old_output = empty_output(&old_path);
    let old = analyze_fixture(&mut old_stream, &mut old_profile, &mut old_context, &mut old_output).unwrap();
    assert_eq!(old.decision, framing.decision);
    assert_eq!(old.framed_records, framing.framed_records);
    assert_eq!(old.physical_records, framing.physical_records);
    assert_eq!(old.report_bytes, framing.report_bytes);
    assert_eq!(old.input_bytes_read, framing.input_bytes_read);
    assert_eq!(old.input_attempts, framing.input_attempts);
    assert_eq!(old.output_attempts, framing.output_attempts);
    assert_eq!(old.observation, framing.observation);
    assert_eq!(old.fixture_framing_observed(), framing.fixture_framing_observed());
    let old_report = report_contract(&old_path, &old, expected.framed);
    // The new path truthfully accounts for more steps. Every other report byte
    // retains the accepted framing semantics and serialization.
    assert_eq!(&old_report[..72], &new_report[..72]);
    assert_eq!(&old_report[80..], &new_report[80..]);
    println!("REVIEW_FIXTURE\t{}\t{}\t{}\t{}\t{}", expected.id, expected.boundary,
             expected.reason, expected.coordinate, envelope.envelope_debit());
}

include!("generated_public_cases.rs");
