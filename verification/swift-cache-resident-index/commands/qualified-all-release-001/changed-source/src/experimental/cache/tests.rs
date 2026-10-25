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

#[test]
fn frozen_layout_and_trace_observation() {
    use std::mem::{align_of, offset_of, size_of};
    macro_rules! shape {
        ($ty:ty) => {
            println!(
                "layout {} {} {}",
                stringify!($ty),
                size_of::<$ty>(),
                align_of::<$ty>()
            );
        };
    }
    shape!(FunctionCache);
    shape!(FunctionPin);
    shape!(Slot);
    shape!(PinRecord);
    shape!(DecodedFunction);
    shape!(Meter<'static>);
    shape!(decode::PassState);
    shape!(decode::Reader<'static>);
    shape!(CacheUsage);
    shape!(CacheFailure);
    println!(
        "offsets cache {} {} {} {} {} {} {}",
        offset_of!(FunctionCache, spans),
        offset_of!(FunctionCache, budget),
        offset_of!(FunctionCache, usage),
        offset_of!(FunctionCache, owner),
        offset_of!(FunctionCache, next_nonce),
        offset_of!(FunctionCache, slots),
        offset_of!(FunctionCache, pins)
    );
    println!(
        "offsets pin {} {} {}",
        offset_of!(FunctionPin, owner),
        offset_of!(FunctionPin, slot),
        offset_of!(FunctionPin, nonce)
    );
    println!(
        "offsets slot {} {} {}",
        offset_of!(Slot, entry),
        offset_of!(Slot, pins),
        offset_of!(Slot, last_used)
    );
    println!(
        "offsets decoded {} {} {} {} {} {} {}",
        offset_of!(DecodedFunction, function),
        offset_of!(DecodedFunction, type_index),
        offset_of!(DecodedFunction, body_offset),
        offset_of!(DecodedFunction, locals),
        offset_of!(DecodedFunction, instructions),
        offset_of!(DecodedFunction, branch_targets),
        offset_of!(DecodedFunction, bytes)
    );
    println!(
        "offsets meter {} {} {} {} {}",
        offset_of!(Meter<'static>, budget),
        offset_of!(Meter<'static>, usage),
        offset_of!(Meter<'static>, cancellation),
        offset_of!(Meter<'static>, function),
        offset_of!(Meter<'static>, offset)
    );
    println!(
        "offsets pinrecord {} {}",
        offset_of!(PinRecord, nonce),
        offset_of!(PinRecord, entry)
    );
    println!("offsets decoder {:?}", decode::frozen_offsets());
    println!("scratch {}", scratch_bytes());
    for profile in [
        Profile::IntegerV1,
        Profile::NumericV2,
        Profile::TableMemoryV3,
    ] {
        let bytes = module(&[0x41, 0x7f, 0x1a, 0x0b], profile);
        let mut c = cache(&bytes, profile);
        println!("new {:?} {:?}", profile, c.usage());
        let p = c.pin(0, &Cancellation::default()).unwrap();
        println!("miss {:?} {:?}", profile, c.usage());
        let q = c.pin(0, &Cancellation::default()).unwrap();
        println!("hit {:?} {:?}", profile, c.usage());
        c.release(p).unwrap();
        c.release(q).unwrap();
        println!("release {:?} {:?}", profile, c.usage());
        let x = c.pin(99, &Cancellation::default()).unwrap_err();
        println!("invalid {:?} {:?}", profile, x);
        let token = Cancellation::default();
        token.cancel();
        let x = c.pin(99, &token).unwrap_err();
        println!("cancel {:?} {:?}", profile, x);
    }
    let bytes = module(&[0x0b], Profile::IntegerV1);
    for (label, budget) in [
        (
            "entries_zero",
            CacheBudget {
                max_entries: 0,
                ..CacheBudget::default()
            },
        ),
        (
            "pins_zero",
            CacheBudget {
                max_pins: 0,
                ..CacheBudget::default()
            },
        ),
        (
            "capacity_widened",
            CacheBudget {
                capacity_bytes: CacheBudget::default().capacity_bytes + 1,
                ..CacheBudget::default()
            },
        ),
        (
            "entry_widened",
            CacheBudget {
                entry_bytes: CacheBudget::default().entry_bytes + 1,
                ..CacheBudget::default()
            },
        ),
    ] {
        let token = Cancellation::default();
        let spans = super::super::validate_spans(
            &bytes,
            Limits::default(),
            super::super::ValidationBudget::default(),
            &token,
        )
        .unwrap();
        println!(
            "precedence new {label} {:?}",
            FunctionCache::new(spans, budget, &token).err().unwrap()
        );
    }
    for label in ["scratch_cancel", "entry", "capacity", "nonce", "work_pin"] {
        let mut c = cache(&bytes, Profile::IntegerV1);
        let token = Cancellation::default();
        if label == "scratch_cancel" {
            c.budget.capacity_bytes = c.usage.fixed_reserved + scratch_bytes() - 1;
            token.cancel();
        }
        if label == "entry" {
            c.budget.entry_bytes = 0;
        }
        if label == "capacity" {
            c.budget.capacity_bytes = c.usage.fixed_reserved + scratch_bytes();
        }
        if label == "nonce" {
            c.next_nonce = u64::MAX;
        }
        if label == "work_pin" {
            for _ in 0..64 {
                let _ = c.pin(0, &token).unwrap();
            }
            c.budget.work_credits = c.usage.work_used;
        }
        println!("precedence pin {label} {:?}", c.pin(0, &token).unwrap_err());
    }
    let mut many = b"\0asm\x01\0\0\0".to_vec();
    section(&mut many, 1, &[1, 0x60, 0, 0]);
    section(&mut many, 3, &[2, 0, 0]);
    section(&mut many, 10, &[2, 2, 0, 0x0b, 2, 0, 0x0b]);
    let build = || {
        let token = Cancellation::default();
        let spans = super::super::validate_spans(
            &many,
            Limits::default(),
            super::super::ValidationBudget::default(),
            &token,
        )
        .unwrap();
        FunctionCache::new(
            spans,
            CacheBudget {
                max_entries: 1,
                max_pins: 2,
                ..CacheBudget::default()
            },
            &token,
        )
        .unwrap()
    };
    let token = Cancellation::default();
    let mut c = build();
    let p = c.pin(0, &token).unwrap();
    println!("precedence all_pinned {:?}", c.pin(1, &token).unwrap_err());
    c.release(p).unwrap();
    let base = c.usage.work_used;
    let p = c.pin(1, &token).unwrap();
    let credits = c.usage.work_used - base;
    c.release(p).unwrap();
    for prefix in 0..credits {
        let mut c = build();
        let p = c.pin(0, &token).unwrap();
        c.release(p).unwrap();
        c.budget.work_credits = c.usage.work_used + prefix;
        let e = c.pin(1, &token).unwrap_err();
        println!("eviction prefix {prefix} {e:?}");
    }

    #[cfg(feature = "experimental-swift-reactor")]
    {
        use crate::experimental_swift_reactor::allocation_tests::measure;
        let bytes = module(&[0x41, 0x7f, 0x1a, 0x0b], Profile::IntegerV1);
        let spans = super::super::validate_spans(
            &bytes,
            Limits::default(),
            super::super::ValidationBudget::default(),
            &Cancellation::default(),
        )
        .unwrap();
        let token = Cancellation::default();
        let (mut c, s) =
            measure(|| FunctionCache::new(spans, CacheBudget::default(), &token).unwrap());
        println!("allocation new {:?}", s);
        let (p, s) = measure(|| c.pin(0, &token).unwrap());
        println!("allocation miss {:?}", s);
        let (q, s) = measure(|| c.pin(0, &token).unwrap());
        println!("allocation hit {:?}", s);
        let (_, s) = measure(|| {
            c.release(p).unwrap();
            c.release(q).unwrap();
        });
        println!("allocation release {:?}", s);
    }
}

#[test]
fn frozen_borrowed_transients_fit_existing_scratch() {
    use std::mem::size_of;
    // A scan wrapper returns before build is called. Each wrapper contains one
    // literal PassState; scan_borrowed/build_borrowed contain only PassParts.
    // Thus one 128-Patch state is simultaneous, even though the unchanged old
    // model conservatively retains two sequential states/readers in its sum.
    // Count every new argument/return/field-borrow transfer conservatively.
    let named = [
        (1, size_of::<decode::PassState>()),
        (2, size_of::<decode::Reader<'static>>()),
        (1, size_of::<Meter<'static>>()),
        (3, size_of::<CacheFailure>()),
        (1, size_of::<[bool; 64]>()),
        (2, size_of::<DecodedFunction>()),
        (4, size_of::<decode::Counts>()),
        (
            3,
            size_of::<borrowed::CacheParts<'static, borrowed::FrozenMode>>(),
        ),
        (
            3,
            size_of::<borrowed::CacheFields<'static, borrowed::FrozenMode>>(),
        ),
        (2, size_of::<borrowed::FrozenOperation<'static>>()),
        (2, size_of::<borrowed::FrozenPolicy<'static>>()),
        (3, size_of::<decode::PassParts<'static>>()),
        (
            3,
            size_of::<crate::experimental::descriptors::FunctionSpanView<'static>>(),
        ),
        // Default resident hooks retain literal work while introducing helper
        // argument/Result transfers. Lookup, removal and insertion execute in
        // separate phases; counting their complete union is deliberately
        // conservative, not a claim that these frames coexist.
        (3, size_of::<Result<Option<usize>, CacheFailure>>()),
        (6, size_of::<Result<(), CacheFailure>>()),
        (
            3,
            size_of::<(
                &'static [Slot],
                &'static mut (),
                u32,
                usize,
                &'static mut Meter<'static>,
            )>(),
        ),
        (1, 256), // unchanged scalar/loop allowance, additional to named adapters
    ];
    let actual: usize = named.into_iter().map(|(n, size)| n * size).sum();
    println!(
        "legacy named simultaneous conservative={} unchanged_scratch={}",
        actual,
        scratch_bytes()
    );
    assert!(actual <= scratch_bytes());
}
