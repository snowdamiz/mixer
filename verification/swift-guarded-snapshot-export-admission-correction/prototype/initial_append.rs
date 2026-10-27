// Private exact sum ownership. Both variants retain the one exclusive control.
// Constructor below is a signature witness, not full snapshot phase admission.
enum CorrectionAccessV1<'c> {
    Admitted { control:&'c mut RuntimeControl, previous:usize },
    Refused { control:&'c mut RuntimeControl, error:AError },
}
struct CorrectionPhaseStorageV1 {
    plan:Option<[u64;8]>, temporary_output:Option<[u8;4096]>,
}
struct CorrectionCompositionV1 {
    primary:InitialProfileConstructionOutcomeV1,
    phase_completion:Result<(),SwiftRunFailure>,
}
fn correction_compose_signature_v1(
    cache:&SwiftFunctionCache, control:&mut RuntimeControl, wasi:Option<&AccountedWasi>,
    scalars:InitialProfileScalarsV1, claims:&UnverifiedProfileDigestBytesV1, row_output:&mut File,
)->CorrectionCompositionV1 {
    let access=CorrectionAccessV1::signature_witness(control);
    let primary='guarded: {
        // The one original literal is relocated here in the disposable source.
        let initial=InitialProfileBorrowV1 { cache,control:access.shared_control(),wasi,scalars };
        let proof_view=initial.cache.proof();
        let control_view=initial.control;
        let _=(proof_view.observations(),control_view.usage(wasi.map(AccountedWasi::usage)));
        let header=match encode_profile_header_v1(&initial,claims) {
            Ok(header)=>header,
            Err(error)=>break 'guarded InitialProfileConstructionOutcomeV1::HeaderRefused {error},
        };
        let rows=write_initial_profile_rows_v1(&initial,row_output);
        InitialProfileConstructionOutcomeV1::HeaderEncoded {header,rows}
    }; // every initial/view/header borrow ends before the consuming call.
    let phase_completion=access.complete(CorrectionPhaseStorageV1 {plan:None,temporary_output:None});
    CorrectionCompositionV1 {primary,phase_completion}
}
impl<'c> CorrectionAccessV1<'c> {
    fn signature_witness(control:&'c mut RuntimeControl)->Self {
        match control.correction_signature_bound_v1() {
            Ok(previous)=>Self::Admitted { control,previous },
            Err(error)=>Self::Refused { control,error },
        }
    }
    fn shared_control<'s>(&'s self)->&'s RuntimeControl {
        match self { Self::Admitted {control,..}|Self::Refused {control,..}=>control }
    }
    fn complete(self,storage:CorrectionPhaseStorageV1)->Result<(),SwiftRunFailure> {
        match self {
            Self::Admitted {control,previous}=>control.end_construction_phase(storage,previous),
            Self::Refused {control:_,error:_}=>{drop(storage);Ok(())},
        }
    }
}
struct CorrectionReborrowPlacesV1<'c> {
    access:CorrectionAccessV1<'c>, access_return:CorrectionAccessV1<'c>,
    access_option:Option<CorrectionAccessV1<'c>>,
    access_match:Result<usize,AError>, refusal:AError,
    shared_receiver:&'c CorrectionAccessV1<'c>, shared_return:&'c RuntimeControl,
    guard_control_argument:&'c RuntimeControl,
    guard:InitialProfileBorrowV1<'c>, guard_reference:&'c InitialProfileBorrowV1<'c>,
    proof_view:&'c ValidatedSwiftReactor, control_view:&'c RuntimeControl,
    storage:CorrectionPhaseStorageV1, storage_move:CorrectionPhaseStorageV1,
    storage_drop:CorrectionPhaseStorageV1,
    primary:InitialProfileConstructionOutcomeV1,
    primary_move:InitialProfileConstructionOutcomeV1,
    completion:Result<(),SwiftRunFailure>, completion_move:Result<(),SwiftRunFailure>,
    returned_pair:(InitialProfileConstructionOutcomeV1,Result<(),SwiftRunFailure>),
}
// Exact original header/row signatures are typechecked in the sole-guard block
// in the disposable source. Neither this packet nor its tests execute that wrapper.
#[no_mangle]
pub static MIXER_CORRECTION_REBORROW_LAYOUT_V1:[usize;18]=[
    size_of::<CorrectionAccessV1<'static>>(),std::mem::align_of::<CorrectionAccessV1<'static>>(),
    size_of::<Option<CorrectionAccessV1<'static>>>(),std::mem::align_of::<Option<CorrectionAccessV1<'static>>>(),
    size_of::<Result<usize,AError>>(),std::mem::align_of::<Result<usize,AError>>(),
    size_of::<CorrectionPhaseStorageV1>(),std::mem::align_of::<CorrectionPhaseStorageV1>(),
    size_of::<CorrectionReborrowPlacesV1<'static>>(),std::mem::align_of::<CorrectionReborrowPlacesV1<'static>>(),
    size_of::<InitialProfileBorrowV1<'static>>(),std::mem::align_of::<InitialProfileBorrowV1<'static>>(),
    size_of::<&'static CorrectionAccessV1<'static>>(),std::mem::align_of::<&'static CorrectionAccessV1<'static>>(),
    size_of::<(InitialProfileConstructionOutcomeV1,Result<(),SwiftRunFailure>)>(),std::mem::align_of::<(InitialProfileConstructionOutcomeV1,Result<(),SwiftRunFailure>)>(),
    size_of::<InitialProfileConstructionOutcomeV1>(),std::mem::align_of::<InitialProfileConstructionOutcomeV1>(),
];
