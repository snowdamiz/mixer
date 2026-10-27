// Data/signature proposal only; deliberately not compiled or integrated.
// Names resolve only inside a future selected actual private cache boundary.
// No size/alignment or original runtime reservation is inferred from repr(C).

#[repr(C)]
struct SnapshotExportObservationV1 {
    output_bytes: u64,
    output_attempts: u64,
    source_extent: u64,
    defined_functions: u64,
    type_count: u64,
    owner_ordinal: u64,
    reserved: [u64; 2],
}

#[repr(C)]
struct SnapshotExportErrorV1 {
    code: u32,
    stage: u32,
    offset: u64,
    output_bytes: u64,
    output_attempts: u64,
}

#[repr(u32)]
enum SnapshotEmissionStateV1 {
    NotAttempted = 1,
    Attempted(Result<SnapshotExportObservationV1, SnapshotExportErrorV1>) = 2,
}

#[must_use = "Preserve original result/proof/cache owners and complete original owning-control cleanup"]
struct InitialProfileBundleOutcomeV1 {
    original: InitialProfileConstructionOutcomeV1,
    snapshot: SnapshotEmissionStateV1,
}

// Selected provenance is NOT externally constructible. The real producer must
// retain actual input-load/source equality and original validation budget, plus
// independently admitted build/session handles. This scalar view is only the
// canonical-record payload; it cannot itself grant selection or owner authority.
#[repr(C)]
struct SnapshotExportProvenanceBytesV1 {
    session_sha256: [u8; 32],
    owner_ordinal: u64,
    candidate_manifest_sha256: [u8; 32],
    validator_binary_sha256: [u8; 32],
    exporter_source_sha256: [u8; 32],
    build_receipt_sha256: [u8; 32],
    original_input_sha256: [u8; 32],
    validation_budget: [u64; 5], // source, metadata, scratch, work, deadline
}

// Proposed source-private selected interface:
// fn export_initial_snapshot_binding_v1(
//     initial: &InitialProfileBorrowV1<'_>,
//     provenance: &SelectedSnapshotExportProvenanceV1,
//     output: &mut std::fs::File,
// ) -> Result<SnapshotExportObservationV1, SnapshotExportErrorV1>;
