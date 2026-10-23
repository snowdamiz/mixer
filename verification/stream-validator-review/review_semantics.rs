#![cfg(feature = "experimental-stream-validation")]
// Original independent review probes. Copied into an immutable export only.
use mixer_vm::experimental::{validate_spans, FailureKind, Resource, ValidationBudget};
use mixer_vm::{Cancellation, Limits, Module, Profile};
use std::io::Write;
use std::process::{Command, Stdio};

fn uint(mut n: u32) -> Vec<u8> {
    let mut b = vec![];
    loop {
        let v = (n & 127) as u8;
        n >>= 7;
        b.push(v | if n == 0 { 0 } else { 128 });
        if n == 0 {
            return b;
        }
    }
}
fn section(m: &mut Vec<u8>, id: u8, bytes: &[u8]) {
    m.push(id);
    m.extend(uint(bytes.len() as u32));
    m.extend(bytes);
}
fn module(result: Option<u8>, bodies: &[Vec<u8>], extra: &[(u8, Vec<u8>)]) -> Vec<u8> {
    let mut m = b"\0asm\x01\0\0\0".to_vec();
    let mut t = vec![1, 0x60, 0];
    match result {
        Some(tpe) => t.extend([1, tpe]),
        None => t.push(0),
    }
    section(&mut m, 1, &t);
    let mut f = uint(bodies.len() as u32);
    f.extend(vec![0; bodies.len()]);
    section(&mut m, 3, &f);
    for (id, bytes) in extra.iter().filter(|(id, _)| *id < 10) {
        section(&mut m, *id, bytes);
    }
    let mut c = uint(bodies.len() as u32);
    for b in bodies {
        c.extend(uint(b.len() as u32));
        c.extend(b);
    }
    section(&mut m, 10, &c);
    for (id, bytes) in extra.iter().filter(|(id, _)| *id > 10) {
        section(&mut m, *id, bytes);
    }
    m
}
fn body(code: &[u8]) -> Vec<u8> {
    let mut b = vec![0];
    b.extend(code);
    b.push(0x0b);
    b
}
fn limits(profile: Profile) -> Limits {
    Limits {
        profile,
        ..Limits::default()
    }
}
fn parity(bytes: &[u8], profile: Profile) -> bool {
    let l = limits(profile);
    let old = Module::decode(bytes, &l).is_ok();
    let new = validate_spans(
        bytes,
        l,
        ValidationBudget::default(),
        &Cancellation::default(),
    );
    assert_eq!(
        old,
        new.is_ok(),
        "frozen parity bytes={bytes:02x?} error={:?}",
        new.err()
    );
    old
}
fn oracle(cases: &[Vec<u8>], profile: Profile, label: &str) {
    // Node is a development reference only. No Node dependency enters the VM.
    let mut child = Command::new("node").args(["-e", "let s='';process.stdin.setEncoding('utf8');process.stdin.on('data',d=>s+=d);process.stdin.on('end',()=>process.stdout.write(s.trim().split('\\n').map(h=>WebAssembly.validate(Buffer.from(h,'hex'))?'1':'0').join('\\n')+'\\n'));" ])
        .stdin(Stdio::piped()).stdout(Stdio::piped()).spawn().unwrap();
    {
        let input = child.stdin.as_mut().unwrap();
        for b in cases {
            for v in b {
                write!(input, "{v:02x}").unwrap();
            }
            writeln!(input).unwrap();
        }
    }
    drop(child.stdin.take());
    let output = child.wait_with_output().unwrap();
    assert!(output.status.success());
    let text = String::from_utf8(output.stdout).unwrap();
    let answers: Vec<_> = text.lines().collect();
    assert_eq!(answers.len(), cases.len());
    let mut accepted = 0;
    for (i, (b, answer)) in cases.iter().zip(answers).enumerate() {
        let valid = parity(b, profile);
        accepted += usize::from(valid);
        assert_eq!(valid, answer == "1", "{label} case={i} bytes={b:02x?}");
    }
    println!(
        "independent Node {label}: cases={} accepted={accepted} rejected={}",
        cases.len(),
        cases.len() - accepted
    );
}

#[test]
fn short_integer_sequences_in_reachable_unreachable_and_nested_frames() {
    let tokens: &[&[u8]] = &[
        &[0],
        &[1],
        &[0x41, 0],
        &[0x42, 0],
        &[0x1a],
        &[0x1b],
        &[0x6a],
        &[0x7c],
        &[0x0f],
        &[0x0c, 0],
        &[0x0d, 0],
        &[0x10, 0],
        &[0x20, 0],
    ];
    let mut cases = vec![];
    for result in [None, Some(0x7f), Some(0x7e)] {
        for nested in [false, true] {
            for n in 0..=3u32 {
                for mut encoded in 0..tokens.len().pow(n) {
                    let mut code = vec![];
                    if nested {
                        code.extend([2, result.unwrap_or(0x40)]);
                    }
                    for _ in 0..n {
                        code.extend(tokens[encoded % tokens.len()]);
                        encoded /= tokens.len();
                    }
                    if nested {
                        code.push(0x0b);
                    }
                    cases.push(module(result, &[body(&code)], &[]));
                }
            }
        }
    }
    oracle(&cases, Profile::IntegerV1, "integer-short-frames");
    for p in [Profile::NumericV2, Profile::TableMemoryV3] {
        for b in &cases {
            parity(b, p);
        }
    }
}

#[test]
fn typed_branch_tables_and_if_arm_joins_use_real_stack_types() {
    let mut cases = vec![];
    for outer in [0x40, 0x7f, 0x7e, 0x7d, 0x7c] {
        for inner in [0x40, 0x7f, 0x7e, 0x7d, 0x7c] {
            for loop_kind in [2, 3] {
                for unreachable in [false, true] {
                    for targets in [[0, 0], [0, 1], [1, 0], [1, 1], [2, 0], [0, 3]] {
                        let mut c = vec![2, outer, loop_kind, inner];
                        if unreachable {
                            c.push(0);
                        }
                        c.extend([0x41, 0, 0x0e, 1, targets[0], targets[1], 0x0b, 0x0b]);
                        cases.push(module(None, &[body(&c)], &[]));
                    }
                }
            }
        }
    }
    for t in [0x40, 0x7f, 0x7e, 0x7d, 0x7c] {
        for a in [&[][..], &[0][..], &[0x41, 0][..], &[0x42, 0][..]] {
            for b in [&[][..], &[0][..], &[0x41, 0][..], &[0x42, 0][..]] {
                let mut c = vec![0x41, 0, 4, t];
                c.extend(a);
                c.push(5);
                c.extend(b);
                c.push(0x0b);
                if t != 0x40 {
                    c.push(0x1a);
                }
                cases.push(module(None, &[body(&c)], &[]));
            }
        }
    }
    oracle(&cases, Profile::NumericV2, "branch-table-if-joins");
}

#[test]
fn uncalled_bodies_and_unreachable_indices_are_never_skipped() {
    let invalid = [
        vec![0, 0x20, 0, 0x1a, 0x0b],
        vec![0, 0, 0x23, 0, 0x1a, 0x0b],
        vec![0, 0, 0x10, 2, 0x0b],
        vec![0, 0, 0xff, 0x0b],
        vec![0, 0, 0x41, 0x80],
        vec![0, 0x0b, 1],
        vec![],
    ];
    for p in [
        Profile::IntegerV1,
        Profile::NumericV2,
        Profile::TableMemoryV3,
    ] {
        for bad in &invalid {
            let b = module(None, &[body(&[]), bad.clone()], &[]);
            assert!(!parity(&b, p));
            let e = validate_spans(
                &b,
                limits(p),
                ValidationBudget::default(),
                &Cancellation::default(),
            )
            .err()
            .unwrap();
            assert_eq!(e.function, Some(1));
            assert!(e.offset <= b.len());
        }
    }
    let cases: Vec<_> = invalid
        .iter()
        .map(|bad| module(None, &[body(&[]), bad.clone()], &[]))
        .collect();
    oracle(&cases, Profile::IntegerV1, "uncalled-bodies");
}

#[test]
fn numeric_memory_and_indirect_types_remain_context_checked_after_unreachable() {
    let mut cases = vec![];
    let extras = [
        (4, vec![1, 0x70, 1, 1, 1]),
        (5, vec![1, 1, 0, 1]),
        (6, vec![1, 0x7e, 0, 0x42, 0, 0x0b]),
    ];
    for op in 0x28..=0x3e {
        for align in [0, 1, 2, 3, 4, 31] {
            for prefix in [&[0][..], &[0, 0x42, 0][..], &[0, 0x41, 0][..]] {
                let mut c = prefix.to_vec();
                c.extend([op, align, 0]);
                if op <= 0x35 {
                    c.push(0x1a);
                }
                cases.push(module(None, &[body(&c)], &extras));
            }
        }
    }
    for sub in [0, 1, 7, 10, 11] {
        for prefix in [&[0][..], &[0, 0x42, 0][..], &[0, 0x41, 0][..]] {
            let mut c = prefix.to_vec();
            c.extend([0xfc, sub]);
            if sub == 10 {
                c.extend([0, 0]);
            } else if sub == 11 {
                c.push(0);
            } else {
                c.push(0x1a);
            }
            cases.push(module(None, &[body(&c)], &extras));
        }
    }
    for (ty, table) in [(0, 0), (1, 0), (0, 1), (255, 0)] {
        cases.push(module(None, &[body(&[0, 0x11, ty, table])], &extras));
    }
    for c in [&[0, 0x24, 0][..], &[0, 0x23, 1, 0x1a][..]] {
        cases.push(module(None, &[body(c)], &extras));
    }
    oracle(
        &cases,
        Profile::TableMemoryV3,
        "memory-call-indirect-context",
    );
}

#[test]
fn spans_own_exact_source_and_remain_stable_after_caller_drop_and_move() {
    let data = vec![1, 0, 0x41, 0x7f, 0x0b, 4, 0xde, 0xad, 0xbe, 0xef];
    let element = vec![1, 2, 0, 0x41, 0, 0x0b, 0, 1, 0];
    let extra = [
        (4, vec![1, 0x70, 1, 1, 1]),
        (5, vec![1, 1, 0, 1]),
        (6, vec![1, 0x7e, 1, 0x42, 0x7f, 0x0b]),
        (9, element),
        (11, data),
    ];
    let mut input = module(None, &[body(&[])], &extra);
    let original = input.clone();
    let input_pointer = input.as_ptr();
    let proof = validate_spans(
        &input,
        limits(Profile::TableMemoryV3),
        ValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
    assert_ne!(proof.source().as_ptr(), input_pointer);
    input.fill(0xff);
    drop(input);
    let moved = Box::new(proof);
    assert_eq!(moved.source(), original);
    let source = moved.source();
    for span in [
        moved.function_body(0).unwrap(),
        moved.global_initializer(0).unwrap(),
        moved.data_segment(0).unwrap().encoded_payload,
        moved.element_segment(0).unwrap().encoded_payload,
    ] {
        let start = span.as_ptr() as usize;
        let base = source.as_ptr() as usize;
        assert!(start >= base && start + span.len() <= base + source.len());
    }
    assert_eq!(moved.function_body(0), Some(&[0, 0x0b][..]));
    assert!(moved.function_body(usize::MAX).is_none());
    assert!(moved.global_initializer(usize::MAX).is_none());
    assert_eq!(moved.data_segment(0).unwrap().destination, u32::MAX);
    assert_eq!(
        moved.data_segment(0).unwrap().encoded_payload,
        [0xde, 0xad, 0xbe, 0xef]
    );
    assert_eq!(moved.element_segment(0).unwrap().encoded_payload, [0]);
    assert_eq!(moved.usage().source_bytes, original.len());
    assert_eq!(moved.usage().scratch_reserved, 0);
}

#[test]
fn every_work_prefix_and_capacity_boundary_fails_closed_without_partial_proof() {
    let mut code = vec![0];
    for _ in 0..32 {
        code.extend([0x41, 0, 0x1a]);
    }
    let input = module(None, &[body(&code)], &[]);
    let cancel = Cancellation::default();
    let usage = validate_spans(
        &input,
        Limits::default(),
        ValidationBudget::default(),
        &cancel,
    )
    .unwrap()
    .usage();
    for credit in 0..usage.work_used {
        let e = validate_spans(
            &input,
            Limits::default(),
            ValidationBudget {
                work_credits: credit,
                ..ValidationBudget::default()
            },
            &cancel,
        )
        .err()
        .unwrap();
        assert_eq!(
            (e.kind, e.resource),
            (FailureKind::ResourceExhausted, Some(Resource::Work))
        );
        assert!(e.attempted > e.limit && e.usage.work_used <= credit);
    }
    for resource in [Resource::Metadata, Resource::Scratch] {
        let peak = if resource == Resource::Metadata {
            usage.metadata_peak_reserved
        } else {
            usage.scratch_peak_reserved
        };
        for capacity in [0, peak - 1, peak] {
            let mut b = ValidationBudget::default();
            if resource == Resource::Metadata {
                b.metadata_bytes = capacity;
            } else {
                b.scratch_bytes = capacity;
            }
            let result = validate_spans(&input, Limits::default(), b, &cancel);
            assert_eq!(result.is_ok(), capacity == peak);
            if let Err(e) = result {
                assert_eq!(e.resource, Some(resource));
                assert!(e.attempted > e.limit);
            }
        }
    }
    println!(
        "independent exhaustive work-prefix rejections: {}",
        usage.work_used
    );
}

#[test]
fn leb_padding_and_long_utf8_names_keep_binary_identity() {
    let mut cases = vec![];
    for suffix in [
        &[0][..],
        &[0x80, 0][..],
        &[0x80, 0x80, 0x80, 0x80, 0][..],
        &[0x80, 0x80, 0x80, 0x80, 0x10][..],
    ] {
        let mut c = vec![0x41];
        c.extend(suffix);
        c.push(0x1a);
        cases.push(module(None, &[body(&c)], &[]));
    }
    let mut names = vec![
        vec![0; 4096],
        "é".repeat(2048).into_bytes(),
        "e\u{301}".repeat(1365).into_bytes(),
        vec![0xf4, 0x8f, 0xbf, 0xbf],
        vec![0xed, 0xa0, 0x80],
        vec![0xc0, 0x80],
    ];
    for name in names.drain(..) {
        let mut ex = vec![1];
        ex.extend(uint(name.len() as u32));
        ex.extend(name);
        ex.extend([0, 0]);
        cases.push(module(None, &[body(&[])], &[(7, ex)]));
    }
    oracle(&cases, Profile::IntegerV1, "leb-and-utf8");
}
