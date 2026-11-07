#![cfg(feature = "experimental-stream-validation")]
mod common;
use common::*;
use mixer_vm::experimental::{
    validate_spans, Failure, FailureKind, Resource, ValidatedSpans, ValidationBudget,
};
use mixer_vm::{Cancellation, Limits, Module, Profile, Type::*, Value};
fn limits(profile: Profile) -> Limits {
    Limits {
        profile,
        ..Limits::default()
    }
}
fn proof(bytes: &[u8], limits: Limits) -> Result<ValidatedSpans, Failure> {
    validate_spans(
        bytes,
        limits,
        ValidationBudget::default(),
        &Cancellation::default(),
    )
}
fn failure(bytes: &[u8], limits: Limits) -> Failure {
    match proof(bytes, limits) {
        Ok(_) => panic!("unexpected proof"),
        Err(e) => e,
    }
}
fn parity(bytes: &[u8], limits: Limits) -> bool {
    let reference = Module::decode(bytes, &limits);
    let stream = proof(bytes, limits);
    assert_eq!(
        reference.is_ok(),
        stream.is_ok(),
        "reference={:?}; stream={:?}",
        reference.as_ref().err(),
        stream.as_ref().err()
    );
    stream.is_ok()
}
fn header() -> Vec<u8> {
    b"\0asm\x01\0\0\0".to_vec()
}
fn raw_body(locals: &[u8], code: &[u8]) -> Vec<u8> {
    let mut m = header();
    section(&mut m, 1, vec![1, 0x60, 0, 0]);
    section(&mut m, 3, vec![1, 0]);
    let mut body = locals.to_vec();
    body.extend_from_slice(code);
    let mut c = vec![1];
    c.extend(u32leb(body.len() as u32));
    c.extend(body);
    section(&mut m, 10, c);
    m
}
fn exports(names: &[&[u8]]) -> Vec<u8> {
    let mut m = header();
    section(&mut m, 1, vec![1, 0x60, 0, 0]);
    section(&mut m, 3, vec![1, 0]);
    let mut e = u32leb(names.len() as u32);
    for name in names {
        e.extend(u32leb(name.len() as u32));
        e.extend_from_slice(name);
        e.extend([0, 0]);
    }
    section(&mut m, 7, e);
    section(&mut m, 10, vec![1, 2, 0, 0x0b]);
    m
}
#[test]
fn all_profiles_complete_spans_and_immutable_source() {
    for p in [
        Profile::IntegerV1,
        Profile::NumericV2,
        Profile::TableMemoryV3,
    ] {
        let mut spec = Spec::one(
            vec![I32, I32],
            Some(I32),
            vec![0x20, 0, 0x20, 1, 0x6a, 0x0b],
        );
        spec.functions
            .push(Function::new(vec![], None, vec![0, 0x1a, 0x0b]));
        spec.memory = Some((1, 2));
        spec.globals = vec![(Value::I64(7), true)];
        spec.data = vec![(13, b"data".to_vec())];
        if p == Profile::TableMemoryV3 {
            spec.table = Some((2, 2));
            spec.elements = vec![(1, vec![0])];
        }
        let mut input = spec.bytes();
        let original = input.clone();
        let sealed = proof(&input, limits(p)).unwrap();
        assert!(parity(&input, limits(p)));
        assert_ne!(sealed.source().as_ptr(), input.as_ptr());
        input.fill(0xff);
        drop(input);
        assert_eq!(sealed.source(), original);
        assert_eq!(sealed.profile(), p);
        assert_eq!(sealed.function_count(), 2);
        assert_eq!(sealed.defined_function_count(), 2);
        assert_eq!(sealed.instruction_count(), 7);
        assert_eq!(
            sealed.function_body(0),
            Some(&[0, 0x20, 0, 0x20, 1, 0x6a, 0x0b][..])
        );
        assert!(sealed.function_body(2).is_none());
        assert_eq!(sealed.global_initializer(0), Some(&[0x42, 7, 0x0b][..]));
        assert!(sealed.global_initializer(1).is_none());
        let d = sealed.data_segment(0).unwrap();
        assert_eq!(
            (d.destination, d.count, d.encoded_payload),
            (13, 4, &b"data"[..])
        );
        assert!(sealed.data_segment(1).is_none());
        if p == Profile::TableMemoryV3 {
            let e = sealed.element_segment(0).unwrap();
            assert_eq!(
                (e.destination, e.count, e.encoded_payload),
                (1, 1, &[0][..])
            );
        }
        let u = sealed.usage();
        assert_eq!(u.source_bytes, original.len());
        assert_eq!(u.scratch_reserved, 0);
        assert!(u.total_peak_reserved >= u.source_bytes + u.metadata_reserved);
    }
}
#[test]
fn rejects_every_uncalled_or_unreachable_bad_body_with_absolute_cursor() {
    let invalid = [
        vec![0xff, 0x0b],
        vec![0, 0xff, 0x0b],
        vec![0, 0x20, 1, 0x0b],
        vec![0x41, 0, 0x0b],
        vec![0x05, 0x0b],
        vec![2, 0x40, 0x0b],
        vec![0x0c, 1, 0x0b],
        vec![0x0b, 1],
    ];
    for code in invalid {
        for p in [
            Profile::IntegerV1,
            Profile::NumericV2,
            Profile::TableMemoryV3,
        ] {
            let mut spec = Spec::one(vec![], None, vec![0x0b]);
            spec.functions
                .push(Function::new(vec![], None, code.clone()));
            let b = spec.bytes();
            assert!(!parity(&b, limits(p)));
            let e = failure(&b, limits(p));
            assert_eq!(e.function, Some(1));
            assert!(e.offset >= 8 && e.offset <= b.len());
        }
    }
    for code in [
        vec![0, 0x6a, 0x1a, 0x0b],
        vec![0, 0x1b, 0x1a, 0x0b],
        vec![0, 0x42, 0, 0x7c, 0x1a, 0x0b],
    ] {
        assert!(parity(&raw_body(&[0], &code), Limits::default()));
    }
    assert!(!parity(
        &raw_body(&[0], &[0, 0x42, 0, 0x6a, 0x1a, 0x0b]),
        Limits::default()
    ));
}
#[test]
fn structured_control_branches_calls_locals_and_globals() {
    let cases = [
        vec![0x41, 0, 4, 0x7f, 0x41, 1, 5, 0x41, 2, 0x0b, 0x1a, 0x0b],
        vec![
            2, 0x40, 3, 0x40, 0x41, 0, 0x0d, 1, 0x0c, 0, 0x0b, 0x0b, 0x0b,
        ],
        vec![
            2, 0x7f, 0x41, 7, 0x41, 0, 0x0e, 2, 0, 0, 0, 0x0b, 0x1a, 0x0b,
        ],
        vec![0x0f, 0x0b],
        vec![0x41, 1, 0x41, 2, 0x41, 0, 0x1b, 0x1a, 0x0b],
    ];
    for code in cases {
        for p in [
            Profile::IntegerV1,
            Profile::NumericV2,
            Profile::TableMemoryV3,
        ] {
            assert!(parity(&raw_body(&[0], &code), limits(p)));
        }
    }
    for code in [
        vec![0x41, 0, 4, 0x7f, 0x41, 1, 0x0b, 0x1a, 0x0b],
        vec![2, 0x7f, 0x41, 0, 0x0e, 1, 0, 1, 0x0b, 0x1a, 0x0b],
        vec![0x42, 0, 0x41, 0, 0x41, 0, 0x1b, 0x1a, 0x0b],
    ] {
        assert!(!parity(&raw_body(&[0], &code), Limits::default()));
    }
    let mut spec = Spec::one(
        vec![I32],
        Some(I32),
        vec![
            0x20, 0, 0x22, 1, 0x21, 1, 0x20, 1, 0x10, 1, 0x24, 0, 0x23, 0, 0x0b,
        ],
    );
    spec.functions[0].locals = vec![I32];
    spec.functions
        .push(Function::new(vec![I32], Some(I32), vec![0x20, 0, 0x0b]));
    spec.globals = vec![(Value::I32(1), true)];
    assert!(parity(&spec.bytes(), Limits::default()));
    spec.globals[0].1 = false;
    assert!(!parity(&spec.bytes(), Limits::default()));
    spec.globals[0].1 = true;
    spec.functions[0].code = vec![0x10, 2, 0x0b];
    assert!(!parity(&spec.bytes(), Limits::default()));
}
#[test]
fn variable_immediates_zero_local_groups_and_all_local_types() {
    for p in [
        Profile::IntegerV1,
        Profile::NumericV2,
        Profile::TableMemoryV3,
    ] {
        let mut groups = u32leb(4096);
        for _ in 0..4096 {
            groups.extend([0, 0x7f]);
        }
        assert!(parity(&raw_body(&groups, &[0x0b]), limits(p)));
        let b = raw_body(&groups, &[0x0b]);
        assert!(proof(&b, limits(p)).unwrap().usage().work_used > 8192);
        let mut labels = vec![2, 0x40, 0x41, 0, 0x0e];
        labels.extend(u32leb(10_000));
        labels.extend(vec![0; 10_001]);
        labels.extend([0x0b, 0x0b]);
        assert!(parity(&raw_body(&[0], &labels), limits(p)));
        let mut invalid = labels.clone();
        invalid[8] = 4;
        assert!(!parity(&raw_body(&[0], &invalid), limits(p)));
    }
    let mut spec = Spec::one(
        vec![I32, I64, F32, F64],
        None,
        vec![
            0x20, 0, 0x21, 4, 0x20, 1, 0x22, 5, 0x1a, 0x20, 2, 0x21, 6, 0x20, 3, 0x21, 7, 0x0b,
        ],
    );
    spec.functions[0].locals = vec![I32, I64, F32, F64];
    assert!(!parity(&spec.bytes(), limits(Profile::IntegerV1)));
    assert!(parity(&spec.bytes(), limits(Profile::NumericV2)));
}
#[test]
fn all_numeric_opcodes_and_prefix_conversions_check_unreachable_types() {
    for op in 0x45..=0xc4 {
        let b = raw_body(&[0], &[0, op, 0x1a, 0x0b]);
        assert!(parity(&b, limits(Profile::NumericV2)));
        assert!(parity(&b, limits(Profile::TableMemoryV3)));
        let float = matches!(op,0x5b..=0x66|0x8b..=0xa6|0xa8..=0xab|0xae..=0xbf);
        assert_eq!(
            parity(&b, limits(Profile::IntegerV1)),
            !float,
            "opcode {op:x}"
        );
    }
    for sub in 0..=7 {
        let b = raw_body(&[0], &[0, 0xfc, sub, 0x1a, 0x0b]);
        assert!(parity(&b, limits(Profile::NumericV2)));
        assert!(!parity(&b, Limits::default()));
    }
    for (op, bytes) in [(0x43, 4), (0x44, 8)] {
        let mut c = vec![op];
        c.extend(vec![0; bytes]);
        c.extend([0x1a, 0x0b]);
        let b = raw_body(&[0], &c);
        assert!(parity(&b, limits(Profile::NumericV2)));
        assert!(!parity(&b, Limits::default()));
    }
}
#[test]
fn memory_numeric_tables_and_bulk_forms_are_profile_bound() {
    for op in 0x28..=0x3e {
        let is_load = op <= 0x35;
        let mut code = vec![0];
        code.extend([op, 0, 0]);
        if is_load {
            code.push(0x1a);
        }
        code.push(0x0b);
        let mut spec = Spec::one(vec![], None, code);
        spec.memory = Some((1, 1));
        assert!(parity(&spec.bytes(), limits(Profile::NumericV2)));
        let floating = [0x2a, 0x2b, 0x38, 0x39].contains(&op);
        assert_eq!(parity(&spec.bytes(), Limits::default()), !floating);
        spec.memory = None;
        assert!(!parity(&spec.bytes(), limits(Profile::NumericV2)));
    }
    for op in [0x3f, 0x40] {
        let mut s = Spec::one(vec![], None, vec![0, op, 0, 0x1a, 0x0b]);
        s.memory = Some((0, 1));
        assert!(parity(&s.bytes(), Limits::default()));
    }
    let mut s = Spec::one(vec![], None, vec![0x41, 0, 0x11, 0, 0, 0x0b]);
    s.table = Some((1, 1));
    s.elements = vec![(0, vec![0])];
    s.explicit_elements = true;
    s.export_table = true;
    assert!(parity(&s.bytes(), limits(Profile::TableMemoryV3)));
    assert!(!parity(&s.bytes(), limits(Profile::NumericV2)));
    s.elements = vec![(u32::MAX, vec![])];
    assert!(parity(&s.bytes(), limits(Profile::TableMemoryV3))); // Instantiation remains a separate operation.
    s.elements = vec![(0, vec![1])];
    assert!(!parity(&s.bytes(), limits(Profile::TableMemoryV3)));
    for sub in [10, 11] {
        let mut c = vec![0, 0xfc, sub, 0];
        if sub == 10 {
            c.push(0);
        }
        c.push(0x0b);
        let mut s = Spec::one(vec![], None, c);
        s.memory = Some((0, 0));
        assert!(parity(&s.bytes(), limits(Profile::TableMemoryV3)));
        assert!(!parity(&s.bytes(), limits(Profile::NumericV2)));
    }
    for c in [
        vec![0, 0x11, 0, 1, 0x0b],
        vec![0, 0xfc, 10, 0, 1, 0x0b],
        vec![0, 0xfc, 11, 1, 0x0b],
        vec![0, 0xfc, 8, 0, 0, 0x0b],
        vec![0xd0, 0x70, 0x0b],
    ] {
        let mut s = Spec::one(vec![], None, c);
        s.memory = Some((1, 1));
        s.table = Some((1, 1));
        assert!(!parity(&s.bytes(), limits(Profile::TableMemoryV3)));
    }
}
#[test]
fn only_existing_imports_and_cross_references_are_accepted() {
    let mut s = Spec::one(vec![], None, vec![0x10, 0, 0x41, 0, 0x10, 1, 0x0b]);
    s.imports = vec![
        ("checkpoint".into(), vec![], None),
        ("abort".into(), vec![I32], None),
    ];
    for p in [
        Profile::IntegerV1,
        Profile::NumericV2,
        Profile::TableMemoryV3,
    ] {
        assert!(parity(&s.bytes(), limits(p)));
    }
    s.imports[1].1 = vec![I64];
    assert!(!parity(&s.bytes(), Limits::default()));
    s.imports[1].1 = vec![I32];
    s.imports[0].0 = "path_open".into();
    assert!(!parity(&s.bytes(), Limits::default()));
    for section_body in [
        vec![1, 1, b'x', 0, 1],
        vec![1, 1, b'x', 3, 0],
        vec![1, 1, b'x', 2, 0],
        vec![1, 1, b'x', 1, 0],
    ] {
        let mut m = header();
        section(&mut m, 7, section_body);
        assert!(!parity(&m, limits(Profile::TableMemoryV3)));
    }
    let mut m = header();
    section(&mut m, 1, vec![1, 0x60, 0, 0]);
    section(&mut m, 3, vec![1, 1]);
    section(&mut m, 10, vec![1, 2, 0, 0x0b]);
    assert!(!parity(&m, Limits::default()));
}
#[test]
fn utf8_duplicate_exports_and_section_integrity() {
    for names in [
        vec![&b""[..]],
        vec![&b"a"[..], &b"b"[..]],
        vec!["é".as_bytes(), "e\u{301}".as_bytes(), "🧑🏽‍💻".as_bytes()],
    ] {
        assert!(parity(&exports(&names), Limits::default()));
    }
    for name in [
        &[0x80][..],
        &[0xc0, 0xaf][..],
        &[0xed, 0xa0, 0x80][..],
        &[0xf4, 0x90, 0x80, 0x80][..],
        &[0xe0, 0x80, 0x80][..],
        &[0xf0, 0x80, 0x80, 0x80][..],
        &[0xf0, 0x9f, 0x92][..],
    ] {
        assert!(!parity(&exports(&[name]), Limits::default()));
    }
    for names in [
        vec![&b"a"[..], &b"a"[..]],
        vec![&b"prefix-z"[..], &b"prefix-a"[..], &b"prefix-a"[..]],
        vec![&b""[..], &b""[..]],
    ] {
        let b = exports(&names);
        assert!(!parity(&b, Limits::default()));
        assert_eq!(failure(&b, Limits::default()).code, "duplicate_export");
    }
    let names: Vec<Vec<u8>> = (0..4096)
        .rev()
        .map(|i| format!("long_shared_name_prefix_{i:04}").into_bytes())
        .collect();
    let refs: Vec<&[u8]> = names.iter().map(Vec::as_slice).collect();
    let b = exports(&refs);
    let u = proof(&b, Limits::default()).unwrap().usage();
    assert!(u.work_used > 100_000);
    assert!(parity(&b, Limits::default()));
    let mut m = header();
    section(&mut m, 0, vec![0, 0xff, 0xfe]);
    assert!(parity(&m, Limits::default()));
    section(&mut m, 1, vec![0]);
    section(&mut m, 1, vec![0]);
    assert!(!parity(&m, Limits::default()));
    for id in [8, 12, 13, 255] {
        let mut m = header();
        section(&mut m, id, vec![0]);
        assert!(!parity(&m, limits(Profile::TableMemoryV3)));
    }
    for m in [
        vec![],
        b"\0asm\x02\0\0\0".to_vec(),
        vec![0, 97, 115, 109, 1, 0, 0, 0, 1, 0x80, 0x80, 0x80, 0x80, 0x10],
        vec![0, 97, 115, 109, 1, 0, 0, 0, 1, 4, 0],
    ] {
        assert!(!parity(&m, Limits::default()));
    }
}
#[test]
fn exact_validation_budgets_and_one_less_fail_closed() {
    let mut s = Spec::one(vec![I32, I64], None, vec![0x20, 0, 0x1a, 0x0b]);
    s.functions[0].locals = vec![I32; 100];
    let b = s.bytes();
    for p in [
        Profile::IntegerV1,
        Profile::NumericV2,
        Profile::TableMemoryV3,
    ] {
        let u = proof(&b, limits(p)).unwrap().usage();
        let exact = ValidationBudget {
            metadata_bytes: u.metadata_peak_reserved,
            scratch_bytes: u.scratch_peak_reserved,
            work_credits: u.work_used,
        };
        assert!(validate_spans(&b, limits(p), exact, &Cancellation::default()).is_ok());
        for resource in [Resource::Metadata, Resource::Scratch, Resource::Work] {
            let mut budget = exact;
            match resource {
                Resource::Metadata => budget.metadata_bytes -= 1,
                Resource::Scratch => budget.scratch_bytes -= 1,
                Resource::Work => budget.work_credits -= 1,
                _ => unreachable!(),
            }
            let e = validate_spans(&b, limits(p), budget, &Cancellation::default())
                .err()
                .unwrap();
            assert_eq!(
                (e.kind, e.resource),
                (FailureKind::ResourceExhausted, Some(resource))
            );
            assert!(e.attempted > e.limit);
        }
        let mut policy = limits(p);
        policy.module_bytes = b.len();
        assert!(proof(&b, policy.clone()).is_ok());
        policy.module_bytes -= 1;
        let e = failure(&b, policy);
        assert_eq!(
            (e.kind, e.resource),
            (FailureKind::ResourceExhausted, Some(Resource::Source))
        );
        assert_eq!(e.usage.source_bytes, 0);
    }
    for budget in [
        ValidationBudget {
            metadata_bytes: 4 * 1024 * 1024 + 1,
            ..ValidationBudget::default()
        },
        ValidationBudget {
            scratch_bytes: 64 * 1024 + 1,
            ..ValidationBudget::default()
        },
        ValidationBudget {
            work_credits: 64_000_001,
            ..ValidationBudget::default()
        },
    ] {
        assert_eq!(
            validate_spans(&b, Limits::default(), budget, &Cancellation::default())
                .err()
                .unwrap()
                .kind,
            FailureKind::InvalidBudget
        );
    }
}
#[test]
fn narrow_profile_limits_cannot_be_evaded() {
    let code = raw_body(&[1, 3, 0x7f], &[0x0b]);
    let mut l = Limits {
        locals: 3,
        ..Limits::default()
    };
    assert!(parity(&code, l.clone()));
    l.locals = 2;
    assert!(!parity(&code, l));
    let code = raw_body(&[0], &[2, 0x40, 0x0b, 0x0b]);
    let mut l = Limits {
        control_depth: 2,
        ..Limits::default()
    };
    assert!(parity(&code, l.clone()));
    l.control_depth = 1;
    assert!(!parity(&code, l));
    let code = raw_body(&[0], &[0x41, 0, 0x41, 1, 0x1a, 0x1a, 0x0b]);
    let mut l = Limits {
        operand_stack: 2,
        ..Limits::default()
    };
    assert!(parity(&code, l.clone()));
    l.operand_stack = 1;
    assert!(!parity(&code, l));
    let code = raw_body(&[0], &[1, 1, 0x0b]);
    let mut l = Limits {
        instructions: 3,
        ..Limits::default()
    };
    assert!(parity(&code, l.clone()));
    l.instructions = 2;
    assert!(!parity(&code, l));
    let mut s = Spec::one(vec![], None, vec![0x0b]);
    s.functions.push(Function::new(vec![], None, vec![0x0b]));
    let l = Limits {
        functions: 1,
        ..Limits::default()
    };
    assert!(!parity(&s.bytes(), l));
    let l = Limits {
        types: 1,
        ..Limits::default()
    };
    assert!(!parity(&s.bytes(), l));
    let mut s = Spec::one(vec![], None, vec![0x0b]);
    s.memory = Some((2, 2));
    assert!(!parity(
        &s.bytes(),
        Limits {
            memory_pages: 1,
            ..Limits::default()
        }
    ));
    s.memory = None;
    s.table = Some((2, 2));
    assert!(!parity(
        &s.bytes(),
        Limits {
            profile: Profile::TableMemoryV3,
            table_elements: 1,
            ..Limits::default()
        }
    ));
    for l in [
        Limits {
            module_bytes: 0,
            ..Limits::default()
        },
        Limits {
            control_depth: 0,
            ..Limits::default()
        },
        Limits {
            instructions: 0,
            ..Limits::default()
        },
        Limits {
            types: 0,
            ..Limits::default()
        },
        Limits {
            functions: 0,
            ..Limits::default()
        },
        Limits {
            operand_stack: 0,
            ..Limits::default()
        },
        Limits {
            call_depth: 0,
            ..Limits::default()
        },
        Limits {
            fuel: 1_000_001,
            ..Limits::default()
        },
        Limits {
            table_elements: 65_537,
            ..Limits::default()
        },
    ] {
        assert!(l.check().is_err());
        assert_eq!(failure(&header(), l).kind, FailureKind::InvalidLimits);
    }
}
#[test]
fn cancellation_never_returns_proof() {
    let b = raw_body(&[0], &[0x0b]);
    let cancellation = Cancellation::default();
    cancellation.cancel();
    let e = validate_spans(
        &b,
        Limits::default(),
        ValidationBudget::default(),
        &cancellation,
    )
    .err()
    .unwrap();
    assert_eq!(e.kind, FailureKind::Cancelled);
    assert_eq!(e.usage.source_bytes, 0);
}
#[test]
fn deterministic_binary_mutations_match_frozen_reference_without_panics() {
    let fixtures = [raw_body(&[0], &[0x0b]), exports(&[b"alpha", b"beta"]), {
        let mut s = Spec::one(vec![I32], Some(I32), vec![0x20, 0, 0x0b]);
        s.memory = Some((1, 2));
        s.table = Some((2, 2));
        s.elements = vec![(0, vec![0])];
        s.data = vec![(0, vec![1, 2, 3])];
        s.bytes()
    }];
    let mut checked = 0;
    for b in fixtures {
        for p in [
            Profile::IntegerV1,
            Profile::NumericV2,
            Profile::TableMemoryV3,
        ] {
            for i in 0..b.len() {
                for x in [0, 0x7f, 0x80, 0xff] {
                    let mut m = b.clone();
                    m[i] = x;
                    parity(&m, limits(p));
                    checked += 1;
                }
            }
            for i in 0..b.len() {
                parity(&b[..i], limits(p));
                checked += 1;
            }
        }
    }
    println!("bounded mutation/truncation comparisons: {checked}");
}

#[test]
fn default_work_ceiling_stops_a_valid_repeated_large_signature() {
    // A compact valid body can demand many parameter visits in unreachable code.
    // This is an intentional validation-budget rejection, not opcode/type parity.
    let mut m = header();
    let mut types = vec![2, 0x60, 0, 0, 0x60];
    types.extend(u32leb(4096));
    types.extend(vec![0x7f; 4096]);
    types.push(0);
    section(&mut m, 1, types);
    section(&mut m, 3, vec![2, 0, 1]);
    let mut body = vec![0, 0];
    for _ in 0..16_384 {
        body.extend([0x10, 1]);
    }
    body.push(0x0b);
    let mut code = vec![2];
    code.extend(u32leb(body.len() as u32));
    code.extend(body);
    code.extend([2, 0, 0x0b]);
    section(&mut m, 10, code);
    assert!(Module::decode(&m, &Limits::default()).is_ok());
    let e = failure(&m, Limits::default());
    assert_eq!(
        (e.kind, e.resource, e.code),
        (
            FailureKind::ResourceExhausted,
            Some(Resource::Work),
            "validation_work"
        )
    );
    assert_eq!(e.limit, 64_000_000);
    assert!(e.usage.work_used <= e.limit);
    assert_eq!(e.function, Some(0));
    println!("intentional additional work-budget rejection of frozen-valid compact module: used={} attempted={} limit={} offset={}",e.usage.work_used,e.attempted,e.limit,e.offset);
}

#[test]
fn published_count_ceilings_exact_and_plus_one() {
    for p in [
        Profile::IntegerV1,
        Profile::NumericV2,
        Profile::TableMemoryV3,
    ] {
        for count in [4096, 4097] {
            let mut locals = vec![1];
            locals.extend(u32leb(count));
            locals.push(0x7f);
            assert_eq!(
                parity(&raw_body(&locals, &[0x0b]), limits(p)),
                count == 4096
            );
        }
        for count in [127, 128] {
            let mut c = vec![];
            for _ in 0..count {
                c.extend([2, 0x40]);
            }
            c.extend(vec![0x0b; count + 1]);
            assert_eq!(parity(&raw_body(&[0], &c), limits(p)), count == 127);
        }
        for count in [199_999, 200_000] {
            let mut c = vec![1; count];
            c.push(0x0b);
            assert_eq!(parity(&raw_body(&[0], &c), limits(p)), count == 199_999);
        }
        for count in [512, 513] {
            let mut m = header();
            let mut t = u32leb(count);
            for _ in 0..count {
                t.extend([0x60, 0, 0]);
            }
            section(&mut m, 1, t);
            assert_eq!(parity(&m, limits(p)), count == 512);
        }
        for count in [1024, 1025] {
            let mut m = header();
            let mut g = u32leb(count);
            for _ in 0..count {
                g.extend([0x7f, 0, 0x41, 0, 0x0b]);
            }
            section(&mut m, 6, g);
            assert_eq!(parity(&m, limits(p)), count == 1024);
        }
        for count in [64, 65] {
            let mut m = header();
            let mut mem = vec![1, 0];
            mem.extend(u32leb(count));
            section(&mut m, 5, mem);
            assert_eq!(parity(&m, limits(p)), count == 64);
        }
    }
    for count in [65_536, 65_537] {
        let mut m = header();
        let mut table = vec![1, 0x70, 0];
        table.extend(u32leb(count));
        section(&mut m, 4, table);
        assert_eq!(parity(&m, limits(Profile::TableMemoryV3)), count == 65_536);
    }
}
