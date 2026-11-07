mod common;
use common::*;
use mixer_vm::{Instance, Limits, Module, Profile, Type, Value};
fn limits() -> Limits {
    Limits {
        profile: Profile::TableMemoryV3,
        ..Limits::default()
    }
}
fn instance(spec: &Spec, l: Limits) -> Result<Instance, mixer_vm::Error> {
    Instance::new(Module::decode(&spec.bytes(), &l)?, l)
}
fn indirect() -> Spec {
    let mut s = Spec::one(
        vec![Type::I32],
        Some(Type::I32),
        vec![0x20, 0, 0x11, 1, 0, 0x0b],
    );
    s.functions
        .push(Function::new(vec![], Some(Type::I32), vec![0x41, 42, 0x0b]));
    s.table = Some((2, 2));
    s.elements = vec![(1, vec![1])];
    s
}
fn bulk(copy: bool) -> Spec {
    let mut s = Spec::one(
        vec![Type::I32; 3],
        None,
        vec![
            0x20,
            0,
            0x20,
            1,
            0x20,
            2,
            0xfc,
            if copy { 10 } else { 11 },
            0,
            0x0b,
        ],
    );
    if copy {
        s.functions[0].code.insert(9, 0);
    }
    s.memory = Some((1, 1));
    s.data = vec![(0, (0..32).collect())];
    s
}
fn args(a: i32, b: i32, c: i32) -> [Value; 3] {
    [Value::I32(a), Value::I32(b), Value::I32(c)]
}
#[test]
fn indirect_calls_null_and_bounds_have_structured_traps() {
    let mut i = instance(&indirect(), limits()).unwrap();
    assert_eq!(
        i.invoke("run", &[Value::I32(1)]).unwrap(),
        Some(Value::I32(42))
    );
    for (index, code) in [
        (0, "indirect_call_null"),
        (2, "table_out_of_bounds"),
        (-1, "table_out_of_bounds"),
    ] {
        let e = i.invoke("run", &[Value::I32(index)]).unwrap_err();
        assert_eq!(e.code, code);
        assert_eq!(e.function, Some(0));
        assert!(e.offset > 8);
    }
}
#[test]
fn equivalent_duplicate_function_types_match_structurally() {
    let mut s = indirect();
    s.functions
        .push(Function::new(vec![], Some(Type::I32), vec![0x41, 9, 0x0b]));
    s.elements = vec![(1, vec![2])];
    assert_eq!(
        instance(&s, limits())
            .unwrap()
            .invoke("run", &[Value::I32(1)])
            .unwrap(),
        Some(Value::I32(9))
    );
}
#[test]
fn mismatched_function_signature_traps_without_calling_target() {
    let mut s = indirect();
    s.functions[1].result = Some(Type::I64);
    s.functions[1].code = vec![0x42, 9, 0x0b];
    s.functions
        .push(Function::new(vec![], Some(Type::I32), vec![0x41, 1, 0x0b]));
    s.functions[0].code[3] = 2;
    assert_eq!(
        instance(&s, limits())
            .unwrap()
            .invoke("run", &[Value::I32(1)])
            .unwrap_err()
            .code,
        "indirect_call_type_mismatch"
    );
}
#[test]
fn element_order_overlap_explicit_table_and_zero_length_bounds() {
    let mut s = indirect();
    s.functions
        .push(Function::new(vec![], Some(Type::I32), vec![0x41, 7, 0x0b]));
    s.elements = vec![(0, vec![1, 1]), (1, vec![2]), (2, vec![])];
    s.explicit_elements = true;
    s.export_table = true;
    assert_eq!(
        instance(&s, limits())
            .unwrap()
            .invoke("run", &[Value::I32(1)])
            .unwrap(),
        Some(Value::I32(7))
    );
    for offset in [3, u32::MAX] {
        s.elements = vec![(offset, vec![])];
        assert_eq!(
            match instance(&s, limits()) {
                Ok(_) => panic!("must trap"),
                Err(e) => e,
            }
            .code,
            "table_out_of_bounds"
        );
    }
    s.elements = vec![(2, vec![1])];
    assert_eq!(
        match instance(&s, limits()) {
            Ok(_) => panic!("must trap"),
            Err(e) => e,
        }
        .code,
        "table_out_of_bounds"
    );
}
#[test]
fn table_type_index_function_index_and_quota_validate_before_instantiation() {
    let mut s = indirect();
    s.elements = vec![(0, vec![99])];
    assert_eq!(
        Module::decode(&s.bytes(), &limits()).unwrap_err().code,
        "validation"
    );
    s.elements.clear();
    s.functions[0].code[3] = 99;
    assert_eq!(
        Module::decode(&s.bytes(), &limits()).unwrap_err().code,
        "validation"
    );
    s.functions[0].code[3] = 1;
    s.table = None;
    assert_eq!(
        Module::decode(&s.bytes(), &limits()).unwrap_err().code,
        "validation"
    );
    let s = indirect();
    assert_eq!(
        Module::decode(
            &s.bytes(),
            &Limits {
                table_elements: 1,
                ..limits()
            }
        )
        .unwrap_err()
        .code,
        "limit"
    );
    let m = Module::decode(&s.bytes(), &limits()).unwrap();
    assert_eq!(
        match Instance::new(
            m,
            Limits {
                table_elements: 1,
                ..limits()
            }
        ) {
            Ok(_) => panic!("must reject narrower limit"),
            Err(e) => e,
        }
        .code,
        "limit"
    );
}

#[test]
fn measured_table_shape_fits_only_the_new_bounded_resource_class() {
    let mut s = indirect();
    s.table = Some((46_700, 46_700));
    s.elements = vec![(4096, vec![1; 42_604])];
    let mut i = instance(&s, limits()).unwrap();
    for selector in [4096, 46_699] {
        assert_eq!(
            i.invoke("run", &[Value::I32(selector)]).unwrap(),
            Some(Value::I32(42))
        );
    }
    assert_eq!(
        i.invoke("run", &[Value::I32(4095)]).unwrap_err().code,
        "indirect_call_null"
    );
    assert_eq!(
        i.invoke("run", &[Value::I32(46_700)]).unwrap_err().code,
        "table_out_of_bounds"
    );
    s.table = Some((65_536, 65_536));
    assert!(instance(&s, limits()).is_ok());
    s.table = Some((65_537, 65_537));
    assert_eq!(
        Module::decode(&s.bytes(), &limits()).unwrap_err().code,
        "limit"
    );

    let mut bytes = b"\0asm\x01\0\0\0".to_vec();
    section(&mut bytes, 4, vec![1, 0x70, 0, 1]); // min1, absent maximum.
    assert!(Instance::new(Module::decode(&bytes, &limits()).unwrap(), limits()).is_ok());
}
#[test]
fn old_profiles_reject_table_and_bulk_features() {
    for p in [Profile::IntegerV1, Profile::NumericV2] {
        let l = Limits {
            profile: p,
            ..Limits::default()
        };
        assert_eq!(
            Module::decode(&indirect().bytes(), &l).unwrap_err().code,
            "unsupported"
        );
        assert_eq!(
            Module::decode(&bulk(true).bytes(), &l).unwrap_err().code,
            "unsupported"
        );
    }
}
#[test]
fn recursive_indirect_calls_share_depth_and_fuel_limits() {
    let mut s = Spec::one(vec![], None, vec![0x41, 0, 0x11, 0, 0, 0x0b]);
    s.table = Some((1, 1));
    s.elements = vec![(0, vec![0])];
    assert_eq!(
        instance(
            &s,
            Limits {
                call_depth: 3,
                ..limits()
            }
        )
        .unwrap()
        .invoke("run", &[])
        .unwrap_err()
        .code,
        "call_depth_exceeded"
    );
    assert_eq!(
        instance(
            &s,
            Limits {
                fuel: 3,
                ..limits()
            }
        )
        .unwrap()
        .invoke("run", &[])
        .unwrap_err()
        .code,
        "fuel_exhausted"
    );
}
#[test]
fn approved_imports_remain_metered_when_called_indirectly() {
    let mut s = Spec::one(vec![], None, vec![0x41, 0, 0x11, 0, 0, 0x0b]);
    s.imports = vec![("checkpoint".into(), vec![], None)];
    s.table = Some((1, 1));
    s.elements = vec![(0, vec![0])];
    assert_eq!(
        instance(
            &s,
            Limits {
                host_calls: 0,
                ..limits()
            }
        )
        .unwrap()
        .invoke("run", &[])
        .unwrap_err()
        .code,
        "host_call_limit"
    );
    let mut i = instance(&s, limits()).unwrap();
    i.invoke("run", &[]).unwrap();
    assert_eq!(i.host_calls_used, 1);
}
#[test]
fn overlapping_copy_is_memmove_in_both_directions() {
    for (dst, src) in [(4, 0), (0, 4)] {
        let s = bulk(true);
        let mut i = instance(&s, limits()).unwrap();
        let mut expected = i.memory().to_vec();
        expected.copy_within(src..src + 16, dst);
        i.invoke("run", &args(dst as i32, src as i32, 16)).unwrap();
        assert_eq!(i.memory(), expected);
    }
}
#[test]
fn bulk_bounds_preflight_preserves_memory_and_zero_lengths_check_addresses() {
    for copy in [true, false] {
        let mut i = instance(&bulk(copy), limits()).unwrap();
        let before = i.memory().to_vec();
        for a in [args(65535, 0, 2), args(-1, 0, 0), args(0, 0, -1)] {
            assert_eq!(
                i.invoke("run", &a).unwrap_err().code,
                "memory_out_of_bounds"
            );
            assert_eq!(i.memory(), before);
        }
        if copy {
            assert_eq!(
                i.invoke("run", &args(0, 65536, 1)).unwrap_err().code,
                "memory_out_of_bounds"
            );
            assert_eq!(i.memory(), before);
        }
        i.invoke("run", &args(65536, if copy { 65536 } else { 999 }, 0))
            .unwrap();
    }
}
#[test]
fn fill_masks_byte_and_bulk_fuel_is_precharged_before_mutation() {
    let s = bulk(false);
    let mut i = instance(&s, limits()).unwrap();
    i.invoke("run", &args(0, 0x1234, 3)).unwrap();
    assert_eq!(&i.memory()[..4], &[0x34, 0x34, 0x34, 3]);
    let mut i = instance(
        &s,
        Limits {
            fuel: 4,
            ..limits()
        },
    )
    .unwrap();
    let before = i.memory().to_vec();
    assert_eq!(
        i.invoke("run", &args(0, 255, 65)).unwrap_err().code,
        "fuel_exhausted"
    );
    assert_eq!(i.memory(), before);
    assert_eq!(i.fuel_remaining, 0);
    let mut i = instance(
        &s,
        Limits {
            fuel: 7,
            ..limits()
        },
    )
    .unwrap();
    i.invoke("run", &args(0, 255, 65)).unwrap();
    assert_eq!(i.fuel_remaining, 0);
}
#[test]
fn unknown_table_forms_and_bulk_indices_fail_closed() {
    let mut b = b"\0asm\x01\0\0\0".to_vec();
    section(&mut b, 4, vec![1, 0x6f, 1, 1, 1]);
    assert_eq!(
        Module::decode(&b, &limits()).unwrap_err().code,
        "unsupported"
    );
    for flags in [1, 3, 4, 5, 6, 7] {
        let mut b = b"\0asm\x01\0\0\0".to_vec();
        section(&mut b, 9, vec![1, flags]);
        assert_eq!(
            Module::decode(&b, &limits()).unwrap_err().code,
            "unsupported"
        );
    }
    let mut s = bulk(false);
    s.functions[0].code[8] = 1;
    assert_eq!(
        Module::decode(&s.bytes(), &limits()).unwrap_err().code,
        "validation"
    );
    let mut s = indirect();
    s.functions[0].code[4] = 1;
    assert_eq!(
        Module::decode(&s.bytes(), &limits()).unwrap_err().code,
        "validation"
    );
}

#[test]
fn cancellation_and_bad_element_declarations_do_not_execute() {
    let mut i = instance(&bulk(true), limits()).unwrap();
    let before = i.memory().to_vec();
    i.cancellation().cancel();
    assert_eq!(
        i.invoke("run", &args(2, 0, 16)).unwrap_err().code,
        "cancelled"
    );
    assert_eq!(i.memory(), before);
    let mut bytes = b"\0asm\x01\0\0\0".to_vec();
    section(&mut bytes, 2, vec![1, 1, b'm', 1, b't', 1, 0x70, 0, 1]);
    assert_eq!(
        Module::decode(&bytes, &limits()).unwrap_err().code,
        "unsupported"
    );
    let mut s = indirect();
    s.elements = vec![(0, vec![1, 1]), (0, vec![1])];
    assert_eq!(
        Module::decode(
            &s.bytes(),
            &Limits {
                table_elements: 2,
                ..limits()
            }
        )
        .unwrap_err()
        .code,
        "limit"
    );
}

#[test]
fn table_bulk_mutation_smoke_is_bounded_and_never_panics() {
    for (bytes, arguments) in [
        (indirect().bytes(), vec![Value::I32(1)]),
        (bulk(true).bytes(), args(4, 0, 16).to_vec()),
        (bulk(false).bytes(), args(4, 255, 16).to_vec()),
    ] {
        for end in 0..bytes.len() {
            assert!(std::panic::catch_unwind(|| Module::decode(&bytes[..end], &limits())).is_ok());
        }
        for index in 0..bytes.len() {
            for bit in 0..8 {
                let mut candidate = bytes.clone();
                candidate[index] ^= 1 << bit;
                let l = Limits {
                    fuel: 100,
                    call_depth: 4,
                    memory_pages: 2,
                    table_elements: 16,
                    ..limits()
                };
                assert!(std::panic::catch_unwind(|| {
                    if let Ok(module) = Module::decode(&candidate, &l) {
                        if let Ok(mut i) = Instance::new(module, l) {
                            let _ = i.invoke("run", &arguments);
                        }
                    }
                })
                .is_ok());
            }
        }
    }
}

#[test]
fn indirect_float_values_preserve_bits_through_arguments_and_results() {
    for value in [Value::F32(0xff80_0001), Value::F64(0xfff0_0000_0000_0001)] {
        let mut s = Spec::one(
            vec![value.ty()],
            Some(value.ty()),
            vec![0x20, 0, 0x41, 0, 0x11, 1, 0, 0x0b],
        );
        s.functions.push(Function::new(
            vec![value.ty()],
            Some(value.ty()),
            vec![0x20, 0, 0x0b],
        ));
        s.table = Some((1, 1));
        s.elements = vec![(0, vec![1])];
        assert_eq!(
            instance(&s, limits())
                .unwrap()
                .invoke("run", &[value])
                .unwrap(),
            Some(value)
        );
    }
}

#[test]
fn indirect_and_bulk_operands_are_statically_typed_even_when_unreachable() {
    let mut s = indirect();
    s.functions[0].code = vec![0x42, 0, 0x11, 1, 0, 0x0b];
    assert_eq!(
        Module::decode(&s.bytes(), &limits()).unwrap_err().code,
        "validation"
    );
    for copy in [true, false] {
        let mut s = bulk(copy);
        s.functions[0].params[0] = Type::I64;
        assert_eq!(
            Module::decode(&s.bytes(), &limits()).unwrap_err().code,
            "validation"
        );
    }
    let mut s = indirect();
    s.functions[0].code = vec![0x00, 0x11, 99, 0, 0x0b];
    assert_eq!(
        Module::decode(&s.bytes(), &limits()).unwrap_err().code,
        "validation"
    );
}
