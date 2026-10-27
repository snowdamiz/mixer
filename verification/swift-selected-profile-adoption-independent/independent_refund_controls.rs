// Independent test-only ticket corruption. This is a deliberately unreachable
// private fault state, not claimed as a public authority or genuine OS fault.
#[cfg(test)]
pub(super) fn independent_refund_faults(mut control: RuntimeControl, mut adopted: AdoptedProof, field: &str) {
    let source=adopted.source.bytes;
    let metadata=adopted.metadata.bytes;
    assert!(source>0 && metadata>0);
    let source_fault=matches!(field,"source"|"both");
    let metadata_fault=matches!(field,"metadata"|"both");
    assert!(source_fault||metadata_fault);
    if source_fault {adopted.source.owner=0;}
    if metadata_fault {adopted.metadata.owner=0;}
    let (result,stats)=super::allocation_tests::measure(||control.drop_proof(adopted));
    assert_eq!(stats.allocations,0);assert_eq!(stats.reallocations,0);
    assert!(stats.deallocations>0 && stats.freed_bytes>=source);
    let failure=result.err().expect("synthetic owner corruption must fail closed");
    assert_eq!(failure.kind,SwiftRunFailureKind::Invariant);
    assert_eq!(failure.code,"swift_run_release_owner");
    assert_eq!(control.first_failure,Some(failure));
    let current=control.usage(None);
    // When source refund fails, successful metadata refund must still execute.
    assert_eq!(current.reservations.retained_source.current,if source_fault {source}else{0});
    assert_eq!(current.reservations.retained_metadata.current,if metadata_fault {metadata}else{0});
    assert_eq!(current.cleanup_invariant,Some(SwiftCleanupInvariant::ReservationOwner));
    assert_eq!(failure.at_failure.reservations.retained_source.current,if source_fault {source}else{0});
    assert_eq!(failure.at_failure.reservations.retained_metadata.current,metadata);
    let after=control.finish_owned_cleanup(None);
    let quarantined=usize::from(source_fault)*source+usize::from(metadata_fault)*metadata;
    assert_eq!(after.reservations.combined.current,quarantined);
    assert_eq!(after.reservations.live_tickets,usize::from(source_fault)+usize::from(metadata_fault));
    assert_eq!(after.cleanup_invariant,Some(SwiftCleanupInvariant::ReservationOwner));
    println!("INDEPENDENT_SYNTHETIC_REFUND\t{field}\tquarantined={quarantined}\tfreed={}\tfirst_failure_preserved",stats.freed_bytes);
}
