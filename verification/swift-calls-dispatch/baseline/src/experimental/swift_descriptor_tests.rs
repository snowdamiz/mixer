//! Original public-validated same-ABI modules; no reactor execution or relaxed policy.
use super::descriptors::{GlobalView, MemoryExecutionView, SignatureView, TableExecutionView};
use super::swift::{validate_swift_reactor, SwiftValidationBudget, ValidatedSwiftReactor};
use crate::experimental_swift_reactor::allocation_tests::measure;
use crate::experimental_wasi::WasiFunction;
use crate::{Cancellation, Type};
use std::ops::Range;

struct ExpectedGlobal {
    ty: Type,
    mutable: bool,
    initializer: Range<usize>,
}
struct ExpectedSegment {
    destination: u32,
    count: u32,
    payload: Range<usize>,
}
struct Fixture {
    bytes: Vec<u8>,
    bodies: Vec<Range<usize>>,
    function_types: Vec<u32>,
    signatures: Vec<(Vec<Type>, Option<Type>)>,
    globals: Vec<ExpectedGlobal>,
    data: Vec<ExpectedSegment>,
    elements: Vec<ExpectedSegment>,
}
fn uint(mut n: u32, bytes: &mut Vec<u8>) {
    loop {
        let byte = (n & 127) as u8;
        n >>= 7;
        bytes.push(byte | if n == 0 { 0 } else { 128 });
        if n == 0 {
            return;
        }
    }
}
fn text(value: &[u8], bytes: &mut Vec<u8>) {
    uint(value.len() as u32, bytes);
    bytes.extend_from_slice(value);
}
fn section(id: u8, payload: &[u8], module: &mut Vec<u8>) -> usize {
    module.push(id);
    uint(payload.len() as u32, module);
    let start = module.len();
    module.extend_from_slice(payload);
    start
}
fn ty(value: Type) -> u8 {
    match value {
        Type::I32 => 0x7f,
        Type::I64 => 0x7e,
        Type::F32 => 0x7d,
        Type::F64 => 0x7c,
    }
}
fn relocate(range: &mut Range<usize>, base: usize) {
    range.start += base;
    range.end += base;
}
impl Fixture {
    fn new() -> Self {
        Self::with_initializers(true)
    }
    fn with_initializers(initializers: bool) -> Self {
        let mut bytes = b"\0asm\x01\0\0\0".to_vec();
        // A leading custom section makes absolute offsets differ from every
        // section-local cursor. The retained source remains a small real module.
        section(0, b"\x05owned\x00\x41\x0b\xff", &mut bytes);
        let mut signatures: Vec<_> = WasiFunction::ALL
            .into_iter()
            .map(|import| {
                (
                    import.parameters().to_vec(),
                    import.results().first().copied(),
                )
            })
            .collect();
        signatures.extend([
            (vec![], None),
            (vec![], Some(Type::I32)),
            (
                vec![Type::I32, Type::I64, Type::F32, Type::F64],
                Some(Type::F64),
            ),
            (vec![], Some(Type::F32)),
        ]);
        let mut types = Vec::new();
        uint(signatures.len() as u32, &mut types);
        for (params, result) in &signatures {
            types.push(0x60);
            uint(params.len() as u32, &mut types);
            types.extend(params.iter().copied().map(ty));
            uint(u32::from(result.is_some()), &mut types);
            types.extend(result.iter().copied().map(ty));
        }
        section(1, &types, &mut bytes);
        let mut imports = vec![34];
        for (index, import) in WasiFunction::ALL.into_iter().enumerate() {
            text(b"wasi_snapshot_preview1", &mut imports);
            text(import.name(), &mut imports);
            imports.push(0);
            uint(index as u32, &mut imports);
        }
        section(2, &imports, &mut bytes);
        // Absolute function132 makes the encoded segment include multi-byte
        // indices without allocating a large source or any guest runtime state.
        let mut function_types = vec![34; 99];
        function_types[0] = 36;
        function_types[28] = 35;
        function_types[98] = 37;
        let mut functions = vec![99];
        for index in &function_types {
            uint(*index, &mut functions);
        }
        section(3, &functions, &mut bytes);
        let mut table = vec![1, 0x70, 1];
        uint(46_713, &mut table);
        uint(46_713, &mut table);
        section(4, &table, &mut bytes);
        let mut memory = vec![1, 0];
        uint(584, &mut memory);
        section(5, &memory, &mut bytes);
        let mut globals = Vec::new();
        let mut declarations = vec![4];
        for (value_type, mutable, initializer) in [
            (Type::I32, false, vec![0x41, 0xff, 0x00, 0x0b]),
            (Type::I64, true, vec![0x42, 0x7f, 0x0b]),
            (Type::F32, true, vec![0x43, 0x01, 0x00, 0xc0, 0x7f, 0x0b]),
            (Type::F64, false, vec![0x44, 1, 2, 3, 4, 5, 6, 7, 8, 0x0b]),
        ] {
            declarations.extend([ty(value_type), u8::from(mutable)]);
            let start = declarations.len();
            declarations.extend(initializer);
            globals.push(ExpectedGlobal {
                ty: value_type,
                mutable,
                initializer: start..declarations.len(),
            });
        }
        if initializers {
            let base = section(6, &declarations, &mut bytes);
            for global in &mut globals {
                relocate(&mut global.initializer, base);
            }
        } else {
            globals.clear();
        }
        let mut exports = vec![3];
        for (name, kind, index) in [
            (b"memory".as_slice(), 2, 0),
            (b"_initialize".as_slice(), 0, 35),
            (b"mixer_fieldlog_corpus_v1".as_slice(), 0, 62),
        ] {
            text(name, &mut exports);
            exports.push(kind);
            uint(index, &mut exports);
        }
        section(7, &exports, &mut bytes);
        let mut elements = Vec::new();
        let mut encoded = vec![3];
        for (explicit, destination, count, payload) in [
            (false, 3, 6, &[0, 33, 0xa2, 0, 62, 0x80, 1, 0x84, 1][..]),
            (true, 4, 2, &[35, 34][..]),
            (false, 46_713, 0, &[][..]),
        ] {
            uint(if explicit { 2 } else { 0 }, &mut encoded);
            if explicit {
                encoded.push(0);
            }
            encoded.push(0x41);
            uint(destination, &mut encoded); // these unsigned values also encode valid positive i32
            encoded.push(0x0b);
            if explicit {
                encoded.push(0); // elemkind funcref
            }
            uint(count, &mut encoded);
            let start = encoded.len();
            encoded.extend_from_slice(payload);
            elements.push(ExpectedSegment {
                destination,
                count,
                payload: start..encoded.len(),
            });
        }
        if initializers {
            let base = section(9, &encoded, &mut bytes);
            for segment in &mut elements {
                relocate(&mut segment.payload, base);
            }
        } else {
            elements.clear();
        }
        let mut bodies = Vec::new();
        let mut code = vec![99];
        for ordinal in 0..99 {
            let body = match ordinal {
                0 => vec![0, 0x20, 3, 0x0b],
                28 => vec![0, 0x41, 0, 0x0b],
                98 => vec![0, 0x43, 0, 0, 0, 0, 0x0b],
                _ => {
                    let mut body = vec![0];
                    body.extend(std::iter::repeat_n(0x01, ordinal % 3));
                    body.push(0x0b);
                    body
                }
            };
            uint(body.len() as u32, &mut code);
            let start = code.len();
            code.extend(body);
            bodies.push(start..code.len());
        }
        let base = section(10, &code, &mut bytes);
        for body in &mut bodies {
            relocate(body, base);
        }
        let mut data = Vec::new();
        let mut encoded = vec![4];
        for (explicit, destination, payload) in [
            (false, 5, &[0xde, 0xad][..]),
            (true, 6, &[0xbe, 0xef, 0x11][..]),
            (false, 584 * 65_536, &[][..]),
            (false, 6, &[][..]),
        ] {
            uint(if explicit { 2 } else { 0 }, &mut encoded);
            if explicit {
                encoded.push(0);
            }
            encoded.push(0x41);
            uint(destination, &mut encoded);
            encoded.push(0x0b);
            uint(payload.len() as u32, &mut encoded);
            let start = encoded.len();
            encoded.extend_from_slice(payload);
            data.push(ExpectedSegment {
                destination,
                count: payload.len() as u32,
                payload: start..encoded.len(),
            });
        }
        if initializers {
            let base = section(11, &encoded, &mut bytes);
            for segment in &mut data {
                relocate(&mut segment.payload, base);
            }
        } else {
            data.clear();
        }
        Self {
            bytes,
            bodies,
            function_types,
            signatures,
            globals,
            data,
            elements,
        }
    }
    fn proof(&self) -> ValidatedSwiftReactor {
        validate_swift_reactor(
            &self.bytes,
            SwiftValidationBudget::default(),
            &Cancellation::default(),
        )
        .unwrap()
    }
}
fn retained_slice(source: &[u8], range: Range<usize>, borrowed: &[u8]) {
    assert!(range.start <= range.end && range.end <= source.len());
    let expected = &source[range];
    assert_eq!(borrowed, expected);
    assert_eq!(borrowed.as_ptr(), expected.as_ptr());
}

#[test]
fn swift_descriptor_signatures_and_functions_use_absolute_indices() {
    let fixture = Fixture::new();
    let proof = fixture.proof();
    assert_eq!(proof.observations().defined_functions, 99);
    assert_eq!(proof.observations().validated_bodies, 99);
    for (absolute, import) in WasiFunction::ALL.into_iter().enumerate() {
        let signature = proof.execution_signature(absolute as u32).unwrap();
        assert_eq!(signature.params, import.parameters());
        assert_eq!(signature.result.as_slice(), import.results());
        assert_eq!(signature, proof.execution_type(absolute as u32).unwrap());
        assert_eq!(
            signature.params.as_ptr(),
            proof
                .execution_type(absolute as u32)
                .unwrap()
                .params
                .as_ptr()
        );
        assert!(proof.execution_function(absolute as u32).is_none());
        assert_eq!(proof.execution_imports()[absolute], import);
        assert_eq!(proof.resolved_import(absolute), Some(import));
    }
    for (ordinal, expected) in fixture.bodies.iter().enumerate() {
        let absolute = ordinal as u32 + 34;
        let function = proof.execution_function(absolute).unwrap();
        assert_eq!(function.absolute_index, absolute);
        assert_eq!(function.type_index, fixture.function_types[ordinal]);
        assert_eq!(function.body_offset, expected.start);
        retained_slice(proof.source(), expected.clone(), function.body);
        assert_eq!(
            function.body.as_ptr(),
            proof.function_body(ordinal).unwrap().as_ptr()
        );
        let signature = proof.execution_signature(absolute).unwrap();
        assert_eq!(
            signature,
            proof.execution_type(function.type_index).unwrap()
        );
        assert_eq!(
            signature.params.as_ptr(),
            proof
                .execution_type(function.type_index)
                .unwrap()
                .params
                .as_ptr()
        );
    }
    for (index, (params, result)) in fixture.signatures.iter().enumerate() {
        assert_eq!(
            proof.execution_type(index as u32).unwrap(),
            SignatureView {
                params,
                result: *result
            }
        );
    }
    for absent in [133, 134, u32::MAX] {
        assert!(proof.execution_signature(absent).is_none());
        assert!(proof.execution_function(absent).is_none());
    }
    for absent in [38, 39, u32::MAX] {
        assert!(proof.execution_type(absent).is_none());
    }
    assert_eq!(proof.execution_imports().len(), 34);
    assert_eq!(
        proof.execution_imports().as_ptr(),
        proof.execution_imports().as_ptr()
    );
    assert!(proof.resolved_import(34).is_none());
}

#[test]
fn swift_descriptor_ranges_cursors_and_encoded_segment_order_are_exact() {
    let fixture = Fixture::new();
    let proof = fixture.proof();
    assert_eq!(proof.source(), fixture.bytes);
    assert_eq!(proof.source().len(), fixture.bytes.len());
    assert_eq!(proof.execution_global_count(), fixture.globals.len());
    for (index, expected) in fixture.globals.iter().enumerate() {
        let global = proof.execution_global(index).unwrap();
        assert_eq!((global.ty, global.mutable), (expected.ty, expected.mutable));
        assert_eq!(
            proof.execution_global_initializer_offset(index),
            Some(expected.initializer.start)
        );
        retained_slice(
            proof.source(),
            expected.initializer.clone(),
            global.initializer,
        );
        assert_eq!(
            global.initializer.as_ptr(),
            proof.global_initializer(index).unwrap().as_ptr()
        );
    }
    assert_eq!(proof.execution_data_count(), fixture.data.len());
    assert_eq!(proof.execution_element_count(), fixture.elements.len());
    for (elements, expected) in [(false, &fixture.data), (true, &fixture.elements)] {
        let mut previous_end = 0;
        for (index, expected) in expected.iter().enumerate() {
            let (segment, public) = if elements {
                (
                    proof.execution_element(index).unwrap(),
                    proof.element_segment(index).unwrap(),
                )
            } else {
                (
                    proof.execution_data(index).unwrap(),
                    proof.data_segment(index).unwrap(),
                )
            };
            assert_eq!(
                (segment.destination, segment.count),
                (expected.destination, expected.count)
            );
            assert_eq!(
                (public.destination, public.count),
                (expected.destination, expected.count)
            );
            assert_eq!(segment.payload_offset, expected.payload.start);
            assert!(segment.payload_offset >= previous_end);
            previous_end = expected.payload.end;
            retained_slice(
                proof.source(),
                expected.payload.clone(),
                segment.encoded_payload,
            );
            assert_eq!(
                segment.encoded_payload.as_ptr(),
                public.encoded_payload.as_ptr()
            );
        }
    }
    // The first two segments overlap in destination. The last empty data
    // payload sits exactly at retained-source end and must remain accessible.
    assert_eq!(
        proof.execution_data(0).unwrap().destination + 1,
        proof.execution_data(1).unwrap().destination
    );
    assert_eq!(
        proof.execution_element(0).unwrap().destination + 1,
        proof.execution_element(1).unwrap().destination
    );
    assert_eq!(
        proof.execution_data(3).unwrap().payload_offset,
        proof.source().len()
    );
    assert!(proof.execution_data(3).unwrap().encoded_payload.is_empty());
    assert_eq!(proof.execution_element(2).unwrap().count, 0);
    assert_eq!(
        proof.execution_element(0).unwrap().encoded_payload,
        &[0, 33, 0xa2, 0, 62, 0x80, 1, 0x84, 1]
    );
    assert_eq!(proof.execution_element(0).unwrap().count, 6);
    for absent in [4, 5, usize::MAX] {
        assert!(proof.execution_global(absent).is_none());
        assert!(proof.execution_global_initializer_offset(absent).is_none());
        assert!(proof.execution_data(absent).is_none());
    }
    for absent in [3, 4, usize::MAX] {
        assert!(proof.execution_element(absent).is_none());
    }
}

#[test]
fn swift_descriptor_empty_collections_have_no_fabricated_entry_or_offset() {
    let fixture = Fixture::with_initializers(false);
    let proof = fixture.proof();
    assert_eq!(
        (
            proof.execution_global_count(),
            proof.execution_data_count(),
            proof.execution_element_count()
        ),
        (0, 0, 0)
    );
    for absent in [0, 1, usize::MAX] {
        assert!(proof.execution_global(absent).is_none());
        assert!(proof.execution_global_initializer_offset(absent).is_none());
        assert!(proof.execution_data(absent).is_none());
        assert!(proof.execution_element(absent).is_none());
    }
    assert_eq!(proof.source(), fixture.bytes);
    assert_eq!(
        proof.execution_function(132).unwrap().body_offset + 7,
        proof.source().len()
    );
}

#[test]
fn swift_descriptor_declared_and_stored_host_limits_remain_distinct() {
    let proof = Fixture::new().proof();
    assert_eq!(
        proof.execution_memory(),
        Some(MemoryExecutionView {
            minimum: 584,
            declared_maximum: None,
            host_maximum: 768,
        })
    );
    assert_eq!(
        proof.execution_table(),
        Some(TableExecutionView {
            minimum: 46_713,
            declared_maximum: Some(46_713),
            host_maximum: 46_713,
        })
    );
    let policy = proof.decode_policy();
    assert!(policy.floats() && policy.tables());
    assert!(!policy.legacy_imports());
    assert_eq!(policy.module_bytes(), 64 * 1024 * 1024);
    assert!(proof.source().len() < policy.module_bytes());
    assert_eq!(policy.table_elements(), 65_536);
    assert_eq!(policy.memory_pages(), 768);
    assert_eq!(
        (
            policy.parameters_per_signature(),
            policy.parameters_plus_locals(),
            policy.local_groups()
        ),
        (128, 256, 256)
    );
    assert_eq!(
        (policy.instructions(), policy.control_depth()),
        (8_000_000, 512)
    );
}

#[test]
fn swift_descriptor_repeated_immutable_borrows_allocate_nothing_and_preserve_usage() {
    let fixture = Fixture::new();
    let proof = fixture.proof();
    let usage = proof.usage();
    let observations = proof.observations();
    let source = proof.source();
    let (_, stats) = measure(|| {
        for _ in 0..32 {
            for function in 0..133 {
                std::hint::black_box(proof.execution_signature(function));
                std::hint::black_box(proof.execution_function(function));
            }
            for index in 0..38 {
                std::hint::black_box(proof.execution_type(index));
            }
            for index in 0..=4 {
                std::hint::black_box(proof.execution_global(index));
                std::hint::black_box(proof.execution_global_initializer_offset(index));
                std::hint::black_box(proof.execution_data(index));
                std::hint::black_box(proof.execution_element(index));
            }
            std::hint::black_box((
                proof.execution_global_count(),
                proof.execution_data_count(),
                proof.execution_element_count(),
            ));
            std::hint::black_box((proof.execution_memory(), proof.execution_table()));
            std::hint::black_box(proof.execution_imports());
            std::hint::black_box(proof.decode_policy());
        }
    });
    assert_eq!(
        (
            stats.allocations,
            stats.reallocations,
            stats.deallocations,
            stats.attempts
        ),
        (0, 0, 0, 0)
    );
    assert_eq!(proof.usage(), usage);
    assert_eq!(proof.observations(), observations);
    assert_eq!(proof.source().as_ptr(), source.as_ptr());
    assert_eq!(proof.source(), fixture.bytes);
    println!("Swift descriptor immutable borrows: 32 complete traversals; allocation/reallocation/deallocation requests=0; validation usage/source unchanged; no target execution");
}

#[test]
#[cfg(target_pointer_width = "64")]
fn swift_descriptor_preserved_layouts_are_measured() {
    macro_rules! layout {
        ($type:ty) => {
            (std::mem::size_of::<$type>(), std::mem::align_of::<$type>())
        };
    }
    assert_eq!(layout!(super::Metadata), (352, 8));
    assert_eq!(
        layout!(super::Metadata<super::metadata::SwiftDeclaration>),
        (384, 8)
    );
    assert_eq!(layout!(super::ValidatedSpans), (520, 8));
    assert_eq!(layout!(ValidatedSwiftReactor), (664, 8));
    assert_eq!(layout!(SignatureView<'_>), (24, 8));
    assert_eq!(layout!(GlobalView<'_>), (24, 8));
    assert_eq!(layout!(super::SegmentView<'_>), (24, 8));
    assert_eq!(layout!(super::policy::Policy<'_>), (8, 8));
    println!("descriptor target layouts (size, align): SwiftProof={:?}; SwiftMetadata={:?}; LegacyProof={:?}; FrozenMetadata={:?}; SignatureView={:?}; GlobalView={:?}; SegmentView={:?}; Policy={:?}",
        layout!(ValidatedSwiftReactor), layout!(super::Metadata<super::metadata::SwiftDeclaration>),
        layout!(super::ValidatedSpans), layout!(super::Metadata), layout!(SignatureView<'_>),
        layout!(GlobalView<'_>), layout!(super::SegmentView<'_>), layout!(super::policy::Policy<'_>));
}
