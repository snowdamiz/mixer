// Separately hashed test overlay, appended only in an owned scratch copy.
// Direct completion only: no begin, proof, loader, cache, VM or writer dispatch.
#[cfg(test)]
pub(in crate::experimental_swift_reactor) fn phase_retention_test_complete_v1(
    control:&mut RuntimeControl,retained:usize,wasi:Option<crate::experimental_wasi::WasiUsage>,admitted:bool,
)->Result<(),SwiftRunFailure>{
    assert_eq!(std::mem::size_of::<SnapshotAccessV1<'_>>(),1104);
    assert_eq!(std::mem::align_of::<SnapshotAccessV1<'_>>(),8);
    assert_eq!(std::mem::size_of::<SnapshotPhaseStorageV1>(),5328);
    assert_eq!(std::mem::align_of::<SnapshotPhaseStorageV1>(),8);
    let access=if admitted {SnapshotAccessV1::Admitted{control,retained,wasi}}
        else {SnapshotAccessV1::Refused{control,error:AError::WorkAuditPending}};
    let storage=if admitted {
        SnapshotPhaseStorageV1{plan:Some(SnapshotPlanV1{
            shape:SnapshotShapeV1{counts:[0;9],extent:0,blocks:0,records:0,words:0},planning:0,emission:0,
        }),transfer:Some([0;4096]),refusal:None}
    } else {SnapshotPhaseStorageV1{plan:None,transfer:None,refusal:Some(AError::WorkAuditPending)}};
    access.complete(storage)
}
