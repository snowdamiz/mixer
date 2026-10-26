//! Real small-module row provenance, synthetic configuration and binding only.
extern crate mixer_cache_fixture as fixture;
use std::fs::{File, OpenOptions};
use std::io::{Read, Seek, SeekFrom};
fn main() {
    let a: Vec<String> = std::env::args().collect();
    assert_eq!(a.len(), 8);
    let mut stream = File::open(&a[1]).unwrap();
    let mut profile = File::open(&a[2]).unwrap();
    let mut context = File::open(&a[3]).unwrap();
    let mut output = OpenOptions::new()
        .read(true)
        .write(true)
        .create_new(true)
        .open(&a[4])
        .unwrap();
    let outcome = fixture::analyze_fixture_cache_state_v1(
        &mut stream,
        &mut profile,
        &mut context,
        &mut output,
    )
    .unwrap();
    assert_eq!(format!("{:?}", outcome.cache_state().boundary()), a[5]);
    assert_eq!(format!("{:?}", outcome.cache_state().reason()), a[6]);
    assert!(!outcome.real_binding_verified());
    assert!(!outcome.stored_prefix_validated());
    assert!(!outcome.full_replay_accepted());
    assert!(!outcome.semantic_metrics_valid());
    let state = outcome.cache_state();
    assert!(!state.real_binding_verified());
    assert!(!state.stored_prefix_validated());
    assert!(!state.full_replay_accepted());
    assert!(!state.semantic_metrics_valid());
    assert!(!outcome.framing().stored_prefix_validated());
    assert!(!outcome.framing().full_replay_accepted());
    assert!(!outcome.envelope().stored_prefix_validated());
    assert!(!outcome.envelope().full_replay_accepted());
    assert!(!outcome.envelope().semantic_metrics_valid());
    assert_eq!(outcome.framing().report_bytes, 49152);
    output.seek(SeekFrom::Start(0)).unwrap();
    let mut report = Vec::new();
    output.read_to_end(&mut report).unwrap();
    assert_eq!(report.len(), 49152);
    assert!(report[512..].iter().all(|b| *b == 0));
    assert_eq!(&report[32..48], &[0u8; 16]);
    println!("case={} context=synthetic-MIXFIX01 profile-header=synthetic-MIXPRF01 rows=actual-validated-owner authority=false report_bytes={} outcome={:?}",a[7],report.len(),outcome);
}
