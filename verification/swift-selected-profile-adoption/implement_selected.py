#!/usr/bin/env python3
"""Selected source migration, with exact frozen preconditions; not a packet runner."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'source/vm/src/experimental_swift_reactor'
selection=ROOT.parent/'swift-semantic-adapter-root-review/selected-profile-adoption-implementation-selection.json'
assert hashlib.sha256(selection.read_bytes()).hexdigest()=='632f68edac578808b2162e94e0051c50732e45a48ebaa3a0d8ea790e3b51f2e3'
(ROOT/'selection.json').write_bytes(selection.read_bytes())

def edit(name,old,new):
 p=SOURCE/name;s=p.read_text();assert s.count(old)==1,(name,old[:80],s.count(old));p.write_text(s.replace(old,new))

edit('retained_profile_loader_v1.rs','//! No package authentication, runtime adoption, exporter or public route.','//! No package authentication, exporter or public route. Private adoption retains full provenance.')
edit('retained_profile_loader_v1.rs','use crate::Cancellation;','use crate::Cancellation;\nuse super::control::{AdoptedProof, RuntimeControl, SwiftRunBudget, SwiftRunFailure};\nuse std::time::Instant;')
edit('retained_profile_loader_v1.rs','struct LoaderProvenanceV1 {','pub(super) struct LoaderProvenanceV1 {')
edit('retained_profile_loader_v1.rs','impl SelectedValidatedProfileV1 {','''/// Opaque actual proof owner. Only the consuming carrier method below can
/// attach selected provenance. No fields, parts or owned extraction are exposed.
pub(super) struct AdoptionBodyV1 {
    proof: ValidatedSwiftReactor,
    selected: Option<LoaderProvenanceV1>,
}
impl AdoptionBodyV1 {
    pub(super) fn ordinary(proof: ValidatedSwiftReactor) -> Self {
        Self { proof, selected: None }
    }
    pub(super) fn proof(&self) -> &ValidatedSwiftReactor { &self.proof }
    pub(super) fn selected_provenance(&self) -> Option<&LoaderProvenanceV1> {
        self.selected.as_ref()
    }
}
impl SelectedValidatedProfileV1 {
    pub(super) fn adopt(
        self, budget: SwiftRunBudget, started: Instant, cancellation: Cancellation,
    ) -> Result<(RuntimeControl, AdoptedProof), SwiftRunFailure> {
        let Self { proof, provenance } = self;
        // Sole selected body literal. The original non-Clone owners move here.
        RuntimeControl::adopt_body(
            AdoptionBodyV1 { proof, selected: Some(provenance) },
            budget, started, cancellation,
        )
    }
''')
old='''    for (i, file) in [
        &files.source,
        &files.build,
        &files.session,
        files.executable.as_ref().expect("opened owner"),
    ]
    .into_iter()
    .enumerate()
    {
        if identity(file, Role::Source)? != identities[i] {
            return Err(LoaderFailureV1::new(
                Refusal::MetadataChanged,
                Role::Source,
                i,
                0,
            ));
        }
    }
'''
edit('retained_profile_loader_v1.rs',old,'    final_metadata_recheck_v1(files, &identities)?;\n')
needle='fn record_validation_peak(\n'
helper='''// Metadata errors retain their original typed payload and exact role. Mismatch
// offsets remain the original identity-array coordinate (0..3).
fn check_final_identity_v1(
    role: Role, index: usize, expected: FileIdentityV1,
    observed: Result<FileIdentityV1, LoaderFailureV1>,
) -> Result<(), LoaderFailureV1> {
    if observed? != expected {
        return Err(LoaderFailureV1::new(Refusal::MetadataChanged, role, index, 0));
    }
    Ok(())
}
#[cfg(target_os = "macos")]
fn final_metadata_recheck_v1(
    files: &ReturnedLoaderFilesV1, identities: &[FileIdentityV1; 4],
) -> Result<(), LoaderFailureV1> {
    for (index, (file, role)) in [
        (&files.source, Role::Source), (&files.build, Role::Build),
        (&files.session, Role::Session),
        (files.executable.as_ref().expect("opened owner"), Role::Executable),
    ].into_iter().enumerate() {
        check_final_identity_v1(role, index, identities[index], identity(file, role))?;
    }
    Ok(())
}
'''
edit('retained_profile_loader_v1.rs',needle,helper+needle)
edit('control.rs','use std::mem::size_of;','use std::mem::size_of;\nuse super::retained_profile_loader_v1::{AdoptionBodyV1, LoaderProvenanceV1};')
edit('control.rs','''pub(crate) struct AdoptedProof {
    proof: ValidatedSwiftReactor,''','''pub(crate) struct AdoptedProof {
    body: AdoptionBodyV1,''')
edit('control.rs','''        &self.proof
    }
}
#[derive(Clone, Copy, Debug)]
pub(crate) enum Work''','''        self.body.proof()
    }
    pub(super) fn selected_provenance(&self) -> Option<&LoaderProvenanceV1> {
        self.body.selected_provenance()
    }
}
#[derive(Clone, Copy, Debug)]
pub(crate) enum Work''')
edit('control.rs','''    ) -> Result<(Self, AdoptedProof), SwiftRunFailure> {
        let validation = proof.usage();''','''    ) -> Result<(Self, AdoptedProof), SwiftRunFailure> {
        Self::adopt_body(AdoptionBodyV1::ordinary(proof), budget, started, cancellation)
    }

    /// One shared original admission/cleanup implementation for both ingresses.
    /// The opaque body cannot be made selected from arbitrary proof/digest parts.
    pub(super) fn adopt_body(
        body: AdoptionBodyV1,
        budget: SwiftRunBudget,
        started: Instant,
        cancellation: Cancellation,
    ) -> Result<(Self, AdoptedProof), SwiftRunFailure> {
        let validation = body.proof().usage();''')
edit('control.rs','''            drop(proof);
            if let Some(ticket) = source''','''            drop(body);
            if let Some(ticket) = source''')
edit('control.rs','''            AdoptedProof {
                proof,
                source:''','''            AdoptedProof {
                body,
                source:''')
edit('control.rs','''        let AdoptedProof {
            proof,
            source,
            metadata,
        } = adopted;
        drop(proof);''','''        let AdoptedProof {
            body,
            source,
            metadata,
        } = adopted;
        drop(body);''')
edit('control.rs','''    let terms: [(usize, usize); 9] = [''','''    let terms: [(usize, usize); 12] = [''')
edit('control.rs','''        (1, super::execution::CONSTRUCTION_BOOTSTRAP_BYTES),''','''        (1, super::execution::CONSTRUCTION_BOOTSTRAP_BYTES),
        // Source ingress/body/result moves precede dependent preparation, and
        // body destruction/refund places survive through final cleanup.
        (1, super::retained_profile_loader_v1::ADOPTION_ENTRY_BYTES_V1),
        (1, super::retained_profile_loader_v1::ADOPTION_MOVE_BYTES_V1),
        (1, ADOPTION_CLEANUP_BYTES_V1),''')
inventory='''
// New source-authored destruction/refund places. Foundation retains this floor
// until all authentic body/proof owners are destroyed. Not physical stack/RSS.
#[allow(dead_code)]
struct AdoptionCleanupPlacesV1 {
    adopted_argument: AdoptedProof,
    body_pattern: AdoptionBodyV1,
    body_drop_argument: AdoptionBodyV1,
    source_pattern: ReservationTicket,
    metadata_pattern: ReservationTicket,
    observation: Option<WasiUsage>,
    source_result: Result<(), SwiftRunFailure>,
    metadata_result: Result<(), SwiftRunFailure>,
    combined_return: Result<(), SwiftRunFailure>,
    refused_body_drop: AdoptionBodyV1,
    refused_source: Option<ReservationTicket>,
    refused_metadata: Option<ReservationTicket>,
    refused_ticket_patterns: [ReservationTicket; 2],
    refused_refund_results: [Result<(), SwiftRunFailure>; 2],
    failure_pattern: SwiftRunFailure,
    cleanup_return: SwiftRunUsage,
    cleanup_some: Option<SwiftRunUsage>,
    receiver_borrows: [&'static mut RuntimeControl; 5],
}
pub(super) const ADOPTION_CLEANUP_BYTES_V1: usize = size_of::<AdoptionCleanupPlacesV1>();
pub(super) const ADOPTION_CLEANUP_ALIGNMENT_V1: usize = std::mem::align_of::<AdoptionCleanupPlacesV1>();
'''
edit('control.rs','\n/// The sole runtime admission authority.',inventory+'\n/// The sole runtime admission authority.')

# Definition-site loader/adoption measurements preserve private field/type access.
types=[('SelectedValidatedProfileV1','SelectedValidatedProfileV1'),('LoaderProvenanceV1','LoaderProvenanceV1'),('LoaderFailureV1','LoaderFailureV1'),('LoaderOutcomeV1','LoaderOutcomeV1'),('ReturnedLoaderFilesV1','ReturnedLoaderFilesV1'),('LoaderUsageV1','LoaderUsageV1'),('FileIdentityV1','FileIdentityV1'),('BuildView',"BuildView<'static>"),('SessionView',"SessionView<'static>"),('ProcessObservationV1','ProcessObservationV1'),('BytesProcess','Bytes<PROCESS_CAP>'),('BytesPath','Bytes<STR_CAP>'),('EnvironmentEntries','[(usize,usize,usize);ENTRY_CAP]'),('ResultSelected','Result<SelectedValidatedProfileV1,LoaderFailureV1>'),('ValidationResult','Result<ValidatedSwiftReactor,SwiftValidationFailure>'),('VecHeader','Vec<u8>'),('File','File'),('OptionFile','Option<File>'),('ValidationBudget','SwiftValidationBudget'),('ValidationFailure','SwiftValidationFailure'),('ObservationPlaces','ObservationPlacesV1'),('LoaderPlaces','LoaderPlacesV1'),('ReadHashPlaces','ReadHashPlacesV1'),('AdoptionBodyV1','AdoptionBodyV1'),('OptionalProvenance','Option<LoaderProvenanceV1>'),('BorrowedProvenance',"Option<&'static LoaderProvenanceV1>"),('AdoptionEntryPlacesV1','AdoptionEntryPlacesV1'),('AdoptionMovePlacesV1','AdoptionMovePlacesV1'),('AdoptionPair','(RuntimeControl,AdoptedProof)'),('AdoptionResult','Result<(RuntimeControl,AdoptedProof),SwiftRunFailure>'),('OptionalAdoptionPair','Option<(RuntimeControl,AdoptedProof)>'),('BorrowedAdoptionBody',"&'static AdoptionBodyV1"),('BorrowedSelectedCarrier',"&'static SelectedValidatedProfileV1"),('FinalRecheckPlacesV1','FinalRecheckPlacesV1')]
places='''
// Conservative complete new ingress and transfer source places. Whole owners
// are counted independently instead of borrowing containing padding.
struct AdoptionEntryPlacesV1 {
    ordinary_proof: ValidatedSwiftReactor,
    ordinary_body_return: AdoptionBodyV1,
    selected_carrier: SelectedValidatedProfileV1,
    selected_proof_pattern: ValidatedSwiftReactor,
    selected_provenance_pattern: LoaderProvenanceV1,
    selected_some: Option<LoaderProvenanceV1>,
    selected_body_literal: AdoptionBodyV1,
    inner_body_argument: AdoptionBodyV1,
    budgets: [SwiftRunBudget; 3],
    started: [Instant; 3],
    cancellations: [Cancellation; 3],
    validation_return: SwiftValidationUsage,
    proof_borrows: [&'static ValidatedSwiftReactor; 2],
    body_borrow: &'static AdoptionBodyV1,
    provenance_borrow: Option<&'static LoaderProvenanceV1>,
}
struct AdoptionMovePlacesV1 {
    adopted_literal: AdoptedProof,
    pair_literal: (RuntimeControl, AdoptedProof),
    inner_return: Result<(RuntimeControl, AdoptedProof), SwiftRunFailure>,
    ordinary_return: Result<(RuntimeControl, AdoptedProof), SwiftRunFailure>,
    selected_return: Result<(RuntimeControl, AdoptedProof), SwiftRunFailure>,
    caller_pair: (RuntimeControl, AdoptedProof),
    caller_option: Option<(RuntimeControl, AdoptedProof)>,
    caller_result: Result<(RuntimeControl, AdoptedProof), SwiftRunFailure>,
}
struct FinalRecheckPlacesV1 {
    arguments: (&'static ReturnedLoaderFilesV1, &'static [FileIdentityV1;4]),
    array: [(&'static File, Role);4],
    iterator: std::iter::Enumerate<std::array::IntoIter<(&'static File,Role),4>>,
    item: Option<(usize,(&'static File,Role))>,
    pattern: (usize,(&'static File,Role)),
    expected_argument: FileIdentityV1,
    observed_result: Result<FileIdentityV1,LoaderFailureV1>,
    helper_argument: Result<FileIdentityV1,LoaderFailureV1>,
    observed_pattern: FileIdentityV1,
    result_places: [Result<(),LoaderFailureV1>;3],
    mismatch_literal: LoaderFailureV1,
}
pub(super) const ADOPTION_ENTRY_BYTES_V1: usize = std::mem::size_of::<AdoptionEntryPlacesV1>();
pub(super) const ADOPTION_MOVE_BYTES_V1: usize = std::mem::size_of::<AdoptionMovePlacesV1>();
'''
places+='pub(super) static ADOPTION_LAYOUTS_V1: [(&str,usize,usize); '+str(len(types)+1)+'] = [\n'
for name,ty in types:places+=f'    ("{name}",std::mem::size_of::<{ty}>(),std::mem::align_of::<{ty}>()),\n'
places+='    ("AdoptionCleanupPlacesV1",super::control::ADOPTION_CLEANUP_BYTES_V1,super::control::ADOPTION_CLEANUP_ALIGNMENT_V1),\n];\n'
p=SOURCE/'retained_profile_loader_v1.rs';p.write_text(p.read_text()+places)
edit('retained_profile_loader_v1.rs','''        + std::mem::size_of::<ReadHashPlacesV1>()''','''        + std::mem::size_of::<ReadHashPlacesV1>()
        + std::mem::size_of::<FinalRecheckPlacesV1>()''')
(ROOT/'appended-layout-types.json').write_text(json.dumps([{'id':166+i,'name':name,'definition_site_type':ty} for i,(name,ty) in enumerate(types)]+[{'id':166+len(types),'name':'AdoptionCleanupPlacesV1','definition_site_type':'control::AdoptionCleanupPlacesV1'}],indent=2)+'\n')
print('shared admission/body/R1 implemented; selected literal tables deliberately unmigrated')
