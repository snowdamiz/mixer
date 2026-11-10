#![cfg(feature = "experimental-swift-reactor")]
#[path = "swift_reactor_validation_fixture.rs"] mod fixture;
#[path = "experimental_swift_command.rs"] mod r110_claims;
use fixture::*;
use mixer_vm::{Cancellation, Limits, Module, Type};
use mixer_vm::experimental_swift_reactor::*;
use mixer_vm::experimental_wasi::{WasiBudget, WasiGrants};
use std::{fs, io::{self, Write}, path::PathBuf};

fn command(body: Vec<u8>) -> Fixture {
    let mut f = Fixture::default();
    f.memory = vec![1, 0, 1]; f.table = vec![1, 0x70, 1, 0, 0];
    f.exports = vec![(b"memory".to_vec(), 2, 0), (b"_start".to_vec(), 0, 34)];
    f.bodies[0] = body; f
}
fn proof(f: &Fixture) -> ValidatedSwiftCommand {
    validate_swift_command(&f.bytes(), SwiftValidationBudget::default(), &Cancellation::default()).unwrap()
}
fn clean(r: &SwiftCommandReport) {
    assert!(r.cleanup_completed, "{r:?}");
    let u = r.after_cleanup.unwrap(); let s = u.reservations;
    assert_eq!([s.retained_source.current,s.retained_metadata.current,s.cache.current,
        s.state.current,s.wasi.current,s.shared.current,s.construction.current,s.combined.current,s.live_tickets], [0;9]);
    assert_eq!([u.live.frames.current,u.live.active_pins.current,u.live.values.current,
        u.live.controls.current,u.live.memory_pages.current], [0;5]);
    assert_eq!(u.cleanup_invariant, None);
}
fn run(f: &Fixture, run: SwiftRunBudget, wasi: WasiBudget, cancel: Cancellation) -> (SwiftCommandReport, Vec<u8>) {
    let mut out=vec![];
    let r=execute_swift_command(proof(f),run,WasiGrants{stdout:true,..Default::default()},wasi,cancel,&mut out,&mut vec![]);
    (r,out)
}
#[test] fn control_whole_validation_last_body_above_old_ceiling() {
    let mut f=command(vec![0,0x0b]);
    f.function_types=vec![34;80_514]; f.bodies=vec![vec![0,0x0b];80_514];
    // i64.add consumes an actual i32 after unreachable; polymorphism cannot hide it.
    f.bodies[80_513]=vec![0,0,0x41,0,0x7c,0x0b];
    let e=validate_swift_command(&f.bytes(),Default::default(),&Cancellation::default()).err().unwrap();
    assert_eq!(e.function,Some(80_547));
    println!("late_unreachable_type_error={e:?}");
}
#[test] fn control_unknown_import_export_flags_and_fixed_abi() {
    let base=command(vec![0,0x0b]);
    let mut cases=vec![];
    let mut f=command(vec![0,0x0b]);f.imports[0].1=b"unknown".to_vec();cases.push(("unknown_import",f));
    let mut f=command(vec![0,0x0b]);f.imports.swap(0,1);cases.push(("import_order",f));
    let mut f=command(vec![0,0x0b]);f.exports[1].2=32;cases.push(("imported_start",f));
    let mut f=command(vec![0,0x0b]);f.exports[1].0=b"_initialize".to_vec();cases.push(("wrong_start_name",f));
    let mut f=command(vec![0,0x0b]);f.exports[1].1=2;cases.push(("wrong_start_kind",f));
    let mut f=command(vec![0,0x0b]);f.exports.push((b"extra".to_vec(),0,34));cases.push(("extra_export",f));
    let mut f=command(vec![0,0x0b]);f.memory=vec![1,2,1,1];cases.push(("shared_memory_flags",f));
    let mut f=command(vec![0,0x0b]);f.table=vec![1,0x70,2,0,0];cases.push(("table_flags",f));
    let mut f=command(vec![0,0x0b]);f.types[34]=signature(&[Type::I32],&[]);cases.push(("start_parameter",f));
    for (name,f) in cases {
        let e=validate_swift_command(&f.bytes(),Default::default(),&Cancellation::default()).err().unwrap();
        println!("refused={name}; code={}; kind={:?}",e.code,e.kind);
    }
    assert!(Module::decode(&base.bytes(),&Limits::default()).is_err());
    assert!(validate_swift_reactor(&base.bytes(),Default::default(),&Cancellation::default()).is_err());
    assert!(validate_swift_reactor(&Fixture::default().bytes(),Default::default(),&Cancellation::default()).is_ok());
    println!("original_fixed_export_ABI_still_admitted=true");
}
fn writer(text: &[u8]) -> Fixture {
    let mut f=command(vec![0,0x41,1,0x41,0,0x41,1,0x41,16,0x10,20,0x10,32,0x0b]);
    let mut data=vec![0;32];data[..4].copy_from_slice(&32u32.to_le_bytes());
    data[4..8].copy_from_slice(&(text.len() as u32).to_le_bytes());data.extend(text);
    let mut segment=vec![0,0x41,0,0x0b];segment.extend(uint(data.len() as u32));segment.extend(data);f.data=vec![segment];f
}
#[test] fn control_output_literal_exit_caps_and_sink_errors() {
    for text in [b"ALPHA".as_slice(),b"omega".as_slice()] {
        let (r,out)=run(&writer(text),Default::default(),Default::default(),Cancellation::default());
        assert!(r.succeeded(),"{r:?}");assert_eq!(out,text);clean(&r);
    }
    let (r,out)=run(&writer(b"ALPHA"),Default::default(),WasiBudget{log_bytes:4,..Default::default()},Cancellation::default());
    assert!(!r.succeeded());assert!(out.is_empty());assert_eq!(r.terminal.unwrap().guest_exit,Some(51));clean(&r);
    let f=command(vec![0,0x41,7,0x10,32,0x0b]);
    let (r,_)=run(&f,Default::default(),Default::default(),Cancellation::default());
    assert_eq!(r.terminal.unwrap().guest_exit,Some(7));assert!(!r.succeeded());clean(&r);
    struct Broken;impl Write for Broken {fn write(&mut self,_:&[u8])->io::Result<usize>{Err(io::ErrorKind::Other.into())}fn flush(&mut self)->io::Result<()>{Ok(())}}
    let r=execute_swift_command(proof(&writer(b"ALPHA")),Default::default(),WasiGrants{stdout:true,..Default::default()},Default::default(),Cancellation::default(),&mut Broken,&mut vec![]);
    assert!(!r.succeeded());assert!(r.output_error);clean(&r);
}
fn errno_exit(index: u8, args: &[u8]) -> Fixture {
    let mut body=vec![0];body.extend(args);body.extend([0x10,index,0x10,32,0x0b]);command(body)
}
#[test] fn control_empty_environment_no_preopens_or_filesystem() {
    // No filesystem, preopens or polling implementation is substituted by success.
    for (index,args,errno) in [(13,vec![0x41,3,0x41,0],8),
        (25,vec![0x41,3,0x41,0,0x41,0,0x41,0,0x41,0,0x42,0,0x42,0,0x41,0,0x41,0],8),
        (31,vec![0x41,0,0x41,0,0x41,0,0x41,0],58)] {
        let (r,_)=run(&errno_exit(index,&args),Default::default(),Default::default(),Cancellation::default());
        assert_eq!(r.terminal.unwrap().guest_exit,Some(errno),"{r:?}");clean(&r);
    }
    // environ_sizes_get writes both zeroes over nonzero data; OR them into exit code.
    let mut f=command(vec![0,0x41,0,0x41,4,0x10,3,0x1a,0x41,0,0x28,2,0,0x41,4,0x28,2,0,0x72,0x10,32,0x0b]);
    f.data=vec![vec![0,0x41,0,0x0b,8,1,1,1,1,1,1,1,1]];
    let (r,_)=run(&f,Default::default(),Default::default(),Cancellation::default());
    assert!(r.succeeded(),"{r:?}");clean(&r);
}
#[test] fn control_coupled_frames_pins_and_narrowing_only_runtime() {
    let f=command(vec![0,0x10,35,0x0b]);
    for budget in [SwiftRunBudget{frames:1,..Default::default()},
        SwiftRunBudget{active_pins:1,..Default::default()},
        SwiftRunBudget{cache_entries:1,..Default::default()},
        SwiftRunBudget{cache_bytes:1,..Default::default()},
        SwiftRunBudget{cache_work:0,..Default::default()},
        SwiftRunBudget{execution_work:0,..Default::default()},
        SwiftRunBudget{frames:65,..Default::default()},
        SwiftRunBudget{active_pins:65,..Default::default()}] {
        let (r,_)=run(&f,budget,Default::default(),Cancellation::default());
        assert!(!r.succeeded(),"budget={budget:?}; {r:?}");clean(&r);
        println!("bounded_failure={:?}; peak_tickets={}",r.terminal.unwrap().kind,r.after_cleanup.unwrap().reservations.peak_tickets);
    }
    let (r,_)=run(&writer(b"host-call-bound"),SwiftRunBudget{host_calls:0,..Default::default()},Default::default(),Cancellation::default());
    assert!(!r.succeeded());clean(&r);
}
#[test] fn control_cancel_deadline_resource_failure_release_and_uncertainty() {
    let f=command(vec![0,0x0b]);
    let cancelled=Cancellation::default();cancelled.cancel();
    let (r,_)=run(&f,Default::default(),Default::default(),cancelled);
    assert_eq!(r.terminal.unwrap().kind,SwiftRunFailureKind::Cancelled);assert!(!r.succeeded());clean(&r);
    let (r,_)=run(&f,SwiftRunBudget{deadline_ms:0,..Default::default()},Default::default(),Cancellation::default());
    assert!(!r.succeeded());clean(&r);
    let (r,_)=run(&f,SwiftRunBudget{combined_bytes:1,..Default::default()},Default::default(),Cancellation::default());
    assert!(!r.succeeded());clean(&r);
    // Concurrent native sink cancellation is observed by cleanup without inventing a pass.
    struct CancelSink(Cancellation);impl Write for CancelSink {fn write(&mut self,b:&[u8])->io::Result<usize>{self.0.cancel();Ok(b.len())}fn flush(&mut self)->io::Result<()>{Ok(())}}
    let c=Cancellation::default();let mut sink=CancelSink(c.clone());
    let r=execute_swift_command(proof(&writer(b"cancel")),Default::default(),WasiGrants{stdout:true,..Default::default()},Default::default(),c,&mut sink,&mut vec![]);
    println!("post_output_cancel_report={r:?}");
    // Cleanup is allowed to finish after guest termination; no success contract is imposed on native sink time.
    assert!(r.after_cleanup.is_some() || !r.cleanup_completed);if r.cleanup_completed {clean(&r);}
}
#[test] fn frozen_r106_and_data_mutation() {
    let dir=PathBuf::from(std::env::var_os("MIXER_R115_SCRATCH").unwrap());
    for (name,oracle) in [("frozen","native"),("literal-mutated","mutated-expected")] {
        let bytes=fs::read(dir.join(format!("{name}.wasm"))).unwrap();
        let old=validate_swift_reactor(&bytes,Default::default(),&Cancellation::default()).err().unwrap();
        assert_eq!(old.code,"profile_vector_limit");assert_eq!(old.limit,79_966);
        assert!(Module::decode(&bytes,&Limits::default()).is_err());
        let c=Cancellation::default();let p=validate_swift_command(&bytes,Default::default(),&c).unwrap();
        assert_eq!(p.observations().validated_bodies,80_514);assert_eq!(p.observations().instructions,6_546_069);
        println!("module={name}; entry={}; observations={:?}; validation={:?}",p.entry_function(),p.observations(),p.usage());
        let mut out=vec![];let mut err=vec![];
        let r=execute_swift_command(p,Default::default(),WasiGrants{stdout:true,stderr:true,secure_random:true,realtime:true,monotonic:true},Default::default(),c,&mut out,&mut err);
        fs::write(dir.join(format!("{name}.stdout")),&out).unwrap();fs::write(dir.join(format!("{name}.stderr")),&err).unwrap();
        println!("module={name}; report={r:?}");
        assert!(r.succeeded(),"{r:?}");assert_eq!(r.terminal.unwrap().guest_exit,Some(0));clean(&r);
        assert_eq!(out,fs::read(dir.join(format!("{oracle}.stdout"))).unwrap());assert!(err.is_empty());
    }
}
