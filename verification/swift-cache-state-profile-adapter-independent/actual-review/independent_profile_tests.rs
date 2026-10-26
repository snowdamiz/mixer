//! Independent actual-source controls; no replacement owner or writer loop.
use super::*;
use crate::experimental_swift_reactor::{validate_swift_reactor, SwiftValidationBudget};
use crate::Cancellation;
use std::fs::{self, OpenOptions};
use std::io::SeekFrom;
use std::path::PathBuf;

fn fixtures() -> PathBuf {
    PathBuf::from(std::env::var_os("MIXER_PROFILE_INDEPENDENT_FIXTURES").unwrap())
}
fn evidence() -> PathBuf {
    PathBuf::from(std::env::var_os("MIXER_PROFILE_EVIDENCE_DIR").unwrap())
}
fn owner(name: &str) -> ValidatedSwiftReactor {
    let bytes = fs::read(fixtures().join(format!("{name}.wasm"))).unwrap();
    validate_swift_reactor(&bytes, SwiftValidationBudget::default(), &Cancellation::default())
        .unwrap()
}
fn fresh(name: &str) -> File {
    OpenOptions::new().read(true).write(true).create_new(true)
        .open(evidence().join(name)).unwrap()
}
fn tuple(e: ProfileAdapterErrorV1) -> (u32,u32,u64,u64,u64) {
    (e.code,e.stage,e.offset,e.output_bytes,e.output_attempts)
}

#[test]
fn independent_all_rows_real_owners_and_file_bytes() {
    for name in ["minimum-abi29", "offset-leb-type129", "maximum-total80000-candidate"] {
        let wasm = fs::read(fixtures().join(format!("{name}.wasm"))).unwrap();
        let expected = fs::read(fixtures().join(format!("{name}.expected-row-body.bin"))).unwrap();
        let s = owner(name);
        let before = (s.usage(), format!("{:?}",s.observations()));
        let mut row_bytes = [0u8;32];
        let (_, stats) = super::super::allocation_tests::measure(|| {
            for absolute in 0..80_000 {
                encode(profile_row_v1(&s,absolute).unwrap(), &mut row_bytes);
                assert_eq!(&row_bytes, &expected[absolute as usize*32..absolute as usize*32+32]);
            }
        });
        assert_eq!(stats.attempts,0);
        let mut f = fresh(&format!("independent-{name}.rows"));
        let (result, stats) = super::super::allocation_tests::measure(|| write_profile_row_body_v1(&s,&mut f));
        let o = result.unwrap();
        assert_eq!(stats.attempts,0);
        assert_eq!((o.rows,o.output_bytes,o.output_attempts,o.reserved),(80000,2560000,625,0));
        assert_eq!(o.source_extent,wasm.len() as u64);
        assert_eq!(fs::read(evidence().join(format!("independent-{name}.rows"))).unwrap(),expected);
        assert_eq!(s.source(),wasm);
        assert_eq!((s.usage(),format!("{:?}",s.observations())),before);
        for n in [80000,u32::MAX] {
            assert_eq!(tuple(profile_row_v1(&s,n).unwrap_err()),(2,2,u64::from(n)*32,0,0));
        }
        f.seek(SeekFrom::Start(0)).unwrap();
        assert_eq!(tuple(write_profile_row_body_v1(&s,&mut f).unwrap_err()),(8,3,0,0,0));
        assert_eq!((s.usage(),format!("{:?}",s.observations())),before);
        println!("INDEPENDENT_ROWS name={name} rows=80000 bytes=2560000 attempts=625 imported={} defined={} types={} allocation_attempts=0",o.imported_functions,o.defined_functions,o.type_count);
    }
}

#[test]
fn independent_invalid_wasm_never_constructs_owner() {
    for name in ["refuse-swapped-import-order", "refuse-missing-import", "refuse-missing-body-end",
                 "refuse-invalid-type-index", "refuse-wrong-memory-minimum"] {
        let bytes = fs::read(fixtures().join(format!("{name}.wasm"))).unwrap();
        let result = validate_swift_reactor(&bytes,SwiftValidationBudget::default(),&Cancellation::default());
        assert!(result.is_err(), "unexpected owner for {name}");
        println!("INDEPENDENT_NO_OWNER name={name} error={:?}",result.err().unwrap());
    }
}

#[test]
fn independent_actual_file_admission_and_readonly_failure() {
    let s = owner("minimum-abi29");
    let mut f = fresh("independent-readonly.bin");
    drop(f);
    f = File::open(evidence().join("independent-readonly.bin")).unwrap();
    assert_eq!(tuple(write_profile_row_body_v1(&s,&mut f).unwrap_err()),(9,4,0,0,1));
    assert_eq!(f.metadata().unwrap().len(),0);
    assert_eq!(f.stream_position().unwrap(),0);
    let mut f = fresh("independent-nonempty.bin");
    f.write_all(b"retained-original").unwrap();
    f.seek(SeekFrom::Start(0)).unwrap();
    assert_eq!(tuple(write_profile_row_body_v1(&s,&mut f).unwrap_err()),(8,3,0,0,0));
    assert_eq!(fs::read(evidence().join("independent-nonempty.bin")).unwrap(),b"retained-original");
    let mut f = fresh("independent-offset.bin");
    f.seek(SeekFrom::Start(1)).unwrap();
    assert_eq!(tuple(write_profile_row_body_v1(&s,&mut f).unwrap_err()),(8,3,0,0,0));
    assert_eq!((f.metadata().unwrap().len(),f.stream_position().unwrap()),(0,1));
    let mut f = File::open(evidence()).unwrap();
    assert_eq!(tuple(write_profile_row_body_v1(&s,&mut f).unwrap_err()),(6,3,0,0,0));
    println!("INDEPENDENT_FILE readonly=9/4/0/0/1 nonempty=8/3/0/0/0 offset=8/3/0/0/0 directory=6/3/0/0/0");
}

#[derive(Clone)]
struct Schedule {
    name: String, code: u32, bytes: u64, attempts: u64, side_effect: usize,
    default: Vec<String>, overrides: Vec<(usize,Vec<String>)>,
}
fn schedules() -> Vec<Schedule> {
    let text = fs::read_to_string(evidence().join("writer-matrix.tsv")).unwrap();
    let mut rows: Vec<Schedule> = Vec::new();
    for line in text.lines() {
        let p: Vec<&str> = line.split('\t').collect();
        match p[0] {
            "CASE" => rows.push(Schedule{name:p[1].into(),code:p[2].parse().unwrap(),bytes:p[3].parse().unwrap(),
                attempts:p[4].parse().unwrap(),side_effect:p[5].parse().unwrap(),default:Vec::new(),overrides:Vec::new()}),
            "DEFAULT" => rows.last_mut().unwrap().default=p[1].split(',').map(String::from).collect(),
            "OVERRIDE" => rows.last_mut().unwrap().overrides.push((p[1].parse().unwrap(),p[2].split(',').map(String::from).collect())),
            _ => panic!("unknown schedule directive"),
        }
    }
    assert_eq!(rows.len(),29);
    rows
}

#[test]
fn independent_predeclared_writer_matrix_and_physical_files() {
    let s = owner("minimum-abi29");
    let expected = fs::read(fixtures().join("minimum-abi29.expected-row-body.bin")).unwrap();
    let before=(s.usage(),format!("{:?}",s.observations()));
    for case in schedules() {
        let mut f = fresh(&format!("matrix-{}.bin",case.name));
        admit_output(&mut f).unwrap();
        let (mut block,mut local,mut calls,mut acknowledged)=(0usize,0usize,0u64,0usize);
        let result=write_body(&s,|b| {
            assert_eq!(b.len(),4096-acknowledged%4096);
            let actions=case.overrides.iter().find(|(n,_)| *n==block).map(|(_,a)| a).unwrap_or(&case.default);
            let action=actions.get(local).expect("unspecified actual callback");
            assert_ne!(action,"F","forbidden 33rd actual callback");
            local+=1;calls+=1;
            assert!(local<=32 && calls<=20000);
            if calls==1 && case.side_effect!=0 {
                assert_eq!(f.write(&b[..case.side_effect]).unwrap(),case.side_effect);
            }
            match action.as_str() {
                "I" => Err(io::ErrorKind::Interrupted.into()),
                "E" => Err(io::Error::other("independent injected ordinary error")),
                "Z" => Ok(0),
                "O" => Ok(b.len()+1),
                _ => {
                    let n=if action=="R" { b.len() } else { action.strip_prefix("B:").unwrap().parse::<usize>().unwrap() };
                    if n<=b.len() {
                        assert_eq!(f.write(&b[..n]).unwrap(),n);
                        acknowledged+=n;
                        if n==b.len() {block+=1;local=0;}
                    }
                    Ok(n)
                }
            }
        });
        if case.code==0 {
            let o=result.unwrap();
            assert_eq!((o.output_bytes,o.output_attempts),(case.bytes,case.attempts),"{}",case.name);
        } else {
            assert_eq!(tuple(result.unwrap_err()),(case.code,4,case.bytes,case.bytes,case.attempts),"{}",case.name);
        }
        assert_eq!((acknowledged as u64,calls),(case.bytes,case.attempts));
        let physical=fs::read(evidence().join(format!("matrix-{}.bin",case.name))).unwrap();
        let physical_len=if case.side_effect!=0 {case.side_effect} else {case.bytes as usize};
        assert_eq!(physical,&expected[..physical_len],"{}",case.name);
        assert_eq!((s.usage(),format!("{:?}",s.observations())),before);
        println!("INDEPENDENT_MATRIX name={} code={} stage={} offset={} bytes={} attempts={} physical={}",
            case.name,case.code,if case.code==0 {0} else {4},case.bytes,case.bytes,case.attempts,physical_len);
    }
}

#[test]
fn independent_full_constructor_result_and_source_view_layouts() {
    use std::mem::{size_of as s,align_of as a};
    use crate::experimental_swift_reactor::{SwiftValidationFailure,SwiftReactorObservations};
    println!("INDEPENDENT_LAYOUT snapshot={} validation_result={} validation_error={} observations={} row_result={} writer_result={} row={} observation={} error={} alignment={} caller_constructor_and_owner={} optional_descriptor={} descriptor={} metadata_result={} metadata={} io_result={} io_error={} option_usize={} comparison_result={} try_from_int_error={} row_caller={} writer_caller={}",
        s::<ValidatedSwiftReactor>(),s::<Result<ValidatedSwiftReactor,SwiftValidationFailure>>(),s::<SwiftValidationFailure>(),
        s::<SwiftReactorObservations>(),s::<Result<ProfileRowV1,ProfileAdapterErrorV1>>(),s::<Result<ProfileRowsObservationV1,ProfileAdapterErrorV1>>(),
        s::<ProfileRowV1>(),s::<ProfileRowsObservationV1>(),s::<ProfileAdapterErrorV1>(),a::<ProfileAdapterErrorV1>(),
        s::<(Result<ValidatedSwiftReactor,SwiftValidationFailure>,ValidatedSwiftReactor)>(),
        s::<Option<crate::experimental::descriptors::FunctionSpanView<'_>>>(),s::<crate::experimental::descriptors::FunctionSpanView<'_>>(),
        s::<io::Result<std::fs::Metadata>>(),s::<std::fs::Metadata>(),s::<io::Result<usize>>(),s::<io::Error>(),s::<Option<usize>>(),
        s::<Result<u64,std::num::TryFromIntError>>(),s::<std::num::TryFromIntError>(),
        s::<(&ValidatedSwiftReactor,u32,Result<ProfileRowV1,ProfileAdapterErrorV1>,ProfileRowV1)>(),
        s::<(&ValidatedSwiftReactor,&mut File,Result<ProfileRowsObservationV1,ProfileAdapterErrorV1>,ProfileRowsObservationV1)>());
}
