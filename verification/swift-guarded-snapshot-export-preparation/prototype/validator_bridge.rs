// Compile-signature preparation only. This module is never executed or integrated.
use super::*;
use crate::experimental_swift_reactor::InitialProfileBorrowV1;
use crate::experimental_swift_reactor::LoaderProvenanceV1;

pub(crate) enum PreparationErrorV1 { MissingSelected, PreparationOnly }
pub(crate) struct PreparationObservationV1 { _private: () }
pub(crate) struct LogicalSnapshotViewV1<'guard> {
    proof: &'guard ValidatedSwiftReactor,
    provenance: &'guard LoaderProvenanceV1,
}
impl<'guard> LogicalSnapshotViewV1<'guard> {
    pub(crate) fn source(&self) -> &'guard [u8] { &self.proof.source }
    fn signature_coverage(&self) {
        // Actual private fields, not descriptors or a second proof argument.
        let proof = self.proof;
        let _all_six = (&proof.source, &proof.metadata, &proof.policy,
                        &proof.imports, &proof.usage, &proof.observations);
        let m = &proof.metadata;
        let _scalars = (&m.memory, &m.table, &m.declarations.memory_maximum,
                        &m.declarations.table_maximum, m.declarations.memory_offset,
                        m.declarations.table_offset, m.instructions);
        let _inventory = [m.signatures.preparation_inventory_v1(),
            m.parameters.preparation_inventory_v1(), m.imports.preparation_inventory_v1(),
            m.functions.preparation_inventory_v1(), m.globals.preparation_inventory_v1(),
            m.exports.preparation_inventory_v1(), m.data.preparation_inventory_v1(),
            m.elements.preparation_inventory_v1()];
        // Compile each logical field using actual source types, without copying slack.
        for s in m.signatures.as_slice() { let _=(s.first,s.count,s.result); }
        for p in m.parameters.as_slice() { let _=*p; }
        for i in m.imports.as_slice() { let _=(i.module.offset,i.module.bytes,i.name.offset,i.name.bytes,i.type_index); }
        for f in m.functions.as_slice() { let _=(f.body.offset,f.body.bytes,f.type_index); }
        for g in m.globals.as_slice() { let _=(g.ty,g.mutable,g.initializer.offset,g.initializer.bytes); }
        for e in m.exports.as_slice() { let _=(e.name.offset,e.name.bytes,e.kind,e.index); }
        for s in m.data.as_slice().iter().chain(m.elements.as_slice()) {
            let _=(s.payload.offset,s.payload.bytes,s.destination,s.count);
        }
        let _provenance = self.provenance.preparation_fields_v1();
    }
}
// Returned borrows use the guard borrow lifetime, not the backing owner lifetime.
pub(crate) fn borrow_logical_snapshot_v1<'guard>(
    initial: &'guard InitialProfileBorrowV1<'_>,
) -> Result<LogicalSnapshotViewV1<'guard>,PreparationErrorV1> {
    let provenance = initial.preparation_selected_v1().ok_or(PreparationErrorV1::MissingSelected)?;
    Ok(LogicalSnapshotViewV1 { proof:initial.preparation_proof_v1(),provenance })
}
// Signature feasibility only: no write, allocation, digest mint, callback or success.
// The next selected slice must replace this explicit refusal with an admitted exporter.
pub(crate) fn export_signature_v1(
    initial: &InitialProfileBorrowV1<'_>, _output:&mut std::fs::File,
) -> Result<PreparationObservationV1,PreparationErrorV1> {
    borrow_logical_snapshot_v1(initial)?.signature_coverage();
    Err(PreparationErrorV1::PreparationOnly)
}

// Selected-target compile assertions only; no Rust struct memory is serialized.
const _: [();664] = [();std::mem::size_of::<ValidatedSwiftReactor>()];
const _: [();12] = [();std::mem::size_of::<metadata::Signature>()];
const _: [();1] = [();std::mem::size_of::<Type>()];
const _: [();20] = [();std::mem::size_of::<metadata::Import>()];
const _: [();12] = [();std::mem::size_of::<metadata::Function>()];
const _: [();12] = [();std::mem::size_of::<metadata::Global>()];
const _: [();16] = [();std::mem::size_of::<metadata::Export>()];
const _: [();16] = [();std::mem::size_of::<metadata::Segment>()];
