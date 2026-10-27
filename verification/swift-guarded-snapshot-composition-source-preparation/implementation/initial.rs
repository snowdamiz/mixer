
use super::super::control::{SnapshotAdmissionErrorV1 as AError,SnapshotStopV1 as Stop};
use crate::experimental::swift::snapshot_encoder_v2::{borrow_snapshot_v2,SnapshotEncodeErrorV2,SnapshotCursorV2,SnapshotViewV2,SnapshotBlockV2};
use std::io::{self,Write,Seek};
use std::os::unix::fs::MetadataExt;

mod branch_seal_v1 { pub(super) trait Closed {} }
struct OriginalBranchV1;
struct SnapshotBranchV1<'f> { output:&'f mut File }
impl branch_seal_v1::Closed for OriginalBranchV1 {}
impl branch_seal_v1::Closed for SnapshotBranchV1<'_> {}
trait SharedControlV1 {fn shared_control(&self)->&RuntimeControl;}
struct OriginalAccessV1<'c>(&'c mut RuntimeControl);
impl SharedControlV1 for OriginalAccessV1<'_>{fn shared_control(&self)->&RuntimeControl{self.0}}
trait ClosedBranchV1:branch_seal_v1::Closed {
    type Output;
    type Attempt;
    type Storage;
    type Access<'c>:SharedControlV1;
    fn early(self,primary:InitialProfileConstructionOutcomeV1)->Self::Output;
    fn begin<'c>(&self,cache:&SwiftFunctionCache,control:&'c mut RuntimeControl,wasi:Option<&AccountedWasi>)->(Self::Access<'c>,Self::Storage);
    fn export(&mut self,initial:&InitialProfileBorrowV1<'_>,storage:&mut Self::Storage,rows:&File)->Self::Attempt;
    fn finish(self,primary:InitialProfileConstructionOutcomeV1,attempt:Self::Attempt,access:Self::Access<'_>,storage:Self::Storage)->Self::Output;
    #[cfg(any(test,mixer_snapshot_encoder_host))]
    fn original_encoder_observer(&self,_:&InitialProfileBorrowV1<'_>){}
}
impl ClosedBranchV1 for OriginalBranchV1 {
    type Output=InitialProfileConstructionOutcomeV1;
    type Attempt=();type Storage=();type Access<'c>=OriginalAccessV1<'c>;
    fn early(self,primary:Self::Output)->Self::Output{primary}
    fn begin<'c>(&self,_:&SwiftFunctionCache,control:&'c mut RuntimeControl,_:Option<&AccountedWasi>)->(Self::Access<'c>,()){
        (OriginalAccessV1(control),())
    }
    fn export(&mut self,_:&InitialProfileBorrowV1<'_>,_:&mut (),_:&File){}
    fn finish(self,primary:Self::Output,_:(),access:Self::Access<'_>,_:())->Self::Output{drop(access);primary}
    #[cfg(any(test,mixer_snapshot_encoder_host))]
    fn original_encoder_observer(&self,initial:&InitialProfileBorrowV1<'_>){snapshot_encoder_host::observe_v2(initial);}
}
impl ClosedBranchV1 for SnapshotBranchV1<'_> {
    type Output=SnapshotOuterV1;type Attempt=SnapshotAttemptV1;
    type Storage=SnapshotPhaseStorageV1;type Access<'c>=SnapshotAccessV1<'c>;
    fn early(self,primary:InitialProfileConstructionOutcomeV1)->Self::Output{
        SnapshotOuterV1 {primary,export:SnapshotAttemptV1::NotReached,phase_completion:Ok(())}
    }
    fn begin<'c>(&self,cache:&SwiftFunctionCache,control:&'c mut RuntimeControl,wasi:Option<&AccountedWasi>)->(Self::Access<'c>,Self::Storage){
        begin_snapshot_access_v1(cache,control,wasi)
    }
    fn export(&mut self,initial:&InitialProfileBorrowV1<'_>,storage:&mut Self::Storage,rows:&File)->Self::Attempt{
        match (&storage.plan,&mut storage.transfer) {
            (Some(plan),Some(transfer))=>write_snapshot_v1(initial,plan,transfer,rows,self.output),
            (None,None)=>SnapshotAttemptV1::AdmissionRefused(storage.refusal.expect("actual refusal")),
            _=>unreachable!("private phase slots paired at admission"),
        }
    }
    fn finish(self,primary:InitialProfileConstructionOutcomeV1,export:Self::Attempt,access:Self::Access<'_>,storage:Self::Storage)->Self::Output{
        let phase_completion=access.complete(storage);
        SnapshotOuterV1 {primary,export,phase_completion}
    }
}

enum SnapshotAccessV1<'c> {
    Admitted {control:&'c mut RuntimeControl,previous:usize,wasi:Option<crate::experimental_wasi::WasiUsage>},
    Refused {control:&'c mut RuntimeControl,error:AError},
}
impl SharedControlV1 for SnapshotAccessV1<'_>{
    fn shared_control(&self)->&RuntimeControl{match self{Self::Admitted{control,..}|Self::Refused{control,..}=>control}}
}
impl SnapshotAccessV1<'_> {
    fn complete(self,storage:SnapshotPhaseStorageV1)->Result<(),SwiftRunFailure>{
        match self{
            Self::Admitted{control,previous,wasi}=>control.end_construction_phase_with_wasi(storage,previous,wasi),
            Self::Refused{control:_,error:_}=>{drop(storage);Ok(())},
        }
    }
}
struct SnapshotShapeV1 {counts:[u64;9],extent:u64,blocks:u64,records:u64,words:u64}
struct SnapshotPlanV1 {shape:SnapshotShapeV1,planning:u64,emission:u64}
struct SnapshotPhaseStorageV1 {plan:Option<SnapshotPlanV1>,transfer:Option<[u8;4096]>,refusal:Option<AError>}
fn checked_add_v1(a:u64,b:u64)->Result<u64,AError>{a.checked_add(b).ok_or(AError::Arithmetic)}
fn checked_mul_v1(a:u64,b:u64)->Result<u64,AError>{a.checked_mul(b).ok_or(AError::Arithmetic)}
fn snapshot_shape_v1(counts:[usize;9])->Result<SnapshotShapeV1,AError>{
    const CAPS:[u64;9]=[67108864,512,8192,34,79966,8192,4096,4096,4096];
    const WIDTHS:[u64;9]=[0,3,1,5,3,4,4,4,4];
    let mut converted=[0u64;9];let mut words=0;let mut records=0;
    for i in 0..9 {
        let n=u64::try_from(counts[i]).map_err(|_|AError::Arithmetic)?;
        if n>CAPS[i]{return Err(AError::Layout);}
        converted[i]=n;
        if i!=0 {records=checked_add_v1(records,n)?;words=checked_add_v1(words,checked_mul_v1(n,WIDTHS[i])?)?;}
    }
    let extent=checked_add_v1(checked_add_v1(2560,converted[0])?,checked_mul_v1(8,words)?)?;
    let blocks=checked_add_v1(extent/4096,u64::from(extent%4096!=0))?;
    Ok(SnapshotShapeV1 {counts:converted,extent,blocks,records,words})
}
fn proposed_emission_work_v1(_shape:&SnapshotShapeV1)->Result<u64,AError>{
    // Deliberate compile-time preparation stop. The old P/R record rationale
    // does not cover repeated record_word validation/directory search. Root is
    // obtaining a separate source action audit. No rounded placeholder debits
    // can accidentally admit this source if called before that review.
    Err(AError::WorkAuditPending)
}
fn begin_snapshot_access_v1<'c>(cache:&SwiftFunctionCache,control:&'c mut RuntimeControl,wasi:Option<&AccountedWasi>)
    ->(SnapshotAccessV1<'c>,SnapshotPhaseStorageV1){
    let decision=(||{
        cache.snapshot_pair_v1(control,wasi)?;
        let additional=SNAPSHOT_PHASE_PLACES_V1;
        control.snapshot_storage_preflight_v1(additional)?;
        let planning=16384u64; // Original fixed planning contract; audit pending.
        control.snapshot_debit_v1(planning)?;
        let shape=snapshot_shape_v1(cache.proof().snapshot_counts_v1())?;
        let emission=proposed_emission_work_v1(&shape)?;
        control.snapshot_debit_v1(emission)?;
        let previous=control.snapshot_commit_storage_v1(additional)?;
        Ok::<_,AError>((previous,shape,planning,emission))
    })();
    match decision{
        Ok((previous,shape,planning,emission))=>{
            let wasi=wasi.map(AccountedWasi::usage); // Pairing completed above.
            let storage=SnapshotPhaseStorageV1 {plan:Some(SnapshotPlanV1{shape,planning,emission}),transfer:Some([0;4096]),refusal:None};
            (SnapshotAccessV1::Admitted{control,previous,wasi},storage)
        },
        Err(error)=>(SnapshotAccessV1::Refused{control,error},SnapshotPhaseStorageV1{plan:None,transfer:None,refusal:Some(error)}),
    }
}

#[derive(Clone,Copy)]
struct SnapshotProgressV1 {bytes:u64,calls:u64,block:u64,attempt:u32,requested:u64}
enum SnapshotCauseV1 {Stop(Stop),Encode(SnapshotEncodeErrorV2),Shape,NotRegular,NotEmpty,Alias,Position,Io,Zero,Overreported,Attempts,Arithmetic}
struct SnapshotExportErrorV1 {cause:SnapshotCauseV1,stage:u32,progress:SnapshotProgressV1,io:Option<io::Error>,post_stop:Option<Stop>}
struct SnapshotObservationV1 {bytes:u64,calls:u64,planning:u64,emission:u64}
enum SnapshotAttemptV1 {NotReached,AdmissionRefused(AError),Completed(SnapshotObservationV1),Failed(SnapshotExportErrorV1)}
#[must_use="Retain original primary, export and phase completion separately"]
pub(in crate::experimental_swift_reactor) struct SnapshotOuterV1 {
    primary:InitialProfileConstructionOutcomeV1,export:SnapshotAttemptV1,phase_completion:Result<(),SwiftRunFailure>,
}
struct SnapshotWriterV1<'g> {initial:&'g InitialProfileBorrowV1<'g>,progress:SnapshotProgressV1}
impl SnapshotWriterV1<'_> {
    fn error(&self,cause:SnapshotCauseV1,stage:u32,io:Option<io::Error>,post_stop:Option<Stop>)->SnapshotExportErrorV1{
        SnapshotExportErrorV1 {cause,stage,progress:self.progress,io,post_stop}
    }
    fn stop(&self,stage:u32)->Result<(),SnapshotExportErrorV1>{
        self.initial.control.snapshot_observe_stop_v1().map_err(|stop|self.error(SnapshotCauseV1::Stop(stop),stage,None,None))
    }
    fn io_result<T>(&self,result:io::Result<T>,stage:u32)->Result<T,SnapshotExportErrorV1>{
        let post_stop=self.initial.control.snapshot_observe_stop_v1().err();
        match result {
            Err(error)=>Err(self.error(SnapshotCauseV1::Io,stage,Some(error),post_stop)),
            Ok(value)=>match post_stop {Some(stop)=>Err(self.error(SnapshotCauseV1::Stop(stop),stage,None,None)),None=>Ok(value)},
        }
    }
    fn encode_result<T>(&self,result:Result<T,SnapshotEncodeErrorV2>,stage:u32)->Result<T,SnapshotExportErrorV1>{
        let post_stop=self.initial.control.snapshot_observe_stop_v1().err();
        match result {
            Err(error)=>Err(self.error(SnapshotCauseV1::Encode(error),stage,None,post_stop)),
            Ok(value)=>match post_stop{Some(stop)=>Err(self.error(SnapshotCauseV1::Stop(stop),stage,None,None)),None=>Ok(value)},
        }
    }
}
fn write_snapshot_v1(initial:&InitialProfileBorrowV1<'_>,plan:&SnapshotPlanV1,transfer:&mut[u8;4096],rows:&File,output:&mut File)->SnapshotAttemptV1{
    let mut writer=SnapshotWriterV1 {initial,progress:SnapshotProgressV1{bytes:0,calls:0,block:0,attempt:0,requested:0}};
    let result=(||{
        writer.stop(1)?;
        let view=writer.encode_result(borrow_snapshot_v2(initial),1)?;
        writer.stop(2)?;
        let mut cursor=writer.encode_result(view.into_cursor(),2)?;
        // This checks actual guard data before any metadata/seek/write call.
        let actual=initial.cache.proof().snapshot_counts_v1();
        let mut same=true;
        for i in 0..9 {same &= u64::try_from(actual[i]).ok()==Some(plan.shape.counts[i]);}
        if !same || cursor.encoded_extent()!=plan.shape.extent{return Err(writer.error(SnapshotCauseV1::Shape,3,None,None));}
        writer.stop(4)?;
        let metadata=writer.io_result(output.metadata(),4)?;
        writer.stop(5)?;
        let row_metadata=writer.io_result(rows.metadata(),5)?;
        if !metadata.is_file(){return Err(writer.error(SnapshotCauseV1::NotRegular,6,None,None));}
        if metadata.dev()==row_metadata.dev() && metadata.ino()==row_metadata.ino(){return Err(writer.error(SnapshotCauseV1::Alias,6,None,None));}
        if metadata.len()!=0{return Err(writer.error(SnapshotCauseV1::NotEmpty,6,None,None));}
        writer.stop(7)?;
        let position=writer.io_result(output.stream_position(),7)?;
        if position!=0{return Err(writer.error(SnapshotCauseV1::Position,7,None,None));}
        loop {
            writer.stop(8)?;transfer.fill(0);writer.stop(8)?;
            writer.stop(9)?;
            let block=writer.encode_result(cursor.next_block(transfer),9)?
                .ok_or_else(||writer.error(SnapshotCauseV1::Shape,9,None,None))?;
            if block.offset()!=writer.progress.bytes{return Err(writer.error(SnapshotCauseV1::Shape,9,None,None));}
            let mut acknowledged=0usize;
            let mut interrupted=None;
            for attempt in 1..=32u32 {
                writer.progress.attempt=attempt;
                let requested=&block.bytes()[acknowledged..];
                writer.progress.requested=u64::try_from(requested.len()).map_err(|_|writer.error(SnapshotCauseV1::Arithmetic,10,None,None))?;
                writer.stop(10)?;
                writer.progress.calls=writer.progress.calls.checked_add(1).ok_or_else(||writer.error(SnapshotCauseV1::Arithmetic,10,None,None))?;
                // Exactly one native write per attempt, including Interrupted.
                let returned=output.write(requested);
                let post_stop=initial.control.snapshot_observe_stop_v1().err();
                match returned {
                    Ok(n) if n>0 && n<=requested.len()=>{
                        acknowledged=acknowledged.checked_add(n).ok_or_else(||writer.error(SnapshotCauseV1::Arithmetic,10,None,post_stop))?;
                        writer.progress.bytes=writer.progress.bytes.checked_add(n as u64).ok_or_else(||writer.error(SnapshotCauseV1::Arithmetic,10,None,post_stop))?;
                        // Acknowledged bytes survive cancellation inside write.
                        if let Some(stop)=post_stop{return Err(writer.error(SnapshotCauseV1::Stop(stop),10,None,None));}
                        if acknowledged==block.bytes().len(){break;}
                    },
                    Ok(0)=>return Err(writer.error(SnapshotCauseV1::Zero,10,None,post_stop)),
                    Ok(_)=>return Err(writer.error(SnapshotCauseV1::Overreported,10,None,post_stop)),
                    Err(error) if error.kind()==io::ErrorKind::Interrupted=>{
                        if post_stop.is_some(){return Err(writer.error(SnapshotCauseV1::Io,10,Some(error),post_stop));}
                        interrupted=Some(error);
                    },
                    Err(error)=>return Err(writer.error(SnapshotCauseV1::Io,10,Some(error),post_stop)),
                }
                if attempt==32{return Err(writer.error(SnapshotCauseV1::Attempts,10,interrupted.take(),None));}
            }
            if acknowledged!=block.bytes().len(){return Err(writer.error(SnapshotCauseV1::Attempts,10,interrupted,None));}
            let final_block=block.is_final();
            drop(block);
            writer.progress.block=writer.progress.block.checked_add(1).ok_or_else(||writer.error(SnapshotCauseV1::Arithmetic,11,None,None))?;
            writer.stop(11)?;
            if final_block{break;}
        }
        if writer.progress.bytes!=plan.shape.extent || cursor.emitted_extent()!=plan.shape.extent || writer.progress.block!=plan.shape.blocks{
            return Err(writer.error(SnapshotCauseV1::Shape,12,None,None));
        }
        writer.stop(12)?;
        let observation=SnapshotObservationV1 {bytes:writer.progress.bytes,calls:writer.progress.calls,planning:plan.planning,emission:plan.emission};
        writer.stop(12)?;
        Ok(observation)
    })();
    match result{Ok(observation)=>SnapshotAttemptV1::Completed(observation),Err(error)=>SnapshotAttemptV1::Failed(error)}
}

pub(in crate::experimental_swift_reactor) struct SnapshotPrimaryRetirementV1 {
    variant:u32,primary:Option<SwiftRunFailure>,header_error:Option<ProfileHeaderErrorV1>,
    header:Option<UnverifiedProfileHeaderV1>,rows:Option<Result<ProfileRowsObservationV1,ProfileAdapterErrorV1>>,
    construction_completion:Option<Result<(),SwiftRunFailure>>,adopted_retirement:Result<(),SwiftRunFailure>,
    export:SnapshotAttemptV1,phase_completion:Result<(),SwiftRunFailure>,
}
impl SnapshotOuterV1 {
    pub(in crate::experimental_swift_reactor) fn retire_v1(self,control:&mut RuntimeControl,wasi:Option<crate::experimental_wasi::WasiUsage>)->SnapshotPrimaryRetirementV1{
        let Self{primary,export,phase_completion}=self;
        let (variant,primary,header_error,header,rows,construction_completion,adopted)=match primary {
            InitialProfileConstructionOutcomeV1::SlotOccupied{adopted}=>(1,None,None,None,None,None,Some(adopted)),
            InitialProfileConstructionOutcomeV1::SelectionRefused{error,adopted}=>(2,None,Some(error),None,None,None,Some(adopted)),
            InitialProfileConstructionOutcomeV1::PreparationFailed{failure,adopted}=>(3,Some(failure),None,None,None,None,Some(adopted)),
            InitialProfileConstructionOutcomeV1::ConstructionFailed{failure,completion}=>(4,Some(failure.failure),None,None,None,Some(completion),failure.rejected_adopted),
            InitialProfileConstructionOutcomeV1::PhaseCompletionFailed{failure}=>(5,Some(failure),None,None,None,None,None),
            InitialProfileConstructionOutcomeV1::HeaderRefused{error}=>(6,None,Some(error),None,None,None,None),
            InitialProfileConstructionOutcomeV1::HeaderOwnerCheckFailed{failure}=>(7,Some(failure),None,None,None,None,None),
            InitialProfileConstructionOutcomeV1::HeaderEncoded{header,rows}=>(8,None,None,Some(header),Some(rows),None,None),
        };
        let adopted_retirement=match adopted{Some(adopted)=>control.drop_proof_with_wasi(adopted,wasi),None=>Ok(())};
        SnapshotPrimaryRetirementV1 {variant,primary,header_error,header,rows,construction_completion,adopted_retirement,export,phase_completion}
    }
}

pub(super) fn construct_snapshot_owned_v1(cache:&mut Option<SwiftFunctionCache>,control:&mut RuntimeControl,wasi:Option<&AccountedWasi>,adopted:AdoptedProof,claims:&UnverifiedProfileDigestBytesV1,rows:&mut File,snapshot:&mut File)->SnapshotOuterV1{
    construct_profile_core_v1(cache,control,wasi,adopted,&selected_initial_profile_v1(),claims,rows,SnapshotBranchV1{output:snapshot})
}

struct SnapshotFoundationPlacesV1<'a> {
    branch:SnapshotBranchV1<'a>,access:SnapshotAccessV1<'a>,access_return:SnapshotAccessV1<'a>,access_option:Option<SnapshotAccessV1<'a>>,
    decision:Result<(usize,SnapshotShapeV1,u64,u64),AError>,shape:SnapshotShapeV1,shape_return:Result<SnapshotShapeV1,AError>,
    storage:SnapshotPhaseStorageV1,storage_return:SnapshotPhaseStorageV1,storage_move:SnapshotPhaseStorageV1,
    attempts:[SnapshotAttemptV1;4],outers:[SnapshotOuterV1;4],outer_option:Option<SnapshotOuterV1>,
    completions:[Result<(),SwiftRunFailure>;4],originals:[InitialProfileConstructionOutcomeV1;2],
    retirement:SnapshotPrimaryRetirementV1,retirement_return:SnapshotPrimaryRetirementV1,
    admission_errors:[AError;4],stop:[Stop;4],borrows:[usize;32],counts:[[u64;9];3],
}
struct SnapshotPhasePlacesV1<'g> {
    plan:SnapshotPlanV1,plan_move:SnapshotPlanV1,
    storage:SnapshotPhaseStorageV1,storage_drop:SnapshotPhaseStorageV1,
    views:[SnapshotViewV2<'g>;3],view_result:Result<SnapshotViewV2<'g>,SnapshotEncodeErrorV2>,
    cursors:[SnapshotCursorV2<'g>;3],cursor_result:Result<SnapshotCursorV2<'g>,SnapshotEncodeErrorV2>,
    blocks:[Option<SnapshotBlockV2<'g>>;3],block_result:Result<Option<SnapshotBlockV2<'g>>,SnapshotEncodeErrorV2>,
    writer:SnapshotWriterV1<'g>,writer_move:SnapshotWriterV1<'g>,
    metadata:[std::fs::Metadata;2],metadata_returns:[Result<std::fs::Metadata,io::Error>;2],
    positions:[Result<u64,io::Error>;2],write_return:Result<usize,io::Error>,
    io_errors:[Option<io::Error>;4],export_errors:[SnapshotExportErrorV1;4],
    observations:[SnapshotObservationV1;3],progress:[SnapshotProgressV1;4],
    shape_counts:[usize;9],identities:[u64;4],counters:[usize;32],
}
pub(super) const SNAPSHOT_FOUNDATION_PLACES_V1:usize=size_of::<SnapshotFoundationPlacesV1<'static>>();
const SNAPSHOT_PHASE_PLACES_V1:usize=size_of::<SnapshotPhasePlacesV1<'static>>();
#[cfg(mixer_snapshot_composition_layout)]
#[no_mangle]
pub static MIXER_COMPOSITION_INITIAL_LAYOUTS_V1:[usize;36]=[
 size_of::<OriginalAccessV1<'static>>(),std::mem::align_of::<OriginalAccessV1<'static>>(),
 size_of::<SnapshotAccessV1<'static>>(),std::mem::align_of::<SnapshotAccessV1<'static>>(),
 size_of::<SnapshotShapeV1>(),std::mem::align_of::<SnapshotShapeV1>(),
 size_of::<SnapshotPlanV1>(),std::mem::align_of::<SnapshotPlanV1>(),
 size_of::<SnapshotPhaseStorageV1>(),std::mem::align_of::<SnapshotPhaseStorageV1>(),
 size_of::<SnapshotProgressV1>(),std::mem::align_of::<SnapshotProgressV1>(),
 size_of::<SnapshotCauseV1>(),std::mem::align_of::<SnapshotCauseV1>(),
 size_of::<SnapshotExportErrorV1>(),std::mem::align_of::<SnapshotExportErrorV1>(),
 size_of::<SnapshotAttemptV1>(),std::mem::align_of::<SnapshotAttemptV1>(),
 size_of::<SnapshotOuterV1>(),std::mem::align_of::<SnapshotOuterV1>(),
 size_of::<SnapshotPrimaryRetirementV1>(),std::mem::align_of::<SnapshotPrimaryRetirementV1>(),
 size_of::<SnapshotFoundationPlacesV1<'static>>(),std::mem::align_of::<SnapshotFoundationPlacesV1<'static>>(),
 size_of::<SnapshotPhasePlacesV1<'static>>(),std::mem::align_of::<SnapshotPhasePlacesV1<'static>>(),
 size_of::<InitialProfileConstructionOutcomeV1>(),std::mem::align_of::<InitialProfileConstructionOutcomeV1>(),
 size_of::<InitialProfileBorrowV1<'static>>(),std::mem::align_of::<InitialProfileBorrowV1<'static>>(),
 size_of::<Result<SnapshotOuterV1,SwiftRunFailure>>(),std::mem::align_of::<Result<SnapshotOuterV1,SwiftRunFailure>>(),
 size_of::<OriginalBranchV1>(),std::mem::align_of::<OriginalBranchV1>(),
 size_of::<SnapshotBranchV1<'static>>(),std::mem::align_of::<SnapshotBranchV1<'static>>(),
];
