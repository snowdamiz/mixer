#![cfg(feature = "experimental-swift-reactor")]
mod swift_reactor_validation_fixture;
use mixer_vm::experimental_swift_reactor::*;
use mixer_vm::experimental_wasi::WasiFunction;
use mixer_vm::{Cancellation, Type};
use swift_reactor_validation_fixture::*;

fn proof(fixture: &Fixture) -> ValidatedSwiftReactor {
    validate_swift_reactor(
        &fixture.bytes(),
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap()
}
fn failure(fixture: &Fixture) -> SwiftValidationFailure {
    validate_swift_reactor(
        &fixture.bytes(),
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .err()
    .unwrap()
}

#[test]
fn same_policy_original_fixture_proves_complete_validation_only() {
    let fixture = Fixture::default();
    let bytes = fixture.bytes();
    let p = proof(&fixture);
    assert_eq!(p.source(), bytes);
    assert_eq!(p.policy_identity(), "swift-reactor-experiment-v1");
    assert_eq!(p.observations().validated_bodies, 29);
    assert_eq!(p.observations().instructions, 30);
    assert_eq!(p.observations().memory_declared_maximum, None);
    assert_eq!(p.observations().table_declared_maximum, Some(46_713));
    assert_eq!(p.usage().scratch_reserved, 0);
    assert_eq!(p.usage().source_bytes, bytes.len());
    for (index, expected) in WasiFunction::ALL.into_iter().enumerate() {
        assert_eq!(p.resolved_import(index), Some(expected));
    }
    assert_eq!(p.resolved_import(34), None);
    assert!(p.function_body(29).is_none());
}

#[test]
fn exact_order_namespace_names_signatures_and_count_are_mandatory() {
    let mut f = Fixture::default();
    f.imports.swap(0, 1);
    assert_eq!(failure(&f).code, "swift_import_order");
    f = Fixture::default();
    f.imports[0] = f.imports[1].clone();
    assert_eq!(failure(&f).kind, SwiftValidationFailureKind::AbiShape);
    f = Fixture::default();
    f.imports[0].0 = b"mixer".to_vec();
    assert_eq!(failure(&f).code, "swift_import_abi");
    f = Fixture::default();
    f.imports[0].1 = b"checkpoint".to_vec();
    assert_eq!(failure(&f).code, "swift_import_abi");
    f = Fixture::default();
    f.imports[0].3 = 34;
    assert_eq!(failure(&f).code, "swift_import_abi");
    f = Fixture::default();
    f.types[17] = signature(&[Type::I32; 4], &[Type::I32]);
    assert_eq!(failure(&f).code, "swift_import_abi"); // fd_seek requires i64 at parameter 1
    f = Fixture::default();
    f.imports.push(f.imports[0].clone());
    assert_eq!(failure(&f).code, "swift_import_count");
    f = Fixture::default();
    f.imports.pop();
    assert_eq!(failure(&f).code, "export_index"); // absolute exported index62 is now out of bounds
    f = Fixture::default();
    f.imports[0].2 = 1;
    assert_eq!(failure(&f).kind, SwiftValidationFailureKind::Unsupported);
}

#[test]
fn exact_export_indices_signatures_and_declared_limit_forms() {
    let mut f = Fixture::default();
    f.exports[1].2 = 34;
    assert_eq!(failure(&f).code, "swift_export_abi");
    f = Fixture::default();
    f.function_types[1] = 35;
    f.bodies[1] = vec![0, 0x41, 0, 0x0b];
    assert_eq!(failure(&f).code, "swift_export_abi");
    f = Fixture::default();
    f.exports[0].0 = b"other".to_vec();
    assert_eq!(failure(&f).code, "swift_export_abi");
    f = Fixture::default();
    f.exports.push((b"extra".to_vec(), 0, 34));
    assert_eq!(failure(&f).code, "swift_export_count");
    f = Fixture::default();
    f.exports[0] = f.exports[1].clone();
    assert_eq!(failure(&f).code, "duplicate_export");
    f = Fixture::default();
    f.memory = vec![1, 1];
    f.memory.extend(uint(584));
    f.memory.extend(uint(768));
    assert_eq!(failure(&f).code, "swift_memory_shape");
    f = Fixture::default();
    f.memory = vec![1, 0];
    f.memory.extend(uint(583));
    assert_eq!(failure(&f).code, "swift_memory_shape");
    f = Fixture::default();
    f.table = vec![1, 0x70, 0];
    f.table.extend(uint(46_713));
    assert_eq!(failure(&f).code, "swift_table_shape");
    f = Fixture::default();
    f.table = vec![1, 0x70, 1];
    f.table.extend(uint(46_713));
    f.table.extend(uint(46_714));
    assert_eq!(failure(&f).code, "swift_table_shape");
    f = Fixture::default();
    f.start = Some(35);
    assert_eq!(failure(&f).kind, SwiftValidationFailureKind::Unsupported);
}

#[test]
fn all_uncalled_and_unreachable_bodies_receive_operand_type_validation() {
    let mut f = Fixture::default();
    f.bodies[0] = vec![0, 0x41, 0, 0x42, 0, 0x6a, 0x1a, 0x0b];
    let e = failure(&f);
    assert_eq!(e.code, "operand_type");
    assert_eq!(e.function, Some(34));
    assert!(e.offset > 8 && e.offset < f.bytes().len());
    f.bodies[0] = vec![0, 0, 0x41, 0, 0x42, 0, 0x6a, 0x1a, 0x0b];
    assert_eq!(failure(&f).code, "operand_type");
    f.bodies[0] = vec![0, 0, 0x0b]; // truly polymorphic unreachable is valid
    assert_eq!(proof(&f).observations().validated_bodies, 29);
    f.bodies[27] = vec![0, 0xff, 0x0b];
    let e = failure(&f);
    assert_eq!(e.kind, SwiftValidationFailureKind::Unsupported);
    assert_eq!(e.function, Some(61));
}

#[test]
fn active_segments_fit_initial_unsigned_extents_in_original_order() {
    let mut f = Fixture {
        data: vec![
            data_segment(584 * 65_536 - 1, &[8]),
            data_segment(584 * 65_536, &[]),
        ],
        elements: vec![element_segment(46_712, &[34]), element_segment(46_713, &[])],
        ..Fixture::default()
    };
    let p = proof(&f);
    assert_eq!(p.data_segment(0).unwrap().encoded_payload, [8]);
    assert_eq!(p.data_segment(1).unwrap().destination, 584 * 65_536);
    assert_eq!(p.element_segment(0).unwrap().destination, 46_712);
    f.data[0] = data_segment(584 * 65_536, &[8]);
    assert_eq!(failure(&f).code, "swift_data_segment_fit");
    f.data[0] = data_segment(-1, &[]);
    assert_eq!(failure(&f).code, "swift_data_segment_fit");
    f.data.clear();
    f.elements[0] = element_segment(46_713, &[34]);
    assert_eq!(failure(&f).code, "swift_element_segment_fit");
    f.elements[0] = element_segment(-1, &[34]);
    assert_eq!(failure(&f).code, "swift_element_segment_fit");
    f.elements[0] = element_segment(0, &[63]);
    assert_eq!(failure(&f).code, "element_function");
}

#[test]
fn independent_signature_aggregate_local_operand_and_control_ceilings() {
    let mut f = Fixture::default();
    f.types.push(signature(&[Type::I32; 128], &[]));
    proof(&f);
    f.types.push(signature(&[Type::I32; 129], &[]));
    let e = failure(&f);
    assert_eq!((e.attempted, e.limit), (129, 128));
    f = Fixture::default();
    let base = f.types.iter().map(|s| s[1] as usize).sum::<usize>();
    let mut remaining = 8192 - base;
    while remaining != 0 {
        let n = remaining.min(128);
        f.types.push(signature(&vec![Type::I32; n], &[]));
        remaining -= n;
    }
    assert_eq!(proof(&f).observations().type_parameters, 8192);
    f.types.push(signature(&[Type::I32], &[]));
    assert_eq!(failure(&f).code, "type_parameters_total");
    f = Fixture::default();
    f.bodies[0] = vec![1];
    f.bodies[0].extend(uint(256));
    f.bodies[0].extend([0x7f, 0x0b]);
    assert_eq!(proof(&f).observations().max_parameters_plus_locals, 256);
    f.bodies[0] = vec![1];
    f.bodies[0].extend(uint(257));
    f.bodies[0].extend([0x7f, 0x0b]);
    assert_eq!(failure(&f).limit, 256);
    f = Fixture::default();
    f.bodies[0] = Fixture::operand_body(128);
    assert_eq!(proof(&f).observations().max_operand_values, 128);
    f.bodies[0] = Fixture::operand_body(129);
    assert_eq!(failure(&f).code, "profile_operand_limit");
    f.bodies[0] = Fixture::block_body(511);
    assert_eq!(proof(&f).observations().max_control_depth, 512);
    f.bodies[0] = Fixture::block_body(512);
    assert_eq!(failure(&f).code, "profile_control_limit");
    f.bodies[0] = uint(256);
    for _ in 0..256 {
        f.bodies[0].extend([0, 0x7f]);
    }
    f.bodies[0].push(0x0b);
    proof(&f);
    f.bodies[0] = uint(257);
    assert_eq!(failure(&f).limit, 256);
}

#[test]
fn every_budget_narrows_independently_zero_is_real_widening_never_allocates_source() {
    let bytes = Fixture::default().bytes();
    let p = validate_swift_reactor(
        &bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
    let u = p.usage();
    drop(p);
    let exact = SwiftValidationBudget {
        source_bytes: bytes.len(),
        metadata_bytes: u.metadata_peak_reserved,
        scratch_bytes: u.scratch_peak_reserved,
        work_credits: u.work_used,
        ..SwiftValidationBudget::default()
    };
    validate_swift_reactor(&bytes, exact, &Cancellation::default()).unwrap();
    for resource in [
        SwiftValidationResource::Source,
        SwiftValidationResource::Metadata,
        SwiftValidationResource::Scratch,
        SwiftValidationResource::Work,
    ] {
        let mut budget = exact;
        match resource {
            SwiftValidationResource::Source => budget.source_bytes -= 1,
            SwiftValidationResource::Metadata => budget.metadata_bytes -= 1,
            SwiftValidationResource::Scratch => budget.scratch_bytes -= 1,
            SwiftValidationResource::Work => budget.work_credits -= 1,
            _ => unreachable!(),
        }
        let e = validate_swift_reactor(&bytes, budget, &Cancellation::default())
            .err()
            .unwrap();
        assert_eq!(e.kind, SwiftValidationFailureKind::ResourceExhausted);
        assert_eq!(e.resource, Some(resource));
        let mut budget = SwiftValidationBudget::default();
        match resource {
            SwiftValidationResource::Source => budget.source_bytes = 0,
            SwiftValidationResource::Metadata => budget.metadata_bytes = 0,
            SwiftValidationResource::Scratch => budget.scratch_bytes = 0,
            SwiftValidationResource::Work => budget.work_credits = 0,
            _ => unreachable!(),
        }
        assert_eq!(
            validate_swift_reactor(&bytes, budget, &Cancellation::default())
                .err()
                .unwrap()
                .kind,
            SwiftValidationFailureKind::ResourceExhausted
        );
    }
    for field in 0..5 {
        let mut budget = SwiftValidationBudget::default();
        match field {
            0 => budget.source_bytes += 1,
            1 => budget.metadata_bytes += 1,
            2 => budget.scratch_bytes += 1,
            3 => budget.work_credits += 1,
            _ => budget.deadline_ms += 1,
        }
        let e = validate_swift_reactor(&bytes, budget, &Cancellation::default())
            .err()
            .unwrap();
        assert_eq!(e.kind, SwiftValidationFailureKind::InvalidBudget);
        assert_eq!(e.usage.source_bytes, 0);
    }
    let zero = SwiftValidationBudget {
        deadline_ms: 0,
        ..SwiftValidationBudget::default()
    };
    assert_eq!(
        validate_swift_reactor(&bytes, zero, &Cancellation::default())
            .err()
            .unwrap()
            .kind,
        SwiftValidationFailureKind::Deadline
    );
    let c = Cancellation::default();
    c.cancel();
    assert_eq!(
        validate_swift_reactor(&bytes, SwiftValidationBudget::default(), &c)
            .err()
            .unwrap()
            .kind,
        SwiftValidationFailureKind::Cancelled
    );
}

#[test]
fn malformed_unsupported_forms_and_semantic_indices_fail_closed() {
    let mut f = Fixture {
        custom_name: Some(vec![0xff]),
        ..Fixture::default()
    };
    assert_eq!(failure(&f).code, "name_utf8");
    f = Fixture::default();
    f.types.push(vec![0x60, 0, 2, 0x7f, 0x7f]);
    assert_eq!(failure(&f).limit, 1);
    f = Fixture::default();
    f.types.push(vec![0x60, 1, 0x70, 0]);
    assert_eq!(failure(&f).code, "value_type");
    f = Fixture::default();
    f.types.push(vec![0x5f]);
    assert_eq!(failure(&f).code, "function_type");
    f = Fixture::default();
    f.function_types[0] = 100;
    assert_eq!(failure(&f).code, "function_type_index");
    f = Fixture::default();
    f.bodies[0] = vec![0, 0x10, 127, 0x0b];
    assert_eq!(failure(&f).code, "call_index");
    f.bodies[0] = vec![0, 0x20, 0, 0x1a, 0x0b];
    assert_eq!(failure(&f).code, "local_index");
    f.bodies[0] = vec![0, 0x0c, 1, 0x0b];
    assert_eq!(failure(&f).code, "branch_depth");
    f.bodies[0] = vec![0, 0x41, 0, 0x11, 127, 0, 0x0b];
    assert_eq!(failure(&f).code, "indirect_type_index");
    f.bodies[0] = vec![0, 0x41, 0, 0x28, 3, 0, 0x1a, 0x0b];
    assert_eq!(failure(&f).code, "load_alignment");
    f.bodies[0] = vec![0, 0xfc, 8, 0x0b];
    assert_eq!(failure(&f).code, "extended_opcode");
    f = Fixture::default();
    f.globals.push(vec![0x7f, 0, 0x42, 0, 0x0b]);
    assert_eq!(failure(&f).code, "global_initializer_type");
    f.globals[0] = vec![0x7f, 0, 0x41, 0, 0x0b];
    f.bodies[0] = vec![0, 0x41, 0, 0x24, 0, 0x0b];
    assert_eq!(failure(&f).code, "immutable_global");
    let mut bytes = Fixture::default().bytes();
    section(&mut bytes, 1, vec![0]);
    assert_eq!(
        validate_swift_reactor(
            &bytes,
            SwiftValidationBudget::default(),
            &Cancellation::default()
        )
        .err()
        .unwrap()
        .code,
        "section_order"
    );
}

#[test]
fn count_memory_table_and_name_static_ceilings_have_distinct_measurements() {
    let mut f = Fixture::default();
    f.types.resize(513, signature(&[], &[]));
    let e = failure(&f);
    assert_eq!((e.attempted, e.limit), (513, 512));
    f = Fixture::default();
    f.globals.resize(8193, vec![0x7f, 0, 0x41, 0, 0x0b]);
    let e = failure(&f);
    assert_eq!((e.attempted, e.limit), (8193, 8192));
    f = Fixture::default();
    f.exports.resize(4097, (b"x".to_vec(), 0, 34));
    let e = failure(&f);
    assert_eq!((e.attempted, e.limit), (4097, 4096));
    f = Fixture::default();
    f.data.resize(4097, data_segment(0, &[]));
    let e = failure(&f);
    assert_eq!((e.attempted, e.limit), (4097, 4096));
    f = Fixture::default();
    f.elements.resize(4097, element_segment(0, &[]));
    let e = failure(&f);
    assert_eq!((e.attempted, e.limit), (4097, 4096));
    f = Fixture::default();
    f.custom_name = Some(vec![b'a'; 4097]);
    let e = failure(&f);
    assert_eq!((e.attempted, e.limit), (4097, 4096));
    f = Fixture::default();
    f.memory = vec![1, 1];
    f.memory.extend(uint(584));
    f.memory.extend(uint(769));
    let e = failure(&f);
    assert_eq!((e.attempted, e.limit), (769, 768));
    f = Fixture::default();
    f.table = vec![1, 0x70, 1];
    f.table.extend(uint(46_713));
    f.table.extend(uint(65_537));
    let e = failure(&f);
    assert_eq!((e.attempted, e.limit), (65_537, 65_536));
    f = Fixture::default();
    f.function_types.resize(80_000 - 34 + 1, 34);
    let e = failure(&f);
    assert_eq!((e.attempted, e.limit), (79_967, 79_966));
}

#[test]
fn maximum_valid_original_metadata_counts_and_all_bodies_are_checked() {
    let mut f = Fixture::default();
    f.types.resize(512, signature(&[], &[]));
    f.function_types.resize(80_000 - 34, 34);
    f.bodies.resize(80_000 - 34, vec![0, 0x0b]);
    f.globals.resize(8192, vec![0x7f, 0, 0x41, 0, 0x0b]);
    f.data.resize(4096, data_segment(0, &[]));
    f.elements.resize(4096, element_segment(0, &[]));
    f.custom_name = Some(vec![b'a'; 4096]);
    let o = proof(&f).observations();
    assert_eq!(
        (
            o.types,
            o.defined_functions,
            o.validated_bodies,
            o.globals,
            o.data_segments,
            o.element_segments
        ),
        (512, 79_966, 79_966, 8192, 4096, 4096)
    );
}

#[test]
fn instruction_and_source_static_ceilings_are_enforced() {
    let mut f = Fixture::default();
    // 28 other bodies have 29 instructions; this body ends with one instruction.
    f.bodies[0] = vec![1; 8_000_000 - 29];
    f.bodies[0][0] = 0;
    f.bodies[0].push(0x0b);
    assert_eq!(proof(&f).observations().instructions, 8_000_000);
    f.bodies[0].insert(1, 1);
    let e = failure(&f);
    assert_eq!(e.code, "profile_instruction_limit");
    assert_eq!((e.attempted, e.limit), (8_000_001, 8_000_000));
    let oversized = vec![0; 64 * 1024 * 1024 + 1];
    let e = validate_swift_reactor(
        &oversized,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .err()
    .unwrap();
    assert_eq!(e.resource, Some(SwiftValidationResource::Source));
    assert_eq!(e.usage.source_bytes, 0);
    let mut bytes = Fixture::default().bytes();
    // A four-byte section size plus one-byte id fills the exact 64MiB source.
    let payload = vec![0; 64 * 1024 * 1024 - bytes.len() - 5];
    section(&mut bytes, 0, payload);
    assert_eq!(bytes.len(), 64 * 1024 * 1024);
    let p = validate_swift_reactor(
        &bytes,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
    assert_eq!(p.usage().source_bytes, 64 * 1024 * 1024);
}

#[test]
fn every_import_signature_mixed_parameters_locals_and_aggregate_elements_are_checked() {
    for index in 0..34 {
        let mut f = Fixture::default();
        f.types[index] = signature(&[], &[]);
        let e = failure(&f);
        assert_eq!(e.code, "swift_import_abi", "ordered import {index}");
        assert_eq!(e.function, Some(index as u32));
    }
    let mut f = Fixture::default();
    f.types.push(signature(&[Type::I32; 128], &[]));
    f.function_types[0] = 36;
    f.bodies[0] = vec![1];
    f.bodies[0].extend(uint(128));
    f.bodies[0].extend([0x7f, 0x0b]);
    assert_eq!(proof(&f).observations().max_parameters_plus_locals, 256);
    f.bodies[0] = vec![1];
    f.bodies[0].extend(uint(129));
    f.bodies[0].extend([0x7f, 0x0b]);
    let e = failure(&f);
    assert_eq!((e.attempted, e.limit), (129, 128));
    f = Fixture::default();
    f.elements = vec![
        element_segment(0, &vec![34; 32_768]),
        element_segment(0, &vec![34; 32_768]),
    ];
    assert_eq!(proof(&f).observations().element_segments, 2);
    f.elements.push(element_segment(0, &[34]));
    let e = failure(&f);
    assert_eq!(e.resource, Some(SwiftValidationResource::StaticPolicy));
    assert_eq!((e.attempted, e.limit), (1, 0));
}
