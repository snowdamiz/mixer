mod common;
use common::*;
use mixer_vm::{validation_inventory as inventory, Instance, Limits, Module, Type::*, Value};
fn run(
    bytes: Vec<u8>,
    args: &[mixer_vm::Value],
    limits: Limits,
) -> Result<Option<mixer_vm::Value>, mixer_vm::Error> {
    let m = Module::decode(&bytes, &limits)?;
    Instance::new(m, limits)?.invoke("run", args)
}
fn ordinary(bytes: Vec<u8>) -> Result<Option<mixer_vm::Value>, mixer_vm::Error> {
    run(bytes, &[], Limits::default())
}
#[test]
fn arithmetic_wrap_and_arguments() {
    let b = Spec::one(
        vec![I32, I32],
        Some(I32),
        vec![0x20, 0, 0x20, 1, 0x6a, 0x0b],
    )
    .bytes();
    assert_eq!(
        run(b, &[Value::I32(i32::MAX), Value::I32(1)], Limits::default()).unwrap(),
        Some(Value::I32(i32::MIN))
    );
}
#[test]
fn integer64_signed_leb_roundtrips() {
    for x in [i64::MIN, i64::MAX, 0, 1, -1, 64, -65] {
        let mut c = constant(Value::I64(x));
        c.push(0x0b);
        assert_eq!(ordinary(single(c, Some(I64))).unwrap(), Some(Value::I64(x)));
    }
}
#[test]
fn division_traps_and_remainder_overflow_semantics() {
    for (a, b, opcode, expected) in [
        (1, 0, 0x6d, "integer_divide_by_zero"),
        (i32::MIN, -1, 0x6d, "integer_overflow"),
    ] {
        let mut c = constant(Value::I32(a));
        c.extend(constant(Value::I32(b)));
        c.extend([opcode, 0x0b]);
        assert_eq!(ordinary(single(c, Some(I32))).unwrap_err().code, expected);
    }
    let mut c = constant(Value::I64(i64::MIN));
    c.extend(constant(Value::I64(-1)));
    c.extend([0x81, 0x0b]);
    assert_eq!(ordinary(single(c, Some(I64))).unwrap(), Some(Value::I64(0)));
}
#[test]
fn if_result_both_arms() {
    let b = Spec::one(
        vec![I32],
        Some(I32),
        vec![0x20, 0, 4, 0x7f, 0x41, 7, 5, 0x41, 9, 0x0b, 0x0b],
    )
    .bytes();
    assert_eq!(
        run(b.clone(), &[Value::I32(1)], Limits::default()).unwrap(),
        Some(Value::I32(7))
    );
    assert_eq!(
        run(b, &[Value::I32(0)], Limits::default()).unwrap(),
        Some(Value::I32(9))
    );
}
#[test]
fn loop_countdown_and_branch() {
    let mut s = Spec::one(
        vec![I32],
        Some(I32),
        vec![
            2, 0x40, 3, 0x40, 0x20, 0, 0x45, 0x0d, 1, 0x20, 1, 0x20, 0, 0x6a, 0x21, 1, 0x20, 0,
            0x41, 1, 0x6b, 0x21, 0, 0x0c, 0, 0x0b, 0x0b, 0x20, 1, 0x0b,
        ],
    );
    s.functions[0].locals = vec![I32];
    assert_eq!(
        run(s.bytes(), &[Value::I32(10)], Limits::default()).unwrap(),
        Some(Value::I32(55))
    );
}
#[test]
fn branch_preserves_block_result_and_discards_intermediates() {
    let c = vec![2, 0x7f, 0x41, 11, 0x41, 42, 0x0c, 0, 0x00, 0x0b, 0x0b];
    assert_eq!(
        ordinary(single(c, Some(I32))).unwrap(),
        Some(Value::I32(42))
    );
}
#[test]
fn br_if_preserves_false_label_value() {
    let c = vec![
        2, 0x7f, 0x41, 42, 0x41, 0, 0x0d, 0, 0x41, 1, 0x6a, 0x0b, 0x0b,
    ];
    assert_eq!(
        ordinary(single(c, Some(I32))).unwrap(),
        Some(Value::I32(43))
    );
}
#[test]
fn branch_to_function_and_return() {
    for opcode in [0x0c, 0x0f] {
        let mut c = vec![0x41, 42, opcode];
        if opcode == 0x0c {
            c.push(0);
        }
        c.extend([0x00, 0x0b]);
        assert_eq!(
            ordinary(single(c, Some(I32))).unwrap(),
            Some(Value::I32(42))
        );
    }
}
#[test]
fn br_table_default_and_index() {
    let s = Spec::one(
        vec![I32],
        Some(I32),
        vec![
            2, 0x7f, 2, 0x7f, 0x41, 42, 0x20, 0, 0x0e, 1, 0, 1, 0x0b, 0x41, 1, 0x6a, 0x0b, 0x0b,
        ],
    );
    assert_eq!(
        run(s.bytes(), &[Value::I32(0)], Limits::default()).unwrap(),
        Some(Value::I32(43))
    );
    assert_eq!(
        run(s.bytes(), &[Value::I32(-1)], Limits::default()).unwrap(),
        Some(Value::I32(42))
    );
}
#[test]
fn direct_call_and_locals() {
    let mut s = Spec::one(vec![], Some(I64), vec![0x42, 7, 0x10, 1, 0x0b]);
    s.functions.push(Function::new(
        vec![I64],
        Some(I64),
        vec![0x20, 0, 0x42, 2, 0x7e, 0x0b],
    ));
    assert_eq!(ordinary(s.bytes()).unwrap(), Some(Value::I64(14)));
}
#[test]
fn memory_load_store_and_data() {
    let mut s = Spec::one(
        vec![],
        Some(I32),
        vec![0x41, 1, 0x41, 42, 0x36, 0, 0, 0x41, 1, 0x28, 0, 0, 0x0b],
    );
    s.memory = Some((1, 2));
    s.data = vec![(0, vec![9])];
    let m = Module::decode(&s.bytes(), &Limits::default()).unwrap();
    let mut i = Instance::new(m, Limits::default()).unwrap();
    assert_eq!(i.memory()[0], 9);
    assert_eq!(i.invoke("run", &[]).unwrap(), Some(Value::I32(42)));
    assert_eq!(i.memory()[1..5], [42, 0, 0, 0]);
}
#[test]
fn narrow_load_sign_extends() {
    let mut s = Spec::one(vec![], Some(I64), vec![0x41, 0, 0x30, 0, 0, 0x0b]);
    s.memory = Some((1, 1));
    s.data = vec![(0, vec![0x80])];
    assert_eq!(ordinary(s.bytes()).unwrap(), Some(Value::I64(-128)));
}
#[test]
fn effective_address_does_not_wrap32() {
    let mut c = constant(Value::I32(-1));
    c.extend([0x28, 2, 1, 0x0b]);
    let mut s = Spec::one(vec![], Some(I32), c);
    s.memory = Some((1, 1));
    let e = ordinary(s.bytes()).unwrap_err();
    assert_eq!(e.code, "memory_out_of_bounds");
    assert_eq!(e.function, Some(0));
    assert!(e.offset > 8);
}
#[test]
fn oob_store_and_segment_trap() {
    let mut s = Spec::one(
        vec![],
        None,
        vec![0x41, 0, 0x42, 0, 0x37, 3, 0x80, 0x80, 4, 0x0b],
    );
    s.memory = Some((1, 1));
    assert_eq!(
        ordinary(s.bytes()).unwrap_err().code,
        "memory_out_of_bounds"
    );
    s.functions[0].code = vec![0x0b];
    s.data = vec![(65536, vec![1])];
    assert_eq!(
        ordinary(s.bytes()).unwrap_err().code,
        "memory_out_of_bounds"
    );
}
#[test]
fn memory_growth_is_capped_and_zero_filled() {
    let mut s = Spec::one(vec![I32], Some(I32), vec![0x20, 0, 0x40, 0, 0x0b]);
    s.memory = Some((1, 2));
    let m = Module::decode(&s.bytes(), &Limits::default()).unwrap();
    let mut i = Instance::new(m, Limits::default()).unwrap();
    assert_eq!(
        i.invoke("run", &[Value::I32(1)]).unwrap(),
        Some(Value::I32(1))
    );
    assert_eq!(i.memory().len(), 131072);
    assert_eq!(i.memory()[65536], 0);
    assert_eq!(
        i.invoke("run", &[Value::I32(1)]).unwrap(),
        Some(Value::I32(-1))
    );
    assert_eq!(i.memory().len(), 131072);
}
#[test]
fn mutable_globals_persist_per_instance() {
    let mut s = Spec::one(
        vec![],
        Some(I32),
        vec![0x23, 0, 0x41, 1, 0x6a, 0x24, 0, 0x23, 0, 0x0b],
    );
    s.globals = vec![(Value::I32(10), true)];
    let mut i = Instance::new(
        Module::decode(&s.bytes(), &Limits::default()).unwrap(),
        Limits::default(),
    )
    .unwrap();
    assert_eq!(i.invoke("run", &[]).unwrap(), Some(Value::I32(11)));
    assert_eq!(i.invoke("run", &[]).unwrap(), Some(Value::I32(12)));
}
#[test]
fn infinite_loop_is_metered() {
    let l = Limits {
        fuel: 10,
        ..Limits::default()
    };
    let e = run(single(vec![3, 0x40, 0x0c, 0, 0x0b, 0x0b], None), &[], l).unwrap_err();
    assert_eq!(e.code, "fuel_exhausted");
    assert_eq!(e.function, Some(0));
}
#[test]
fn recursion_uses_explicit_bounded_frames() {
    let l = Limits {
        call_depth: 3,
        ..Limits::default()
    };
    assert_eq!(
        run(single(vec![0x10, 0, 0x0b], None), &[], l)
            .unwrap_err()
            .code,
        "call_depth_exceeded"
    );
}
#[test]
fn cancellation_before_execution() {
    let b = single(vec![0x0b], None);
    let mut i = Instance::new(
        Module::decode(&b, &Limits::default()).unwrap(),
        Limits::default(),
    )
    .unwrap();
    i.cancellation().cancel();
    assert_eq!(i.invoke("run", &[]).unwrap_err().code, "cancelled");
}
#[test]
fn host_imports_are_metered_and_capability_closed() {
    let mut s = Spec::one(vec![], None, vec![0x10, 0, 0x10, 0, 0x0b]);
    s.imports = vec![("checkpoint".into(), vec![], None)];
    assert_eq!(
        run(
            s.bytes(),
            &[],
            Limits {
                host_calls: 1,
                ..Limits::default()
            }
        )
        .unwrap_err()
        .code,
        "host_call_limit"
    );
    s.imports[0].0 = "arbitrary_socket".into();
    let inv = inventory(&s.bytes(), &Limits::default());
    assert!(inv.complete);
    assert_eq!(inv.imports[0].1, "arbitrary_socket");
    assert_eq!(inv.error.unwrap().code, "unsupported");
}
#[test]
fn host_abort_is_a_structured_failure() {
    let mut s = Spec::one(vec![], None, vec![0x41, 7, 0x10, 0, 0x0b]);
    s.imports = vec![("abort".into(), vec![I32], None)];
    assert_eq!(ordinary(s.bytes()).unwrap_err().code, "host_abort");
}
#[test]
fn invalid_stack_types_and_indices_fail_validation() {
    for code in [
        vec![0x6a, 0x0b],
        vec![0x42, 1, 0x41, 1, 0x6a, 0x0b],
        vec![0x20, 0, 0x0b],
        vec![0x0c, 1, 0x0b],
        vec![0x10, 1, 0x0b],
        vec![0x41, 1, 0x0b],
    ] {
        assert_eq!(
            Module::decode(&single(code, None), &Limits::default())
                .unwrap_err()
                .code,
            "validation"
        );
    }
}
#[test]
fn malformed_control_is_rejected() {
    for code in [
        vec![5, 0x0b],
        vec![2, 0x40, 5, 0x0b, 0x0b],
        vec![0x41, 1, 4, 0x7f, 0x41, 1, 0x0b, 0x0b],
        vec![2, 0x40, 0x0b],
        vec![0x0b, 0x01],
    ] {
        assert!(Module::decode(&single(code, None), &Limits::default()).is_err());
    }
}
#[test]
fn unreachable_stack_polymorphism_is_valid() {
    assert_eq!(
        Module::decode(
            &single(vec![0x00, 0x6a, 0x0b], Some(I32)),
            &Limits::default()
        )
        .unwrap()
        .function_count(),
        1
    );
    assert_eq!(
        ordinary(single(vec![0x00, 0x6a, 0x0b], Some(I32)))
            .unwrap_err()
            .code,
        "unreachable"
    );
}
#[test]
fn unsupported_opcodes_fail_before_execution_and_partial_inventory_is_honest() {
    let inv = inventory(
        &single(vec![0x41, 1, 0x43, 0, 0, 0, 0, 0x0b], Some(I32)),
        &Limits::default(),
    );
    assert!(!inv.complete);
    assert!(inv.opcodes.contains_key(&0x43));
    let e = inv.error.unwrap();
    assert_eq!(e.code, "unsupported");
    assert_eq!(e.function, Some(0));
}
#[test]
fn malformed_leb_width_and_unused_bits() {
    for code in [
        vec![0x41, 0x80, 0x80, 0x80, 0x80, 0x08, 0x0b],
        vec![
            0x42, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 2, 0x0b,
        ],
    ] {
        assert_eq!(
            Module::decode(&single(code, Some(I32)), &Limits::default())
                .unwrap_err()
                .code,
            "malformed"
        );
    }
    let mut b = b"\0asm\x01\0\0\0".to_vec();
    b.extend([1, 0x80, 0x80, 0x80, 0x80, 0x10]);
    assert_eq!(
        Module::decode(&b, &Limits::default()).unwrap_err().code,
        "malformed"
    );
}
#[test]
fn duplicate_ordered_sections_bad_utf8_and_length_are_rejected() {
    for suffix in [
        vec![1, 1, 0, 1, 1, 0],
        vec![3, 1, 0, 1, 1, 0],
        vec![0, 2, 1, 255],
        vec![1, 127],
    ] {
        let mut b = b"\0asm\x01\0\0\0".to_vec();
        b.extend(suffix);
        assert!(Module::decode(&b, &Limits::default()).is_err());
    }
}
#[test]
fn resource_limits_fail_closed() {
    let b = single(vec![0x41, 1, 0x41, 2, 0x6a, 0x0b], Some(I32));
    assert_eq!(
        Module::decode(
            &b,
            &Limits {
                module_bytes: 8,
                ..Limits::default()
            }
        )
        .unwrap_err()
        .code,
        "limit"
    );
    assert_eq!(
        Module::decode(
            &b,
            &Limits {
                operand_stack: 1,
                ..Limits::default()
            }
        )
        .unwrap_err()
        .code,
        "limit"
    );
    assert_eq!(
        Module::decode(
            &b,
            &Limits {
                instructions: 2,
                ..Limits::default()
            }
        )
        .unwrap_err()
        .code,
        "limit"
    );
    let b = single(vec![2, 0x40, 2, 0x40, 0x0b, 0x0b, 0x0b], None);
    assert_eq!(
        Module::decode(
            &b,
            &Limits {
                control_depth: 2,
                ..Limits::default()
            }
        )
        .unwrap_err()
        .code,
        "limit"
    );
}
#[test]
fn wrong_arguments_and_unknown_exports_fail() {
    let b = Spec::one(vec![I32], Some(I32), vec![0x20, 0, 0x0b]).bytes();
    assert_eq!(
        run(b, &[Value::I64(1)], Limits::default())
            .unwrap_err()
            .code,
        "invalid_arguments"
    );
}
#[test]
fn decoder_mutation_smoke_has_no_panics() {
    let original = single(vec![0x41, 42, 0x0b], Some(I32));
    for end in 0..original.len() {
        assert!(
            std::panic::catch_unwind(|| Module::decode(&original[..end], &Limits::default()))
                .is_ok()
        );
    }
    for i in 0..original.len() {
        for bit in 0..8 {
            let mut b = original.clone();
            b[i] ^= 1 << bit;
            assert!(std::panic::catch_unwind(|| Module::decode(&b, &Limits::default())).is_ok());
        }
    }
    let mut seed = 0x13579bdfu32;
    for len in 0..512 {
        let mut b = b"\0asm\x01\0\0\0".to_vec();
        for _ in 0..len {
            seed ^= seed << 13;
            seed ^= seed >> 17;
            seed ^= seed << 5;
            b.push(seed as u8);
        }
        assert!(std::panic::catch_unwind(|| Module::decode(&b, &Limits::default())).is_ok());
    }
}

#[test]
fn non_authorizing_inventory_records_unsupported_float_and_bulk_memory() {
    let bytes = single(vec![0x43, 0, 0, 0, 0, 0x1a, 0x0b], None);
    let inv = mixer_vm::inventory(&bytes, &Limits::default());
    assert!(inv.complete);
    assert!(inv.inventory_error.is_none());
    assert_eq!(inv.error.unwrap().code, "unsupported");
    assert_eq!(inv.opcodes.get(&0x43), Some(&1));
    let bytes = single(vec![0xfd, 0, 0x0b], None);
    let inv = mixer_vm::inventory(&bytes, &Limits::default());
    assert!(!inv.complete);
    assert_eq!(inv.inventory_error.unwrap().code, "inventory_unsupported");
    assert!(inv.error.is_some());
}

#[test]
fn narrowed_instance_limits_revalidate_control_and_source_size() {
    let bytes = single(vec![2, 0x40, 2, 0x40, 0x0b, 0x0b, 0x0b], None);
    let m = Module::decode(&bytes, &Limits::default()).unwrap();
    let error = match Instance::new(
        m.clone(),
        Limits {
            control_depth: 2,
            ..Limits::default()
        },
    ) {
        Ok(_) => panic!("must reject"),
        Err(e) => e,
    };
    assert_eq!(error.code, "limit");
    let error = match Instance::new(
        m,
        Limits {
            module_bytes: 8,
            ..Limits::default()
        },
    ) {
        Ok(_) => panic!("must reject"),
        Err(e) => e,
    };
    assert_eq!(error.code, "limit");
}

#[test]
fn invalid_import_signatures_memory_alignment_and_immutable_globals_reject() {
    let mut s = Spec::one(vec![], None, vec![0x0b]);
    s.imports = vec![("checkpoint".into(), vec![I32], None)];
    assert_eq!(
        Module::decode(&s.bytes(), &Limits::default())
            .unwrap_err()
            .code,
        "unsupported"
    );
    let mut s = Spec::one(vec![], Some(I32), vec![0x41, 0, 0x28, 3, 0, 0x0b]);
    s.memory = Some((1, 1));
    assert_eq!(
        Module::decode(&s.bytes(), &Limits::default())
            .unwrap_err()
            .code,
        "validation"
    );
    let mut s = Spec::one(vec![], None, vec![0x41, 0, 0x24, 0, 0x0b]);
    s.globals = vec![(Value::I32(1), false)];
    assert_eq!(
        Module::decode(&s.bytes(), &Limits::default())
            .unwrap_err()
            .code,
        "validation"
    );
}

#[test]
fn mutated_executable_modules_never_panic_with_tight_execution_budgets() {
    let originals = [
        single(vec![0x41, 42, 0x0b], Some(I32)),
        single(vec![2, 0x40, 3, 0x40, 0x0c, 1, 0x0b, 0x0b, 0x0b], None),
    ];
    for original in originals {
        for index in 0..original.len() {
            for bit in 0..8 {
                let mut bytes = original.clone();
                bytes[index] ^= 1 << bit;
                let limits = Limits {
                    fuel: 100,
                    call_depth: 4,
                    memory_pages: 2,
                    ..Limits::default()
                };
                assert!(
                    std::panic::catch_unwind(|| {
                        if let Ok(module) = Module::decode(&bytes, &limits) {
                            if let Ok(mut instance) = Instance::new(module, limits) {
                                let _ = instance.invoke("run", &[]);
                            }
                        }
                    })
                    .is_ok(),
                    "mutation index={index} bit={bit}"
                );
            }
        }
    }
}

#[test]
fn memory_limit_flags_are_bytes_and_cannot_use_leb_aliases() {
    let mut b = b"\0asm\x01\0\0\0".to_vec();
    // A limits flag is a byte; 0x80,0x00 is not a valid alias for 0x00.
    section(&mut b, 5, vec![1, 0x80, 0, 0]);
    assert!(Module::decode(&b, &Limits::default()).is_err());
}
