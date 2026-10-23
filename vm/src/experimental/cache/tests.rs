use super::*;
use crate::{Limits, Module, Op};

fn leb(mut value: u32) -> Vec<u8> {
    let mut bytes = Vec::new();
    loop {
        let b = (value & 127) as u8;
        value >>= 7;
        bytes.push(b | if value != 0 { 128 } else { 0 });
        if value == 0 {
            return bytes;
        }
    }
}
fn section(module: &mut Vec<u8>, id: u8, bytes: &[u8]) {
    module.push(id);
    module.extend(leb(bytes.len() as u32));
    module.extend_from_slice(bytes);
}
fn module(code: &[u8], profile: Profile) -> Vec<u8> {
    let mut bytes = b"\0asm\x01\0\0\0".to_vec();
    section(&mut bytes, 1, &[1, 0x60, 0, 0]);
    section(&mut bytes, 3, &[1, 0]);
    if profile == Profile::TableMemoryV3 {
        section(&mut bytes, 4, &[1, 0x70, 1, 1, 1]);
    }
    section(&mut bytes, 5, &[1, 1, 1, 1]);
    section(&mut bytes, 6, &[1, 0x7f, 1, 0x41, 0, 0x0b]);
    let mut body = vec![1, 1, 0x7f];
    body.extend_from_slice(code);
    let mut payload = vec![1];
    payload.extend(leb(body.len() as u32));
    payload.extend(body);
    section(&mut bytes, 10, &payload);
    bytes
}
fn old(operation: Operation, labels: &[u32]) -> Op {
    match operation {
        Operation::Unreachable => Op::Unreachable,
        Operation::Nop => Op::Nop,
        Operation::Block {
            kind,
            result,
            end,
            alternative,
        } => Op::Block {
            kind: match kind {
                ControlKind::Block => crate::BlockKind::Block,
                ControlKind::Loop => crate::BlockKind::Loop,
                ControlKind::If => crate::BlockKind::If,
            },
            result,
            end,
            alternative,
        },
        Operation::Else { end } => Op::Else { end },
        Operation::End => Op::End,
        Operation::Br(n) => Op::Br(n),
        Operation::BrIf(n) => Op::BrIf(n),
        Operation::BrTable {
            first,
            count,
            default,
        } => Op::BrTable(labels[first..first + count].to_vec(), default),
        Operation::Return => Op::Return,
        Operation::Call(n) => Op::Call(n),
        Operation::CallIndirect(n) => Op::CallIndirect(n),
        Operation::MemoryCopy => Op::MemoryCopy,
        Operation::MemoryFill => Op::MemoryFill,
        Operation::Drop => Op::Drop,
        Operation::Select => Op::Select,
        Operation::LocalGet(n) => Op::LocalGet(n),
        Operation::LocalSet(n) => Op::LocalSet(n),
        Operation::LocalTee(n) => Op::LocalTee(n),
        Operation::GlobalGet(n) => Op::GlobalGet(n),
        Operation::GlobalSet(n) => Op::GlobalSet(n),
        Operation::Load { opcode, offset } => Op::Load { opcode, offset },
        Operation::Store { opcode, offset } => Op::Store { opcode, offset },
        Operation::MemorySize => Op::MemorySize,
        Operation::MemoryGrow => Op::MemoryGrow,
        Operation::Const(value) => Op::Const(value),
        Operation::Numeric(n) => Op::Numeric(n),
        Operation::Saturating(n) => Op::Saturating(n),
    }
}
fn cache(bytes: &[u8], profile: Profile) -> FunctionCache {
    let cancellation = Cancellation::default();
    let spans = super::super::validate_spans(
        bytes,
        Limits {
            profile,
            ..Limits::default()
        },
        super::super::ValidationBudget::default(),
        &cancellation,
    )
    .unwrap();
    FunctionCache::new(spans, CacheBudget::default(), &cancellation).unwrap()
}
#[test]
fn frozen_ir_parity_for_all_supported_opcode_shapes() {
    for profile in [
        Profile::IntegerV1,
        Profile::NumericV2,
        Profile::TableMemoryV3,
    ] {
        let mut code = vec![
            0, 1, 0, 0x0c, 0, 0, 0x0d, 0, 0, 0x0e, 3, 0, 0, 0, 0, 0, 0x0f, 0, 0x10, 0, 0, 0x1a, 0,
            0x1b,
        ];
        for opcode in 0x20..=0x24 {
            code.extend([0, opcode, 0]);
        }
        for opcode in 0x28..=0x3e {
            if !profile.floats() && matches!(opcode, 0x2a | 0x2b | 0x38 | 0x39) {
                continue;
            }
            code.extend([0, opcode, 0, 0x80, 1]);
        }
        code.extend([0, 0x3f, 0, 0, 0x40, 0, 0, 0x41, 0x7f, 0, 0x42, 0x80, 0x7f]);
        for opcode in 0x45..=0xc4 {
            if matches!(opcode, 0x45..=0x5a | 0x67..=0x8a | 0xa7 | 0xac | 0xad | 0xc0..=0xc4)
                || profile.floats()
                    && matches!(opcode, 0x5b..=0x66 | 0x8b..=0xa6 | 0xa8..=0xab | 0xae..=0xbf)
            {
                code.extend([0, opcode]);
            }
        }
        if profile.floats() {
            code.extend([
                0, 0x43, 0, 0, 0xc0, 0x7f, 0, 0x44, 0, 0, 0, 0, 0, 0, 0xf8, 0x7f,
            ]);
            for sub in 0..=7 {
                code.extend([0, 0xfc, sub]);
            }
        }
        if profile == Profile::TableMemoryV3 {
            code.extend([0, 0x11, 0, 0, 0, 0xfc, 10, 0, 0, 0, 0xfc, 11, 0]);
        }
        code.extend([
            0, 2, 0x40, 3, 0x40, 0, 0x0d, 1, 0x0b, 0x0b, 0, 4, 0x40, 1, 5, 1, 0x0b, 0, 0x0b,
        ]);
        let bytes = module(&code, profile);
        let frozen = Module::decode(
            &bytes,
            &Limits {
                profile,
                ..Limits::default()
            },
        )
        .unwrap();
        let mut cache = cache(&bytes, profile);
        let pin = cache.pin(0, &Cancellation::default()).unwrap();
        let view = cache.view(&pin).unwrap();
        let function = &frozen.functions[0];
        assert_eq!(view.locals, function.locals);
        assert_eq!(view.body_offset, function.offset);
        assert_eq!(view.type_index, function.type_index);
        assert_eq!(view.instructions.len(), function.code.len());
        for (new, original) in view.instructions.iter().zip(&function.code) {
            assert_eq!(new.offset, original.offset);
            assert_eq!(
                format!("{:?}", old(new.operation, view.branch_targets)),
                format!("{:?}", original.op)
            );
        }
        cache.release(pin).unwrap();
    }
}
#[test]
fn stale_token_nonce_and_owner_exhaustion_fail_closed() {
    let bytes = module(&[0x0b], Profile::IntegerV1);
    let mut cache = cache(&bytes, Profile::IntegerV1);
    let pin = cache.pin(0, &Cancellation::default()).unwrap();
    let stale = FunctionPin {
        owner: pin.owner,
        slot: pin.slot,
        nonce: pin.nonce,
    };
    cache.release(pin).unwrap();
    assert_eq!(
        cache.view(&stale).err().unwrap().kind,
        CacheFailureKind::InvalidPin
    );
    assert_eq!(
        cache.release(stale).unwrap_err().failure.kind,
        CacheFailureKind::InvalidPin
    );
    cache.next_nonce = u64::MAX;
    assert_eq!(
        cache.pin(0, &Cancellation::default()).unwrap_err().kind,
        CacheFailureKind::NonceExhausted
    );
    assert_eq!(cache.usage().active_pins, 0);
    let local_owner = AtomicU64::new(u64::MAX);
    let mut usage = CacheUsage::default();
    let cancel = Cancellation::default();
    let meter = Meter {
        budget: CacheBudget::default(),
        usage: &mut usage,
        cancellation: &cancel,
        function: None,
        offset: 0,
    };
    assert_eq!(
        issue_owner(&local_owner, &meter).unwrap_err().kind,
        CacheFailureKind::IdentityExhausted
    );
    assert_eq!(local_owner.load(Ordering::Relaxed), u64::MAX);
}

#[test]
fn scalar_statistics_never_wrap_or_leak_construction() {
    let bytes = module(&[0x0b], Profile::IntegerV1);
    let cancel = Cancellation::default();
    let mut cache = cache(&bytes, Profile::IntegerV1);
    cache.usage.decodes = u64::MAX;
    assert_eq!(
        cache.pin(0, &cancel).unwrap_err().kind,
        CacheFailureKind::WorkExhausted
    );
    assert_eq!(
        (
            cache.usage.resident_bytes,
            cache.usage.construction_bytes,
            cache.usage.active_pins
        ),
        (0, 0, 0)
    );
    cache.usage.decodes = 0;
    let pin = cache.pin(0, &cancel).unwrap();
    cache.usage.hits = u64::MAX;
    assert_eq!(
        cache.pin(0, &cancel).unwrap_err().kind,
        CacheFailureKind::WorkExhausted
    );
    assert_eq!(cache.usage.active_pins, 1);
    cache.release(pin).unwrap();
    cache.usage.work_used = u64::MAX;
    assert_eq!(
        cache.pin(0, &cancel).unwrap_err().kind,
        CacheFailureKind::WorkExhausted
    );
    assert_eq!(cache.usage.work_used, u64::MAX);
}
