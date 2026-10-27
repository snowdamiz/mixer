//! Independently encoded test modules. No fixture/model generator is imported.
use super::*;
use crate::{
    experimental_swift_reactor::{validate_swift_reactor, SwiftValidationBudget},
    Cancellation,
};
use std::fs::{self, OpenOptions};
use std::io::{Read, SeekFrom};
use std::path::PathBuf;

fn leb(mut value: u32) -> Vec<u8> {
    let mut out = Vec::new();
    loop {
        let b = (value & 127) as u8;
        value >>= 7;
        out.push(b | if value != 0 { 128 } else { 0 });
        if value == 0 {
            return out;
        }
    }
}
fn text(s: &str, out: &mut Vec<u8>) {
    out.extend(leb(s.len() as u32));
    out.extend(s.as_bytes());
}
fn section(module: &mut Vec<u8>, tag: u8, bytes: &[u8]) -> usize {
    module.push(tag);
    module.extend(leb(bytes.len() as u32));
    let start = module.len();
    module.extend(bytes);
    start
}
struct Encoded {
    bytes: Vec<u8>,
    offsets: Vec<usize>,
    bodies: Vec<Vec<u8>>,
    types: Vec<u32>,
}
fn module(count: usize, wide: bool) -> Encoded {
    assert!(count >= 29);
    // The selected ABI is written independently as names plus I32/I64 signatures.
    let abi = [
        ("args_get", "ii"),
        ("args_sizes_get", "ii"),
        ("environ_get", "ii"),
        ("environ_sizes_get", "ii"),
        ("clock_res_get", "ii"),
        ("clock_time_get", "ili"),
        ("fd_close", "i"),
        ("fd_fdstat_get", "ii"),
        ("fd_fdstat_set_flags", "ii"),
        ("fd_filestat_get", "ii"),
        ("fd_filestat_set_size", "il"),
        ("fd_filestat_set_times", "illi"),
        ("fd_pread", "iiili"),
        ("fd_prestat_get", "ii"),
        ("fd_prestat_dir_name", "iii"),
        ("fd_read", "iiii"),
        ("fd_readdir", "iiili"),
        ("fd_seek", "ilii"),
        ("fd_sync", "i"),
        ("fd_tell", "ii"),
        ("fd_write", "iiii"),
        ("path_create_directory", "iii"),
        ("path_filestat_get", "iiiii"),
        ("path_filestat_set_times", "iiiilli"),
        ("path_link", "iiiiiii"),
        ("path_open", "iiiiillii"),
        ("path_readlink", "iiiiii"),
        ("path_remove_directory", "iii"),
        ("path_rename", "iiiiii"),
        ("path_symlink", "iiiii"),
        ("path_unlink_file", "iii"),
        ("poll_oneoff", "iiii"),
        ("proc_exit", "i"),
        ("random_get", "ii"),
    ];
    let type_count = if wide { 130 } else { 36 };
    let mut bytes = b"\0asm\x01\0\0\0".to_vec();
    let mut custom = Vec::new();
    text("independent-profile-offset", &mut custom);
    custom.extend([0x5a; 150]);
    section(&mut bytes, 0, &custom);
    let mut payload = leb(type_count);
    for (name, params) in abi {
        payload.push(0x60);
        payload.extend(leb(params.len() as u32));
        for b in params.bytes() {
            payload.push(if b == b'i' { 0x7f } else { 0x7e });
        }
        payload.push(if name == "proc_exit" { 0 } else { 1 });
        if name != "proc_exit" {
            payload.push(0x7f);
        }
    }
    payload.extend([0x60, 0, 0, 0x60, 0, 1, 0x7f]);
    for _ in 36..type_count {
        payload.extend([0x60, 0, 0]);
    }
    section(&mut bytes, 1, &payload);
    payload = leb(34);
    for (i, (name, _)) in abi.iter().enumerate() {
        text("wasi_snapshot_preview1", &mut payload);
        text(name, &mut payload);
        payload.push(0);
        payload.extend(leb(i as u32));
    }
    section(&mut bytes, 2, &payload);
    let mut types = vec![if wide { 129 } else { 34 }; count];
    types[28] = 35;
    payload = leb(count as u32);
    for ty in &types {
        payload.extend(leb(*ty));
    }
    section(&mut bytes, 3, &payload);
    payload = vec![1, 0x70, 1];
    payload.extend(leb(46713));
    payload.extend(leb(46713));
    section(&mut bytes, 4, &payload);
    payload = vec![1, 0];
    payload.extend(leb(584));
    section(&mut bytes, 5, &payload);
    payload = leb(3);
    for (name, kind, index) in [
        ("memory", 2, 0),
        ("_initialize", 0, 35),
        ("mixer_fieldlog_corpus_v1", 0, 62),
    ] {
        text(name, &mut payload);
        payload.push(kind);
        payload.extend(leb(index));
    }
    section(&mut bytes, 7, &payload);
    let mut bodies = vec![vec![0, 0x0b]; count];
    bodies[28] = vec![0, 0x41, 0, 0x0b];
    if wide {
        bodies[0] = vec![0];
        bodies[0].extend([1; 130]);
        bodies[0].push(0x0b);
    }
    payload = leb(count as u32);
    let mut offsets = Vec::new();
    for body in &bodies {
        payload.extend(leb(body.len() as u32));
        offsets.push(payload.len());
        payload.extend(body);
    }
    let base = section(&mut bytes, 10, &payload);
    for offset in &mut offsets {
        *offset += base;
    }
    Encoded {
        bytes,
        offsets,
        bodies,
        types,
    }
}
fn validate(encoded: &Encoded) -> ValidatedSwiftReactor {
    validate_swift_reactor(
        &encoded.bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap()
}
fn directory() -> PathBuf {
    PathBuf::from(
        std::env::var_os("MIXER_PROFILE_EVIDENCE_DIR").expect("owned supervisor evidence path"),
    )
}
fn fresh(name: &str) -> File {
    OpenOptions::new()
        .read(true)
        .write(true)
        .create_new(true)
        .open(directory().join(name))
        .unwrap()
}
fn assert_wire(bytes: &[u8], e: &Encoded) {
    assert_eq!(bytes.len(), 2_560_000);
    for (absolute, row) in bytes.chunks_exact(32).enumerate() {
        let defined = u32::from_le_bytes(row[0..4].try_into().unwrap());
        let ty = u32::from_le_bytes(row[4..8].try_into().unwrap());
        let off = u64::from_le_bytes(row[8..16].try_into().unwrap());
        let len = u64::from_le_bytes(row[16..24].try_into().unwrap());
        assert_eq!(&row[24..32], &[0; 8]);
        if absolute >= 34 && absolute < 34 + e.bodies.len() {
            let i = absolute - 34;
            assert_eq!(
                (defined, ty, off, len),
                (1, e.types[i], e.offsets[i] as u64, e.bodies[i].len() as u64)
            );
        } else {
            assert_eq!((defined, ty, off, len), (0, u32::MAX, u64::MAX, 0));
        }
    }
}
#[test]
fn rows_absolute_offsets_and_equal_bodies() {
    let e = module(130, true);
    let s = validate(&e);
    for absolute in 0..80000 {
        let row = profile_row_v1(&s, absolute).unwrap();
        if absolute >= 34 && absolute < 164 {
            let i = absolute as usize - 34;
            assert_eq!(
                (row.type_index, row.body_offset, row.body_len),
                (e.types[i], e.offsets[i] as u64, e.bodies[i].len() as u64)
            );
            assert_eq!(s.function_body(i).unwrap(), e.bodies[i]);
        } else {
            assert_eq!(
                row,
                ProfileRowV1 {
                    defined: 0,
                    type_index: u32::MAX,
                    body_offset: u64::MAX,
                    body_len: 0,
                    reserved: 0
                }
            );
        }
    }
    assert_eq!(e.bodies[1], e.bodies[2]);
    assert_ne!(e.offsets[1], e.offsets[2]);
    assert!(e.bodies[0].len() > 127);
    assert_eq!(profile_row_v1(&s, 128).unwrap().type_index, 129);
}
#[test]
fn rows_out_of_range_coordinates() {
    let s = validate(&module(29, false));
    for n in [80000, u32::MAX] {
        assert_eq!(
            profile_row_v1(&s, n).unwrap_err(),
            error(2, 2, u64::from(n) * 32)
        );
    }
}
#[test]
fn rows_minimum_and_last_admitted_position() {
    for count in [29, 79966] {
        let e = module(count, false);
        let s = validate(&e);
        assert_eq!(s.observations().defined_functions, count);
        let n = (33 + count) as u32;
        assert_eq!(
            profile_row_v1(&s, n).unwrap().body_offset,
            e.offsets[count - 1] as u64
        );
        assert_eq!(
            profile_row_v1(&s, 79999).unwrap().defined,
            u32::from(count == 79966)
        );
        println!("BOUNDARY defined={count} usage={:?}", s.usage());
    }
}
#[test]
fn rows_real_validator_rejects_malformed_and_widened_budget() {
    let mut e = module(29, false);
    let p = e.offsets[0];
    e.bytes[p + 1] = 0xff;
    assert!(validate_swift_reactor(
        &e.bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default()
    )
    .is_err());
    let e = module(29, false);
    let mut budget = SwiftValidationBudget::default();
    budget.source_bytes += 1;
    assert!(validate_swift_reactor(&e.bytes, budget, &Cancellation::default()).is_err());
}
#[test]
fn owner_immutable_and_rows_zero_allocations() {
    let e = module(130, true);
    let s = validate(&e);
    let usage = s.usage();
    let obs = s.observations();
    let ((), stats) = super::super::allocation_tests::measure(|| {
        for _ in 0..2 {
            for n in 0..80000 {
                assert!(profile_row_v1(&s, n).is_ok());
            }
        }
    });
    assert_eq!(stats.attempts, 0);
    assert_eq!(s.source(), e.bytes);
    assert_eq!(s.usage(), usage);
    assert_eq!(format!("{:?}", s.observations()), format!("{:?}", obs));
    println!("ROW_ALLOCATIONS {:?}", stats);
}
#[test]
fn file_complete_exact_bytes_and_no_allocations() {
    let e = module(130, true);
    let s = validate(&e);
    let mut file = fresh("actual-rows.bin");
    let (result, stats) =
        super::super::allocation_tests::measure(|| write_profile_row_body_v1(&s, &mut file));
    let o = result.unwrap();
    assert_eq!(
        (o.rows, o.output_bytes, o.output_attempts, o.reserved),
        (80000, 2560000, 625, 0)
    );
    assert_eq!(stats.attempts, 0);
    file.seek(SeekFrom::Start(0)).unwrap();
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes).unwrap();
    assert_wire(&bytes, &e);
    fs::write(directory().join("actual-module.wasm"), &e.bytes).unwrap();
    fs::write(directory().join("actual-module.json"),format!("{{\"source_extent\":{},\"type_count\":130,\"first_offset\":{},\"first_len\":132,\"second_offset\":{},\"second_len\":2,\"defined_functions\":130,\"imported_functions\":34}}\n",e.bytes.len(),e.offsets[0],e.offsets[1])).unwrap();
    println!("WRITER_ALLOCATIONS {:?} OBS {:?}", stats, o);
}
#[test]
fn file_nonempty_refuses_and_preserves() {
    let s = validate(&module(29, false));
    let mut f = fresh("nonempty.bin");
    f.write_all(b"keep").unwrap();
    f.seek(SeekFrom::Start(0)).unwrap();
    assert_eq!(
        write_profile_row_body_v1(&s, &mut f).unwrap_err(),
        error(8, 3, 0)
    );
    assert_eq!(fs::read(directory().join("nonempty.bin")).unwrap(), b"keep");
}
#[test]
fn file_nonzero_offset_refuses_empty() {
    let s = validate(&module(29, false));
    let mut f = fresh("offset.bin");
    f.seek(SeekFrom::Start(9)).unwrap();
    assert_eq!(
        write_profile_row_body_v1(&s, &mut f).unwrap_err(),
        error(8, 3, 0)
    );
    assert_eq!(f.metadata().unwrap().len(), 0);
    assert_eq!(f.stream_position().unwrap(), 9);
}
#[test]
fn file_nonregular_refuses() {
    let s = validate(&module(29, false));
    let mut f = File::open(directory()).unwrap();
    assert_eq!(
        write_profile_row_body_v1(&s, &mut f).unwrap_err(),
        error(6, 3, 0)
    );
}
#[test]
fn file_partial_failure_bytes_and_coordinates() {
    let e = module(29, false);
    let s = validate(&e);
    let mut f = fresh("partial.bin");
    admit_output(&mut f).unwrap();
    let mut calls = 0;
    let err = write_body(&s, |b| {
        calls += 1;
        match calls {
            1 => f.write(b),
            2 => f.write(&b[..7]),
            _ => Err(io::Error::other("injected")),
        }
    })
    .unwrap_err();
    assert_eq!(
        (
            err.code,
            err.stage,
            err.offset,
            err.output_bytes,
            err.output_attempts
        ),
        (9, 4, 4103, 4103, 3)
    );
    let actual = fs::read(directory().join("partial.bin")).unwrap();
    assert_eq!(actual.len(), 4103);
    let mut expected = Vec::new();
    for n in 0..129usize {
        if n >= 34 && n < 63 {
            let i = n - 34;
            expected.extend(1u32.to_le_bytes());
            expected.extend(e.types[i].to_le_bytes());
            expected.extend((e.offsets[i] as u64).to_le_bytes());
            expected.extend((e.bodies[i].len() as u64).to_le_bytes());
            expected.extend(0u64.to_le_bytes());
        } else {
            expected.extend(0u32.to_le_bytes());
            expected.extend(u32::MAX.to_le_bytes());
            expected.extend(u64::MAX.to_le_bytes());
            expected.extend(0u64.to_le_bytes());
            expected.extend(0u64.to_le_bytes());
        }
    }
    assert_eq!(actual, &expected[..4103]);
}
#[test]
fn faults_short_and_interrupted_complete_on_32() {
    let s = validate(&module(29, false));
    for interrupts in [30, 31] {
        let mut calls = 0;
        let o = write_body(&s, |b| {
            calls += 1;
            if calls <= interrupts {
                Err(io::ErrorKind::Interrupted.into())
            } else {
                Ok(b.len())
            }
        })
        .unwrap();
        assert_eq!(o.output_attempts, 625 + interrupts);
        assert_eq!(o.output_bytes, 2560000);
    }
}
#[test]
fn faults_32_short_calls_per_block_and_20000_total() {
    let s = validate(&module(29, false));
    let o = write_body(&s, |b| Ok(b.len().min(128))).unwrap();
    assert_eq!(o.output_attempts, 20000);
    assert_eq!(o.output_bytes, 2560000);
}
#[test]
fn faults_32_interrupted_exhaust_without_33() {
    let s = validate(&module(29, false));
    let mut calls = 0;
    let e = write_body(&s, |_| {
        calls += 1;
        Err(io::ErrorKind::Interrupted.into())
    })
    .unwrap_err();
    assert_eq!(
        (e.code, e.offset, e.output_bytes, e.output_attempts, calls),
        (12, 0, 0, 32, 32)
    );
}
#[test]
fn faults_32_incomplete_short_exhaust_without_33() {
    let s = validate(&module(29, false));
    let mut calls = 0;
    let e = write_body(&s, |_| {
        calls += 1;
        Ok(1)
    })
    .unwrap_err();
    assert_eq!(
        (e.code, e.offset, e.output_bytes, e.output_attempts, calls),
        (12, 32, 32, 32, 32)
    );
}
#[test]
fn faults_zero_error_overreport_specific_on_32() {
    let s = validate(&module(29, false));
    for kind in 0..3 {
        let mut calls = 0;
        let e = write_body(&s, |b| {
            calls += 1;
            if calls < 32 {
                Err(io::ErrorKind::Interrupted.into())
            } else {
                match kind {
                    0 => Ok(0),
                    1 => Err(io::Error::other("injected")),
                    _ => Ok(b.len() + 1),
                }
            }
        })
        .unwrap_err();
        assert_eq!(e.code, [10, 9, 11][kind]);
        assert_eq!(
            (e.stage, e.offset, e.output_bytes, e.output_attempts, calls),
            (4, 0, 0, 32, 32)
        );
    }
}
#[test]
fn faults_prior_block_progress_is_retained() {
    let s = validate(&module(29, false));
    for kind in 0..4 {
        let mut calls = 0;
        let e = write_body(&s, |b| {
            calls += 1;
            if calls == 1 {
                return Ok(b.len());
            }
            match kind {
                0 => Ok(0),
                1 => Err(io::Error::other("injected")),
                2 => Ok(b.len() + 1),
                _ => Err(io::ErrorKind::Interrupted.into()),
            }
        })
        .unwrap_err();
        assert_eq!(
            (e.code, e.offset, e.output_bytes, e.output_attempts),
            (
                [10, 9, 11, 12][kind],
                4096,
                4096,
                if kind == 3 { 33 } else { 2 }
            )
        );
    }
}
#[test]
fn layouts_complete_results_arguments_and_caller_places() {
    use std::mem::{align_of as a, size_of as s};
    type RowResult = Result<ProfileRowV1, ProfileAdapterErrorV1>;
    println!("EXTRA_LAYOUT admit_result={} option_usize={} optional_descriptor={} conversion_result={} metadata_result={} position_result={} range={} step_by={} with_progress_args={} encode_args={} closure={} io_error_kind={}",
        s::<Result<(),ProfileAdapterErrorV1>>(),s::<Option<usize>>(),s::<Option<crate::experimental::descriptors::FunctionSpanView<'_>>>(),s::<Result<u64,std::num::TryFromIntError>>(),s::<io::Result<std::fs::Metadata>>(),s::<io::Result<u64>>(),s::<std::ops::Range<u32>>(),s::<std::iter::StepBy<std::ops::Range<u32>>>(),s::<(ProfileAdapterErrorV1,u64,u64)>(),s::<(ProfileRowV1,&mut [u8])>(),s::<&mut File>(),s::<io::ErrorKind>());
    type WriterResult = Result<ProfileRowsObservationV1, ProfileAdapterErrorV1>;
    assert_eq!(
        (
            s::<ProfileRowV1>(),
            s::<ProfileRowsObservationV1>(),
            s::<ProfileAdapterErrorV1>()
        ),
        (32, 64, 32)
    );
    assert_eq!((s::<RowResult>(), s::<WriterResult>()), (40, 72));
    println!("LAYOUT row={} row_align={} observation={} observation_align={} error={} error_align={} row_result={} writer_result={} args={} snapshot={} observations={} descriptor={} usage={} file={} metadata={} io_error={} io_result={} block={} row_caller_tuple={} writer_caller_tuple={}",s::<ProfileRowV1>(),a::<ProfileRowV1>(),s::<ProfileRowsObservationV1>(),a::<ProfileRowsObservationV1>(),s::<ProfileAdapterErrorV1>(),a::<ProfileAdapterErrorV1>(),s::<RowResult>(),s::<WriterResult>(),s::<(&ValidatedSwiftReactor,&mut File)>(),s::<ValidatedSwiftReactor>(),s::<crate::experimental_swift_reactor::SwiftReactorObservations>(),s::<crate::experimental::descriptors::FunctionSpanView<'_>>(),s::<crate::experimental_swift_reactor::SwiftValidationUsage>(),s::<File>(),s::<std::fs::Metadata>(),s::<io::Error>(),s::<io::Result<usize>>(),s::<[u8;4096]>(),s::<(&ValidatedSwiftReactor,u32,RowResult,ProfileRowV1)>(),s::<(&ValidatedSwiftReactor,&mut File,WriterResult,ProfileRowsObservationV1)>());
}
