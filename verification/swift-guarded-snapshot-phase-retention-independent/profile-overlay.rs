// Independent scratch-only completion shim; no begin/adoption/loader/VM/writer.
#[cfg(test)]
pub(in crate::experimental_swift_reactor) fn independent_phase_complete_v1(
    control:&mut RuntimeControl,target:usize,wasi:Option<crate::experimental_wasi::WasiUsage>,admitted:bool,
)->Result<(),SwiftRunFailure>{
    use std::sync::{Arc,atomic::{AtomicUsize,Ordering}};
    #[derive(Debug)] struct OwnedDiagnostic(Arc<AtomicUsize>);
    impl std::fmt::Display for OwnedDiagnostic{
        fn fmt(&self,f:&mut std::fmt::Formatter<'_>)->std::fmt::Result{f.write_str("independent surviving diagnostic")}
    }
    impl std::error::Error for OwnedDiagnostic{}
    impl Drop for OwnedDiagnostic{fn drop(&mut self){self.0.fetch_add(1,Ordering::SeqCst);}}
    assert_eq!((std::mem::size_of::<SnapshotAccessV1<'_>>(),std::mem::align_of::<SnapshotAccessV1<'_>>()),(1104,8));
    assert_eq!((std::mem::size_of::<SnapshotPhaseStorageV1>(),std::mem::align_of::<SnapshotPhaseStorageV1>()),(5328,8));
    let drops=Arc::new(AtomicUsize::new(0));
    let export=SnapshotAttemptV1::Failed(SnapshotExportErrorV1 {
        cause:SnapshotCauseV1::Io,stage:71,
        progress:SnapshotProgressV1{bytes:73,calls:79,block:83,attempt:89,requested:97},
        io:Some(io::Error::new(io::ErrorKind::Other,OwnedDiagnostic(Arc::clone(&drops)))),post_stop:None,
    });
    let backing=match &export{SnapshotAttemptV1::Failed(error)=>error.io.as_ref().unwrap().get_ref().unwrap() as *const dyn std::error::Error as *const (),_=>unreachable!()};
    let access=if admitted{SnapshotAccessV1::Admitted{control,retained:target,wasi}}
        else{SnapshotAccessV1::Refused{control,error:AError::WorkAuditPending}};
    let storage=if admitted{SnapshotPhaseStorageV1 {
        plan:Some(SnapshotPlanV1{shape:SnapshotShapeV1{counts:[0;9],extent:0,blocks:0,records:0,words:0},planning:0,emission:0}),
        transfer:Some([0;4096]),refusal:None,
    }}else{SnapshotPhaseStorageV1{plan:None,transfer:None,refusal:Some(AError::WorkAuditPending)}};
    let completion=access.complete(storage);
    assert_eq!(drops.load(Ordering::SeqCst),0);
    match &export{SnapshotAttemptV1::Failed(error)=>{
        assert_eq!(error.io.as_ref().unwrap().get_ref().unwrap() as *const dyn std::error::Error as *const (),backing);
        assert_eq!(error.io.as_ref().unwrap().to_string(),"independent surviving diagnostic");
    },_=>unreachable!()}
    drop(export);assert_eq!(drops.load(Ordering::SeqCst),1);
    completion
}
