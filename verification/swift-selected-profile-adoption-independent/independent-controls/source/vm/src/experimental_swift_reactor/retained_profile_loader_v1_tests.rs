use super::*;
use crate::experimental_wasi::WasiFunction;
use crate::Type;
use std::io::{SeekFrom, Write};
use std::os::unix::fs::MetadataExt;
fn leb(mut n: u32, out: &mut Vec<u8>) {
    loop {
        let b = (n & 127) as u8;
        n >>= 7;
        out.push(b | if n == 0 { 0 } else { 128 });
        if n == 0 {
            return;
        }
    }
}
fn text(s: &[u8], out: &mut Vec<u8>) {
    leb(s.len() as u32, out);
    out.extend_from_slice(s);
}
fn section(id: u8, payload: &[u8], out: &mut Vec<u8>) {
    out.push(id);
    leb(payload.len() as u32, out);
    out.extend_from_slice(payload);
}
fn ty(t: Type) -> u8 {
    match t {
        Type::I32 => 0x7f,
        Type::I64 => 0x7e,
        Type::F32 => 0x7d,
        Type::F64 => 0x7c,
    }
}
fn sig(p: &[Type], r: &[Type], out: &mut Vec<u8>) {
    out.push(0x60);
    leb(p.len() as u32, out);
    out.extend(p.iter().copied().map(ty));
    leb(r.len() as u32, out);
    out.extend(r.iter().copied().map(ty));
}
fn fixture() -> Vec<u8> {
    let mut m = b"\0asm\x01\0\0\0".to_vec();
    let mut types = vec![37];
    for import in WasiFunction::ALL {
        sig(import.parameters(), import.results(), &mut types);
    }
    sig(&[], &[], &mut types);
    sig(&[], &[Type::I32], &mut types);
    sig(&[], &[], &mut types);
    section(1, &types, &mut m);
    let mut imports = vec![34];
    for (i, import) in WasiFunction::ALL.into_iter().enumerate() {
        text(b"wasi_snapshot_preview1", &mut imports);
        text(import.name(), &mut imports);
        imports.push(0);
        leb(i as u32, &mut imports);
    }
    section(2, &imports, &mut m);
    let mut functions = vec![64];
    for i in 0..64 {
        leb(
            if i == 0 {
                36
            } else if i == 28 {
                35
            } else {
                34
            },
            &mut functions,
        );
    }
    section(3, &functions, &mut m);
    let mut table = vec![1, 0x70, 1];
    leb(46713, &mut table);
    leb(46713, &mut table);
    section(4, &table, &mut m);
    let mut memory = vec![1, 0];
    leb(584, &mut memory);
    section(5, &memory, &mut m);
    section(6, &[1, 0x7f, 1, 0x41, 0, 0x0b], &mut m);
    let mut exports = vec![3];
    for (name, kind, index) in [
        (b"memory".as_slice(), 2, 0),
        (b"_initialize".as_slice(), 0, 35),
        (b"mixer_fieldlog_corpus_v1".as_slice(), 0, 62),
    ] {
        text(name, &mut exports);
        exports.push(kind);
        leb(index, &mut exports);
    }
    section(7, &exports, &mut m);
    let mut code = vec![64];
    for i in 0..64 {
        let body: &[u8] = if i == 28 {
            &[0, 0x41, 0, 0x0b]
        } else {
            &[0, 0x0b]
        };
        leb(body.len() as u32, &mut code);
        code.extend_from_slice(body);
    }
    section(10, &code, &mut m);
    assert_eq!(m.len(), 1947);
    m
}
#[test]
fn emit_genuine_validator_fixture() {
    let Some(path) = std::env::var_os("MIXER_LOADER_FIXTURE_OUTPUT") else {
        return;
    };
    let b = fixture();
    let p = validate_swift_reactor(
        &b,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
    assert_eq!(p.source(), b);
    std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .unwrap()
        .write_all(&b)
        .unwrap();
}
struct Script {
    calls: u32,
    interrupt: u32,
    limit: usize,
    overreport: bool,
    error: bool,
    eof: bool,
}
impl Read for Script {
    fn read(&mut self, out: &mut [u8]) -> io::Result<usize> {
        self.calls += 1;
        if self.calls <= self.interrupt {
            return Err(io::Error::from(io::ErrorKind::Interrupted));
        }
        if self.error {
            return Err(io::Error::from_raw_os_error(9));
        }
        if self.overreport {
            return Ok(out.len() + 1);
        }
        if self.eof {
            return Ok(0);
        }
        let n = out.len().min(self.limit);
        out[..n].fill(37);
        Ok(n)
    }
}
fn script() -> Script {
    Script {
        calls: 0,
        interrupt: 0,
        limit: usize::MAX,
        overreport: false,
        error: false,
        eof: false,
    }
}
#[test]
fn exact_32nd_call_success_and_no_33rd() {
    let mut output = [0; 32];
    let mut usage = LoaderUsageV1::default();
    let mut s = Script {
        limit: 1,
        ..script()
    };
    read_request(&mut s, &mut output, false, Role::Source, 0, &mut usage).unwrap();
    assert_eq!((s.calls, usage.read_bytes[0]), (32, 32));
    let mut s = Script {
        interrupt: 31,
        ..script()
    };
    read_request(&mut s, &mut output, false, Role::Source, 0, &mut usage).unwrap();
    assert_eq!(s.calls, 32);
    let mut s = Script {
        interrupt: 32,
        ..script()
    };
    let f = read_request(&mut s, &mut output, false, Role::Source, 0, &mut usage).unwrap_err();
    assert_eq!((s.calls, f.kind, f.attempts), (32, Refusal::Attempts, 32));
    let mut s = Script {
        limit: 1,
        ..script()
    };
    let f = read_request(&mut s, &mut [0; 33], false, Role::Source, 7, &mut usage).unwrap_err();
    assert_eq!((s.calls, f.offset), (32, 39));
}
#[test]
fn eof_short_overreport_and_original_io_error() {
    let mut u = LoaderUsageV1::default();
    let mut s = Script {
        eof: true,
        interrupt: 31,
        ..script()
    };
    read_request(&mut s, &mut [0; 1], true, Role::Source, 41, &mut u).unwrap();
    assert_eq!(s.calls, 32);
    let mut s = Script {
        eof: true,
        ..script()
    };
    assert_eq!(
        read_request(&mut s, &mut [0; 4], false, Role::Source, 19, &mut u)
            .unwrap_err()
            .kind,
        Refusal::ShortInput
    );
    let mut s = script();
    assert_eq!(
        read_request(&mut s, &mut [0; 1], true, Role::Source, 19, &mut u)
            .unwrap_err()
            .kind,
        Refusal::ExtraInput
    );
    let mut s = Script {
        overreport: true,
        ..script()
    };
    assert_eq!(
        read_request(&mut s, &mut [0; 4], false, Role::Source, 19, &mut u)
            .unwrap_err()
            .kind,
        Refusal::OverreportedRead
    );
    let mut s = Script {
        error: true,
        interrupt: 31,
        ..script()
    };
    let f = read_request(&mut s, &mut [0; 4], false, Role::Source, 19, &mut u).unwrap_err();
    assert_eq!(
        (f.kind, f.offset, f.attempts, f.io.unwrap().raw_os_error()),
        (Refusal::Io, 19, 32, Some(9))
    );
}
#[test]
fn encoding_raw_bytes_duplicate_keys_and_caps() {
    let raw = b"Z=\xffA=x";
    let mut entries = [(0, 3, 1), (3, 3, 1)];
    let mut out = Bytes::new();
    encode_environment(raw, &mut entries, &mut out).unwrap();
    validate_list(out.slice(), true, false).unwrap();
    assert!(out.slice().contains(&255));
    let raw = b"A=xA=y";
    let mut entries = [(0, 3, 1), (3, 3, 1)];
    assert_eq!(
        encode_environment(raw, &mut entries, &mut Bytes::new())
            .unwrap_err()
            .kind,
        Refusal::DuplicateEnvironment
    );
    let mut b = Bytes::<8>::new();
    assert!(b.put(&[0; 8]).is_ok());
    assert_eq!(b.put(&[1]).unwrap_err().kind, Refusal::ProcessLimit);
    let mut x = vec![0; 8];
    x[..8].copy_from_slice(&65u64.to_le_bytes());
    assert!(validate_list(&x, false, false).is_err());
    for bytes in [&b"\x01\0\0\0\0\0\0\0"[..], &[0; 7][..]] {
        assert!(validate_list(bytes, false, false).is_err());
    }
    let mut v = Vec::new();
    v.extend_from_slice(&1u64.to_le_bytes());
    v.extend_from_slice(&3u64.to_le_bytes());
    v.extend_from_slice(b"a\0b");
    assert!(validate_list(&v, false, false).is_err());
}
#[test]
fn identity_hex_and_all_five_budget_fields() {
    assert_eq!(parse_hex(&[b'0'; 64]), Some([0; 32]));
    assert!(parse_hex(&[b'A'; 64]).is_none());
    assert!(parse_hex(&[b'0'; 63]).is_none());
    let b = SwiftValidationBudget::default();
    for i in 0..5 {
        let mut n = b;
        match i {
            0 => n.source_bytes += 1,
            1 => n.metadata_bytes += 1,
            2 => n.scratch_bytes += 1,
            3 => n.work_credits += 1,
            _ => n.deadline_ms += 1,
        }
        assert!(!budget_valid(n));
    }
}
#[test]
fn malformed_headers_never_index_unchecked() {
    for n in 0..512 {
        let bytes = vec![0; n];
        assert!(parse_build(&bytes).is_err());
        assert!(parse_session(&bytes).is_err());
    }
    for n in [BUILD_CAP + 1, SESSION_CAP + 1] {
        let bytes = vec![0; n];
        assert!(parse_build(&bytes).is_err());
        assert!(parse_session(&bytes).is_err());
    }
}
#[test]
fn actual_file_allocation_refusal_returns_caller_owner() {
    let Some(path) = std::env::var_os("MIXER_LOADER_SOURCE_FILE") else {
        return;
    };
    let mut source = File::open(path).unwrap();
    let id = identity(&source, Role::Source).unwrap();
    let mut usage = LoaderUsageV1::default();
    let (result, stats) =
        crate::experimental_swift_reactor::allocation_tests::measure_extended(Some(0), || {
            retained(&mut source, Role::Source, SOURCE_CAP, id, &mut usage, 0)
        });
    assert_eq!(result.unwrap_err().kind, Refusal::Allocation);
    assert_eq!(stats.injected_failures, 1);
    assert_eq!(identity(&source, Role::Source).unwrap(), id);
    assert_eq!(source.stream_position().unwrap(), 0);
}
#[test]
fn actual_selected_loader_child() {
    let Some(source_path) = std::env::var_os("MIXER_LOADER_SOURCE_FILE") else {
        return;
    };
    let scenario = std::env::var("MIXER_LOADER_SCENARIO").unwrap();
    let mut source = if scenario == "nonregular" {
        File::open("/dev/null").unwrap()
    } else if scenario == "unreadable" {
        std::fs::OpenOptions::new()
            .write(true)
            .open(&source_path)
            .unwrap()
    } else {
        File::open(&source_path).unwrap()
    };
    let build = if scenario == "alias" {
        source.try_clone().unwrap()
    } else {
        File::open(std::env::var_os("MIXER_LOADER_BUILD_FILE").unwrap()).unwrap()
    };
    let session = File::open(std::env::var_os("MIXER_LOADER_SESSION_FILE").unwrap()).unwrap();
    if scenario == "offset" {
        source.seek(SeekFrom::Start(1)).unwrap();
    }
    let original = [
        source.metadata().unwrap(),
        build.metadata().unwrap(),
        session.metadata().unwrap(),
    ]
    .map(|m| (m.dev(), m.ino()));
    let mut budget = SwiftValidationBudget::default();
    if scenario == "narrowed" || scenario == "adopt-independent-narrowed" {
        budget = SwiftValidationBudget {
            source_bytes: 1947,
            metadata_bytes: 1_000_000,
            scratch_bytes: 65536,
            work_credits: 1_000_000,
            deadline_ms: 10000,
        };
    }
    if let Some(field) = scenario.strip_prefix("zero-") {
        match field {
            "source" => budget.source_bytes = 0,
            "metadata" => budget.metadata_bytes = 0,
            "scratch" => budget.scratch_bytes = 0,
            "work" => budget.work_credits = 0,
            "deadline" => budget.deadline_ms = 0,
            _ => panic!("bad field"),
        }
    }
    if let Some(field) = scenario.strip_prefix("drift-") {
        match field {
            "source" => budget.source_bytes -= 1,
            "metadata" => budget.metadata_bytes -= 1,
            "scratch" => budget.scratch_bytes -= 1,
            "work" => budget.work_credits -= 1,
            "deadline" => budget.deadline_ms -= 1,
            _ => panic!("bad field"),
        }
    }
    if let Some(field) = scenario.strip_prefix("widen-") {
        match field {
            "source" => budget.source_bytes += 1,
            "metadata" => budget.metadata_bytes += 1,
            "scratch" => budget.scratch_bytes += 1,
            "work" => budget.work_credits += 1,
            "deadline" => budget.deadline_ms += 1,
            _ => panic!("bad field"),
        }
    }
    let cancellation = Cancellation::default();
    if scenario == "cancelled" {
        cancellation.cancel();
    }
    let outcome = load_selected_retained_profile_v1(source, build, session, budget, &cancellation);
    let actual = [
        &outcome.files.source,
        &outcome.files.build,
        &outcome.files.session,
    ]
    .map(|f| {
        let m = f.metadata().unwrap();
        (m.dev(), m.ino())
    });
    assert_eq!(actual, original);
    if !scenario.starts_with("widen-") {
        assert!(outcome.files.executable.is_some());
    }
    match outcome.selected {
        Ok(selected) => {
            assert!(matches!(
                scenario.as_str(),
                "success" | "narrowed" | "raw-environment" | "raw-cwd" | "raw-executable"
            ) || scenario.starts_with("adopt-"));
            assert_eq!(selected.source(), fixture());
            assert_eq!(selected.provenance.validation_budget, budget);
            assert_eq!(selected.provenance.source_extent, 1947);
            assert_eq!(outcome.usage.source_equality_bytes, 1947);
            assert_eq!(selected.proof.observations().validated_bodies, 64);
            assert_eq!(selected.provenance.identities[0].dev, original[0].0);
            if scenario.starts_with("adopt-independent-") {
                independent_selected_controls(selected,scenario.strip_prefix("adopt-").unwrap());
            } else if let Some(case)=scenario.strip_prefix("adopt-") {
                super::super::cache::test_selected_initial_outcome_v1(selected,case);
            }
            println!(
                "SELECTED\t{}\t{}\t{}",
                scenario, outcome.usage.hash_bytes, outcome.usage.allocated_peak_requested
            );
        }
        Err(failure) => {
            let expected = if scenario.starts_with("drift-") {
                Refusal::BudgetMismatch
            } else if scenario.starts_with("widen-") {
                Refusal::InvalidBudget
            } else {
                match scenario.as_str() {
                    "source-substitute" | "source-extent" => Refusal::SourceIdentity,
                    "build-tail" => Refusal::Digest,
                    "build-identity" | "binary-substitute" => Refusal::BuildIdentity,
                    "session-digest" => Refusal::SessionIdentity,
                    "nonce" => Refusal::SessionNonce,
                    "argv" | "environment" | "cwd" => Refusal::ProcessMismatch,
                    "offset" => Refusal::FileOffset,
                    "alias" => Refusal::AliasedFiles,
                    "nonregular" => Refusal::FileType,
                    "unreadable" => Refusal::Io,
                    "zero-source" => Refusal::FileLimit,
                    "zero-metadata" | "zero-scratch" | "zero-work" | "zero-deadline"
                    | "cancelled" | "malformed" | "large-malformed" => Refusal::Validation,
                    "build-overcap" | "session-overcap" => Refusal::FileLimit,
                    _ => panic!("unexpected failing scenario {} {:?}", scenario, failure),
                }
            };
            assert_eq!(failure.kind, expected, "{} {:?}", scenario, failure);
            if expected == Refusal::Validation {
                let v = failure
                    .validation
                    .expect("original typed failure preserved");
                assert!(!v.code.is_empty());
                assert_eq!(v.usage.deadline_ms, budget.deadline_ms);
                if scenario == "cancelled" {
                    assert_eq!(v.kind, super::super::SwiftValidationFailureKind::Cancelled);
                }
                if scenario == "zero-deadline" {
                    assert_eq!(v.kind, super::super::SwiftValidationFailureKind::Deadline);
                }
                if scenario == "large-malformed" {
                    let bytes = outcome.files.source.metadata().unwrap().len() as usize;
                    assert!(bytes >= 8 * 1024 * 1024);
                    assert_eq!(v.usage.source_bytes, bytes);
                    assert!(
                        outcome.usage.allocated_peak_requested >= 2 * bytes,
                        "validation-failure peak omitted actual retained validator source"
                    );
                    println!(
                        "LARGE_FAILURE_PEAK\t{}",
                        outcome.usage.allocated_peak_requested
                    );
                }
                println!(
                    "ORIGINAL_VALIDATION\t{}\t{:?}\t{}\t{}\t{}\t{}",
                    scenario, v.kind, v.code, v.offset, v.usage.work_used, v.usage.elapsed_micros
                );
            }
            if expected == Refusal::Io {
                assert!(failure
                    .io
                    .as_ref()
                    .and_then(io::Error::raw_os_error)
                    .is_some());
            }
            println!(
                "REFUSED\t{}\t{:?}\t{}\t{}",
                scenario, expected, failure.offset, failure.attempts
            );
        }
    }
    // All four actual files remain owned here. Dropping below is explicitly not a
    // close-success receipt; trusted runner retains independent name cleanup.
    assert_eq!(
        outcome.files.source.metadata().unwrap().dev(),
        original[0].0
    );
}
#[test]
fn loader_named_layout_inventory() {
    macro_rules! item {
        ($name:expr,$t:ty) => {
            println!(
                "LOADER_LAYOUT\t{}\t{}\t{}",
                $name,
                std::mem::size_of::<$t>(),
                std::mem::align_of::<$t>()
            );
        };
    }
    item!("SelectedValidatedProfileV1", SelectedValidatedProfileV1);
    item!("LoaderProvenanceV1", LoaderProvenanceV1);
    item!("LoaderFailureV1", LoaderFailureV1);
    item!("LoaderOutcomeV1", LoaderOutcomeV1);
    item!("ReturnedLoaderFilesV1", ReturnedLoaderFilesV1);
    item!("LoaderUsageV1", LoaderUsageV1);
    item!("FileIdentityV1", FileIdentityV1);
    item!("BuildView", BuildView<'static>);
    item!("SessionView", SessionView<'static>);
    item!("ProcessObservationV1", ProcessObservationV1);
    item!("BytesProcess", Bytes<PROCESS_CAP>);
    item!("BytesPath", Bytes<STR_CAP>);
    item!("EnvironmentEntries", [(usize, usize, usize); ENTRY_CAP]);
    item!("ResultSelected",Result<SelectedValidatedProfileV1,LoaderFailureV1>);
    item!("ValidationResult",Result<ValidatedSwiftReactor,SwiftValidationFailure>);
    item!("VecHeader", Vec<u8>);
    item!("File", File);
    item!("OptionFile", Option<File>);
    item!("ValidationBudget", SwiftValidationBudget);
    item!("ValidationFailure", SwiftValidationFailure);
}

#[test]
fn complete_adoption_layout_inventory_v1() {
    for (name,bytes,alignment) in &ADOPTION_LAYOUTS_V1 {
        println!("ADOPTION_LAYOUT\t{}\t{}\t{}",name,bytes,alignment);
    }
    println!("ADOPTION_FLOOR\t{}\t{}\t{}\t{}",
        ADOPTION_ENTRY_BYTES_V1,ADOPTION_MOVE_BYTES_V1,
        super::super::control::ADOPTION_CLEANUP_BYTES_V1,
        super::super::control::foundation_construction_bytes().unwrap());
}

#[test]
fn ordinary_adoption_has_no_selected_provenance_v1() {
    let proof=validate_swift_reactor(&fixture(),SwiftValidationBudget::default(),&Cancellation::default()).unwrap();
    let (mut control,adopted)=RuntimeControl::adopt(proof,SwiftRunBudget::default(),Instant::now(),Cancellation::default()).unwrap();
    assert!(adopted.selected_provenance().is_none());
    assert_eq!(adopted.proof().source(),fixture());
    control.drop_proof(adopted).unwrap();
    let usage=control.finish_owned_cleanup(None);
    assert_eq!(usage.reservations.combined.current,0);
    assert_eq!(usage.reservations.live_tickets,0);
    assert_eq!(usage.cleanup_invariant,None);
}

#[test]
fn final_metadata_actual_safe_files_all_four_roles_v1() {
    use std::io::Write;
    let directory=std::path::PathBuf::from(std::env::var_os("MIXER_LOADER_HELPER_DIR").expect("owned helper directory"));
    let paths=["final-source","final-build","final-session","final-executable"].map(|n|directory.join(n));
    let mut owned=Vec::new();
    for path in &paths {owned.push(std::fs::OpenOptions::new().read(true).write(true).create_new(true).open(path).unwrap());}
    let mut values=owned.into_iter();
    let mut files=ReturnedLoaderFilesV1 {source:values.next().unwrap(),build:values.next().unwrap(),session:values.next().unwrap(),executable:Some(values.next().unwrap())};
    let roles=[Role::Source,Role::Build,Role::Session,Role::Executable];
    for (index,role) in roles.into_iter().enumerate() {
        let expected=[&files.source,&files.build,&files.session,files.executable.as_ref().unwrap()].map(|f|identity(f,Role::Source).unwrap());
        assert!(final_metadata_recheck_v1(&files,&expected).is_ok());
        let file=match index {0=>&mut files.source,1=>&mut files.build,2=>&mut files.session,_=>files.executable.as_mut().unwrap()};
        file.write_all(&[index as u8]).unwrap();file.flush().unwrap();
        let failure=final_metadata_recheck_v1(&files,&expected).err().unwrap();
        assert_eq!((failure.kind,failure.role,failure.offset,failure.attempts),(Refusal::MetadataChanged,role,index as u64,0));
        assert!(failure.original_io().is_none());
        for file in [&files.source,&files.build,&files.session,files.executable.as_ref().unwrap()] {assert!(file.metadata().is_ok());}
        println!("ACTUAL_FINAL_FILE_MISMATCH\t{:?}\t{}\tall_four_owners_retained",role,index);
    }
    drop(files); // No close-success inference.
    for path in paths {std::fs::remove_file(path).unwrap();}
}

#[test]
fn final_metadata_synthetic_helper_io_all_four_roles_v1() {
    for (index,role) in [Role::Source,Role::Build,Role::Session,Role::Executable].into_iter().enumerate() {
        let original=io::Error::from_raw_os_error(13);
        let original_kind=original.kind();
        let observed=Err(LoaderFailureV1::io(role,0,0,original));
        let failure=check_final_identity_v1(role,index,FileIdentityV1::default(),observed).err().unwrap();
        assert_eq!((failure.kind,failure.role,failure.offset,failure.attempts),(Refusal::Io,role,0,0));
        let retained=failure.original_io().unwrap();
        assert_eq!(retained.raw_os_error(),Some(13));assert_eq!(retained.kind(),original_kind);
        println!("SYNTHETIC_HELPER_IO_ONLY\t{:?}\t{:?}\t13",role,original_kind);
    }
}

#[test]
fn genuine_proof_source_substitution_is_not_length_equality() {
    let first = fixture();
    let mut second = first.clone();
    let at = second
        .windows(4)
        .position(|w| w == [0, 0x41, 0, 0x0b])
        .unwrap();
    second[at + 2] = 1;
    let a = validate_swift_reactor(
        &first,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
    let b = validate_swift_reactor(
        &second,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
    assert_eq!(a.source().len(), b.source().len());
    assert!(source_bytes_equal(&a, &first));
    assert!(source_bytes_equal(&b, &second));
    assert!(!source_bytes_equal(&a, &second));
    assert!(!source_bytes_equal(&b, &first));
}
#[test]
fn bounded_os_string_scan_keeps_raw_bytes_and_refuses_null_or_nontermination() {
    let raw = [255u8, 13, 0];
    let bytes = unsafe { platform::c_string(raw.as_ptr().cast()) }.unwrap();
    assert_eq!(bytes, &[255, 13]);
    let raw = [1u8; STR_CAP];
    assert_eq!(
        unsafe { platform::c_string(raw.as_ptr().cast()) }
            .unwrap_err()
            .kind,
        Refusal::ProcessLimit
    );
    assert_eq!(
        unsafe { platform::c_string(std::ptr::null()) }
            .unwrap_err()
            .kind,
        Refusal::ProcessApi
    );
}

#[test]
fn closed_list_encodings_exclusions_and_non_utf8() {
    fn list(values: &[&[u8]]) -> Vec<u8> {
        let mut out = (values.len() as u64).to_le_bytes().to_vec();
        for v in values {
            out.extend_from_slice(&(v.len() as u64).to_le_bytes());
            out.extend_from_slice(v);
        }
        out
    }
    for key in COMPILE_IDENTITIES {
        let value = format!("{}=x", key);
        assert!(validate_list(&list(&[value.as_bytes()]), true, true).is_err());
    }
    for key in [SESSION_IDENTITY, SESSION_NONCE] {
        let mut v = key.to_vec();
        v.extend_from_slice(b"=x");
        assert!(validate_list(&list(&[&v]), true, false).is_err());
    }
    assert!(validate_list(&list(&[b"A=x", b"A=y"]), true, false).is_err());
    assert!(validate_list(&list(&[b"Z=x", b"A=y"]), true, false).is_err());
    assert!(validate_list(&list(&[b"A=x=y", b"Z=\xff"]), true, false).is_ok());
    assert!(validate_list(&list(&[b"", b"\xff"]), false, false).is_ok());
    let mut valid = list(&[b"arg"]);
    valid.push(0);
    assert!(validate_list(&valid, false, false).is_err());
    assert!(validate_list(&list(&[&[1; 4096]]), false, false).is_err());
}
#[test]
fn named_storage_includes_moves_and_is_separate_from_runtime_ledgers() {
    for (name, bytes, alignment) in [
        (
            "ObservationPlaces",
            std::mem::size_of::<ObservationPlacesV1>(),
            std::mem::align_of::<ObservationPlacesV1>(),
        ),
        (
            "LoaderPlaces",
            std::mem::size_of::<LoaderPlacesV1>(),
            std::mem::align_of::<LoaderPlacesV1>(),
        ),
        (
            "ReadHashPlaces",
            std::mem::size_of::<ReadHashPlacesV1>(),
            std::mem::align_of::<ReadHashPlacesV1>(),
        ),
    ] {
        println!("LOADER_LAYOUT\t{}\t{}\t{}", name, bytes, alignment);
    }
    let fixed = fixed_named_storage_bound_v1();
    assert!(fixed < 1024 * 1024);
    println!("LOADER_FIXED\t{}", fixed);
    let maximum = 2 * SOURCE_CAP + 16 * 1024 * 1024 + 1024 * 1024 + BUILD_CAP + SESSION_CAP + fixed;
    assert!(maximum < 268435456);
    println!("LOADER_NAMED_UNION\t{}", maximum);
}
#[test]
fn actual_retained_file_detects_extra_and_metadata_change() {
    use std::os::unix::fs::PermissionsExt;
    let Some(path) = std::env::var_os("MIXER_LOADER_SOURCE_FILE") else {
        return;
    };
    let mut source = File::open(&path).unwrap();
    let initial = identity(&source, Role::Source).unwrap();
    let mut changed = source.metadata().unwrap().permissions();
    changed.set_mode(changed.mode() ^ 0o100);
    source.set_permissions(changed).unwrap();
    let failure = retained(
        &mut source,
        Role::Source,
        SOURCE_CAP,
        initial,
        &mut LoaderUsageV1::default(),
        0,
    )
    .unwrap_err();
    assert_eq!(failure.kind, Refusal::MetadataChanged);
    assert!(source.metadata().is_ok());
    let temporary = std::path::Path::new(&path).with_extension("extra");
    let mut file = std::fs::OpenOptions::new()
        .read(true)
        .write(true)
        .create_new(true)
        .open(&temporary)
        .unwrap();
    file.write_all(b"a").unwrap();
    file.seek(SeekFrom::Start(0)).unwrap();
    let id = identity(&file, Role::Source).unwrap();
    file.write_all(b"ab").unwrap();
    file.seek(SeekFrom::Start(0)).unwrap();
    let failure = retained(
        &mut file,
        Role::Source,
        SOURCE_CAP,
        id,
        &mut LoaderUsageV1::default(),
        0,
    )
    .unwrap_err();
    assert_eq!(failure.kind, Refusal::ExtraInput);
    assert!(file.metadata().is_ok());
    drop(file);
    std::fs::remove_file(temporary).unwrap();
}

fn independent_normalize_usage(mut u: super::super::control::SwiftRunUsage) -> super::super::control::SwiftRunUsage {
    u.elapsed_micros=0;
    u.deadline_overshoot_micros=0;
    u.validation.elapsed_micros=0;
    u
}
fn independent_normalize_failure(mut f: SwiftRunFailure) -> SwiftRunFailure {
    f.at_failure=independent_normalize_usage(f.at_failure);
    f.after_cleanup=f.after_cleanup.map(independent_normalize_usage);
    f
}
fn independent_selected_controls(selected: SelectedValidatedProfileV1, case: &str) {
    use super::super::control::*;
    if let Some(field)=case.strip_prefix("independent-parity-") {
        let proof=validate_swift_reactor(&fixture(), SwiftValidationBudget::default(), &Cancellation::default()).unwrap();
        let mut budget=SwiftRunBudget::default();
        let ordinary_cancel=Cancellation::default();
        let selected_cancel=Cancellation::default();
        match field {
            "source"=>budget.source_bytes=0,
            "metadata"=>budget.metadata_bytes=0,
            "combined"=>budget.combined_bytes=0,
            "invalid"=>budget.source_bytes+=1,
            "cancelled"=>{ordinary_cancel.cancel();selected_cancel.cancel();},
            "deadline"=>budget.deadline_ms=0,
            _=>panic!("independent field"),
        }
        let ordinary=match RuntimeControl::adopt(proof,budget,Instant::now(),ordinary_cancel) {
            Err(f)=>f,Ok(_)=>panic!("ordinary refusal expected"),
        };
        let selected=match selected.adopt(budget,Instant::now(),selected_cancel) {
            Err(f)=>f,Ok(_)=>panic!("selected refusal expected"),
        };
        assert_eq!(independent_normalize_failure(ordinary),independent_normalize_failure(selected));
        let after=selected.after_cleanup.unwrap();
        assert_eq!((after.reservations.combined.current,after.reservations.live_tickets,after.cleanup_invariant),(0,0,None));
        println!("SELECTED_OUTCOME\t{case}\tindependent_direct_full_failure_payload_parity_except_elapsed");
        return;
    }
    if let Some(field)=case.strip_prefix("independent-refund-") {
        let expected=test_provenance_encoding_v1(selected.test_provenance_v1());
        let (control,adopted)=selected.adopt(SwiftRunBudget::default(),Instant::now(),Cancellation::default()).unwrap();
        assert_eq!(test_provenance_encoding_v1(adopted.selected_provenance().unwrap()),expected);
        super::super::control::independent_refund_faults(control,adopted,field);
        println!("SELECTED_OUTCOME\t{case}\tindependent_synthetic_ticket_fault_quarantined");
        return;
    }
    if let Some(edge)=case.strip_prefix("independent-boundary-") {
        let validation=selected.proof.usage();
        let floor=foundation_construction_bytes().unwrap();
        let before=validation.source_bytes+validation.metadata_reserved+std::mem::size_of::<RuntimeControl>()+Cancellation::requested_backing_layout().size();
        let combined=before+floor;
        let combined=match edge {"below"=>combined-1,"equal"=>combined,"above"=>combined+1,_=>panic!("edge")};
        let budget=SwiftRunBudget {combined_bytes:combined,..SwiftRunBudget::default()};
        match selected.adopt(budget,Instant::now(),Cancellation::default()) {
            Err(f)=>{
                assert_eq!(edge,"below");assert_eq!(f.kind,SwiftRunFailureKind::CombinedExhausted);
                assert_eq!(f.attempted as usize,before+floor);assert_eq!(f.limit as usize,combined);
                assert_eq!(f.at_failure.reservations.combined.current,before);
                assert_eq!(f.at_failure.reservations.construction.current,0);
                let after=f.after_cleanup.unwrap();assert_eq!((after.reservations.combined.current,after.reservations.live_tickets),(0,0));
            },
            Ok((mut control,adopted))=>{
                assert_ne!(edge,"below");assert!(adopted.selected_provenance().is_some());
                let usage=control.usage(None);assert_eq!(usage.reservations.construction.current,floor);
                assert_eq!(usage.reservations.combined.current,before+floor);
                control.drop_proof(adopted).unwrap();let after=control.finish_owned_cleanup(None);
                assert_eq!((after.reservations.combined.current,after.reservations.live_tickets,after.cleanup_invariant),(0,0,None));
            },
        }
        println!("SELECTED_OUTCOME\t{case}\tindependent_actual_selected_floor_boundary\t{before}\t{floor}\t{combined}");
        return;
    }
    assert_eq!(case,"independent-narrowed");
    assert_eq!(selected.validation_budget(),SwiftValidationBudget {source_bytes:1947,metadata_bytes:1000000,scratch_bytes:65536,work_credits:1000000,deadline_ms:10000});
    super::super::cache::test_selected_initial_outcome_v1(selected,"encoded");
    println!("SELECTED_OUTCOME\t{case}\tindependent_all_five_narrowed_limits_through_actual_cache");
}
