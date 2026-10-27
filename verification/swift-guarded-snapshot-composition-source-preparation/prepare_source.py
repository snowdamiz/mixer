"""Fresh inline-only source preparation; never imports or executes old runners."""
from pathlib import Path
import json, hashlib,shutil

ROOT = Path(__file__).resolve().parent
VM = ROOT / 'source/vm'
CONTROL = VM / 'src/experimental_swift_reactor/control.rs'
INITIAL = VM / 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
LOADER = VM / 'src/experimental_swift_reactor/retained_profile_loader_v1.rs'

def replace_one(path, old, new):
    text = path.read_text()
    assert text.count(old) == 1, (path, old[:120], text.count(old))
    path.write_text(text.replace(old, new, 1))

def append(path, part):
    path.write_text(path.read_text() + '\n' + (ROOT / 'implementation' / part).read_text())

def prepare():
    # Reconstruct only this lane's owned source, verifying every frozen byte.
    frozen=ROOT.parent/'swift-guarded-snapshot-encoder-implementation/source/vm'
    expected=json.loads((ROOT/'input-source-manifest.json').read_text())['members']
    for member in expected:
        data=(frozen/member['path']).read_bytes()
        assert len(data)==member['bytes'] and hashlib.sha256(data).hexdigest()==member['sha256']
    if VM.exists():shutil.rmtree(VM)
    shutil.copytree(frozen,VM)
    # The original body is one common core. The closed profile fixes its return
    # type; no independent Selected retirement result reaches an Original adapter.
    replace_one(CONTROL,
'''    ) -> Result<(Self, AdoptedProof), SwiftRunFailure> {
        let validation = body.proof().usage();''',
'''    ) -> Result<(Self, AdoptedProof), SwiftRunFailure> {
        Self::adopt_body_core_v1::<OriginalAdoptionV1>(body,budget,started,cancellation)
    }

    fn adopt_body_core_v1<P: ClosedAdoptionV1>(
        body: AdoptionBodyV1, budget: SwiftRunBudget, started: Instant,
        cancellation: Cancellation,
    ) -> Result<(Self, AdoptedProof), P::Failure> {
        let validation = body.proof().usage();''')
    replace_one(CONTROL, 'let construction = foundation_construction_bytes().ok_or_else(|| {',
                'let construction = P::foundation().ok_or_else(|| {')
    replace_one(CONTROL,
'''            if let Some(ticket) = source {
                let _ = control.refund(ticket);
            }
            if let Some(ticket) = metadata {
                let _ = control.refund(ticket);
            }
            failure.after_cleanup = Some(control.finish_owned_cleanup(None));
            return Err(failure);''',
'''            let retirement = P::retire_tickets(&mut control,source,metadata);
            failure.after_cleanup = Some(control.finish_owned_cleanup(None));
            return Err(P::failure(failure,retirement));''')
    append(CONTROL, 'control.rs')

    # Exactly one private selected body literal, shared by original and new entry.
    replace_one(LOADER,
'''        let Self { proof, provenance } = self;
        // Sole selected body literal. The original non-Clone owners move here.
        RuntimeControl::adopt_body(
            AdoptionBodyV1 { proof, selected: Some(provenance) },
            budget, started, cancellation,
        )''',
'''        RuntimeControl::adopt_body(self.into_adoption_body_v1(),budget,started,cancellation)''')
    replace_one(LOADER, '    pub(super) fn validation_budget(&self) -> SwiftValidationBudget {',
'''    fn into_adoption_body_v1(self)->AdoptionBodyV1 {
        let Self { proof,provenance }=self;
        // Sole authentic selected body literal. No parts constructor is exposed.
        AdoptionBodyV1 { proof,selected:Some(provenance) }
    }
    pub(super) fn into_snapshot_scope_v1(
        self,budget:SwiftRunBudget,started:Instant,cancellation:Cancellation,
    )->Result<super::control::SnapshotScopeV1,super::control::SnapshotPreScopeFailureV1> {
        let selected_body=SelectedSnapshotBodyV1(self.into_adoption_body_v1());
        RuntimeControl::adopt_snapshot_body_v1(selected_body,budget,started,cancellation)
    }
    pub(super) fn validation_budget(&self) -> SwiftValidationBudget {''')
    replace_one(LOADER,'impl SelectedValidatedProfileV1 {',
'''/// Authentic selected-only capability. The tuple constructor is loader-private.
pub(super) struct SelectedSnapshotBodyV1(AdoptionBodyV1);
impl SelectedSnapshotBodyV1 {
    pub(super) fn into_adoption_body_v1(self)->AdoptionBodyV1{self.0}
}
impl SelectedValidatedProfileV1 {''')

    # Original ABI is a statically Original instantiation of one constructor.
    replace_one(INITIAL,
''')->InitialProfileConstructionOutcomeV1 {
    if cache_out.is_some()''',
''')->InitialProfileConstructionOutcomeV1 {
    construct_profile_core_v1(cache_out,control,wasi,adopted,selected,claims,row_output,OriginalBranchV1)
}
fn construct_profile_core_v1<B:ClosedBranchV1>(
    cache_out:&mut Option<SwiftFunctionCache>,control:&mut RuntimeControl,
    wasi:Option<&AccountedWasi>,adopted:AdoptedProof,
    selected:&SelectedInitialProfileV1,claims:&UnverifiedProfileDigestBytesV1,
    row_output:&mut File,mut branch:B,
)->B::Output {
    if cache_out.is_some()''')
    text=INITIAL.read_text()
    begin=text.index('fn construct_profile_core_v1')
    end=text.index('fn write_initial_profile_rows_v1',begin)
    body=text[begin:end]
    body=body.replace('return InitialProfileConstructionOutcomeV1::SlotOccupied { adopted };',
                      'return branch.early(InitialProfileConstructionOutcomeV1::SlotOccupied { adopted });')
    body=body.replace('return InitialProfileConstructionOutcomeV1::SelectionRefused { error,adopted };',
                      'return branch.early(InitialProfileConstructionOutcomeV1::SelectionRefused { error,adopted });')
    body=body.replace('return InitialProfileConstructionOutcomeV1::PreparationFailed { failure,adopted },',
                      'return branch.early(InitialProfileConstructionOutcomeV1::PreparationFailed { failure,adopted }),')
    body=body.replace('return InitialProfileConstructionOutcomeV1::ConstructionFailed { failure,completion };',
                      'return branch.early(InitialProfileConstructionOutcomeV1::ConstructionFailed { failure,completion });')
    body=body.replace('return InitialProfileConstructionOutcomeV1::PhaseCompletionFailed { failure };',
                      'return branch.early(InitialProfileConstructionOutcomeV1::PhaseCompletionFailed { failure });')
    body=body.replace('return InitialProfileConstructionOutcomeV1::HeaderRefused { error },',
                      'return branch.early(InitialProfileConstructionOutcomeV1::HeaderRefused { error }),')
    body=body.replace('return InitialProfileConstructionOutcomeV1::HeaderOwnerCheckFailed { failure },',
                      'return branch.early(InitialProfileConstructionOutcomeV1::HeaderOwnerCheckFailed { failure }),')
    literal=body.index('    // Sole guard literal.')
    body=body[:literal]+'''    let (access,mut storage)=branch.begin(cache,control,wasi);
    let (primary,attempt)='guarded: {
        // Sole guard literal. The access owns the exclusive borrow in both states.
        let initial=InitialProfileBorrowV1 { cache,control:access.shared_control(),wasi,scalars };
        #[cfg(any(test,mixer_snapshot_encoder_host))]
        branch.original_encoder_observer(&initial);
        let attempt=branch.export(&initial,&mut storage,row_output);
        #[cfg(any(test,mixer_initial_profile_component_host))] tests::mark(3);
        let header=match encode_profile_header_v1(&initial,claims) {
            Ok(header)=>header,
            Err(error)=>break 'guarded (InitialProfileConstructionOutcomeV1::HeaderRefused {error},attempt),
        };
        #[cfg(any(test,mixer_initial_profile_component_host))] tests::mark(4);
        let rows=write_initial_profile_rows_v1(&initial,row_output);
        (InitialProfileConstructionOutcomeV1::HeaderEncoded {header,rows},attempt)
    }; // Every guard/view/cursor/block borrow has ended.
    branch.finish(primary,attempt,access,storage)
}
'''
    text=text[:begin]+body+text[end:]
    # Visibility changes expose opaque types only inside the existing owner tree.
    text=text.replace('struct UnverifiedProfileDigestBytesV1 {','pub(in crate::experimental_swift_reactor) struct UnverifiedProfileDigestBytesV1 {')
    INITIAL.write_text(text)
    append(INITIAL, 'initial.rs')
    append(INITIAL, 'future_host.rs')
    append(VM/'src/experimental_swift_reactor/cache.rs', 'cache.rs')
    append(VM/'src/experimental_wasi/accounted.rs', 'wasi.rs')
    append(VM/'src/experimental/swift.rs', 'shape.rs')
    append(LOADER,'loader_measurement.rs')
    encoder_path=VM/'src/experimental/swift.rs'
    text=encoder_path.read_text()
    frozen_text=(frozen/'src/experimental/swift.rs').read_text()
    insertion=frozen_text.rfind('\n}')
    seam='\n'+(ROOT/'implementation/encoder_measurement.rs').read_text()
    encoder_path.write_text(text[:insertion]+seam+text[insertion:])
    members=[]
    for p in sorted(VM.rglob('*')):
        if p.is_file():
            data=p.read_bytes(); members.append({'path':p.relative_to(VM).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    assert len(members)==144,len(members)
    (ROOT/'source-manifest.json').write_text(json.dumps({'schema':1,'members':members,'source_members':144},indent=2)+'\n')

if __name__=='__main__': prepare()
