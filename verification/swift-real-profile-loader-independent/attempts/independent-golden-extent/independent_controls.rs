use super::*;
use std::io::{SeekFrom, Write};
#[path = "/Users/andreyyurlov/Documents/dev/mixer/verification/swift-real-profile-loader-independent/original_fixture.rs"]
mod original_fixture;
fn le(b: &mut [u8], at: usize, n: u64) {
    b[at..at + 8].copy_from_slice(&n.to_le_bytes());
}
fn counted(values: &[&[u8]]) -> Vec<u8> {
    let mut v = (values.len() as u64).to_le_bytes().to_vec();
    for x in values {
        v.extend_from_slice(&(x.len() as u64).to_le_bytes());
        v.extend_from_slice(x);
    }
    v
}
fn build_wire() -> Vec<u8> {
    let parts = [
        b"{}".to_vec(),
        counted(&[b"/compiler", b""]),
        counted(&[b"A=1=2", b"Z=\xff"]),
        b"compiler version\n".to_vec(),
    ];
    let mut v = vec![0; 512];
    v[..8].copy_from_slice(b"MIXLBD01");
    le(&mut v, 8, 1);
    le(&mut v, 16, 512);
    le(&mut v, 32, 144);
    le(&mut v, 40, 11);
    le(&mut v, 80, 1);
    v[88..107].copy_from_slice(b"aarch64-apple-darwin");
    for (i, p) in parts.iter().enumerate() {
        le(&mut v, 48 + i * 8, p.len() as u64);
        v.extend_from_slice(p);
    }
    let n = v.len();
    le(&mut v, 24, n as u64);
    v
}
fn session_wire() -> Vec<u8> {
    let parts = [
        vec![0; 64],
        counted(&[b"/exe"]),
        counted(&[]),
        b"/".to_vec(),
    ];
    let mut v = vec![0; 512];
    v[..8].copy_from_slice(b"MIXLSE01");
    le(&mut v, 8, 1);
    le(&mut v, 16, 512);
    let b = SwiftValidationBudget::default();
    for (i, x) in [
        b.source_bytes as u64,
        b.metadata_bytes as u64,
        b.scratch_bytes as u64,
        b.work_credits,
        b.deadline_ms,
    ]
    .into_iter()
    .enumerate()
    {
        le(&mut v, 72 + i * 8, x);
    }
    for (i, p) in parts.iter().enumerate() {
        le(&mut v, 40 + i * 8, p.len() as u64);
        v.extend_from_slice(p);
    }
    let n = v.len();
    le(&mut v, 24, n as u64);
    v
}
#[test]
fn independent_reserved_header_lengths_and_target_refuse() {
    let b = build_wire();
    let s = session_wire();
    assert!(parse_build(&b).is_ok());
    assert!(parse_session(&s).is_ok());
    for (wire, start, build) in [(&b, 344, true), (&s, 368, false)] {
        for at in start..512 {
            for bit in 0..8 {
                let mut v = wire.clone();
                v[at] = 1 << bit;
                if build {
                    assert!(parse_build(&v).is_err());
                } else {
                    assert!(parse_session(&v).is_err());
                }
            }
        }
    }
    for at in 88..152 {
        let mut v = b.clone();
        v[at] ^= 1;
        assert!(parse_build(&v).is_err());
    }
    for (wire, offsets, build) in [(&b, 48, true), (&s, 40, false)] {
        for at in [8, 16, 24, offsets, offsets + 8, offsets + 16, offsets + 24] {
            for value in [0, u64::MAX, 512, 131073] {
                let mut v = wire.clone();
                le(&mut v, at, value);
                if build {
                    assert!(parse_build(&v).is_err(), "{} {}", at, value);
                } else {
                    assert!(parse_session(&v).is_err(), "{} {}", at, value);
                }
            }
        }
        for length in 0..wire.len() {
            let v = &wire[..length];
            if build {
                assert!(parse_build(v).is_err());
            } else {
                assert!(parse_session(v).is_err());
            }
        }
        let mut tail = wire.clone();
        tail.push(1);
        let n = tail.len();
        le(&mut tail, 24, n as u64);
        if build {
            assert!(parse_build(&tail).is_err());
        } else {
            assert!(parse_session(&tail).is_err());
        }
    }
}
#[test]
fn independent_list_exact_limits_and_raw_octets() {
    assert!(validate_list(&counted(&[]), true, false).is_ok());
    assert!(validate_list(&counted(&[]), false, false).is_err());
    let empty: Vec<&[u8]> = vec![b""; 64];
    assert!(validate_list(&counted(&empty), false, false).is_ok());
    let empty: Vec<&[u8]> = vec![b""; 65];
    assert!(validate_list(&counted(&empty), false, false).is_err());
    let max = vec![b'x'; 4095];
    let long = vec![b'x'; 4096];
    assert!(validate_list(&counted(&[&max]), false, false).is_ok());
    assert!(validate_list(&counted(&[&long]), false, false).is_err());
    let fourth = vec![b'x'; 4059];
    let exact = counted(&[&max, &max, &max, &fourth]);
    assert_eq!(exact.len(), 16384);
    assert!(validate_list(&exact, false, false).is_ok());
    let mut over = exact;
    over.push(1);
    assert!(validate_list(&over, false, false).is_err());
    for octet in 0u8..=255 {
        let value = [b'K', b'=', octet, b'=', 255];
        assert_eq!(
            validate_list(&counted(&[&value]), true, false).is_ok(),
            octet != 0
        );
    }
    for values in [
        [b"A=x".as_slice(), b"A=y".as_slice()],
        [b"Z=x".as_slice(), b"A=y".as_slice()],
        [b"=x".as_slice(), b"A=y".as_slice()],
    ] {
        assert!(validate_list(&counted(&values), true, false).is_err());
    }
    let mut all = counted(&[b"\xff=x", b"A=y"]);
    assert!(validate_list(&all, true, false).is_err());
    all = counted(&[b"A=y", b"\xff=x"]);
    assert!(validate_list(&all, true, false).is_ok());
}
#[test]
fn independent_identity_exclusion_exact_bytes_and_hex() {
    for key in COMPILE_IDENTITIES {
        let mut v = key.as_bytes().to_vec();
        v.extend_from_slice(b"=x");
        assert!(validate_list(&counted(&[&v]), true, true).is_err());
        v.insert(0, b'X');
        assert!(validate_list(&counted(&[&v]), true, true).is_ok());
    }
    for key in [SESSION_IDENTITY, SESSION_NONCE] {
        let mut v = key.to_vec();
        v.extend_from_slice(b"=x");
        assert!(validate_list(&counted(&[&v]), true, false).is_err());
        v.insert(0, b'X');
        assert!(validate_list(&counted(&[&v]), true, false).is_ok());
    }
    for at in 0..64 {
        for octet in 0u8..=255 {
            let mut text = [b'0'; 64];
            text[at] = octet;
            assert_eq!(
                parse_hex(&text).is_some(),
                octet.is_ascii_digit() || (b'a'..=b'f').contains(&octet)
            );
        }
    }
}
#[test]
fn independent_sha256_known_and_all_single_byte_preimages() {
    let mut u = LoaderUsageV1::default();
    assert_eq!(
        platform::hash(b"", &mut u).unwrap(),
        parse_hex(b"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855").unwrap()
    );
    assert_eq!(
        platform::hash(b"abc", &mut u).unwrap(),
        parse_hex(b"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad").unwrap()
    );
    let expected=include_bytes!("/Users/andreyyurlov/Documents/dev/mixer/verification/swift-real-profile-loader-independent/sha256-single-byte.bin");
    for octet in 0u8..=255 {
        assert_eq!(
            platform::hash(&[octet], &mut u).unwrap().as_slice(),
            &expected[octet as usize * 32..octet as usize * 32 + 32]
        );
    }
    assert_eq!(
        platform::hash(&vec![b'a'; 1_000_000], &mut u).unwrap(),
        parse_hex(b"cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0").unwrap()
    );
    assert_eq!(u.hash_bytes, 1_000_259);
}
struct ByteReader {
    calls: u32,
    interrupt: u32,
    bytes_per_call: usize,
    fail_on: Option<u32>,
}
impl Read for ByteReader {
    fn read(&mut self, o: &mut [u8]) -> io::Result<usize> {
        self.calls += 1;
        if self.fail_on == Some(self.calls) {
            return Err(io::Error::from_raw_os_error(9));
        }
        if self.calls <= self.interrupt {
            return Err(io::Error::from(io::ErrorKind::Interrupted));
        }
        let n = o.len().min(self.bytes_per_call);
        o[..n].fill(0xa5);
        Ok(n)
    }
}
#[test]
fn independent_block_completes_on_32_and_error_coordinates() {
    for interrupted in 0..=31 {
        let mut r = ByteReader {
            calls: 0,
            interrupt: interrupted,
            bytes_per_call: BLOCK,
            fail_on: None,
        };
        let mut u = LoaderUsageV1::default();
        let mut b = [0; BLOCK];
        read_request(&mut r, &mut b, false, Role::Build, 8192, &mut u).unwrap();
        assert_eq!(r.calls, interrupted + 1);
        assert_eq!(u.read_calls[1], u64::from(r.calls));
        assert_eq!(u.read_bytes[1], 4096);
        assert!(b.iter().all(|b| *b == 0xa5));
    }
    let mut r = ByteReader {
        calls: 0,
        interrupt: 0,
        bytes_per_call: 128,
        fail_on: None,
    };
    let mut u = LoaderUsageV1::default();
    read_request(&mut r, &mut [0; 4096], false, Role::Session, 4096, &mut u).unwrap();
    assert_eq!(r.calls, 32);
    let mut r = ByteReader {
        calls: 0,
        interrupt: 0,
        bytes_per_call: 127,
        fail_on: None,
    };
    let f = read_request(
        &mut r,
        &mut [0; 4096],
        false,
        Role::Session,
        4096,
        &mut LoaderUsageV1::default(),
    )
    .unwrap_err();
    assert_eq!(
        (r.calls, f.kind, f.attempts, f.offset),
        (32, Refusal::Attempts, 32, 8160)
    );
    let mut r = ByteReader {
        calls: 0,
        interrupt: 0,
        bytes_per_call: 1,
        fail_on: Some(32),
    };
    let f = read_request(
        &mut r,
        &mut [0; 4096],
        false,
        Role::Executable,
        500,
        &mut LoaderUsageV1::default(),
    )
    .unwrap_err();
    assert_eq!(
        (
            r.calls,
            f.kind,
            f.attempts,
            f.offset,
            f.original_io().unwrap().raw_os_error()
        ),
        (32, Refusal::Io, 32, 531, Some(9))
    );
}
#[test]
fn independent_cstring_last_accepted_byte_and_retained_empty_file() {
    let mut bytes = [255u8; 4096];
    bytes[4095] = 0;
    let raw = unsafe { platform::c_string(bytes.as_ptr().cast()) }.unwrap();
    assert_eq!(raw.len(), 4095);
    assert!(raw.iter().all(|b| *b == 255));
    if let Some(folder) = std::env::var_os("MIXER_REVIEW_EMPTY_ROOT") {
        let p = std::path::Path::new(&folder).join("empty");
        let mut f = std::fs::OpenOptions::new()
            .create_new(true)
            .read(true)
            .write(true)
            .open(&p)
            .unwrap();
        let id = identity(&f, Role::Source).unwrap();
        let mut u = LoaderUsageV1::default();
        let data = retained(&mut f, Role::Source, 0, id, &mut u, 37).unwrap();
        assert!(data.is_empty());
        assert_eq!(data.capacity(), 0);
        assert_eq!(u.read_calls[0], 1);
        assert_eq!(u.read_bytes[0], 0);
        assert_eq!(u.allocated_peak_requested, 37);
        drop(f);
        std::fs::remove_file(p).unwrap();
    }
}
#[test]
fn independent_emit_late_fixture() {
    let Some(folder) = std::env::var_os("MIXER_REVIEW_FIXTURE_ROOT") else {
        return;
    };
    let folder = std::path::Path::new(&folder);
    let mut f = original_fixture::Fixture::default();
    f.custom_name = Some(b"independent-review-late-function-failure".to_vec());
    f.custom_payload = vec![0xa5; 8 * 1024 * 1024];
    let good = f.bytes();
    let p = validate_swift_reactor(
        &good,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
    assert_eq!(p.observations().validated_bodies, 29);
    drop(p);
    std::fs::write(folder.join("valid.wasm"), &good).unwrap();
    f.bodies[28] = vec![0, 255, 11];
    let late = f.bytes();
    std::fs::write(folder.join("late.wasm"), &late).unwrap();
    assert_eq!(late.len(), 8_390_448);
}
#[test]
fn independent_actual_loader_child() {
    let Some(case) = std::env::var_os("MIXER_REVIEW_CASE") else {
        return;
    };
    let case = case.into_string().unwrap();
    let source_path = std::env::var_os("MIXER_REVIEW_SOURCE").unwrap();
    let build_path = std::env::var_os("MIXER_REVIEW_BUILD").unwrap();
    let session_path = std::env::var_os("MIXER_REVIEW_SESSION").unwrap();
    let executable = std::env::var_os("MIXER_REVIEW_EXECUTABLE").unwrap();
    let mut source = File::open(&source_path).unwrap();
    let mut build = File::open(&build_path).unwrap();
    let mut session = File::open(&session_path).unwrap();
    match case.as_str() {
        "alias-source-session" => session = source.try_clone().unwrap(),
        "alias-source-executable" => source = File::open(&executable).unwrap(),
        "alias-build-session" => session = build.try_clone().unwrap(),
        "alias-build-executable" => build = File::open(&executable).unwrap(),
        "alias-session-executable" => session = File::open(&executable).unwrap(),
        _ => {}
    }
    let original = [
        identity(&source, Role::Source).unwrap(),
        identity(&build, Role::Build).unwrap(),
        identity(&session, Role::Session).unwrap(),
    ];
    let cancel = Cancellation::default();
    let budget = SwiftValidationBudget::default();
    let outcome = if let Some(n) = case.strip_prefix("allocation-") {
        let n = n.parse::<usize>().unwrap();
        let (o, stats) =
            crate::experimental_swift_reactor::allocation_tests::measure_extended(Some(n), || {
                load_selected_retained_profile_v1(source, build, session, budget, &cancel)
            });
        assert_eq!(stats.injected_failures, 1);
        o
    } else {
        load_selected_retained_profile_v1(source, build, session, budget, &cancel)
    };
    assert_eq!(
        original,
        [
            identity(&outcome.files.source, Role::Source).unwrap(),
            identity(&outcome.files.build, Role::Build).unwrap(),
            identity(&outcome.files.session, Role::Session).unwrap()
        ]
    );
    assert!(outcome.files.executable.is_some());
    assert!(outcome
        .files
        .executable
        .as_ref()
        .unwrap()
        .metadata()
        .is_ok());
    if case == "raw-argv" {
        let selected = outcome.selected.unwrap();
        assert_eq!(selected.proof.observations().validated_bodies, 29);
        assert_eq!(selected.validation_budget(), budget);
        println!("INDEPENDENT_SELECTED raw-argv {}", selected.source().len());
        return;
    }
    let failure = match outcome.selected {
        Ok(_) => panic!("unexpected carrier"),
        Err(f) => f,
    };
    if case.starts_with("alias-") {
        assert_eq!(failure.kind, Refusal::AliasedFiles);
        println!("INDEPENDENT_REFUSED {}", case);
        return;
    }
    if let Some(n) = case.strip_prefix("allocation-") {
        let n = n.parse::<usize>().unwrap();
        if n < 4 {
            assert_eq!(failure.kind, Refusal::Allocation);
        } else {
            assert_eq!(failure.kind, Refusal::Validation);
            let v = failure.original_validation().unwrap();
            assert_eq!(
                v.kind,
                super::super::SwiftValidationFailureKind::AllocationFailure
            );
            assert_eq!(v.code, "source_allocation");
        }
        println!(
            "INDEPENDENT_ALLOCATION {} {}",
            n, outcome.usage.allocated_peak_requested
        );
        return;
    }
    assert_eq!(case, "late-failure");
    assert_eq!(failure.kind, Refusal::Validation);
    let actual = *failure.original_validation().unwrap();
    let data = std::fs::read(source_path).unwrap();
    let expected = match validate_swift_reactor(&data, budget, &Cancellation::default()) {
        Ok(_) => panic!("late input validated"),
        Err(f) => f,
    };
    let mut a = actual;
    let mut e = expected;
    a.usage.elapsed_micros = 0;
    e.usage.elapsed_micros = 0;
    assert_eq!(a, e);
    assert_eq!(actual.code, "opcode");
    assert_eq!(actual.function, Some(62));
    assert_eq!(actual.offset, 8_390_447);
    let base = data.len()
        + outcome.files.build.metadata().unwrap().len() as usize
        + outcome.files.session.metadata().unwrap().len() as usize;
    let peak = base
        + actual.usage.source_bytes
        + actual.usage.metadata_peak_reserved
        + actual.usage.scratch_peak_reserved;
    assert_eq!(outcome.usage.allocated_peak_requested, peak);
    assert_eq!(actual.usage.total_peak_reserved, 8_393_796);
    println!(
        "INDEPENDENT_LATE_FAILURE {} {} {} {} {} {}",
        actual.offset,
        actual.usage.source_bytes,
        actual.usage.metadata_peak_reserved,
        actual.usage.scratch_peak_reserved,
        actual.usage.work_used,
        peak
    );
}
