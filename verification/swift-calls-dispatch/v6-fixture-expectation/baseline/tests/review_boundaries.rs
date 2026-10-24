//! Independently authored adversarial review regressions; no external engine fixtures.
mod common;
use common::{constant, single, u32leb, Spec};
use mixer_vm::{
    inventory, mixer_vm_invoke, mixer_vm_validate, Instance, Limits, MixerVmLimits, MixerVmReport,
    MixerVmValue, Module, Type, Value,
};

#[test]
fn reference_inventory_does_not_consume_the_instruction_after_ref_as_non_null() {
    // ref.null func; ref.as_non_null; drop; end. 0xd4 has no immediate.
    let bytes = single(vec![0xd0, 0x70, 0xd4, 0x1a, 0x0b], None);
    let report = inventory(&bytes, &Limits::default());
    assert!(
        report.error.is_some(),
        "references must remain non-executable"
    );
    assert!(report.complete);
    assert!(report.inventory_error.is_none());
    assert_eq!(report.opcodes.get(&0xd4), Some(&1));
    assert_eq!(
        report.opcodes.get(&0x1a),
        Some(&1),
        "drop must not be consumed as an immediate"
    );
    assert_eq!(report.opcodes.get(&0x0b), Some(&1));
}

#[test]
fn reference_branch_inventory_consumes_label_index_and_preserves_next_opcode() {
    // Neither reference branch becomes executable merely because inspection knows its shape.
    for opcode in [0xd5, 0xd6] {
        let bytes = single(vec![0xd0, 0x70, opcode, 0x41, 0x1a, 0x0b], None);
        let report = inventory(&bytes, &Limits::default());
        assert!(report.error.is_some());
        assert!(
            report.complete,
            "known label immediate must be inspected: {opcode:#x}"
        );
        assert_eq!(
            report.opcodes.get(&0x41),
            None,
            "label index 65 is not i32.const"
        );
        assert_eq!(report.opcodes.get(&0x1a), Some(&1));
    }
}

#[test]
fn maximal_effective_addresses_trap_without_wrap_or_partial_store() {
    for opcode in [
        0x28, 0x29, 0x2c, 0x2d, 0x2e, 0x2f, 0x30, 0x31, 0x32, 0x33, 0x34, 0x35,
    ] {
        let mut code = constant(Value::I32(-1));
        code.extend([opcode, 0]);
        code.extend(u32leb(u32::MAX));
        code.extend([0x1a, 0x0b]);
        let spec = Spec {
            memory: Some((1, 1)),
            ..Spec::one(vec![], None, code)
        };
        let module = Module::decode(&spec.bytes(), &Limits::default()).unwrap();
        let mut instance = Instance::new(module, Limits::default()).unwrap();
        let error = instance.invoke("run", &[]).unwrap_err();
        assert_eq!(error.code, "memory_out_of_bounds", "opcode {opcode:#x}");
    }
    for opcode in [0x36, 0x37, 0x3a, 0x3b, 0x3c, 0x3d, 0x3e] {
        let mut code = constant(Value::I32(-1));
        code.extend(constant(if opcode == 0x37 || opcode >= 0x3c {
            Value::I64(-1)
        } else {
            Value::I32(-1)
        }));
        code.extend([opcode, 0]);
        code.extend(u32leb(u32::MAX));
        code.push(0x0b);
        let spec = Spec {
            memory: Some((1, 1)),
            ..Spec::one(vec![], None, code)
        };
        let module = Module::decode(&spec.bytes(), &Limits::default()).unwrap();
        let mut instance = Instance::new(module, Limits::default()).unwrap();
        assert_eq!(
            instance.invoke("run", &[]).unwrap_err().code,
            "memory_out_of_bounds"
        );
        assert!(
            instance.memory().iter().all(|byte| *byte == 0),
            "trapping store must not write"
        );
    }
}

#[test]
fn unreachable_code_still_rejects_illegal_indices_and_branch_label_types() {
    let mut illegal_local = vec![0x00, 0x20];
    illegal_local.extend(u32leb(u32::MAX));
    illegal_local.extend([0x1a, 0x0b]);
    assert_eq!(
        Module::decode(&single(illegal_local, None), &Limits::default())
            .unwrap_err()
            .code,
        "validation"
    );
    // The two br_table labels have void and i32 types respectively.
    let table = single(
        vec![
            0x02, 0x7f, 0x02, 0x40, 0x41, 0, 0x0e, 1, 0, 1, 0x0b, 0x0b, 0x0b,
        ],
        Some(Type::I32),
    );
    let error = Module::decode(&table, &Limits::default()).unwrap_err();
    assert_eq!(error.code, "validation");
    assert_eq!(error.message, "br_table targets have different label types");
}

#[test]
fn c_boundary_accepts_documented_unaligned_structs_and_rejects_huge_lengths() {
    let bytes = Spec::one(vec![Type::I32], Some(Type::I32), vec![0x20, 0, 0x0b]).bytes();
    let limits = MixerVmLimits {
        struct_size: std::mem::size_of::<MixerVmLimits>() as u32,
        abi_version: 1,
        fuel: 100,
        memory_pages: 1,
        operand_stack: 128,
        call_depth: 8,
        host_calls: 1,
    };
    let argument = MixerVmValue {
        value_type: 1,
        reserved: 0,
        value: 42,
    };
    let mut limits_storage = vec![0u8; std::mem::size_of::<MixerVmLimits>() + 1];
    let mut argument_storage = vec![0u8; std::mem::size_of::<MixerVmValue>() + 1];
    let mut report_storage = vec![0u8; std::mem::size_of::<MixerVmReport>() + 1];
    // SAFETY: each offset pointer has the full documented readable/writable extent.
    // The C header explicitly permits unaligned fixed structs and forbids overlap.
    unsafe {
        let limits_pointer = limits_storage.as_mut_ptr().add(1).cast::<MixerVmLimits>();
        let argument_pointer = argument_storage.as_mut_ptr().add(1).cast::<MixerVmValue>();
        let report_pointer = report_storage.as_mut_ptr().add(1).cast::<MixerVmReport>();
        limits_pointer.write_unaligned(limits);
        argument_pointer.write_unaligned(argument);
        assert_eq!(
            mixer_vm_invoke(
                bytes.as_ptr(),
                bytes.len(),
                b"run".as_ptr(),
                3,
                argument_pointer,
                1,
                limits_pointer,
                report_pointer
            ),
            0
        );
        let report = report_pointer.read_unaligned();
        assert_eq!(report.value, 42);
        assert_eq!(report.value_type, 1);
        assert_eq!(report.fuel_used, 2);
        assert_eq!(
            mixer_vm_validate(
                std::ptr::null(),
                usize::MAX,
                std::ptr::null(),
                report_pointer
            ),
            3
        );
        assert_eq!(
            mixer_vm_invoke(
                bytes.as_ptr(),
                bytes.len(),
                b"run".as_ptr(),
                3,
                std::ptr::null(),
                usize::MAX,
                std::ptr::null(),
                report_pointer
            ),
            3
        );
    }
}

#[test]
fn c_boundary_rejects_bad_value_contracts_before_execution() {
    let bytes = Spec::one(vec![Type::I32], Some(Type::I32), vec![0x20, 0, 0x0b]).bytes();
    for argument in [
        MixerVmValue {
            value_type: 1,
            reserved: 1,
            value: 2,
        },
        MixerVmValue {
            value_type: 1,
            reserved: 0,
            value: i64::MAX,
        },
        MixerVmValue {
            value_type: 3,
            reserved: 0,
            value: 2,
        },
    ] {
        let mut report = MixerVmReport::default();
        // SAFETY: all buffers are valid for their given extents and do not overlap.
        let status = unsafe {
            mixer_vm_invoke(
                bytes.as_ptr(),
                bytes.len(),
                b"run".as_ptr(),
                3,
                &argument,
                1,
                std::ptr::null(),
                &mut report,
            )
        };
        assert_eq!(status, 3);
        assert_eq!(report.fuel_used, 0);
    }
}
