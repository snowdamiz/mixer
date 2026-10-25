// Independently authored completion controls. The product operation bodies are unchanged.
mod ordered_completion_tests {
    use super::*;
    use super::ordered_observer::{DispatchGuard,EndReceipt,Custody,begin,phase,footer,retire_after_quiescence,stored_for_fixture,flags,state};
    use super::ordered_wire::*;
    use super::super::allocation_tests::AllocationStats;
    use std::fs::{File,OpenOptions};
    use std::fmt::Write as FmtWrite;
    use std::os::unix::fs::OpenOptionsExt;
    use std::path::{Path,PathBuf};
    use std::sync::atomic::{AtomicU64,Ordering};
    static CASE:AtomicU64=AtomicU64::new(0);

    // A bounded synchronous formatter, rather than an allocated format! buffer.
    // Each fill uses at most 32 writes, and the entire receipt is <=8192 bytes.
    struct ReceiptWriter {file:File,buffer:[u8;512],used:usize,total:usize,attempts:u64}
    impl ReceiptWriter {
        fn create(path:&Path)->Self {
            Self{file:OpenOptions::new().write(true).create_new(true).custom_flags(0x100).open(path).unwrap(),buffer:[0;512],used:0,total:0,attempts:0}
        }
        fn drain(&mut self)->std::fmt::Result {
            if self.used!=0 {
                if !bounded_write(&mut self.file,&self.buffer[..self.used],&mut self.attempts){return Err(std::fmt::Error);}
                self.used=0;
            } Ok(())
        }
        fn finish(mut self){self.drain().unwrap();assert!(self.total<=8192);}
    }
    impl std::fmt::Write for ReceiptWriter {
        fn write_str(&mut self,text:&str)->std::fmt::Result {
            let next=self.total.checked_add(text.len()).ok_or(std::fmt::Error)?;
            if next>8192{return Err(std::fmt::Error);}
            self.total=next;let mut bytes=text.as_bytes();
            while !bytes.is_empty(){let n=(512-self.used).min(bytes.len());self.buffer[self.used..self.used+n].copy_from_slice(&bytes[..n]);self.used+=n;bytes=&bytes[n..];if self.used==512{self.drain()?;}}
            Ok(())
        }
    }
    fn path()->PathBuf {
        let id=CASE.fetch_add(1,Ordering::Relaxed);
        let name=format!("completion-{id}.bin");assert!(name.capacity()<=128);
        let p=PathBuf::from(std::env::var_os("TMPDIR").unwrap()).join(name);assert!(p.capacity()<=512);p
    }
    fn custody(path:&Path,c:Custody){
        let mut out=ReceiptWriter::create(path);
        write!(out,"{{\"dev\":{},\"ino\":{},\"mode\":{},\"len\":{},\"mtime_sec\":{},\"mtime_nsec\":{},\"ctime_sec\":{},\"ctime_nsec\":{}}}\n",c.dev,c.ino,c.mode,c.len,c.mtime_sec,c.mtime_nsec,c.ctime_sec,c.ctime_nsec).unwrap();out.finish();
    }
    fn start(path:&Path)->DispatchGuard {
        let file=OpenOptions::new().write(true).create_new(true).custom_flags(0x100).open(path).unwrap();
        {let m=file.metadata().unwrap();assert!(m.is_file());assert_eq!(m.len(),0);custody(&path.with_extension("initial.json"),Custody::from_metadata(&m));}
        let h=header(4096,49,[[7;32];4]).unwrap();
        let writer=Writer::new(file,4096,49,24,&h).unwrap();begin(writer).unwrap()
    }
    fn rows(path:&Path)->Vec<Record>{
        assert!(std::fs::metadata(path).unwrap().len()<=16384);
        let b=std::fs::read(path).unwrap();assert!(b.len()>=1024);assert_eq!((b.len()-1024)%128,0);
        b[512..b.len()-512].chunks_exact(128).map(|x|Record::decode(x.try_into().unwrap())).collect()
    }
    fn usage_keys(out:&mut ReceiptWriter,u:&SwiftRunUsage){
        write!(out,"{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}\n",
            u.reservations,u.live,u.cache_work,u.execution_work,u.instruction_fuel,u.instructions,u.host_calls,u.cleanup_invariant,u.deadline_ms,u.deadline_origin,u.deadline_overshoot_micros,
            u.validation.input_visible_bytes,u.validation.source_bytes,u.validation.metadata_reserved,u.validation.scratch_reserved,u.validation.metadata_peak_reserved,u.validation.scratch_peak_reserved,u.validation.total_peak_reserved,u.validation.work_used,u.validation.deadline_ms).unwrap();
        assert!(u.wasi.is_none());
    }
    fn failure_keys(out:&mut ReceiptWriter,f:&SwiftRunFailure){
        write!(out,"{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}\n",f.stage,f.kind,f.code,f.function,f.offset,f.resource,f.attempted,f.limit,f.observed_capacity,f.deadline_origin,f.wasi_failure,f.guest_exit).unwrap();
        usage_keys(out,&f.at_failure);if let Some(ref u)=f.after_cleanup{usage_keys(out,u);}
    }
    struct Outcome {
        original:Option<SwiftRunFailure>,before:SwiftRunUsage,final_usage:SwiftRunUsage,
        cache:SwiftCacheUsage,cleanup:Option<SwiftRunFailure>,foreign:Option<SwiftRunUsage>,
        stats:AllocationStats,token:[u64;2],
    }
    fn persist(path:&Path,o:&Outcome){
        // Called only after End and quiescent retirement. TLS Option storage is
        // still fully charged; no formatter or receipt buffer escapes its scope.
        {let mut out=ReceiptWriter::create(&path.with_extension("original.txt"));write!(out,"original_failure={:?}\noriginal_final_usage={:?}\n",o.original,o.final_usage).unwrap();out.finish();}
        {let mut out=ReceiptWriter::create(&path.with_extension("details.txt"));write!(out,"before={:?}\ncache={:?}\ncleanup={:?}\nforeign={:?}\nallocations={:?}\ntoken={:?}\n",o.before,o.cache,o.cleanup,o.foreign,o.stats,o.token).unwrap();out.finish();}
        {let mut out=ReceiptWriter::create(&path.with_extension("semantic.txt"));
            if let Some(ref f)=o.original{failure_keys(&mut out,f);}usage_keys(&mut out,&o.before);usage_keys(&mut out,&o.final_usage);
            if let Some(ref f)=o.cleanup{failure_keys(&mut out,f);}if let Some(ref u)=o.foreign{usage_keys(&mut out,u);}
            write!(out,"{:?}|{:?}|{:?}\n",o.cache,o.stats,o.token).unwrap();out.finish();}
    }
    fn close(enabled:Option<DispatchGuard>,path:&Path,u:&SwiftRunUsage,f:Option<&SwiftRunFailure>)->Option<EndReceipt>{
        enabled.map(|g|{phase(5,(u.cache_work,u.instructions));let receipt=g.end(footer(u,f));retire_after_quiescence();if let Some(m)=receipt.custody{custody(&path.with_extension("final.json"),m);}receipt})
    }
    fn consume(mut enabled:Option<DispatchGuard>,cache:SwiftFunctionCache,mut c:RuntimeControl,f:&SwiftRunFailure)->(SwiftRunUsage,Option<SwiftRunFailure>,Option<DispatchGuard>){
        if enabled.is_some(){ordered_observer::failure(f,true);phase(4,c.ordered_coordinates());}
        let call=||super::cleanup(cache,&mut c,None);
        let cleanup=if let Some(g)=enabled.as_mut(){g.dispatch(call)}else{call()};
        let u=c.finish_owned_cleanup(None);assert_eq!(u.reservations.combined.current,0);assert_eq!(u.reservations.live_tickets,0);assert_eq!(u.live.cache_entries.current,0);assert_eq!(u.live.active_pins.current,0);
        (u,cleanup,enabled)
    }
    fn parity(a:&Path,b:&Path){assert_eq!(std::fs::read(a.with_extension("semantic.txt")).unwrap(),std::fs::read(b.with_extension("semantic.txt")).unwrap());}

    #[test]fn ordered_completion_publication_cancel_actual_result_and_prefix(){
        fn run(on:bool)->PathBuf{
            let path=path();let (outcome,receipt)={let bytes=fixture(0,&[0,0x0b],100);let(mut c,mut cache)=new(&bytes,SwiftRunBudget::default());let mut enabled=on.then(||start(&path));
            hooks(Hooks{pause:Some(CacheStep::Publication),cancel_pause:true,..Hooks::default()});
            let (actual,stats)=measure(||{let mut call=||pin(&mut cache,&mut c,34,None);if let Some(g)=enabled.as_mut(){g.dispatch(call)}else{call()}});
            let f=actual.err().unwrap();hooks(Hooks::default());assert_eq!(f.kind,SwiftRunFailureKind::Cancelled);assert_eq!(f.code,"swift_run_cancelled");assert_eq!(f.stage,SwiftRunStage::Cache);assert_eq!(f.function,Some(34));
            let before=c.usage(None);let snapshot=cache.usage();assert_eq!(snapshot.decodes,0);assert_eq!(snapshot.active_pins,0);
            let(final_usage,cleanup,enabled)=consume(enabled,cache,c,&f);let receipt=close(enabled,&path,&final_usage,Some(&f));
            (Outcome{original:Some(f),before,final_usage,cache:snapshot,cleanup,foreign:None,stats,token:[0;2]},receipt)};persist(&path,&outcome);
            if let Some(r)=receipt{assert_eq!(r.flags,0);let records=rows(&path);assert!(records.iter().any(|x|x.0[1]==10));assert!(!records.iter().any(|x|x.0[1]==11));assert!(records.iter().any(|x|x.0[1]==14&&x.0[3]>0&&x.0[13..16]==[2,1,2]));assert!(records.iter().any(|x|x.0[1]==14&&x.0[3]==0));}
            path
        }let off=run(false);let on=run(true);parity(&off,&on);println!("COMPLETION publication originalParity=true stream={} fullReplayAccepted=false",on.display());
    }

    #[test]fn ordered_completion_release_wrong_owner_and_stale_original_errors(){
        fn run(on:bool,stale:bool)->PathBuf{
            let path=path();let (outcome,receipt)={let bytes=fixture(0,&[0,0x0b],100);let(mut c,mut cache)=new(&bytes,SwiftRunBudget::default());let mut enabled=on.then(||start(&path));
            let p=if let Some(g)=enabled.as_mut(){g.dispatch(||pin(&mut cache,&mut c,34,None).unwrap())}else{pin(&mut cache,&mut c,34,None).unwrap()};let token=inspection::elision_pin_parts(&p);
            let (f,before,snapshot,stats,cleanup,final_usage,enabled)=if stale{
                let duplicate=inspection::stale(&p);cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();
                let count=on.then(stored_for_fixture);
                let(actual,stats)=measure(||cache.release(duplicate,&mut c,None));if let Some(n)=count{assert_eq!(stored_for_fixture(),n);}let err=actual.err().unwrap();let f=err.failure;let returned=err.into_pin();assert_eq!(inspection::elision_pin_parts(&returned),token);drop(returned);
                assert_eq!(f.code,"stale_pin");let before=c.usage(None);let snapshot=cache.usage();assert_eq!(snapshot.active_pins,0);
                let(u,cleanup,enabled)=consume(enabled,cache,c,&f);(f,before,snapshot,stats,cleanup,u,enabled)
            }else{
                let(mut foreign,mut other)=new(&bytes,SwiftRunBudget::default());let baseline=other.usage();
                let count=on.then(stored_for_fixture);
                let(actual,stats)=measure(||other.release(p,&mut foreign,None));if let Some(n)=count{assert_eq!(stored_for_fixture(),n);}let err=actual.err().unwrap();let f=err.failure;let returned=err.into_pin();assert_eq!(inspection::elision_pin_parts(&returned),token);assert_eq!(other.usage(),baseline);
                assert_eq!(f.code,"wrong_cache_owner");let before=foreign.usage(None);let snapshot=other.usage();
                // The original valid token is returned intact and released only
                // against its own original cache/control. No stale authority is reused.
                cache.release(returned,&mut c,None).map_err(|e|e.failure).unwrap();if let Some(n)=count{assert_eq!(stored_for_fixture(),n+1);}finish(cache,c);
                let(u,cleanup,enabled)=consume(enabled,other,foreign,&f);(f,before,snapshot,stats,cleanup,u,enabled)
            };
            assert_eq!(f.kind,SwiftRunFailureKind::Invariant);assert_eq!(f.stage,SwiftRunStage::Cache);assert!(f.function.is_none());assert!(f.offset.is_none());
            let receipt=close(enabled,&path,&final_usage,Some(&f));(Outcome{original:Some(f),before,final_usage,cache:snapshot,cleanup,foreign:None,stats,token},receipt)};persist(&path,&outcome);
            if let Some(r)=receipt{assert_eq!(r.flags,CODE);assert!(r.stored>=8);let records=rows(&path);assert!(records.is_empty());assert_eq!(std::fs::metadata(&path).unwrap().len(),1024);println!("COMPLETION releaseInvalid bufferedStored={} serializedRecords=0 partialBufferDiscarded=true footerStoredMismatch=true",r.stored);}
            path
        }for stale in [false,true]{let off=run(false,stale);let on=run(true,stale);parity(&off,&on);println!("COMPLETION release stale={stale} originalParity=true stream={} flags=CODE fullReplayAccepted=false",on.display());}
    }

    #[test]fn ordered_completion_evict_taken_foreign_ticket_actual_refund_failure(){
        fn run(on:bool)->PathBuf{
            let path=path();let (outcome,receipt)={let bytes=fixture(0,&[0,0x0b],100);let(mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_entries:1,..SwiftRunBudget::default()});let mut enabled=on.then(||start(&path));
            let p=if let Some(g)=enabled.as_mut(){g.dispatch(||pin(&mut cache,&mut c,34,None).unwrap())}else{pin(&mut cache,&mut c,34,None).unwrap()};let token=inspection::elision_pin_parts(&p);cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();
            // Four real warm hits/releases place EvictTaken at record32, which
            // naturally flushes before the later unknown refund code latches.
            for _ in 0..4{let q=if let Some(g)=enabled.as_mut(){g.dispatch(||pin(&mut cache,&mut c,34,None).unwrap())}else{pin(&mut cache,&mut c,34,None).unwrap()};cache.release(q,&mut c,None).map_err(|e|e.failure).unwrap();}
            if on{assert_eq!(stored_for_fixture(),25);assert_eq!(std::fs::metadata(&path).unwrap().len(),512);}
            let(mut foreign,proof)=adopt(&bytes,SwiftRunBudget::default());let foreign_ticket=foreign.admit(SwiftReservationCategory::Cache,1,cache_cursor()).unwrap();let displaced=inspection::replace_entry_ticket(&mut cache,foreign_ticket);
            let(actual,stats)=measure(||{let mut call=||pin(&mut cache,&mut c,35,None);if let Some(g)=enabled.as_mut(){g.dispatch(call)}else{call()}});let f=actual.err().unwrap();
            assert_eq!(f.code,"swift_run_release_owner");assert_eq!(f.kind,SwiftRunFailureKind::Invariant);assert_eq!(f.stage,SwiftRunStage::Cleanup);assert!(f.function.is_none());assert!(f.offset.is_none());
            let snapshot=cache.usage();assert_eq!(snapshot.evictions,0);assert_eq!(snapshot.decodes,1);assert_eq!(snapshot.active_pins,0);let before=c.usage(None);
            if enabled.is_some(){ordered_observer::failure(&f,true);phase(4,c.ordered_coordinates());}
            // Original decoded storage was destroyed by drop_reserved before
            // foreign-owner rejection. Consume the displaced valid ticket once.
            c.drop_reserved((),displaced).unwrap();
            let call=||super::cleanup(cache,&mut c,None);let cleanup=if let Some(g)=enabled.as_mut(){g.dispatch(call)}else{call()};let final_usage=c.finish_owned_cleanup(None);assert_eq!(final_usage.reservations.combined.current,0);assert_eq!(final_usage.reservations.live_tickets,0);assert_eq!(final_usage.live.cache_entries.current,0);assert_eq!(final_usage.live.active_pins.current,0);
            foreign.drop_proof(proof).unwrap();let quarantine=foreign.finish_owned_cleanup(None);assert_eq!(quarantine.reservations.cache.current,1);assert_eq!(quarantine.reservations.combined.current,1);assert_eq!(quarantine.reservations.live_tickets,1);
            let receipt=close(enabled,&path,&final_usage,Some(&f));(Outcome{original:Some(f),before,final_usage,cache:snapshot,cleanup,foreign:Some(quarantine),stats,token},receipt)};persist(&path,&outcome);
            if let Some(r)=receipt{assert_eq!(r.flags,CODE);assert_eq!(r.stored,32);let records=rows(&path);assert_eq!(records.len(),32);assert_eq!(std::fs::metadata(&path).unwrap().len(),5120);let last=records.iter().position(|x|x.0[1]==7).unwrap();assert_eq!(last,31);assert_eq!(records[last-1].0[1],6);assert!(!records[last+1..].iter().any(|x|[8,9,10,11,14].contains(&x.0[1])));assert_eq!(records.iter().filter(|x|x.0[1]==11).count(),5);}
            path
        }let off=run(false);let on=run(true);parity(&off,&on);println!("COMPLETION evictTaken originalParity=true stream={} flags=CODE foreign_quarantine_bytes=1 foreign_quarantine_tickets=1 fullReplayAccepted=false",on.display());
    }

    #[test]fn ordered_completion_guard_drop_actual_hook_refusal(){
        let path=path();let bytes=fixture(0,&[0,0x0b],100);let(mut c,mut cache)=new(&bytes,SwiftRunBudget::default());let mut g=start(&path);
        let p=g.dispatch(||pin(&mut cache,&mut c,34,None).unwrap());drop(g);let before=std::fs::read(&path).unwrap();let latched=flags();
        cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();assert_eq!(before,std::fs::read(&path).unwrap());assert_eq!(flags(),latched);assert_eq!(state()&((1<<32)-1),0);finish(cache,c);
        println!("COMPLETION guardDrop noFooter=true actualReleaseRefused=true stream={}",path.display());
    }

    #[allow(dead_code)]
    struct CallbackValues {
        payload:[u64;11],coordinates:(u64,u64),record:Record,body:crate::experimental::descriptors::FunctionSpanView<'static>,
        gate_before:u64,lifetime:u64,operation:Option<u64>,sticky:u32,
        gate:&'static AtomicU64,latch:&'static std::sync::atomic::AtomicU32,owner:&'static Cell<u64>,
        cell:&'static std::cell::RefCell<Option<Writer<File>>>,
        borrow_result:Result<std::cell::RefMut<'static,Option<Writer<File>>>,std::cell::BorrowMutError>,
        borrow:std::cell::RefMut<'static,Option<Writer<File>>>,writer:&'static mut Writer<File>,
        file:&'static mut File,bytes:&'static[u8],offset:usize,retry:std::ops::Range<usize>,
        result:std::io::Result<usize>,error:std::io::Error,error_kind:std::io::ErrorKind,
        words:std::slice::Iter<'static,u64>,encoded_word:[u8;8],index:usize,
        record_borrow:&'static Record,encode_output:&'static mut[u8;128],checked:Option<u64>,
        slice:&'static[u8],attempts:&'static mut u64,failure:&'static SwiftRunFailure,
        source_code:&'static str,source_id:u64,phase:&'static mut CacheOperationPhase<'static>,cache:&'static mut SwiftFunctionCache,
    }
    #[allow(dead_code)]
    struct BeginValues {references:[usize;16],results:[Option<u64>;4],scalars:[u64;8],guard_return:Option<DispatchGuard>}
    #[allow(dead_code)]
    struct FormatterValues {
        arguments:std::fmt::Arguments<'static>,twenty_argument_roles:[(usize,usize);20],scalars:[usize;16],borrows:[usize;8],
        formatter:std::fmt::Formatter<'static>,write_result:std::io::Result<usize>,write_error:std::io::Error,
        error_kind:std::io::ErrorKind,range:std::ops::Range<usize>,checked:Option<u64>,
        receiver:&'static mut ReceiptWriter,text:&'static str,bytes:&'static[u8],format_result:std::fmt::Result,
    }
    #[test]fn ordered_completion_complete_logical_phase_inventory(){
        use std::mem::{size_of,align_of,offset_of};
        let tls=size_of::<std::cell::RefCell<Option<Writer<File>>>>();
        let atomics=3*size_of::<AtomicU64>()+size_of::<std::sync::atomic::AtomicU32>()+size_of::<Cell<u64>>()+2*size_of::<AtomicU64>();
        let common=tls+atomics+502;
        let writer=size_of::<Writer<File>>();let moved=size_of::<Option<Writer<File>>>();let guard=size_of::<DispatchGuard>();let receipt=size_of::<EndReceipt>();
        let metadata=size_of::<std::fs::Metadata>()+2*size_of::<std::io::Result<std::fs::Metadata>>()+size_of::<&std::fs::Metadata>();
        // 1024 conservatively covers the finite receipt format literals. The
        // packet's independent literal scanner checks actual UTF8 bytes <=1024.
        let literals=1024usize;let path=512usize;let callback=size_of::<CallbackValues>();let outputs=size_of::<Outcome>();
        let phases=[
            ("path-construction",common+4*path+128+size_of::<BeginValues>()+literals),
            ("initial-metadata-receipt",common+2*path+metadata+size_of::<ReceiptWriter>()+size_of::<FormatterValues>()+literals),
            ("header-construction",common+path+4*512+128+size_of::<BeginValues>()+literals),
            // Charge both complete local/return or argument/Some-move owners,
            // in addition to complete TLS storage even when its value is None.
            ("writer-new-and-return",common+path+512+2*writer+size_of::<BeginValues>()+literals),
            ("begin-and-failed-begin-disposal",common+path+512+writer+moved+size_of::<BeginValues>()+literals),
            ("callback",common+path+guard+3*callback+2*size_of::<Result<SwiftFunctionPin,SwiftRunFailure>>()+size_of::<SwiftRunFailure>()+size_of::<SwiftCacheUsage>()+size_of::<AllocationStats>()+size_of::<ReservationTicket>()+literals),
            ("release-result-and-returned-error",common+path+guard+3*callback+2*size_of::<Result<(),SwiftReleaseFailure>>()+size_of::<SwiftRunFailure>()+size_of::<SwiftFunctionPin>()+size_of::<SwiftCacheUsage>()+size_of::<AllocationStats>()+literals),
            ("consuming-cleanup-return",common+path+guard+3*size_of::<Option<SwiftRunFailure>>()+3*size_of::<SwiftRunUsage>()+size_of::<SwiftRunFailure>()+size_of::<SwiftCacheUsage>()+size_of::<AllocationStats>()+literals),
            ("footer",common+path+guard+outputs+5*512+128+receipt+metadata+7*size_of::<usize>()+literals),
            ("retirement",common+path+guard+outputs+moved+512+receipt+metadata+23*size_of::<usize>()+literals),
            // Each actual run assembles Outcome inside an explicit block, ends
            // all original Copy-output bindings, then calls persist. Charge
            // both copies during assembly, before any formatter is created.
            ("output-assembly",common+path+2*outputs+2*receipt+literals),
            ("final-custody-serialization",common+2*path+outputs+size_of::<ReceiptWriter>()+size_of::<FormatterValues>()+2*receipt+metadata+literals),
            ("serialization",common+2*path+outputs+size_of::<ReceiptWriter>()+size_of::<FormatterValues>()+2*receipt+literals),
            ("formatter-boundary-control",common+2*path+4096+size_of::<ReceiptWriter>()+size_of::<FormatterValues>()+literals),
            ("abnormal-guard-drop",common+path+guard+moved+size_of::<BeginValues>()+size_of::<Result<SwiftFunctionPin,SwiftRunFailure>>()+literals),
            ("after-drop-refusal-and-file-comparison",common+path+2*512+2*size_of::<Vec<u8>>()+guard+size_of::<SwiftFunctionPin>()+size_of::<BeginValues>()+literals),
        ];
        println!("COMPLETION_LAYOUT writer={writer} writer_align={} writer_buffer_offset={} writer_sink_offset={} tls={tls} atomics={atomics} callback={callback} outputs={outputs} begin={} formatter={} receipt={receipt} metadata={metadata} receipt_writer={} pin_result={} release_result={} failure={} usage={} option_wasi={} supported_code_literals=502 receipt_literal_cap=1024",align_of::<Writer<File>>(),offset_of!(Writer<File>,buffer),offset_of!(Writer<File>,sink),size_of::<BeginValues>(),size_of::<FormatterValues>(),size_of::<ReceiptWriter>(),size_of::<Result<SwiftFunctionPin,SwiftRunFailure>>(),size_of::<Result<(),SwiftReleaseFailure>>(),size_of::<SwiftRunFailure>(),size_of::<SwiftRunUsage>(),size_of::<Option<WasiUsage>>());
        for(name,total)in phases{println!("COMPLETION_PHASE {name}={total} cap=16384");assert!(total<=16384,"{name} exceeds unchanged logical ceiling: {total}");}
    }
    #[test]fn ordered_completion_receipt_formatter_exact_cap_refuses_one_more_byte(){
        let path=path();let text=[b'x';4096];let text=std::str::from_utf8(&text).unwrap();let mut out=ReceiptWriter::create(&path);
        out.write_str(text).unwrap();out.write_str(text).unwrap();assert_eq!(out.total,8192);assert_eq!(out.attempts,16);
        assert!(out.write_str("x").is_err());assert_eq!(out.total,8192);out.finish();assert_eq!(std::fs::metadata(&path).unwrap().len(),8192);
    }
}
